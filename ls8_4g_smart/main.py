# -*- coding: utf-8 -*-
"""
文件名称: main.py
功能描述: 4G拨号连接测试主程序
作者: AutoGen
创建日期: 2026-03-17
运行环境: Python 3.8+, paramiko
"""

import os
import sys
import time
import datetime

if getattr(sys, 'frozen', False):
    # 打包后的exe环境
    current_dir = os.path.dirname(sys.executable)
else:
    # 开发环境
    current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import (
    ConfigManager, 
    LogManager, 
    SSHClient, 
    CSVReporter,
)


class FourGSmartTest:
    """4G拨号连接智能测试类"""
    
    def __init__(self, cycle_times: int = None, base_export_num: int = None):
        self.config = ConfigManager()
        self.ssh_config = self.config.get_ssh_config()
        self.test_params = self.config.get_test_params()
        self.output_config = self.config.get_output_config()
        
        # 初始化目录
        self.date_str = datetime.datetime.now().strftime("%Y_%m%d")
        
        if base_export_num:
            self.output_config['base_export_num'] = base_export_num
        self.export_num = f"{self.output_config['base_export_num']:02d}"
        
        if cycle_times:
            self.test_params['cycle_times'] = cycle_times
        
        self.project_name = self.output_config['project_name']

        # 获取exe或脚本所在目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 如果配置的root_path是相对路径，则基于base_dir
        root_path = self.output_config['root_path']
        if not os.path.isabs(root_path):
            self.root_path = os.path.join(base_dir, root_path)
        else:
            self.root_path = root_path

        self.csv_dir = os.path.join(self.root_path, f"{self.project_name}_csv")
        self.log_dir = os.path.join(self.root_path, f"{self.project_name}_log")
        # 日志文件名
        log_filename = f"{self.date_str}_{self.export_num}_{self.project_name}_log.txt"
        self.logger = LogManager(self.log_dir, log_filename)
        
        # CSV报告
        csv_filename = f"{self.date_str}_{self.export_num}.csv"
        self.csv_reporter = CSVReporter(self.csv_dir, csv_filename)
        
        # SSH客户端
        self.ssh_client = None
        
        # 测试结果
        self.results = []
        self.success_count = 0
        self.fail_count = 0
    
    def run_single_cycle(self, cycle_num: int) -> bool:
        """执行单次4G拨号测试"""
        self.logger.info(f"===== 第{cycle_num}次4G拨号测试开始 =====")
        
        start_time = time.time()
        
        try:
            # 步骤1: SSH连接
            self.logger.info("步骤1: SSH连接接收机...")
            self.ssh_client = SSHClient(
                host=self.ssh_config['host'],
                port=self.ssh_config['port'],
                username=self.ssh_config['username'],
                password=self.ssh_config['password'],
                timeout=30
            )
            self.logger.info("步骤1完成: SSH连接成功")
            
            # 步骤2: 修改脚本权限
            self.logger.info("步骤2: 修改脚本执行权限...")
            script_path = self.test_params['script_path']
            if not self.ssh_client.chmod(script_path):
                self.logger.error("步骤2失败: 修改脚本权限失败")
                self.csv_reporter.write_result("修改权限", False, "修改脚本权限失败")
                self.ssh_client.close()
                return False
            self.logger.info("步骤2完成: 脚本权限修改成功")
            
            # 步骤3: 执行4G拨号脚本
            self.logger.info("步骤3: 执行4G拨号脚本...")
            script_command = f"cd /data/sbin"
            script_command = f"./start_4g.sh"
            self.ssh_client.execute_command(script_command, timeout=15)
            self.logger.info("步骤3完成: 4G拨号脚本已执行")
            
            # 等待5秒后查看日志
            self.logger.info("等待5秒后查看日志...")
            time.sleep(5)
            
            # 步骤4: 查看日志
            self.logger.info("步骤4: 查看日志文件...")
            success, log_content = self.ssh_client.get_file_lines(
                self.test_params['log_file'],
                self.test_params['log_lines']
            )
            
            if not success:
                self.logger.error(f"步骤4失败: 读取日志文件失败 - {log_content}")
                self.csv_reporter.write_result("查看日志", False, log_content)
            else:
                self.logger.info("步骤4完成: 日志内容如下:")
                self.logger.info("-" * 40)
                for line in log_content.split('\n'):
                    self.logger.info(line)
                self.logger.info("-" * 40)
                self.csv_reporter.write_result("查看日志", True, "成功读取最后4行日志")
            
            # 步骤5: Ping测试
            self.logger.info("步骤5: 执行Ping测试...")
            success, ping_result = self.ssh_client.ping(
                self.test_params['ping_address'],
                count=4,
                timeout=self.test_params['ping_timeout']
            )
            
            if not success:
                self.logger.error(f"步骤5失败: Ping测试失败 - {ping_result}")
                self.logger.error("尝试使用IP地址测试...")
                success, ping_result = self.ssh_client.ping(
                    "114.114.114.114",
                    count=4,
                    timeout=self.test_params['ping_timeout']
                )
                if not success:
                    self.logger.error(f"IP测试也失败: {ping_result}")
                    self.csv_reporter.write_result("Ping测试", False, ping_result)
                else:
                    self.logger.info("IP测试成功，网络连接正常")
                    self.csv_reporter.write_result("Ping测试", True, "成功连接互联网（IP测试）")
            else:
                self.logger.info("步骤5完成: Ping测试成功")
                self.csv_reporter.write_result("Ping测试", True, "成功连接互联网")
            
            self.logger.info(f"===== 第{cycle_num}次4G拨号测试完成 =====")
            
            end_time = time.time()
            duration = end_time - start_time
            self.logger.info(f"本次测试耗时: {duration:.2f}秒")
            self.csv_reporter.write_result("测试耗时", True, f"{duration:.2f}秒")
            
            self.success_count += 1
            return True
            
        except Exception as e:
            self.logger.error(f"测试执行异常: {e}")
            import traceback
            traceback.print_exc()
            self.csv_reporter.write_result("测试执行", False, f"异常: {str(e)}")
            return False
        finally:
            if self.ssh_client:
                self.ssh_client.close()
    
    def run(self):
        """执行完整测试流程"""
        cycle_times = self.test_params['cycle_times']
        
        self.logger.info("=" * 60)
        self.logger.info("4G拨号连接测试开始")
        self.logger.info(f"接收机IP: {self.ssh_config['host']}")
        self.logger.info(f"脚本路径: {self.test_params['script_path']}")
        self.logger.info(f"循环次数: {cycle_times}")
        self.logger.info("=" * 60)
        
        for cycle_num in range(1, cycle_times + 1):
            is_success = self.run_single_cycle(cycle_num)
            
            if is_success:
                self.logger.info(f"第{cycle_num}次测试成功")
            else:
                self.logger.warning(f"第{cycle_num}次测试失败")
            
            self.fail_count = cycle_num - self.success_count
            
            # 间隔时间
            if cycle_num < cycle_times:
                self.logger.info("等待3秒后进行下一次测试...")
                time.sleep(3)
        
        # 生成汇总
        self._generate_summary()
        
        self.logger.info("=" * 60)
        self.logger.info("4G拨号连接测试完成")
        self.logger.info("=" * 60)
    
    def _generate_summary(self):
        """生成汇总统计"""
        total = self.success_count + self.fail_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0.0
        
        summary = {
            '总测试次数': total,
            '成功次数': self.success_count,
            '失败次数': self.fail_count,
            '成功率': f"{success_rate:.2f}%",
        }
        
        self.csv_reporter.write_summary(summary)
        
        print("\n" + "=" * 60)
        print("-------------------- 测试汇总 --------------------")
        print(f"总测试次数: {total}")
        print(f"成功次数: {self.success_count}")
        print(f"失败次数: {self.fail_count}")
        print(f"成功率: {success_rate:.2f}%")
        
        threshold = self.test_params['success_threshold']
        if success_rate >= threshold:
            print(f"\n结论: 测试通过 (成功率 {success_rate:.2f}% >= {threshold}%)")
        else:
            print(f"\n结论: 测试失败 (成功率 {success_rate:.2f}% < {threshold}%)")
        
        print("=" * 60 + "\n")


def get_user_input():
    """获取用户输入的测试参数"""
    print("\n" + "=" * 50)
    print("4G拨号连接测试参数设置")
    print("=" * 50)
    
    while True:
        try:
            cycle_times = int(input("请输入循环次数 (默认1): ").strip() or "1")
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
    print("=" * 50 + "\n")
    
    return cycle_times, base_export_num


def main():
    """主函数入口"""
    try:
        cycle_times, base_export_num = get_user_input()
        
        test = FourGSmartTest(cycle_times, base_export_num)
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
