---
name: superpowers-requesting-code-review
description: 完成任务/实现大功能/准备 merge 之前使用 — 派发 review subagent 或 security-review subagent 在问题级联前捕获问题
---

# Superpowers Requesting Code Review — Reasonix Code 版

## 概述

在问题级联前捕获问题。审查者获得精确构造的上下文进行评估——不继承当前 session 的历史。

**核心原则：** Review early, review often。

## 何时请求审查

**必须：**
- 完成每个 subagent-dev 任务后
- 完成大功能后
- Merge 到 main 之前

**推荐：**
- 遇到阻塞时（新视角）
- 重构之前（基线检查）
- 修完复杂 bug 后

## 如何请求审查

### 方案 A：使用内置 review subagent（推荐）

Reasonix Code 内置了 `review` 和 `security-review` subagent 技能，专门做代码审查：

```
run_skill({
  name: "review",
  arguments: "审查 <分支/变更摘要>。重点关注：实现是否满足需求、代码质量、测试覆盖、潜在问题。"
})
```

对于涉及安全的变更：

```
run_skill({
  name: "security-review",
  arguments: "审查 <分支/变更摘要> 的安全方面。重点关注：注入、认证、授权、数据泄露。"
})
```

### 方案 B：获取 git diff 后自己审查

```bash
# 获取变更统计
git diff --stat HEAD~1..HEAD

# 获取完整 diff
git diff HEAD~1..HEAD
```

然后在当前 session 内逐文件 read_file + 分析。

## 审查检查单

**代码质量：**
- 清晰的职责分离？
- 正确的错误处理？
- DRY 原则？
- 边界情况处理了？

**架构：**
- 设计合理？
- 性能影响？
- 安全问题？

**测试：**
- 测试真正测逻辑（不是 mock 实现）？
- 边界情况覆盖？
- 所有测试通过？

**需求：**
- 所有计划需求都实现了？
- 没有 scope creep？
- Breaking changes 有文档？

## 处理反馈

| 严重级别 | 行动 |
|---------|------|
| Critical | 立即修复 |
| Important | 继续前修复 |
| Minor | 记录稍后处理 |
| 审查错误 | 用技术理由反驳 |

## Reasonix Code 工具映射

| 动作 | 工具 |
|------|------|
| 派发审查 subagent | `run_skill(name:"review")` 或 `run_skill(name:"security-review")` |
| 看 git 历史 | `run_command("git diff")` |
| 读具体文件 | `read_file` |
| 修复问题 | `edit_file`, `multi_edit` |
