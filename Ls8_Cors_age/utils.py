# -*- coding: utf-8 -*-
"""
文件名称: utils.py
功能描述: 差分龄期数据获取工具函数模块
作者: AutoGen
创建日期: 2026-03-19
运行环境: Python 3.8+
"""

import os
import sys
import time
import csv
import configparser
import datetime
import uiautomator2 as u2
from typing import Dict, List, Tuple, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        self.config = configparser.ConfigParser()
        self.config_path = config_path or self._get_default_config_path()
        self._load()
    
    def _get_default_config_path(self) -> str:
        # 获取脚本或exe所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'config.ini')
    
    def _load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        self.config.read(self.config_path, encoding='utf-8')
    
    def get_app_config(self) -> Dict[str, any]:
        return {
            'project_name': self.config.get('AppConfig', 'project_name'),
            'root_path': self.config.get('AppConfig', 'root_path'),
            'package_name': self.config.get('AppConfig', 'package_name'),
            'main_activity': self.config.get('AppConfig', 'main_activity'),
        }
    
    def get_test_params(self) -> Dict[str, any]:
        return {
            'cycle_times': self.config.getint('TestParams', 'cycle_times'),
            'base_export_num': self.config.getint('TestParams', 'base_export_num'),
            'wait_interval': self.config.getfloat('TestParams', 'wait_interval'),
            'success_threshold': self.config.getfloat('TestParams', 'success_threshold'),
            'max_wait_time': self.config.getint('TestParams', 'max_wait_time'),
        }
    
    def get_ui_elements(self) -> Dict[str, str]:
        return {
            'diff_age_id': self.config.get('UIElements', 'diff_age_id'),
            'agree_btn': self.config.get('UIElements', 'agree_btn'),
            'connect_device_btn': self.config.get('UIElements', 'connect_device_btn'),
            'wifi_list_item': self.config.get('UIElements', 'wifi_list_item'),
            'target_wifi': self.config.get('UIElements', 'target_wifi'),
            'back_btn': self.config.get('UIElements', 'back_btn'),
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


class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        self.device = None
    
    def connect(self, serial: str = None) -> u2.Device:
        if serial:
            self.device = u2.connect(serial)
        else:
            self.device = u2.connect()
        self.device.settings["operation_delay"] = (0.5, 0.5)
        return self.device
    
    def is_connected(self) -> bool:
        if not self.device:
            return False
        try:
            self.device.info
            return True
        except:
            return False
    
    def get_text(self, element_id: str) -> str:
        """获取元素的text属性"""
        try:
            element = self.device(resourceId=element_id)
            if element.exists:
                return element.get_text()
            return ""
        except Exception as e:
            return ""
    
    def close(self):
        self.device = None


class CSVReporter:
    """CSV报告生成器"""
    
    def __init__(self, csv_dir: str, csv_filename: str):
        self.csv_dir = csv_dir
        self.csv_filepath = os.path.join(csv_dir, csv_filename)
        self._ensure_dir()
        self.results = []
    
    def _ensure_dir(self):
        if not os.path.exists(self.csv_dir):
            os.makedirs(self.csv_dir)
    
    def write_header(self, headers: List[str]):
        with open(self.csv_filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def write_row(self, row_data: List[str]):
        with open(self.csv_filepath, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row_data)
        self.results.append(row_data)
    
    def write_result(self, step: str, success: bool, detail: str = ""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "成功" if success else "失败"
        self.write_row([timestamp, step, status, detail])
