---
name: superpowers-finishing-branch
description: 实现完成、测试通过、需要决定如何集成工作时使用 — 提供 merge/PR/保留/丢弃四个结构化选项，适配标准 git 工作流
---

# Superpowers Finishing Branch — Reasonix Code 版

## 概述

通过清晰的选项指导完成开发工作：验证测试 → 展示选项 → 执行选择 → 清理。

## 流程

### 步骤 1：验证测试

用 `run_command` 运行完整测试套件。

```
run_command("npm test / pytest / cargo test / go test ./...")
```

**如果测试失败：** 停止。不能继续。必须修复。

**如果测试通过：** 继续步骤 2。

### 步骤 2：确定基准分支

```bash
git merge-base HEAD main
# 或
git merge-base HEAD master
```

### 步骤 3：展示选项

用 `ask_choice` 展示 4 个选项：

> 实现完成。你想做什么？

- **A: Merge 回本地 main/master**
- **B: Push 并创建 Pull Request**
- **C: 保留分支（稍后处理）**
- **D: 丢弃这个工作**

### 步骤 4：执行选择

#### A: 本地 Merge

```bash
git checkout main && git pull
git merge feature-branch
# 验证合并后测试
run_command(<test-command>)
# 通过后
git branch -d feature-branch
```

#### B: Push 并创建 PR

```bash
git push -u origin feature-branch
# gh pr create 或手动
```

#### C: 保留

报告：`保留分支 <name>。当前在 <branch>。`

不要做额外清理。

#### D: 丢弃

先确认：用 `ask_choice` 或直接让主人确认。

```bash
git checkout main
git branch -D feature-branch
```

## 快速参考

| 选项 | Merge | Push | 保留分支 | 清理 |
|------|-------|------|---------|------|
| A. 本地 merge | ✅ | - | - | ✅ |
| B. 创建 PR | - | ✅ | ✅ | - |
| C. 保留 | - | - | ✅ | - |
| D. 丢弃 | - | - | - | ✅ |

## Reasonix Code 工具映射

| 动作 | 工具 |
|------|------|
| 运行测试 | `run_command` |
| 展示选项 | `ask_choice` |
| 执行 git 操作 | `run_command` |
