import time
import serial  # 串口通信模块，用于RS232电源控制
import logging
import argparse
import uiautomator2 as u2
import csv
import os
import subprocess
from datetime import datetime
# 在现有的导入后面添加
import sys
from typing import Dict, List, Tuple
from functools import wraps
import threading

log_filename = time.strftime("power_%Y%m%d_%H%M%S.log")
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),  # 使用基于时间生成的文件名
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeviceStatusChecker:
    def __init__(self, device_serial):
        self.device_serial = device_serial
        self.d = None
        self.csv_filename = time.strftime("power_test_%Y%m%d_%H%M%S.csv")
        self._init_csv()
        self._connect_device()
    
    def _init_csv(self):
        """初始化CSV文件，写入表头"""
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['循环次数', '上电时间戳', '上电是否成功', '设备状态变化', '状态变化耗时(秒)', 
                         '下电是否成功', 'WIFI检查结果', '运营商切换-联通', '运营商切换-电信', 
                         '运营商切换-移动', '备注'])
    
    def _connect_device(self):
        """连接安卓设备"""
        try:
            self.d = u2.connect(self.device_serial)
            logger.info(f"成功连接到设备: {self.device_serial}")
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
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
                logger.warning(f"检查状态时出错: {e}")
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
                logger.info("检测到取消按钮，点击")
            
                self.d(text="取消").click()
            else:
                return "未连接"
        except Exception as e:
            logger.error(f"获取设备状态失败: {e}")
            return "错误"
    
    def _restart_app(self):
        """重启应用"""
        package_name = 'com.huace.groundstation'
        logger.info(f"正在强制关闭: {package_name}")
        self.d.app_stop(package_name)
        time.sleep(5)
        # 5. 重新启动软件
        # 使用包名启动应用[citation:3][citation:7]
        logger.info(f"正在重新启动: {package_name}")
        self.d.app_start(package_name)
        time.sleep(20)
    
    def _take_screenshot(self, prefix="error", subdir="./AIBOX_model_image"):
        """
        截图并保存 - 支持子目录
        功能：捕获设备当前屏幕并保存为PNG图片，支持自定义文件名前缀和子目录
        参数：
            prefix: 文件名前缀，默认为"error"
            subdir: 子目录路径，默认为"./AIBOX_model_image"
        """
        try:
            # 生成时间戳，格式为年月日_时分秒
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 组合文件名：前缀_时间戳.png
            filename = f"{prefix}_{timestamp}.png"
            # 如果指定了子目录，创建并使用
            if subdir:
                import os
                # 创建子目录（如果不存在），exist_ok=True表示目录已存在时不报错
                os.makedirs(subdir, exist_ok=True)
                # 组合完整文件路径
                filepath = os.path.join(subdir, filename)
                # 执行截图并保存到指定路径
                self.d.screenshot(filepath)
            else:
                # 未指定子目录时，直接保存到当前目录
                self.d.screenshot(filename)
            # 记录截图成功日志
            logger.info(f"截图已保存: {filename}")
        except Exception as e:
            # 记录截图失败日志
            logger.error(f"截图失败: {e}")
    
    def check_wifi_available(self,  timeout=100):
        """
        检查WIFI是否可用
        wifi_name: WIFI名称
        timeout: 超时时间（秒）
        """
        start_time = time.time()
        end_time = start_time + timeout

        package_name = 'com.huace.groundstation'
        logger.info(f"正在强制关闭: {package_name}")
        self.d.app_stop(package_name)
        time.sleep(5)
        # 5. 重新启动软件
        # 使用包名启动应用[citation:3][citation:7]
        logger.info(f"正在重新启动: {package_name}")
        self.d.app_start(package_name)

        while time.time() < end_time:
            try:
                # 使用adb命令检查WIFI
                if self.d(text="AirInsight Box").exists:
                    logger.info(f"重启后，AirInsight Box存在")
                    return True
                if self.d(text="取消").exists:
                    logger.info("检测到取消按钮，点击")
                    self.d(text="取消").click()
                time.sleep(5)  # 每5秒检查一次
                
            except subprocess.TimeoutExpired:
                logger.warning("WIFI检查超时")
            except Exception as e:
                logger.warning(f"WIFI检查出错: {e}")
                time.sleep(5)
        
        logger.warning(f"重启后，AirInsight Box在{timeout}秒内未找到")
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
            
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
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
            logger.error(f"写入CSV失败: {e}")


class PowerState:
    def __init__(self, timeout_up, duration, interval_down, connection_string, device_serial):
        self.timeout_up = timeout_up  # 上电超时时间
        self.duration = duration
        self.interval_down = interval_down
        self.connection_string = connection_string
        self.device_serial = device_serial
        self.tester = FinalOperatorSwitch(device_serial)
        self.state = {
            'up': 0,
            'down': 0,
        }

        self.fail_up = []
        self.fail_down = []
        
        # 初始化设备状态检查器
        self.status_checker = DeviceStatusChecker(device_serial)

        logger.info(f'串口为：{self.connection_string}')
        logger.info(f'设备序列号：{self.device_serial}')
        logger.info(f'上电超时时间：{self.timeout_up}秒')
        logger.info(f'下电时间为：{self.interval_down}秒')
        logger.info(f'循环次数为：{self.duration}')
        logger.info(f'******************************************************')


    def navigate_to_operator_page(self) -> bool:
        """
        导航到运营商切换页面
        操作流程：点击【手动飞行】→点击右侧空白区域→点击"三"菜单按钮→选择"4G"选项→上滑
        """
        logger.info("[NAV] 开始导航到运营商切换页面...")

        try:
            # 等待设备稳定
            # time.sleep(100)
            
            # 步骤1: 点击【手动飞行】按钮
            logger.info("[NAV] 步骤1: 点击【手动飞行】按钮...")
            if self.status_checker.d(resourceId="com.huace.groundstation:id/fly_self").wait(timeout=5):
                self.status_checker.d(resourceId="com.huace.groundstation:id/fly_self").click()
                logger.info("[NAV] 步骤1完成: 已点击手动飞行")
            else:
                logger.warning("[NAV] 步骤1跳过: 未找到手动飞行按钮")
                return False

            time.sleep(3)
            tmp = 0
            for i in range(10):
                if not self.status_checker.d(text = '载入地图中…').exists:
                    break
                else:
                    time.sleep(1)
                    tmp += 1
                    if tmp >= 10:
                        logger.warning("[NAV] 步骤1跳过: 持续载入地图中")

            time.sleep(1)
            # 步骤2: 点击右侧空白区域
            logger.info("[NAV] 步骤2: 点击右侧空白区域...")
            self.status_checker.d.click(0.9, 0.5)
            logger.info("[NAV] 步骤2完成: 已点击右侧空白区域")
            time.sleep(3)

            # 步骤3: 点击【三】菜单按钮
            logger.info("[NAV] 步骤3: 点击【三】菜单按钮...")
            self.status_checker.d(resourceId="com.huace.groundstation:id/btnMore").wait(timeout=10)
            if self.status_checker.d(resourceId="com.huace.groundstation:id/btnMore").exists:
                self.status_checker.d(resourceId="com.huace.groundstation:id/btnMore").click()
                logger.info("[NAV] 步骤3完成: 已点击菜单按钮")
            else:
                logger.warning("[NAV] 步骤3跳过: 未找到菜单按钮")
                return False

            time.sleep(1)

            # 步骤4: 选择【4G】选项
            logger.info("[NAV] 步骤4: 选择【4G】选项...")
            self.status_checker.d(resourceId="com.huace.groundstation:id/radioButton4GSetting").wait(timeout=4)
            if not self.status_checker.d(resourceId="com.huace.groundstation:id/radioButton4GSetting").exists:
                logger.info("第一次没用点击到【三】")
                if self.status_checker.d(resourceId="com.huace.groundstation:id/btnMore").exists:
                    self.status_checker.d(resourceId="com.huace.groundstation:id/btnMore").click()
                    logger.info("二次点击【三】")
                    time.sleep(2)


            self.status_checker.d(resourceId="com.huace.groundstation:id/radioButton4GSetting").wait(timeout=10)
            if self.status_checker.d(resourceId="com.huace.groundstation:id/radioButton4GSetting").exists:
                self.status_checker.d(resourceId="com.huace.groundstation:id/radioButton4GSetting").click()
                logger.info("[NAV] 步骤4完成: 已选择4G选项")
                time.sleep(2)
                
                # 步骤5: 向上滚动以显示运营商切换按钮
                logger.info("[NAV] 步骤5: 向上滚动...")
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                # 检查是否连接上

                num = 0
                for n in range(10):
                    a = self.status_checker.d(text="强").count
                    if a == 2:
                        logger.info("[NAV] 飞行器网络已连接")
                        return True

                    else:
                        time.sleep(1)
                        num += 1
                        if num >= 60:
                            logger.warning("[NAV] 飞行器网络未连接")
                            return False

            else:
                logger.warning("[NAV] 步骤4跳过: 未找到4G选项")
                return False

            time.sleep(0.5)
            logger.info("[NAV] 导航到运营商切换页面完成")
            return True

        except Exception as e:
            logger.error(f"[NAV] 导航到运营商页面异常: {e}")
            import traceback
            logger.error(f"[NAV] 异常详情: {traceback.format_exc()}")
            return False
            
    def click_back_button(self, cycle_num):
        """
        点击两次返回按钮（下电前准备）
        返回按钮ID: com.huace.groundstation:id/activity_fly_mode_main_top_sb_back
        """
        logger.info("[BACK] 开始执行返回操作（点击两次返回按钮）...")
        
        back_button_id = "com.huace.groundstation:id/activity_fly_mode_main_top_sb_back"
        
        try:
            # 第一次点击
            time.sleep(1)
            self.status_checker.d.press('back')
            # self.status_checker.d(resourceId=back_button_id).click()
            # time.sleep(2)
            #
            # # 第二次点击
            # self.status_checker.d(resourceId=back_button_id).click()
            time.sleep(1)
            
            logger.info("[BACK] 返回按钮点击完成")
            return True
            
        except Exception as e:
            logger.error(f"[BACK] 点击返回按钮异常: {e}")
            return False

    def switch_operator_with_screenshots(self, operator_name, cycle_num):
        """
        检查运营商控件是否存在，并在关键节点截图
        关键节点：
        1. 上滑操作前
        2. 上滑操作后
        3. 检查成功（找到控件）
        4. 检查失败（未找到控件）
        """
        logger.info(f"开始检查运营商: {operator_name}")
        start_time = time.time()
        
        try:
            operator_elem = self.status_checker.d(text=operator_name)
            
            # # 【关键节点1】上滑操作前截图
            # self.status_checker._take_screenshot(
            #     subdir="operator_screenshots"
            # )
            
            # 检查控件是否存在
            if operator_elem.wait(timeout=10):
                logger.info(f"{operator_name}控件存在")
            else:
                # 未找到，执行上滑
                logger.info(f"未找到{operator_name}控件，执行上滑...")
                self.status_checker.d.swipe(0.5, 0.8, 0.5, 0.2, steps=10)
                time.sleep(2)
                
                # 【关键节点2】上滑操作后截图

                # 再次检查
                if not operator_elem.wait(timeout=5):
                    elapsed = (time.time() - start_time) * 1000
                    logger.warning(f"上滑后仍未找到{operator_name}控件")
                    
                    # 【关键节点4】检查失败截图
                    self.status_checker._take_screenshot(
                        f"cycle{cycle_num}_{operator_name}_fail_not_found", 
                        subdir="operator_screenshots"
                    )
                    return False, elapsed, f"未找到{operator_name}控件"
                    #终止所有循环，停止代码
            
            # 找到控件
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"{operator_name}控件存在，检查成功")
            

            return True, elapsed, "控件存在"
                
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"检查{operator_name}异常: {e}")
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}_{operator_name}_error", 
                subdir="operator_screenshots"
            )
            return False, elapsed, f"异常: {str(e)[:30]}"

    def power_rs232(self, state):
        port_name = self.connection_string
        baud_rate = 9600  # 常见值：9600, 19200, 38400...
        data_bits = 8
        stop_bits = 1
        parity = serial.PARITY_NONE  # 常见值：PARITY_NONE, PARITY_EVEN

        if state == 'on':
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 FF F1 D1')
        else:
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 00 B1 91')

        try:
            # 创建并配置串口连接
            # 重要：timeout参数用于设置读超时，防止程序挂起
            with serial.Serial(port=port_name,
                               baudrate=baud_rate,
                               bytesize=data_bits,
                               stopbits=stop_bits,
                               parity=parity,
                               timeout=1.0) as ser:  # 1秒超时

                # logger.info(f"连接串口 {ser.name} 成功")

                # 清空输入输出缓冲区，避免旧数据干扰
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # 发送报文
                logger.info(f"发送报文: {message_to_send.hex(' ').upper()}")
                ser.write(message_to_send)
                logger.info("报文发送完毕，等待响应...")
                time.sleep(0.2)  # 给设备一点反应时间，具体取决于波特率和帧长
                response = ser.read_all()  # 读取串口缓冲区中所有的数据

                if response.hex().upper() == 'FE0F000000084002':
                    return 'pass'
                else:
                    return response.hex().upper()

        except serial.SerialException as e:
            logger.info(f"串口错误: {e}")
            return 'fail'
        except Exception as e:
            logger.info(f"发生错误: {e}")
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
        logger.info("[MAIN] 开始导航到运营商切换页面...")
        nav_success = self.navigate_to_operator_page()
        if not nav_success:
            logger.warning("[MAIN] 导航失败，跳过本次运营商检查")
            #导航失败截图
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}_nav_fail", 
                subdir="operator_screenshots"
            )
            self.status_checker._restart_app()
        else:
            logger.info(f"[MAIN] 导航完成: {nav_success}")
            self.status_checker._take_screenshot(
                f"cycle{cycle_num}__after_swipe",
                subdir="operator_screenshots"
            )
            for operator in operators:
                operator_name = operator['name']
                logger.info(f"========== 准备检查: {operator_name} ==========")

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
                    logger.info(f"{operator_name}检查成功")
                    # 开始切换4G
                    res = self.tester.run_single_cycle(self.status_checker)
                    if res:
                        logger.info("-------------------------切换4G成功-------------------------------")
                        break
                        # self.status_checker._take_screenshot(
                        #     f"成功切换{cycle_num}_{operator_name}",
                        #     subdir="operator_screenshots")
                    else:
                        logger.warning("###################切换4G失败########################")
                        self.status_checker._take_screenshot(
                            f"fail_cycle{cycle_num}_{operator_name}_fail",
                            subdir="operator_screenshots"
                        )
                        return False

                else:
                    logger.warning(f"{operator_name}检查失败: {remark}")
                    #停止循环，跳过其他运营商
                    # 强制关闭并重启应用
                    self.status_checker._restart_app()
                    break
                    
                        # 【关键节点3】检查成功截图


            self.status_checker._take_screenshot(
                f"成功切换cycle{cycle_num}_success",
                subdir="operator_screenshots"
                )
        return results

    def run_auto(self):
        # 开始循环
        for i in range(1, self.duration + 1):
            try:
                logger.info(f'第{i}次循环开始')
                
                # 记录开始时间
                cycle_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 1. 检查当前设备状态
                logger.info('检查当前设备状态...')
                current_status = self.status_checker._get_current_status()
                logger.info(f'当前设备状态: {current_status}')
                
                # 2. 执行下电操作
                logger.info('执行下电操作')
                power_off_success = False
                res = self.power_rs232('off')
                if res == 'pass':
                    logger.info(f'第{i}次:电源已关闭')
                    self.state['down'] += 1
                    power_off_success = True
                else:
                    logger.info(f'第{i}次:电源关闭失败：{res}')
                    self.fail_down.append(i)
                    power_off_success = False
                    # 下电失败时截图
                    self.status_checker._take_screenshot(f'power_off_fail_{i}')

                logger.info('-' * 30)
                
                # 3. 等待下电时间
                logger.info(f'等待下电时间: {self.interval_down}秒')
                time.sleep(self.interval_down)
                
                # 4. 检查下电后设备状态（期望变为"未连接" - AirInsight Box元素不存在）
                if power_off_success:
                    logger.info('检查下电后设备状态变化...')
                    status_change_success, time_elapsed = self.status_checker.check_status_change('未连接',timeout=5)
                    if status_change_success:
                        logger.info(f'设备状态成功变为"未连接"（AirInsight Box元素消失），耗时: {time_elapsed:.2f}秒')
                    else:
                        logger.warning(f'设备状态未在3分钟内变为"未连接"（AirInsight Box元素未消失）')
                        self.status_checker._take_screenshot(f'status_timeout_off_{i}')
                
                # 5. 执行上电操作
                logger.info('执行上电操作')
                power_on_success = False
                power_on_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                res = self.power_rs232('on')
                if res == 'pass':
                    logger.info(f'第{i}次:电源已上电')
                    self.state['up'] += 1
                    power_on_success = True
                else:
                    logger.info(f'第{i}次:电源上电失败：{res}')
                    self.fail_up.append(i)
                    power_on_success = False
                    # 上电失败时截图
                    self.status_checker._take_screenshot(f'power_on_fail_{i}')
                    continue
                # 6. 检查上电后设备状态（期望变为"AirInsight Box" - AirInsight Box元素存在）
                status_change = False
                status_change_time = 0
                wifi_check_result = None
                
                if power_on_success:
                    logger.info('检查上电后设备状态变化...')
                    status_change, status_change_time = self.status_checker.check_status_change('AirInsight Box', self.timeout_up)
                    
                    if status_change:
                        logger.info(f'设备状态成功变为"AirInsight Box"（AirInsight Box元素出现），耗时: {status_change_time:.2f}秒')
                        
                        # ========== 执行运营商检查 ==========
                        logger.info('=' * 50)
                        logger.info('开始执行运营商控件检查')
                        logger.info('=' * 50)
                        
                        # 等待设备稳定
                        time.sleep(15)
                        
                        # 执行运营商检查
                        operator_results = self.run_operator_switch_cycle(i)
                        if operator_results == False:
                            logger.warning(f'运营商检查切换失败')
                            wifi_check_result = "4G检查切换失败"
                            power_on_success = False
                            self.fail_up.append(i)
                        
                        logger.info('=' * 50)
                        logger.info('运营商控件检查完成')
                        # ========== 执行返回操作（下电前准备）==========
                        logger.info('开始执行返回操作（下电前准备）')

                        self.click_back_button(i)
                        logger.info('[MAIN] 返回操作完成，准备下电')
                        logger.info('=' * 50)
                        # =====================================================
                        
                    else:
                        # 上电失败，没有运营商检查结果
                        operator_results = None
                        logger.warning(f'设备状态未在{self.timeout_up}秒内变为"AirInsight Box"')
                        self.status_checker._take_screenshot(f'status_timeout_on_{i}')
                        
                        # 上电超时后进行二次检查：检查WIFI
                        logger.info('进行重启smartgo二次检查...')
                        wifi_available = self.status_checker.check_wifi_available(timeout=120)
                        
                        if wifi_available:
                            logger.info('检查正常，设备显示异常')
                            wifi_check_result = "显示异常，但重启连接正常"
                        else:
                            logger.warning('检查失败，设备WIFI异常')
                            wifi_check_result = "WIFI异常"
                            # while True:
                            #     print('11111111111111')
                            #     time.sleep(10)
                            # break
                        # 上电超时，本次循环失败
                        power_on_success = False
                        self.fail_up.append(i)
                        
                        if not wifi_available:
                            continue



                # #点击手动飞行→右侧空白处→“三”菜单→“4G”→上滑检查运营商切换按钮
                # logger.info("[MAIN] 开始导航到运营商切换页面...")
                # try:
                #     nav_result = self.navigate_to_operator_page()
                #     logger.info(f"[MAIN] navigate_to_operator_page()返回: {nav_result}")
                # except Exception as e:
                #     logger.error(f"[MAIN] navigate_to_operator_page()异常: {e}")
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
                
                logger.info('#' * 50)
                
                # 8. 如果上电成功且状态变化成功，等待设备稳定
                if power_on_success and status_change:
                    logger.info('等待设备稳定运行...')
                    time.sleep(8)  # 等待30秒让设备稳定运行
                
            except Exception as e:
                logger.error(f'第{i}次循环发生异常: {e}')
                # 异常时截图
                self.status_checker._take_screenshot(f'exception_{i}')
                # 记录异常到CSV
                self.status_checker.record_to_csv(
                    cycle_num=i,
                    power_on_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    power_on_success=False,
                    status_change=False,
                    time_elapsed=0,
                    power_off_success=False,
                    wifi_check="异常中断",
                    operator_results=None,
                    notes=f"异常: {str(e)}"
                )

        logger.info(f'******************************************************')
        logger.info(f'测试完成')
        logger.info(f'上电成功次数：{self.state["up"]}')
        logger.info(f'下电成功次数：{self.state["down"]}')
        logger.info(f'上电失败轮次：{self.fail_up}')
        logger.info(f'下电失败轮次：{self.fail_down}')
        logger.info(f'CSV记录文件: {self.status_checker.csv_filename}')


class FinalOperatorSwitch:
    """最终优化的运营商切换测试类"""

    # 运营商列表 - 按切换顺序排列
    OPERATORS = ['中国移动', '中国联通', '中国电信']

    # 运营商单选框ID映射
    OPERATOR_IDS = {
        '中国移动': 'com.huace.groundstation:id/rb_ai_box_operator_mobile',
        '中国联通': 'com.huace.groundstation:id/rb_ai_box_operator_unicom',
        '中国电信': 'com.huace.groundstation:id/rb_ai_box_operator_telecom'
    }

    # 网络等级元素ID - 用于判断切换是否成功
    NETWORK_LEVEL_ID = 'com.huace.groundstation:id/tv_aircraft_network_section_level'

    # 超时参数
    SWITCH_TIMEOUT = 60  # 运营商切换超时时间（秒）

    def __init__(self, device_serial=None):
        """初始化"""
        logger.info('初始化')


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
            logger.info(f"wait超时({timeout}秒)，强制返回False")
            return False
        return result[0] if result[0] is not None else False

    def check_operator_switch(self,device) -> bool:
        """检查运营商切换是否成功 - 基于原始逻辑，但改为for循环每5秒检查一次"""
        max_wait_time = 120  # 最大等待时间180秒
        check_interval = 0.3  # 每5秒检查一次

        try:
            start_time = time.time()
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                elem = device.d(resourceId=self.NETWORK_LEVEL_ID)
                elem1 = device.d(text="正在设置参数，请稍等")
                if not elem1.exists and elem.exists:
                    logger.info(f"网络等级元素已出现，等待时间: {elapsed_time}秒")
                    return True

                # logger.info(f"网络等级元素尚未出现，已等待: {elapsed_time}秒，继续等待...")
                time.sleep(check_interval)
                elapsed_time = int(time.time() - start_time)

            # 超时处理
            logger.info(f"等待超时，{max_wait_time}秒内网络等级元素未出现")
            return False

        except Exception as e:
            logger.info(f"检查运营商切换异常: {e}")
            return False

    def get_current_operator(self,device):
        """
        获取当前选中的运营商 - 通过检查单选框的checked属性

        Returns:
            str: 当前运营商名称，如果未找到返回None
        """
        # try:
        # 检查每个运营商的单选框checked属性
        for operator in self.OPERATORS:
            operator_id = self.OPERATOR_IDS[operator]
            operator_elem = device.d(resourceId=operator_id)

            if operator_elem.exists:
                # 获取checked属性
                checked = operator_elem.info.get('checked', False)
                logger.info(f"运营商: {operator}, checked属性: {checked}")

                if checked:
                    logger.info(f"当前选中的运营商: {operator}")
                    return operator

        logger.info("未找到当前选中的运营商")
        return None

        # except Exception as e:
        #     logger.info(f"获取当前运营商异常: {e}")
        #     return None

    def switch_to_next_operator(self, current_operator,device):
        """
        切换到下一个运营商 - 基于原始switch_operator()函数逻辑

        Args:
            current_operator: 当前运营商名称

        Returns:
            bool: 切换是否成功
        """
        if current_operator not in self.OPERATORS:
            logger.info(f"未知的当前运营商: {current_operator}")
            return False

        # 计算下一个运营商索引
        current_index = self.OPERATORS.index(current_operator)
        next_index = (current_index + 1) % len(self.OPERATORS)
        next_operator = self.OPERATORS[next_index]

        logger.info(f"当前运营商: {current_operator} → 切换为: {next_operator}")
        start_time = time.time()

        try:
            # 查找下一个运营商单选框控件
            next_operator_id = self.OPERATOR_IDS[next_operator]
            next_operator_elem = device.d(resourceId=next_operator_id)

            # 点击运营商单选框
            next_operator_elem.click()
            logger.info(f"已点击运营商单选框: {next_operator}")

            # 检查运营商切换结果 - 使用原始逻辑
            logger.info(f"检查运营商切换结果...")
            if self.check_operator_switch(device):
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"运营商切换成功，耗时: {elapsed:.2f}ms")
                return True
            else:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"切换后网络等级元素不存在，耗时: {elapsed:.2f}ms")
                return False

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"运营商切换异常: {e}")
            return False

    def run_single_cycle(self,device):
        """执行单次循环 - 只切换一次运营商"""
        logger.info("-" * 40)
        try:
            # 获取当前运营商状态
            current_operator = self.get_current_operator(device)
    
            if current_operator is None:
                logger.info("无法获取当前运营商状态，跳过本次循环")
                return False
    
            # 切换到下一个运营商
            success = self.switch_to_next_operator(current_operator,device)
    
            if success:
                logger.info("切换成功")
                return True
            else:
                logger.info("切换失败")
                return False
        except Exception as e:
            logger.info(f"执行单次循环异常: {e}")
            return False

    def run(self, cycle_times=1):
        """执行测试"""
        logger.info("=" * 60)
        logger.info("最终优化的运营商切换测试程序")
        logger.info("每次循环只切换一次运营商")
        logger.info("基于原始switch_operator()函数逻辑")
        logger.info(f"循环次数: {cycle_times}")
        logger.info("=" * 60)



        # 执行循环测试
        for i in range(1, cycle_times + 1):
            logger.info(f"\n第 {i}/{cycle_times} 次循环")
            self.run_single_cycle('dddddd')
            time.sleep(5)
        logger.info("\n" + "=" * 60)
        logger.info("测试完成")
        logger.info("=" * 60)

if __name__ == "__main__":

    duration = int(input("上下电次数："))  # 上下点次数
    timeout_up = int(input("上电超时时间（秒）："))   # 上电超时时间
    interval_down = int(input("下电时间（秒）："))    # 下电时间
    connection_string = input("串口号：")  # 串口
    device_serial = input("设备序列号（adb devices查看）：")  # 设备序列号

    data = PowerState(timeout_up, duration, interval_down, connection_string, device_serial)
    data.run_auto()


