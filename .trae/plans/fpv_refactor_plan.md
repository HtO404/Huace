# 改造计划：fpv_通信.py 优化

## 目标
1. 分析测试流程
2. 硬编码变量改成 input() 运行前输入
3. 集成 log_up.py 统一日志和导出
4. 修复流程中的 bug

## Step 1: 分析测试流程
- 梳理完整的上下电 + ping 检测闭环流程
- 文档化输出

## Step 2: 将硬编码变量改成 input()
- DEVICE_IPS → 逗号分隔输入
- CYCLE_TIMES → input
- POWER_OFF_DELAY → input
- POWER_ON_DELAY → input
- PING_COUNT → input
- PING_TIMEOUT → input
- connection_string → input（默认 COM8）

## Step 3: 集成 log_up.py
- 替换自建的 _write_log、无目录检查的日志逻辑
- 替换 CSV 导出（目前无 CSV，新增）
- 使用 setup_logging() + get_export_path() + write_csv_row()

## Step 4: 修复 bug 清单
- logs/ 目录未创建导致崩溃
- com8 → COM8（Windows 串口名规范）
- _ping_device_off() 未使用（下电检测被注释）
- 缺少 CSV 输出
- 类变量与实例变量混用混乱

## Step 5: 验证
- Python 语法检查
- --help 参数正常
