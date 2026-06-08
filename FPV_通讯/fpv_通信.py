import sys
import time
import subprocess
import logging
from datetime import datetime
from typing import List, Dict
import serial

sys.path.insert(0, r"d:\Hcode")
from log_up import setup_logging, get_export_path, write_csv_row, init_csv, \
    log_test_start, log_test_cycle, log_step, log_summary


class DevicePowerCycleTester:
    """
    设备批量上下电+连通性自动化测试类
    功能：统一控制设备上下电+下电有效性检测+上电有效性检测、循环测试、ping连通性校验
    日志：完整记录+实时显示累计成功/失败次数，上下电状态均记录，Windows系统完美适配
    """
    # 待测试的4个设备固定IP

    # DEVICE_IPS = ["192.168.0.54"]
    def __init__(self, cycle_times: int,
                 power_off_delay: int, power_on_delay: int,
                 ping_count: int, ping_timeout: int,
                 connection_string: str):
        self.DEVICE_IPS = [ "192.168.0.52"]
        self.CYCLE_TIMES = cycle_times
        self.POWER_OFF_DELAY = power_off_delay
        self.POWER_ON_DELAY = power_on_delay
        self.PING_COUNT = ping_count
        self.PING_TIMEOUT = ping_timeout
        self.connection_string = connection_string

        self.success_total: Dict[str, int] = {ip: 0 for ip in self.DEVICE_IPS}
        self.test_total = self.CYCLE_TIMES

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path, log_path = get_export_path(
            root_path=r"d:\Hcode\FPV_通讯\output",
            project_name="fpv",
            export_num=1,
            date_str=ts
        )
        self.csv_path = csv_path
        self.log_path = log_path

        init_csv(self.csv_path)

        setup_logging(self.log_path)

    def power_rs232(self, state: str) -> str:
        port_name = self.connection_string
        baud_rate = 9600  # 常见值：9600, 19200, 38400...
        data_bits = 8
        stop_bits = 1
        parity = serial.PARITY_NONE  # 常见值：PARITY_NONE, PARITY_EVEN

        if state == 'on':
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 FF F1 D1')
        else:
            message_to_send = bytes.fromhex('FE 0F 00 00 00 08 01 00 B1 91')

        try:
            # 创建并配置串口连接
            # 重要：timeout参数用于设置读超时，防止程序挂起
            with serial.Serial(port=port_name,
                               baudrate=baud_rate,
                               bytesize=data_bits,
                               stopbits=stop_bits,
                               parity=parity,
                               timeout=1.0) as ser:  # 1秒超时

                # logger.info(f"连接串口 {ser.name} 成功")

                # 清空输入输出缓冲区，避免旧数据干扰
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                logging.info(f"发送报文: {message_to_send.hex(' ').upper()}")
                ser.write(message_to_send)
                logging.info("报文发送完毕，等待响应...")
                time.sleep(0.2)
                response = ser.read_all()

                if response.hex().upper() == 'FE0F000000084002':
                    return 'pass'
                else:
                    return response.hex().upper()

        except serial.SerialException as e:
            logging.error(f"串口错误: {e}")
            return 'fail'
        except Exception as e:
            logging.error(f"发生错误: {e}")
            return 'fail'

    def _ping_device(self, ip: str) -> bool:
        """
        私有方法：Windows系统专用ping连通性检测，核心校验逻辑
        :param ip: 设备IP地址
        :return: True=ping通，False=ping不通
        """
        ping_cmd = [
            "ping", "-n", str(self.PING_COUNT),
            "-w", str(self.PING_TIMEOUT * 1000),
            "-4", ip
        ]
        start_time = time.time()
        for i in range(10):
            result = subprocess.run(
                ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                encoding="gbk"  # Windows系统cmd默认编码，防止中文乱码
            )
            if result.returncode == 0:
                total_time = round(time.time() - start_time, 2)
                logging.info(f'√ 设备{ip}通信耗时为：{total_time}s')
                return True
            else:
                time.sleep(3)

        total_time = round(time.time() - start_time, 2)
        logging.error(f'× 设备{ip}通信失败：{total_time}s')
        return False

    def _ping_device_off(self, ip: str) -> bool:
        """
        私有方法：Windows系统专用ping连通性检测，核心校验逻辑
        :param ip: 设备IP地址
        :return: True=ping通，False=ping不通
        """
        ping_cmd = [
            "ping", "-n", '2',
            "-w", '2000',
            "-4", ip
        ]
        result = subprocess.run(
            ping_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            encoding="gbk"  # Windows系统cmd默认编码，防止中文乱码
        )
        return result.returncode == 0

    def power_cycle_test(self):
        """
        核心公有方法：执行完整的上下电循环测试（闭环流程）
        完整流程：初始化日志 -> 循环100次 -> 下电操作 -> 下电等待 -> 【下电状态检测】-> 上电操作 -> 上电等待 -> 【上电状态检测】-> 记录统计
        """
        log_test_start("FPV设备上下电连通性测试", self.CYCLE_TIMES)
        logging.info(f"测试设备IP列表: {self.DEVICE_IPS}")
        logging.info(f"下电等待时间: {self.POWER_OFF_DELAY}s | 上电等待时间: {self.POWER_ON_DELAY}s")
        logging.info(f"Ping配置: 发送{self.PING_COUNT}个包，超时{self.PING_TIMEOUT}s")
        logging.info(f"判定标准：下电成功=PING不通 | 上电成功=PING通")

        for cycle_num in range(1, self.CYCLE_TIMES + 1):
            log_test_cycle(cycle_num)

            log_step(1, "下电")
            res = self.power_rs232('off')
            if res == 'pass':
                logging.info('电源已断电')
            else:
                logging.error(f'电源断电失败：{res}')
            time.sleep(self.POWER_OFF_DELAY)

            log_step(2, "下电状态检测（确保设备真正断电）")
            off_check_ok = True
            for ip in self.DEVICE_IPS:
                is_online = self._ping_device_off(ip)
                if is_online:
                    logging.error(f"❌ 设备{ip}下电失败 | 仍能PING通【异常】")
                    off_check_ok = False
                else:
                    logging.info(f"✅ 设备{ip}下电成功 | PING不通")

            log_step(3, "上电")
            res = self.power_rs232('on')
            if res == 'pass':
                logging.info('电源已打开')
            else:
                logging.error(f'电源打开失败：{res}')
            time.sleep(self.POWER_ON_DELAY)

            log_step(4, "上电状态检测")
            cycle_all_ok = True
            for ip in self.DEVICE_IPS:
                is_online = self._ping_device(ip)
                if is_online:
                    self.success_total[ip] += 1
                    curr_success = self.success_total[ip]
                    curr_fail = cycle_num - curr_success
                    logging.info(f"✅ 设备{ip} 上电成功 | PING通 | 累计成功:{curr_success} 累计失败:{curr_fail}")
                else:
                    cycle_all_ok = False
                    curr_success = self.success_total[ip]
                    curr_fail = cycle_num - curr_success
                    logging.error(f"❌ 设备{ip} 上电失败 | PING不通 | 累计成功:{curr_success} 累计失败:{curr_fail}")
                time.sleep(2)

            log_step(5, "CSV记录")
            on_success_ips = [ip for ip in self.DEVICE_IPS if self.success_total[ip] > 0]
            on_fail_ips = [ip for ip in self.DEVICE_IPS if self.success_total[ip] == 0]
            write_csv_row(self.csv_path, [
                cycle_num,
                '通过' if off_check_ok else '失败',
                '通过' if cycle_all_ok else '失败',
                f"上电成功={len(on_success_ips)}台",
                f"上电失败={len(on_fail_ips)}台",
                '全部通过' if cycle_all_ok else '有故障'
            ])

        log_step(6, "最终统计")
        logging.info("\n" + "=" * 60)
        logging.info("测试执行完毕")
        for ip in self.DEVICE_IPS:
            success_rate = round((self.success_total[ip] / self.test_total) * 100, 2)
            fail_num = self.test_total - self.success_total[ip]
            logging.info(
                f"设备 {ip} : 上电成功{self.success_total[ip]}次 | 上电失败{fail_num}次 | 成功率: {success_rate}%")

        log_summary(self.test_total,
                    sum(self.success_total.values()),
                    self.test_total * len(self.DEVICE_IPS) - sum(self.success_total.values()))

        from log_up import write_csv_summary
        total_all = self.test_total * len(self.DEVICE_IPS)
        success_all = sum(self.success_total.values())
        fail_all = total_all - success_all
        write_csv_summary(self.csv_path, total_all, success_all, fail_all, [
            ['CSV文件路径', self.csv_path],
            ['日志文件路径', self.log_path],
        ])
        print(f"\n=== CSV: {self.csv_path} ===")
        print(f"=== LOG: {self.log_path} ===")


# 程序入口：实例化类并执行测试
if __name__ == "__main__":
    print("=" * 50)
    print("FPV设备批量上下电连通性测试")
    print("=" * 50)

    ips_input = input("设备IP（逗号分隔，默认 192.168.0.52）：").strip()
    cycle_times = int(input("循环测试次数（默认2000）：") or "2000")
    power_off_delay = int(input("下电等待秒数（默认8）：") or "8")
    power_on_delay = int(input("上电等待秒数（默认5）：") or "5")
    ping_count = int(input("Ping发送包个数（默认5）：") or "5")
    ping_timeout = int(input("Ping超时秒数（默认3）：") or "3")
    connection_string = input(f"串口号（默认COM8）：").strip() or "COM8"

    print(f"\n配置: {device_ips} | {cycle_times}次 | 下电{power_off_delay}s | "
          f"上电{power_on_delay}s | Ping{ping_count}个 | {connection_string}\n")

    tester = DevicePowerCycleTester(
        cycle_times=cycle_times,
        power_off_delay=power_off_delay,
        power_on_delay=power_on_delay,
        ping_count=ping_count,
        ping_timeout=ping_timeout,
        connection_string=connection_string
    )
    tester.power_cycle_test()
