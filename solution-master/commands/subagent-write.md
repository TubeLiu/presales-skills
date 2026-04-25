---
description: 子智能体并行撰写——为撰写计划中的每个章节任务分派一个全新隔离的子智能体并行执行，避免主对话上下文污染。
---

用户运行了 `/solution-master:subagent-write $ARGUMENTS` —— 请激活 solution-master plugin 的 `subagent-driven-writing` skill 处理：

`$ARGUMENTS`

详细工作流见 `skills/subagent-driven-writing/SKILL.md`（前置：planning 已产出章节任务清单）。
