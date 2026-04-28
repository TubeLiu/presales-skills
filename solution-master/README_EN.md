# Solution Master

[中文](./README.md) | **English**

**A plugin that makes Claude Code produce delivery-grade solution documents.** Solution Master is not "another prompt template" — it assembles Socratic requirement extraction, isolated subagent writing, two-stage independent review, four-source knowledge fusion, and enterprise-grade DOCX layout into one auditable pipeline. Every solution goes through a "write → review content → review writing-quality" closed loop, not a one-shot "write and ship".

### Why not just "ask Claude to write a solution"

- **Socratic requirement extraction**: before writing, the project type, scope, constraints, audience, and acceptance criteria are clarified, avoiding ungrounded boilerplate (`skills/go/workflow/brainstorming.md`)
- **Subagent isolation + two-stage review**: each chapter is written by an independent subagent, then **spec-reviewer** checks content correctness and **quality-reviewer** checks writing quality. Reviewers are forced to **"distrust the report"** — they must open the draft file with Read and verify line by line, not just read the writer's self-report (`skills/go/agents/spec-reviewer.md` · `skills/go/agents/quality-reviewer.md`)
- **Four-source knowledge fusion**: local knowledge base + AnythingLLM semantic search + Web search (Tavily / Exa) + CDP authenticated browser (can reach Confluence and other intranet sites). Scored across four dimensions (relevance / authority / completeness / freshness), cross-source semantic deduplication, and gap-targeted re-search (`skills/go/workflow/knowledge-retrieval.md`)
- **Iron rules + auto-injecting SessionStart hook**: every session start (including `/clear`, `/compact`) auto-injects iron rules, red-line list, and skill routing table into Claude's context — cannot be forgotten or "rationalized away" (`skills/go/SKILL.md` · `hooks/session-start`)
- **Context-aware visuals + multi-provider AI image generation**: architecture diagrams go through draw.io, concept art through AI image, product screenshots through local assets, picked automatically per chapter semantics. AI image generation supports 13 providers (ByteDance, Alibaba, Google, OpenAI, Replicate, etc.), managed via `/ai-image:gen models` (`ai-image plugin` · `drawio plugin` · `skills/go/scripts/sm_config.py`). **Structured visuals (infographics / UI screenshots / academic graphical abstracts / neural network architectures / paper figures) automatically route through ai-image's 79 built-in templates**, avoiding ad-hoc prompt rewrites
- **One-click enterprise DOCX output**: Markdown by default, DOCX output follows separate Chinese/English fonts, H1–H5 multi-level auto-numbering, and auto-embedded draw.io PNGs — no manual formatting (`skills/go/workflow/docx.md` · `skills/go/scripts/docx_writer.py`)

**Workflow**: `brainstorming` (clarify) → `planning` (task breakdown + acceptance criteria) → for each chapter: `knowledge-retrieval` + ai-image / drawio plugin (cross-plugin invocation) + writer subagent → `spec-review` → `quality-review` → assemble → `docx` → done. See [`docs/workflow.dot`](./docs/workflow.dot) for the detailed workflow diagram.

## Use cases

- Technical solution proposals
- Business proposals
- Consulting reports
- Project proposals
- Other documents requiring structured composition

## Core features

### Skill structure (v1.0.0)

The main skill `solution-master` (slash entry `/solution-master:go`) consists of one unified SKILL.md and on-demand workflow sub-files:

| File | Purpose |
|---|---|
| `skills/go/SKILL.md` | Main entry: description / iron rules / file navigation / subagent dispatch |
| `skills/go/workflow/brainstorming.md` | Stage 1: Socratic requirement extraction |
| `skills/go/workflow/planning.md` | Stage 2: task decomposition + acceptance criteria |
| `skills/go/workflow/writing.md` | Stage 3: writing main flow + subagent dispatch |
| `skills/go/workflow/knowledge-retrieval.md` | Multi-source knowledge retrieval |
| `skills/go/workflow/spec-review.md` | Content correctness review |
| `skills/go/workflow/quality-review.md` | Writing quality review |
| `skills/go/workflow/docx.md` | DOCX output + font spec |
| `skills/go/workflow/config.md` | Configuration management |
| `skills/go/agents/{writer,spec-reviewer,quality-reviewer}.md` | Task subagent role prompts |
| `skills/go/scripts/{sm_config,kb_indexer,docx_writer}.py` | Python utility scripts |
| `skills/go/prompts/*.yaml` | Writing rules / image guidelines / source ranking / fusion strategy |

**Shared dependencies** (install on demand):

| Plugin | Role | When required |
|---|---|---|
| `drawio` | Architecture / flow / topology diagrams | Always |
| `ai-image` | Unified AI image generation (13 providers) | Always |
| `anythingllm-mcp` | Knowledge base semantic search | Optional — when AnythingLLM is enabled (auto / `--kb-source anythingllm`); without it, falls back to local KB |
| `web-access` | Web access + CDP browser automation | Optional — required only when `cdp_sites.enabled=true` (authenticated-site retrieval) |

### Anti-derail mechanisms

1. **SessionStart hook** — every session start (including `/clear`, `/compact`) auto-injects `skills/go/SKILL.md` into Claude's `additionalContext`. Iron rules + red-line list + workflow navigation table + "distrust the report" principle cannot be forgotten or rationalized away. The hook includes a **project gate**: only triggers when cwd contains `drafts/` / `docs/specs/` / `skills/go/SKILL.md` markers, so non-SM projects don't get polluted.
2. **Hardened subagent prompts** — `agents/spec-reviewer.md` + `agents/quality-reviewer.md` retain the "do not trust the report" passage vendored from superpowers-zh, forcing reviewers to Read the file and verify line by line.
3. **HARD-GATE tags** — `workflow/brainstorming.md` etc. use `<HARD-GATE>` to mark un-bypassable checkpoints (e.g., "do not start writing before user approval"); enforced via prompt engineering.

> **Install**: see the root [README_EN.md#install](../README_EN.md#install) (covers both Claude Code marketplace and Cursor / Codex / OpenCode cross-agent loading).
>
> Once installed, Claude Code automatically sets `${CLAUDE_PLUGIN_ROOT}` to the plugin directory, registers the SessionStart hook from `hooks/hooks.json`, and discovers `skills/go/SKILL.md`. Verify: `/plugin list`. Uninstall: `/plugin uninstall solution-master@presales-skills`.

## Quick start

After installation:

1. Configure ai-image: tell Claude "Configure ai-image" (first time) or "Set ai-image \<key\> to \<value\>"
2. Start writing: describe your project, e.g., "write a GitOps blue-green deployment technical solution" — the SKILL auto-triggers, starting from `brainstorming`

## Configuration

**Unified config file**: `~/.config/presales-skills/config.yaml` (the legacy `~/.config/solution-master/config.yaml` is auto-migrated).

**Management**: managed through ai-image plugin sub-commands (auto-migrate merges legacy paths):

```bash
# Claude Code slash (recommended)
/ai-image:gen setup       # First-time configuration (includes auto-migrate)
/ai-image:gen show        # View current config
/ai-image:gen validate    # Health check

# Or natural-language triggers:
"Configure ai-image"
"I just installed a new version and need to initialize"
"Migrate old config"
```

solution-master's own config tool: `skills/go/scripts/sm_config.py` (called by SKILL.md, wraps a sm-specific layer on top of ai-image plugin).

## Developer mode

To develop in this repo, load via the umbrella marketplace's local path:

```bash
cd /path/to/presales-skills     # umbrella marketplace root
claude
```

Then in the Claude Code session:
```
/plugin marketplace add .
/plugin install solution-master@presales-skills
/reload-plugins
```

After modifying SKILL / agent / hook / workflow, run `/reload-plugins` to hot-update (some scenarios require restarting Claude Code).
