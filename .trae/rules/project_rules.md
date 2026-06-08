# 项目规则 - 识别默认SIM卡测试分析

## 测试输出目录结构
```
output/
├── csv/        # 测试结果CSV（sim_test_YYYYMMDD_HHmmss.csv）
├── image/      # 每轮循环截图（cycleN_结果_时间戳.png + no_signal_N_时间戳.png）
│   └── thumb/  # 压缩后缩略图（发送飞书时使用）
└── logs/       # 日志文件（sim_YYYYMMDD_HHmmss.log）
```

## 分析输出要求
- 只做失败/异常的汇总，不分析图片内容
- 按日志文件分组，每条失败信息需包含：**时间戳 + 关键日志行** → 对应截图文件路径
- 飞书发送时，截图先压缩再上传（见下方图片压缩规则）
- 格式示例：`[14:20:42] Cycle 17 信号超时`

## 已知失败模式
| 失败类型 | 日志特征 | 截图命名规律 |
|---------|---------|-------------|
| 运营商全False | `卡槽检测 -> 联通:False 电信:False 移动:False` | `cycleN_未知(...).png` |
| 信号超时 | `[WARNING] 信号在100s内未出现` | `no_signal_N_时间戳.png` + `cycleN_跳过(无信号)_时间戳.png` |
| 信号耗时异常 | `信号已出现，耗时 >46s`（远高于正常44s） | `cycleN_卡1_时间戳.png` |
| 未连接耗时异常 | `未连接已出现，耗时 >1s`（远高于正常0.2~0.3s） | `cycleN_卡1_时间戳.png` |
| 测试中断 | 日志截断，无后续输出 | 无对应截图，CSV记录不完整 |

## 正常基准值
- 信号出现耗时：约 42~46s（超过此范围视为异常）
- 未连接出现耗时：约 0.2~0.5s（超过此范围视为异常）
- 上下电控制：始终应为"成功"

## 飞书发送配置
- App ID: `cli_aa8c6754bdbc5bee`
- open_id: `ou_0ef6162434b000480afe9b4bb4e65b89`
- 身份: `--as bot`
- 注意: App Secret 存储在 config.json 而非 keychain，避免 keychain 缓存问题

## 图片压缩规则
- 发送飞书前必须压缩，使用 `d:\Hcode\识别默认sim卡\resize.ps1`
- 用法: `powershell -ExecutionPolicy Bypass -File "d:\Hcode\识别默认sim卡\resize.ps1" -src <原图> -dst <输出路径>`
- 压缩参数: 宽度限制 800px，PNG 格式（保持清晰度）
- 效果: 平均缩减 ~60%（766KB → ~300KB）
- 原图保持不变，压缩图输出到 `output/image/thumb/` 目录

---

## 完整分析工作流（自动化执行）

当用户要求分析测试结果时，按以下步骤执行：

### Step 1: 扫描输出目录
```bash
# 列出 output/ 下所有文件，确认有哪些日志/CSV/截图
LS "d:\Hcode\识别默认sim卡\output\"  # 或直接用 Glob
```

### Step 2: 读取所有日志文件
```bash
# 读取每个 .log 文件全文，搜索以下关键模式：
# 1. [WARNING] 信号在100s内未出现        → 信号超时
# 2. 卡槽检测 -> 联通:False 电信:False ... → 运营商全False
# 3. 信号已出现，耗时 XXs                 → 统计异常耗时（>46s）
# 4. 未连接已出现，耗时 XXs               → 统计异常耗时（>1s）
# 5. 日志末尾是否完整                     → 判断测试中断
```
核心 grep 命令：
```powershell
# 找超时
Select-String -Path "output\logs\*.log" -Pattern "信号在\d+s内未出现|信号未出现|超时"

# 找运营商False
Select-String -Path "output\logs\*.log" -Pattern "卡槽检测.*False"

# 找信号耗时
Select-String -Path "output\logs\*.log" -Pattern "信号已出现，耗时"
```

### Step 3: 读取 CSV 交叉验证
CSV 列：`次数,下电结果,上电结果,未连接出现耗时(s),信号出现耗时(s),默认识别结果,备注`
- 找出"信号出现耗时(s)"列为"超时"的行
- 找出"默认识别结果"不是"卡1"的行（如"跳过（无信号）"、"未知"）
- 找出"未连接出现耗时(s)" > 1s 的行

### Step 4: 汇总输出（先展示给用户）
按日志文件分组，格式：
```
📄 日志1: sim_20260515_135741.log（完成 100 次）

  [14:20:42] Cycle 17 — 信号超时
  → no_signal_17_20260515_142033.png

  [15:07:03] Cycle 52 — 信号耗时异常 89.1s（正常 44s）
  → cycle52_卡1_20260515_150703.png
```

### Step 5: 发送飞书（用户确认后）
#### 5a. 找到需要发送的截图文件
```bash
Glob "**/no_signal_*.png" 或 Glob "**/cycle*异常*.png"
# 根据 Step 4 的失败记录，匹配对应的截图路径
```

#### 5b. 压缩截图
```powershell
cd "d:\Hcode\识别默认sim卡\output\image"
foreach ($f in @("no_signal_17_...png", "cycle52_...png", ...)) {
    powershell -ExecutionPolicy Bypass -File "d:\Hcode\识别默认sim卡\resize.ps1" -src $f -dst "thumb\$f"
}
```

#### 5c. 先发文字汇总
```powershell
# 内容写入临时 UTF-8 文件，避免 PowerShell 编码问题
$msgFile = "d:\Hcode\.trae\tmp_msg.txt"
# 用 Write 工具写入 UTF-8 内容
$msg = Get-Content $msgFile -Raw -Encoding UTF8
lark-cli im +messages-send --user-id ou_0ef6162434b000480afe9b4bb4e65b89 --text $msg --as bot
```

#### 5d. 再发截图（压缩版）
```powershell
cd "d:\Hcode\识别默认sim卡\output\image"
lark-cli im +messages-send --user-id ou_0ef6162434b000480afe9b4bb4e65b89 --image "thumb\no_signal_17_...png" --as bot
# 每张图单独一条消息（一次一张）
```

### Step 6: 清理
```powershell
Remove-Item "d:\Hcode\.trae\tmp_msg.txt" -ErrorAction SilentlyContinue
```

### 注意事项
- **不能一次发多张图**：`--image` 和 `--text` 互斥，每张图单独一条消息
- **中文不乱码**：文字内容先写入 UTF-8 文件，再用 `Get-Content -Raw -Encoding UTF8` 读取
- **必须先发文字再发图**：方便用户对照看
- **压缩速度**：6张图约 3-5 秒完成，无需等待太久

---

## 自动化测试流水线（全自动）

### 用法
用户说"跑 N 次测试"时，AI 自动执行完整流水线：
1. 启动测试（非交互模式）
2. 等待测试完成
3. 自动分析结果
4. 自动发送飞书（文字汇总 + 缩略图）

### 启动命令
```powershell
# 示例：100次，下电15秒，串口COM9
python "d:/Hcode/识别默认sim卡/main.py" `
  --cycle-times 100 `
  --interval-down 15 `
  --serial-port COM9 `
  --marker "d:/Hcode/识别默认sim卡/output/.last_test.json"
```

### --marker 标记文件
测试完成后自动写入 JSON 标记文件：
```json
{
  "timestamp": "20260515_170000",
  "csv_path": "D:/.../csv/sim_test_20260515_170000.csv",
  "log_dir": "D:/.../logs",
  "img_dir": "D:/.../image",
  "cycle_times": 100,
  "success_cnt": 95,
  "rate": 95.0
}
```

### AI 自动执行流程
1. **RunCommand** 启动 `python main.py --cycle-times N ... --marker ...`（blocking=true）
2. 等待进程退出（exit_code=0 表示完成）
3. 读取 `--marker` 指定的 JSON 文件获取 `csv_path`、`log_dir`、`img_dir`
4. 按 Step 2-4 分析日志 + CSV
5. 按 Step 5 压缩截图并发送飞书
6. **无需用户确认**（因为是用户主动要求跑的）

### main.py 改动说明
- 新增 `--cycle-times` / `--interval-down` / `--serial-port` / `--marker` 参数
- 不加参数仍走原交互模式（向后兼容）
- 修复了原代码中 2 处 `self.d` → `d` 的 bug

---

## 通用规则：所有 Python 脚本统一使用 log_up.py

### 强制要求
任何新脚本或改造现有脚本，**日志和导出必须调用 `d:\Hcode\log_up.py`**，禁止自己手写日志/CSV 逻辑。

### 标准引入方式
```python
import sys
sys.path.insert(0, r"d:\Hcode")
from log_up import setup_logging, get_export_path, write_csv_row, init_csv, \
    log_test_start, log_test_cycle, log_step, log_summary
```

### 标准用法模板
```python
# 1. 获取路径（自动创建目录）
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path, log_path = get_export_path(
    root_path=r"d:\Hcode\<项目文件夹>\output",
    project_name="<项目名>",
    export_num=1,
    date_str=ts
)

# 2. 初始化 CSV + 日志
init_csv(csv_path)
setup_logging(log_path)

# 3. 测试开始标记
log_test_start("项目名称", 循环次数)

# 4. 每次循环标记
log_test_cycle(cycle_num)

# 4b. 步骤标记（每次循环中划分步骤）
log_step(1, "下电")
log_step(2, "上电状态检测")
log_step(3, "上电")
log_step(4, "上电状态检测")

# 5. 记录行数据（自动加时间戳）
write_csv_row(csv_path, [字段1, 字段2, ...])

# 6. 汇总
log_summary(total, success, fail)
```

### 输出目录约定
```
<项目文件夹>/output/
├── <项目名>_csv/        # CSV 文件
└── <项目名>_log/        # 日志文件
```

---

## FPV 上下电测试脚本

### 文件位置
`d:\Hcode\FPV_通讯\fpv_通信.py`

### 交互模式
```powershell
python "d:/Hcode/FPV_通讯/fpv_通信.py"
```
运行后会依次提示输入所有参数。

### 非交互模式（自动化用）
```powershell
python "d:/Hcode/FPV_通讯/fpv_通信.py" ` 
  --cycle-times 100 ` 
  --power-off-delay 8 ` 
  --power-on-delay 5 ` 
  --ping-count 5 ` 
  --ping-timeout 3 ` 
  --serial-port COM8 ` 
  --device-ips "192.168.0.52,192.168.0.53"
```

### AI 自动执行（用户说"跑 FPV 测试"时）
1. `RunCommand` 启动非交互模式（blocking=true）
2. 等待完成
3. 自动读取输出目录中最新的 CSV + 日志
4. 分析失败记录
5. 发飞书通知

### 测试流程
```
下电(RS232) → 等待下电 → 下电检测(PING不通) → 上电(RS232) → 等待上电 → 上电检测(PING通) → CSV记录 → 循环
```

### 输出文件
- CSV: `output/fpv_csv/YYYYMMDD_01.csv`
- 日志: `output/fpv_log/YYYYMMDD_01_fpv_log.txt`
