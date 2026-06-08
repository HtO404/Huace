# -*- coding: utf-8 -*-
"""
文件名称: 运营商切换_最终版.py
功能描述: 最终优化的AIBOX运营商切换测试程序 - 基于原始逻辑的简化版本
作者: AutoGen
创建日期: 2026-04-17
运行环境: Python 3.8+, uiautomator2, adb
"""

import os
import sys
import time
import threading

try:
    import uiautomator2 as u2
except ImportError:
    print("错误: 请先安装 uiautomator2 库")
    print("安装命令: pip install uiautomator2")
    sys.exit(1)


class FinalOperatorSwitch:
    """最终优化的运营商切换测试类"""

    # 运营商列表 - 按切换顺序排列
    OPERATORS = ['中国移动', '中国联通', '中国电信']
    
    # 运营商单选框ID映射
    OPERATOR_IDS = {
        '中国移动': 'com.huace.groundstation:id/rb_ai_box_operator_mobile',
        '中国联通': 'com.huace.groundstation:id/rb_ai_box_operator_unicom', 
        '中国电信': 'com.huace.groundstation:id/rb_ai_box_operator_telecom'
    }
    
    # 网络等级元素ID - 用于判断切换是否成功
    NETWORK_LEVEL_ID = 'com.huace.groundstation:id/tv_aircraft_network_section_level'
    
    # 超时参数
    SWITCH_TIMEOUT = 60  # 运营商切换超时时间（秒）

    def __init__(self, device_serial=None):
        """初始化"""
        self.device = None
        self.device_serial = device_serial

    def connect_device(self):
        """连接设备"""
        try:
            if self.device_serial:
                print(f"连接设备: {self.device_serial}")
                self.device = u2.connect(self.device_serial)
            else:
                print("连接默认设备")
                self.device = u2.connect()
            
            print("设备连接成功")
            return True
        except Exception as e:
            print(f"设备连接失败: {e}")
            return False

    def safe_wait(self, elem, timeout: float) -> bool:
        """安全执行wait()，带超时保护 - 基于原始逻辑"""
        result = [None]
        completed = [False]

        def wait_task():
            try:
                result[0] = elem.wait(timeout=timeout)
            except Exception as e:
                result[0] = False
            finally:
                completed[0] = True

        thread = threading.Thread(target=wait_task, daemon=True)
        thread.start()
        thread.join(timeout + 2)

        if not completed[0]:
            print(f"wait超时({timeout}秒)，强制返回False")
            return False
        return result[0] if result[0] is not None else False

    def check_operator_switch(self) -> bool:
        """检查运营商切换是否成功 - 基于原始逻辑，但改为for循环每5秒检查一次"""
        max_wait_time = 180  # 最大等待时间180秒
        check_interval = 5    # 每5秒检查一次
        
        try:
            start_time = time.time()
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                elem = self.device(resourceId=self.NETWORK_LEVEL_ID)
                if elem.exists:
                    print(f"网络等级元素已出现，等待时间: {elapsed_time}秒")
                    return True
                
                # print(f"网络等级元素尚未出现，已等待: {elapsed_time}秒，继续等待...")
                time.sleep(check_interval)
                elapsed_time = int(time.time() - start_time)
            
            # 超时处理
            print(f"等待超时，{max_wait_time}秒内网络等级元素未出现")
            return False
            
        except Exception as e:
            print(f"检查运营商切换异常: {e}")
            return False

    def get_current_operator(self):
        """
        获取当前选中的运营商 - 通过检查单选框的checked属性
        
        Returns:
            str: 当前运营商名称，如果未找到返回None
        """
        try:
            # 检查每个运营商的单选框checked属性
            for operator in self.OPERATORS:
                operator_id = self.OPERATOR_IDS[operator]
                operator_elem = self.device(resourceId=operator_id)
                
                if operator_elem.exists:
                    # 获取checked属性
                    checked = operator_elem.info.get('checked', False)
                    print(f"运营商: {operator}, checked属性: {checked}")
                    
                    if checked:
                        print(f"当前选中的运营商: {operator}")
                        return operator
            
            print("未找到当前选中的运营商")
            return None
            
        except Exception as e:
            print(f"获取当前运营商异常: {e}")
            return None

    def switch_to_next_operator(self, current_operator):
        """
        切换到下一个运营商 - 基于原始switch_operator()函数逻辑
        
        Args:
            current_operator: 当前运营商名称
            
        Returns:
            bool: 切换是否成功
        """
        if current_operator not in self.OPERATORS:
            print(f"未知的当前运营商: {current_operator}")
            return False
        
        # 计算下一个运营商索引
        current_index = self.OPERATORS.index(current_operator)
        next_index = (current_index + 1) % len(self.OPERATORS)
        next_operator = self.OPERATORS[next_index]
        
        print(f"当前运营商: {current_operator} → 切换为: {next_operator}")
        start_time = time.time()
        
        try:
            # 查找下一个运营商单选框控件
            next_operator_id = self.OPERATOR_IDS[next_operator]
            next_operator_elem = self.device(resourceId=next_operator_id)

            # 点击运营商单选框
            next_operator_elem.click()
            print(f"已点击运营商单选框: {next_operator}")
            
            # 检查运营商切换结果 - 使用原始逻辑
            print(f"检查运营商切换结果...")
            if self.check_operator_switch():
                elapsed = (time.time() - start_time) * 1000
                print(f"运营商切换成功，耗时: {elapsed:.2f}ms")
                return True
            else:
                elapsed = (time.time() - start_time) * 1000
                print(f"切换后网络等级元素不存在，耗时: {elapsed:.2f}ms")
                return False
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"运营商切换异常: {e}")
            return False

    def run_single_cycle(self):
        """执行单次循环 - 只切换一次运营商"""
        print("-" * 40)
        
        # 获取当前运营商状态
        current_operator = self.get_current_operator()
        
        if current_operator is None:
            print("无法获取当前运营商状态，跳过本次循环")
            return
        
        # 切换到下一个运营商
        success = self.switch_to_next_operator(current_operator)
        
        if success:
            print("✓ 切换成功")
        else:
            print("✗ 切换失败")

    def run(self, cycle_times=1):
        """执行测试"""
        print("=" * 60)
        print("最终优化的运营商切换测试程序")
        print("每次循环只切换一次运营商")
        print("基于原始switch_operator()函数逻辑")
        print(f"循环次数: {cycle_times}")
        print("=" * 60)
        
        # 连接设备
        if not self.connect_device():
            return
        
        # 执行循环测试
        for i in range(1, cycle_times + 1):
            print(f"\n第 {i}/{cycle_times} 次循环")
            self.run_single_cycle()
            time.sleep(5)
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)


def main():
    """主函数"""
    try:
        # 获取用户输入
        cycle_times = int(input("请输入循环执行次数: "))
        
        # 可选：指定设备序列号
        device_serial = input("请输入设备序列号（留空使用默认设备）: ").strip()
        if not device_serial:
            device_serial = None
        
        # 创建测试实例并运行
        tester = FinalOperatorSwitch(device_serial)
        tester.run(cycle_times)
        
    except ValueError:
        print("输入错误: 请输入有效的数字")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行异常: {e}")


if __name__ == "__main__":
    main()