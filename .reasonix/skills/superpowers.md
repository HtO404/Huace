---
name: superpowers
description: Superpowers 工作流总入口 — 告诉你想做什么，自动路由到对应子技能（brainstorming/debugging/planning/subagent-dev 等）
---

# Superpowers 工作流启动器

你说想做什么，我来帮你选对的工作流和技能。

## 第一步：了解需求

用一句话描述你现在想做什么。例如：

> "我想给项目加个新的 CLI 命令"
> "有个测试一直挂，我不知道为什么"
> "我有个设计稿，需要写实现计划"
> "代码写完了，准备提交"

## 路由逻辑

根据你的回答，我会自动选择最适合的流程：

| 你说的是… | 我用的是… |
|-----------|-----------|
| 做新功能/新组件/新模块 | → `superpowers-brainstorming`：需求探索 → 设计 → 批准 → 计划 |
| 修 bug / 测试挂了 / 出错了 | → `superpowers-systematic-debugging`：四阶段调试（根因→模式→假设→修复） |
| 有设计/需求文档，要写计划 | → `superpowers-writing-plans`：小粒度任务计划 + `submit_plan` |
| 有计划要执行/开始实现 | → `superpowers-subagent-dev`：逐任务实现 + 两阶段审查 |
| 代码写完了要收尾 | → `superpowers-verification` → `superpowers-requesting-code-review` → `superpowers-finishing-branch` |
| 多个独立问题要并行处理 | → `superpowers-parallel-agents` |
| 收到了别人的代码审查意见 | → `superpowers-receiving-code-review` |
| 想了解整套方法论 | → `superpowers-overview` |

## 执行

1. 先问用户想做什么（用 `ask_choice` 展示上述选项，或直接等用户说）
2. 根据回答，用 `run_skill` 调用对应的子技能
3. 如果用户说的内容跨越多个阶段（如"新功能做完了要提交"），按流程顺序依次调用

## 流程连锁

```markdown
用户说"我要做新功能"
  → run_skill("superpowers-brainstorming")   # 设计
    → 批准后 run_skill("superpowers-writing-plans")  # 计划
      → 批准后 run_skill("superpowers-subagent-dev") # 实现
        → 完成后 superpowers-verification → superpowers-requesting-code-review → superpowers-finishing-branch
```

每个技能完成后，检查是否应该自动进入下一个阶段。
