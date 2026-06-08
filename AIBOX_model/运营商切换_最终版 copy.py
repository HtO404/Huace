# -*- coding: utf-8 -*-
"""
项目名称: AIBOX 运营商切换测试
功能描述: 最终优化的AIBOX运营商切换测试程序 - 基于原始逻辑，集成 log_up 日志+CSV模块，
          配置统一由 utils.ConfigManager 单例从 config.ini 拉取
作者: AutoGen
创建日期: 2026-04-17
修改日期: 2026-05-19
运行环境: Python 3.8+, uiautomator2, adb
"""

# ===== 标准库 =====
import os
import sys
import time
import threading
import logging
from datetime import datetime

# ===== 第三方库 =====
try:
    import uiautomator2 as u2
except ImportError:
    print("错误: 请先安装 uiautomator2 库")
    print("安装命令: pip install uiautomator2")
    sys.exit(1)

# ===== 本地模块 =====
from log_up import setup_logging, get_export_path, \
    init_csv, write_csv_row, write_csv_summary, log_test_start, \
    log_test_cycle, log_test_cycle_ok, log_test_cycle_fail, log_summary
from utils import ConfigManager


class FinalOperatorSwitch:
    """最终优化的运营商切换测试类 —— 配置全部从 ConfigManager 单例拉取"""

    # 运营商列表 - 按切换顺序排列（业务逻辑顺序，非配置项）
    OPERATORS = ['中国移动', '中国联通', '中国电信']

    def __init__(self, device_serial=None):
        """初始化 —— 从 ConfigManager 拉取所有配置"""
        # ===== 从 config.ini 拉取配置 =====
        config = ConfigManager()

        # UI 元素 ID
        ui = config.get_ui_elements()
        self.operator_ids = {
            '中国移动': ui['operator_mobile'],
            '中国联通': ui['operator_unicom'],
            '中国电信': ui['operator_telecom'],
        }
        self.network_level_id = ui['network_level']

        # 超时 / 间隔参数
        params = config.get_test_params()
        self.operator_switch_timeout = params['operator_switch_timeout']
        self.freeze_timeout = params['freeze_timeout']
        self.wait_interval = params['wait_interval']

        # 设备
        self.device = None
        self.device_serial = device_serial

    def connect_device(self):
        """连接设备"""
        try:
            if self.device_serial:
                logging.info(f"连接设备: {self.device_serial}")
                self.device = u2.connect(self.device_serial)
            else:
                logging.info("连接默认设备")
                self.device = u2.connect()

            logging.info("设备连接成功")
            return True
        except Exception as e:
            logging.error(f"设备连接失败: {e}")
            return False

    def safe_wait(self, elem, timeout: float) -> bool:
        """安全执行wait()，带超时保护 - 基于原始逻辑"""
        result = [None]
        completed = [False]

        def wait_task():
            try:
                result[0] = elem.wait(timeout=timeout)
            except Exception as e:
                result[0] = False
            finally:
                completed[0] = True

        thread = threading.Thread(target=wait_task, daemon=True)
        thread.start()
        thread.join(timeout + 2)

        if not completed[0]:
            logging.warning(f"wait超时({timeout}秒)，强制返回False")
            return False
        return result[0] if result[0] is not None else False

    def check_operator_switch(self) -> bool:
        """检查运营商切换是否成功 - 基于原始逻辑，每 wait_interval 秒检查一次"""
        max_wait_time = self.freeze_timeout     # 最大等待时间（config.ini: freeze_timeout）
        check_interval = self.wait_interval      # 检查间隔（config.ini: wait_interval）

        try:
            start_time = time.time()
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                elem = self.device(resourceId=self.network_level_id)
                if elem.exists:
                    logging.info(f"网络等级元素已出现，等待时间: {elapsed_time}秒")
                    return True

                time.sleep(check_interval)
                elapsed_time = int(time.time() - start_time)

            # 超时处理
            logging.error(f"等待超时，{max_wait_time}秒内网络等级元素未出现")
            return False

        except Exception as e:
            logging.error(f"检查运营商切换异常: {e}")
            return False

    def get_current_operator(self):
        """
        获取当前选中的运营商 - 通过检查单选框的checked属性

        Returns:
            str: 当前运营商名称，如果未找到返回None
        """
        try:
            # 检查每个运营商的单选框checked属性
            for operator in self.OPERATORS:
                operator_id = self.operator_ids[operator]
                operator_elem = self.device(resourceId=operator_id)

                if operator_elem.exists:
                    # 获取checked属性
                    checked = operator_elem.info.get('checked', False)
                    logging.info(f"运营商: {operator}, checked属性: {checked}")

                    if checked:
                        logging.info(f"当前选中的运营商: {operator}")
                        return operator

            logging.warning("未找到当前选中的运营商")
            return None

        except Exception as e:
            logging.error(f"获取当前运营商异常: {e}")
            return None

    def switch_to_next_operator(self, current_operator):
        """
        切换到下一个运营商 - 基于原始switch_operator()函数逻辑

        Args:
            current_operator: 当前运营商名称

        Returns:
            tuple: (bool, str) — (是否成功, 详细信息)
        """
        if current_operator not in self.OPERATORS:
            detail = f"未知的当前运营商: {current_operator}"
            logging.error(detail)
            return False, detail

        # 计算下一个运营商索引
        current_index = self.OPERATORS.index(current_operator)
        next_index = (current_index + 1) % len(self.OPERATORS)
        next_operator = self.OPERATORS[next_index]

        logging.info(f"当前运营商: {current_operator} → 切换为: {next_operator}")
        start_time = time.time()

        try:
            # 查找下一个运营商单选框控件
            next_operator_id = self.operator_ids[next_operator]
            next_operator_elem = self.device(resourceId=next_operator_id)

            # 点击运营商单选框
            next_operator_elem.click()
            logging.info(f"已点击运营商单选框: {next_operator}")

            # 检查运营商切换结果 - 使用原始逻辑
            logging.info("检查运营商切换结果...")
            if self.check_operator_switch():
                elapsed = (time.time() - start_time) * 1000
                detail = f"耗时: {elapsed:.2f}ms"
                logging.info(f"运营商切换成功，{detail}")
                return True, detail
            else:
                elapsed = (time.time() - start_time) * 1000
                detail = f"切换后网络等级元素不存在，耗时: {elapsed:.2f}ms"
                logging.error(detail)
                return False, detail

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            detail = f"运营商切换异常: {e}"
            logging.error(detail)
            return False, detail

    def run_single_cycle(self):
        """
        执行单次循环 - 只切换一次运营商

        Returns:
            tuple: (bool, str, str, str) — (是否成功, 当前运营商, 目标运营商, 详情)
        """
        logging.info("-" * 40)

        # 获取当前运营商状态
        current_operator = self.get_current_operator()

        if current_operator is None:
            logging.warning("无法获取当前运营商状态，跳过本次循环")
            return False, "未知", "未知", "无法获取当前运营商状态"

        # 计算目标运营商
        current_index = self.OPERATORS.index(current_operator)
        next_index = (current_index + 1) % len(self.OPERATORS)
        next_operator = self.OPERATORS[next_index]

        # 切换到下一个运营商
        success, detail = self.switch_to_next_operator(current_operator)

        if success:
            logging.info("✓ 切换成功")
        else:
            logging.error("✗ 切换失败")

        return success, current_operator, next_operator, detail

    def run(self, cycle_times=1):
        """
        执行测试

        Args:
            cycle_times: 循环次数

        Returns:
            tuple: (success_count, fail_count)
        """
        # 连接设备
        if not self.connect_device():
            return 0, 0

        # 执行循环测试
        success_count = 0
        fail_count = 0

        for i in range(1, cycle_times + 1):
            log_test_cycle(i)

            success, current_op, next_op, detail = self.run_single_cycle()

            # 统计
            if success:
                success_count += 1
                log_test_cycle_ok(i)
            else:
                fail_count += 1
                log_test_cycle_fail(i, detail)

            # 写入CSV
            test_item = f"运营商切换: {current_op}→{next_op}"
            status = '成功' if success else '失败'
            write_csv_row(
                csv_path=main_csv_path,
                row=[i, test_item, status, detail]
            )

            time.sleep(self.wait_interval)

        return success_count, fail_count


# 全局CSV路径引用，供 run() 内的循环使用
main_csv_path = None


def main():
    """主函数 —— 配置全部从 ConfigManager 单例拉取"""
    global main_csv_path

    # 加载配置（单例，全项目共享同一实例）
    config = ConfigManager()

    project_name = config.get('AppConfig', 'project_name', fallback='AIBOX_model')
    root_path = config.get('AppConfig', 'root_path', fallback='./AIBOX_model')
    base_export_num = config.getint('OutputConfig', 'base_export_num', fallback=0)

    # 生成导出路径 + 初始化日志
    csv_path, log_path = get_export_path(root_path, project_name, base_export_num)
    main_csv_path = csv_path
    setup_logging(log_path)

    try:
        # 获取用户输入
        cycle_times = int(input("请输入循环执行次数: "))

        # 可选：指定设备序列号
        device_serial = input("请输入设备序列号（留空使用默认设备）: ").strip()
        if not device_serial:
            device_serial = None

        # 日志：测试开始
        log_test_start(project_name, cycle_times)
        if device_serial:
            logging.info(f"设备序列号: {device_serial}")

        # 初始化CSV
        init_csv(csv_path)

        # 创建测试实例并运行
        tester = FinalOperatorSwitch(device_serial)
        success_count, fail_count = tester.run(cycle_times)

        # 输出统计汇总
        total = success_count + fail_count
        log_summary(total, success_count, fail_count)
        write_csv_summary(csv_path, total, success_count, fail_count)

        logging.info("=" * 60)
        logging.info("测试完成")
        logging.info("=" * 60)

    except ValueError:
        logging.error("输入错误: 请输入有效的数字")
    except KeyboardInterrupt:
        logging.warning("\n程序被用户中断")
    except Exception as e:
        logging.error(f"程序执行异常: {e}")


if __name__ == "__main__":
    main()
