# skill-optimizer plugin — Skill 审查与优化

**中文** | [English](./README_EN.md)

审查和优化已有 Skill，重点看触发语义、工作流门槛、资源组织、安全边界、依赖可安装性，以及 README / SKILL 的职责分层。

## Slash 入口

| 触发方式 | 形式 |
|---|---|
| Claude Code canonical | `/skill-optimizer:optimize` |
| Codex / Cursor / OpenCode 短形式 alias | `/optimize` |
| 自然语言 auto-trigger | "优化这个 skill" / "审一下 SKILL.md" / "改进某个 skill" / "重构技能说明" / "检查 skill 质量" |

## 适用场景

- 想检查一个 Skill 是否容易触发、容易误触发，或边界不清
- 想补确认门槛、异常处理、敏感操作保护
- 想优化 `references/`、`scripts/`、索引、README 等结构设计
- 想判断 Skill 粒度是否合适，是否与同级 Skill 重叠或适合合并

## 工作流（5 步）

1. **Scope** — 确认目标 skill 与本次范围
2. **Review** — 读 SKILL.md，按需读 references / scripts / assets / README，对照 [references/review-checklist.md](skills/optimize/references/review-checklist.md) 与 [references/skill-design-review-framework.md](skills/optimize/references/skill-design-review-framework.md)
3. **Plan** — 输出审查结论 + 优化计划，**等待用户明确确认**才进入下一步
4. **Implement** — 仅在用户回复"按计划执行"/"开始修改"等开始执行类确认语后，再小步修改
5. **Verify** — frontmatter / 触发语义 / 拆分合理性 / 异常处理 / 依赖安装 / 敏感信息 / README 与 SKILL 分工等多维校验

## references 三件套

| 文件 | 何时读 |
|---|---|
| [review-checklist.md](skills/optimize/references/review-checklist.md) | 默认审查基线（9 个维度的 通过/存疑/不通过 判定 + 常见优化）|
| [skill-design-review-framework.md](skills/optimize/references/skill-design-review-framework.md) | 判断 5 种 Agent Skill 模式（Tool Wrapper / Generator / Reviewer / Inversion / Pipeline）是否匹配；含轻量审查模式 |
| [skill-creation-best-practices-claude-api-docs.md](skills/optimize/references/skill-creation-best-practices-claude-api-docs.md) | 需要在最佳实践层面取舍时（Anthropic / Claude Code 官方指南）|

## 风险与边界

- 默认先审查、后规划、再修改；没有明确确认前不会改目标 Skill
- 如果发现疑似敏感信息（API Key / Token / Cookie / 账号），不会在回复中回显完整内容
- 如果目标 Skill 包含删除、覆盖、部署、发送消息、付费调用等高副作用操作，会要求增加确认门槛或风险提示
- 如果依赖外部 CLI / 服务 / 运行时，会要求补安装和校验命令，避免 Skill 只能"看懂"但不能"执行"

## README 与 SKILL 的区别

- `README.md` 面向人：使用场景、主要功能、风险、边界和整体认知
- `SKILL.md` 面向 AI：触发条件、工作流、Gotchas、确认门槛和执行规范

两个文件互补，不大段重复。
