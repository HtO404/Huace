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
        self._connect_device()

    
    def _connect_device(self):
        """连接安卓设备"""
        try:
            self.d = u2.connect(self.device_serial)
            logger.info(f"成功连接到设备: {self.device_serial}")
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            raise

    def _get_current_status(self):
        """获取当前设备状态"""
        if self.d(text="取消").exists:
            self.d(text="取消").click()
        try:
            # 检查是否存在"AirInsight Box"文本元素
            if self.d(text="AirInsight Box").exists:
                return "AirInsight Box"
            elif self.d(text="取消").exists:
                logger.info("检测到取消按钮，点击")
                self.d(text="取消").click()
            # elif self.d(text="正在请求参数，请稍后").exists:
            #     logger.info("检测到取消按钮，点击")
            #     self.d(text="取消").click()
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
        time.sleep(120)
    
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




class PowerState:
    def __init__(self, duration, interval_down, connection_string, device_serial):
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
        
        # 初始化设备状态检查器
        self.status_checker = DeviceStatusChecker(device_serial)

        logger.info(f'串口为：{self.connection_string}')
        logger.info(f'设备序列号：{self.device_serial}')
        logger.info(f'下电时间为：{self.interval_down}秒')
        logger.info(f'循环次数为：{self.duration}')
        logger.info(f'******************************************************')


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



    def _ping_device(self):
        """ping 192.168.0.100 并输出前10条记录"""
        try:
            logger.info('========== 开始ping 192.168.0.100 ==========')
            result = subprocess.run(
                ['ping', '192.168.0.100', '-n', '10'],
                capture_output=True,
                text=True,
                timeout=15
            )
            lines = result.stdout.split('\n')
            for line in lines[:10]:
                logger.info(f'[PING] {line.strip()}')
            logger.info('========== ping结束 ==========')
        except subprocess.TimeoutExpired:
            logger.warning('[PING] ping超时')
        except Exception as e:
            logger.warning(f'[PING] ping执行异常: {e}')

    def run_auto(self):
        """完整流程：退主页→杀进程→ping→下电→等待→上电→等5min→重启地面站→导航航线→检测连接→超时重试"""
        for i in range(1, self.duration + 1):
            try:
                logger.info(f'========== 第{i}次循环开始 ==========')

                # 0. 退回主页面，杀死地面站后台进程
                self._go_home_and_kill_app()

                # 0.5 ping设备
                # self._ping_device()

                # 1. 执行下电操作
                logger.info('执行下电操作')
                res = self.power_rs232('off')
                if res == 'pass':
                    logger.info(f'第{i}次:电源已关闭')
                    self.state['down'] += 1
                else:
                    logger.info(f'第{i}次:电源关闭失败：{res}')
                    self.fail_down.append(i)
                    self.status_checker._take_screenshot(f'power_off_fail_{i}')

                logger.info('-' * 30)

                # 2. 等待下电时间
                logger.info(f'等待下电时间: {self.interval_down}秒')
                time.sleep(self.interval_down)

                # 3. 执行上电操作
                logger.info('执行上电操作')
                res = self.power_rs232('on')
                if res == 'pass':
                    logger.info(f'第{i}次:电源已上电')
                    self.state['up'] += 1
                else:
                    logger.info(f'第{i}次:电源上电失败：{res}')
                    self.fail_up.append(i)
                    self.status_checker._take_screenshot(f'power_on_fail_{i}')
                    continue

                # 4. 等待5分钟设备启动
                logger.info('等待5分钟设备启动...')
                time.sleep(240)

                # 5. 重启地面站并导航到航线1
                self._restart_groundstation_and_navigate()

                # 6. 检查界面连接状态（5分钟超时）
                logger.info('检查界面连接状态')
                start_time = time.time()
                timeout = 180
                connected = False

                while time.time() - start_time < timeout:
                    try:
                        if self.status_checker.d(text="取消").exists:
                            self.status_checker.d(text="取消").click()
                            logger.info('**********点击取消**********')
                        if self.status_checker.d(text="等待").exists:
                            self.status_checker.d(text="等待").click()
                            logger.info('************点击等待*********')

                        if self.status_checker.d(text="SmartGo没有响应").exists:
                            logger.info('**********SmartGo没有响应*********')
                            self.status_checker._take_screenshot(f'SmartGo_fail_{i}')
                            self.status_checker._restart_app()
                            self._restart_groundstation_and_navigate()
                            continue

                        connect_elements = self.status_checker.d(textMatches=".*速度.*").count
                        if connect_elements >= 2:
                            connecting_element = self.status_checker.d(textMatches=".*正在连接.*").exists
                            if not connecting_element and self.status_checker.d(textMatches=".*192.168.0.100:554.*").exists:
                                connected = True
                                logger.info(f'第{i}次:界面连接检查通过')
                                self.status_checker._take_screenshot(f'success_{i}')
                                time.sleep(10)
                                break
                        time.sleep(5)
                    except Exception as e:
                        logger.warning(f'检查连接状态时出错: {e}')
                        time.sleep(5)

                if not connected:
                    logger.error(f'----------------第{i}次:界面连接检查超时（5分钟）-------------')
                    self.status_checker._take_screenshot(f'connection_check_fail_{i}')

                    # 超时重试：返回×2 → 截图 → 航线规划 → 航线1 → 加载 → 截图 → 重新检测
                    logger.info('========== 超时后执行重试流程 ==========')
                    try:
                        self.status_checker.d.press('back')
                        time.sleep(4)
                        self.status_checker.d.press('back')
                        time.sleep(10)
                        if self.status_checker.d(text="取消").exists:
                            self.status_checker.d(text="取消").click()
                        self.status_checker._take_screenshot(f'retry_back_{i}')

                        fly_plan = self.status_checker.d(resourceId="com.huace.groundstation:id/fly_plan")
                        if fly_plan.wait(timeout=3.0):
                            fly_plan.click()
                            logger.info('重试:点击航线规划按钮')
                            time.sleep(2)

                        route1 = self.status_checker.d(resourceId="com.huace.groundstation:id/imgNotInManagement")
                        if route1.wait(timeout=3.0):
                            route1.click()
                            logger.info('重试:点击航线1')

                        logger.info('重试:等待12秒加载...')
                        time.sleep(12)
                        self.status_checker._take_screenshot(f'retry_loaded_{i}')

                        # 重新检测
                        logger.info('重试:开始重新检测界面连接状态')
                        retry_start = time.time()
                        retry_timeout = 60
                        retry_connected = False

                        while time.time() - retry_start < retry_timeout:
                            try:
                                if self.status_checker.d(text="取消").exists:
                                    self.status_checker.d(text="取消").click()
                                if self.status_checker.d(text="等待").exists:
                                    self.status_checker.d(text="等待").click()

                                connect_elements = self.status_checker.d(textMatches=".*速度.*").count
                                if connect_elements >= 2:
                                    connecting_element = self.status_checker.d(textMatches=".*正在连接.*").exists
                                    if not connecting_element and self.status_checker.d(textMatches=".*192.168.0.100:554.*").exists:
                                        retry_connected = True
                                        logger.info(f'第{i}次:重试后界面连接检查通过')
                                        self.status_checker._take_screenshot(f'retry_success_{i}')
                                        time.sleep(10)
                                        break
                                time.sleep(5)
                            except Exception as e:
                                logger.warning(f'重试检查连接状态时出错: {e}')
                                time.sleep(5)

                        if retry_connected:
                            connected = True
                            logger.info(f'第{i}次:重试流程最终成功')
                        else:
                            logger.error(f'----------------第{i}次:重试后界面连接检查超时-------------')
                            self.status_checker._take_screenshot(f'retry_fail_{i}')

                    except Exception as retry_e:
                        logger.error(f'重试流程异常: {retry_e}')
                        self.status_checker._take_screenshot(f'retry_exception_{i}')


            except Exception as e:
                logger.error(f'第{i}次循环发生异常: {e}')
                self.status_checker._take_screenshot(f'exception_{i}')


        logger.info(f'******************************************************')
        logger.info(f'测试完成')


    # ====================== 新增流程：退主页 → 杀进程 → 下电 → 上电 → 重启地面站 → 导航航线 ======================

    def _go_home_and_kill_app(self):
        """退回主页面，杀死地面站后台进程"""
        try:
            self.status_checker.d.press("home")
            time.sleep(2)
            package_name = 'com.huace.groundstation'
            self.status_checker.d.app_stop(package_name)
            time.sleep(2)
            logger.info("已退回主页面并杀死地面站后台进程")
        except Exception as e:
            logger.error(f"退回主页/杀进程失败: {e}")

    def _restart_groundstation_and_navigate(self):
        """重启地面站并导航到航线1"""
        try:
            package_name = 'com.huace.groundstation'
            logger.info(f"正在启动地面站: {package_name}")
            self.status_checker.d.app_start(package_name)
            time.sleep(20)

            if self.status_checker.d(text="取消").exists:
                self.status_checker.d(text="取消").click()
                time.sleep(1)
            if self.status_checker.d(text="等待").exists:
                self.status_checker.d(text="等待").click()
                time.sleep(1)

            fly_plan = self.status_checker.d(resourceId="com.huace.groundstation:id/fly_plan")
            if fly_plan.wait(timeout=5.0):
                fly_plan.click()
                logger.info('点击航线规划按钮')
                time.sleep(2)
            else:
                logger.warning('未找到航线规划按钮')

            route1 = self.status_checker.d(resourceId="com.huace.groundstation:id/imgNotInManagement")
            if route1.wait(timeout=5.0):
                route1.click()
                logger.info('点击航线1')
                time.sleep(8)
            else:
                logger.warning('未找到航线1按钮')

            logger.info("地面站已重启并进入航线1界面")
        except Exception as e:
            logger.error(f"重启地面站/导航失败: {e}")


if __name__ == "__main__":

    duration = int(input("上下电次数："))
    interval_down = int(input("下电时间（秒）："))
    connection_string = input("串口号：")
    device_serial = input("设备序列号（adb devices查看）：")

    data = PowerState(duration, interval_down, connection_string, device_serial)
    data.run_auto()


