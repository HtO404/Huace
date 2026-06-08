#!/bin/sh

DEVICE="/dev/ttyUSB2"
BAUDRATE="9600"
MAX_RETRIES=30
INTERVAL_TIME=1
NET_INTERFACE="wwan0"
LOG_FILE="/log/4g.log"  
DIAL_BIN="/data/sbin/fibocom-dial"  
IPTABLES_BIN="/usr/sbin/iptables"  

file_size_monitor()
{
    local file="$1"
    local MAX_SIZE=$((10 * 1024 * 1024))

    if [ -z "$file" ]; then
        echo "Error: no file specified"
        return 1
    fi

    if [ -f "$file" ]; then
        local size
        size=$(stat -c %s "$file")
        if [ "$size" -gt "$MAX_SIZE" ]; then
            mv "$file" "$file.bk"
            sync
        fi
    fi
}

file_size_monitor "$LOG_FILE"

exec >> "$LOG_FILE" 2>&1
# exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "\n\nStart 4g----------------------------------------"
echo "Date: $(date +"%Y-%m-%d %H:%M:%S")"

rm /etc/resolv.conf
touch /etc/resolv.conf
chmod 644 /etc/resolv.conf

count=0
found_dev=0
while [ $count -lt $MAX_RETRIES ]; do
    if [ -c "$DEVICE" ]; then
        echo "device $DEVICE is connected, start send at command..."
        found_dev=1
        break
    else
        echo "device $DEVICE not found, retry count:$count"
        sleep $INTERVAL_TIME
        count=$((count + 1))
    fi
done

if [ $found_dev -ne 1 ]; then
    echo "ERROR: device $DEVICE not found"
    exit 1
fi

stty -F $DEVICE $BAUD_RATE cs8 -cstopb -parenb
exec 3<> "$DEVICE"
timeout 1 cat <&3 > /dev/null

count=0
at_success=0
while [ $count -lt $MAX_RETRIES ]; do
    echo -e "AT\r\n" >&3
    RESPONSE=$(timeout 1 cat <&3)
    if echo "$RESPONSE" | grep -q "OK"; then
        echo "device $DEVICE at success"
        at_success=1
        break
    else
        echo "device $DEVICE at failed, retry count:$count"
        count=$((count + 1))
    fi
done

if [ $at_success -ne 1 ]; then
    echo "ERROR: device $DEVICE at failed"
    exec 3<&-
    exit 1
fi

count=0
mode_success=0
while [ $count -lt $MAX_RETRIES ]; do
    echo -e "AT+GTUSBMODE?\r\n" >&3
    RESPONSE=$(timeout 1 cat <&3)
    if echo "$RESPONSE" | grep -q "17"; then
        echo "device $DEVICE mode success"
        mode_success=1
        break
    else
        echo "device $DEVICE mode failed, retry count:$count"
        echo -e "AT+GTUSBMODE=17\r\n" >&3
        count=$((count + 1))
    fi
done

if [ $mode_success -ne 1 ]; then
    echo "ERROR: device $DEVICE mode failed"
    exec 3<&-
    exit 1
fi

exec 3<&-

echo "Start iptables config --------------------------"

# echo 1 > /proc/sys/net/ipv4/ip_forward
# $IPTABLES_BIN -F
# $IPTABLES_BIN -t nat -F
# $IPTABLES_BIN -t nat -A POSTROUTING -o $NET_INTERFACE -j MASQUERADE
# $IPTABLES_BIN  -A FORWARD -i wlan0 -o $NET_INTERFACE -j ACCEPT
# $IPTABLES_BIN  -A FORWARD -i $NET_INTERFACE -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "Start fibocom-dial------------------------------"
killall fibocom-dial
$DIAL_BIN &

count=0
net_interface_ready=0
while [ $count -lt $MAX_RETRIES ]; do
    if ip link show $NET_INTERFACE &>/dev/null; then
        echo "Found network interface: $NET_INTERFACE"
        net_interface_ready=1
        break
    else
        echo "$NET_INTERFACE not found, retry count:$count"
        sleep "$INTERVAL_TIME"
        count=$((count + 1))
    fi
done

if [ "$net_interface_ready" -ne 1 ]; then
    echo "ERROR: $NET_INTERFACE not found"
    exit 1
fi

exit 0
