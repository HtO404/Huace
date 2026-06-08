---
name: superpowers-subagent-dev
description: 有实现计划且任务独立时使用 — 通过派发 subagent 按任务执行计划，每任务两阶段审查（规格合规→代码质量），适配 Reasonix Code 的 run_skill 机制
---

# Superpowers Subagent 开发 — Reasonix Code 版

## 概述

通过为每个任务派发独立 subagent 来执行计划，每个任务后进行两阶段审查。

**核心原则：** 每个任务新鲜 subagent + 两阶段审查（规格合规 → 代码质量）

## Reasonix Code 适配

Reasonix Code 用 `run_skill` 调用 subagent 技能。内置的 `explore`、`research`、`review`、`security-review` 都是 subagent 技能。

但 subagent-dev 的场景特殊：我们需要派发一个 subagent **去实现代码**（创建/修改文件、运行测试、commit），而不仅仅是读代码。Reasonix Code 当前没有通用的"实现 subagent"机制——因此**本技能由主 agent 在当前 session 中顺序执行**，利用 `todo_write` 跟踪进度，并调用 `review` subagent 或 `security-review` subagent 做审查。

## 流程

### 0. 初始化

```markdown
读取计划文件 → 提取所有任务
用 `todo_write` 创建任务追踪列表
```

### 1. 逐个执行任务

对每个任务：

#### a. 实现阶段

- 读计划中的任务详情
- `read_file` 读需要修改的文件
- 用 `edit_file` / `multi_edit` / `write_file` 做修改
- 运行测试验证

#### b. 规格合规审查（自己审查）

- 检查实现是否满足计划中的规格
- 每个需求都有对应实现吗？
- 发现问题 → 修复 → 重新验证

#### c. 代码质量审查（可选）

对于关键任务，调用内置 `review` subagent：

```
run_skill(name: "review", arguments: "审查刚刚对 <files> 的修改")
```

或 `security-review` 做安全审查。

#### d. 标记完成

用 `mark_step_complete`（如用 `submit_plan`）或用笔记标记。

### 2. 所有任务完成后

- 运行完整测试套件（`run_command`）
- 调用 `superpowers-verification` 验证
- 调用 `superpowers-requesting-code-review` 请求代码审查
- 调用 `superpowers-finishing-branch` 收尾

## 任务粒度指南

| 任务大小 | 示例 | 处理方式 |
|---------|------|---------|
| 小（1-2 文件） | 修一个函数 | 直接 edit_file 实现 |
| 中（3-5 文件） | 加一个新模块 | 用 todo_write 拆子步骤 |
| 大（5+ 文件） | 大功能 | 应考虑拆分到多个计划任务 |

## 内置 Subagent 技能参考

| 技能名 | 用途 | 何时调用 |
|--------|------|---------|
| `explore` | 只读探索 | 需要理解不熟悉的代码时 |
| `research` | 搜索+代码阅读 | 需要查外部资料时 |
| `review` | 审查变更 | 每个任务后的代码质量检查 |
| `security-review` | 安全审查 | 涉及敏感操作时 |
| `test` | 跑测试+修测试 | 需要自动化测试修复时 |

## Red Flags

**永远不要：**
- 跳过审查
- 有公开问题时继续下一个任务
- 在 main/master 分支上开始实现（没有主人明确同意）
- 同时执行多个可能冲突的任务
