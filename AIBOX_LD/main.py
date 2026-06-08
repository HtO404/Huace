# -*- coding: utf-8 -*-
"""
AIBOX_LD LFP自动化测试脚本
功能：双击屏幕坐标触发LFP值变化，OCR识别LFP值并记录耗时
"""
import os
import re
import subprocess
import time
import csv
import sys
import configparser
import datetime
import uiautomator2 as u2
import pytesseract
from PIL import Image, ImageEnhance
from typing import Dict, List, Tuple


class ConfigManager:
    """配置文件管理器，用于读取config.ini配置"""
    
    _instance = None
    
    def __new__(cls, config_path: str = None):
        """
        单例模式，确保全局只读取一次配置文件
        
        :param config_path: 配置文件路径
        :return: ConfigManager 实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        :param config_path: 配置文件路径，默认读取同目录下的config.ini
        :raises: configparser.Error 配置文件读取异常
        """
        if hasattr(self, 'config'):
            return
        self.config = configparser.ConfigParser()
        if config_path:
            self.config_path = config_path
        else:
            # 获取exe或脚本所在目录
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(exe_dir, 'config.ini')
        self.config.read(self.config_path, encoding='utf-8')

    def get(self, section: str, key: str, fallback=None):
        """
        获取字符串配置
        
        :param section: 配置节名称
        :param key: 配置键名
        :param fallback: 默认值，当配置不存在时返回
        :return: 配置值字符串
        """
        return self.config.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback=0):
        """
        获取整数配置
        
        :param section: 配置节名称
        :param key: 配置键名
        :param fallback: 默认值，当配置不存在时返回
        :return: 配置值整数
        """
        return self.config.getint(section, key, fallback=fallback)

    def get_float(self, section: str, key: str, fallback=0.0):
        """
        获取浮点数配置
        
        :param section: 配置节名称
        :param key: 配置键名
        :param fallback: 默认值，当配置不存在时返回
        :return: 配置值浮点数
        """
        return self.config.getfloat(section, key, fallback=fallback)


class LogManager:
    """日志管理器，负责记录测试日志到文件"""
    
    def __init__(self, log_dir: str, log_filename: str):
        """
        初始化日志管理器
        
        :param log_dir: 日志目录路径
        :param log_filename: 日志文件名
        """
        self.log_dir = log_dir
        self.log_filepath = os.path.join(log_dir, log_filename)
        os.makedirs(log_dir, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """
        写入日志到文件并打印到控制台
        
        :param message: 日志消息内容
        :param level: 日志级别（INFO/ERROR/WARNING）
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        with open(self.log_filepath, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
        print(log_entry)

    def info(self, message: str): 
        """记录info级别日志"""
        self.log(message, "INFO")
    
    def error(self, message: str): 
        """记录error级别日志"""
        self.log(message, "ERROR")
    
    def warning(self, message: str): 
        """记录warning级别日志"""
        self.log(message, "WARNING")


class DeviceManager:
    """设备管理器，负责连接设备并进行操作"""
    
    def __init__(self):
        """
        初始化设备管理器，从配置文件读取设备相关参数
        
        从 config.ini 的以下配置节读取参数：
        - OCRConfig: OCR识别相关配置（对比度、语言、超时时间）
        - ResetConfig: 复位操作配置（控件ID、重试次数、操作间隔）
        
        配置项说明：
        - contrast_enhance: 图像对比度增强系数（默认2.0）
        - ocr_language: OCR识别语言（默认'eng'）
        - timeout: OCR识别超时时间（默认60秒）
        - max_retries: 复位操作最大重试次数（默认3次）
        - reset_wait_interval: 复位操作等待间隔（默认0.3秒）
        - cb_orientation_id: 找平镜头控件ID
        - btn_home_id: 返回主页控件ID
        
        :raises: configparser.NoSectionError 配置节不存在
        :raises: configparser.NoOptionError 配置项不存在
        """
        self.device = None
        cfg = ConfigManager()
        self.contrast_enhance = cfg.get_float('OCRConfig', 'contrast_enhance', fallback=2.0)
        self.ocr_language = cfg.get('OCRConfig', 'ocr_language', fallback='eng')
        self.timeout = cfg.get_int('OCRConfig', 'timeout', fallback=60)
        self.max_retries = cfg.get_int('ResetConfig', 'max_retries', fallback=3)
        self.reset_wait_interval = cfg.get_float('ResetConfig', 'reset_wait_interval', fallback=0.3)
        self.cb_orientation_id = cfg.get('ResetConfig', 'cb_orientation_id')
        self.btn_home_id = cfg.get('ResetConfig', 'btn_home_id')

    def connect(self, serial: str = None):
        """
        连接uiautomator2设备
        
        :param serial: 设备序列号，None则连接默认设备
        :return: uiautomator2设备对象
        :raises: Exception 设备连接失败异常
        """
        print(f"[连接] 开始连接设备...")
        if serial:
            print(f"[连接] 使用设备序列号: {serial}")
            self.device = u2.connect(serial)
        else:
            print(f"[连接] 使用默认设备...")
            self.device = u2.connect()
        
        print(f"[连接] 设备连接成功")
        return self.device

    def double_click(self, x: int, y: int):
        """
        双击指定坐标（通过两次单击实现，间隔100ms）

        采用两次单击模拟双击，确保在不同设备上都能可靠响应

        :param x: X坐标
        :param y: Y坐标
        """
        if self.device is None:
            print(f"[跳过] 设备未连接，跳过双击操作: ({x}, {y})")
            return
        
        print(f"[点击] 开始双击坐标: ({x}, {y})")
        print(f"[点击] 第1次单击...")
        self.device.click(x, y)
        print(f"[点击] 等待100ms...")
        time.sleep(0.1)
        print(f"[点击] 第2次单击...")
        self.device.click(x, y)
        print(f"[点击] 双击操作完成")

    def get_lfp_and_angle(self, bounds: List[int]) -> Tuple[str, str]:
        """
        通过OCR识别LFP值和偏移角度值

        实现流程：
        1. 截取屏幕指定区域
        2. 增强图像对比度提高识别率
        3. 使用OCR识别文字内容
        4. 通过正则表达式提取LFP值和角度值

        :param bounds: 裁剪区域坐标 [x1, y1, x2, y2]
        :return: (LFP值, 角度值)，未识别到时返回空字符串
        :raises: Exception OCR识别异常
        """
        if self.device is None:
            print("[跳过] 设备未连接，跳过OCR识别")
            return "", ""
        try:
            screenshot = self.device.screenshot()
            x1, y1, x2, y2 = bounds
            region = screenshot.crop((x1, y1, x2, y2))
            enhancer = ImageEnhance.Contrast(region)
            enhanced = enhancer.enhance(self.contrast_enhance)
            text = pytesseract.image_to_string(enhanced, lang=self.ocr_language)

            lfp_value = ""
            angle_value = ""

            lfp_match = re.search(r'LFP[:\s]*([\d.]+)', text, re.IGNORECASE)
            if lfp_match:
                lfp_value = lfp_match.group(1)

            angle_match = re.search(r'(-?\d+)°', text)
            if angle_match:
                angle_value = angle_match.group(1)

            if not lfp_value and not angle_value:
                numbers = re.findall(r'[\d.]+', text)
                if numbers:
                    lfp_value = numbers[-1]

            return lfp_value, angle_value
        except Exception as e:
            print(f"OCR识别异常: {e}")
            return "", ""

    def get_lfp_by_ocr(self, bounds: List[int]) -> str:
        """
        通过OCR识别LFP值（兼容旧接口）
        
        :param bounds: 裁剪区域坐标 [x1, y1, x2, y2]
        :return: LFP数值字符串，未识别到时返回空字符串
        """
        lfp, _ = self.get_lfp_and_angle(bounds)
        return lfp

    def wait_for_change(self, get_value_func, initial_value: str, timeout: float = None) -> Tuple[bool, str, float]:
        """
        等待数值变化
        
        :param get_value_func: 获取数值的函数
        :param initial_value: 初始值
        :param timeout: 超时时间（秒），None则使用配置文件中的值
        :return: (是否变化, 变化后的值, 耗时毫秒)
        """
        if timeout is None:
            timeout = self.timeout
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False, "", elapsed * 1000
            current = get_value_func()
            if current and current != initial_value:
                return True, current, elapsed * 1000
            time.sleep(0.01)

    def wait_for_lfp_or_angle_change(self, get_func, initial_lfp: str, initial_angle: str, timeout: float = None) -> Tuple[bool, str, str, float]:
        """
        等待LFP值或角度值变化（OR逻辑）
        
        当LFP值或角度值任一发生变化时，即判定为变化成功
        
        :param get_func: 获取(lfp, angle)的函数
        :param initial_lfp: 初始LFP值
        :param initial_angle: 初始角度值
        :param timeout: 超时时间（秒），None则使用配置文件中的值
        :return: (是否变化, 变化后的LFP, 变化后的角度, 耗时毫秒)
        """
        if timeout is None:
            timeout = self.timeout
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False, "", "", elapsed * 1000

            current_lfp, current_angle = get_func()

            lfp_changed = current_lfp and current_lfp != initial_lfp
            angle_changed = current_angle and current_angle != initial_angle

            if lfp_changed or angle_changed:
                return True, current_lfp, current_angle, elapsed * 1000

            time.sleep(0.01)

    def take_debug_screenshot(self, mark: str = ""):
        """
        调试用截屏函数
        
        :param mark: 截图标记
        :return: 截图文件路径
        """
        if self.device is None:
            print(f"[截屏] 设备未连接，跳过截屏")
            return None
        
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{ts}_{mark}.png"
            screenshot_path = os.path.join(os.getcwd(), filename)
            self.device.screenshot(screenshot_path)
            print(f"[截屏] 调试截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"[截屏] 截图失败: {e}")
            return None

    def close(self):
        """关闭设备连接"""
        self.device = None

    def level_camera_reset(self, max_retries: int = None) -> Tuple[bool, str]:
        """
        找平镜头复位操作

        实现流程：
        1. 点击 cbOrientation 控件
        2. 等待操作响应
        3. 点击 btnHome 控件
        4. 检查操作结果

        :param max_retries: 最大重试次数，None则使用配置文件中的值
        :return: (是否成功, 结果信息)
        """
        if self.device is None:
            print("[跳过] 设备未连接，跳过复位操作")
            return False, "设备未连接"
        if max_retries is None:
            max_retries = self.max_retries
        
        for attempt in range(1, max_retries + 1):
            try:
                cb_elem = self.device(resourceId=self.cb_orientation_id)
                if cb_elem.exists(timeout=5000):
                    cb_elem.click()
                    time.sleep(self.reset_wait_interval)
                else:
                    return False, f"第{attempt}次尝试：未找到cbOrientation控件"

                btn_elem = self.device(resourceId=self.btn_home_id)
                if btn_elem.exists(timeout=5000):
                    btn_elem.click()
                    return True, f"复位成功"
                else:
                    return False, f"第{attempt}次尝试：未找到btnHome控件"

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(0.5)
                    continue
                return False, f"第{attempt}次尝试异常：{str(e)}"

        return False, "达到最大重试次数"


class ADBChecker:
    """ADB设备检查器，用于检查设备连接状态"""
    
    @staticmethod
    def check() -> Tuple[bool, List[str]]:
        """
        检查ADB设备连接
        
        :return: (是否连接成功, 设备列表)
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=60)
            lines = result.stdout.strip().split('\n')
            devices = [line.split('\t')[0] for line in lines[1:] if line.strip() and '\tdevice' in line]
            return len(devices) > 0, devices
        except FileNotFoundError:
            return False, ["ADB未找到"]
        except Exception as e:
            return False, [str(e)]


class CSVReporter:
    """CSV报告生成器，用于记录测试结果"""
    
    def __init__(self, csv_dir: str, csv_filename: str):
        """
        初始化CSV报告器
        
        :param csv_dir: CSV目录路径
        :param csv_filename: CSV文件名
        """
        self.csv_dir = csv_dir
        self.csv_filepath = os.path.join(csv_dir, csv_filename)
        os.makedirs(csv_dir, exist_ok=True)

    def write_header(self, headers: List[str]):
        """写入CSV表头"""
        with open(self.csv_filepath, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(headers)

    def write_row(self, row_data: List[str]):
        """写入CSV数据行"""
        with open(self.csv_filepath, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(row_data)


class AIBOXTest:
    """AIBOX_LD测试主类"""

    def __init__(self, cycle_times=None):
        """
        初始化测试类，读取配置并初始化各管理器
        
        从 config.ini 读取以下配置：
        - AppConfig: 项目名称、输出根目录
        - TestParams: 设备序列号、循环次数、操作间隔、双击坐标
        - UIElements: LFP区域坐标
        
        :param cycle_times: 循环次数，None则使用配置文件中的值
        """
        cfg = ConfigManager()
        
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            self.root_path = os.path.dirname(sys.executable)
        else:
            # 开发环境
            self.root_path = os.path.dirname(os.path.abspath(__file__))
        
        self.project_name = cfg.get('AppConfig', 'project_name')
        self.device_serial = cfg.get('TestParams', 'device_serial')
        self.cycle_times = cycle_times if cycle_times else cfg.get_int('TestParams', 'cycle_times')
        self.wait_interval = cfg.get_int('TestParams', 'wait_interval')
        
        coords = [int(x) for x in cfg.get('TestParams', 'click_coords').split(',')]
        self.click_coords = [[coords[i], coords[i+1]] for i in range(0, len(coords), 2)]
        
        lfp_bounds = [int(x) for x in cfg.get('UIElements', 'lfp_bounds').split(',')]
        self.lfp_bounds = lfp_bounds
        
        self._init_logger("00")
        self._init_csv("00")
        
        self.device_mgr = DeviceManager()
        self.success_count = 0
        self.fail_count = 0
        self.operation_count = 0
        self.reset_count = 0
        self.operation_threshold = cfg.get_int('ResetConfig', 'operation_threshold', fallback=10)

    def _init_logger(self, export_num_str):
        """初始化日志管理器"""
        date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.log_dir = os.path.join(self.root_path, f"{self.project_name}_log")
        log_file = f"{date_str}_{export_num_str}_{self.project_name}_log.txt"
        self.logger = LogManager(self.log_dir, log_file)

    def _init_csv(self, export_num_str):
        """初始化CSV报告"""
        date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.csv_dir = os.path.join(self.root_path, f"{self.project_name}_csv")
        csv_file = f"{date_str}_{export_num_str}.csv"
        self.csv = CSVReporter(self.csv_dir, csv_file)
        self.csv.write_header(["时间", "序号", "坐标点", "初始LFP", "变化后LFP", "初始角度", "变化后角度", "耗时(ms)", "状态"])
    
    def check_device(self) -> bool:
        """
        检查ADB设备连接
        
        :return: 设备是否连接
        """
        self.logger.info("检查ADB设备连接...")
        connected, devices = ADBChecker.check()
        if connected:
            self.logger.info(f"设备已连接: {devices}")
            return True
        else:
            self.logger.error(f"设备未连接: {devices}")
            return False
    
    def get_lfp_value(self) -> str:
        """
        获取当前LFP值
        
        :return: LFP数值字符串
        """
        return self.device_mgr.get_lfp_by_ocr(self.lfp_bounds)

    def get_lfp_and_angle(self) -> Tuple[str, str]:
        """
        获取当前LFP值和角度值
        
        :return: (LFP值, 角度值)
        """
        lfp, angle = self.device_mgr.get_lfp_and_angle(self.lfp_bounds)
        print(f"[OCR] LFP: {lfp or 'N/A':>8} | 角度: {angle or 'N/A':>8}")
        return lfp, angle
    
    def run_single_cycle(self, cycle_num: int):
        """
        执行单次测试循环
        
        测试流程：
        1. 遍历所有双击坐标点
        2. 记录双击前的LFP值和角度值
        3. 执行双击操作
        4. 等待LFP值或角度值变化
        5. 记录测试结果
        6. 每10次操作执行一次找平镜头复位
        
        :param cycle_num: 循环序号
        """
        self.logger.info(f"===== 第{cycle_num}次测试 =====")
        print(f"[流程] 开始第{cycle_num}次测试循环")

        if self.device_mgr.device is None:
            self.logger.warning("设备未连接，跳过本次循环")
            print(f"[流程] 设备未连接，跳过本次循环")
            return

        labels = ['a', 'b']

        for idx, (x, y) in enumerate(self.click_coords):
            label = labels[idx]
            self.logger.info(f"双击{label}点 [{x}, {y}]")
            print(f"[流程] 准备双击{label}点: ({x}, {y})")

            print(f"[流程] 步骤1: 获取双击前的LFP和角度...")
            initial_lfp, initial_angle = self.get_lfp_and_angle()
            self.logger.info(f"双击前 LFP: {initial_lfp}, 角度: {initial_angle}")
            print(f"[流程] 步骤1完成: LFP={initial_lfp}, 角度={initial_angle}")

            print(f"[流程] 步骤2: 执行双击操作...")
            self.device_mgr.take_debug_screenshot(f"before_click_{label}")
            self.device_mgr.double_click(x, y)
            self.device_mgr.take_debug_screenshot(f"after_click_{label}")
            print(f"[流程] 步骤2完成: 双击操作已执行")

            def get_values(): return self.get_lfp_and_angle()

            print(f"[流程] 步骤3: 等待值变化（超时{self.device_mgr.timeout}秒）...")
            changed, new_lfp, new_angle, elapsed = self.device_mgr.wait_for_lfp_or_angle_change(
                get_values, initial_lfp, initial_angle, timeout=self.device_mgr.timeout
            )
            print(f"[流程] 步骤3完成: 等待结束，耗时{elapsed:.2f}ms")

            if changed:
                change_desc = []
                if new_lfp != initial_lfp:
                    change_desc.append(f"LFP:{initial_lfp}->{new_lfp}")
                if new_angle != initial_angle:
                    change_desc.append(f"角度:{initial_angle}->{new_angle}")
                self.logger.info(f"{label}点变化: {', '.join(change_desc)}, 耗时: {elapsed:.2f}ms")
                print(f"[成功] {label}点检测到变化: {', '.join(change_desc)}")
                self.csv.write_row([
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(cycle_num), label, initial_lfp, new_lfp, initial_angle, new_angle, f"{elapsed:.2f}", "成功"
                ])
                self.success_count += 1
            else:
                current_lfp, current_angle = self.get_lfp_and_angle()
                self.logger.warning(f"{label}点超时, 当前 LFP: {current_lfp}, 角度: {current_angle}")
                print(f"[超时] {label}点未检测到变化，当前值: LFP={current_lfp}, 角度={current_angle}")
                self.csv.write_row([
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(cycle_num), label, initial_lfp, current_lfp, initial_angle, current_angle, f"{elapsed:.2f}", "超时"
                ])
                self.fail_count += 1
                self.device_mgr.take_debug_screenshot(f"timeout_{label}")

            self.operation_count += 1
            print(f"[流程] 累计操作次数: {self.operation_count}")

            if self.operation_count % self.operation_threshold == 0:
                self.logger.info(f"累计操作{self.operation_count}次，执行找平镜头复位...")
                print(f"[流程] 执行找平镜头复位...")
                reset_start = time.time()
                success, msg = self.device_mgr.level_camera_reset()
                reset_elapsed = (time.time() - reset_start) * 1000
                self.reset_count += 1
                self.logger.info(f"复位操作结果: {msg}, 耗时: {reset_elapsed:.2f}ms")
                print(f"[流程] 复位操作完成: {msg}, 耗时{reset_elapsed:.2f}ms")

            print(f"[流程] 等待1秒后继续...")
            time.sleep(1)
    
    def run(self, export_num_str):
        """
        运行完整的自动化测试
        
        测试流程：
        1. 初始化日志和CSV报告
        2. 检查设备连接
        3. 连接uiautomator2设备
        4. 执行多次测试循环
        5. 输出测试结果统计
        
        :param export_num_str: 导出次数字符串，用于文件命名
        """
        self._init_logger(export_num_str)
        self._init_csv(export_num_str)

        self.logger.info("=" * 50)
        self.logger.info("AIBOX_LD LFP自动化测试开始")
        self.logger.info(f"循环次数: {self.cycle_times}")
        self.logger.info("=" * 50)
        print(f"[启动] ==================== 测试启动 ====================")
        print(f"[启动] 项目名称: {self.project_name}")
        print(f"[启动] 循环次数: {self.cycle_times}")
        print(f"[启动] 操作间隔: {self.wait_interval}秒")
        print(f"[启动] 双击坐标: {self.click_coords}")
        print(f"[启动] LFP区域: {self.lfp_bounds}")
        print(f"[启动] ===============================================")

        print(f"[启动] 步骤1: 检查ADB设备连接...")
        if not self.check_device():
            print(f"[启动] 错误: ADB设备未连接，程序退出")
            print("\n错误: ADB设备未连接\n")
            return
        print(f"[启动] 步骤1完成: ADB设备已连接")

        print(f"[启动] 步骤2: 连接uiautomator2设备...")
        try:
            self.logger.info("连接uiautomator2...")
            self.device_mgr.connect(self.device_serial)
            self.logger.info("设备连接成功")
            print(f"[启动] 步骤2完成: uiautomator2设备连接成功")
        except Exception as e:
            self.logger.error(f"设备连接失败: {e}")
            print(f"[启动] 错误: uiautomator2设备连接失败 - {e}")
            print(f"\n错误: 设备连接失败 - {e}\n")
            return

        self.device_mgr.take_debug_screenshot("test_start")

        for i in range(1, self.cycle_times + 1):
            try:
                self.run_single_cycle(i)
                if i < self.cycle_times:
                    self.logger.info(f"等待{self.wait_interval}秒...")
                    print(f"[等待] 循环{self.wait_interval}秒后继续...")
                    time.sleep(self.wait_interval)
            except Exception as e:
                self.logger.error(f"第{i}次循环异常: {e}")
                print(f"[错误] 第{i}次循环异常: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        total = self.success_count + self.fail_count
        rate = (self.success_count / total * 100) if total > 0 else 0
        self.logger.info("=" * 50)
        self.logger.info(f"总次数: {total}, 成功: {self.success_count}, 失败: {self.fail_count}, 成功率: {rate:.2f}%")
        self.logger.info(f"累计操作次数: {self.operation_count}, 复位操作次数: {self.reset_count}")
        self.logger.info("=" * 50)

        print(f"\n[完成] ==================== 测试完成 ====================")
        print(f"[完成] 总次数: {total}")
        print(f"[完成] 成功: {self.success_count}")
        print(f"[完成] 失败: {self.fail_count}")
        print(f"[完成] 成功率: {rate:.2f}%")
        print(f"[完成] 累计操作: {self.operation_count}次")
        print(f"[完成] 复位操作: {self.reset_count}次")
        print(f"[完成] ===============================================\n")


def main():
    """程序入口"""
    try:
        cycle_times = int(input("请输入循环执行次数: "))
        export_num = int(input("请输入导出次数(用于文件命名): "))
        export_num_str = export_num if export_num >= 10 else f"0{export_num}"

        test = AIBOXTest(cycle_times)
        test.run(export_num_str)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
