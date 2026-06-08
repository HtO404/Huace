---
name: superpower
description: 分析 Hcode 下所有脚本的重复模式，抽离通用模块，减少重复造轮子
runAs: subagent
---

## superpower — 代码去重 + 通用模块抽离

将项目中高度重复的样板代码识别并抽离为共享模块。

### 执行流程

1. **浏览项目** — 列出根目录所有项目文件夹（ls8_*、AIBOX_*、Ls8_*、Leida_* 等）
2. **识别重复模式** — 逐一检查每个项目的 main.py / utils.py，找出以下常见重复代码：
   - `setup_logging()` — 日志配置（FileHandler + StreamHandler）
   - `get_export_path()` — CSV + log 路径生成
   - `load_config()` — config.ini 加载
   - CSV 表头写入 / 行追加 / 汇总统计
   - 测试循环结构（for + try/except + 统计）
3. **分析用户编码习惯** — 查看 `我的编码习惯总结.md` 确认命名、格式、编码偏好
4. **产出通用模块** — 在项目根目录创建共享 `.py` 文件（如 `log_up.py`），包含上述函数
5. **更新编码习惯文档** — 在模板中改为 `from log_up import ...`
6. **输出报告** — 列出已识别的重复代码量和简化后的代码对比
