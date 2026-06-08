# -*- coding: utf-8 -*-
"""
文件名称: utils.py
功能描述: AIBOX运营商切换测试工具函数模块
作者: AutoGen
创建日期: 2026-04-01
运行环境: Python 3.8+, uiautomator2, adb
"""

import os
import re
import time
import csv
import subprocess
import configparser
import datetime
from typing import Dict, List, Tuple, Optional


class ConfigManager:
    """配置管理器"""

    _instance = None

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        self._initialized = True

        self.config = configparser.ConfigParser()
        if config_path:
            self.config_path = config_path
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(current_dir, 'config.ini')

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        self.config.read(self.config_path, encoding='utf-8')

    def get(self, section: str, key: str, fallback=None):
        """获取字符串配置"""
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback=0):
        """获取整数配置"""
        return self.config.getint(section, key, fallback=fallback)

    def getfloat(self, section: str, key: str, fallback=0.0):
        """获取浮点数配置"""
        return self.config.getfloat(section, key, fallback=fallback)

    def getboolean(self, section: str, key: str, fallback=False):
        """获取布尔配置"""
        return self.config.getboolean(section, key, fallback=fallback)

    def get_app_config(self) -> Dict[str, any]:
        """获取应用配置"""
        return {
            'project_name': self.get('AppConfig', 'project_name'),
            'root_path': self.get('AppConfig', 'root_path'),
            'app_package': self.get('AppConfig', 'app_package'),
        }

    def get_device_config(self) -> Dict[str, any]:
        """获取设备配置"""
        return {
            'device_serial': self.get('DeviceConfig', 'device_serial'),
            'connect_timeout': self.getint('DeviceConfig', 'connect_timeout'),
        }

    def get_test_params(self) -> Dict[str, any]:
        """获取测试参数"""
        return {
            'cycle_times': self.getint('TestParams', 'cycle_times'),
            'wait_interval': self.getint('TestParams', 'wait_interval'),
            'operator_switch_timeout': self.getint('TestParams', 'operator_switch_timeout'),
            'freeze_timeout': self.getint('TestParams', 'freeze_timeout'),
            'enable_app_restart': self.getboolean('TestParams', 'enable_app_restart'),
        }

    def get_ui_elements(self) -> Dict[str, str]:
        """获取UI元素配置"""
        return {
            'manual_flight': self.get('UIElements', 'manual_flight'),
            'right_blank_area': self.get('UIElements', 'right_blank_area'),
            'menu_button': self.get('UIElements', 'menu_button'),
            'option_4g': self.get('UIElements', 'option_4g'),
            'not_update': self.get('UIElements', 'not_update'),
            'manual_control': self.get('UIElements', 'manual_control'),
            'operator_unicom': self.get('UIElements', 'operator_unicom'),
            'operator_telecom': self.get('UIElements', 'operator_telecom'),
            'operator_mobile': self.get('UIElements', 'operator_mobile'),
            'loading_dialog': self.get('UIElements', 'loading_dialog'),
            'network_level': self.get('UIElements', 'network_level'),
        }

    def get_output_config(self) -> Dict[str, any]:
        """获取输出配置"""
        return {
            'base_export_num': self.getint('OutputConfig', 'base_export_num'),
            'screenshot_mode': self.get('OutputConfig', 'screenshot_mode', fallback='reduced'),
        }


class LogManager:
    """日志管理器"""

    def __init__(self, log_dir: str, log_filename: str):
        self.log_dir = log_dir
        self.log_filepath = os.path.join(log_dir, log_filename)
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        with open(self.log_filepath, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        print(log_entry)

    def info(self, message: str):
        self.log(message, "INFO")

    def error(self, message: str):
        self.log(message, "ERROR")

    def warning(self, message: str):
        self.log(message, "WARNING")

    def debug(self, message: str):
        self.log(message, "DEBUG")


class CSVReporter:
    """CSV报告生成器"""

    def __init__(self, csv_dir: str, csv_filename: str):
        self.csv_dir = csv_dir
        self.csv_filepath = os.path.join(csv_dir, csv_filename)
        self._ensure_dir()
        self._init_file()

    def _ensure_dir(self):
        if not os.path.exists(self.csv_dir):
            os.makedirs(self.csv_dir)

    def _init_file(self):
        if not os.path.exists(self.csv_filepath):
            with open(self.csv_filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '时间', '循环序号', '运营商', '操作', '结果',
                    '耗时(ms)', '备注'
                ])

    def write_row(self, row_data: List[str]):
        """写入数据行"""
        with open(self.csv_filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)

    def write_result(self, cycle_num: int, operator: str, operation: str,
                     result: str, duration: float, remark: str = ''):
        """写入测试结果"""
        self.write_row([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(cycle_num),
            operator,
            operation,
            result,
            f"{duration:.2f}",
            remark
        ])

    def write_summary(self, summary_data: Dict):
        """写入汇总数据"""
        with open(self.csv_filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([])
            writer.writerow(['===== 汇总统计 ====='])
            for key, value in summary_data.items():
                writer.writerow([key, value])


class ADBChecker:
    """ADB设备检查器"""

    @staticmethod
    def check() -> Tuple[bool, List[str]]:
        """检查ADB设备连接"""
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = result.stdout.strip().split('\n')
            devices = [
                line.split('\t')[0]
                for line in lines[1:]
                if line.strip() and '\tdevice' in line
            ]
            return len(devices) > 0, devices
        except FileNotFoundError:
            return False, ["ADB未找到"]
        except Exception as e:
            return False, [str(e)]

    @staticmethod
    def check_device_by_serial(serial: str) -> bool:
        """检查指定序列号设备是否连接"""
        connected, devices = ADBChecker.check()
        return serial in devices if connected else False


class DeviceController:
    """设备控制器"""

    def __init__(self, device=None):
        self.device = device
        self.app_package = None

    def set_app_package(self, package: str):
        """设置应用包名"""
        self.app_package = package

    def start_app(self, package: str = None):
        """启动应用"""
        pkg = package or self.app_package
        if not pkg or not self.device:
            return False
        try:
            self.device.app_start(pkg)
            return True
        except Exception:
            return False

    def stop_app(self, package: str = None):
        """停止应用（杀后台）"""
        pkg = package or self.app_package
        if not pkg or not self.device:
            return False
        try:
            self.device.app_stop(pkg)
            return True
        except Exception:
            return False

    def restart_app(self, package: str = None):
        """重启应用"""
        pkg = package or self.app_package
        if not pkg or not self.device:
            return False
        self.stop_app(pkg)
        time.sleep(1)
        return self.start_app(pkg)

    def take_screenshot(self, filepath: str) -> bool:
        """截图"""
        if not self.device:
            return False
        try:
            self.device.screenshot(filepath)
            return True
        except Exception:
            return False

    def click_by_coordinates(self, x: float, y: float) -> bool:
        """根据坐标点击（支持比例坐标）"""
        if not self.device:
            return False
        try:
            self.device.click(x, y)
            return True
        except Exception:
            return False

    def get_hierarchy(self) -> str:
        """获取当前界面XML层次结构"""
        if not self.device:
            return ""
        try:
            return self.device.dump_hierarchy()
        except Exception:
            return ""
