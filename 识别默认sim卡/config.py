# -*- coding: utf-8 -*-

PROJECT_NAME = "识别默认sim卡"
ROOT_PATH = "."
OUTPUT_DIR = "./output"

# 串口配置
SERIAL_PORT = "COM9"
SERIAL_BAUD = 9600
CMD_POWER_ON = bytes.fromhex("FE 0F 00 00 00 08 01 FF F1 D1")
CMD_POWER_OFF = bytes.fromhex("FE 0F 00 00 00 08 01 00 B1 91")
POWER_RESP_OK = "FE0F000000084002"

# 超时
TIMEOUT_SIGNAL = 100
WAIT_STABLE = 5

# 地面站包名
APP_PACKAGE = "com.huace.groundstation"

# UI元素
ELEMENT_DISCONNECTED = "com.huace.groundstation:id/tv_aircraft_network_section_level"
ELEMENT_SIGNAL = "com.huace.groundstation:id/iv_aircraft_network_section_signal"

ELEMENT_SLOT1_LAYOUT = "com.huace.groundstation:id/include_ai_box_network_1"
ELEMENT_OPERATOR_UNICOM = "com.huace.groundstation:id/rb_ai_box_operator_unicom"
ELEMENT_OPERATOR_TELECOM = "com.huace.groundstation:id/rb_ai_box_operator_telecom"
ELEMENT_OPERATOR_MOBILE = "com.huace.groundstation:id/rb_ai_box_operator_mobile"
