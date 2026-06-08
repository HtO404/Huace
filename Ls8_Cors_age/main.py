# -*- coding: utf-8 -*-
"""
文件名称: main.py
功能描述: 差分龄期数据获取测试
作者: AutoGen
创建日期: 2026-03-19
运行环境: Python 3.8+
"""

import os
import sys
import time
import datetime

# 获取当前目录（兼容打包后的exe环境）
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import (
    ConfigManager,
    LogManager,
    DeviceManager,
    CSVReporter,
)


class CorsAgeTest:
    """差分龄期数据获取测试类"""
    
    def __init__(self, cycle_times: int = None, base_export_num: int = None):
        self.config = ConfigManager()
        self.app_config = self.config.get_app_config()
        self.test_params = self.config.get_test_params()
        self.ui_elements = self.config.get_ui_elements()
        
        if cycle_times:
            self.test_params['cycle_times'] = cycle_times
        
        if base_export_num:
            self.test_params['base_export_num'] = base_export_num
        
        self.project_name = self.app_config['project_name']
        
        # 获取基准目录（兼容开发环境和打包后的exe环境）
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            self.base_dir = os.path.dirname(sys.executable)
            self.run_mode = "打包环境 (exe)"
        else:
            # 开发环境
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.run_mode = "开发环境 (python)"
        
        # 处理根路径（支持相对路径和绝对路径）
        root_path = self.app_config['root_path']
        if not os.path.isabs(root_path):
            # 相对路径：基于基准目录
            self.root_path = os.path.abspath(os.path.join(self.base_dir, root_path))
        else:
            # 绝对路径：直接使用
            self.root_path = root_path
        
        print(f"\n[路径解析] 运行模式: {self.run_mode}")
        print(f"[路径解析] 基准目录: {self.base_dir}")
        print(f"[路径解析] 配置的root_path: {root_path}")
        print(f"[路径解析] 最终根路径: {self.root_path}")
        
        self.date_str = datetime.datetime.now().strftime("%Y_%m%d")
        
        export_num = f"{self.test_params['base_export_num']:02d}"
        self.csv_dir = os.path.join(self.root_path, f"{self.project_name}_csv")
        self.log_dir = os.path.join(self.root_path, f"{self.project_name}_log")
        
        # 延迟初始化日志和CSV报告器
        self.logger = None
        self.csv_reporter = None
        self._log_filename = f"{self.date_str}_{export_num}_{self.project_name}_log.txt"
        self._csv_filename = f"{self.date_str}_{export_num}.csv"
        
        self.device_manager = DeviceManager()
        self.diff_age_id = self.ui_elements['diff_age_id']
        
        self.success_count = 0
        self.fail_count = 0
    
    def init_logging(self):
        """初始化日志文件夹和日志记录器（可提前调用以验证日志导出功能）"""
        print(f"\n[日志初始化] 创建日志目录: {self.log_dir}")
        print(f"[日志初始化] 创建CSV目录: {self.csv_dir}")
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        
        # 初始化日志记录器
        self.logger = LogManager(self.log_dir, self._log_filename)
        self.csv_reporter = CSVReporter(self.csv_dir, self._csv_filename)
        
        # 记录初始化成功信息
        self.logger.info("=" * 60)
        self.logger.info("日志系统初始化成功")
        self.logger.info(f"项目名称: {self.project_name}")
        self.logger.info(f"日志目录: {self.log_dir}")
        self.logger.info(f"CSV目录: {self.csv_dir}")
        self.logger.info("=" * 60)
        
        print(f"[日志初始化] 日志系统初始化成功！")
        print(f"[日志初始化] 日志文件: {os.path.join(self.log_dir, self._log_filename)}")
        print(f"[日志初始化] CSV文件: {os.path.join(self.csv_dir, self._csv_filename)}")
    
    def run(self):
        """执行测试流程"""
        cycle_times = self.test_params['cycle_times']
        
        self.logger.info("=" * 60)
        self.logger.info("差分龄期数据获取测试开始")
        self.logger.info(f"差分龄期元素ID: {self.diff_age_id}")
        self.logger.info(f"循环次数: {cycle_times}")
        self.logger.info("=" * 60)
        
        try:
            self.logger.info("连接设备...")
            self.device_manager.connect()
            self.logger.info("设备连接成功")
            
            csv_headers = ["时间", "序号", "差分龄期", "状态"]
            self.csv_reporter.write_header(csv_headers)
            
            for cycle_num in range(1, cycle_times + 1):
                self.logger.info(f"===== 第{cycle_num}次获取开始 =====")
                
                start_time = time.time()
                
                diff_age_text = self.device_manager.get_text(self.diff_age_id)
                
                if diff_age_text:
                    self.logger.info(f"获取成功: {diff_age_text}")
                    self.csv_reporter.write_row([
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        cycle_num,
                        diff_age_text,
                        "成功"
                    ])
                    self.success_count += 1
                else:
                    self.logger.error(f"获取失败: 元素不存在或text为空")
                    self.csv_reporter.write_row([
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        cycle_num,
                        "",
                        "失败"
                    ])
                    self.fail_count += 1
                
                if cycle_num < cycle_times:
                    wait_time = self.test_params['wait_interval']
                    self.logger.info(f"等待{wait_time}秒后进行下一次获取...")
                    time.sleep(wait_time)
            
            self._generate_summary()
            
        except Exception as e:
            self.logger.error(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.device_manager.close()
    
    def _generate_summary(self):
        """生成汇总"""
        total = self.success_count + self.fail_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0.0
        
        self.logger.info("=" * 60)
        self.logger.info("测试汇总")
        self.logger.info(f"总获取次数: {total}")
        self.logger.info(f"成功次数: {self.success_count}")
        self.logger.info(f"失败次数: {self.fail_count}")
        self.logger.info(f"成功率: {success_rate:.2f}%")
        self.logger.info("=" * 60)
        
        print("\n" + "=" * 60)
        print("-------------------- 测试汇总 --------------------")
        print(f"总获取次数: {total}")
        print(f"成功次数: {self.success_count}")
        print(f"失败次数: {self.fail_count}")
        print(f"成功率: {success_rate:.2f}%")
        print("=" * 60 + "\n")


def get_user_input():
    """获取用户输入的测试参数"""
    print("\n" + "=" * 50)
    print("差分龄期数据获取测试参数设置")
    print("=" * 50)
    
    while True:
        try:
            cycle_times = int(input("请输入循环次数 (默认100): ").strip() or "100")
            if cycle_times < 1:
                print("循环次数必须大于0，请重新输入")
                continue
            break
        except ValueError:
            print("输入无效，请输入数字")
    
    while True:
        try:
            base_export_num = int(input("请输入导出编号 (默认1): ").strip() or "1")
            if base_export_num < 1:
                print("导出编号必须大于0，请重新输入")
                continue
            break
        except ValueError:
            print("输入无效，请输入数字")
    
    print("=" * 50)
    print(f"循环次数: {cycle_times}")
    print(f"导出编号: {base_export_num}")
    print(f"采集间隔: 20ms")
    print("=" * 50 + "\n")
    
    return cycle_times, base_export_num


def main():
    """主函数入口"""
    try:
        cycle_times, base_export_num = get_user_input()
        
        test = CorsAgeTest(cycle_times, base_export_num)
        
        # 提前初始化日志文件夹（在连接设备之前）
        test.init_logging()
        
        test.run()
        
    except FileNotFoundError as e:
        print(f"文件错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
