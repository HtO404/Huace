# -*- coding: utf-8 -*-
"""
文件名称: main.py
功能描述: AIBOX运营商切换测试主程序
作者: AutoGen
创建日期: 2026-04-01
运行环境: Python 3.8+, uiautomator2, adb
"""

import os
import sys
import time
import datetime
import threading
from typing import Dict, List, Tuple
from functools import wraps

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import (
    ConfigManager,
    LogManager,
    CSVReporter,
    ADBChecker,
    DeviceController
)

try:
    import uiautomator2 as u2
except ImportError:
    print("错误: 请先安装 uiautomator2 库")
    print("安装命令: pip install uiautomator2")
    sys.exit(1)


def timeout_decorator(timeout_seconds, default_return=None):
    """超时装饰器 - 防止操作无限等待"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            completed = [False]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
                finally:
                    completed[0] = True

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout_seconds)

            if not completed[0]:
                return default_return
            if exception[0]:
                raise exception[0]
            return result[0]
        return wrapper
    return decorator


class OperatorSwitchTest:
    """AIBOX运营商切换测试类"""

    OPERATORS = [
        {'name': '中国联通', 'id': 'operator_unicom'},
        {'name': '中国电信', 'id': 'operator_telecom'},
        {'name': '中国移动', 'id': 'operator_mobile'},
    ]

    def __init__(self):
        self.config = ConfigManager()

        self.app_config = self.config.get_app_config()
        self.device_config = self.config.get_device_config()
        self.test_params = self.config.get_test_params()
        self.ui_elements = self.config.get_ui_elements()
        self.output_config = self.config.get_output_config()

        self.project_name = self.app_config['project_name']
        self.root_path = self.app_config['root_path']
        self.app_package = self.app_config['app_package']

        self.date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.export_num = f"{self.output_config['base_export_num']:02d}"

        self.csv_dir = os.path.join(self.root_path, f"{self.project_name}_csv")
        self.log_dir = os.path.join(self.root_path, f"{self.project_name}_log")
        self.image_dir = os.path.join(self.root_path, f"{self.project_name}_image")

        log_filename = f"{self.date_str}_{self.export_num}_{self.project_name}_log.txt"
        self.logger = LogManager(self.log_dir, log_filename)

        csv_filename = f"{self.date_str}_{self.export_num}.csv"
        self.csv_reporter = CSVReporter(self.csv_dir, csv_filename)

        self.device = None
        self.device_controller = DeviceController()

        self.success_count = 0
        self.fail_count = 0
        self.timeout_count = 0
        self.freeze_count = 0
        self.restart_count = 0

        self.screenshot_mode = self.output_config.get('screenshot_mode', 'reduced')
        self.screenshot_count = 0
        self.logger.info(f"[INIT] 截图模式: {self.screenshot_mode}")

    def connect_device(self) -> bool:
        """连接设备"""
        serial = self.device_config.get('device_serial')
        if serial:
            self.logger.info(f"连接设备: {serial}")
            self.device = u2.connect(serial)
        else:
            self.logger.info("连接默认设备")
            self.device = u2.connect()

        self.device_controller.device = self.device
        self.device_controller.set_app_package(self.app_package)
        return True

    def safe_wait(self, elem, timeout: float) -> bool:
        """安全执行wait()，带超时保护"""
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
            self.logger.warning(f"[SAFE_WAIT] wait超时({timeout}秒)，强制返回False")
            return False
        return result[0] if result[0] is not None else False

    def check_operator_switch(self) -> bool:
        """检查运营商切换是否成功 - 带有超时保护"""
        network_level_id = self.ui_elements['network_level']
        self.logger.debug(f"[CHECK_SWITCH] 开始检查运营商切换结果")

        try:
            elem = self.device(resourceId=network_level_id)
            exists = elem.wait(timeout=200)
            self.logger.debug(f"[CHECK_SWITCH] elem.wait()返回: {exists}")
            return exists
        except Exception as e:
            self.logger.warning(f"[CHECK_SWITCH] 检查运营商切换异常: {e}")
            return False


    def switch_operator(self, operator: Dict, cycle_num: int) -> Tuple[bool, float, str]:
        """
        切换运营商 - 带有详细日志

        Returns:
            (是否成功, 耗时毫秒, 备注)
        """
        operator_name = operator['name']
        operator_id = self.ui_elements[operator['id']]

        self.logger.info(f"[======================SWITCH {operator_name}] 开始切换运营商======================")
        start_time = time.time()

        # self.take_screenshot_with_name(f"switch_{operator_name}_before")

        try:
            self.logger.debug(f"[SWITCH {operator_name}] 查找运营商控件...")
            # operator_elem = self.device(resourceId=operator_id)
            operator_elem = self.device(text=operator_name)
            self.logger.debug(f"[SWITCH {operator_name}] 等待控件出现，最多5秒...")

            if not operator_elem.wait(timeout=10):
                self.logger.warning(f"[SWITCH {operator_name}] 5秒未找到控件，执行上滑...")
                self.device.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                time.sleep(2)
                self.logger.info(f"[SWITCH {operator_name}] 上滑完成，再次等待控件...")
                if not operator_elem.wait(timeout=5):
                    elapsed = (time.time() - start_time) * 1000
                    self.logger.warning(f"[SWITCH {operator_name}] 上滑后仍未找到控件，耗时: {elapsed:.2f}ms")
                    self.take_screenshot_with_name(f"switch_{operator_name}_not_found")
                    return False, elapsed, f"未找到{operator_name}控件"
                else:
                    self.logger.info(f"[SWITCH {operator_name}] 上滑后找到控件")

            self.logger.debug(f"[SWITCH {operator_name}] 控件已找到，执行点击...")
            operator_elem.click()
            self.logger.info(f"[SWITCH {operator_name}] 已点击运营商按钮")
            # self.take_screenshot_with_name('test11111')

            timeout_val = self.test_params['operator_switch_timeout']
            self.logger.debug(f"[SWITCH {operator_name}] 等待加载弹窗消失，超时: {timeout_val}秒...")
            # success, elapsed = self.wait_loading_dialog(timeout=timeout_val)
            #
            # if not success:
            #     elapsed = (time.time() - start_time) * 100000
            #     self.logger.warning(f"[SWITCH {operator_name}] 等待加载弹窗超时，耗时: {elapsed:.2f}ms")
            #     self.take_screenshot_with_name(f"switch_{operator_name}_timeout")
            #     return False, elapsed, f"等待加载弹窗超时({timeout_val}s)"

            self.logger.debug(f"[SWITCH {operator_name}] 检查运营商切换结果...")
            if self.check_operator_switch():
                elapsed = (time.time() - start_time) * 1000
                self.logger.info(f"[======================SWITCH {operator_name}] 运营商切换成功，耗时: {elapsed:.2f}ms==================================================")
                # self.take_screenshot_with_name(f"switch_{operator_name}_success")
                return True, elapsed, "切换成功"
            else:
                elapsed = (time.time() - start_time) * 1000
                self.logger.warning(f"[SWITCH {operator_name}] 切换后网络等级元素不存在，耗时: {elapsed:.2f}ms")
                self.take_screenshot_with_name(f"switch_{operator_name}_fail")
                return False, elapsed, "切换后网络等级元素不存在"

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.logger.error(f"[SWITCH {operator_name}] 切换运营商异常: {e}")
            self.take_screenshot_with_name(f"switch_{operator_name}_error")
            return False, elapsed, f"异常: {str(e)[:30]}"

    def check_freeze(self) -> bool:
        """检测是否卡死 - 只检查network_level是否在200ms内出现"""
        network_level_id = self.ui_elements['network_level']
        elem = self.device(resourceId=network_level_id)
        # 200ms内出现说明没卡死，没出现说明可能卡死
        return not elem.wait(timeout=200)

    def navigate_to_operator_page(self) -> bool:
        """
        导航到运营商切换页面 - 带有详细日志
        操作流程：点击【手动飞行】→点击右侧空白区域→点击"三"菜单按钮→选择"4G"选项
        """
        self.logger.info("[NAV] 开始导航到运营商切换页面...")

        try:
            manual_flight_id = self.ui_elements['manual_flight']
            right_blank = self.ui_elements['right_blank_area']
            menu_button_id = self.ui_elements['menu_button']
            option_4g = self.ui_elements['option_4g']

            self.logger.info("[NAV] 步骤1: 点击【手动飞行】按钮...")
            if self.device(resourceId=manual_flight_id).wait(timeout=5):
                self.device(resourceId=manual_flight_id).click()
                self.logger.info("[NAV] 步骤1完成: 已点击手动飞行")
            else:
                self.logger.warning("[NAV] 步骤1跳过: 未找到手动飞行按钮")

            time.sleep(4)
            self.logger.debug("[NAV] 等待4秒完成")

            self.logger.info("[NAV] 步骤2: 点击右侧空白区域...")
            if right_blank and ',' in right_blank:
                x_ratio, y_ratio = map(float, right_blank.split(','))
                self.logger.debug(f"[NAV] 点击坐标: ({x_ratio}, {y_ratio})")
                self.device.click(x_ratio, y_ratio)
                self.logger.info("[NAV] 步骤2完成: 已点击右侧空白区域")
            else:
                self.logger.warning("[NAV] 步骤2跳过: 右侧空白区域坐标未配置")

            time.sleep(4)
            self.logger.debug("[NAV] 等待4秒完成")

            self.logger.info("[NAV] 步骤3: 点击【三】菜单按钮...")
            if self.device(resourceId=menu_button_id).wait(timeout=5):
                self.device(resourceId=menu_button_id).click()
                self.logger.info("[NAV] 步骤3完成: 已点击菜单按钮")
            else:
                self.logger.warning("[NAV] 步骤3跳过: 未找到菜单按钮")

            time.sleep(4)
            self.logger.debug("[NAV] 等待4秒完成")

            self.logger.info("[NAV] 步骤4: 选择【4G】选项...")
            if self.device(resourceId=option_4g).wait(timeout=5):
                self.device(resourceId=option_4g).click()
                self.logger.info("[NAV] 步骤4完成: 已选择4G选项")
                time.sleep(2)
                self.logger.info("[NAV] 步骤5: 向上滚动以显示运营商切换按钮...")
                self.device.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                self.logger.info("[NAV] 步骤5完成: 已滚动")
            else:
                self.logger.warning("[NAV] 步骤4跳过: 未找到4G选项")

            time.sleep(4)
            self.logger.debug("[NAV] 等待4秒完成")

            self.logger.info("[NAV] 导航到运营商切换页面完成，返回True")
            return True

        except Exception as e:
            self.logger.error(f"[NAV] 导航到运营商页面异常: {e}")
            import traceback
            self.logger.error(f"[NAV] 异常详情: {traceback.format_exc()}")
            return False

    def take_screenshot_with_name(self, mark: str) -> str:
        """
        截图并以指定标记命名 - 支持截图模式控制
        命名方式与txt、csv保持一致
        """
        # if self.screenshot_mode == 'minimal':
        #     if '_fail' not in mark and '_error' not in mark and '_freeze' not in mark:
        #         self.logger.debug(f"[SCREENSHOT] 模式minimal，跳过非失败截图: {mark}")
        #         return ""
        # elif self.screenshot_mode == 'reduced':
        #     critical_markers = ['init', 'page_ready', 'freeze', 'restart', 'fail', 'error']
        #     if not any(m in mark for m in critical_markers):
        #         return ""

        try:
            os.makedirs(self.image_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ts}_{self.export_num}_{self.project_name}_{mark}.png"
            filepath = os.path.join(self.image_dir, filename)
            self.device.screenshot(filepath)
            self.screenshot_count += 1
            self.logger.info(f"[SCREENSHOT] 截图已保存({self.screenshot_count}): {filename}")
            return filepath
        except Exception as e:
            self.logger.error(f"[SCREENSHOT] 截图失败: {e}")
            return ""

    def handle_freeze(self) -> bool:
        """处理卡死情况 - 带有详细日志"""
        self.logger.warning("[FREEZE] 检测到应用卡死，执行重启处理...")
        self.freeze_count += 1
        self.logger.info(f"[FREEZE] 卡死计数+1，当前卡死次数: {self.freeze_count}")

        self.take_screenshot_with_name("freeze")

        if self.test_params['enable_app_restart']:
            self.logger.info("[FREEZE] 启用应用重启，开始执行restart_app()...")
            return self.restart_app()
        else:
            self.logger.warning("[FREEZE] 应用重启已禁用，返回False")
            return False

    def restart_app(self) -> bool:
        """重启应用并初始化 - 修复版本"""
        self.logger.info("=" * 40)
        self.logger.info("[RESTART] 开始重启应用...")

        try:
            self.logger.info("[RESTART] 步骤1: 杀后台应用...")
            self.device.app_stop(self.app_package)
            time.sleep(3)
            self.logger.info("[RESTART] 步骤1完成: 应用已停止")

            self.logger.info("[RESTART] 步骤2: 启动应用...")
            self.device.app_start(self.app_package)
            time.sleep(5)
            self.logger.info("[RESTART] 步骤2完成: 应用已启动")

            self.logger.info("[RESTART] 步骤3: 导航到运营商切换页面...")
            nav_result = self.navigate_to_operator_page()
            if not nav_result:
                self.logger.warning("[RESTART] navigate_to_operator_page()返回False，继续执行")

            self.restart_count += 1
            self.logger.info(f"[RESTART] 重启计数+1，当前重启次数: {self.restart_count}")

            self.take_screenshot_with_name("restart")
            self.logger.info("[RESTART] 应用重启完成")
            return True

        except Exception as e:
            self.logger.error(f"[RESTART] 重启应用异常: {e}")
            self.take_screenshot_with_name("restart_error")
            return False

    def run_single_cycle(self, cycle_num: int):
        """执行单次测试循环 - 带有详细日志"""
        self.logger.info(f"===== 第{cycle_num}次循环开始 =====")

        for idx, operator in enumerate(self.OPERATORS):
            operator_name = operator['name']
            self.logger.info(f"[==============================CYCLE {cycle_num}] [{idx+1}/{len(self.OPERATORS)}] 准备切换运营商: {operator_name}===============================")

            try:
                self.logger.info(f"[CYCLE {cycle_num}] [{operator_name}] 开始执行switch_operator()...")
                switch_start = time.time()
                success, duration, remark = self.switch_operator(operator, cycle_num)
                switch_elapsed = time.time() - switch_start
                self.logger.info(f"[CYCLE {cycle_num}] [{operator_name}] switch_operator()完成，耗时: {switch_elapsed:.3f}秒，成功: {success}，备注: {remark}")
            except Exception as e:
                self.logger.error(f"[CYCLE {cycle_num}] [{operator_name}] switch_operator()异常: {e}")
                success, duration, remark = False, 0, f"异常: {str(e)[:50]}"
                switch_elapsed = 0

            try:
                self.logger.debug(f"[CYCLE {cycle_num}] [{operator_name}] 写入CSV结果...")
                self.csv_reporter.write_result(
                    cycle_num=cycle_num,
                    operator=operator_name,
                    operation="切换运营商",
                    result="成功" if success else "失败",
                    duration=duration,
                    remark=remark
                )
                self.logger.debug(f"[CYCLE {cycle_num}] [{operator_name}] CSV写入完成")
            except Exception as e:
                self.logger.error(f"[CYCLE {cycle_num}] [{operator_name}] CSV写入异常: {e}")

            if success:
                self.success_count += 1
                self.logger.info(f"[CYCLE {cycle_num}] [{operator_name}] 成功计数+1，当前成功次数: {self.success_count}")
            else:
                self.fail_count += 1
                self.logger.info(f"[CYCLE {cycle_num}] [{operator_name}] 失败计数+1，当前失败次数: {self.fail_count}")
                if self.test_params['operator_switch_timeout'] >= 100:
                    self.logger.warning(f"[CYCLE {cycle_num}] [{operator_name}] 切换失败: {remark}")
                continue  # 失败处理完再跳


    def run(self):
        """执行完整测试流程 - 带有详细日志"""
        self.logger.info("=" * 60)
        self.logger.info(f"{self.project_name} 运营商切换测试开始")
        self.logger.info(f"循环次数: {self.test_params['cycle_times']}")
        self.logger.info(f"运营商切换超时: {self.test_params['operator_switch_timeout']}s")
        self.logger.info(f"卡死检测超时: {self.test_params['freeze_timeout']}s")
        self.logger.info("=" * 60)

        self.logger.info("[MAIN] 检查ADB设备连接...")
        connected, devices = ADBChecker.check()
        if not connected:
            self.logger.error(f"[MAIN] 设备未连接: {devices}")
            print(f"\n错误: ADB设备未连接\n")
            return

        self.logger.info(f"[MAIN] 设备已连接: {devices}")

        self.logger.info("[MAIN] 连接uiautomator2设备...")
        try:
            self.connect_device()
            self.logger.info("[MAIN] 设备连接成功")
            self.take_screenshot_with_name("init")
        except Exception as e:
            self.logger.error(f"[MAIN] 设备连接失败: {e}")
            print(f"\n错误: 设备连接失败 - {e}\n")
            return

        cycle_times = self.test_params['cycle_times']

        self.logger.info("[MAIN] 开始导航到运营商切换页面...")
        try:
            nav_result = self.navigate_to_operator_page()
            self.logger.info(f"[MAIN] navigate_to_operator_page()返回: {nav_result}")
        except Exception as e:
            self.logger.error(f"[MAIN] navigate_to_operator_page()异常: {e}")

        self.take_screenshot_with_name("page_ready")

        for i in range(1, cycle_times + 1):
            self.logger.info(f"[MAIN] ===================== 开始第{i}次循环 =======================================================")
            try:
                self.run_single_cycle(i)
                self.logger.info(f"[MAIN] 第{i}次循环run_single_cycle()完成")

                if i < cycle_times:
                    wait_time = self.test_params['wait_interval']
                    self.logger.info(f"[MAIN] 第{i}次循环完成，等待{wait_time}秒后继续...")
                    time.sleep(wait_time)
                    self.logger.info(f"[MAIN] 第{i}次循环间等待完成")

            except (ConnectionError, OSError) as e:
                # 致命错误：设备连接问题，终止测试
                self.logger.error(f"[MAIN] 设备连接异常，终止测试: {e}")
                import traceback
                self.logger.error(f"[MAIN] 异常详情: {traceback.format_exc()}")
                break  # 终止循环

            except Exception as e:
                # 非致命错误：继续下一次循环
                self.logger.error(f"[MAIN] 第{i}次循环发生异常: {e}")
                import traceback
                traceback.print_exc()
                self.logger.error(f"[MAIN] 第{i}次循环异常详情: {traceback.format_exc()}")
                continue

        self._generate_summary()

        self.logger.info("=" * 60)
        self.logger.info(f"{self.project_name} 运营商切换测试完成")
        self.logger.info("=" * 60)

    def _generate_summary(self):
        """生成汇总统计"""
        total = self.success_count + self.fail_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0.0

        summary = {
            '总测试次数': total,
            '成功次数': self.success_count,
            '失败次数': self.fail_count,
            '超时次数': self.timeout_count,
            '卡死次数': self.freeze_count,
            '重启次数': self.restart_count,
            '截图次数': self.screenshot_count,
            '成功率': f"{success_rate:.2f}%",
        }

        self.csv_reporter.write_summary(summary)

        self.logger.info("=" * 60)
        self.logger.info("-------------------- 测试汇总 --------------------")
        self.logger.info(f"总测试次数: {total}")
        self.logger.info(f"成功次数: {self.success_count}")
        self.logger.info(f"失败次数: {self.fail_count}")
        self.logger.info(f"超时次数: {self.timeout_count}")
        self.logger.info(f"卡死次数: {self.freeze_count}")
        self.logger.info(f"重启次数: {self.restart_count}")
        self.logger.info(f"截图次数: {self.screenshot_count}")
        self.logger.info(f"成功率: {success_rate:.2f}%")
        self.logger.info("=" * 60)




def main():
    """主函数入口"""
    try:
        cycle_times_input = int(input("请输入循环执行次数: "))
        export_num = int(input("请输入导出次数(用于文件命名): "))
        export_num_str = f"{export_num:02d}"

        test = OperatorSwitchTest()
        
        # 使用用户输入的值覆盖配置文件中的值
        test.test_params['cycle_times'] = cycle_times_input
        test.output_config['base_export_num'] = export_num
        test.export_num = export_num_str

        # 重新创建logger和csv_reporter（在run()之前）
        test.csv_reporter = CSVReporter(
            test.csv_dir,
            f"{test.date_str}_{export_num_str}.csv"
        )
        test.logger = LogManager(
            test.log_dir,
            f"{test.date_str}_{export_num_str}_{test.project_name}_log.txt"
        )

        # 先写入初始化日志
        test.logger.info("=" * 60)
        test.logger.info(f"用户输入循环次数: {cycle_times_input}")
        test.logger.info(f"用户输入导出次数: {export_num}")
        test.logger.info("=" * 60)

        test.run()

    except ValueError as e:
        print(f"输入错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
