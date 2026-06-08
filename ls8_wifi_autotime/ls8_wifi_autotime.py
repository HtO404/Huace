# -*- coding: utf-8 -*-
"""
文件名称：ls8_wifi_autotime.py
功能：LS8 WiFi 自动连接时间压力测试（100 次循环）
遵循规则：日志/截图/Excel 自动生成 + 可输入变量 + 异常处理
运行环境：PyCharm + Python3.8+ + uiautomator2 + adb 环境
"""

# ====================== 【第一步：导入依赖库与加载配置】 ======================
import os
import sys
import time
import datetime
import subprocess
import configparser
import xlwt
import xlrd
import uiautomator2 as u2
from xlutils.copy import copy

# ====================== 【第二步：配置加载模块】 ======================

class ConfigManager:
    """配置管理类，封装所有配置项"""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.app_config = {}
        self.ui_elements = {}
        self.default_params = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        # 获取脚本或exe所在目录（兼容开发环境和打包环境）
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            current_dir = os.path.dirname(sys.executable)
            self.run_mode = "打包环境 (exe)"
        else:
            # 开发环境
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.run_mode = "开发环境 (python)"
        
        config_path = os.path.join(current_dir, 'config.ini')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"未找到配置文件：{config_path}")
        
        self.config.read(config_path, encoding='utf-8')
        
        self.app_config = dict(self.config.items('AppConfig'))
        self.ui_elements = dict(self.config.items('UIElements'))
        self.default_params = {
            'cycle_times': self.config.getint('DefaultParams', 'cycle_times'),
            'base_export_num': self.config.getint('DefaultParams', 'base_export_num'),
            'wait_operate': self.config.getint('DefaultParams', 'wait_operate'),
            'success_threshold': self.config.getfloat('DefaultParams', 'success_threshold'),
            'max_connection_time': self.config.getint('DefaultParams', 'max_connection_time', fallback=60),
        }
    
    def get_app_config(self):
        return self.app_config
    
    def get_ui_elements(self):
        return self.ui_elements
    
    def get_default_params(self):
        return self.default_params


# ====================== 【第三步：工具函数模块】 ======================

class UtilityFunctions:
    """工具函数类，提供日志、截图等通用功能"""
    
    def __init__(self, config):
        self.config = config
        self.date_format_dir = "%Y_%m%d"
        self.date_format_screenshot = "%Y%m%d_%H%M%S"
        self.date_format_log = "%Y-%m-%d %H:%M:%S"
        self.excel_headers = ["循环次数", "连接状态", "连接时间 (秒)", "操作时间", "备注"]
        self.export_num = '01'  # 默认导出编号
    
    def get_user_input(self):
        """获取用户输入的运行时参数"""
        print("=" * 50 + " 输入测试参数 " + "=" * 50)
        params = self.config.get_default_params().copy()
        
        try:
            cycle_input = input(f"\n请输入测试循环次数（默认{params['cycle_times']}）：")
            params['cycle_times'] = int(cycle_input) if cycle_input else params['cycle_times']
            
            export_num_input = input(f"请输入基准导出次数（默认{params['base_export_num']}）：")
            params['base_export_num'] = int(export_num_input) if export_num_input else params['base_export_num']
            
            wait_op_input = input(f"操作间隔时间（秒，默认{params['wait_operate']}）：")
            params['wait_operate'] = int(wait_op_input) if wait_op_input else params['wait_operate']
            
            max_time_input = input(f"请输入最大连接时间阈值（秒，默认{params['max_connection_time']}）：")
            params['max_connection_time'] = int(max_time_input) if max_time_input else params['max_connection_time']
        except ValueError:
            print("❌ 输入错误！将使用所有默认值。")
            return self.config.get_default_params()
        
        return params
    
    def init_directories_and_files(self, config_dict):
        """初始化所有目录和文件"""
        date_str = datetime.datetime.now().strftime(self.date_format_dir)
        
        # 设置导出编号
        self.export_num = config_dict.get('export_num', '01')
        
        image_parent_dir = os.path.join(config_dict["root_path"], f"{config_dict['project_name']}_image")
        excel_dir = os.path.join(config_dict["root_path"], f"{config_dict['project_name']}_excel")
        log_dir = os.path.join(config_dict["root_path"], f"{config_dict['project_name']}_log")
        current_image_dir = os.path.join(
            image_parent_dir,
            f"{date_str}_{config_dict['export_num']}_{config_dict['project_name']}_image"
        )
        
        dir_list = [config_dict["root_path"], image_parent_dir, excel_dir, log_dir, current_image_dir]
        for dir_path in dir_list:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                self.write_log(f"✅ 自动创建目录：{dir_path}", log_dir, date_str)
        
        excel_filename = f"{date_str}_{config_dict['export_num']}.xls"
        excel_path = os.path.join(excel_dir, excel_filename)
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("WiFi 自动连接时间测试")
        for col, header in enumerate(self.excel_headers):
            worksheet.write(0, col, header)
        workbook.save(excel_path)
        
        return {
            "date_str": date_str,
            "current_image_dir": current_image_dir,
            "excel_path": excel_path,
            "log_dir": log_dir
        }
    
    def write_log(self, content, log_dir, date_str, is_error=False):
        """写入日志文件"""
        # 使用固定的日志文件名格式，避免解析 content 导致的错误
        export_num = getattr(self, 'export_num', '01') if hasattr(self, 'export_num') else '01'
        log_filename = f"{date_str}_{export_num}_log.txt"
        log_path = os.path.join(log_dir, log_filename)
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_time = datetime.datetime.now().strftime(self.date_format_log)
        log_prefix = "【异常】" if is_error else "【正常】"
        log_content = f"[{log_time}] {log_prefix} {content}\n"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)
        
        print(log_content.strip())
    
    def take_screenshot(self, d, init_info, mark, is_error=False):
        """截图并保存"""
        screenshot_time = datetime.datetime.now().strftime(self.date_format_screenshot)
        error_suffix = "异常" if is_error else ""
        screenshot_name = f"screenshot_{screenshot_time}_{mark}{error_suffix}.png"
        screenshot_path = os.path.join(init_info["current_image_dir"], screenshot_name)
        
        try:
            d.screenshot(screenshot_path)
            self.write_log(f"📸 截图成功：{screenshot_name}", init_info["log_dir"], init_info["date_str"])
        except Exception as e:
            self.write_log(f"❌ 截图失败：{str(e)}", init_info["log_dir"], init_info["date_str"], is_error=True)
    
    def execute_adb_command(self, cmd, init_info):
        """执行 ADB 命令"""
        try:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            self.write_log(f"🖥️ ADB 执行成功：{cmd}\n结果：{result.decode('utf-8').strip()}",
                          init_info["log_dir"], init_info["date_str"])
            return True
        except subprocess.CalledProcessError as e:
            self.write_log(f"❌ ADB 执行失败：{cmd}\n错误：{e.output.decode('utf-8').strip()}",
                          init_info["log_dir"], init_info["date_str"], is_error=True)
            return False


# ====================== 【第四步：核心业务模块】 ======================

class TestSteps(UtilityFunctions):
    """测试步骤类，实现所有测试流程"""
    
    def __init__(self, d, config_manager, user_config, init_info):
        super().__init__(config_manager)
        self.d = d
        self.config_manager = config_manager
        self.user_config = user_config
        self.init_info = init_info
        self.ui_elements = config_manager.get_ui_elements()
        self.app_config = config_manager.get_app_config()
    
    def create_logger(self, cycle_num):
        """创建局部日志记录器"""
        def log_step(message, is_error=False):
            self.write_log(f"第{cycle_num}次：{message}", self.init_info['log_dir'],
                          self.init_info['date_str'], is_error)
        return log_step
    
    def step_1_open_ls8_and_settings(self, log_func):
        """步骤 1：打开 LS8 软件，进入设置，点击 WiFi 搜索接收机"""
        log_func("步骤 1：启动 LS8 App 并进入设置")
        
        # 启动 LS8 应用
        self.d.app_start(self.app_config['ls8_package_name'], self.app_config['ls8_main_activity'])
        time.sleep(2)
        
        # 点击"我同意"按钮
        log_func("点击'我同意'按钮")
        if self.d(resourceId=self.ui_elements['ls8_agree_btn']).wait(timeout=1.0):
            self.d(resourceId=self.ui_elements['ls8_agree_btn']).click()
        elif self.d(text="我同意").wait(timeout=1.0):
            self.d(text="我同意").click()
        else:
            log_func("⚠️未找到'我同意'按钮，继续执行")
        
        time.sleep(1)
        
        # 检查并处理弹窗
        time.sleep(2)
        self.check_and_handle_base_station_dialog(log_func)

        # ==================== 【步骤 2】点击连接设备 ====================
        log_func("👆【步骤 2】点击连接设备")
        if self.d(text=self.ui_elements.get('ls8_connect_device_btn', '')).wait(timeout=1.0):
            self.d(text=self.ui_elements.get('ls8_connect_device_btn', '')).click()
            time.sleep(1)
            log_func("✅【步骤 2】点击连接设备完成")
        else:
            log_func("⚠️ 未找到点击连接设备按钮")

        # ==================== 【步骤 3】点击选择 WiFi 设备 ====================
        log_func("👆【步骤 3】点击选择 wifi 设备")
        if self.d(resourceId='com.huace.landstar:id/tvWifiName').wait(timeout=1.0):
            self.d(resourceId='com.huace.landstar:id/tvWifiName').click()
            time.sleep(1)
            log_func("✅【步骤 3】点击选择 wifi 设备完成")
        else:
            log_func("⚠️ 未找到点击选择 wifi 设备按钮", is_error=True)

        # ==================== 【步骤 4】点击 WiFi 开关 ====================
        log_func("👆【步骤 4】点击 wifi 开关")
        if self.d(text='点击 wifi 开关').wait(timeout=1.0):
            self.d(text='点击 wifi 开关').click()
            time.sleep(1)
            log_func("✅【步骤 4】点击 wifi 开关完成")
        else:
            log_func("⚠️ 未找到点击 wifi 开关按钮", is_error=True)

        # ==================== 【步骤 5】通过 XPath 点击系统 WiFi 开关控件 ====================
        # 说明：Android 系统的 WiFi 开关控件有固定的资源 ID，使用 XPath 精确定位
        log_func("👆【步骤 5】点击系统级 WiFi 开关控件")
        try:
            # 使用 XPath 定位 Android 系统原生开关控件
            # resource-id="android:id/switch_widget" 是 Android 系统标准的 Switch 控件
            wifi_switch = self.d.xpath('//*[@resource-id="android:id/switch_widget"]')
            
            if wifi_switch.wait(timeout=2.0):
                wifi_switch.click()
                log_func("✅【步骤 5】已成功点击系统级 WiFi 开关")
                time.sleep(2)  # 等待 WiFi 开关状态变化
                
                # ==================== 【步骤 6】点击返回按钮 ====================
                log_func("👆【步骤 6】点击返回按钮")
                back_btn_xpath = self.ui_elements.get('ls8_back_btn', '')
                if back_btn_xpath:
                    if self.d.xpath(back_btn_xpath).wait(timeout=2.0):
                        self.d.xpath(back_btn_xpath).click()
                        log_func("✅【步骤 6】已成功点击返回按钮")
                        time.sleep(1)
                    else:
                        log_func("⚠️【步骤 6】未找到返回按钮", is_error=True)
                else:
                    log_func("⚠️【步骤 6】未配置返回按钮 XPath", is_error=True)
                
                # ==================== 【步骤 7】点击"已连接"文本 ====================
                log_func("👆【步骤 7】点击'连接'文本")
                if self.d(text='连接').wait(timeout=1.0):
                    self.d(text='连接').click()
                    log_func("✅【步骤 7】已成功点击'连接'")
                else:
                    log_func("⚠️【步骤 7】未找到'连接'文本", is_error=True)
            else:
                log_func("⚠️【步骤 5】未找到系统级 WiFi 开关控件，但继续执行", is_error=True)
        except Exception as e:
            log_func(f"❌【步骤 5】点击系统级 WiFi 开关失败：{e}", is_error=True)

    def step_2_wait_wifi_connection(self, log_func):
        """步骤 2：等待 WiFi 连接成功"""
        log_func("步骤 2：等待 WiFi 连接成功")
        
        # 等待电量视图中出现"外接"文本
        timeout = 15  # 最多等待 15 秒
        start_time = time.time()
        connected = False
        
        while time.time() - start_time < timeout:
            try:
                # 使用 XPath 定位电量视图控件，并检查是否包含"外接"文本
                electric_view = self.d.xpath('//*[@resource-id="com.huace.landstar:id/viewElectricQuantity"]')
                if self.d(resourceId=self.ui_elements['ls8_fixed_status_indicator'], text='固定').exists:
                    log_func("✅步骤 6：成功，状态已固定")
                    return
            except Exception as e:
                pass
            time.sleep(0.5)
        
        if not connected:
            log_func("⚠️ 未检测到‘固定’提示，但继续执行", is_error=True)
        
        return connected
    
    def step_3_reboot_device(self, log_func):
        """步骤 3：重启接收机（通过 ADB 重启安卓设备）"""
        log_func("步骤 3：重启接收机")
        
        # 执行 ADB 重启命令
        reboot_cmd = "adb reboot"
        try:
            subprocess.run(reboot_cmd, shell=True, check=True)
            log_func("✅ 已发送重启命令")
        except subprocess.CalledProcessError as e:
            log_func(f"❌ 重启命令执行失败：{e}", is_error=True)
            raise Exception("重启设备失败")
        
        # 等待设备重启完成（通常需要 1-2 分钟）
        log_func("⏳ 等待设备重启中...")
        time.sleep(20)  # 等待 15 秒让设备启动
        
        # 重新连接设备
        try:
            self.d = u2.connect()
            log_func("✅ 设备重启后重新连接成功")
        except Exception as e:
            log_func(f"❌ 重新连接设备失败：{e}", is_error=True)
            raise Exception("设备重启后无法连接")
        
        return self.d
    
    def measure_connection_time(self, log_func):
        """测量 WiFi 连接时间（从重启完成到显示 WiFi 连接成功）"""
        log_func("⏱️ 开始计时：WiFi 自动连接")
        start_time = time.time()
        
        # 步骤 1：解锁屏幕
        log_func("📱 步骤 1：解锁屏幕")
        try:
            # 大幅度上滑解锁（从屏幕底部 80% 位置滑到顶部 20% 位置）
            log_func("👆 上滑解锁屏幕")
            self.d.swipe(0.5, 0.8, 0.5, 0.2, 0.5)
            time.sleep(1)

            
            log_func("✅ 屏幕解锁完成")
        except Exception as e:
            log_func(f"⚠️ 屏幕解锁失败：{e}", is_error=True)

        # 点击屏幕右下角
        log_func("👆 点击屏幕右下角")
        screen_size = self.d.window_size()
        if screen_size:
            click_x = int(screen_size[0] * 0.9)  # 90% 宽度位置
            click_y = int(screen_size[1] * 0.9)  # 90% 高度位置
            self.d.click(click_x, click_y)
            time.sleep(1)
        else:
            # 如果获取不到屏幕尺寸，使用默认坐标
            self.d.click(900, 1600)
            time.sleep(1)
        # 步骤 2：打开 LS8 应用
        log_func("📱 步骤 2：打开 LS8 应用")
        try:
            self.d.app_start(self.app_config['ls8_package_name'], self.app_config['ls8_main_activity'])
            time.sleep(3)  # 等待应用启动
            log_func("✅ LS8 应用已启动")
        except Exception as e:
            log_func(f"⚠️ 打开应用失败：{e}", is_error=True)
        
        # 步骤 3：点击"我同意"按钮
        log_func("👆 步骤 3：点击'我同意'按钮")
        try:
            if self.d(resourceId=self.ui_elements['ls8_agree_btn']).wait(timeout=2.0):
                self.d(resourceId=self.ui_elements['ls8_agree_btn']).click()
                log_func("✅ 已点击'我同意'按钮")
            elif self.d(text="我同意").wait(timeout=2.0):
                self.d(text="我同意").click()
                log_func("✅ 已点击'我同意'按钮")
            else:
                log_func("⚠️ 未找到'我同意'按钮，继续执行")
            time.sleep(1)
        except Exception as e:
            log_func(f"⚠️ 点击'我同意'失败：{e}", is_error=True)

        # 步骤 4：监测并处理弹窗
        log_func("🔍 步骤 4：监测基站坐标变化弹窗")
        time.sleep(2)
        self.check_and_handle_base_station_dialog(log_func)
        
        # 步骤 5：等待并检测"固定"状态
        timeout = 60  # 最多等待 60 秒
        connected = False
        elapsed_time = 0
        
        log_func("🔍 步骤 5：开始监测'固定'状态...")
        
        while time.time() - start_time < timeout:
            try:
                # 检查是否出现"固定"状态
                if self.d(resourceId=self.ui_elements['ls8_fixed_status_indicator'], text='固定').exists:
                    connected = True
                    elapsed_time = time.time() - start_time
                    log_func(f"✅ WiFi 连接成功（检测到'固定'状态）！总耗时：{elapsed_time:.2f}秒")
                    break
            except Exception as e:
                pass
            
            time.sleep(1)
        
        if not connected:
            elapsed_time = time.time() - start_time
            log_func(f"⚠️ 在{timeout}秒内未检测到'固定'状态", is_error=True)
            return elapsed_time, False
        
        return elapsed_time, True

    
    def check_and_handle_base_station_dialog(self, log_func):
        """检查并处理基站坐标变化弹窗"""
        try:
            layout_id = self.ui_elements.get('ls8_three_button_layout_id', '')
            if not layout_id:
                return False
            
            layout_obj = self.d(resourceId=layout_id)
            if layout_obj.wait(timeout=1):
                xpath_layout = f'//*[@resource-id="{layout_id}"]'
                btn_nodes = self.d.xpath(xpath_layout + '//android.widget.Button').all()
                if btn_nodes:
                    try:
                        btn_nodes[-1].click()
                        log_func("✅【弹窗监测】通过 ID 点击确认按钮")
                        time.sleep(1)
                        return True
                    except Exception:
                        pass
                
                try:
                    info = layout_obj.info
                    b = info.get('bounds', None)
                    if b:
                        x = int(b['left'] + (b['right'] - b['left']) * 0.85)
                        y = int(b['top'] + (b['bottom'] - b['top']) * 0.5)
                        self.d.click(x, y)
                        log_func("✅【弹窗监测】通过 ID 坐标点击确认")
                        time.sleep(1)
                        return True
                except Exception:
                    pass
                
                try:
                    layout_obj.click()
                    log_func("✅【弹窗监测】点击三按钮布局容器")
                    time.sleep(1)
                    return True
                except Exception:
                    pass
                
                log_func("❌【弹窗监测】检测到弹窗但无法点击")
                return False
            return False
        except Exception as e:
            log_func(f"❌【弹窗监测】出错：{e}")
            return False
    
    def kill_all_background_apps(self, log_func):
        """杀死所有后台应用"""
        try:
            log_func("🧹【后台清理】开始清理后台应用...")
            self.d.shell("am force-stop com.android.settings")
            self.d.shell("am force-stop com.huace.landstar")
            
            self.d.press("recent")
            time.sleep(1)
            self.d.shell("input keyevent KEYCODE_CLEAR_ALL")
            time.sleep(1)
            
            log_func("✅【后台清理】后台应用清理完成")
        except Exception as e:
            log_func(f"⚠️【后台清理】清理时出错：{e}")



# ====================== 【第五步：主流程模块】 ======================

class WifiAutoTimeTest:
    """WiFi 自动连接时间测试主类"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.utility = UtilityFunctions(self.config_manager)
        self.d = None
        self.user_config = None
        self.init_info = None
    
    def run_single_test_cycle(self, cycle_num, is_first_cycle=False):
        """执行单次测试循环"""
        log_func = self.test_steps.create_logger(cycle_num)
        
        connection_time = 0
        is_success = False
        
        try:
            # 只有第一次循环才执行 WiFi 连接设置流程
            if is_first_cycle:
                # 步骤 1：打开 LS8 并进入 WiFi 设置（仅首次）
                log_func("=== 开始步骤 1：打开 LS8 并搜索 WiFi（仅首次） ===")
                self.test_steps.step_1_open_ls8_and_settings(log_func)
                time.sleep(self.user_config['wait_operate'])
                self.test_steps.check_and_handle_base_station_dialog(log_func)
                
                # 步骤 2：等待 WiFi 连接成功（仅首次）
                log_func("=== 开始步骤 2：等待 WiFi 连接（仅首次） ===")
                connected = self.test_steps.step_2_wait_wifi_connection(log_func)
                time.sleep(self.user_config['wait_operate'])
            else:
                log_func("⏭️  跳过 WiFi 连接设置流程（非首次循环）")
            
            # 步骤 3：重启设备并开始计时（每次循环都执行）
            log_func("=== 开始步骤 3：重启设备并计时 ===")
            self.test_steps.step_3_reboot_device(log_func)
            
            # 测量连接时间（每次循环都执行）
            log_func("=== 开始测量 WiFi 连接时间 ===")
            connection_time, is_success = self.test_steps.measure_connection_time(log_func)
            
            # 截图记录
            if is_success:
                self.utility.take_screenshot(self.d, self.init_info, f"循环{cycle_num}_成功_{connection_time:.2f}s")
            else:
                self.utility.take_screenshot(self.d, self.init_info, f"循环{cycle_num}_失败_{connection_time:.2f}s", is_error=True)
            
            # 清理环境
            log_func("🧹 开始清理环境...")
            self.test_steps.kill_all_background_apps(log_func)
            time.sleep(2)
            
        except Exception as e:
            log_func(f"❌ 测试流程异常：{e}", is_error=True)
            self.utility.take_screenshot(self.d, self.init_info, f"循环{cycle_num}_异常", is_error=True)
            is_success = False
        
        return is_success, connection_time
    
    def run(self):
        """主运行方法"""
        # 1. 获取用户输入
        self.user_config = self.utility.get_user_input()
        
        # 2. 合并配置
        app_config = self.config_manager.get_app_config()
        self.user_config['project_name'] = app_config.get('project_name', 'LS8_WIFI_AUTOTIME')
        
        # 获取基准目录（兼容开发环境和打包环境）
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            run_mode = "打包环境 (exe)"
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            run_mode = "开发环境 (python)"
        
        # 处理根路径（支持相对路径和绝对路径）
        root_path = app_config.get('root_path', '.')
        if not os.path.isabs(root_path):
            # 相对路径：基于基准目录
            final_root_path = os.path.abspath(os.path.join(base_dir, root_path))
        else:
            # 绝对路径：直接使用
            final_root_path = root_path
        
        self.user_config['root_path'] = final_root_path
        self.user_config['export_num'] = f"{self.user_config['base_export_num']:02d}"
        
        # 输出路径解析信息
        print(f"\n[路径解析] 运行模式: {run_mode}")
        print(f"[路径解析] 基准目录: {base_dir}")
        print(f"[路径解析] 配置的root_path: {root_path}")
        print(f"[路径解析] 最终根路径: {final_root_path}")
        
        # 3. 初始化目录和文件
        self.init_info = self.utility.init_directories_and_files(self.user_config)
        
        # 4. 连接设备
        try:
            self.d = u2.connect()
            self.d.settings["operation_delay"] = 1
            self.utility.write_log("📱 成功通过有线 ADB 连接安卓设备", 
                                  self.init_info['log_dir'], self.init_info['date_str'])
        except Exception as e:
            print(f"❌ 设备连接失败：{e}")
            print("💡 请确保：")
            print("   1. 设备已通过 USB 线连接到电脑")
            print("   2. 已开启 USB 调试模式")
            print("   3. 电脑已安装 ADB 驱动")
            return
        
        # 5. 初始化测试步骤类
        self.test_steps = TestSteps(self.d, self.config_manager, self.user_config, self.init_info)
        
        # 6. 初始化 Excel
        success_count = 0
        total_connection_time = 0
        rb = xlrd.open_workbook(self.init_info['excel_path'], formatting_info=True)
        wb = copy(rb)
        ws = wb.get_sheet(0)
        
        # 7. 执行循环测试
        for cycle_num in range(1, self.user_config["cycle_times"] + 1):
            print(f"\n{'='*60}")
            print(f"📊 开始第 {cycle_num}/{self.user_config['cycle_times']} 次循环测试")
            print(f"{'='*60}\n")
            
            # 只有第一次循环需要执行完整的 WiFi 连接流程
            is_first_cycle = (cycle_num == 1)
            is_success, connection_time = self.run_single_test_cycle(cycle_num, is_first_cycle)
            
            if is_success:
                success_count += 1
                total_connection_time += connection_time
            
            # 写入 Excel
            operate_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = cycle_num
            ws.write(row, 0, cycle_num)
            ws.write(row, 1, "成功" if is_success else "失败")
            ws.write(row, 2, f"{connection_time:.2f}" if connection_time > 0 else "N/A")
            ws.write(row, 3, operate_time)
            ws.write(row, 4, "" if is_success else "连接超时或异常")
            wb.save(self.init_info['excel_path'])
            
            # 输出本次结果
            status = "✅ 成功" if is_success else "❌ 失败"
            time_info = f"{connection_time:.2f}秒" if connection_time > 0 else "N/A"
            print(f"\n{status} | 连接时间：{time_info}")
            print(f"===== 第{cycle_num}次测试结束 =====\n")
        
        # 8. 统计结果
        avg_connection_time = total_connection_time / success_count if success_count > 0 else 0
        success_rate = (success_count / self.user_config["cycle_times"]) * 100
        max_threshold = self.user_config['max_connection_time']
        
        # 判断是否满足预期
        if avg_connection_time <= max_threshold and success_rate >= self.user_config['success_threshold']:
            test_result = f"🎉 测试通过！平均连接时间{avg_connection_time:.2f}秒 ≤ {max_threshold}秒，成功率{success_rate:.2f}%"
        else:
            if avg_connection_time > max_threshold:
                test_result = f"❌ 测试失败！平均连接时间{avg_connection_time:.2f}秒 > {max_threshold}秒"
            else:
                test_result = f"❌ 测试失败！成功率{success_rate:.2f}% < {self.user_config['success_threshold']}%"
        
        final_report = f"""
{'='*60}
-------------------- 测试完成 --------------------
总循环次数：{self.user_config['cycle_times']}
成功次数：{success_count}
失败次数：{self.user_config['cycle_times'] - success_count}
成功率：{success_rate:.2f}%
平均连接时间：{avg_connection_time:.2f}秒
最大连接时间阈值：{max_threshold}秒
结论：{test_result}
--------------------------------------------------
{'='*60}
"""
        
        print(final_report)
        self.utility.write_log(final_report, self.init_info['log_dir'], self.init_info['date_str'])
        
        # 写入 Excel 总结
        summary_row = self.user_config["cycle_times"] + 2
        ws.write(summary_row, 0, "测试结论")
        ws.write(summary_row, 1, test_result)
        ws.write(summary_row, 2, f"平均时间：{avg_connection_time:.2f}秒")
        wb.save(self.init_info['excel_path'])


# ====================== 【程序入口】 ======================
def main():
    """主函数"""
    try:
        import uiautomator2
        import xlwt
        import xlrd
        import xlutils
    except ImportError as e:
        print(f"❌ 缺少依赖库！请执行：pip install uiautomator2 xlwt xlrd xlutils")
        print(f"   缺少的库：{e.name}")
        return
    
    test = WifiAutoTimeTest()
    test.run()


if __name__ == "__main__":
    main()
