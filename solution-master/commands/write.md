---
description: Solution Master 主入口——开始撰写一份方案/解决方案文档。接受项目主题/需求作为 $ARGUMENTS，依次走 brainstorming → planning → subagent-driven-writing 三阶段。
---

用户运行了 `/solution-master:write $ARGUMENTS` —— 请按 Solution Master 框架启动方案撰写工作流。

**用户输入**：`$ARGUMENTS`

## 工作流（详见各 skill）

1. **铁律入口**（必须先做）：调用 `using-solution-master` skill 确立铁律清单。
2. **头脑风暴**：调用 `solution-brainstorming` skill 通过苏格拉底式提问把模糊需求转成完整方案设计规格说明。`$ARGUMENTS` 作为初始项目主题输入。
3. **拆解计划**：用户批准设计规格后，调用 `solution-planning` skill 将方案拆分成可执行的章节撰写任务。
4. **子智能体撰写**：调用 `solution-writing` / `subagent-driven-writing` skill 为每个章节分派独立子智能体撰写，每个章节完成后两阶段审查（`spec-reviewing` 内容正确性 → `quality-reviewing` 写作质量）。
5. **配图与导出**：通过 `image-gen`（ai-image plugin）/ `drawio-gen`（drawio plugin）配图；`docx-formatting` skill 输出标准格式 DOCX。

## 配置入口

- `/solution-config` — solution-master 专属配置（localkb / cdp_sites / docx 选项等）
- `/ai-image:setup` — AI 图片生成 API key 配置
- `/twc setup` — 招投标专属配置（如果同时使用 tender-workflow）

## 注意

- 所有 skill 加载顺序由 `using-solution-master` skill 中的铁律决定，不能跳过。
- 撰写任务必须用子智能体并行（`subagent-driven-writing`）以隔离上下文，不在主对话直接写章节。
