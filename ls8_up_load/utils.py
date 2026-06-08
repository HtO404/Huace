# -*- coding: utf-8 -*-
"""
文件名称: utils.py
功能描述: FTP上传/下载测试工具函数模块
作者: AutoGen
创建日期: 2026-03-13
运行环境: Python 3.8+
"""

import os
import sys
import time
import ftplib
import csv
import configparser
import datetime
import hashlib
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
    
    def get_ftp_config(self) -> Dict[str, any]:
        return {
            'server': self.config.get('FtpConfig', 'ftp_server'),
            'port': self.config.getint('FtpConfig', 'ftp_port'),
            'username': self.config.get('FtpConfig', 'ftp_username'),
            'password': self.config.get('FtpConfig', 'ftp_password'),
            'passive_mode': self.config.getboolean('FtpConfig', 'passive_mode'),
        }
    
    def get_test_params(self) -> Dict[str, any]:
        return {
            'test_type': self.config.getint('TestParams', 'test_type'),
            'cycle_times': self.config.getint('TestParams', 'cycle_times'),
            'file_size_mb': self.config.getint('TestParams', 'file_size_mb'),
            'test_file_path': self.config.get('TestParams', 'test_file_path'),
            'buffer_size': self.config.getint('TestParams', 'buffer_size'),
            'test_interval': self.config.getint('TestParams', 'test_interval'),
            'connect_timeout': self.config.getint('TestParams', 'connect_timeout'),
            'timeout': self.config.getint('TestParams', 'timeout'),
            'success_threshold': self.config.getfloat('TestParams', 'success_threshold'),
        }
    
    def get_output_config(self) -> Dict[str, any]:
        return {
            'project_name': self.config.get('OutputConfig', 'project_name'),
            'root_path': self.config.get('OutputConfig', 'root_path'),
            'base_export_num': self.config.getint('OutputConfig', 'base_export_num'),
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


class FileManager:
    """文件管理器 - 管理测试文件"""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._ensure_dir()
    
    def _ensure_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def get_file_size(self, filepath: str) -> int:
        """获取文件大小(字节)"""
        if not os.path.exists(filepath):
            return 0
        return os.path.getsize(filepath)
    
    def calculate_file_md5(self, filepath: str) -> str:
        """计算文件MD5值"""
        hash_md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def delete_file(self, filepath: str):
        """删除文件"""
        if os.path.exists(filepath):
            os.remove(filepath)


class FTPClient:
    """FTP客户端封装"""
    
    def __init__(self, server: str, port: int, username: str, password: str, 
                 passive_mode: bool = False, timeout: int = 60):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.passive_mode = passive_mode
        self.timeout = timeout
        self.ftp = None
        self._connect()
    
    def _connect(self):
        """建立FTP连接"""
        self.ftp = ftplib.FTP()
        self.ftp.connect(self.server, self.port, timeout=self.timeout)
        self.ftp.login(self.username, self.password)
        self.ftp.set_pasv(self.passive_mode)
    
    def upload_file(self, local_path: str, remote_path: str, 
                    buffer_size: int = 1048576) -> Tuple[bool, str, float]:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            buffer_size: 缓冲区大小
            
        Returns:
            (是否成功, 错误信息, 耗时秒)
        """
        start_time = time.time()
        
        try:
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_path}', f, blocksize=buffer_size)
            
            elapsed_time = time.time() - start_time
            return True, "", elapsed_time
            
        except ftplib.error_temp as e:
            return False, f"FTP临时错误: {e}", time.time() - start_time
        except ftplib.error_perm as e:
            return False, f"FTP权限错误: {e}", time.time() - start_time
        except ftplib.error_proto as e:
            return False, f"FTP协议错误: {e}", time.time() - start_time
        except TimeoutError as e:
            return False, f"上传超时: {e}", time.time() - start_time
        except Exception as e:
            return False, f"上传异常: {e}", time.time() - start_time
    
    def download_file(self, remote_path: str, local_path: str, 
                      buffer_size: int = 1048576) -> Tuple[bool, str, float]:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            buffer_size: 缓冲区大小
            
        Returns:
            (是否成功, 错误信息, 耗时秒)
        """
        start_time = time.time()
        
        try:
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write, blocksize=buffer_size)
            
            elapsed_time = time.time() - start_time
            return True, "", elapsed_time
            
        except ftplib.error_temp as e:
            return False, f"FTP临时错误: {e}", time.time() - start_time
        except ftplib.error_perm as e:
            return False, f"FTP权限错误: {e}", time.time() - start_time
        except ftplib.error_proto as e:
            return False, f"FTP协议错误: {e}", time.time() - start_time
        except TimeoutError as e:
            return False, f"下载超时: {e}", time.time() - start_time
        except Exception as e:
            return False, f"下载异常: {e}", time.time() - start_time
    
    def delete_file(self, remote_path: str) -> Tuple[bool, str]:
        """删除远程文件"""
        try:
            self.ftp.delete(remote_path)
            return True, ""
        except ftplib.error_perm as e:
            return False, f"删除失败: {e}"
        except Exception as e:
            return False, f"删除异常: {e}"
    
    def file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        try:
            self.ftp.size(remote_path)
            return True
        except:
            return False
    
    def close(self):
        """关闭FTP连接"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                self.ftp.close()
            self.ftp = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class CSVReporter:
    """CSV报告生成器"""
    
    def __init__(self, output_dir: str, filename: str):
        self.output_dir = output_dir
        self.filepath = os.path.join(output_dir, filename)
        self._ensure_dir()
        self._init_file()
    
    def _ensure_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def _init_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['轮次', '开始时间', '结束时间', '耗时(秒)', '传输速率(MB/s)', '状态', '备注'])
    
    def write_result(self, cycle: int, start_time: str, end_time: str, 
                    duration: float, speed: float, status: str, remark: str = ''):
        """写入测试结果"""
        with open(self.filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([cycle, start_time, end_time, f"{duration:.2f}", 
                           f"{speed:.2f}" if speed > 0 else "0.00", status, remark])
    
    def write_summary(self, summary_data: Dict):
        """写入汇总数据"""
        with open(self.filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([])
            writer.writerow(['===== 汇总统计 ====='])
            for key, value in summary_data.items():
                writer.writerow([key, value])


class StatisticsCalculator:
    """统计计算器"""
    
    @staticmethod
    def calculate(speeds: List[float]) -> Dict[str, float]:
        if not speeds:
            return {
                'count': 0,
                'average': 0.0,
                'std_dev': 0.0,
                'max': 0.0,
                'min': 0.0,
                'fluctuation_pct': 0.0,
            }
        
        n = len(speeds)
        average = sum(speeds) / n
        
        variance = sum((x - average) ** 2 for x in speeds) / n
        std_dev = variance ** 0.5
        
        max_speed = max(speeds)
        min_speed = min(speeds)
        
        fluctuation_pct = ((max_speed - min_speed) / average * 100) if average > 0 else 0.0
        
        return {
            'count': n,
            'average': average,
            'std_dev': std_dev,
            'max': max_speed,
            'min': min_speed,
            'fluctuation_pct': fluctuation_pct,
        }
