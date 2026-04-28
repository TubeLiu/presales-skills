# Tender Workflow — AI-assisted bid/tender workflow

[中文](./README.md) | **English**

End-to-end AI-assisted solution from tender document to final bid. **Four roles** (Planner / Analyst / Writer / Reviewer) cover the full tender, analysis, writing, and review flow.

---

> **Install**: see the root [README_EN.md#install](../README_EN.md#install). Once installed, you can call `/tpl` `/taa` `/taw` `/trv` `/twc` from any directory. Source mode (just `cd` into this directory) also works; the `python skills/...` commands shown below run directly in source mode.

---

## Four roles + data flow

| Role | Skill | Serves | Task |
|---|---|---|---|
| Planner | `tpl` | Buyer | Product features → tender technical spec + scoring rules (no control-bid traces) |
| Analyst | `taa` | Bidder | Tender doc → 7-module analysis report + bid outline |
| Writer | `taw` | Bidder | Outline + KB → chapter draft DOCX |
| Reviewer | `trv` | Both | Multi-axis review + AI-driven smart revision |

```
Buyer:  Project requirements → [tpl] → Tender doc → [trv] → Publish
Bidder: Tender doc → [taa] → Analysis + outline → [trv] → [taw] → Chapter drafts → [trv] → Complete bid
```

---

## User input routing (avoids 5 skills competing for triggers)

| User says | Perspective | Use |
|---|---|---|
| Write tender / generate tender spec / tender planning / anti-control-bid | Buyer | `/tpl` |
| Write bid / write a chapter / draft bid | Bidder | `/taw` (**must run `/taa` first**) |
| Analyze tender / assess bid feasibility / look at this tender | Bidder | `/taa` |
| Review the quality of the tender doc itself | Buyer | `/trv --type tender_doc` |
| Review bid analysis / outline / chapter / full bid | Bidder | `/trv --type analysis\|outline\|chapter\|full_bid` |
| Configure / setup / show / validate / migrate / config not taking effect | — | `/twc` |

Disambiguation (always pin down the perspective):

- **"Analyze tender"** defaults to bidder understanding the requirement → `/taa`; if the user actually wants to review buyer-doc quality, use `/trv --type tender_doc`
- **"Write tender" vs "write bid"** is easy to confuse — **tender** = buyer `/tpl`; **bid** = bidder `/taw`
- **`/taw` always requires `/taa` first**; calling `/taw` without an outline hard-errors ("report not found")

---

## Common commands

```bash
# Planner
/tpl <feature-list> [--project <overview>] --template <government|finance|soe|enterprise> [--level detailed|standard|general|brief] [--no-scoring]

# Analyst
/taa <tender-doc> [--product <product-capability.xlsx|.md>] [--vendor <name>] [--kb-source auto|anythingllm|local]

# Writer
/taw <dir> --chapter <number> [--vendor <name>] [--search-tool auto|websearch|<FQN>] [--image-source auto|local|drawio|ai|web|placeholder] [--image-provider ark|dashscope|gemini]

# Reviewer
/trv <file> --type <tender_doc|analysis|outline|chapter|full_bid> [--reference <ref>] [--revise-docx --revise-scope must|all]

# Configuration
/twc setup       # Interactive first-time setup
/twc show        # View config
/twc validate    # Health check
/twc models      # List AI image models
```

For detailed parameters, run `-h` / `--help` on each skill.

---

## taw single-chapter vs multi-chapter mode (important)

`taw` chapter titles use Word's native **multi-level list auto-numbering** (do not write "1.3.1 ..." in the heading text).

| Mode | Command | Word display | Use case |
|---|---|---|---|
| **Multi-chapter merge** (recommended for production) | `/taw <dir> --chapter all` or range `1.1-1.11` | "1." chapter / "1.3" section / "1.3.1" subsection naturally continuous | Formal bid |
| Single-chapter standalone | `/taw <dir> --chapter 1.3` | Single doc starts from "1." automatically; doesn't show "1.3" | Local preview / testing only |

Single-chapter mode cannot preserve original chapter numbers — that's intrinsic to Word's multi-level list design (auto-numbering starts from 1 inside a single document). **Formal bids must use multi-chapter mode** so numbering stays naturally continuous.

---

## Bid format spec (2026 edition)

`taw`'s DOCX output automatically follows:

- **Page**: A4, top/bottom 2.5cm / left/right 2.4cm
- **Headings**: H1 三号 SimHei bold / H2 小三 SimSun bold / H3 四号 SimSun bold / H4 13pt / H5 12pt (Word multi-level auto-numbering 1, 1.1, 1.1.1, ...)
- **Body**: 小四 SimSun, 1.5 line spacing, first-line indent 2 chars
- **Spacing**: 0.5 line before / after each paragraph
- **Images**: caption below image, "Figure X-Y caption" 小五 SimSun centered
- **TOC**: TOC field at document start (press F9 in Word to update)
- **Anti-overpromise**: forbids absolute wording like "guarantee" / "ensure 100%" / "absolutely"; replaces with "expected to achieve / aim to deliver / design target is"
- **Source attribution**: web-derived numbers tagged `[Internet source, please verify]`; unsupported claims tagged `[to be confirmed]`

---

## Knowledge base (Local-KnowledgeBase)

`taw` v3.0 uses an all-Markdown image-text integrated KB:

```
<KB_ROOT>/
├── tech-solution-XXX/
│   ├── full.md            # Main doc (images embedded as ![](images/HASH.jpg))
│   ├── images/            # Image directory
│   ├── content_list_v2.json
│   └── layout.json
└── .index/
    └── kb_catalog.yaml    # Auto-generated by kb_indexer.py
```

Build the index:

```bash
/taw --build-kb-index                                    # Uses localkb.path from config
/taw --build-kb-index --kb-path /path/to/Local-KnowledgeBase
```

KB path resolution priority: `--kb` ad-hoc override > config `localkb.path` > first-run prompt.

---

## Configuration

Unified config file: `~/.config/tender-workflow/config.yaml`

```yaml
localkb:
  path: /data/Local-KnowledgeBase
anythingllm:
  workspace: <slug-or-uuid>          # Optional; fill when using anythingllm-mcp plugin
ai_image:
  default_provider: ark              # ark / dashscope / gemini
```

Resolution priority: **CLI args > env vars > skill section > global section > defaults**.

`/twc setup` walks through 6 steps (KB path → AnythingLLM → draw.io → MCP search tool → skill defaults → verify).

### MCP search tools

The "MCP search tools" step in `/twc setup` §4 has two halves:

**Half a — register** (uses web-access plugin's `mcp_installer.py`; if `node` / `uv` is missing, the wizard auto-installs at user level; after registration, asks whether to actually test; **prerequisite**: install `web-access` plugin first; if not installed, this step is skipped without affecting other configuration). Three built-in candidates:

| `<provider>` | Tool | Get key |
|---|---|---|
| `tavily` | `tavily_search` | https://tavily.com |
| `exa` | `web_search_exa` | https://exa.ai |
| `minimax` (MiniMax Token Plan) | `web_search` + `understand_image` | Subscribe to [Token Plan](https://platform.minimaxi.com/subscribe/token-plan) for an `sk-cp-` prefixed key (regular chat keys do not work for MCP, see [issue #96](https://github.com/MiniMax-AI/MiniMax-M2/issues/96)) |

**Half b — pick default** (§4.4): `mcp_installer.py list-search-tools` **dynamically enumerates** all MCP servers currently registered in `~/.claude.json` (not just the three above), letting the user pick a default search tool from the actually-available list. Newly installed MCPs (no plugin upgrade required) appear at the next setup automatically — matching the "use whatever is in Claude Code" design.

`mcp_search.priority` stores an FQN list (`mcp__<server>__<tool>` or built-in `WebSearch`); the workflow (taw / taa) tries them in order and falls back to `WebSearch`. Legacy aliases in old configs (`tavily_search`, etc.) are transparently converted to FQN by `tw_config.py`.

---

## Subagent architecture (taw / parallel writing)

For long chapters (H3 ≥ 3 and target word count ≥ 4500), `taw` automatically enables parallel writing:

```
Phase 2A  Main session prepares materials + image_plan (KB / Web / AI image all localized;
          structured AI images auto-route through ai-image's 79 templates)
   ↓
Phase 2B  Concurrently dispatch H3 writer subagents (Read agents/writer.md)
   ↓
Phase 2C  Integration (concat + intro + transition + consistency + M4 final check + image-list audit)
   ↓
Phase 2.5R  Parallel dispatch spec-reviewer + quality-reviewer subagents → apply revisions (max 2 rounds)
   ↓
Phase 3  DOCX output (multi-level list + TOC + hierarchy validation)
```

**Zero-config**: all restricted tools (Skill / mcp__* / WebSearch / WebFetch) are consumed once by the main session in Phase 2A; subagents only use Read / Bash / Glob / Grep on the prepared materials. No manual `~/.claude/settings.json` configuration needed.

---

## Troubleshooting

| Symptom | Action |
|---|---|
| `taw` cannot find outline / report | Shorthand directory mode requires both `.docx` + `.md` in the dir; or explicitly pass `--outline` / `--report` separately |
| KB retrieval returns 0 hits | Run `/taw --build-kb-index` to rebuild; check `localkb.path` in `~/.config/tender-workflow/config.yaml` |
| AnythingLLM call fails | Check whether `/plugin install anythingllm-mcp@presales-skills` was run; or use `--kb-source local` to skip |
| draw.io diagram generation fails | `/plugin install drawio@presales-skills`; CLI fallback requires draw.io Desktop |
| AI image generation fails | Run `/twc validate` to check API config; or use `--image-source placeholder` |
| DOCX heading level wrong (1.3 shown as H1) | Upgrade to v2.0+ (Word multi-level auto-numbering); don't write numbers in heading text |
| Cross-platform issues | Windows: use Git Bash / WSL2; use forward slashes in paths |

---

## Development

```bash
# After cloning, activate the pre-commit hook (auto-runs tests/test_skill_refs.py)
git config core.hooksPath tools/hooks

# Run unit tests
python3 -m pytest -q

# Run SKILL.md reference consistency check
python3 -m pytest tests/test_skill_refs.py -v
```

For detailed architecture + skill internals, see each skill's `SKILL.md`:

- `skills/tpl/SKILL.md`, `skills/taa/SKILL.md`, `skills/taw/SKILL.md`, `skills/trv/SKILL.md`, `skills/twc/SKILL.md`
- `taw` heavy-workflow details (read on demand): `skills/taw/references/{cli-help, preflight, io-formats, templates, kb-retrieval, image-retrieval, markdown-writing}.md`
