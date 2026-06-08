# -*- coding: utf-8 -*-
"""
文件名称: main.py
功能描述: AIBOX运营商切换测试主程序（整合电源控制版本）
作者: AutoGen
创建日期: 2026-04-01
运行环境: Python 3.8+, uiautomator2, adb
"""

import os
import sys
import time
import logging
import datetime
import threading
import serial  # 新增：串口通信模块
import csv     # 新增
import subprocess  # 新增
from typing import Dict, List, Tuple
from functools import wraps

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import (
    ConfigManager,
    CSVReporter,
    ADBChecker,
    DeviceController, LogManager
)

# ===== 本地模块 - 日志与CSV =====
from log_up import setup_logging, get_export_path,     init_csv, write_csv_row, write_csv_summary, log_test_start,     log_test_cycle, log_test_cycle_ok, log_test_cycle_fail, log_summary

try:
    import uiautomator2 as u2
except ImportError:
    print("错误: 请先安装 uiautomator2 库")
    print("安装命令: pip install uiautomator2")
    sys.exit(1)


# 全局CSV路径引用，供 DeviceStatusChecker 和 PowerState 使用
main_csv_path = None


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


class DeviceStatusChecker:
    """设备状态检查器类"""
    
    def __init__(self, device_serial):
        self.device_serial = device_serial
        self.d = None
        self._connect_device()
    
    
    def _connect_device(self):
        """连接安卓设备"""
        try:
            self.d = u2.connect(self.device_serial)
            logging.info(f"成功连接到设备: {self.device_serial}")
        except Exception as e:
            logging.error(f"连接设备失败: {e}")
            raise
    
    def check_status_change(self, expected_status, timeout=60):
        """
        检查设备状态变化
        expected_status: 期望状态 ('AirInsight Box' - 上电成功, '未连接' - 下电成功)
        timeout: 超时时间（秒）
        """
        start_time = time.time()
        end_time = start_time + timeout
        
        while time.time() < end_time:
            try:
                current_status = self._get_current_status()
                if current_status == expected_status:
                    elapsed_time = time.time() - start_time
                    return True, elapsed_time
                time.sleep(2)  # 每2秒检查一次
            except Exception as e:
                logging.warning(f"检查状态时出错: {e}")
                time.sleep(2)
        
        # 超时后截图
        self._take_screenshot(f"timeout_{int(time.time())}")
        return False, timeout
    
    def _get_current_status(self):
        """获取当前设备状态"""
        try:
            # 检查是否存在"AirInsight Box"文本元素
            if self.d(text="AirInsight Box").exists:
                return "AirInsight Box"
            elif self.d(text="取消").exists:
                logging.info("检测到取消按钮，点击")
                self.d(text="取消").click()
            else:
                return "未连接"
        except Exception as e:
            logging.error(f"获取设备状态失败: {e}")
            return "错误"
    
    def _restart_app(self):
        """重启应用"""
        package_name = 'com.huace.groundstation'
        logging.info(f"正在强制关闭: {package_name}")
        self.d.app_stop(package_name)
        time.sleep(5)
        # 5. 重新启动软件
        logging.info(f"正在重新启动: {package_name}")
        self.d.app_start(package_name)
        time.sleep(10)
    
    def _take_screenshot(self, prefix="error", subdir="./AIBOX_model_image"):
        """
        截图并保存 - 支持子目录
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            if subdir:
                os.makedirs(subdir, exist_ok=True)
                filepath = os.path.join(subdir, filename)
                self.d.screenshot(filepath)
            else:
                self.d.screenshot(filename)
            logging.info(f"截图已保存: {filename}")
        except Exception as e:
            logging.error(f"截图失败: {e}")
    
    def check_wifi_available(self, timeout=100):
        """
        检查WIFI是否可用
        """
        start_time = time.time()
        end_time = start_time + timeout

        package_name = 'com.huace.groundstation'
        logging.info(f"正在强制关闭: {package_name}")
        self.d.app_stop(package_name)
        time.sleep(5)
        logging.info(f"正在重新启动: {package_name}")
        self.d.app_start(package_name)

        while time.time() < end_time:
            try:
                if self.d(text="AirInsight Box").exists:
                    logging.info(f"重启后，AirInsight Box存在")
                    return True
                if self.d(text="取消").exists:
                    logging.info("检测到取消按钮，点击")
                    self.d(text="取消").click()
                time.sleep(5)
                
            except subprocess.TimeoutExpired:
                logging.warning("WIFI检查超时")
            except Exception as e:
                logging.warning(f"WIFI检查出错: {e}")
                time.sleep(5)
        
        logging.warning(f"重启后，AirInsight Box在{timeout}秒内未找到")
        return False
    
    def record_to_csv(self, cycle_num, power_on_time, power_on_success, status_change, time_elapsed, 
                  power_off_success, wifi_check=None, operator_results=None, notes=""):
        """记录测试结果到CSV - 支持运营商切换结果"""
        try:
            # 处理运营商切换结果
            unicom_result = ""
            telecom_result = ""
            mobile_result = ""
            
            if operator_results:
                for result in operator_results:
                    if result['operator'] == '中国联通':
                        unicom_result = "成功" if result['success'] else f"失败({result['remark']})"
                    elif result['operator'] == '中国电信':
                        telecom_result = "成功" if result['success'] else f"失败({result['remark']})"
                    elif result['operator'] == '中国移动':
                        mobile_result = "成功" if result['success'] else f"失败({result['remark']})"
            
            with open(main_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    cycle_num,
                    power_on_time,
                    power_on_success,
                    status_change,
                    round(time_elapsed, 2) if time_elapsed else '',
                    power_off_success,
                    wifi_check if wifi_check is not None else '',
                    unicom_result,
                    telecom_result,
                    mobile_result,
                    notes
                ])
        except Exception as e:
            logging.error(f"写入CSV失败: {e}")

class PowerState:
    """电源控制类 - 实现上下电循环和运营商切换测试"""
    
    def __init__(self, timeout_up, duration, interval_down, connection_string, device_serial):
        self.timeout_up = timeout_up  # 上电超时时间
        self.duration = duration
        self.interval_down = interval_down
        self.connection_string = connection_string
        self.device_serial = device_serial
        
        self.state = {
            'up': 0,
            'down': 0,
        }

        self.fail_up = []
        self.fail_down = []

        # ===== 从 ConfigManager 拉取配置 =====
        config = ConfigManager()
        ui = config.get_ui_elements()
        self.ui_manual_flight = ui['manual_flight']
        self.ui_right_blank = ui['right_blank_area']
        self.ui_menu_button = ui['menu_button']
        self.ui_option_4g = ui['option_4g']
        self.ui_back_button = ui.get('back_button_id', 'com.huace.groundstation:id/activity_fly_mode_main_top_sb_back')
        self.ui_network_level = ui['network_level']
        self.operator_ids = {
            '中国移动': ui['operator_mobile'],
            '中国联通': ui['operator_unicom'],
            '中国电信': ui['operator_telecom'],
        }
        params = config.get_test_params()
        self.operator_switch_timeout = params['operator_switch_timeout']
        self.freeze_timeout = params['freeze_timeout']
        self.wait_interval = params['wait_interval']

        # 初始化设备状态检查器
        self.status_checker = DeviceStatusChecker(device_serial)

        logging.info(f'串口为：{self.connection_string}')
        logging.info(f'设备序列号：{self.device_serial}')
        logging.info(f'上电超时时间：{self.timeout_up}秒')
        logging.info(f'下电时间为：{self.interval_down}秒')
        logging.info(f'循环次数为：{self.duration}')
        logging.info(f'******************************************************')

    def navigate_to_operator_page(self) -> bool:
        """
        导航到运营商切换页面
        操作流程：点击【手动飞行】→点击右侧空白区域→点击"三"菜单按钮→选择"4G"选项→上滑
        """
        logging.info("[NAV] 开始导航到运营商切换页面...")

        try:
            # 等待设备稳定
            time.sleep(10)
            
            # 步骤1: 点击【手动飞行】按钮
            logging.info("[NAV] 步骤1: 点击【手动飞行】按钮...")
            if self.status_checker.d(resourceId=self.ui_manual_flight).wait(timeout=5):
                self.status_checker.d(resourceId=self.ui_manual_flight).click()
                logging.info("[NAV] 步骤1完成: 已点击手动飞行")
            else:
                logging.warning("[NAV] 步骤1跳过: 未找到手动飞行按钮")
                return False

            time.sleep(4)

            # 步骤2: 点击右侧空白区域
            logging.info("[NAV] 步骤2: 点击右侧空白区域...")
            if self.ui_right_blank and ',' in self.ui_right_blank:
                x, y = map(float, self.ui_right_blank.split(','))
                self.status_checker.d.click(x, y)
            else:
                self.status_checker.d.click(0.9, 0.5)
            logging.info("[NAV] 步骤2完成: 已点击右侧空白区域")

            time.sleep(5)

            # 步骤3: 点击【三】菜单按钮
            logging.info("[NAV] 步骤3: 点击【三】菜单按钮...")
            if self.status_checker.d(resourceId=self.ui_menu_button).wait(timeout=10):
                self.status_checker.d(resourceId=self.ui_menu_button).click()
                logging.info("[NAV] 步骤3完成: 已点击菜单按钮")
            else:
                logging.warning("[NAV] 步骤3跳过: 未找到菜单按钮")
                return False

            # 步骤4: 选择【4G】选项
            logging.info("[NAV] 步骤4: 选择【4G】选项...")
            if self.status_checker.d(resourceId=self.ui_option_4g).wait(timeout=10):
                self.status_checker.d(resourceId=self.ui_option_4g).click()
                logging.info("[NAV] 步骤4完成: 已选择4G选项")
                time.sleep(2)
                
                # 步骤5: 向上滚动以显示运营商切换按钮
                logging.info("[NAV] 步骤5: 向上滚动...")
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                logging.info("[NAV] 步骤5完成: 已滚动")
            else:
                logging.warning("[NAV] 步骤4跳过: 未找到4G选项")
                return False

            time.sleep(2)
            logging.info("[NAV] 导航到运营商切换页面完成")
            return True

        except Exception as e:
            logging.error(f"[NAV] 导航到运营商页面异常: {e}")
            import traceback
            logging.error(f"[NAV] 异常详情: {traceback.format_exc()}")
            return False
            
    def click_back_button(self, cycle_num):
        """
        点击两次返回按钮（下电前准备）
        """
        logging.info("[BACK] 开始执行返回操作（点击两次返回按钮）...")
        
        back_button_id = self.ui_back_button
        
        try:
            # 第一次点击
            self.status_checker.d(resourceId=back_button_id).click()
            time.sleep(2)
            
            # 第二次点击
            self.status_checker.d(resourceId=back_button_id).click()
            time.sleep(2)
            
            logging.info("[BACK] 两次返回按钮点击完成")
            return True
            
        except Exception as e:
            logging.error(f"[BACK] 点击返回按钮异常: {e}")
            return False

    def get_current_operator(self):
        """获取当前选中的运营商 - 通过检查单选框的checked属性"""
        try:
            for operator_name, operator_id in self.operator_ids.items():
                operator_elem = self.status_checker.d(resourceId=operator_id)
                if operator_elem.exists:
                    checked = operator_elem.info.get('checked', False)
                    logging.info(f"运营商: {operator_name}, checked属性: {checked}")
                    if checked:
                        logging.info(f"当前选中的运营商: {operator_name}")
                        return operator_name
            logging.warning("未找到当前选中的运营商")
            return None
        except Exception as e:
            logging.error(f"获取当前运营商异常: {e}")
            return None

    def check_operator_switch(self) -> bool:
        """检查运营商切换是否成功 - 轮询网络等级元素"""
        max_wait_time = self.freeze_timeout
        check_interval = self.wait_interval
        try:
            start_time = time.time()
            elapsed_time = 0
            while elapsed_time < max_wait_time:
                elem = self.status_checker.d(resourceId=self.ui_network_level)
                if elem.exists:
                    logging.info(f"网络等级元素已出现，等待时间: {elapsed_time}秒")
                    return True
                time.sleep(check_interval)
                elapsed_time = int(time.time() - start_time)
            logging.error(f"等待超时，{max_wait_time}秒内网络等级元素未出现")
            return False
        except Exception as e:
            logging.error(f"检查运营商切换异常: {e}")
            return False

    def switch_operator_with_screenshots(self, operator_name, cycle_num):
        """
        切换运营商 - 基于 FinalOperatorSwitch 完整逻辑：
        先检测当前checked状态 → 找到目标运营商 → click radio button → 验证网络等级元素
        """
        logging.info(f"[SWITCH] 开始切换运营商: {operator_name}")
        start_time = time.time()

        try:
            # 1. 获取当前运营商
            current_operator = self.get_current_operator()
            if current_operator is None:
                elapsed = (time.time() - start_time) * 1000
                logging.warning(f"[SWITCH] 无法获取当前运营商状态")
                self.status_checker._take_screenshot(
                    f"cycle{cycle_num}_{operator_name}_no_current",
                    subdir="operator_screenshots"
                )
                return False, elapsed, "无法获取当前运营商"

            logging.info(f"[SWITCH] 当前运营商: {current_operator} → 目标: {operator_name}")

            # 2. 查找目标运营商radio button
            if operator_name not in self.operator_ids:
                elapsed = (time.time() - start_time) * 1000
                return False, elapsed, f"未知运营商: {operator_name}"

            target_id = self.operator_ids[operator_name]
            target_elem = self.status_checker.d(resourceId=target_id)

            # 如果找不到，尝试上滑
            if not target_elem.wait(timeout=3):
                logging.info(f"[SWITCH] 未找到{operator_name}控件，执行上滑...")
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                time.sleep(1)

            # 3. 点击运营商radio button
            target_elem.click()
            logging.info(f"[SWITCH] 已点击运营商: {operator_name}")

            # 切换前截图
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}_{operator_name}_after_click",
                subdir="operator_screenshots"
            )

            # 4. 验证切换结果
            logging.info("[SWITCH] 检查运营商切换结果...")
            if self.check_operator_switch():
                elapsed = (time.time() - start_time) * 1000
                logging.info(f"[SWITCH] {operator_name}切换成功，耗时: {elapsed:.2f}ms")
                self.status_checker._take_screenshot(
                    f"cycle{cycle_num}_{operator_name}_success",
                    subdir="operator_screenshots"
                )
                return True, elapsed, "切换成功"
            else:
                elapsed = (time.time() - start_time) * 1000
                logging.error(f"[SWITCH] {operator_name}切换后网络等级元素不存在，耗时: {elapsed:.2f}ms")
                self.status_checker._take_screenshot(
                    f"cycle{cycle_num}_{operator_name}_fail",
                    subdir="operator_screenshots"
                )
                return False, elapsed, "切换后网络等级元素不存在"

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logging.error(f"[SWITCH] 切换{operator_name}异常: {e}")
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}_{operator_name}_error",
                subdir="operator_screenshots"
            )
            return False, elapsed, f"异常: {str(e)[:30]}"

    def power_rs232(self, state):
        port_name = self.connection_string
        baud_rate = 9600
        data_bits = 8
        stop_bits = 1
        parity = serial.PARITY_NONE

        if state == 'on':
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 FF F1 D1')
        else:
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 00 B1 91')

        try:
            with serial.Serial(port=port_name,
                               baudrate=baud_rate,
                               bytesize=data_bits,
                               stopbits=stop_bits,
                               parity=parity,
                               timeout=1.0) as ser:

                ser.reset_input_buffer()
                ser.reset_output_buffer()

                logging.info(f"发送报文: {message_to_send.hex(' ').upper()}")
                ser.write(message_to_send)
                logging.info("报文发送完毕，等待响应...")
                time.sleep(0.2)
                response = ser.read_all()

                if response.hex().upper() == 'FE0F000000084002':
                    return 'pass'
                else:
                    return response.hex().upper()

        except serial.SerialException as e:
            logging.info(f"串口错误: {e}")
            return 'fail'
        except Exception as e:
            logging.info(f"发生错误: {e}")
            return 'fail'

    def run_operator_switch_cycle(self, cycle_num):
        """执行一次完整的运营商检查循环（检查三个运营商控件是否存在）"""
        operators = [
            {'name': '中国联通'},
            {'name': '中国电信'},
            {'name': '中国移动'},
        ]
        
        results = []
        
        # 先导航到运营商切换页面
        logging.info("[MAIN] 开始导航到运营商切换页面...")
        nav_success = self.navigate_to_operator_page()
        if not nav_success:
            logging.warning("[MAIN] 导航失败，跳过本次运营商检查")
            #导航失败截图
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}_nav_fail", 
                subdir="operator_screenshots"
            )
            self.status_checker._restart_app()
        else:
            logging.info(f"[MAIN] 导航完成: {nav_success}")
            for operator in operators:
                operator_name = operator['name']
                logging.info(f"========== 准备检查: {operator_name} ==========")
                self.status_checker._take_screenshot(
                    f"cycle{cycle_num}_{operator_name}_after_swipe", 
                    subdir="operator_screenshots"
                )
                # 调用检查方法
                success, duration, remark = self.switch_operator_with_screenshots(
                    operator_name, cycle_num
                )
            
                results.append({
                    'cycle_num': cycle_num,
                    'operator': operator_name,
                    'success': success,
                    'duration': duration,
                    'remark': remark
                })
                if success:
                    logging.info(f"{operator_name}检查成功")
                else:
                    logging.warning(f"{operator_name}检查失败: {remark}")
                    # 强制关闭并重启应用
                    self.status_checker._restart_app()
                    
                # 检查成功截图
                self.status_checker._take_screenshot(
                    f"cycle{cycle_num}_{operator_name}_success", 
                    subdir="operator_screenshots"
                )
        return results

    def run_auto(self):
        """执行自动上下电测试循环"""
        # 开始循环
        for i in range(1, self.duration + 1):
            try:
                logging.info(f'第{i}次循环开始')
                
                # 记录开始时间
                cycle_start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 1. 检查当前设备状态
                logging.info('检查当前设备状态...')
                current_status = self.status_checker._get_current_status()
                logging.info(f'当前设备状态: {current_status}')
                
                # 2. 执行下电操作
                logging.info('执行下电操作')
                power_off_success = False
                res = self.power_rs232('off')
                if res == 'pass':
                    logging.info(f'第{i}次:电源已关闭')
                    self.state['down'] += 1
                    power_off_success = True
                else:
                    logging.info(f'第{i}次:电源关闭失败：{res}')
                    self.fail_down.append(i)
                    power_off_success = False
                    # 下电失败时截图
                    self.status_checker._take_screenshot(f'power_off_fail_{i}')

                logging.info('-' * 30)
                
                # 3. 等待下电时间
                logging.info(f'等待下电时间: {self.interval_down}秒')
                time.sleep(self.interval_down)
                
                # 4. 检查下电后设备状态（期望变为"未连接"）
                if power_off_success:
                    logging.info('检查下电后设备状态变化...')
                    status_change_success, time_elapsed = self.status_checker.check_status_change('未连接',timeout=5)
                    if status_change_success:
                        logging.info(f'设备状态成功变为"未连接"，耗时: {time_elapsed:.2f}秒')
                    else:
                        logging.warning(f'设备状态未在3分钟内变为"未连接"')
                        self.status_checker._take_screenshot(f'status_timeout_off_{i}')
                
                # 5. 执行上电操作
                logging.info('执行上电操作')
                power_on_success = False
                power_on_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                res = self.power_rs232('on')
                if res == 'pass':
                    logging.info(f'第{i}次:电源已上电')
                    self.state['up'] += 1
                    power_on_success = True
                else:
                    logging.info(f'第{i}次:电源上电失败：{res}')
                    self.fail_up.append(i)
                    power_on_success = False
                    # 上电失败时截图
                    self.status_checker._take_screenshot(f'power_on_fail_{i}')
                    continue
                    
                # 6. 检查上电后设备状态
                status_change = False
                status_change_time = 0
                wifi_check_result = None
                operator_results = None
                
                if power_on_success:
                    logging.info('检查上电后设备状态变化...')
                    status_change, status_change_time = self.status_checker.check_status_change('AirInsight Box', self.timeout_up)
                    
                    if status_change:
                        logging.info(f'设备状态成功变为"AirInsight Box"，耗时: {status_change_time:.2f}秒')

                        time.sleep(15)
                        # 执行运营商检查
                        logging.info('=' * 50)
                        logging.info('开始执行运营商控件检查')
                        logging.info('=' * 50)
                        
                        # 执行运营商检查
                        operator_results = self.run_operator_switch_cycle(i)
                        
                        logging.info('=' * 50)
                        logging.info('运营商控件检查完成')
                        logging.info('=' * 50)
                        
                        # 执行返回操作（下电前准备）
                        logging.info('=' * 50)
                        logging.info('开始执行返回操作（下电前准备）')
                        logging.info('=' * 50)
                        
                        self.click_back_button(i)
                        
                        logging.info('[MAIN] 返回操作完成，准备下电')
                        logging.info('=' * 50)
                        
                    else:
                        # 上电失败，没有运营商检查结果
                        operator_results = None
                        logging.warning(f'设备状态未在{self.timeout_up}秒内变为"AirInsight Box"')
                        self.status_checker._take_screenshot(f'status_timeout_on_{i}')
                        
                        # 上电超时后进行二次检查：检查WIFI
                        logging.info('进行重启smartgo二次检查...')
                        wifi_available = self.status_checker.check_wifi_available(timeout=120)
                        
                        if wifi_available:
                            logging.info('WIFI检查正常，设备显示异常')
                            wifi_check_result = "显示异常，WIFI正常"
                        else:
                            logging.warning('WIFI检查失败，设备WIFI异常')
                            wifi_check_result = "WIFI异常"
                        # 上电超时，本次循环失败
                        power_on_success = False
                        self.fail_up.append(i)
                        
                        if not wifi_available:
                            continue

                # 7. 记录到CSV
                notes = ""
                if not power_on_success:
                    notes += "上电失败; "
                if not power_off_success:
                    notes += "下电失败; "
                if not status_change:
                    notes += "状态变化超时; "
                
                self.status_checker.record_to_csv(
                    cycle_num=i,
                    power_on_time=power_on_time,
                    power_on_success=power_on_success,
                    status_change=status_change,
                    time_elapsed=status_change_time,
                    power_off_success=power_off_success,
                    wifi_check=wifi_check_result,
                    operator_results=operator_results,
                    notes=notes.strip()
                )
                
                logging.info('#' * 50)
                
                # 8. 如果上电成功且状态变化成功，等待设备稳定
                if power_on_success and status_change:
                    logging.info('等待设备稳定运行...')
                    time.sleep(10)
                
            except Exception as e:
                logging.error(f'第{i}次循环发生异常: {e}')
                # 异常时截图
                self.status_checker._take_screenshot(f'exception_{i}')
                # 记录异常到CSV
                self.status_checker.record_to_csv(
                    cycle_num=i,
                    power_on_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    power_on_success=False,
                    status_change=False,
                    time_elapsed=0,
                    power_off_success=False,
                    wifi_check="异常中断",
                    operator_results=None,
                    notes=f"异常: {str(e)}"
                )

        logging.info(f'******************************************************')
        logging.info(f'测试完成')
        logging.info(f'上电成功次数：{self.state["up"]}')
        logging.info(f'下电成功次数：{self.state["down"]}')
        logging.info(f'上电失败轮次：{self.fail_up}')
        logging.info(f'下电失败轮次：{self.fail_down}')
        logging.info(f'CSV记录文件: {self.status_checker.csv_filename}')


class OperatorSwitchTest:
    """AIBOX运营商切换测试类 - 保留供参考"""

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

            time.sleep(8)
            self.logger.debug("[NAV] 等待8秒完成")

            while True:


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
            if self.device(resourceId=menu_button_id).wait(timeout=10):
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




if __name__ == "__main__":
    # ===== 加载配置（单例） =====
    config = ConfigManager()
    project_name = config.get('AppConfig', 'project_name', fallback='AIBOX_model')
    root_path = config.get('AppConfig', 'root_path', fallback='./AIBOX_model')
    base_export_num = config.getint('OutputConfig', 'base_export_num', fallback=0)+1

    # ===== 初始化日志和CSV路径 =====
    csv_path, log_path = get_export_path(root_path, project_name, base_export_num)
    main_csv_path = csv_path
    setup_logging(log_path)


    # ===== 用户输入 =====
    duration = int(input("上下电次数："))  # 上下点次数
    timeout_up = int(input("上电超时时间（秒）："))   # 上电超时时间
    interval_down = int(input("下电时间（秒）："))    # 下电时间
    connection_string = input("串口号：")  # 串口
    device_serial = input("设备序列号（adb devices查看）：")  # 设备序列号

    logging.info(f"上下电次数: {duration}")
    logging.info(f"上电超时: {timeout_up}秒")
    logging.info(f"下电时间: {interval_down}秒")
    logging.info(f"串口: {connection_string}")
    logging.info(f"设备序列号: {device_serial}")

    # ===== 初始化CSV =====
    init_csv(csv_path, headers=[
        '循环次数', '上电时间戳', '上电是否成功', '设备状态变化', '状态变化耗时(秒)',
        '下电是否成功', 'WIFI检查结果', '运营商切换-联通', '运营商切换-电信',
        '运营商切换-移动', '备注'
    ])

    # ===== 运行测试 =====
    logging.info("=" * 60)
    logging.info(f"{project_name} 电源+运营商整合测试")
    logging.info("=" * 60)
    data = PowerState(timeout_up, duration, interval_down, connection_string, device_serial)
    data.run_auto()

    # ===== 汇总统计 =====
    total = data.state['up'] + len(data.fail_up)
    logging.info("=" * 60)
    logging.info("测试完成")
    logging.info(f"上电成功次数：{data.state['up']}")
    logging.info(f"下电成功次数：{data.state['down']}")
    logging.info(f"上电失败轮次：{data.fail_up}")
    logging.info(f"下电失败轮次：{data.fail_down}")
    logging.info("=" * 60)
    write_csv_summary(csv_path, total, data.state['up'], len(data.fail_up),
                      extra_rows=[['下电成功次数', data.state['down']],
                                  ['下电失败轮次', str(data.fail_up)],
                                  ['上电失败轮次', str(data.fail_down)]])
