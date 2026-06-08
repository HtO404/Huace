# -*- coding: utf-8 -*-
"""
文件名称: main.py
功能描述: FTP上传/下载稳定性测试主程序
作者: AutoGen
创建日期: 2026-03-13
运行环境: Python 3.8+
"""

import os
import sys
import time
import datetime
from typing import Dict, List, Tuple

# 获取当前目录（兼容打包后的exe环境）
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import (
    ConfigManager, 
    LogManager, 
    FileManager, 
    FTPClient, 
    CSVReporter,
    StatisticsCalculator
)


class FtpTransferTest:
    """FTP传输稳定性测试类"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.ftp_config = self.config.get_ftp_config()
        self.test_params = self.config.get_test_params()
        self.output_config = self.config.get_output_config()
        
        # 获取基准目录（兼容开发环境和打包后的exe环境）
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
            self.run_mode = "打包环境 (exe)"
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.run_mode = "开发环境 (python)"
        
        # 处理根路径（支持相对路径和绝对路径）
        root_path = self.output_config['root_path']
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
        
        # 初始化目录
        self.date_str = datetime.datetime.now().strftime("%Y_%m%d")
        self.export_num = f"{self.output_config['base_export_num']:02d}"
        
        # 测试类型
        self.test_type = self.test_params['test_type']
        self.test_type_name = "上传" if self.test_type == 1 else "下载"
        self.type_suffix = "up" if self.test_type == 1 else "down"
        
        # 根据测试类型设置目录名
        self.csv_dir = os.path.join(self.root_path, f"{self.output_config['project_name']}_{self.type_suffix}_csv")
        self.log_dir = os.path.join(self.root_path, f"{self.output_config['project_name']}_{self.type_suffix}_log")
        self.download_dir = os.path.join(self.root_path, f"{self.output_config['project_name']}_{self.type_suffix}_download")
        
        # 日志文件名
        log_filename = f"{self.date_str}_{self.export_num}_{self.output_config['project_name']}_log.txt"
        self.logger = LogManager(self.log_dir, log_filename)
        
        # 文件管理器
        self.file_manager = FileManager(self.download_dir)
        
        # 测试文件路径
        self.test_file_path = self.test_params['test_file_path']
        
        # CSV报告
        csv_filename = f"{self.date_str}_{self.export_num}_{self.type_suffix}.csv"
        self.csv_reporter = CSVReporter(self.csv_dir, csv_filename)
        
        # 测试结果存储
        self.results: List[Dict] = []
        self.success_count = 0
        self.fail_count = 0
        self.success_speeds: List[float] = []
        
        # 测试类型
        self.test_type = self.test_params['test_type']
        self.test_type_name = "上传" if self.test_type == 1 else "下载"
    
    def run_single_cycle(self, cycle_num: int) -> Tuple[bool, Dict]:
        """执行单次传输测试"""
        start_time = time.time()
        start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result = {
            'cycle': cycle_num,
            'start_time': start_time_str,
            'end_time': '',
            'duration': 0.0,
            'speed': 0.0,
            'status': '失败',
            'remark': '',
        }
        
        try:
            self.logger.info(f"===== 第{cycle_num}次{self.test_type_name}测试开始 =====")
            
            # 建立FTP连接
            ftp = FTPClient(
                server=self.ftp_config['server'],
                port=self.ftp_config['port'],
                username=self.ftp_config['username'],
                password=self.ftp_config['password'],
                passive_mode=self.ftp_config['passive_mode'],
                timeout=self.test_params['timeout']
            )
            
            # 获取文件大小(MB)
            file_size_mb = self.test_params['file_size_mb']
            
            if self.test_type == 1:
                # 上传测试
                success, error_msg, duration = self._upload_cycle(ftp, cycle_num)
            else:
                # 下载测试
                success, error_msg, duration = self._download_cycle(ftp, cycle_num)
            
            # 关闭连接
            ftp.close()
            
            # 计算传输速率
            speed = file_size_mb / duration if duration > 0 else 0.0
            
            result['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result['duration'] = duration
            result['speed'] = speed
            
            if success:
                result['status'] = '成功'
                result['remark'] = ''
                self.logger.info(f"第{cycle_num}次{self.test_type_name}成功 - 耗时: {duration:.2f}秒, 速率: {speed:.2f}MB/s")
                return True, result
            else:
                result['status'] = '失败'
                result['remark'] = error_msg
                self.logger.error(f"第{cycle_num}次{self.test_type_name}失败 - {error_msg}")
                return False, result
                
        except Exception as e:
            result['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result['duration'] = time.time() - start_time
            result['status'] = '失败'
            result['remark'] = f"异常: {str(e)}"
            self.logger.error(f"第{cycle_num}次{self.test_type_name}异常 - {str(e)}")
            return False, result
    
    def _upload_cycle(self, ftp: FTPClient, cycle_num: int) -> Tuple[bool, str, float]:
        """执行上传测试"""
        remote_filename = f"test_file_{cycle_num}.dat"
        
        success, error_msg, duration = ftp.upload_file(
            self.test_file_path,
            remote_filename,
            self.test_params['buffer_size']
        )
        
        # 上传完成后删除远程文件
        if success:
            ftp.delete_file(remote_filename)
        
        return success, error_msg, duration
    
    def _download_cycle(self, ftp: FTPClient, cycle_num: int) -> Tuple[bool, str, float]:
        """执行下载测试"""
        # 检查测试文件是否存在于FTP服务器
        remote_filename = os.path.basename(self.test_file_path)
        
        if not ftp.file_exists(remote_filename):
            # 文件不存在，先上传
            self.logger.info("FTP服务器上不存在测试文件，先执行上传...")
            success, error_msg, _ = ftp.upload_file(
                self.test_file_path,
                remote_filename,
                self.test_params['buffer_size']
            )
            if not success:
                return False, f"上传测试文件失败: {error_msg}", 0.0
        
        # 下载文件到临时目录
        temp_filename = f"download_temp_{cycle_num}.dat"
        local_filepath = os.path.join(self.download_dir, temp_filename)
        
        success, error_msg, duration = ftp.download_file(
            remote_filename,
            local_filepath,
            self.test_params['buffer_size']
        )
        
        # 下载完成后删除本地临时文件
        if success:
            self.file_manager.delete_file(local_filepath)
        
        return success, error_msg, duration
    
    def run(self):
        """执行完整测试流程"""
        # 检查测试文件是否存在
        if not os.path.exists(self.test_file_path):
            raise FileNotFoundError(f"测试文件不存在: {self.test_file_path}")
        
        file_size = os.path.getsize(self.test_file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        self.logger.info("=" * 60)
        self.logger.info(f"FTP{self.test_type_name}稳定性测试开始")
        self.logger.info(f"FTP服务器: {self.ftp_config['server']}:{self.ftp_config['port']}")
        self.logger.info(f"测试文件: {self.test_file_path} ({file_size_mb:.2f}MB)")
        self.logger.info(f"测试类型: {self.test_type_name}测试")
        self.logger.info(f"循环次数: {self.test_params['cycle_times']}")
        self.logger.info(f"测试间隔: {self.test_params['test_interval']}秒")
        self.logger.info("=" * 60)
        
        cycle_times = self.test_params['cycle_times']
        
        for cycle_num in range(1, cycle_times + 1):
            # 执行单次测试
            is_success, result = self.run_single_cycle(cycle_num)
            
            # 记录结果
            self.results.append(result)
            
            if is_success:
                self.success_count += 1
                self.success_speeds.append(result['speed'])
            else:
                self.fail_count += 1
            
            # 写入CSV
            self.csv_reporter.write_result(
                result['cycle'],
                result['start_time'],
                result['end_time'],
                result['duration'],
                result['speed'],
                result['status'],
                result['remark']
            )
            
            # 间隔时间
            if cycle_num < cycle_times:
                self.logger.info(f"等待{self.test_params['test_interval']}秒后进行下一次测试...")
                time.sleep(self.test_params['test_interval'])
        
        # 统计结果
        self._generate_summary()
        
        self.logger.info("=" * 60)
        self.logger.info(f"FTP{self.test_type_name}稳定性测试完成")
        self.logger.info("=" * 60)
    
    def _generate_summary(self):
        """生成汇总统计"""
        total = self.success_count + self.fail_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0.0
        
        # 计算速率统计（仅成功轮次）
        stats = StatisticsCalculator.calculate(self.success_speeds)
        
        # 计算所有轮次的平均耗时和平均速率
        all_durations = [r['duration'] for r in self.results if r['duration'] > 0]
        all_speeds = [r['speed'] for r in self.results if r['speed'] > 0]
        avg_duration_all = sum(all_durations) / len(all_durations) if all_durations else 0.0
        avg_speed_all = sum(all_speeds) / len(all_speeds) if all_speeds else 0.0
        
        # 汇总数据
        summary = {
            '测试类型': f"{self.test_type_name}测试",
            '总测试次数': total,
            '成功次数': self.success_count,
            '失败次数': self.fail_count,
            '成功率': f"{success_rate:.2f}%",
            '平均耗时(全部)': f"{avg_duration_all:.2f} 秒",
            '平均速率(全部)': f"{avg_speed_all:.2f} MB/s",
            '平均速率(成功)': f"{stats['average']:.2f} MB/s",
            '速率标准差': f"{stats['std_dev']:.2f} MB/s",
            '最大速率': f"{stats['max']:.2f} MB/s",
            '最小速率': f"{stats['min']:.2f} MB/s",
            '波动百分比': f"{stats['fluctuation_pct']:.2f}%",
        }
        
        # 写入CSV
        self.csv_reporter.write_summary(summary)
        
        # 控制台输出
        print("\n" + "=" * 60)
        print("-------------------- 测试汇总 --------------------")
        print(f"测试类型: {self.test_type_name}测试")
        print(f"总测试次数: {total}")
        print(f"成功次数: {self.success_count}")
        print(f"失败次数: {self.fail_count}")
        print(f"成功率: {success_rate:.2f}%")
        print(f"\n------ 全部轮次统计 ------")
        print(f"平均耗时: {avg_duration_all:.2f} 秒")
        print(f"平均速率: {avg_speed_all:.2f} MB/s")
        
        if self.success_speeds:
            print(f"\n------ 成功轮次速率统计 ------")
            print(f"平均速率: {stats['average']:.2f} MB/s")
            print(f"标准差: {stats['std_dev']:.2f} MB/s")
            print(f"最大速率: {stats['max']:.2f} MB/s")
            print(f"最小速率: {stats['min']:.2f} MB/s")
            print(f"波动百分比: {stats['fluctuation_pct']:.2f}%")
        
        # 判断是否通过
        threshold = self.test_params['success_threshold']
        if success_rate >= threshold:
            print(f"\n结论: 测试通过 (成功率 {success_rate:.2f}% >= {threshold}%)")
        else:
            print(f"\n结论: 测试失败 (成功率 {success_rate:.2f}% < {threshold}%)")
        
        print("=" * 60 + "\n")


def get_user_test_type() -> int:
    """获取用户选择的测试类型"""
    print("\n" + "=" * 50)
    print("请选择测试类型:")
    print("  1 - 上传速率测试")
    print("  2 - 下载速率测试")
    print("=" * 50)
    
    while True:
        try:
            choice = input("请输入测试类型 (1 或 2): ").strip()
            if choice in ['1', '2']:
                return int(choice)
            else:
                print("输入无效，请输入 1 或 2")
        except ValueError:
            print("输入无效，请输入数字 1 或 2")


def main():
    """主函数入口"""
    try:
        # 获取用户选择的测试类型
        test_type = get_user_test_type()
        
        # 创建测试实例（会自动读取配置）
        test = FtpTransferTest()
        
        # 覆盖配置中的测试类型
        test.test_type = test_type
        test.test_type_name = "上传" if test_type == 1 else "下载"
        test.type_suffix = "up" if test_type == 1 else "down"
        
        # 运行测试
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
