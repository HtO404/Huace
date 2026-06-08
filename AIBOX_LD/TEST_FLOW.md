# AIBOX_LD 测试流程说明

## 整体流程图

```
程序启动
    │
    ├─→ 步骤1: 用户输入参数
    │      ├─ 循环执行次数
    │      └─ 导出次数(用于文件命名)
    │
    ├─→ 步骤2: 初始化测试环境
    │      ├─ 读取 config.ini 配置
    │      ├─ 初始化日志管理器
    │      ├─ 初始化CSV报告器
    │      └─ 输出启动信息
    │
    ├─→ 步骤3: 检查ADB设备连接
    │      ├─ 执行 `adb devices` 命令
    │      ├─ 检查是否有设备连接
    │      ├─ 成功 → 进入下一步
    │      └─ 失败 → 程序退出
    │
    ├─→ 步骤4: 连接uiautomator2设备
    │      ├─ 根据设备序列号或默认设备连接
    │      ├─ 记录连接日志
    │      ├─ 保存启动截图 (debug_XXXXXX_test_start.png)
    │      ├─ 成功 → 进入主循环
    │      └─ 失败 → 程序退出
    │
    ├─→ 主循环 (执行N次)
    │      │
    │      └─→ 单次测试循环
    │              │
    │              ├─→ 遍历双击坐标点 (a点, b点)
    │              │       │
    │              │       ├─→ 步骤1: 获取双击前的LFP和角度
    │              │       │       ├─ OCR识别屏幕
    │              │       │       ├─ 提取LFP值
    │              │       │       ├─ 提取角度值
    │              │       │       └─ 记录初始值
    │              │       │
    │              │       ├─→ 步骤2: 执行双击操作
    │              │       │       ├─ 保存双击前截图 (debug_XXXXXX_before_click_a.png)
    │              │       │       ├─ 第1次单击
    │              │       │       ├─ 等待100ms
    │              │       │       ├─ 第2次单击
    │              │       │       └─ 保存双击后截图 (debug_XXXXXX_after_click_a.png)
    │              │       │
    │              │       ├─→ 步骤3: 等待值变化 (60秒超时)
    │              │       │       ├─ 轮询OCR识别结果
    │              │       │       ├─ 检测LFP或角度变化
    │              │       │       ├─ 变化 → 进入成功处理
    │              │       │       └─ 超时 → 进入超时处理
    │              │       │
    │              │       ├─→ 成功处理
    │              │       │       ├─ 记录变化详情
    │              │       │       ├─ 写入CSV报告
    │              │       │       └─ 成功计数+1
    │              │       │
    │              │       ├─→ 超时处理
    │              │       │       ├─ 获取当前值
    │              │       │       ├─ 记录超时日志
    │              │       │       ├─ 保存超时截图 (debug_XXXXXX_timeout_a.png)
    │              │       │       ├─ 写入CSV报告
    │              │       │       └─ 失败计数+1
    │              │       │
    │              │       ├─→ 操作计数+1
    │              │       │
    │              │       ├─→ 判断是否需要复位
    │              │       │       └─ 操作数 % 10 == 0 → 执行找平镜头复位
    │              │       │
    │              │       └─→ 等待1秒后继续
    │              │
    │              └─→ 判断是否继续循环
    │                      ├─ 未到最后一次 → 等待wait_interval秒后继续
    │                      └─ 最后一次 → 退出循环
    │
    └─→ 输出测试结果统计
           ├─ 总次数
           ├─ 成功次数
           ├─ 失败次数
           ├─ 成功率
           ├─ 累计操作次数
           └─ 复位操作次数
```

## 关键步骤详细说明

### 1. 设备连接阶段

**控制台日志标记**: `[连接]`、`[启动]`

**关键操作**:
1. 使用 `adb devices` 检查设备连接状态
2. 使用 `u2.connect()` 或 `u2.connect(serial)` 连接设备
3. 保存启动截图

**调试截图**: `debug_XXXXXX_test_start.png`

---

### 2. 双击操作阶段

**控制台日志标记**: `[点击]`、`[流程]`

**关键操作**:
1. 保存双击前截图
2. 第1次单击
3. 等待100ms
4. 第2次单击
5. 保存双击后截图

**调试截图**:
- `debug_XXXXXX_before_click_a.png` (a点双击前)
- `debug_XXXXXX_after_click_a.png` (a点双击后)
- `debug_XXXXXX_before_click_b.png` (b点双击前)
- `debug_XXXXXX_after_click_b.png` (b点双击后)

---

### 3. OCR识别阶段

**控制台日志标记**: `[OCR]`

**关键操作**:
1. 截取屏幕指定区域
2. 增强图像对比度（2.0倍）
3. 使用 Tesseract OCR 识别文字
4. 正则表达式提取:
   - LFP值: `LFP[:\s]*([\d.]+)`
   - 角度值: `(-?\d+)°`

---

### 4. 超时处理阶段

**控制台日志标记**: `[超时]`

**关键操作**:
1. 获取当前LFP和角度值
2. 记录超时日志
3. 保存超时截图
4. 写入CSV报告（状态: "超时"）

**调试截图**: `debug_XXXXXX_timeout_a.png`、`debug_XXXXXX_timeout_b.png`

---

### 5. 找平镜头复位

**控制台日志标记**: `[流程]`

**触发条件**: 累计操作次数 % 10 == 0

**关键操作**:
1. 点击 cbOrientation 控件
2. 等待3秒
3. 点击 btnHome 控件

---

## 配置文件说明 (config.ini)

### [AppConfig]
- `project_name`: 项目名称
- `root_path`: 输出根目录（相对路径）

### [TestParams]
- `device_serial`: 设备序列号（为空则连接默认设备）
- `cycle_times`: 循环次数
- `wait_interval`: 操作间隔(秒)
- `click_coords`: 双击坐标列表 (x1,y1,x2,y2,...)

### [UIElements]
- `lfp_bounds`: LFP值范围坐标 (x1,y1,x2,y2)

### [OCRConfig]
- `tesseract_path`: Tesseract OCR路径
- `contrast_enhance`: 图像增强对比度系数
- `ocr_language`: OCR语言
- `timeout`: 超时时间(秒)

### [ResetConfig]
- `cb_orientation_id`: 找平镜头控件ID
- `btn_home_id`: 返回主页控件ID
- `max_retries`: 最大重试次数
- `reset_wait_interval`: 复位操作间隔(秒)
- `operation_threshold`: 操作计数阈值

---

## 调试技巧

### 1. 检查设备连接
如果卡在设备连接阶段，先手动执行:
```bash
adb devices
```
确认设备已连接。

### 2. 检查截图
所有关键步骤都会保存截图，查看截图可以了解:
- 设备连接后屏幕状态
- 双击操作前屏幕状态
- 双击操作后屏幕状态
- 超时发生时屏幕状态

### 3. 查看控制台日志
控制台会输出详细的流程日志，包括:
- `[启动]`: 启动信息
- `[连接]`: 设备连接信息
- `[流程]`: 测试流程步骤
- `[点击]`: 双击操作详情
- `[OCR]`: OCR识别结果
- `[成功]`: 成功状态
- `[超时]`: 超时状态
- `[完成]`: 完成统计

### 4. 检查坐标是否正确
如果点击没反应，可能是坐标不正确。可以:
1. 查看 `debug_XXXXXX_before_click_*.png` 截图
2. 确认点击坐标在有效区域内
3. 调整 `config.ini` 中的 `click_coords`

---

## 常见问题排查

### Q: 设备屏幕没反应？
**排查步骤**:
1. 查看控制台日志，确认已执行双击操作
2. 检查 `debug_XXXXXX_before_click_*.png` 和 `debug_XXXXXX_after_click_*.png`
3. 确认点击坐标是否在有效区域内
4. 确认设备屏幕未锁定

### Q: OCR识别不到值？
**排查步骤**:
1. 查看控制台 `[OCR]` 输出
2. 检查 `config.ini` 中的 `lfp_bounds` 坐标是否正确
3. 调整 `contrast_enhance` 对比度增强系数
4. 确认 Tesseract OCR 已正确安装

### Q: 总是超时？
**排查步骤**:
1. 查看超时截图 `debug_XXXXXX_timeout_*.png`
2. 确认双击操作是否真的触发了LFP值变化
3. 检查OCR识别区域是否正确
4. 考虑增加超时时间

---

## 文件输出

### 日志文件
位置: `AIBOX_LD_log/YYYY_MMdd_XX_AIBOX_LD_log.txt`
内容: 所有日志记录，带时间戳

### CSV报告
位置: `AIBOX_LD_csv/YYYY_MMdd_XX.csv`
内容: 测试结果，包含时间、序号、坐标点、LFP值、角度值、耗时、状态

### 调试截图
位置: 当前工作目录
命名: `debug_YYYYMMdd_HHmmss_mark.png`
用途: 关键步骤的屏幕截图，用于调试
