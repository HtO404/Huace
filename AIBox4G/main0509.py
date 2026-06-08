import uiautomator2 as u2
import time
import datetime
import os
import sys


# 核心检测元素：固传 IP
RC_IP_TEXT = "192.168.0.13:554"

# 吊舱的4G与RC地址
DETECT_IP_TEXT = "192.168.0.13:554"
ip_4g_text = "139.224.46.162"


# ===================== 打包专用路径函数 =====================
def get_resource_path(relative_path):
    """ 获取资源的绝对路径，兼容开发环境和打包后的环境 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ===================== 智能路径配置（关键修改） =====================
# 自动获取程序当前所在的文件夹，不管在哪台电脑都能用
if getattr(sys, 'frozen', False):
    # 如果是打包后的 exe 运行
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是代码脚本运行
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 在程序旁边创建一个“测试记录”文件夹，用来放日志和截图
BASE_DIR = os.path.join(BASE_DIR, "测试记录")
LOG_DIR = os.path.join(BASE_DIR, "log")
SCREENSHOT_ROOT_DIR = os.path.join(BASE_DIR, "imag_temp")
EXCEL_DIR = os.path.join(BASE_DIR, "excel_report")

# ===================== 核心配置区 =====================
try:
    LOOP_TIMES = int(input("压力测试循环次数:"))
except:
    LOOP_TIMES = 1  # 如果输入错误，默认 1 次

app_package = "com.huace.groundstation"

# 页面元素配置
ELEMENT_TEXT_MANUAL = "手动操控"
ELEMENT_TEXT_DEVICE_NAMES = ["X500", "Simulation"]
ELEMENT_TEXT_AIBOX = "AI 盒子"
REQUEST_PARAM_POPUP_TEXT = "正在请求参数，请稍等"



# 禁飞区弹窗配置
NO_FLY_ZONE_TIMEOUT_TEXT = "禁飞区上传失败：执行超时"
NO_FLY_ZONE_CHECKBOX_XPATH = "//android.widget.CheckBox"
NO_FLY_ZONE_AGREE_BTN_TEXT = "同意，不更新"

# 按钮 ID 配置
MENU_SETTING_ID = "com.huace.groundstation:id/btnMore"
ID_4G = "com.huace.groundstation:id/radioButton4GSetting"
ID_4G_MODULE = "com.huace.groundstation:id/rbStreamCheck4g"
ID_AIRLINK_MODULE = "com.huace.groundstation:id/rbStreamCheckAirlink"
ID_NOT_UPDATE = "com.huace.groundstation:id/btnNotUpdate"

# 等待时间配置
ELEMENT_WAIT_TIMEOUT = 3
REQUEST_PARAM_POPUP_TIMEOUT = 30
APP_LOAD_WAIT_TIME = 8
NO_FLY_ZONE_CHECK_INTERVAL = 1

# 导出次数 + 坐标配置

# EXPORT_INDEX = int(input("导出次数:"))
EXPORT_INDEX = 1

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1920
LEFT_BLANK_POS = (int(SCREEN_WIDTH * 0.216), int(SCREEN_HEIGHT * 0.512))

# 生成今天的日期字符串
TODAY_STR = datetime.datetime.now().strftime("%Y%m%d")
CURRENT_SCREENSHOT_DIR = os.path.join(SCREENSHOT_ROOT_DIR, f"{TODAY_STR}_{EXPORT_INDEX}_aibox_image")


# ===================== 基础工具函数 =====================
def write_log(content):
    """日志函数：记录并打印日志"""
    log_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_content = f"[{log_time}] {content}\n"
    print(log_content.strip())

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    try:
        with open(os.path.join(LOG_DIR, f"{TODAY_STR}_log.txt"), "a", encoding="utf-8") as f:
            f.write(log_content)
    except:
        pass


def take_screenshot(d, mark=""):
    """截图函数：仅在报错时调用"""
    if not os.path.exists(CURRENT_SCREENSHOT_DIR):
        os.makedirs(CURRENT_SCREENSHOT_DIR)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_name = f"screenshot_{timestamp}_{mark}.png" if mark else f"screenshot_{timestamp}.png"
    screenshot_path = os.path.join(CURRENT_SCREENSHOT_DIR, screenshot_name)

    try:
        d.screenshot(screenshot_path)
        write_log(f"📸 截图已保存：{screenshot_name}")
        return True
    except Exception as e:
        write_log(f"❌ 截图失败：{str(e)}")
        return False


# ===================== 弹窗监控与处理 =====================
def handle_no_fly_zone_timeout_popup(d, trigger_scene="未知场景"):
    """处理禁飞区弹窗（带场景标记）"""
    if d(textMatches=f".*{NO_FLY_ZONE_TIMEOUT_TEXT}.*").exists:
        write_log(f"\n⚠️【{trigger_scene}】检测到{NO_FLY_ZONE_TIMEOUT_TEXT}弹窗，开始处理...")
        try:
            if d.xpath(NO_FLY_ZONE_CHECKBOX_XPATH).exists:
                d.xpath(NO_FLY_ZONE_CHECKBOX_XPATH).click()
                write_log(f"✅ 点击禁飞区弹窗复选框")
            else:
                write_log(f"⚠️ 未找到禁飞区弹窗复选框")

            if d(text=NO_FLY_ZONE_AGREE_BTN_TEXT).exists:
                d(text=NO_FLY_ZONE_AGREE_BTN_TEXT).click()
                write_log(f"✅ 点击禁飞区弹窗同意按钮")
                write_log(f"✅【{trigger_scene}】禁飞区弹窗处理完成")
                return True
            else:
                write_log(f"❌ 未找到禁飞区弹窗同意按钮")
        except Exception as e:
            write_log(f"❌ 处理禁飞区弹窗失败：{str(e)}")
    return False


def setup_no_fly_watcher(d):
    """设置后台弹窗监控器"""
    write_log("\n🛡️ 初始化禁飞区弹窗监控器（后台实时监听）")

    def watcher_handler():
        handle_no_fly_zone_timeout_popup(d, trigger_scene="后台监控器")

    d.watcher.when(NO_FLY_ZONE_TIMEOUT_TEXT).call(watcher_handler)
    d.watcher.start(interval=1.0)
    write_log("✅ 禁飞区弹窗监控器已启动")


def continuous_no_fly_check(d, duration, trigger_scene):
    """持续检测弹窗（用于长等待场景）"""
    write_log(f"\n🔍【{trigger_scene}】持续检测禁飞区弹窗（时长{duration}秒）")
    start_time = time.time()
    while time.time() - start_time < duration:
        handle_no_fly_zone_timeout_popup(d, trigger_scene=f"{trigger_scene}_持续检测")
        time.sleep(NO_FLY_ZONE_CHECK_INTERVAL)
    write_log(f"✅【{trigger_scene}】持续检测结束")


# ===================== 增强版元素操作函数 =====================
def wait_for_element_enhanced(d, text="", resource_id="", xpath="", timeout=ELEMENT_WAIT_TIMEOUT):
    """增强版元素等待"""
    start_time = time.time()
    element_found = False
    while time.time() - start_time < timeout:
        handle_no_fly_zone_timeout_popup(d, trigger_scene=f"检测元素中")
        try:
            if resource_id and d(resourceId=resource_id).exists:
                element_found = True
                break
            elif text and d(text=text).exists:
                element_found = True
                break
            elif text and d(textContains=text).exists:
                element_found = True
                break
            elif xpath and d.xpath(xpath).exists:
                element_found = True
                break
            time.sleep(0.5)
        except:
            time.sleep(0.5)
    return element_found


def wait_not_element(d, text, timeout=ELEMENT_WAIT_TIMEOUT):
    """等待元素消失"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        handle_no_fly_zone_timeout_popup(d, trigger_scene=f"等待元素消失中")
        try:
            if not d(textMatches=f".*{text}.*").exists:
                return True
            time.sleep(0.5)
        except:
            time.sleep(0.5)
    return False


def click_element(d, text="", resource_id="", xpath="", pos=None, desc="未知元素"):
    """统一点击函数"""
    handle_no_fly_zone_timeout_popup(d, trigger_scene=f"点击 [{desc}] 前")
    click_success = False
    try:
        if pos:
            d.click(*pos)
            click_success = True
        elif resource_id and d(resourceId=resource_id).exists:
            d(resourceId=resource_id).click()
            click_success = True
        elif text and d(text=text).exists:
            d(text=text).click()
            click_success = True
        elif xpath and d.xpath(xpath).exists:
            d.xpath(xpath).click()
            click_success = True
        elif text and d(textContains=text).exists:
            d(textContains=text).click()
            click_success = True

        if click_success:
            time.sleep(1)
            handle_no_fly_zone_timeout_popup(d, trigger_scene=f"点击 [{desc}] 后")
    except Exception as e:
        write_log(f"❌ 点击{desc}时异常：{str(e)}")
    return click_success


def wait_for_request_param_popup(d, timeout=REQUEST_PARAM_POPUP_TIMEOUT):
    """等待请求参数弹窗消失"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        handle_no_fly_zone_timeout_popup(d, trigger_scene="等待请求参数弹窗中")
        try:
            if d(textMatches=f".*{REQUEST_PARAM_POPUP_TEXT}.*").exists:
                time.sleep(1)
            else:
                return True
        except:
            time.sleep(1)
    return False


def click_menu_setting(d):
    """点击菜单设置按钮"""
    wait_not_element(d, REQUEST_PARAM_POPUP_TEXT, timeout=5)
    if wait_for_element_enhanced(d, resource_id=MENU_SETTING_ID, timeout=5):
        click_success = click_element(d, resource_id=MENU_SETTING_ID, desc="菜单设置按钮")
        if click_success:
            if d(textMatches=f".*{REQUEST_PARAM_POPUP_TEXT}.*").exists:
                wait_for_request_param_popup(d, timeout=15)
            return True
    return False


def click_left_blank(d):
    """点击左边空白区域"""
    try:
        d.click(*LEFT_BLANK_POS)
        return True
    except:
        return False


# ===================== 模块切换函数 =====================
def switch_to_4g_module(d):
    """切换到 4G 模块"""
    write_log("\n📶 开始切换到 4G 模块")
    if not click_menu_setting(d):
        return False

    if wait_for_element_enhanced(d, resource_id=ID_4G_MODULE, timeout=2):
        click_element(d, resource_id=ID_4G_MODULE, desc="4G 模块按钮")
        click_left_blank(d)
    else:
        if wait_for_element_enhanced(d, resource_id=ID_4G, timeout=2):
            click_element(d, resource_id=ID_4G, desc="4G 设置按钮")
            if wait_for_element_enhanced(d, resource_id=ID_4G_MODULE, timeout=2):
                click_element(d, resource_id=ID_4G_MODULE, desc="4G 模块按钮")
                click_left_blank(d)
            else:
                return False
        else:
            return False

    # 验证切换结果
    time.sleep(1)
    switch_success = False
    for i in range(60):
        handle_no_fly_zone_timeout_popup(d, trigger_scene=f"4G 验证第{i + 1}次")
        is_connecting = d(text="正在连接").exists
        ip_found = wait_for_element_enhanced(d, text=ip_4g_text, timeout=1)
        is_4g_selected = d(resourceId=ID_4G_MODULE).selected if d(resourceId=ID_4G_MODULE).exists else False

        if (ip_found or is_4g_selected) and not is_connecting:
            switch_success = True
            break
        time.sleep(0.5)

    if not switch_success:
        take_screenshot(d, "4G 切换失败")
    return switch_success


def switch_to_camera_module(d):
    """切换到固传模块"""
    write_log("\n📸 开始切换到固传模块")
    if not click_menu_setting(d):
        return False

    if wait_for_element_enhanced(d, resource_id=ID_AIRLINK_MODULE, timeout=2):
        click_element(d, resource_id=ID_AIRLINK_MODULE, desc="固传模块按钮")
        click_left_blank(d)

    else:
        if wait_for_element_enhanced(d, resource_id=ID_4G, timeout=2):
            click_element(d, resource_id=ID_4G, desc="4G 设置按钮")
            if wait_for_element_enhanced(d, resource_id=ID_AIRLINK_MODULE, timeout=2):
                click_element(d, resource_id=ID_AIRLINK_MODULE, desc="固传模块按钮")
                click_left_blank(d)
            else:
                take_screenshot(d, "固传模块按钮未找到")
                return False
        else:
            return False

    # 验证切换结果
    time.sleep(1)
    switch_success = False
    for i in range(60):
        handle_no_fly_zone_timeout_popup(d, trigger_scene=f"固传验证第{i + 1}次")
        is_connecting = d(text="正在连接").exists

        ip_found = wait_for_element_enhanced(d, text=DETECT_IP_TEXT, timeout=1)

        if ip_found and not is_connecting:
            switch_success = True
            break
        time.sleep(0.5)

    if not switch_success:
        take_screenshot(d, "固传切换失败")
    return switch_success


# ===================== 初始化函数 =====================
def app_init(d):
    """APP 初始化"""
    write_log(f"\n🚀 开始 APP 初始化流程")
    continuous_no_fly_check(d, duration=APP_LOAD_WAIT_TIME, trigger_scene="APP 加载中")

    handle_no_fly_zone_timeout_popup(d, trigger_scene="处理初始弹窗前")
    try:
        popup_xpath = '//android.widget.RelativeLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]'
        if wait_for_element_enhanced(d, xpath=popup_xpath, timeout=5):
            click_element(d, xpath=popup_xpath, desc="初始弹窗关闭按钮")
            time.sleep(2)
            if wait_for_element_enhanced(d, resource_id=ID_NOT_UPDATE, timeout=5):
                click_element(d, resource_id=ID_NOT_UPDATE, desc="不更新按钮")
    except Exception as e:
        write_log(f"⚠️ 处理初始弹窗出错：{str(e)}")

    handle_no_fly_zone_timeout_popup(d, trigger_scene="点击手动操控前")
    if wait_for_element_enhanced(d, text=ELEMENT_TEXT_MANUAL, timeout=ELEMENT_WAIT_TIMEOUT):
        click_element(d, text=ELEMENT_TEXT_MANUAL, desc="手动操控按钮")
        time.sleep(2)
        wait_for_request_param_popup(d)
    else:
        return False

    try:
        d.click(0.831, 0.487)
        time.sleep(1)
    except:
        return False
    return True


def restart_app(d):
    """重启应用"""
    handle_no_fly_zone_timeout_popup(d, trigger_scene="重启应用前")
    try:
        d.app_stop(app_package)
        time.sleep(3)
        d.app_start(app_package)
        continuous_no_fly_check(d, duration=5, trigger_scene="APP 启动中")
        return app_init(d)
    except:
        return False


# ===================== 主流程 =====================
def main():
    """主流程"""
    # 初始化目录
    write_log("\n📁 初始化日志/截图目录")
    for dir_path in [LOG_DIR, SCREENSHOT_ROOT_DIR, CURRENT_SCREENSHOT_DIR, EXCEL_DIR]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    try:
        write_log("\n========== 开始测试 ==========")
        write_log(f"📱 目标应用：{app_package}")
        write_log(f"🔄 循环次数：{LOOP_TIMES}")

        # 连接设备
        write_log("\n🔌 连接到安卓设备")
        d = u2.connect()
        d.settings["operation_delay"] = (0.5, 1)
        d.settings["wait_timeout"] = ELEMENT_WAIT_TIMEOUT

        # 启动弹窗监控器
        setup_no_fly_watcher(d)

        # 核心检测
        write_log(f"\n🎯 核心检测：前台是否存在元素 {DETECT_IP_TEXT}")
        ip_detected = wait_for_element_enhanced(d, text=DETECT_IP_TEXT, timeout=10)

        if ip_detected:
            click_menu_setting(d)
        else:
            write_log(f"\n▶️ 启动应用：{app_package}")
            d.app_start(app_package)
            time.sleep(5)
            if not app_init(d):
                write_log("❌ APP 初始化失败，测试终止")
                return

        # 压力测试循环
        write_log(f"\n🧪 开始{LOOP_TIMES}次模块切换循环")
        for loop_num in range(1, LOOP_TIMES + 1):
            write_log(f"\n================ 第{loop_num}次循环 ================")
            # 循环前检查是否是吊舱界面
            ip_found = wait_for_element_enhanced(d, text=RC_IP_TEXT, timeout=1)
            if ip_found:
                d.click(0.1,0.9)
                time.sleep(1)

            # 切换 4G
            while True:
                if switch_to_4g_module(d):
                    break
                else:
                    if not restart_app(d):
                        return

            # 切换固传
            while True:
                if switch_to_camera_module(d):
                    break
                else:
                    if not restart_app(d):
                        return

        write_log("\n🎉 所有测试完成！🎉")
        write_log(f"📁 记录保存位置：{BASE_DIR}")

    except Exception as e:
        write_log(f"❌ 测试异常：{str(e)}")
        if 'd' in locals():
            take_screenshot(d, f"异常_{str(e)[:20]}")
    finally:
        if 'd' in locals():
            d.watcher.stop()
        write_log("\n========== 测试结束 ==========")


if __name__ == "__main__":
    main()
