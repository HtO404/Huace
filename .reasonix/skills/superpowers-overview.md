---
name: superpowers-overview
description: 开始任何开发工作时使用，或不确定用哪个技能时 — 提供 Reasonix Code 版 Superpowers 方法论套件的入口和导航
---

# Superpowers 开发方法论 — Reasonix Code 版

## 这是什么

Superpowers 是一套为 AI coding agent 设计的**结构化开发方法论**，核心是：

> Agent 不应一上来就写代码，而应该先理解需求 → 设计方案 → 制定计划 → TDD 实现 → 审查代码 → 收尾。

本技能套件将 Superpowers 移植到 **Reasonix Code**，针对 `submit_plan`、`todo_write`、`ask_choice`、`run_skill`（subagent）等原生工具做了适配。

## 技能套件（11个）

### 🚀 入门

| 技能 | 何时用 | 做什么 |
|------|--------|--------|
| **superpowers-overview**（这个） | 不知道从哪里开始 | 查看套件全貌和入口 |
| **superpowers-brainstorming** | 做新功能/改东西之前 | 探索需求、提方案、获批准、写设计文档 |
| **superpowers-writing-plans** | 有了设计需要计划 | 写小粒度任务计划，每步 2-5 分钟 |

### 🔨 执行

| 技能 | 何时用 | 做什么 |
|------|--------|--------|
| **superpowers-subagent-dev** | 有实现计划，任务独立 | 派发 subagent 执行任务 + 两阶段审查 |
| **superpowers-parallel-agents** | 多个独立问题要并行处理 | 并行派发多个 subagent 同时工作 |
| **superpowers-systematic-debugging** | 遇到 bug/测试失败/意外行为 | 四阶段调试：根因→模式→假设→修复 |
| **superpowers-verification** | 声称任何"完成了"/"通过了"之前 | 强制证据先行，必须运行验证命令 |

### ✅ 质量保障

| 技能 | 何时用 | 做什么 |
|------|--------|--------|
| **superpowers-requesting-code-review** | 完成任务/重大功能/merge 之前 | 派发审查捕获问题 |
| **superpowers-receiving-code-review** | 收到代码审查反馈时 | 验证后实现，合理反驳 |
| **superpowers-finishing-branch** | 实现完成，测试通过，要收尾 | 展示 merge/PR/保留/丢弃选项 |

### 📖 元技能

| 技能 | 何时用 | 做什么 |
|------|--------|--------|
| **using-superpowers** | 任何对话开始时 | 建立"有技能先调用"的习惯，禁止绕过 |

## 开发流程图

```
用户请求新功能
        │
        ▼
┌───────────────────────────┐
│ superpowers-brainstorming  │
│ 探索需求 + 设计方案 + 批准  │
└───────────┬───────────────┘
            │ 主人批准设计
            ▼
┌───────────────────────────┐
│ superpowers-writing-plans  │
│ 写实现计划（小粒度任务清单） │
└───────────┬───────────────┘
            │
    ┌───────┴───────────────┐
    │    选择执行模式         │
    └───────┬───────────────┘
            │
    ┌───────┴────────────┐
    │                    │
    ▼                    ▼
┌────────────────┐  ┌─────────────────────┐
│ subagent-dev   │  │ 直接按 plan 执行     │
│（推荐）         │  │ submit_plan →        │
│ 每个任务派发     │  │ todo_write →         │
│ subagent + 审查 │  │ 逐任务实现            │
└───────┬────────┘  └──────────┬──────────┘
        │                     │
        └─────────┬───────────┘
                  │
                  ▼
        ┌────────────────────────┐
        │ superpowers-verification│
        │ 证据先行：跑测试确认通过  │
        └───────────┬────────────┘
                    │
                    ▼
        ┌────────────────────────────┐
        │ superpowers-requesting-    │
        │ code-review                │
        └───────────┬────────────────┘
                    │
                    ▼
        ┌────────────────────────────┐
        │ superpowers-finishing-branch│
        │ merge / PR / 保留 / 丢弃    │
        └────────────────────────────┘
```

## 日常使用决策

| 场景 | 流程 |
|------|------|
| **"我要做 X 功能"** | brainstorming → writing-plans → subagent-dev → verification → review → finishing |
| **"我要修 bug"** | systematic-debugging → verification |
| **"3 个测试独立失败"** | parallel-agents → 分别调查 → 整合 |
| **"代码写完了准备提交"** | verification → requesting-code-review → finishing-branch |

## 核心原则

1. **设计在实现之先** — 不要跳到代码
2. **证据在声称之前** — 运行验证，不只说"应该好了"
3. **根因在修复之先** — 不要猜，要调试
4. **测试在代码之先** — TDD，不是测试后补
5. **审查在集成之先** — 问题要早发现

## Reasonix Code 适配说明

| 原版概念 | Reasonix Code 对应 |
|---------|-------------------|
| `Skill` 工具 | `run_skill` / `/skill <name>` |
| `Task` 级联 | `run_skill(name)` 带 subagent 标记 |
| `TodoWrite` | `todo_write`（本机工具） |
| `submit_plan` | `submit_plan`（本机工具，含步骤追踪） |
| `ask_choice` | `ask_choice`（本机工具） |
| `sessions_spawn` | subagent 技能（`[🧬 subagent]`） |
| git worktree | git branches（标准分支） |
| 内置技能 | `explore`, `research`, `review`, `security-review`, `test` |
