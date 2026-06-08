# -*- coding: utf-8 -*-
"""
文件名称：wifi_first.py
功能：LS8 WiFi 配对连接自动化测试（100 次循环）
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

# ====================== 【第一步：配置加载模块】 ======================

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    # 获取当前脚本或exe所在目录（兼容开发环境和打包环境）
    if getattr(sys, 'frozen', False):
        # 打包后的exe环境
        current_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"未找到配置文件：{config_path}")
        
    config.read(config_path, encoding='utf-8')
    
    app_config = dict(config.items('AppConfig'))
    ui_elements = dict(config.items('UIElements'))
    default_params = {
        'cycle_times': config.getint('DefaultParams', 'cycle_times'),
        'base_export_num': config.getint('DefaultParams', 'base_export_num'),
        'wait_operate': config.getint('DefaultParams', 'wait_operate'),
        'success_threshold': config.getfloat('DefaultParams', 'success_threshold'),
        'test_mode': config.getint('DefaultParams', 'test_mode', fallback=2),  # 默认自动连接测试
    }
    
    return app_config, ui_elements, default_params

# 加载配置
APP_CONFIG, UI_ELEMENTS, DEFAULT_PARAMS = load_config()

# 将配置项赋值给全局变量，以保持与后续代码的兼容性
# 注意：configparser 会自动将键名转为小写，所以这里使用小写获取
PROJECT_NAME = APP_CONFIG.get('project_name', 'LS8_WIFI_TEST')
ROOT_PATH = APP_CONFIG.get('root_path', os.getcwd())
LS8_PACKAGE_NAME = APP_CONFIG.get('ls8_package_name', 'com.huace.landstar')
LS8_MAIN_ACTIVITY = APP_CONFIG.get('ls8_main_activity', 'com.huace.landstar.ui.StartActivity')
SETTINGS_PACKAGE_NAME = APP_CONFIG.get('settings_package_name', 'com.android.settings')

# --- 4. 固定格式配置 ---
DATE_FORMAT_DIR = "%Y_%m%d"
DATE_FORMAT_SCREENSHOT = "%Y%m%d_%H%M%S"
DATE_FORMAT_LOG = "%Y-%m-%d %H:%M:%S"
EXCEL_HEADERS = ["循环次数", "连接状态", "操作时间", "备注"]

# ====================== 【第二步：工具函数模块】 ======================

def get_user_input():
    """仅获取用户输入的运行时参数（[DEFAULT_PARAMS]）。"""
    print("=" * 40 + " 输入测试参数 " + "=" * 40)
    params = DEFAULT_PARAMS.copy()
    try:
        # 【新增】选择测试用例类型
        print("\n请选择测试用例类型：")
        print("1 - 首次连接测试（完整流程，包含 WiFi 选择和连接）")
        print("2 - 自动连接测试（简化流程，仅验证自动连接）")
        test_type_input = input(f"请输入测试类型（1 或 2，默认 2）：")
        if test_type_input == "1":
            params['test_mode'] = 1
            print("✅ 已选择：首次连接测试")
        else:
            params['test_mode'] = 2
            print("✅ 已选择：自动连接测试")

        cycle_input = input(f"\n请输入测试循环次数（默认{params['cycle_times']}）：")
        params['cycle_times'] = int(cycle_input) if cycle_input else params['cycle_times']

        export_num_input = input(f"请输入基准导出次数（默认{params['base_export_num']}）：")
        params['base_export_num'] = int(export_num_input) if export_num_input else params['base_export_num']

        wait_op_input = input(f"操作间隔时间（秒，默认{params['wait_operate']}）：")
        params['wait_operate'] = int(wait_op_input) if wait_op_input else params['wait_operate']
    except ValueError:
        print("❌ 输入错误！将使用所有默认值。")
        params['test_mode'] = 2  # 默认使用自动连接测试
        return DEFAULT_PARAMS
    return params


def init_directories_and_files(config):
    """
    功能：初始化所有目录和文件（按规则自动创建）
    参数：config - 用户输入的配置字典
    返回：初始化后的路径/格式信息
    """
    # 生成时间戳
    date_str = datetime.datetime.now().strftime(DATE_FORMAT_DIR)
    
    # 定义各目录路径
    image_parent_dir = os.path.join(config["root_path"], f"{config['project_name']}_image")
    excel_dir = os.path.join(config["root_path"], f"{config['project_name']}_excel")
    log_dir = os.path.join(config["root_path"], f"{config['project_name']}_log")
    current_image_dir = os.path.join(
        image_parent_dir,
        f"{date_str}_{config['export_num']}_{config['project_name']}_image"
    )
    
    # 自动创建目录（不存在则创建）
    dir_list = [config["root_path"], image_parent_dir, excel_dir, log_dir, current_image_dir]
    for dir_path in dir_list:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            write_log(config, f"✅ 自动创建目录：{dir_path}", log_dir, date_str)
    
    # 创建Excel文件并写入表头
    excel_filename = f"{date_str}_{config['export_num']}.xls"
    excel_path = os.path.join(excel_dir, excel_filename)
    workbook = xlwt.Workbook(encoding="utf-8")
    worksheet = workbook.add_sheet("WiFi连接测试结果")
    for col, header in enumerate(EXCEL_HEADERS):
        worksheet.write(0, col, header)
    workbook.save(excel_path)
    
    # 返回初始化结果
    return {
        "date_str": date_str,
        "current_image_dir": current_image_dir,
        "excel_path": excel_path,
        "log_dir": log_dir
    }

def write_log(config, content, log_dir, date_str, is_error=False):
    """
    功能：写入日志文件（自动加时间戳）
    参数：
        config - 配置字典
        content - 日志内容
        log_dir - 日志目录
        date_str - 日期字符串
        is_error - 是否为异常日志
    """
    # 日志文件名
    # export_num = config.get('export_num', f"{config.get('base_export_num', 1):02d}")
    log_filename = f"{date_str}_{config['export_num']}_log.txt"
    log_path = os.path.join(log_dir, log_filename)
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志时间戳
    log_time = datetime.datetime.now().strftime(DATE_FORMAT_LOG)
    log_prefix = "【异常】" if is_error else "【正常】"
    log_content = f"[{log_time}] {log_prefix} {content}\n"
    
    # 写入日志（追加模式）
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_content)
    # 控制台打印（方便调试）
    print(log_content.strip())

def take_screenshot(d, config, init_info, mark, is_error=False):
    """
    功能：截图并按规则命名保存
    参数：
        d - uiautomator2连接对象
        config - 配置字典
        init_info - 初始化信息
        mark - 截图标记（如“循环1_连接成功”）
        is_error - 是否为异常截图
    """
    # 生成截图时间戳
    screenshot_time = datetime.datetime.now().strftime(DATE_FORMAT_SCREENSHOT)
    # 异常标记
    error_suffix = "异常" if is_error else ""
    # 截图文件名
    screenshot_name = f"screenshot_{screenshot_time}_{mark}{error_suffix}.png"
    screenshot_path = os.path.join(init_info["current_image_dir"], screenshot_name)
    
    # 执行截图
    try:
        d.screenshot(screenshot_path)
        write_log(config, f"📸 截图成功：{screenshot_name}", init_info["log_dir"], init_info["date_str"])
    except Exception as e:
        write_log(config, f"❌ 截图失败：{str(e)}", init_info["log_dir"], init_info["date_str"], is_error=True)

def execute_adb_command(cmd, config, init_info):
    """
    功能：执行ADB命令并返回结果
    参数：cmd - ADB命令字符串
    返回：True-成功，False-失败
    """
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        write_log(config, f"🖥️ ADB执行成功：{cmd}\n结果：{result.decode('utf-8').strip()}",
                  init_info["log_dir"], init_info["date_str"])
        return True
    except subprocess.CalledProcessError as e:
        write_log(config, f"❌ ADB执行失败：{cmd}\n错误：{e.output.decode('utf-8').strip()}",
                  init_info["log_dir"], init_info["date_str"], is_error=True)
        return False

# ====================== 【第三步：核心业务模块（按步骤拆分）】 ======================

def step_1_open_app_and_handle_connection(d, log_func):
    """步骤 1：打开 LS8 应用，点击'我同意'按钮，处理连接弹窗，监测固定状态"""

    log_func("步骤 1：启动 LS8 App 并处理连接流程")
    d.app_start(LS8_PACKAGE_NAME, LS8_MAIN_ACTIVITY)
    time.sleep(1.5)  # 等待 App 完全启动

    # 点击"我同意"按钮（隐私协议）
    log_func("点击'我同意'按钮")
    if d(resourceId=UI_ELEMENTS['ls8_agree_btn']).wait(timeout=1.0):
        d(resourceId=UI_ELEMENTS['ls8_agree_btn']).click()
    elif d(text="我同意").wait(timeout=1.0):
        d(text="我同意").click()
    else:
        log_func("⚠️未找到'我同意'按钮，继续执行")

    time.sleep(1)  # 等待界面跳转


    # 监测并处理弹窗
    check_and_handle_base_station_dialog(d, log_func)

def step_2_select_connection_type_and_turn_on_wifi(d, log_func, test_mode=2):
    """步骤 2：点击连接设备，选择连接设备类型，并打开 WiFi 开关（仅在首次连接模式下执行）"""

    # 【所有模式】都需要检查并关闭"连接到设备"弹窗
    log_func("🔍【步骤 2】检查'连接到设备'弹窗")
    try:
        # 方式 1：查找"取消"按钮
        if d(text="取消").wait(timeout=1.0):
            d(text="取消").click()
            log_func("✅【步骤 2】已点击'取消'按钮关闭连接弹窗")
            time.sleep(1)
        else:
            log_func("ℹ️【步骤 2】未发现连接弹窗，继续执行")
    except Exception as e:
        log_func(f"⚠️【步骤 2】检查连接弹窗时出错：{e}", is_error=True)
    
    # 【所有模式】都点击"连接设备"按钮
    log_func("👆【步骤 2】点击连接设备")
    d(text=UI_ELEMENTS['ls8_connect_device_btn']).click()
    time.sleep(1)
    log_func("✅【步骤 2】连接设备点击完成")

    # if test_mode == 1:
    #     # 首次连接测试：执行完整流程
        
    log_func("👆【步骤 2选择连接设备类型")
    d(resourceId=UI_ELEMENTS['ls8_select_wifi_list']).click()
    time.sleep(1)
    log_func("✅【步骤 2】设备类型选择完成")

    log_func("👆【步骤 2】点击 WiFi 开关")
    time.sleep(1)  # 等待界面加载
    try:
        # 使用 XPath 定位并点击 WiFi 开关
        wifi_switch = d.xpath('//*[@resource-id="android:id/switch_widget"]')
        if wifi_switch.wait(timeout=2.0):
            wifi_switch.click()
            log_func("✅【步骤 2】已成功点击 WiFi 开关")
            time.sleep(2)  # 等待 WiFi 打开
        else:
            log_func("⚠️【步骤 2】未找到 WiFi 开关，继续执行", is_error=True)
    except Exception as e:
        log_func(f"❌【步骤 2】点击 WiFi 开关失败：{e}", is_error=True)


def step_3_find_and_click_wifi(d, log_func, test_mode=2):
    """步骤 3：进入 WiFi 选择页，查找并点击目标 WiFi（仅在首次连接模式下执行）"""

    if test_mode == 1:
        log_func(f"🔍【步骤 3-首次连接】查找并点击 WiFi [{UI_ELEMENTS.get('target_wifi_name', '未知')}]")
        if d(text=UI_ELEMENTS.get('target_wifi_name', '')).wait(timeout=2.0):
            d(text=UI_ELEMENTS.get('target_wifi_name', '')).click()
            log_func("✅【步骤 3-首次连接】直接找到并点击 WiFi")
        else:
            log_func("⚠️【步骤 3-首次连接】未直接找到 WiFi，尝试上滑一次")
            d.swipe(0.5, 0.8, 0.5, 0.2, 0.5)  # 上滑
            time.sleep(1)
            if not d(text=UI_ELEMENTS.get('target_wifi_name', '')).wait(timeout=2.0):
                raise Exception(f"❌【步骤 3-首次连接】上滑后依然未找到 WiFi [{UI_ELEMENTS.get('target_wifi_name', '未知')}]")
            d(text=UI_ELEMENTS.get('target_wifi_name', '')).click()
            log_func("✅【步骤 3-首次连接】上滑后找到并点击 WiFi")
        log_func("✅【步骤 3-首次连接】WiFi 选择完成")
    else:
        # 自动连接测试：跳过此步骤
        log_func("⏭️【步骤 3-自动连接】跳过（WiFi 已自动连接）")


def step_4_verify_wifi_connected_and_return(d, log_func, test_mode=2):
    """步骤 4：等待"已连接"状态出现，然后返回上一级"""
    if test_mode == 1:
        log_func("⏳【步骤 4】等待'已连接'状态")
        if not d(text=UI_ELEMENTS['ls8_wifi_connected_status']).wait(timeout=3.0):
            raise Exception("❌【步骤 4】连接 WiFi 后，未在 3 秒内显示'已连接'状态")
        log_func("✅【步骤 4】WiFi 已连接")

    else:
        # 自动连接测试：跳过此步骤
        log_func("⏭️【步骤 3-自动连接】跳过（WiFi 已自动连接）")

    log_func("🔙【步骤 4】返回上一级")
    d.xpath(UI_ELEMENTS['ls8_back_btn']).click()
    log_func("✅【步骤 4】返回完成")


def step_5_click_main_connect_button(d, log_func,test_mode=2):
    """步骤 5：点击主界面的"连接"按钮"""
    if test_mode != 0:
        log_func("👆【步骤 5】点击主界面连接按钮")
        d(resourceId=UI_ELEMENTS['ls8_main_connect_btn']).click()
        log_func("✅【步骤 5】连接按钮点击完成")

def step_6_wait_for_fixed_status(d, log_func):
    """步骤 6：等待状态显示为绿色"固定"，此为测试成功的核心标志"""
    log_func("步骤 6：等待状态变为'固定'")

    # 在等待期间持续监测弹窗
    start_time = time.time()
    timeout = 10.0

    while time.time() - start_time < timeout:
        # 检查是否已经达到固定状态
        if d(resourceId=UI_ELEMENTS['ls8_fixed_status_indicator'], text='固定').exists:
            log_func("✅步骤 6：成功，状态已固定")
            return

        # 监测并处理弹窗
        check_and_handle_base_station_dialog(d, log_func)

        # 短暂等待后继续检查
        time.sleep(0.5)

    # 如果超时仍未达到固定状态
    raise Exception("❌等待 10 秒后，状态未变为'固定'")


def step_7_forget_wifi_in_settings(d, log_func, test_mode=2):
    """步骤 7：进入系统设置，忘记指定的 WiFi 网络（仅在首次连接模式下执行）"""

    if test_mode == 1:
        log_func("步骤 7（首次连接）：进入系统设置忘记 WiFi")
        try:
            log_func("7.1：返回主屏幕")
            d.press("home")
            time.sleep(2)

            log_func("7.2：启动系统设置应用")
            d.app_start(APP_CONFIG['settings_package_name'])
            time.sleep(1.5)

            log_func("7.3：尝试进入网络设置")
            if d(text=UI_ELEMENTS.get('settings_network_text', '')).wait(timeout=1.0):
                log_func("7.3：找到'网络和互联网'，点击进入")
                d(text=UI_ELEMENTS.get('settings_network_text', '')).click()
            else:
                log_func("7.3：❌未找到网络相关选项")

            d(text=UI_ELEMENTS.get('settings_internet_text', '')).wait(timeout=1.0)
            log_func("7.3：找到'互联网'，点击进入")
            d(text=UI_ELEMENTS.get('settings_internet_text', '')).click()

            time.sleep(1)

            log_func("7.4：查找已连接的 WiFi")
            if not d(text=UI_ELEMENTS.get('target_wifi_name_connected', UI_ELEMENTS.get('target_wifi_name', ''))).wait(
                    timeout=2.0):
                log_func("7.4：尝试查找普通 WiFi 名称")
                if not d(text=UI_ELEMENTS.get('target_wifi_name', '')).wait(timeout=1.0):
                    log_func("❌7.4：在 WiFi 列表中未找到目标 WiFi")
                else:
                    log_func("✅7.4：找到普通 WiFi 名称，点击")
                    d(text=UI_ELEMENTS.get('target_wifi_name', '')).click()
            else:
                log_func("7.4.5：✅找到已连接 WiFi，点击")
                d(text=UI_ELEMENTS.get('target_wifi_name_connected', UI_ELEMENTS.get('target_wifi_name', ''))).click()

            time.sleep(2)

            log_func("7.5：尝试点击忘记按钮")
            if d(resourceId=UI_ELEMENTS.get('settings_forget_wifi_btn', '')).wait(timeout=2.0):
                log_func("7.5：通过资源 ID 找到忘记按钮，点击")
                d(resourceId=UI_ELEMENTS.get('settings_forget_wifi_btn', '')).click()
            elif d(text="忘记").wait(timeout=2.0):
                log_func("7.5：找到中文'忘记'按钮，点击")
                d(text="忘记").click()
            elif d(text="Forget").wait(timeout=2.0):
                log_func("7.5：找到英文'Forget'按钮，点击")
                d(text="Forget").click()
            else:
                log_func("7.5：❌未找到忘记按钮")
        except Exception as e:
            d.press("home")
            raise Exception(f"❌忘记 WiFi 过程出错：{e}")

    log_func("7.6：返回主屏幕")
    d.press("home")
    time.sleep(1)

    log_func("7.7：清理后台应用")
    kill_all_background_apps(d, log_func)

    log_func(f"步骤 7（测试模式{test_mode}）：✅完成")
    # except Exception as e:
    #     # 确保无论如何都返回主屏幕
    # d.press("home")
    # raise Exception(f"忘记WiFi过程出错: {e}")


# ====================== 【第四步：主流程模块】 ======================

def check_and_handle_base_station_dialog(d, log_func):
    try:
        layout_id = UI_ELEMENTS['ls8_three_button_layout_id']
        layout_obj = d(resourceId=layout_id)
        if layout_obj.wait(timeout=0.5):
            xpath_layout = f'//*[@resource-id="{layout_id}"]'
            btn_nodes = d.xpath(xpath_layout + '//android.widget.Button').all()
            if btn_nodes:
                try:
                    btn_nodes[-1].click()
                    log_func("✅【弹窗监测】通过 ID 点击确认按钮")
                    time.sleep(1)
                    return True
                except Exception as _:
                    pass
            try:
                info = layout_obj.info
                b = info.get('bounds', None)
                if b:
                    x = int(b['left'] + (b['right'] - b['left']) * 0.85)
                    y = int(b['top'] + (b['bottom'] - b['top']) * 0.5)
                    d.click(x, y)
                    log_func("✅【弹窗监测】通过 ID 坐标点击确认")
                    time.sleep(1)
                    return True
            except Exception as _:
                pass
            try:
                layout_obj.click()
                log_func("✅【弹窗监测】点击三按钮布局容器")
                time.sleep(1)
                return True
            except Exception as _:
                pass
            log_func("❌【弹窗监测】检测到弹窗但无法点击")
            return False
        return False
    except Exception as e:
        log_func(f"❌【弹窗监测】出错：{e}")
        return False


def kill_all_background_apps(d, log_func):
    """
    杀死所有后台应用，清理内存
    """
    try:
        log_func("🧹【后台清理】开始清理后台应用...")
        # 方法 1：使用 ADB 命令清理后台
        d.shell("am force-stop com.android.settings")  # 先停止设置应用
        d.shell("am force-stop com.huace.landstar")   # 停止 LS8 应用
        
        # 方法 2：使用最近任务键清理
        d.press("recent")  # 打开最近任务
        time.sleep(1)
        d.shell("input keyevent KEYCODE_CLEAR_ALL")  # 清理所有后台
        time.sleep(1)
        
        log_func("✅【后台清理】后台应用清理完成")
    except Exception as e:
        log_func(f"⚠️【后台清理】清理时出错：{e}")
        # 即使出错也继续执行


def run_single_test_cycle(d, user_config, init_info, cycle_num):
    """
    执行单次完整的测试循环。
    返回：True-成功，False-失败
    """

    # 创建一个局部函数来简化日志记录
    def log_step(message, is_error=False):
        write_log(user_config, f"第{cycle_num}次 (模式{user_config['test_mode']})：{message}", init_info['log_dir'],
                  init_info['date_str'], is_error)

    try:
        test_mode = user_config['test_mode']

        step_1_open_app_and_handle_connection(d, log_step)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        step_2_select_connection_type_and_turn_on_wifi(d, log_step, test_mode)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        step_3_find_and_click_wifi(d, log_step, test_mode)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        step_4_verify_wifi_connected_and_return(d, log_step, test_mode)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        step_5_click_main_connect_button(d, log_step)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        step_6_wait_for_fixed_status(d, log_step)
        time.sleep(user_config['wait_operate'])
        check_and_handle_base_station_dialog(d, log_step)  # 弹窗监测

        # 如果所有步骤成功，返回 True
        log_step("✅ 本次循环测试成功", is_error=False)
        take_screenshot(d, user_config, init_info, f"循环{cycle_num}_成功")
        return True

    except Exception as e:
        log_step(f"❌ 测试流程异常：{e}", is_error=True)
        take_screenshot(d, user_config, init_info, f"循环{cycle_num}_异常", is_error=True)
        return False

    finally:
        # 无论成功与否，都尝试清理环境
        log_step("开始环境清理...")
        try:
            test_mode = user_config['test_mode']

            # 仅在首次连接测试模式下执行忘记 WiFi 操作
            if test_mode == 1:
                step_7_forget_wifi_in_settings(d, log_step, test_mode)
            else:
                # 自动连接测试模式下只清理后台
                d.press("home")
                time.sleep(1)
                kill_all_background_apps(d, log_step)
                log_step("✅环境清理完成（自动连接模式）")

            # 【新增】关闭 WiFi 连接
            if test_mode != 0:
                try:
                    log_step("正在关闭 WiFi...")
                    d.shell("svc wifi disable")
                    time.sleep(1)
                    log_step("✅ WiFi 已关闭")
                except Exception as wifi_error:
                    log_step(f"⚠️ 关闭 WiFi 异常：{wifi_error}")

            log_step("✅环境清理完成")
        except Exception as e:
            log_step(f"❌ 环境清理异常：{e}", is_error=True)
            d.app_stop(APP_CONFIG['ls8_package_name'])
            d.press("home")
            time.sleep(1)
            kill_all_background_apps(d, log_step)
# ====================== 【第五步：主流程模块（整合所有逻辑）】 ======================
def main():
    """主函数：程序入口"""
    # 1. 获取用户输入的运行时参数
    user_config = get_user_input()
    
    # 获取基准目录（兼容开发环境和打包环境）
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        run_mode = "打包环境 (exe)"
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        run_mode = "开发环境 (python)"
    
    # 处理根路径（支持相对路径和绝对路径）
    root_path = ROOT_PATH
    if not os.path.isabs(root_path):
        # 相对路径：基于基准目录
        final_root_path = os.path.abspath(os.path.join(base_dir, root_path))
    else:
        # 绝对路径：直接使用
        final_root_path = root_path
    
    # 将固定配置合并到用户配置中
    user_config['project_name'] = PROJECT_NAME
    user_config['root_path'] = final_root_path
    user_config['export_num'] = f"{user_config['base_export_num']:02d}"
    
    # 输出路径解析信息
    print(f"\n[路径解析] 运行模式: {run_mode}")
    print(f"[路径解析] 基准目录: {base_dir}")
    print(f"[路径解析] 配置的root_path: {root_path}")
    print(f"[路径解析] 最终根路径: {final_root_path}")

    # 2. 初始化目录和文件
    init_info = init_directories_and_files(user_config)
    
    # 3. 连接安卓设备（使用有线 ADB 连接）
    try:
        # 使用有线 ADB 连接，自动检测已连接的设备
        d = u2.connect()
        d.settings["operation_delay"] = 1  # 全局操作延迟
        write_log(user_config, "📱 成功通过有线 ADB 连接安卓设备", init_info['log_dir'], init_info['date_str'])
    except Exception as e:
        print(f"❌ 设备连接失败：{e}")
        print("💡 请确保：")
        print("   1. 设备已通过 USB 线连接到电脑")
        print("   2. 已开启 USB 调试模式")
        print("   3. 电脑已安装 ADB 驱动")
        return

    # 4. 初始化 Excel
    success_count = 0
    rb = xlrd.open_workbook(init_info['excel_path'], formatting_info=True)
    wb = copy(rb)
    ws = wb.get_sheet(0)
    
    # 5. 执行循环测试
    for cycle_num in range(1, user_config["cycle_times"] + 1):
        is_success = run_single_test_cycle(d, user_config, init_info, cycle_num)
        if is_success:
            success_count += 1
        
        # 写入Excel
        operate_time = datetime.datetime.now().strftime(DATE_FORMAT_LOG)
        ws.write(cycle_num, 0, cycle_num)
        ws.write(cycle_num, 1, "成功" if is_success else "失败")
        ws.write(cycle_num, 2, operate_time)
        ws.write(cycle_num, 3, "" if is_success else "流程异常，详见日志")
        wb.save(init_info['excel_path'])
        
        print(f"===== 第{cycle_num}次测试结束 =====\n")

    # 6. 统计并输出最终结果
    success_rate = (success_count / user_config["cycle_times"]) * 100
    threshold = DEFAULT_PARAMS['success_threshold']
    if success_rate >= threshold:
        test_result = f"🎉 测试通过！成功率{success_rate:.2f}% ≥ {threshold}%"
    else:
        test_result = f"❌ 测试未通过！成功率{success_rate:.2f}% ＜ {threshold}%"
    
    final_report = f"""
    -------------------- 测试完成 --------------------
    总循环次数：{user_config['cycle_times']}
    成功次数：{success_count}
    成功率：{success_rate:.2f}%
    结论：{test_result}
    --------------------------------------------------
    """
    print(final_report)
    write_log(user_config, final_report, init_info['log_dir'], init_info['date_str'])
    ws.write(user_config["cycle_times"] + 2, 0, "测试结论")
    ws.write(user_config["cycle_times"] + 2, 1, test_result)
    wb.save(init_info['excel_path'])

# ====================== 【程序入口】 ======================
if __name__ == "__main__":
    # 先检查依赖（可选）
    try:
        import uiautomator2
        import xlwt
        import xlrd
        import xlutils
    except ImportError as e:
        print(f"❌ 缺少依赖库！请执行：pip install uiautomator2 xlwt xlrd xlutils")
        print(f"   缺少的库：{e.name}")
    else:
        main()
