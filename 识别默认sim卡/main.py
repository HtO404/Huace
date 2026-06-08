# -*- coding: utf-8 -*-

import argparse
import json
import time
import serial
import csv
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import uiautomator2 as u2

import config


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = config.OUTPUT_DIR
if not os.path.isabs(OUTPUT_DIR):
    OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, OUTPUT_DIR))


class TestLogger:
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, log_dir: str, name: str):
        self.log_dir = log_dir
        self.name = name
        os.makedirs(log_dir, exist_ok=True)
        self.logger = self._setup()

    def _setup(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        if logger.handlers:
            return logger
        fh = RotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}.log"),
            maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        fh.setFormatter(logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT))
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT))
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

    def info(self, msg):
        self.logger.info(msg)

    def warn(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)


class CSVReporter:
    def __init__(self, csv_dir: str, filename: str):
        os.makedirs(csv_dir, exist_ok=True)
        self.path = os.path.join(csv_dir, filename)

    def write_row(self, row: list):
        with open(self.path, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(row)


def power_rs232(state: str, logger: TestLogger, serial_port: str) -> str:
    cmd = config.CMD_POWER_ON if state == "on" else config.CMD_POWER_OFF
    try:
        with serial.Serial(
            port=serial_port,
            baudrate=config.SERIAL_BAUD,
            bytesize=8, stopbits=1,
            parity=serial.PARITY_NONE,
            timeout=1.0
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            logger.info(f"发送报文: {cmd.hex(' ').upper()}")
            ser.write(cmd)
            logger.info("报文发送完毕，等待响应...")
            time.sleep(0.2)
            response = ser.read_all()
            resp_hex = response.hex().upper()
            if resp_hex == config.POWER_RESP_OK:
                logger.info(f"电源{state}成功")
                return "pass"
            else:
                logger.warn(f"电源{state}响应异常: {resp_hex}")
                return resp_hex
    except Exception as e:
        logger.error(f"串口错误({state}): {e}")
        return "fail"


def main():
    parser = argparse.ArgumentParser(description="识别默认SIM卡 - 上下电后检测默认数据SIM卡")
    parser.add_argument("--cycle-times", type=int, default=0, help="上下电次数（默认交互输入）")
    parser.add_argument("--interval-down", type=int, default=0, help="下电等待时间秒（默认交互输入）")
    parser.add_argument("--serial-port", type=str, default="", help=f"串口号（默认{config.SERIAL_PORT}）")
    parser.add_argument("--marker", type=str, default="", help="完成后写入标记文件路径（供自动化流水线使用）")
    args = parser.parse_args()

    if args.cycle_times > 0:
        cycle_times = args.cycle_times
        interval_down = args.interval_down if args.interval_down > 0 else 15
        serial_port = args.serial_port or config.SERIAL_PORT
        print(f"非交互模式: {cycle_times}次 / 下电{interval_down}s / {serial_port}")
    else:
        print("=" * 50)
        print("识别默认SIM卡 - 上下电后检测默认数据SIM卡")
        print("=" * 50)
        cycle_times = int(input("上下电次数：") or "1")
        interval_down = int(input("下电等待时间（秒）：") or "5")
        serial_port = input(f"串口号（默认{config.SERIAL_PORT}）：").strip() or config.SERIAL_PORT

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(OUTPUT_DIR, "logs")
    csv_dir = os.path.join(OUTPUT_DIR, "csv")
    img_dir = os.path.join(OUTPUT_DIR, "image")
    os.makedirs(img_dir, exist_ok=True)

    logger = TestLogger(log_dir, f"sim_{ts}")
    csv_reporter = CSVReporter(csv_dir, f"sim_test_{ts}.csv")
    csv_reporter.write_row([
        "次数", "下电结果", "上电结果", "未连接出现耗时(s)",
        "信号出现耗时(s)", "默认识别结果", "备注"
    ])
    logger.info(f"CSV文件已创建: {csv_reporter.path}")

    d = None
    try:
        d = u2.connect()
        logger.info("设备已连接")
    except Exception as e:
        logger.error(f"连接设备失败: {e}")
        return

    success_cnt = 0

    for cycle in range(1, cycle_times + 1):
        logger.info(f"\n{'='*50}")
        logger.info(f"第 {cycle}/{cycle_times} 次循环")
        logger.info(f"{'='*50}")

        notes = []
        disconnect_time = None
        signal_time = None
        off_result = ""
        on_result = ""

        # 1. 下电
        logger.info("--- 下电 ---")
        res = power_rs232("off", logger, serial_port)
        if res == "pass":
            off_result = "成功"
        else:
            off_result = "失败"
            path = os.path.join(img_dir, f"power_off_fail_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            d.screenshot(path)
            logger.info(f"截图已保存: {path}")
            notes.append(f"下电{off_result}")

        # 2. 等待下电时间
        logger.info(f"等待下电 {interval_down}s ...")
        time.sleep(interval_down)

        # 3. 等待"未连接"出现
        logger.info("--- 等待未连接出现 ---")
        disconnect_start = time.time()
        disconnect_ok = False
        while time.time() - disconnect_start < 30:
            try:
                if d(resourceId=config.ELEMENT_DISCONNECTED).exists:
                    disconnect_time = time.time() - disconnect_start
                    logger.info(f"未连接已出现，耗时 {disconnect_time:.1f}s")
                    disconnect_ok = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not disconnect_ok:
            disconnect_time = 10
            logger.warn("未连接在10s内未出现")
            path = os.path.join(img_dir, f"no_disconnect_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            d.screenshot(path)
            logger.info(f"截图已保存: {path}")
            notes.append("未连接未出现")

        # 4. 上电
        logger.info("--- 上电 ---")
        res = power_rs232("on", logger, serial_port)
        if res == "pass":
            on_result = "成功"
        else:
            on_result = "失败"
            path = os.path.join(img_dir, f"power_on_fail_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            d.screenshot(path)
            logger.info(f"截图已保存: {path}")
            notes.append(f"上电{on_result}")

            if d(text="AirInsight Box").exists:
                return "AirInsight Box"
            elif d(text="取消").exists:
                d(text="取消").click()
                logger.info(f"点击[取消]按钮")
            else:
                return "未连接"

        # 6. 等待"信号"出现
        logger.info("--- 等待信号出现 ---")
        signal_start = time.time()
        signal_ok = False
        while time.time() - signal_start < config.TIMEOUT_SIGNAL:
            try:
                if d(resourceId=config.ELEMENT_SIGNAL).exists:
                    signal_time = time.time() - signal_start
                    logger.info(f"信号已出现，耗时 {signal_time:.1f}s")
                    signal_ok = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not signal_ok:
            signal_time = config.TIMEOUT_SIGNAL
            logger.warn(f"信号在{config.TIMEOUT_SIGNAL}s内未出现")
            path = os.path.join(img_dir, f"no_signal_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            d.screenshot(path)
            logger.info(f"截图已保存: {path}")
            notes.append("信号未出现")

            if d(text="AirInsight Box").exists:
                    return "AirInsight Box"
            elif d(text="取消").exists:
                d(text="取消").click()
                logger.info(f"点击[取消]按钮")
            else:
                return "未连接"

        # 7. 判断默认识别的SIM卡
        logger.info("--- 判断默认识别 ---")
        result = "跳过（无信号）"
        if signal_ok:
            try:
                layout = d(resourceId=config.ELEMENT_SLOT1_LAYOUT)
                if layout.exists:
                    linear = layout.child(className="android.widget.LinearLayout")
                    if linear.exists:
                        has_unicom = linear.child(resourceId=config.ELEMENT_OPERATOR_UNICOM).exists
                        has_telecom = linear.child(resourceId=config.ELEMENT_OPERATOR_TELECOM).exists
                        has_mobile = linear.child(resourceId=config.ELEMENT_OPERATOR_MOBILE).exists
                        logger.info(f"卡槽检测 -> 联通:{has_unicom} 电信:{has_telecom} 移动:{has_mobile}")

                        if has_unicom and has_telecom and has_mobile:
                            result = "卡1"
                        elif has_unicom and not has_telecom and not has_mobile:
                            result = "卡2（实为卡2）"
                        else:
                            result = f"未知（联通:{has_unicom} 电信:{has_telecom} 移动:{has_mobile}）"
                    else:
                        result = "未知（无LinearLayout）"
                else:
                    result = "未知（无卡槽控件）"
            except Exception as e:
                logger.error(f"SIM检测异常: {e}")
                result = f"异常:{e}"

        if "卡1" in result:
            success_cnt += 1

        # 8. 截图
        ts_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_tag = result.replace("（", "(").replace("）", ")").replace(":", "_").replace(" ", "")
        img_path = os.path.join(img_dir, f"cycle{cycle}_{safe_tag}_{ts_now}.png")
        d.screenshot(img_path)
        logger.info(f"截图已保存: {img_path}")

        # 9. 写入CSV
        csv_reporter.write_row([
            cycle, off_result, on_result,
            round(disconnect_time, 1) if isinstance(disconnect_time, float) else "超时",
            round(signal_time, 1) if isinstance(signal_time, float) else "超时",
            result, "; ".join(notes)
        ])
        logger.info(f"CSV记录已写入: 第{cycle}次")

        # 10. 输出当次结果
        if "卡1" in result:
            logger.info(f"✓ 第{cycle}次: 默认识别正确 -> {result}")
        elif "卡2" in result:
            logger.info(f"⚠ 第{cycle}次: 默认识别异常 -> {result}")
        else:
            logger.info(f"✗ 第{cycle}次: 检测失败 -> {result}")

        # 11. 等待稳定
        if cycle < cycle_times:
            logger.info(f"等待 {config.WAIT_STABLE}s 稳定...")
            time.sleep(config.WAIT_STABLE)

    rate = (success_cnt / cycle_times * 100) if cycle_times else 0
    logger.info(f"\n{'='*50}")
    logger.info(f"完成 | 识别正确: {success_cnt}/{cycle_times} | 正确率: {rate:.1f}%")
    logger.info(f"CSV文件: {csv_reporter.path}")
    logger.info(f"{'='*50}")

    if args.marker:
        marker_data = {
            "timestamp": ts,
            "csv_path": csv_reporter.path,
            "log_dir": log_dir,
            "img_dir": img_dir,
            "cycle_times": cycle_times,
            "success_cnt": success_cnt,
            "rate": rate
        }
        with open(args.marker, "w", encoding="utf-8") as f:
            json.dump(marker_data, f, ensure_ascii=False)
        print(f"\n=== MARKER_OK: {args.marker} ===")


if __name__ == "__main__":
    main()
