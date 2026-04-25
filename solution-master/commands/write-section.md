---
description: 撰写单个章节——根据计划、知识库素材和配图方案完成一个章节任务（通常由子智能体执行，主对话很少直接调用）。
---

用户运行了 `/solution-master:write-section $ARGUMENTS` —— 请激活 solution-master plugin 的 `solution-writing` skill 处理：

`$ARGUMENTS`

详细工作流见 `skills/solution-writing/SKILL.md`。

> ⚠ 通常通过子智能体调度（`/solution-master:subagent-write`）一次写多个章节；只有特殊场景（手工补章节、单测）才直接调本命令。
