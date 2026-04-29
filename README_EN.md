# presales-skills — A SKILL collection for presales work

[中文](./README.md) | **English**

A SKILL collection focused on presales / solution / consulting scenarios, distributed via marketplace.

**Target users**: people doing presales / writing solutions / bidding / making PPT — hopefully helping you lose less hair, ship more output, work fewer late nights, and spend more time with yourself and your family.

**Compatibility**: works on both **Claude Code** (direct marketplace install) and **Cursor / Codex / OpenCode** (via [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI).

---

## Overview of 10 plugins

Split by role: 4 **shared plugins** provide foundational capabilities (called by main plugins, also usable standalone), 4 **main plugins** form end-to-end business flows, 1 **developer-tools plugin** reviews / optimizes skills themselves, and 1 **general-purpose plugin** provides independent utility.

### Shared plugins (foundational / 4)

| Plugin | Entry | One-liner |
|---|---|---|
| **ai-image** | `/ai-image:gen` or `/image-gen` | Unified AI image generator — 13 backends (volcengine/ark, qwen/dashscope, gemini, openai, minimax, stability, bfl, ideogram, zhipu, siliconflow, fal, replicate, openrouter) sharing one model registry; built-in 79 structured prompt templates (PPT slide / infographic / UI mockup / academic figure / technical diagram / poster, 17 categories); OpenAI backend additionally supports inpainting + transparent background + webp/jpeg output. Shared by solution-master / ppt-master / tender-workflow. |
| **web-access** | `/web-access:browse` or `/browse` | Web operations + CDP browser automation (search / scrape / authenticated session / browser automation), and provides `mcp_installer.py` to one-click register tavily / exa / minimax search MCP servers into `~/.claude.json`; `list-search-tools` sub-command dynamically enumerates all available search MCPs in the current session (so sm / tw setup can pick the default dynamically). |
| **drawio** | `/drawio:draw` or `/draw` | Draw.io diagrams (`.drawio` XML + optional PNG / SVG / PDF export), covering architecture / flow / sequence / ER / topology / ML model diagrams. |
| **anythingllm-mcp** | (MCP server, no slash) | AnythingLLM knowledge-base semantic search — auto-registers `anythingllm` MCP server on install; main plugins call it via `mcp__anythingllm__*` tools. |

### Main plugins (end-to-end flows / 4)

| Plugin | Entry | One-liner |
|---|---|---|
| **solution-master** | `/solution-master:go` or `/solution-master` | Generic solution writing: Socratic questioning → task decomposition → parallel subagent writing → two-stage review (spec + quality) → multi-source knowledge retrieval → image insertion → Markdown + DOCX output. |
| **ppt-master** | `/ppt-master:make` or `/make` | Multi-source documents (PDF / DOCX / URL / Markdown) → natively editable PPTX (SVG pipeline + real PowerPoint shapes; default free-design, 22 built-in templates available). |
| **tender-workflow** | `/tender-workflow:taa` / `:taw` / `:tpl` / `:trv` / `:twc` | Four-role bid + config: `tpl` tender planning (buyer) / `taa` tender analysis (bidder) / `taw` bid writing (bidder, parallel) / `trv` multi-axis review / `twc` config. |
| **customer-research** | `/customer-research:research` or `/research` | Multi-source customer research — systematic research on customer issues, product topics, or account queries with source attribution and confidence scoring. For customer profiling, competitive analysis, and technical feasibility validation before solution writing. |

### Developer-tools plugin (meta / 1)

| Plugin | Entry | One-liner |
|---|---|---|
| **skill-optimizer** | `/skill-optimizer:optimize` or `/optimize` | Skill review and optimizer — 5-step flow (Scope → Review → Plan → Implement → Verify) reviews target skill's trigger semantics, workflow gates, resource organization, safety boundaries, dependency installability, and README / SKILL division of responsibility. Defaults to "diagnosis + plan first" and only modifies files after the user explicitly says "execute the plan". Independent plugin, no other dependencies. |

### General-purpose plugin (independent utility / 1)

| Plugin | Entry | One-liner |
|---|---|---|
| **market** | `/market:polish` or `/polish` | B2B tech marketing copy editing — seven-sweep framework (Clarity / Voice & Tone / Value Association / Evidence / Specificity / Emotion / Risk Elimination) + expert panel scoring + Chinese redundancy replacement guide. Independent plugin, no external dependencies. |

> **Two trigger methods**:
> - **Slash commands**: `/<plugin>:<sub-skill>` (e.g., `/solution-master:go`); Claude Code auto-completes short aliases to canonical
> - **Natural language**: each SKILL.md's `description:` field includes trigger keywords; "draw an architecture diagram" / "generate image" / "make a PPT" / "write a solution" / "look at this tender" etc. directly trigger the corresponding sub-skill

---

## Install

### Path A: Claude Code (primary)

```
/plugin marketplace add Alauda-io/presales-skills
```

After adding the marketplace, the rest is done in the `/plugins` UI (no need to type install commands one by one):

**Step 1 — `/plugins` → Marketplaces tab → see presales-skills already added**

![Step 1 — Marketplaces tab finds presales-skills](docs/images/install/install-1.png)

**Step 2 — arrow to presales-skills, press Enter, select Browse plugins**

![Step 2 — manage menu select Browse plugins](docs/images/install/install-2.png)

**Step 3 — Discover tab lists all plugins. Space to multi-select → `i` to batch install (recommended), or Enter to single-select to install one component**

![Step 3 — Discover tab batch install](docs/images/install/install-3.png)

**Step 4 — `/reload-plugins` to load (or quit and re-enter Claude Code, safer)**

![Step 4 — /reload-plugins loads](docs/images/install/install-4.png)

Expected reload output: `10 plugins · 13 skills · 1 hook · 1 plugin MCP server`
- 1 hook: solution-master's SessionStart injects the main SKILL (only when cwd is in an SM project)
- 1 MCP server: `anythingllm` (from anythingllm-mcp plugin; absent if not installed)

Dependency order: install shared plugins first (ai-image / web-access / drawio / anythingllm-mcp), then main plugins (solution-master / ppt-master / tender-workflow / customer-research). `anythingllm-mcp` is optional — when absent, main plugins gracefully degrade to local YAML index + web search; `skill-optimizer` and `market` are optional — for skill review and copy editing respectively.

Local path also works: `/plugin marketplace add /path/to/presales-skills`

#### Install a single plugin (optional)

You can install just one or two plugins — each runs independently. Use Step 3's Enter-single-select, or directly run the command:

```
/plugin install drawio@presales-skills              # Only drawio
```

### Path B: Cursor / Codex / OpenCode

```bash
npx --yes skills add Alauda-io/presales-skills -a cursor   # Cursor
npx --yes skills add Alauda-io/presales-skills -a codex    # Codex
npx --yes skills add Alauda-io/presales-skills -a opencode # OpenCode
```

After the command runs, vercel-labs/skills CLI lists all 13 skills; press space to multi-select + Enter to confirm install:

![vercel-labs/skills CLI install UI: lists 13 skills, space to multi-select](docs/images/install/install-codex.png)

For detailed loading options and cross-agent capability differences, see [docs/cross-agent.md](docs/cross-agent.md).

### System dependencies

`ppt-master` requires system-level pandoc + cairo:

```bash
brew install pandoc cairo                 # macOS
apt install pandoc libcairo2-dev          # Debian / Ubuntu
```

For Windows, see [docs/cross-agent.md §3](docs/cross-agent.md#3-windows-适配).

---

## Quick start

> **Mindset**: every plugin's "configure" and "use" can be done by talking to AI in natural language — no need to memorize CLI flags; the AI walks you through the corresponding setup wizard step by step.

### Step 1: configure shared plugins first

#### `ai-image` — unified AI image engine

After install, **let AI configure it**:

```
> Configure ai-image
```

The AI walks you through: pick which of the 13 providers you'll use → fill API keys (as needed) → pick default provider → pick default size → validate. Then:

```
> Generate an image: a modern minimalist container cloud architecture diagram
> Use ark to generate a K8s network topology diagram
> /ai-image:gen "futuristic cloud platform dashboard, hi-tech aesthetic"
```

Provider is picked per `ai_image.default_provider` in `~/.config/presales-skills/config.yaml`; explicitly mentioning a provider name (ark / dashscope / gemini / openai / ...) in natural language overrides the default.

**Structured scenarios auto-route through templates**: when you say "make a Bento grid infographic / chat-screenshot mockup / system architecture / ER diagram / academic graphical abstract / policy-style slide" or similar structured types, ai-image picks a matching one from the 79 built-in templates (17 categories, sourced from garden-skills MIT), confirms each slot, then generates — much more stable than freeform prompts.

**OpenAI backend exclusive**: transparent-background PNG (logo / icon cutout), webp/jpeg custom-compression output, image editing (inpainting, with optional mask for partial repaint):

```
> Generate a transparent-background fox logo
> Replace the background of this image with blue sky and white clouds (provide source path)
```

#### `web-access` — web access + browser automation + MCP search registration

After install, **let AI configure it**:

```
> Configure web-access
```

The AI walks you through: detect Node.js 22+ (auto-install if missing) → enable Chrome remote debugging (tick the box at `chrome://inspect/#remote-debugging`, restart browser) → start and verify CDP Proxy (port :3456) → risk acknowledgment. Then:

```
> Search the latest news about company X
> Scrape the content of this Xiaohongshu post (login required)
> /web-access:browse "https://www.example.com/page"
```

**Bonus**: web-access bundles `mcp_installer.py`, used by `/twc setup` and `/solution-master setup` to one-click register tavily / exa / minimax-token-plan web search MCP servers into `~/.claude.json`; missing `node` / `uv` is auto-installed at user level (no sudo).

#### `drawio` — install and use (no wizard)

drawio works out of the box:

```
> Draw an architecture diagram: user → API gateway → microservices → database
> /drawio:draw "GitOps blue-green deployment flow"
```

Outputs a `.drawio` source file; if you have draw.io desktop or `drawio-cli` installed, also exports PNG / SVG / PDF:

```bash
brew install --cask drawio                   # macOS
npm install -g @drawio/drawio-desktop-cli    # Cross-platform
```

#### `anythingllm-mcp` — install and auto-register (no wizard)

No slash entry — once installed, the `anythingllm` MCP server is auto-registered, and main plugins (solution-master / tender-workflow) call it directly via `mcp__anythingllm__anythingllm_search` to query local / remote AnythingLLM workspaces. **When not installed**, main plugins gracefully degrade to local YAML index + web search; no hard-fail.

You need to run the [AnythingLLM](https://anythingllm.com/) service locally or remotely with at least one workspace; the workspace slug is filled in solution-master / tender-workflow's setup wizards.

---

### Step 2: configure and use `solution-master` — write a solution

**Configure first**:

```
> Configure solution-master
```

The AI walks you through: local KB path → AnythingLLM workspace (optional) → MCP search-tool priority (tavily / exa / minimax, any one) → CDP authenticated sites (optional) → draw.io desktop detection → API keys passed through to ai-image → validate.

**Then use**:

```
> Write a container-cloud technical solution for the finance industry
> /solution-master:go "GitOps blue-green deployment technical solution"
```

When inside an SM project directory (containing `drafts/` / `docs/specs/` / `solution-master:go` SKILL installed), solution-master triggers the **SessionStart hook to auto-inject the main SKILL.md iron rules**, then walks the workflow:

```
brainstorming (Socratic questioning)
  ↓
planning (task breakdown + acceptance criteria)
  ↓
per-chapter loop: knowledge-retrieval + ai-image / drawio image gen + writer subagent
  ↓
spec-review (content review) + quality-review (writing review)
  ↓
docx output
```

For detailed workflows, see `solution-master/skills/go/workflow/{brainstorming,planning,writing,spec-review,quality-review,knowledge-retrieval,docx,config}.md` (read on demand).

---

### Step 3: (optional) use `ppt-master` — make a PPT

**No dedicated config**: API keys are shared from ai-image, so as long as `ai-image` is installed and configured, `ppt-master` works out of the box.

**Use**:

```
> Make this PDF into a 12-page PPT
> Make this WeChat article into a deck
> /ppt-master:make /path/to/source.pdf
```

**Default free-design** (AI lays out freely, no preset template). 22 built-in templates available on demand:

```
> Use the mckinsey template for this PPT          # Switch to mckinsey
> Free design, no template, art style              # Exit template path
> What templates are available                     # List templates
```

**Global default override** (in `~/.config/presales-skills/config.yaml`):

```yaml
ppt_master:
  default_layout: china_telecom_template   # Or another built-in template name
```

---

### Step 4: configure and use `tender-workflow` — bidding

**Configure first**:

```
> Configure tender                                   # One-time setup for the 4 roles (tpl/taa/taw/trv)
```

The AI walks you through 6 steps: local KB path → AnythingLLM (optional) → drawio detection → MCP search tools (tavily / exa / minimax, via web-access's `mcp_installer.py`) → skill defaults (taa vendor name / tpl template etc.) → validate.

**Then use** (triggered per scenario):

```
> Look at this tender doc                          # → /tender-workflow:taa tender analysis
> Help me write chapter 3 of the bid              # → /tender-workflow:taw writing
> Generate a tender spec from this product feature list  # → /tender-workflow:tpl planning (buyer)
> Review this bid                                  # → /tender-workflow:trv review
```

For four-role details, see `tender-workflow/README.md`.

---

### Step 5: (optional) use `skill-optimizer` — review / optimize skills

**No dedicated config**: skill-optimizer is a read-only-and-modify-by-plan meta tool; install and use.

**Use**:

```
> Optimize this skill: <path/to/SKILL.md>
> Review ai-image's SKILL.md
> Check the trigger semantics of solution-master skill
> /skill-optimizer:optimize tender-workflow/skills/taa
```

Fixed 5-step flow:

```
Scope (confirm range)
  ↓
Review (read SKILL.md + on-demand references / scripts)
  ↓
Plan (output review findings + optimization plan) — ⚠ wait for explicit "execute the plan" before continuing
  ↓
Implement (small step-by-step file edits)
  ↓
Verify (multi-axis check + report)
```

**Key constraint**: "let me see" / "makes sense" / "for now" do not count as confirmation. Only explicit go-ahead like "execute the plan" / "start modifying" / "confirm the modification" actually edits files. During review, suspected sensitive info (API key / token / cookie / account) is described by type and position only — never echoes the full value.

For applicable scenarios, see `skill-optimizer/README.md`.

---

## Further reading

| Want to learn | See here |
|---|---|
| **Engineering discipline required for code changes** (version-number bump / cross-plugin paths / runtime pitfalls) | [CLAUDE.md](CLAUDE.md) — auto-loaded by Claude Code in this repo's sessions |
| Design rationale (skills/ only / path self-locate / SessionStart / Task subagent / MCP installer) | [docs/architecture.md](docs/architecture.md) |
| Cursor / Codex / OpenCode loading + compatibility matrix + Windows adaptation | [docs/cross-agent.md](docs/cross-agent.md) |
| Config file physical layout + pure CLI config + auto-dependency install | [docs/configuration.md](docs/configuration.md) |
| `/plugin-review` deep audit + `tests/test_skill_format.py` 24 lint items + PR flow | [docs/contributing.md](docs/contributing.md) |
