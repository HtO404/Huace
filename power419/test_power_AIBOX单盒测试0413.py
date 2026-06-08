import time
import serial
import logging
import csv
from datetime import datetime
from pymavlink import mavutil
import sys
# 强制标准输出使用 utf-8，解决 Windows GBK 编码报错
sys.stdout.reconfigure(encoding='utf-8')

log_filename = time.strftime("test_power_%Y%m%d_%H%M%S.log")
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),  # 使用基于时间生成的文件名
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import pywifi

class DeviceStatusChecker:
    def __init__(self, device_serial):
        self.device_serial = device_serial
        self.d = None
        self.csv_filename = time.strftime(f"logs/test_power_%Y%m%d_%H%M%S.csv")
        self._init_csv()

    def _init_csv(self):
        """初始化CSV文件，写入表头"""
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['循环次数', '上电时间戳', '上电是否成功', '设备状态变化', '状态变化耗时(秒)', '下电是否成功',
                 '运行期间心跳总数', '运行期间心跳记录时间', '备注'])

    # 检查设备是否处于关闭状态（10秒内无心跳）
    def check_device_off(self, mavlink_com, timeout=10):
        """检查设备是否关闭：10秒内无心跳"""
        time.sleep(10)
        ser = mavutil.mavlink_connection(mavlink_com, baud=115200, source_system=10)
        start_time = time.time()
        last_msg_time = start_time
        
        while time.time() - start_time < timeout:
            msg = ser.recv_match(blocking=False)
            if msg:
                last_msg_time = time.time()
                logger.info(f"检测到心跳，设备可能未关闭")
                ser.close()
                return False
            time.sleep(1)
        
        ser.close()
        # 如果10秒内都没有收到心跳，认为设备已关闭
        if time.time() - last_msg_time >= timeout:
            logger.info(f"设备确认关闭（{timeout}秒内无心跳）")
            return True
        return False

    # 检查设备是否处于启动状态（连续收到20次心跳）
    def check_device_on(self, mavlink_com, required_heartbeats=10, timeout=180):
        """检查设备是否启动：连续收到20次心跳"""
        ser = mavutil.mavlink_connection(mavlink_com, baud=115200, source_system=10)
        start_time = time.time()
        heartbeat_count = 0
        first_heartbeat_time = None
        
        while time.time() - start_time < timeout:
            msg = ser.recv_match(blocking=False)
            if msg:
                if first_heartbeat_time is None:
                    first_heartbeat_time = time.time()
                    logger.info(f"开启aibox，瞬时心跳")
                heartbeat_count += 1
                logger.info(f"收到第{heartbeat_count}次心跳")
                
                if heartbeat_count >= required_heartbeats:
                    ser.close()
                    logger.info(f"设备确认启动（收到{heartbeat_count}次心跳）")
                    return True, time.time() - first_heartbeat_time
            
            time.sleep(1)
        
        ser.close()
        logger.info(f"设备启动失败（超时{timeout}秒，仅收到{heartbeat_count}次心跳）")
        return False, 0

    # 监控设备运行期间的心跳
    def monitor_heartbeats(self, mavlink_com, duration_hours=7200):
        """监控设备运行期间的心跳"""
        ser = mavutil.mavlink_connection(mavlink_com, baud=115200, source_system=10)
        duration_seconds = duration_hours
        start_time = time.time()
        heartbeat_count = 0
        heartbeat_timestamps = []
        
        logger.info(f"开始监控心跳，持续2小时")
        
        while time.time() - start_time < duration_seconds:
            msg = ser.recv_match(blocking=False)
            if msg:
                heartbeat_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                heartbeat_timestamps.append(current_time)
                
                if heartbeat_count % 60 == 0:  # 每60次心跳记录一次
                    logger.info(f"已收到{heartbeat_count}次心跳")
            
            time.sleep(1)
        
        ser.close()
        logger.info(f"心跳监控结束，共收到{heartbeat_count}次心跳")
        
        # 将时间戳列表转换为字符串
        timestamps_str = "; ".join(heartbeat_timestamps[:10])  # 只记录前10次时间戳
        if len(heartbeat_timestamps) > 10:
            timestamps_str += f"... (共{len(heartbeat_timestamps)}次)"
        
        return heartbeat_count, timestamps_str

    def check_status_change(self, mavlink_com, timeout=60):
        """
        检查设备状态变化，是否有心跳（兼容旧版本）
        """
        # 使用新的检查方法
        is_on, elapsed_time = self.check_device_on(mavlink_com, required_heartbeats=1, timeout=timeout)
        if is_on:
            logger.info(f"检测到心跳")
            return True, elapsed_time
        else:
            logger.info(f"没有检测到心跳")
            return False, timeout

    def record_to_csv(self, cycle_num, power_on_time, power_on_success, status_change, time_elapsed, power_off_success,
                      heartbeat_count=None, heartbeat_timestamps="", notes=""):
        """记录测试结果到CSV"""
        try:
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    cycle_num,
                    power_on_time,
                    power_on_success,
                    status_change,
                    round(time_elapsed, 2) if time_elapsed else '',
                    power_off_success,
                    heartbeat_count if heartbeat_count is not None else '',
                    heartbeat_timestamps,
                    notes
                ])
        except Exception as e:
            logger.error(f"写入CSV失败: {e}")


class PowerState:
    def __init__(self, timeout_up, duration, interval_down, connection_string, mavlink_com, device_serial):
        self.timeout_up = timeout_up  # 上电超时时间
        self.duration = duration
        self.interval_down = interval_down
        self.connection_string = connection_string
        self.device_serial = device_serial
        self.mavlink_com = mavlink_com

        self.up_power_time = 7200

        self.state = {
            'up': 0,
            'down': 0,
        }

        self.fail_up = []
        self.fail_down = []

        # 初始化设备状态检查器
        self.status_checker = DeviceStatusChecker(device_serial)

        logger.info(f'串口为：{self.connection_string}')
        logger.info(f'设备序列号：{self.device_serial}')
        logger.info(f'上电超时时间：{self.timeout_up}秒')
        logger.info(f'下电时间为：{self.interval_down}秒')
        logger.info(f'循环次数为：{self.duration}')
        logger.info(f'******************************************************')

    def power_rs232(self, state):
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

                # 发送报文
                logger.info(f"发送报文: {message_to_send.hex(' ').upper()}")
                ser.write(message_to_send)
                logger.info("报文发送完毕，等待响应...")
                time.sleep(0.2)  # 给设备一点反应时间，具体取决于波特率和帧长
                response = ser.read_all()  # 读取串口缓冲区中所有的数据

                if response.hex().upper() == 'FE0F000000084002':
                    return 'pass'
                else:
                    return response.hex().upper()

        except serial.SerialException as e:
            logger.info(f"串口错误: {e}")
            return 'fail'
        except Exception as e:
            logger.info(f"发生错误: {e}")
            return 'fail'

    def run_auto(self):
        # 开始循环
        for i in range(1, self.duration + 1):
            try:
                logger.info(f'第{i}次循环开始')
                
                # 初始化变量
                power_on_success = False
                power_off_success = False
                status_change = False
                status_change_time = 0
                heartbeat_count = 0
                heartbeat_timestamps = ""
                
                # 阶段1：上电操作和状态检查
                logger.info('=== 阶段1：上电操作 ===')

                # 1.1 上电前检查：确认设备是否关闭（10秒内无心跳）
                logger.info('上电前检查设备状态...')
                is_device_off = (self.status_checker.
                                 check_device_off(self.mavlink_com, timeout=10))
                
                if not is_device_off:
                    logger.warning('设备可能未完全关闭，尝试强制下电...')
                    # 如果设备未关闭，先执行下电操作
                    res = self.power_rs232('off')
                    if res == 'pass':
                        logger.info('强制下电成功，等待10秒...')
                        time.sleep(10)
                        # 再次检查设备是否关闭
                        is_device_off = self.status_checker.check_device_off(self.mavlink_com, timeout=10)
                    else:
                        logger.error('强制下电失败，跳过本次循环')
                        continue
                
                if is_device_off:
                    logger.info('设备确认关闭，开始上电操作')
                    
                    # 1.2 执行上电操作
                    power_on_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    res = self.power_rs232('on')
                    
                    if res == 'pass':
                        logger.info(f'第{i}次:电源已上电')
                        
                        # 1.3 上电后检查：等待设备启动（3分钟内连续收到20次心跳）
                        logger.info('等待设备启动...')
                        status_change, status_change_time = self.status_checker.check_device_on(
                            self.mavlink_com, required_heartbeats=20, timeout=200
                        )
                        wifi_aibox = self.wifi_state()
                        if not status_change:
                            print('心跳接收失败，二次检测wifi是否启动')
                            if wifi_aibox == 'on':
                                print('二次wifi启动成功')
                                status_change = True

                        if status_change:
                            logger.info(f'设备上电成功，启动耗时: {status_change_time:.2f}秒')
                            power_on_success = True
                            self.state['up'] += 1
                            
                            # 阶段2：设备运行期间监控（2小时）
                            logger.info('=== 阶段2：2小时心跳监控 ===')
                            heartbeat_count, heartbeat_timestamps = self.status_checker.monitor_heartbeats(
                                self.mavlink_com, duration_hours=self.up_power_time
                            )
                            
                            # 阶段3：下电操作和状态检查
                            logger.info('=== 阶段3：下电操作 ===')
                            
                            # 3.1 下电前检查：确认设备处于启动状态（连续收到20次心跳）
                            logger.info('下电前检查设备状态...')
                            is_device_on, _ = self.status_checker.check_device_on(
                                self.mavlink_com, required_heartbeats=20, timeout=180
                            )

                            res = self.power_rs232('off')
                            if is_device_on:
                                logger.info('设备确认启动，开始下电操作')
                                
                                # 3.2 执行下电操作
                                if res == 'pass':
                                    logger.info(f'第{i}次:电源已关闭')
                                    
                                    # 3.3 下电后检查：确认设备关闭（10秒内无心跳）
                                    logger.info('检查设备是否成功关闭...')
                                    is_device_off_after = self.status_checker.check_device_off(
                                        self.mavlink_com, timeout=10
                                    )
                                    
                                    if is_device_off_after:
                                        logger.info('设备确认关闭，下电成功')
                                        power_off_success = True
                                        self.state['down'] += 1
                                    else:
                                        logger.warning('设备可能未完全关闭')
                                        power_off_success = False
                                        self.fail_down.append(i)
                                else:
                                    logger.error(f'第{i}次:电源关闭失败：{res}')
                                    power_off_success = False
                                    self.fail_down.append(i)
                            else:
                                logger.error('设备未处于启动状态，跳过下电操作')

                                power_off_success = False
                                self.fail_down.append(i)

                        else:
                            logger.error('设备上电后启动失败')
                            power_on_success = False
                            self.fail_up.append(i)
                    else:
                        logger.error(f'第{i}次:电源上电失败：{res}')
                        power_on_success = False
                        self.fail_up.append(i)
                else:
                    logger.error('设备无法确认关闭状态，跳过本次循环')
                    power_on_success = False
                    power_off_success = False
                
                # 阶段4：等待2小时（下电状态）
                if power_off_success:
                    logger.info('=== 阶段4：等待2小时（下电状态） ===')
                    logger.info(f'等待{self.interval_down}秒后开始下一次循环...')
                    time.sleep(self.interval_down)
                else:
                    logger.warning('下电失败，跳过等待阶段')
                
                # 记录到CSV
                notes = ""
                if not power_on_success:
                    notes += "上电失败; "
                if not power_off_success:
                    notes += "下电失败; "
                if not status_change:
                    notes += "状态变化超时; "

                self.status_checker.record_to_csv(
                    cycle_num=i,
                    power_on_time=power_on_time,
                    power_on_success=power_on_success,
                    status_change=status_change,
                    time_elapsed=status_change_time,
                    power_off_success=power_off_success,
                    heartbeat_count=heartbeat_count,
                    heartbeat_timestamps=heartbeat_timestamps,
                    notes=notes.strip()
                )

                logger.info(f'第{i}次循环完成')
                logger.info('#' * 50)

            except Exception as e:
                logger.error(f'第{i}次循环发生异常: {e}')
                # 记录异常到CSV
                self.status_checker.record_to_csv(
                    cycle_num=i,
                    power_on_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    power_on_success=False,
                    status_change=False,
                    time_elapsed=0,
                    power_off_success=False,
                    heartbeat_count=0,
                    heartbeat_timestamps="异常中断",
                    notes=f"异常: {str(e)}"
                )

        logger.info(f'******************************************************')
        logger.info(f'测试完成')
        logger.info(f'上电成功次数：{self.state["up"]}')
        logger.info(f'下电成功次数：{self.state["down"]}')
        logger.info(f'上电失败轮次：{self.fail_up}')
        logger.info(f'下电失败轮次：{self.fail_down}')
        logger.info(f'CSV记录文件: {self.status_checker.csv_filename}')

    def scan_wifi_networks(self):
        """
        扫描并返回附近的 WiFi 网络列表
        """
        # 初始化 PyWiFi 对象
        wifi = pywifi.PyWiFi()
        # 获取第一个无线网卡接口（通常电脑只有一个）
        iface = wifi.interfaces()[0]
        # 开始扫描
        print("正在扫描附近的 WiFi 网络，请稍候...")
        iface.scan()
        # 等待扫描完成（扫描需要一定时间，建议等待 3-5 秒）
        time.sleep(5)

        # 获取扫描结果
        scan_results = iface.scan_results()

        # 用于存储去重后的 WiFi 信息（避免同一 SSID 重复显示）
        networks = {}

        for network in scan_results:
            ssid = network.ssid
            # 过滤掉隐藏的 WiFi（ssid 为空）
            if ssid:
                # 如果同一 SSID 有多个信号源，保留信号最强的
                if ssid not in networks or networks[ssid]['signal'] < network.signal:
                    networks[ssid] = {
                        'ssid': ssid,
                        'signal': network.signal,
                        'bssid': network.bssid,
                        'auth': network.akm  # 加密类型
                    }

        return networks

    def wifi_state(self):
        try:
            aibox = 'AIBOX-0892'
            wifi_list = self.scan_wifi_networks()
            wifi_name = []
            print("\n" + "=" * 50)
            print("序号\t信号强度(dBm)\tWiFi 名称")
            print("=" * 50)
            # 按信号强度排序（从强到弱）
            sorted_wifi = sorted(wifi_list.values(), key=lambda x: x['signal'], reverse=True)
            for idx, wifi in enumerate(sorted_wifi, 1):
                wifi_name.append(wifi['ssid'])
                print(f"{idx}\t{wifi['signal']}\t\t{wifi['ssid']}")
            logger.info("=" * 50)
            logger.info(f"共扫描到 {len(sorted_wifi)} 个 WiFi 网络")
            logger.info(f"——————开始检测aibox是否正常启动——————")
            if aibox in wifi_name:
                logger.info(f'----搜索到wifi:{aibox},aibox处于上电状态----')
                return 'on'
            else:
                logger.info(f'-----没有搜索到wifi:{aibox}，aibox处于断电状态----')
                return 'off'

        except Exception as e:
            print(f"扫描出错: {e}")
            print("提示：请确保已安装无线网卡驱动，并以管理员身份运行脚本[citation:3]")
            return 'error'

if __name__ == "__main__":
    duration = int(input("测试循环次数："))  # 测试循环次数
    timeout_up = 180  # 上电超时时间固定为3分钟
    interval_down = 7200  # 下电等待时间固定为2小时（7200秒）
    connection_string = input("继电器串口号：")  # 串口
    mavlink_com = input("mavlink心跳串口号：")  # 串口
    device_serial = input("设备序列号（adb devices查看）：")  # 设备序列号


    logger.info(f'测试配置：')
    logger.info(f'循环次数：{duration}')
    logger.info(f'上电超时时间：{timeout_up}秒（3分钟）')
    logger.info(f'下电等待时间：{interval_down}秒（2小时）')
    logger.info(f'运行监控时间：2小时')
    logger.info(f'总测试时间：约{duration * (2 + 2) / 24:.1f}天')

    data = PowerState(timeout_up, duration, interval_down, connection_string, mavlink_com,device_serial)
    data.run_auto()


