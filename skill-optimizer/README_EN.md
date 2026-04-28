# skill-optimizer plugin — Skill Review and Optimization

[中文](./README.md) | **English**

Review and optimize existing Skills, focusing on trigger semantics, workflow gates, resource organization, safety boundaries, dependency installability, and the division of responsibility between README and SKILL.

> 🙏 **Upstream attribution**: the methodology and original content of the `references/` triplet (`review-checklist.md` / `skill-design-review-framework.md` / `skill-creation-best-practices-claude-api-docs.md`) come from [chujianyun/skills](https://github.com/chujianyun/skills/tree/main/skills/skill-optimizer/references) — the 9-dimension review checklist, 5 Skill design patterns (Tool Wrapper / Generator / Reviewer / Inversion / Pipeline), and Anthropic Skill creation best practices. This repo directly vendors the three refs as the design baseline for skill-optimizer. Thanks to chujianyun for the open-source work.

## Slash entry points

| Trigger | Form |
|---|---|
| Claude Code canonical | `/skill-optimizer:optimize` |
| Codex / Cursor / OpenCode short alias | `/optimize` |
| Natural language auto-trigger | "optimize this skill" / "review SKILL.md" / "improve a skill" / "refactor skill spec" / "check skill quality" |

## When to use

- Check whether a Skill is easy to trigger, prone to false-trigger, or has fuzzy boundaries
- Add confirmation gates, exception handling, or guards on sensitive operations
- Optimize `references/`, `scripts/`, indexes, or README structure
- Decide whether the Skill granularity is appropriate, or whether it overlaps with sibling Skills and could be merged

## Workflow (5 steps)

1. **Scope** — confirm the target skill and the scope for this round
2. **Review** — read SKILL.md, then references / scripts / assets / README on demand, against [references/review-checklist.md](skills/optimize/references/review-checklist.md) and [references/skill-design-review-framework.md](skills/optimize/references/skill-design-review-framework.md)
3. **Plan** — output review findings + optimization plan, **wait for explicit user confirmation** before continuing
4. **Implement** — only after the user replies "execute the plan" / "start modifying" / similar explicit go-ahead, make small step-by-step edits
5. **Verify** — multi-axis check: frontmatter / trigger semantics / split rationality / exception handling / dependency install / sensitive info / README vs SKILL division of responsibility

## References (three docs)

| File | When to read |
|---|---|
| [review-checklist.md](skills/optimize/references/review-checklist.md) | Default review baseline (9 dimensions of pass/uncertain/fail + common optimizations) |
| [skill-design-review-framework.md](skills/optimize/references/skill-design-review-framework.md) | Identify which of 5 Agent Skill patterns (Tool Wrapper / Generator / Reviewer / Inversion / Pipeline) applies; includes lightweight review mode |
| [skill-creation-best-practices-claude-api-docs.md](skills/optimize/references/skill-creation-best-practices-claude-api-docs.md) | When tradeoffs require best-practice guidance (Anthropic / Claude Code official) |

## Risks and boundaries

- Always reviews first, plans second, modifies third; never modifies the target Skill without explicit confirmation
- If suspected sensitive info (API Key / Token / Cookie / account) is detected, will not echo the full content in replies
- If the target Skill contains high-side-effect operations (delete, overwrite, deploy, send messages, paid API calls), will demand confirmation gates or risk prompts
- If external CLI / service / runtime dependencies are involved, will demand install + verify commands so the Skill can not only "be understood" but also "be executed"

## README vs SKILL

- `README.md` is for humans: use cases, main features, risks, boundaries, and big-picture context
- `SKILL.md` is for AI: trigger conditions, workflow, gotchas, confirmation gates, and execution rules

The two complement each other and should not duplicate large blocks.
