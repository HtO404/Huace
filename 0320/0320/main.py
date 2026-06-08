# -*- coding: utf-8 -*-
"""
AIBOX_LD LFP自动化测试脚本
功能：双击屏幕坐标触发LFP值变化，OCR识别LFP值并记录耗时
"""
from calendar import c
import os
import re
import subprocess
import time
import csv
import configparser
import datetime
from tkinter import W
import uiautomator2 as u2
import pytesseract
from PIL import Image, ImageEnhance
from typing import Dict, List, Tuple

# 配置Tesseract OCR路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ConfigManager:
    """配置文件管理器，用于读取config.ini配置"""

    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        :param config_path: 配置文件路径，默认读取同目录下的config.ini
        """
        self.config = configparser.ConfigParser()
        if config_path:
            self.config_path = config_path
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(current_dir, 'config.ini')
        self.config.read(self.config_path, encoding='utf-8')

    def get(self, section: str, key: str, fallback=None):
        """获取字符串配置"""
        return self.config.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback=0):
        """获取整数配置"""
        return self.config.getint(section, key, fallback=fallback)

    def get_float(self, section: str, key: str, fallback=0.0):
        """获取浮点数配置"""
        return self.config.getfloat(section, key, fallback=fallback)


class LogManager:
    """日志管理器，负责记录测试日志到文件"""

    def __init__(self, log_dir: str, log_filename: str):
        """
        初始化日志管理器
        :param log_dir: 日志目录
        :param log_filename: 日志文件名
        """
        self.log_dir = log_dir
        self.log_filepath = os.path.join(log_dir, log_filename)
        os.makedirs(log_dir, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """写入日志到文件并打印到控制台"""
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
        """初始化设备管理器"""
        self.device = None
        self.timeout = 120  # 默认超时120秒

    def connect(self, serial: str = None):
        """
        连接uiautomator2设备
        :param serial: 设备序列号
        :return: 设备对象
        """
        self.device = u2.connect()
        return self.device

    def double_click(self, x: int, y: int):
        """
        双击指定坐标
        :param x: X坐标
        :param y: Y坐标
        """
        self.device.click(x, y)
        self.device.click(x, y)
        self.device.click(x, y)

    def take_screenshot(self, mark=''):
        """自定义截屏函数：保存到本次运行的截图文件夹"""
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screen_{ts}_{mark}.png"
            screenshot_path = os.path.join(os.getcwd(), filename)
            self.device.screenshot(screenshot_path)
            print(f"截屏成功：{screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"❌ 截屏失败：{str(e)}")
            return None

    def start_dir(self):
        """找平镜头复位操作"""
        try:
            if self.device(resourceId='com.huace.groundstation:id/cbOrientation').exists:
                self.device(resourceId='com.huace.groundstation:id/cbOrientation').click()
                time.sleep(1)
                self.device.click(0.75, 0.237)
                time.sleep(1)
                self.device(resourceId='com.huace.groundstation:id/cbOrientation').click()
        except Exception as e:
            print(f"❌ 复位操作异常：{str(e)}")

    def find_out(self):
        """检测并处理取消返航对话框"""
        try:
            if self.device(text='取消返航').exists:
                self.device(text='取消返航').click()
        except Exception as e:
            print(f"❌ 处理取消返航对话框异常：{str(e)}")

    def get_lfp_by_ocr(self, bounds: List[int]) -> str:
        """
        通过OCR识别LFP值
        :param bounds: 裁剪区域坐标 [x1, y1, x2, y2]
        :return: LFP数值字符串，识别失败返回空字符串
        """
        try:
            screenshot = self.device.screenshot()
            x1, y1, x2, y2 = bounds
            region = screenshot.crop((x1, y1, x2, y2))
            # enhancer = ImageEnhance.Contrast(region)
            # enhanced = enhancer.enhance(2.0)
            text = pytesseract.image_to_string(
                region,
                config='--psm 7 -c tessedit_char_whitelist=0123456789.'
            ).strip()
            
            # 处理结果：分割成数组（按数字分割）
            values = re.findall(r'[\d.]+', text)

            if len(values) == 2:
                return values

                # # 处理 '134' 去掉最后一位
                # for i, val in enumerate(values):
                #         values[i] = val[:-1]  # 去掉最后一位
                #         break
                # # 优先匹配LFP:后面的数字
                # match = re.search(r'LFP[:\s]*([\d.]+)', text, re.IGNORECASE)
                # if match:
                #     return match.group(1)

                # 备用方案：使用分割后的数组
                # if values:
                #     return values[0] if values else ""
            else:
                return ""
        except Exception as e:
            print(f"OCR错误: {e}")
            return ""

    def wait_for_change(self, lfp_bounds,initial_value: str, timeout: float = 120.0) -> Tuple[bool, str, float]:
        """
        等待数值变化（带超时机制）
        :param get_value_func: 获取数值的函数
        :param initial_value: 初始值
        :param timeout: 超时时间（秒），默认120秒
        :return: (是否变化, 变化后的值, 耗时毫秒)
        """
        start_time = time.time()
        last_valid_value = initial_value

        while True:
            elapsed = time.time() - start_time

            # 超时检查
            if elapsed >= timeout:
                return False, last_valid_value, elapsed * 1000

            try:
                for _ in range(4):
                    current = self.get_lfp_by_ocr(lfp_bounds)
                    if current != '' and len(current[0].replace('.', '')) >= 3 and len(current[1].replace('.', '')) >= 2:
                        break
                    else:
                        self.logger.info(f"当前值不正确：{current}")

                if current == '':
                    continue
                
                # 记录最近一次有效值
                if current:
                    last_valid_value = current
   
                res1 = str(current[0]).replace('.', '')[:2]
                res2 = str(current[1]).replace('.', '')[:1]

                temp1 = str(initial_value[0]).replace('.', '')[:2]
                temp2 = str(initial_value[1]).replace('.', '')[:1]
     

                change1 = round(abs(int(res1) - int(temp1)), 2)
                change2 = round(abs(int(res2) - int(temp2)), 2)

                if change1 > 0 or change2 > 0:
                    return True, current, elapsed * 1000

                # temp = round(abs(float(current) - float(initial_value)), 2)    
                # print(f'变化值：{temp}')
                # 检查是否有有效变化
                # if current and current != initial_value and temp > 0.1:
                #     return True, current, elapsed * 1000

            except Exception as e:
                # 识别异常，记录但继续等待
                print(f"⚠️ 获取值异常：{e}")

            time.sleep(0.1)

    def close(self):
        """关闭设备连接"""
        self.device = None
 

class ADBChecker:
    """ADB设备检查器，用于检查设备连接状态"""

    @staticmethod
    def check() -> Tuple[bool, List[str]]:
        """
        检查ADB设备连接
        :return: (是否连接成功, 设备列表)
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
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
        :param csv_dir: CSV目录
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

    def __init__(self):
        """初始化测试类，读取配置并初始化各管理器"""
        cfg = ConfigManager()

        self.project_name = cfg.get('AppConfig', 'project_name')
        self.root_path = cfg.get('AppConfig', 'root_path')
        self.device_serial = cfg.get('TestParams', 'device_serial')
        self.cycle_times = cfg.get_int('TestParams', 'cycle_times')
        self.wait_interval = cfg.get_int('TestParams', 'wait_interval')

        coords = [int(x) for x in cfg.get('TestParams', 'click_coords').split(',')]
        self.click_coords = [[coords[i], coords[i+1]] for i in range(0, len(coords), 2)]

        lfp_bounds = [int(x) for x in cfg.get('UIElements', 'lfp_bounds').split(',')]
        self.lfp_bounds = lfp_bounds

        self._init_logger()
        self._init_csv()

        self.device_mgr = DeviceManager()
        self.success_count = 0
        self.fail_count = 0
        self.timeout_count = 0  # 超时计数

    def _init_logger(self):
        """初始化日志管理器"""
        date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.log_dir = os.path.join(self.root_path, f"{self.project_name}_log")
        log_file = f"{date_str}_{self.project_name}_log.txt"
        self.logger = LogManager(self.log_dir, log_file)

    def _init_csv(self):
        """初始化CSV报告"""
        date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.csv_dir = os.path.join(self.root_path, f"{self.project_name}_csv")
        csv_file = f"{date_str}.csv"
        self.csv = CSVReporter(self.csv_dir, csv_file)
        self.csv.write_header(["时间", "序号", "坐标点", "初始LFP", "变化后LFP", "耗时(ms)", "状态"])

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

    def run_single_cycle(self, cycle_num: int):
        """
        执行单次测试循环
        :param cycle_num: 循环序号
        """
        self.logger.info(f"===== 第{cycle_num}次测试 =====")
        labels = ['a', 'b']

        for idx, (x, y) in enumerate(self.click_coords):
            label = labels[idx]

            try:
                # 处理取消返航对话框
                self.device_mgr.find_out()

                self.logger.info(f"双击{label}点 [{x}, {y}]")

                # 获取双击前的LFP值
                for _ in range(4):
                    initial_lfp = self.get_lfp_value()
                    if initial_lfp != '' and len(initial_lfp[0].replace('.', '')) >= 3 and len(initial_lfp[1].replace('.', '')) >= 2:
                        break
                    else:
                        self.logger.info(f"事先值不正确：{initial_lfp}")
                if initial_lfp == '':
                    self.logger.info(f"错误，initial_lfp识别失败: {initial_lfp}")
                    break

                self.logger.info(f"双击前LFP: {initial_lfp}")

                # 执行双击
                self.device_mgr.double_click(x, y)
                # # 定义获取LFP值的函数
                # for _ in range(3):
                #     temp = self.get_lfp_value()
                #     if temp.strip() != '':
                #         break
                # if temp.strip() == '':
                #     self.logger.info(f"错误，temp识别失败: {temp}")
                #     break

                # get_val = temp.replace('.', '')
                # # def get_val():
                # #     return self.get_lfp_value()
                

                # 等待LFP值变化（120秒超时）
                changed, new_lfp, elapsed = self.device_mgr.wait_for_change(
                    self.lfp_bounds, initial_lfp, timeout=120.0
                )

                if changed:
                    # LFP变化成功
                    self.logger.info(f"LFP变化: {initial_lfp} -> {new_lfp}, 耗时: {elapsed:.2f}ms")
                    self.csv.write_row([
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        str(cycle_num), label, initial_lfp, new_lfp, f"{elapsed:.2f}", "成功"
                    ])
                    self.success_count += 1
                else:
                    # 超时处理
                    self.timeout_count += 1
                    current = self.get_lfp_value()
                    self.logger.warning(f"{label}点超时({elapsed:.2f}ms), 当前LFP: {current}")
                    self.csv.write_row([
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        str(cycle_num), label, initial_lfp, current, f"{elapsed:.2f}", "超时"
                    ])
                    self.fail_count += 1
                    # 超时截屏
                    self.device_mgr.take_screenshot(f"{label}_timeout")

            except Exception as e:
                # 捕获异常，确保循环继续
                self.logger.error(f"{label}点执行异常：{str(e)}")
                self.csv.write_row([
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(cycle_num), label, "N/A", "N/A", "0", f"异常:{str(e)[:20]}"
                ])
                self.fail_count += 1

            # 每次操作后等待
            time.sleep(3)

    def run(self):
        """
        运行完整的自动化测试
        """
        self.logger.info("=" * 50)
        self.logger.info("AIBOX_LD LFP自动化测试开始")
        self.logger.info(f"循环次数: {self.cycle_times}")
        self.logger.info("=" * 50)

        # 检查设备连接
        if not self.check_device():
            print("\n错误: ADB设备未连接\n")
            return

        # 连接uiautomator2设备
        self.logger.info("连接uiautomator2...")
        self.device_mgr.connect()
        self.logger.info("设备连接成功")

        # 执行多次测试循环
        for i in range(1, self.cycle_times + 1):
            try:
                self.run_single_cycle(i)

                if i < self.cycle_times:
                    self.logger.info(f"等待{self.wait_interval}秒...")
                    time.sleep(self.wait_interval)

                # 每10次复位一次
                if i % 6 == 0:
                    self.logger.info("执行找平镜头复位...")
                    self.device_mgr.start_dir()
                    time.sleep(2)
                # self.device_mgr.stop_dir()
            except Exception as e:
                # 外层异常捕获，确保循环不中断
                self.logger.error(f"第{i}次循环异常：{str(e)}")
                continue

        # 输出测试结果统计
        total = self.success_count + self.fail_count
        rate = (self.success_count / total * 100) if total > 0 else 0
        self.logger.info("=" * 50)
        self.logger.info(f"总次数: {total}, 成功: {self.success_count}, 失败: {self.fail_count}, 超时: {self.timeout_count}, 成功率: {rate:.2f}%")
        self.logger.info("=" * 50)

        print(f"\n测试完成: 成功{self.success_count}, 失败{self.fail_count}, 超时{self.timeout_count}, 成功率{rate:.2f}%\n")


def main():
    """程序入口"""
    try:
        test = AIBOXTest()
        test.run()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
