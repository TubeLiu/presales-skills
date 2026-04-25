---
name: solution-writing
description: 当有撰写计划中的具体章节任务需要执行时使用——根据计划、知识库素材和配图方案撰写方案章节
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__plugin_anythingllm-mcp_anythingllm__anythingllm_search, mcp__plugin_anythingllm-mcp_anythingllm__anythingllm_list_workspaces
---

# 方案撰写：执行章节任务

通过为每个章节任务分派一个全新的子智能体来执行撰写计划，每个任务完成后进行两阶段审查：先审查内容正确性，再审查写作质量。

**为什么用子智能体：** 将任务委派给具有隔离上下文的专用子智能体。它们不继承你的会话历史——你精确构造它们所需的一切。这避免了上下文污染，也为你保留协调工作的上下文。

**核心原则：** 每个任务一个全新子智能体 + 两阶段审查（先规格后质量）= 高质量方案产出

## 流程图

```dot
digraph solution_writing {
    rankdir=TB;
    node [fontname="SimHei"];

    subgraph cluster_per_task {
        label="每个章节任务";
        style=dashed;

        "分派知识检索" [shape=box, label="knowledge-retrieval\n多源检索+智能融合"];
        "分派配图规划" [shape=box, label="ai-image\n上下文感知选图"];
        "分派撰写子智能体" [shape=box, label="分派 writer 子智能体\n(agents/writer.md)"];
        "撰写子智能体有疑问?" [shape=diamond];
        "回答问题" [shape=box];
        "撰写子智能体完成撰写" [shape=box];
        "分派 spec-reviewer" [shape=box, label="分派 spec-reviewer\n(agents/spec-reviewer.md)"];
        "内容审查通过?" [shape=diamond];
        "修复内容问题" [shape=box];
        "分派 quality-reviewer" [shape=box, label="分派 quality-reviewer\n(agents/quality-reviewer.md)"];
        "质量审查通过?" [shape=diamond];
        "修复质量问题" [shape=box];
        "标记任务完成" [shape=box];

        "分派知识检索" -> "需要配图?";
        "需要配图?" [shape=diamond];
        "需要配图?" -> "分派配图规划" [label="是"];
        "需要配图?" -> "分派撰写子智能体" [label="否"];
        "分派配图规划" -> "分派撰写子智能体";
        "分派撰写子智能体" -> "撰写子智能体有疑问?";
        "撰写子智能体有疑问?" -> "回答问题" [label="是"];
        "回答问题" -> "分派撰写子智能体";
        "撰写子智能体有疑问?" -> "撰写子智能体完成撰写" [label="否"];
        "撰写子智能体完成撰写" -> "分派 spec-reviewer";
        "分派 spec-reviewer" -> "内容审查通过?";
        "内容审查通过?" -> "修复内容问题" [label="否"];
        "修复内容问题" -> "分派 spec-reviewer" [label="重审"];
        "内容审查通过?" -> "分派 quality-reviewer" [label="是"];
        "分派 quality-reviewer" -> "质量审查通过?";
        "质量审查通过?" -> "修复质量问题" [label="否"];
        "修复质量问题" -> "分派 quality-reviewer" [label="重审"];
        "质量审查通过?" -> "标记任务完成" [label="是"];
    }

    "读取计划，创建任务列表" [shape=box];
    "还有剩余任务?" [shape=diamond];
    "最终组装所有章节" [shape=box];
    "输出格式选择" [shape=box, label="docx-formatting\n（如需 DOCX）"];

    "读取计划，创建任务列表" -> "分派知识检索";
    "标记任务完成" -> "还有剩余任务?";
    "还有剩余任务?" -> "分派知识检索" [label="是"];
    "还有剩余任务?" -> "最终组装所有章节" [label="否"];
    "最终组装所有章节" -> "输出格式选择";
}
```

## 执行步骤

### Phase 0：输入校验

1. 读取撰写计划文件（`docs/specs/*-plan.md`）
2. 提取所有任务的完整文本
3. 创建任务跟踪列表（使用 TaskCreate）
4. 确认用户选择的输出格式（Markdown / DOCX）
5. **draw.io 可用性前置检查**：
   - drawio 技能已作为 solution-master 插件的一部分捆绑分发，**默认情况下始终可用**（plugin 模式经由插件 skill 自动发现，npx 模式经由 `.claude/skills/drawio/` 复制）
   - 如果用户明确自定义了 drawio 覆盖（例如 `/solution-config` 安装了本地版本），检测顺序为：
     ```python
     python3 -c "
     from pathlib import Path
     # drawio 已捆绑在 solution-master 插件中，默认可用
     # 此处仅检测用户是否提供了本地覆盖版本
     overrides = [
         Path('.claude/skills/drawio/SKILL.md'),          # npx 项目模式覆盖
         Path.home() / '.claude/skills/drawio/SKILL.md',  # 全局覆盖
     ]
     for p in overrides:
         if p.exists():
             print(f'INSTALLED: override at {p}')
             exit()
     print('INSTALLED: bundled with solution-master')
     "
     ```
   - 因为 drawio 必定可用，Phase 0 不会再触发"未安装"警告。若未来 solution-master 的分发形态改变、drawio 变成可选依赖，再补充降级警告逻辑

### Phase 1：知识检索 + 配图规划（每个任务）

1. 调用 knowledge-retrieval 技能，传入任务的 KB 检索关键词
2. **检查任务的"配图需求"字段**：
   - 如果配图需求明确表示需要图片（即字段值不是"无"、"无需配图"、"无配图需求"、"N/A"等否定性表述），**必须**调用 ai-image plugin 的 `image-gen` 命令
   - `image-gen` 产出一个"配图方案"（每张图的描述 + 图片路径或占位符）
   - 如果 `image-gen` 调用失败（如 API 不可用），配图方案中使用标准占位符格式，不阻塞撰写流程
   - 如果配图需求明确为"无"或等价否定表述，跳过此步骤
3. 收集检索结果和配图方案（如有）

<HARD-GATE>
如果任务的"配图需求"字段表示需要图片（非"无"、"无需配图"、"无配图需求"、"N/A"），且未调用 ai-image plugin 的 `image-gen` 命令，则不得进入 Phase 2（分派撰写子智能体）。
</HARD-GATE>

**配图方案产出格式**（传给 writer 子智能体）：
```
配图方案：
- H3 "xxx"：需要架构图 → ![图 1.1-1：xxx架构设计](../output/images/xxx.png) 或 [图片占位符 — xxx架构设计：请手动插入图片]
- H3 "yyy"：需要流程图 → [图片占位符 — yyy业务流程：请手动插入图片]
- H3 "zzz"：无需配图
```

**图片路径规范：** 草稿文件保存在 `drafts/` 目录，图片保存在 `output/images/` 目录。因此配图方案中的图片路径必须使用 `../output/images/xxx.png` 格式（相对于 `drafts/` 目录）。**禁止**使用 `output/images/xxx.png`（这是相对于项目根目录的路径，从 `drafts/` 下的文件无法正确引用）。

writer 子智能体必须将上述每个图片引用/占位符插入到对应段落后，不可省略。

### Phase 2：分派撰写子智能体

构造子智能体提示，包含：
- 任务完整文本（直接粘贴，不是文件引用）
- 方案上下文（这个任务在整体方案中的位置）
- 知识库检索结果（Phase 1 产出）
- 配图方案（Phase 1 产出）
- 输出格式要求

子智能体返回状态：
- **DONE** → 进入审查
- **DONE_WITH_CONCERNS** → 读取疑虑后进入审查
- **NEEDS_CONTEXT** → 补充信息后重新分派
- **BLOCKED** → 上报用户

### Phase 3：两阶段审查

**审查反馈展示原则：每次审查完成后，必须将审查报告的关键内容展示给用户。**

**第一阶段：内容正确性审查（spec-reviewing）**
- 分派独立 spec-reviewer 子智能体
- 传入：计划中的任务要求 + 实际撰写产出
- 审查完成后 → **向用户展示审查结果**（PASS/FAIL + 问题列表）
- 结果 PASS → 进入第二阶段
- 结果 FAIL → 向用户展示问题和修复建议 → 撰写子智能体修复 → 重新审查

**第二阶段：写作质量审查（quality-reviewing）**
- 分派独立 quality-reviewer 子智能体
- 传入：实际撰写产出
- 审查完成后 → **向用户展示审查结果**（评分 + 关键发现）
- 结果 PASS → 任务完成
- 结果 FAIL → 向用户展示问题和修复建议 → 撰写子智能体修复 → 重新审查

**展示格式**：
```
📋 内容审查：✅ PASS（或 ❌ FAIL）
  - [通过项摘要]
  - [问题项及修复建议（如有）]

📋 质量审查：✅ PASS（评分 A/B）（或 ❌ FAIL 评分 C/D）
  - [优点]
  - [问题项及修复建议（如有）]
```

### Phase 4：最终组装

所有任务完成后：
1. 按章节顺序组装所有草稿，Markdown 完整方案保存到 `output/` 目录（如 `output/方案名称.md`）
2. **重写图片路径**：草稿中的 `../output/images/xxx` 在组装后需改为 `output/images/xxx`（项目根目录相对路径）。用全局替换 `](../output/images/` → `](output/images/` 即可。**说明**：虽然组装文件在 `output/` 下，但主流 IDE（VS Code 等）以项目根目录为基准解析 Markdown 图片路径，因此使用项目根相对路径确保预览正确
3. 检查章节间衔接
4. 生成目录
5. 如需 DOCX 输出，调用 docx-formatting 技能。DOCX 文件同样保存到 `output/` 目录

## 子智能体提示模板

分派撰写子智能体时使用以下结构（详见 `subagent-driven-writing/writer-prompt.md`）：

```
你是一个方案撰写子智能体。请参考 agents/writer.md 中的角色定义。

## 你的任务

[粘贴任务完整文本]

## 方案上下文

[方案名称、整体结构、当前章节在整体中的位置]

## 知识库素材

[knowledge-retrieval 的检索结果完整粘贴]

## 配图方案

[ai-image (image-gen) 的配图方案，如本任务无配图需求则写"本任务无配图需求"]

## 输出要求

- 格式：Markdown
- 保存到：drafts/[章节编号]_[章节名称].md
- 图片路径：使用 ../output/images/xxx.png 格式（相对于 drafts/ 目录），禁止使用 output/images/xxx.png
- 来源标注：正文中禁止出现任何来源标注（如"（出处：Web — xxx）"、"（来源：xxx）"等括号标注）。知识库素材的内容可以使用，但不要在正文中暴露检索来源
- 完成后以 subagent-driven-writing 的状态汇报规范汇报（DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED）
```

## 章节模板

根据方案类型（technical / business / consulting / proposal），从 `${CLAUDE_SKILL_DIR}/prompts/section_templates/` 加载对应模板。典型用法：

```bash
cat "${CLAUDE_SKILL_DIR}/prompts/section_templates/technical.yaml"
```

`${CLAUDE_SKILL_DIR}` 由 Claude Code 在调用本 skill 时自动设置，在 plugin/npx/全局三种安装模式下都正确指向 `<...>/skills/solution-writing/`。不要使用 `prompts/section_templates/...` 这样的 cwd-相对路径——Claude 的 cwd 是用户项目，不是 skill 所在目录。

## 红线

- 跳过知识检索直接撰写
- 跳过配图规划直接撰写（计划中有配图需求的任务）
- 跳过 spec-reviewing 直接进入 quality-reviewing
- 让撰写子智能体自己审查自己
- 审查不通过就跳到下一个任务
- 使用文件引用而非直接粘贴任务内容给子智能体
