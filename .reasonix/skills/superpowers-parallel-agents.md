---
name: superpowers-parallel-agents
description: 面对 2+ 个独立任务（无共享状态）时使用 — 利用 Reasonix Code 的 subagent 技能并行派发多个子 agent 同时调查或执行
---

# Superpowers Parallel Agents — Reasonix Code 版

## 概述

当面临 2+ 个独立任务时，将它们分配给专门的并行 subagent，同时工作。

**核心原则：** 每个独立问题域分配一个 agent，让它们并发工作。

## Reasonix Code 适配

Reasonix Code 没有通用的 `sessions_spawn` 并行派发机制。但有两个实现方式：

### 方式 1：串行调用 subagent 技能（推荐）

分别独立调用 `run_skill`：

```markdown
1. `run_skill({ name: "explore", arguments: "调查 A 问题..." })` 
2. `run_skill({ name: "explore", arguments: "调查 B 问题..." })`
3. `run_skill({ name: "explore", arguments: "调查 C 问题..." })`
```

虽然是串行调用，但每个 subagent 独立运行，上下文隔离。适合 2-4 个独立调查任务。

### 方式 2：顺序执行 + 主 session 协调

由主 agent 在当前 session 中逐个处理每个问题域，但用 `todo_write` 追踪多个独立任务：

```markdown
todo_write: [
  { content: "修复测试文件 A", status: "in_progress" },
  { content: "修复测试文件 B", status: "pending" },
  { content: "修复测试文件 C", status: "pending" }
]
```

虽然不是真正的并行，但保持了关注点分离。

## 使用条件

```
有多个失败/独立任务？
  → 它们独立？（不同根因、无共享状态）
    → 可以独立处理
      → 用 parallel-agents（这个技能）
    → 顺序更合适
      → 逐一处理
  → 需要全面上下文理解
    → 单一 agent 处理
```

**适用场景：**
- 3+ 个测试文件失败，根因不同
- 多个子系统独立损坏
- 调查之间无共享状态

**不适用：**
- 失败互相关联（修一个可能修其他）
- Agents 会互相干扰（编辑同一文件）

## 流程

### 1. 识别独立问题域

按问题分组，确认每个域独立。

### 2. 为每个域创建专注任务

每个任务获得：
- **明确范围：** 一个测试文件或子系统
- **清晰目标：** 让这些测试通过 / 修复这个 bug
- **约束：** 不要改其他代码
- **预期输出：** 发现什么、修复什么的摘要

### 3. 派发 subagent

用 `run_skill({ name: "explore", arguments: "..." })` 派发调查任务。
或直接用 `search_content` + `read_file` 在当前 session 处理（如果任务不大）。

### 4. 审查和整合

当 subagents 返回（或当前 session 完成任务后）：
- 读每个摘要
- 验证修复不冲突
- `run_command` 运行完整测试套件

## Subagent 提示结构

```
Fix the 3 failing tests in src/components/A.test.ts:

1. "should handle empty state" - expects empty array but gets null
2. "should sort by date" - wrong sort order
3. "should filter by category" - filter not applied

Your task:
1. Read test file, understand each test
2. Identify root cause
3. Return what you found

Do not modify other files.
```

## 可用 subagent 技能

| 技能 | 适合场景 |
|------|---------|
| `explore` | 只读调查：理解代码、找根因 |
| `research` | 需要查外部资料+代码 |
| `review` | 审查已完成的工作 |
| `security-review` | 安全角度审查 |

## 常见错误

| 错误 | 修复 |
|------|------|
| 范围太广："修所有测试" | 具体："修 A.test.ts" |
| 无上下文：不粘贴错误信息 | 给具体错误和测试名 |
| 无约束：Agent 可能重构一切 | 加"不要改其他代码" |
| 输出模糊："修好了" | 要求"返回根因和变更摘要" |
