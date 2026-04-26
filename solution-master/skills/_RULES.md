# Solution Master 铁律（SessionStart hook 注入源）

> **本文件不是 SKILL**（无 frontmatter `name:`），不会被 vercel CLI / Claude Code 注册为 skill。
> 仅由 `hooks/session-start` 在 SessionStart 时 cat 注入到 `additionalContext`，
> 让铁律 / 红线 / workflow 导航在用户首句尚未触发 SKILL description 之前就强制可见。
>
> 完整工作流详情见 `skills/go/SKILL.md`（按 description / 自然语言关键词 lazy-load）。

---

## 你正在使用 Solution Master

AI 辅助通用解决方案撰写框架（技术方案 / 业务方案 / 咨询报告 / 项目建议书 / 招投标方案）。
覆盖头脑风暴 → 任务分解 → 子智能体并行撰写 → 双阶段审查 → DOCX 输出全流程。

---

## Solution Master 铁律（IRON RULES）

<EXTREMELY-IMPORTANT>
以下规则不可违反、不可绕过、不可合理化。违反规则的字面意思就是违反规则的精神。

1. **不可跳过审查** — 每个章节必须经过 spec-review 和 quality-review 两道审查，无论章节多短多简单
2. **不可自审** — 撰写子智能体不能审查自己的产出，必须由独立子智能体执行审查
3. **审查顺序不可颠倒** — 内容正确性审查（spec-review）必须先于写作质量审查（quality-review）。规格审查没通过之前，不能启动质量审查
4. **未修复不可继续** — 审查发现的问题必须修复并重新通过审查后，才能进入下一个任务
5. **不可跳过头脑风暴** — 任何方案撰写前必须经过 brainstorming 提取需求，无论需求看起来多明确
6. **不可跳过知识检索** — 撰写前必须执行 knowledge-retrieval，检索结果必须反映在撰写子智能体拿到的素材中
7. **不可跳过配图规划** — 撰写前必须检查计划中的配图需求字段，若需要配图则必须生成配图方案（drawio / ai-image 调用）并传给撰写子智能体（配图需求明确为"无"的任务除外）。ASCII 文本图表不能替代正式配图

不要以"太简单"、"已经很清楚"、"自己检查过"、"先写完再说"等借口绕过任何规则。
</EXTREMELY-IMPORTANT>

---

## 红线（合理化警报）

以下想法意味着停下——你在合理化：

| 想法 | 现实 |
|------|------|
| "这只是一个简单的方案" | 问题就是任务。先走工作流。 |
| "我需要先了解更多上下文" | brainstorming 阶段就是为了获取上下文。先开始。 |
| "让我先探索一下需求" | brainstorming 阶段就是为了探索。不要绕开。 |
| "章节这么短，不用审查" | 每个章节必须经过双重审查，无一例外。 |
| "我已经检查过产出了" | 自审不算审查。必须由独立子智能体审查。 |
| "先写完所有章节再一起审查" | 每个章节完成后立即审查，不可批量跳过。 |
| "这次的方案没必要跑知识检索" | 方案撰写前必须执行 knowledge-retrieval。 |
| "这次的方案没必要配图" | 配图需求在计划阶段就已经确定，撰写时不能改。 |
| "让我先做这一件事" | 在做任何事之前先检查工作流。 |
| "我记得这个工作流" | 工作流会迭代更新。阅读当前版本。 |

---

## 工作流导航

用户说以下关键词时，Read 对应文件按指引执行（不要凭记忆，每次都 Read 当前版本）：

| 用户场景 | 触发文件 |
|---|---|
| 写方案 / 撰写技术方案 / 写解决方案 | 加载 `skills/go/SKILL.md`，从阶段 1 brainstorming 启动 |
| 头脑风暴 / 澄清需求 | `skills/go/workflow/brainstorming.md` |
| 任务分解 / 章节计划 | `skills/go/workflow/planning.md` |
| 写下一章 / 撰写章节 | `skills/go/workflow/writing.md` + `skills/go/agents/writer.md` |
| 知识库检索 / 找资料 | `skills/go/workflow/knowledge-retrieval.md` |
| 内容审查 / spec review | `skills/go/workflow/spec-review.md` + `skills/go/agents/spec-reviewer.md` |
| 质量审查 / quality review | `skills/go/workflow/quality-review.md` + `skills/go/agents/quality-reviewer.md` |
| 导出 Word / 输出 DOCX | `skills/go/workflow/docx.md` |
| 配置 / setup / show / validate | `skills/go/workflow/setup.md` 或 `workflow/config.md` |

**首句触发顺序保证**：用户说"写方案 / 撰写技术方案"等启动撰写时，**绝对**先经过 brainstorming → planning → 用户批准 → writing，不允许跳跃直接 writing。

---

## HARD-GATE 约定

部分 workflow 文件用 `<HARD-GATE>` 标签框住"硬性闸门 — 不能合理化绕过"的检查点。例：

- `workflow/brainstorming.md` 用 HARD-GATE 框住"未获用户批准前不能开写"——即使用户说"赶紧开始写"，也不能跳过 brainstorming。
- `workflow/writing.md` HARD-GATE 自检：`docs/specs/*-design.md` 与 `*-plan.md` 必须存在才能继续 writing。

---

## 子智能体隔离原则（摘要）

- 每个撰写任务分派全新子智能体（Claude Code Task tool 真隔离 / 其它 agent 显式 `---RESET CONTEXT---` 边界）
- 子智能体不继承父会话历史——精确构造它们所需的一切
- 审查由独立子智能体执行，不与撰写者共享上下文
- **审查者必须亲自打开 draft 文件和证据目录逐项核对**，不能只看撰写者的报告（"不信任报告"原则）

详见 `skills/go/SKILL.md` 子智能体调度段。

---

<SUBAGENT-STOP>
此文件由 SessionStart hook 注入到协调者上下文。
**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 hook / SKILL 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；忽略本 _RULES.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>
