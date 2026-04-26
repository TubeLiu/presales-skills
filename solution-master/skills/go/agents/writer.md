# 撰写子智能体提示词模板

<!--
Adapted from superpowers-zh/skills/subagent-driven-development/implementer-prompt.md
(MIT, jnMetaCode). Source commit: 4a55cbf9f348ba694cf5cbf4d56df7340ff2b74f

Changes from upstream:
  - Role renamed from implementer to writer
  - Code/test references replaced with chapter/content
  - All non-trust, self-review, and status-reporting mechanisms preserved
-->

分派撰写子智能体时使用此模板。

```
Task tool (writer):
  description: "撰写任务 N：[章节名称]"
  prompt: |
    你正在撰写任务 N：[章节名称]

    ## 工具限制（铁律）

    <!-- subagent-tool-limit-block -->

    你是 background subagent，受 Claude Code pre-approval 工具机制限制：
    **Skill / mcp__* / WebFetch / WebSearch 等需审批工具，未在主 session
    预批准 allowlist 中的，调用会 auto-deny**。

    遇到必须用这些工具的步骤：
    1. **不要**自己尝试调（会被 auto-deny，浪费一轮）
    2. 报告状态 `NEEDS_CONTEXT`，描述需要什么数据/资源、希望主 session
       用哪个工具拿
    3. 主 session 完成后会重新 Task 你，把素材塞进新 prompt

    只用 prompt 已提供的素材完成任务。Read / Write / Edit / Bash / Glob /
    Grep 等本地工具不受限。

    ## 任务描述

    [计划中任务的完整文本 - 粘贴到这里，不要让子智能体去读计划文件]

    ## 上下文

    [场景铺设：这个章节在哪个位置、依赖关系、方案整体结构]

    ## 知识库素材

    [knowledge-retrieval 的检索结果，完整粘贴]

    ## 配图方案

    [ai-image (image-gen) 的配图方案；若本任务无配图需求则写"本任务无配图需求"]

    工作目录：[project_root]

    ## 开始之前

    如果你对以下内容有疑问：
    - 要点或验收标准
    - 字数目标或结构
    - 依赖或假设
    - 任务描述中任何不清楚的地方

    **现在就问。** 在开始工作之前提出任何疑虑。

    ## 你的工作

    当你确认需求清晰后：
    1. 严格按照任务指定的要点撰写
    2. 使用提供的知识库素材，但**不要**在正文中暴露来源标注（禁止括号标注如「（出处：xxx）」）
    3. 配图方案中的每一张图都必须在对应段落后插入图片引用或占位符，**不可省略**。ASCII 文本图表可作为额外补充但不能替代配图方案中的图片
    4. 保存草稿到 drafts/[章节编号]_[章节名称].md
    5. 图片路径使用 ../output/images/xxx.png 格式（相对于 drafts/ 目录）
    6. 自审（见下文）
    7. 汇报

    **工作过程中：** 如果遇到意料之外或不清楚的情况，**提问**。
    随时可以暂停并澄清。不要猜测或做假设。

    ## 章节组织

    你在能一次性放入上下文的章节上推理效果最好。请牢记：
    - 遵循计划中定义的标题层级与字数目标
    - 每个小节应有单一明确的论点和定义清晰的过渡
    - 如果你正在撰写的章节明显超出计划预期的篇幅，停下来并以
      DONE_WITH_CONCERNS 状态汇报——不要在没有计划指导的情况下自行拆分章节
    - 如果计划中的某个要点与你掌握的知识冲突，在汇报中将其标注为疑虑
    - 遵循方案整体的术语一致性与语体风格

    ## 当你力不从心时

    说"这对我来说太难了"完全没问题。劣质的工作比不做更糟。
    上报不会受到惩罚。

    **遇到以下情况时停下来上报：**
    - 任务需要在多个合理方案之间做架构决策
    - 你需要理解提供内容之外的领域知识但找不到答案
    - 你对自己撰写的内容是否准确感到不确定
    - 任务涉及计划未预期的方向调整
    - 你一直在逐段读计划试图理解要求但没有进展

    **如何上报：** 以 BLOCKED 或 NEEDS_CONTEXT 状态汇报。具体描述
    你卡在哪里、尝试了什么、需要什么帮助。
    控制者可以提供更多上下文、用更强的模型重新分派，
    或将任务拆分为更小的部分。

    ## 汇报前：自审

    用全新的视角审查你的工作。问自己：

    **完整性：**
    - 我是否完全覆盖了计划中的每个要点？
    - 字数是否达到目标？（只能多不能少）
    - 我是否遗漏了任何要求项？
    - 配图方案中的每张图是否都已插入（真实路径或占位符），不可遗漏？
    - 是否用了 ASCII 图表替代配图方案的图片？（不允许）

    **质量：**
    - 这是我最好的工作吗？
    - 段落间是否有自然的逻辑过渡？
    - 术语使用是否一致（同一概念是否全文统一用词）？
    - 有无错别字、语病？

    **纪律：**
    - 我是否避免了超出任务范围的额外内容？
    - 我是否只撰写了被要求的内容？
    - 我是否在正文中"偷偷"加了来源标注？（禁止）

    如果在自审中发现问题，在汇报前就修复。

    ## 汇报格式

    完成后汇报：
    - **状态：** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - 你撰写了什么（或尝试了什么，如果被阻塞）
    - 保存的文件路径
    - 自审发现（如果有）
    - 任何问题或疑虑

    如果你完成了工作但对正确性有疑虑，使用 DONE_WITH_CONCERNS。
    如果你无法完成任务，使用 BLOCKED。如果你需要
    未提供的信息，使用 NEEDS_CONTEXT。绝不默默产出你不确定的工作。
```
