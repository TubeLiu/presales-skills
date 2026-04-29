# Tender Assistant — Tender-analysis Assistant

[中文](./README.md) | **English**

> One command, from a hundred-page tender doc to an actionable bid strategy.

**Tender Assistant** is a **Claude Code** AI Skill built for presales / bid teams. It deeply parses tender documents and auto-generates a structured **tender analysis report (.md)** and **bid outline (.docx)**, compressing what used to be hours of manual reading, extraction, and organization into a few minutes.

## Why use it

| Traditional approach | With Tender Assistant |
|---|---|
| Manually read hundreds of pages of tender doc | AI auto-extracts all key information |
| Item-by-item transcription of technical requirements, prone to omissions | 7 systematic analysis modules, zero ★-clause omissions |
| Disqualification risk judged by intuition | Disqualification clauses listed item-by-item + TOP-5 risk ranking |
| Scoring items written by feel | Each scoring item gets a concrete high-score strategy |
| Outline structure built from scratch every time | Auto-generated Word outline with chapter numbering and requirement-to-chapter mapping |

## Highlights

**Deep analysis, not a simple summary** — 7 analysis modules (M1-M7) cover project overview, technical matrix, business terms, scoring strategy, disqualification risks, format checklist, and writing guidance; every analysis cites the original source (chapter / page).

**Industry auto-detection** — auto-recognizes three major industries (Government IT, SOE / Central enterprise, Finance) and loads matching extension modules (e.g., government procurement compliance, domestic IT requirements, financial regulation); generic projects use the default template.

**Two ready-to-use output files** — Markdown analysis report for internal team decisions; Word outline (.docx) directly usable as the bid skeleton, with Chinese-font typography and A4 page setup.

**Full requirement coverage check** — Part C requirement-to-chapter mapping ensures every【mandatory】clause in the tender doc has a corresponding outline chapter, preventing key requirements from being missed.

## Usage

Run in Claude Code:

```bash
# Basic (use default index or AI fuzzy assessment)
/taa <tender-doc-path>

# Specify product capability spec (precise match scoring)
/taa <tender-doc-path> --product <product-capability.xlsx|.md>

# Save index to default location during analysis
/taa <tender-doc-path> --product <product-capability.xlsx> --save-index

# Specify vendor (required, can be persisted via /twc setup)
/taa <tender-doc-path> --vendor "BoCloud"

# Combined
/taa <tender-doc-path> --product specs/product-capability.md --vendor "BoCloud"

# Build product capability index only (no analysis)
/taa --build-index --product <product-capability.xlsx>

# Build index from default file path (env var)
/taa --build-index

# Force AnythingLLM as product capability source (errors if unavailable)
/taa <tender-doc-path> --kb-source anythingllm

# Force local index, skip AnythingLLM
/taa <tender-doc-path> --kb-source local
```

Auto-trigger also works: after uploading a tender doc, say "analyze tender", "assess tender doc", "look at this tender" — the Skill auto-takes over.

### Product capability source priority

```
--product specified file (highest priority, precise assessment)
    ↓ if not specified
AnythingLLM semantic search (queried on demand in M2 phase, with query cache)
    ↓ if unavailable
Local YAML index (V2 three-tier / V1 single-file)
    ↓ if all unavailable
AI fuzzy assessment
```

**`--kb-source` parameter** (added in v2.2.1):

| Value | Behavior |
|---|---|
| `auto` (default) | Try AnythingLLM first; fall back to local index if unavailable |
| `anythingllm` | Force AnythingLLM (error and exit if unavailable) |
| `local` | Force local index, skip AnythingLLM detection |

**Note**: When `--product` and `--kb-source anythingllm` are used together, the latter takes precedence (forces AnythingLLM).

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `<tender-doc>` | positional | Required. Tender document path |
| `--product` | path | Optional. Product capability spec (Excel/Markdown), used for precise match scoring. **Note**: ignored when used with `--kb-source anythingllm` (which forces AnythingLLM) |
| `--vendor` | string | Required. Vendor name (can be persisted via /twc setup; missing triggers an error guide) |
| `--build-index` | flag | Optional. Only build product capability index and save to default location, do not analyze |
| `--save-index` | flag | Optional. Save index to default location during analysis (used with `--product`) |
| `--anythingllm-workspace` | string | Optional. Specify AnythingLLM workspace slug (recommended) or name. If unset, uses config file; otherwise picks the first workspace |
| `--kb-source` | string | Optional. Product capability source control: `auto` (default — AnythingLLM then local index), `anythingllm` (force AnythingLLM, error if unavailable), `local` (force local index, skip AnythingLLM) |

### Environment variables

| Variable | Description | Example |
|---|---|---|
| `TAA_DEFAULT_PRODUCT` | Default product capability file path, used when `--build-index` has no args | `/data/products/ACP_4.2.0.xlsx` |
| `TAA_ANYTHINGLLM_WS` | Default AnythingLLM workspace; lower priority than config and CLI args | `product-kb` |

**Config file**: `~/.config/tender-workflow/config.yaml` (unified config, managed via `/twc setup`)

```yaml
anythingllm:
  workspace: product-kb              # Global default AnythingLLM workspace
```

The Skill auto-runs three phases:

```
Phase 0  Read file → auto-detect industry → load industry template
Phase 1  7-module deep analysis → output tender_analysis_report_[timestamp].md
Phase 2  Generate bid outline → output bid_outline_[timestamp].docx
```

Output files are saved in `./output/`.

## Analysis report breakdown

### Base modules (all projects)

| Module | Content | Core value |
|---|---|---|
| **M1** | Project overview and bid recommendation | One table for the full picture; clear bid / no-bid recommendation (strongly recommend / recommend / cautious / do not recommend) |
| **M2** | Technical requirements analysis matrix | 9 categories of technical requirements extracted item-by-item with priority. With `--product`, support level is auto-filled; otherwise AI fuzzy assessment |
| **M3** | Business terms and contract clauses | In-depth analysis of IP ownership, penalty clauses, subcontracting limits; high-risk clauses tagged `[difficulty]` |
| **M4** | Scoring criteria and scoring strategy | **Concrete actionable methods to score high** for each scoring sub-item, not vague "highlight the strengths" |
| **M5** | Disqualification clauses and risk ranking | `[disqualify]` / `[deduct]` separately tagged; TOP-5 risk priority + countermeasures |
| **M6** | Format requirements checklist | Direct-tickable format-confirmation checklist with reminders for easily missed details |
| **M7** | Bid writing guidance | Writing priority, keyword list, scoring-item writing strategy, differentiating-strength suggestions, writing red lines |

### Industry extension modules (auto-loaded)

| Industry | Extensions | Focus |
|---|---|---|
| Government IT | E1 budget compliance · E2 govt procurement compliance · E3 security and confidentiality | Funding source, SME policy, cybersecurity classification |
| SOE / Central | E1 SASAC oversight · E2 domestic IT requirements · E3 anti-corruption risk control | SASAC approval, CPU / OS / database models, recusal system |
| Finance | E1 financial regulation · E2 data security · E3 business continuity | CBIRC / CSRC requirements, data classification, RTO / RPO |

## Bid outline output

The outline is dynamically generated from the analysis report, with three parts:

- **Part A — Outline rationale**: structural decision basis (why chapters are organized this way)
- **Part B — Complete outline**: technical section only (1.1-1.11); service plans integrated at the end
- **Part C — Requirement-to-chapter mapping**: every【mandatory】clause → corresponding chapter number, ensuring zero omissions

The generated `.docx` is preset with:

- Chinese fonts (unified SimSun across heading levels)
- A4 page (top/bottom 2.5cm, left/right 2.4cm)
- Word heading styles (auto-TOC supported)

## Analysis quality assurance

- Every analysis cites the original source: `(source: Chapter X p.XX)`
- Disqualification items `[disqualify]`, deduction items `[deduct]`, difficulties `[difficulty]` precisely tagged
- Missing info: "**not specified in document**" — never fabricate numbers
- M7 writing guidance is project-specific, not generic boilerplate

## Project structure

```
tender-assistant/
├── SKILL.md                         # Claude Code Skill main file (full Phase 0/1/2 prompt)
├── prompts/
│   ├── analysis.yaml                # 7-module analysis framework
│   └── outline.yaml                 # Outline generation framework
└── templates/builtin/
    ├── government_it.yaml           # Government IT extension modules
    ├── state_owned_enterprise.yaml  # SOE / Central enterprise extensions
    ├── finance.yaml                 # Finance extensions
    └── general.yaml                 # Generic (default)
```

## Version

**Current**: v2.4.0 · **Updated**: 2026-04-02 · **Maintainer**: 刘子佼 tubeliu@gmail.com

### v2.4.0 (2026-04-02)

- ✅ **Phase 0 extraction**: parameter handling rules moved from SKILL.md to `prompts/phase0_params.md`, loaded on demand, reducing main orchestrator size

### v2.3.0 (2026-04-01)

- ✅ **Context window optimization Wave 1+2**: compressed redundant SKILL.md descriptions; large config blocks and detailed rules externalized to YAML / MD files

### v2.2.1 (2026-03-17)

- ✅ **AnythingLLM integration enhancement**: added `--kb-source` to force AnythingLLM or local index
- ✅ **Complete AnythingLLM detection**: workspace listing and selection, three-tier priority (arg > config > env var)
- ✅ **M2 query rules enhanced**: query cache (avoid duplicate queries); failure fallback ("AI fuzzy assessment (query failed)")

### v2.2.0 (2026-03-10)

- ✅ **Outline simplification**: technical section only; service plans integrated at the end (1.10 and 1.11)
- ✅ **Numbering system adjustment**: chapter numbering changed from 5.X to 1.X

### v2.1.0 (2026-03-09)

- ✅ **AnythingLLM integration**: `--anythingllm-workspace` parameter and config support

### v2.0.0 (2026-03-05)

- ✅ **Product V2 three-tier index**: L0 fast routing (~2KB) + L1 category index (11) + L2 full detail (11), on-demand loading saves 70-90% tokens
