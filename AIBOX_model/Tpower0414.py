# -*- coding: utf-8 -*-
"""
文件名称: Tpower0414.py
功能描述: AIBOX电源控制测试脚本
作者: AutoGen
创建日期: 2026-04-14
修改历史:
    2026-04-14 - 整理日志、CSV、截图输出规范

运行环境: Python 3.8+, uiautomator2, serial, adb
"""

import time
import serial
import logging
from logging.handlers import RotatingFileHandler
import uiautomator2 as u2
import csv
import os
import subprocess
from datetime import datetime
from typing import List

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

# 在类外部或utils中定义
class TestLogger:
    """测试日志管理器"""
    
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(self, log_dir: str, log_name: str):
        self.log_dir = log_dir
        self.log_name = log_name
        self._ensure_dir()
        self.logger = self._setup_logger()
    
    def _ensure_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_logger(self) -> logging.Logger:
        """配置日志记录器"""
        logger = logging.getLogger(self.log_name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 文件处理器 - 按大小轮转
        log_path = os.path.join(self.log_dir, f"{self.log_name}.log")
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT))
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT))
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)

class CSVReporter:
    """CSV报告管理器"""
    
    def __init__(self, csv_dir: str, filename: str):
        self.csv_dir = csv_dir
        self.filename = filename
        self.filepath = os.path.join(csv_dir, filename)
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保CSV目录存在"""
        if not os.path.exists(self.csv_dir):
            os.makedirs(self.csv_dir)
    
    def write_header(self, headers: List[str]):
        """写入CSV表头"""
        with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def write_row(self, row: List):
        """写入单行数据"""
        with open(self.filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

class DeviceStatusChecker:
    def __init__(self, device_serial):
        self.device_serial = device_serial
        self.d = None
        # CSV报告由PowerState类统一管理，此处无需重复初始化
        self._connect_device()
    
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
                if self.d(text="取消").exists:
                    self.d(text="取消").click()
                if self.d(text="等待").exists:
                    self.d(text="等待").click()
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
                self.d(text="取消").click()
                logger.info(f"点击[取消]按钮")
            else:
                return "未连接"
        except Exception as e:
            logger.error(f"获取设备状态失败: {e}")
            return "错误"
    
    def _take_screenshot(self, prefix="error", subdir="screenshots"):
        """
        截图并保存 - 支持子目录
        
        Args:
            prefix: 文件名前缀
            subdir: 子目录名称
        """
        try:
            # 创建子目录
            screenshot_dir = os.path.join("./output", subdir)
            os.makedirs(screenshot_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)
            
            self.d.screenshot(filepath)
            logger.info(f"截图已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def check_wifi_available(self,  timeout=100):
        """
        检查WIFI是否可用
        wifi_name: WIFI名称
        timeout: 超时时间（秒）
        """
        start_time = time.time()
        end_time = start_time + timeout
        package_name = 'com.huace.groundstation'
        print(f"正在强制关闭: {package_name}")
        self.d.app_stop(package_name)
        time.sleep(5)
        # 5. 重新启动软件
        # 使用包名启动应用[citation:3][citation:7]
        print(f"正在重新启动: {package_name}")
        self.d.app_start(package_name)
        while time.time() < end_time:
            try:
                # 使用adb命令检查WIFI
                print("操作完成。")
                if self.d(text="AirInsight Box").exists:
                    logger.info(f"重启后，AirInsight Box存在")
                    return True
                if self.d(text="取消").exists:
                    self.d(text="取消").click()
                time.sleep(5)  # 每5秒检查一次
                
            except subprocess.TimeoutExpired:
                logger.warning("WIFI检查超时")
            except Exception as e:
                logger.warning(f"WIFI检查出错: {e}")
                time.sleep(5)
        
        logger.warning(f"重启后，AirInsight Box在{timeout}秒内未找到")
        return False
    
class PowerState:
    def __init__(self, timeout_up, duration, interval_down, connection_string, device_serial):
        self.timeout_up = timeout_up  # 上电超时时间
        self.duration = duration
        self.interval_down = interval_down
        self.connection_string = connection_string
        self.device_serial = device_serial
        self.d = None
        
        self.output_dir = "./output"
        self.log_dir = os.path.join(self.output_dir, "logs")
        self.csv_dir = os.path.join(self.output_dir, "csv")
        self.screenshot_dir = os.path.join(self.output_dir, "screenshots")

        # 确保目录存在
        for dir_path in [self.log_dir, self.csv_dir, self.screenshot_dir]:
            os.makedirs(dir_path, exist_ok=True)

        # 初始化日志
        log_name = f"power_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger = TestLogger(self.log_dir, log_name)

        # 初始化CSV报告器
        #self.csv_reporter = CSVReporter(self.csv_dir, self.csv_filename)
        # 初始化CSV
        csv_name = f"power_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.csv_reporter = CSVReporter(self.csv_dir, csv_name)
        self.csv_reporter.write_header(['循环次数', '上电时间戳', '上电是否成功', '设备状态变化', '状态变化耗时(秒)', '下电是否成功', 'WIFI检查结果', '备注'])

        self.state = {
            'up': 0,
            'down': 0,
        }

        self.fail_up = []
        self.fail_down = []
        
        # 初始化设备状态检查器
        self.status_checker = DeviceStatusChecker(device_serial)

        self.logger.info(f'串口为：{self.connection_string}')
        self.logger.info(f'设备序列号：{self.device_serial}')
        self.logger.info(f'上电超时时间：{self.timeout_up}秒')
        self.logger.info(f'下电时间为：{self.interval_down}秒')
        self.logger.info(f'循环次数为：{self.duration}')
        self.logger.info(f'******************************************************')

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
            self.logger.info(f"串口错误: {e}")
            return 'fail'
        except Exception as e:
            self.logger.info(f"发生错误: {e}")
            return 'fail'


    def run_auto(self):
        # 开始循环
        for i in range(1, self.duration + 1):
            try:
                self.logger.info("=" * 15)
                self.logger.info(f'第{i}次循环开始')
                self.logger.info("=" * 15)
                # 记录开始时间
                cycle_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.logger.info(f'第{i}次循环开始时间: {cycle_start_time}')
                
                # 1. 检查当前设备状态
                self.logger.info('检查当前设备状态...')
                current_status = self.status_checker._get_current_status()
                self.logger.info(f'当前设备状态: {current_status}')
                
                # 2. 执行下电操作
                self.logger.info('执行下电操作')
                power_off_success = False
                res = self.power_rs232('off')
                if res == 'pass':
                    self.logger.info(f'第{i}次:电源已关闭')
                    self.state['down'] += 1
                    power_off_success = True
                else:
                    self.logger.info(f'第{i}次:电源关闭失败：{res}')
                    self.fail_down.append(i)
                    power_off_success = False
                    # 下电失败时截图
                    self.status_checker._take_screenshot(f'power_off_fail_{i}')

                self.logger.info('-' * 30)
                
                # 3. 等待下电时间
                self.logger.info(f'等待下电时间: {self.interval_down}秒')
                time.sleep(self.interval_down)
                
                # 4. 检查下电后设备状态（期望变为"未连接" - AirInsight Box元素不存在）
                if power_off_success:
                    self.logger.info('检查下电后设备状态变化...')
                    status_change_success, time_elapsed = self.status_checker.check_status_change('未连接',timeout=5)
                    if status_change_success:
                        self.logger.info(f'设备状态成功变为"未连接"（AirInsight Box元素消失），耗时: {time_elapsed:.2f}秒')
                    else:
                        self.logger.warning(f'设备状态未在3分钟内变为"未连接"（AirInsight Box元素未消失）') 
                        self.status_checker._take_screenshot(f'status_timeout_off_{i}')
                
                # 5. 执行上电操作
                self.logger.info('执行上电操作')
                power_on_success = False
                power_on_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                res = self.power_rs232('on')
                if res == 'pass':
                    self.logger.info(f'第{i}次:电源已上电')
                    self.state['up'] += 1
                    power_on_success = True
                else:
                    self.logger.info(f'第{i}次:电源上电失败：{res}')
                    self.fail_up.append(i)
                    power_on_success = False
                    # 上电失败时截图
                    self.status_checker._take_screenshot(f'power_on_fail_{i}')
                # 6. 检查上电后设备状态（期望变为"AirInsight Box" - AirInsight Box元素存在）
                status_change = False
                status_change_time = 0
                wifi_check_result = None
                
                if power_on_success:
                    self.logger.info(f'第{i}次:上电成功时间: {power_on_time}')
                    self.logger.info('检查上电后设备状态变化...')
                    # 点击坐标 {"x":0,"y":0,"width":1920,"height":98}
                    self.status_checker.d.click(0.5, 0.051)
                    status_change, status_change_time = self.status_checker.check_status_change('AirInsight Box', self.timeout_up)
                    
                    if status_change:
                        self.logger.info(f'设备状态成功变为"AirInsight Box"（AirInsight Box元素出现），耗时: {status_change_time:.2f}秒')
                    else:
                        self.logger.warning(f'设备状态未在{self.timeout_up}秒内变为"AirInsight Box"（AirInsight Box元素未出现）')
                        self.status_checker._take_screenshot(f'status_timeout_on_{i}')
          
                        # 上电超时后进行二次检查：检查WIFI
                        self.logger.info('进行重启smartgo二次检查...')
                        wifi_available = self.status_checker.check_wifi_available(timeout=100)
                        
                        if wifi_available:
                            self.logger.info('WIFI检查正常，设备显示异常')
                            wifi_check_result = "显示异常，WIFI正常"
                        else:
                            self.logger.warning('WIFI检查失败，设备WIFI异常')
                            wifi_check_result = "WIFI异常"
                            self.logger.info('=============等待10秒，确保设备稳定===========================')
                            time.sleep(10)
                            
                        # 上电超时，本次循环失败
                        power_on_success = False
                        self.fail_up.append(i)
                
                # 7. 记录到CSV
                notes = ""
                if not power_on_success:
                    notes += "上电失败; "
                if not power_off_success:
                    notes += "下电失败; "
                if not status_change:
                    notes += "状态变化超时; "
                
                self.csv_reporter.write_row([
                    i,
                    power_on_time,
                    power_on_success,
                    status_change,
                    round(status_change_time, 2) if status_change_time else '',
                    power_off_success,
                    wifi_check_result if wifi_check_result is not None else '',
                    notes.strip()
                ])
                
                self.logger.info('#' * 50)

                # 8. 如果上电成功且状态变化成功，等待设备稳定
                if power_on_success and status_change:
                    self.logger.info('等待设备稳定运行...')
                    time.sleep(35)  # 等待20秒让设备稳定运行
                
            except Exception as e:
                self.logger.error(f'第{i}次循环发生异常: {e}')
                # 异常时截图
                self.status_checker._take_screenshot(f'exception_{i}')
                # 记录异常到CSV
                self.csv_reporter.write_row([
                    i,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    False,
                    False,
                    0,
                    False,
                    "异常中断",
                    f"异常: {str(e)}"
                ])

        self.logger.info(f'******************************************************')
        self.logger.info(f'测试完成')
        self.logger.info(f'上电成功次数：{self.state["up"]}')
        self.logger.info(f'下电成功次数：{self.state["down"]}')
        self.logger.info(f'上电失败轮次：{self.fail_up}')
        self.logger.info(f'下电失败轮次：{self.fail_down}')
        self.logger.info(f'CSV记录文件: {self.csv_reporter.filepath}')


if __name__ == "__main__":

    duration = int(input("上下电次数："))  # 上下点次数
    timeout_up = int(input("上电超时时间（秒）："))   # 上电超时时间
    interval_down = int(input("下电时间（秒）："))    #
    connection_string = input("串口号：")  # 串口
    device_serial = input("设备序列号（adb devices查看）：")  # 设备序列号

    data = PowerState(timeout_up, duration, interval_down, connection_string, device_serial)
    data.run_auto()


