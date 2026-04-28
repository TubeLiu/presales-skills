# taw — Bid-document Writing Assistant

[中文](./README.md) | **English**

**taw** (Tender Article Writer) is the core writing role in the bid workflow. Based on the **tender analysis report** and **bid outline** produced by `taa`, combined with the company knowledge base, it auto-generates high-quality bid-chapter drafts (DOCX format).

**Version**: v3.0.0 | **Last updated**: 2026-04-03

---

## Highlights

### 1. Image-text symbiotic mode (added in v3.0.0)

- AI directly reads KB Markdown files and naturally perceives embedded image references (`![](images/xxx.png)`)
- No regex matching or scoring formula — images load with paragraph context, naturally associated
- `kb_indexer.py` generates a lightweight directory index (`kb_catalog.yaml`), storing only directory / title / category / summary
- `image_guidelines.yaml` provides image-usage guardrails (count caps, size specs, placeholder rules)
- H3 sub-sections without matching KB images automatically fall back to AI image gen or placeholder

### 2. Parallel writing architecture (v1.8.0+)

- ✅ Long chapters (≥3 H3 sub-sections AND ≥4,500 words) auto-enable parallel writing
- ✅ Phase 2A: writing blueprint generation (argument thread, H3 division of labor, glossary, word allocation)
- ✅ Phase 2B: concurrent subagent writing (each H3 sub-section runs in an independent agent in parallel)
- ✅ Phase 2C: integration review (transition fill-in, term unification, contradiction detection, scoring-coverage final check)
- ✅ Smart routing: parallel / sequential mode chosen automatically by chapter complexity
- ✅ Graceful degradation: when >50% subagents fail, automatically falls back to sequential writing

### 3. draw.io professional diagram generation

- ✅ Generates professional diagrams via draw.io (architecture / flow / org / sequence)
- ✅ Outputs editable .drawio source files
- ✅ Supports PNG/SVG/PDF export (XML-embedded, re-editable in draw.io)
- ✅ Auto-detects draw.io CLI path (macOS/Windows/Linux)

### 4. Multi-MCP search-tool support

- ✅ Detects all available MCP tools (Tavily Search, Exa Search)
- ✅ Sequential fallback chain: when a tool fails, automatically falls back to the next available
- ✅ Fine-grained control: `--search-tool tavily/exa/mcp/websearch/auto`
- ✅ Differentiated tagging: different tool sources use distinct labels

### 5. Flexible image-source control

- ✅ Unified `--image-source` parameter: `auto` / `local` / `drawio` / `ai` / `web` / `placeholder`
- ✅ Dual API support: Volcengine Ark Seedream 5.0 Lite + Alibaba Tongyi Wanxiang (2K resolution)
- ✅ Failure transparency: when the specified plan fails, falls back to placeholder (no implicit downgrade)

### 6. Deep content generation

- ✅ Core chapters 4,500+ words: segmented generation (3-5 sub-themes, 900-1,500 words each)
- ✅ Five heading levels: H1-H5 supported, fits deep outline structures
- ✅ Parameterized words / images: `--l2-words` / `--l3-words` / `--l2-images` etc. override template defaults
- ✅ Fact extraction table (WEB_FACTS): structured management of internet search results
- ✅ Scenario-aware tool choice: WebSearch for product queries, MCP for technical solutions

### 7. Quality assurance mechanisms

- ✅ 100% scoring coverage (every M4 scoring point answered)
- ✅ Keyword coverage ≥ 80% (M7 keyword list)
- ✅ Zero violations of disqualification red lines (M5 clauses and M7.5 red lines)
- ✅ Overpromise detection (zero absolute wording)
- ✅ To-confirm tagging (all unsupported content tagged)

---

## Table of contents

- [Quick start](#quick-start)
- [Full parameter reference](#full-parameter-reference)
- [Execution-flow detail](#execution-flow-detail)
- [Knowledge base config](#knowledge-base-config)
- [KB index build](#kb-index-build)
- [Chapter-number format detail](#chapter-number-format-detail)
- [Usage scenario examples](#usage-scenario-examples)
- [Output file spec](#output-file-spec)
- [Workflow integration](#workflow-integration)
- [Quality assurance mechanisms](#quality-assurance-mechanisms-1)
- [FAQ](#faq)

---

## Quick start

### Prerequisites

1. `/taa` has run, producing a tender analysis report (`output/tender_analysis_report_*.md`) and bid outline (`output/bid_outline_*.docx`)
2. KB path is configured (auto-guided on first run), or use `--kb-source none` to skip

### Minimal usage

```bash
# Minimal: directory mode auto-matches latest outline + report
/taw output/ --chapter 1.3

# Explicit file paths
/taw --outline output/bid_outline_20260305.docx --report output/tender_analysis_report_20260305.md --chapter 1.3

# Write the entire technical section (all sub-sections of chapter 1)
/taw --outline output/ --report output/ --chapter 一

# Specify vendor (required, can be persisted via /twc setup)
/taw output/ --chapter 1.3 --vendor "BoCloud"

# Write all chapters (chapter 1, technical section, 11 sub-sections)
/taw --outline output/ --report output/ --chapter all
```

Output files are saved to `./drafts/`.

---

## Full parameter reference

```
Usage:
  /taw --outline <outline.docx|dir> --report <report.md|dir> --chapter <number> [options...]
  /taw <dir> --chapter <number>            # Shorthand: directory matches both files
  /taw --set-kb <kb-path>
  /taw --build-kb-index
  /taw -h | --help
```

### Required parameters

| Parameter | Type | Description |
|---|---|---|
| `--outline` | path or dir | Bid outline (DOCX) produced by taa, or its directory (picks latest .docx). Optional in `--set-kb` / `--build-kb-index` / `-h` modes |
| `--report` | path or dir | Tender analysis report (Markdown) produced by taa, or its directory (picks latest .md). Optional in `--set-kb` / `--build-kb-index` / `-h` modes |
| `--chapter <number>` | chapter number | Target chapter; multiple formats supported (see below) |

### Optional parameters

| Parameter | Description |
|---|---|
| `--kb <path>` | Override KB path for this run only; does not modify config |
| `--kb-source <source>` | KB source control: `auto` (default, combined), `anythingllm`, `local`, `none` (see below) |
| `--set-kb <path>` | Permanently set default KB path, saved to `~/.config/tender-workflow/config.yaml` |
| `--build-kb-index` | Scan Local-KnowledgeBase directory, generate kb_catalog.yaml index, and exit |
| `--image-source <source>` | Image source control: `auto` (default, picked per H3 sub-section), `local` (KB images), `ai`, `web`, `drawio`, `placeholder` |
| `--search-tool <tool>` | Search tool control: `auto` (default), `tavily`, `exa`, `mcp`, `websearch` |
| `--vendor <name>` | Specify bidder vendor identity (required; can be persisted via /twc setup) |
| `--query <terms>` | Manually specify supplementary query terms |
| `--anythingllm-workspace <slug>` | Specify AnythingLLM workspace slug |
| `--l2-words <words>` | L2 chapter (X.X) target word count, overrides template default |
| `--l3-words <words>` | L3 sub-section (X.X.X) target words (default 900) |
| `--l4-words <words>` | L4 sub-section (X.X.X.X) target words (default 600) |
| `--l5-words <words>` | L5 sub-section (X.X.X.X.X) target words (default 400) |
| `--l2-images <count>` | L2 chapter image quota, overrides template default |
| `--l3-images <count>` | L3 sub-section image quota (default 0) |
| `-h, --help` | Show command help and exit |

### `--kb-source` parameter detail

Controls KB source for different scenarios:

| Value | Behavior | Use case |
|---|---|---|
| `auto` (default) | Combined use of all available KBs, dynamically picked by match score and content quality | Routine use |
| `anythingllm` | Force AnythingLLM; error and exit if unavailable | Ensure latest KB |
| `local` | Force local YAML index, skip AnythingLLM detection | No network or AnythingLLM unavailable |
| `none` | Completely skip KB; rely on internet search only | KB not yet built or need latest external info |

### `--kb` vs `--kb-source` vs `--set-kb`

The three parameters serve different purposes:

| Parameter | Purpose | Persistent | Priority |
|---|---|---|---|
| `--kb <path>` | Temporarily specify KB path | ❌ No | Highest |
| `--kb-source <source>` | Specify KB source type | ❌ No | Medium |
| `--set-kb <path>` | Permanently set default KB path | ✅ Yes | - |

**Examples**:

```bash
# Temporarily use a specific KB (this run only)
/taw output/ --chapter 1.3 --kb /tmp/test-kb

# Force AnythingLLM (error if unavailable)
/taw output/ --chapter 1.3 --kb-source anythingllm

# Skip KB completely; use internet only
/taw output/ --chapter 1.3 --kb-source none

# Permanently set default KB path (used in subsequent runs)
/taw --set-kb /data/company-kb
```

---

## Execution-flow detail

taw's full execution has four phases.

### Phase 0: input and config detection

```
User command
  ├─ Has -h/--help?       → Print help, exit
  ├─ Has --build-kb-index? → Scan KB dir, generate index, exit
  ├─ Has --set-kb?         → Save config, exit
  └─ Normal writing mode
       ├─ Path resolution
       ├─ KB path resolution (priority: --kb > config > first-run prompt)
       ├─ --kb-source parsing → KB source control
       ├─ --vendor parsing → VENDOR_NAME (required, errors with guidance if missing)
       ├─ --query parsing → EXTRA_QUERY (uses default template if empty)
       └─ --chapter parsing → CHAPTERS_TO_WRITE list
```

### Phase 1: writing preparation

#### Scoring mapping and writing-guidance extraction

- Extract scoring items from analysis report **M4**, mark high-score items (≥10 points) as priority topics
- Extract keyword list, writing strategy, differentiating strengths, red-line constraints from analysis report **M7**

#### KB text retrieval (four layers)

When `--kb-source none`, layers 1-3 are skipped, going directly to layer 4.

```
Layer 1: fixed (verbatim copy)
  Trigger: chapter touches fixed clauses like "after-sales / warranty / quality assurance"
  Hit → verbatim copy, tagged [source: fixed clause, do not modify]
  ↓ Miss

Layer 2: reusable (light edit)
  Trigger: any chapter (parallel-checked with fixed)
  Hit → read file, edit lightly and write (top 1-2 most relevant)
  ↓ Miss

Layer 3: history (extract for reference)
  Trigger: layer 2 missed
  Hit → precise read by key_sections.pages, apply de-identification mapping, rewrite
  ↓ Miss

Layer 4: WebSearch fallback
  Trigger: all three layers missed, or --kb-source none
  Cap: ≤2/section (≤3/section when --kb-source none)
```

#### Image acquisition (priority chain)

```
--image-source auto mode:
  At H3 sub-section granularity, pick image source per sub-section content context
  (drawio / ai / web / placeholder). Different H3 sub-sections under the same H2 may pick different sources.

Specified mode (e.g., --image-source ai):
  Try the specified source only; fall back to placeholder if it fails.
```

### Phase 2: content generation

- **Single-section mode**: direct generation, output `drafts/1.3_overall-design.docx`
- **Multi-section mode**: loop in order, show progress per section, all sections merged into one DOCX

### Phase 3: quality self-check and output

After each section, a basic self-check runs and produces a self-check report.

---

## Knowledge base config

taw uses the `Local-KnowledgeBase/` directory structure (each document is a main `.md` + an `images/` sub-directory). The indexer auto-discovers `.md` files in the directory (preferring `full.md`, but accepting any filename). Run `python kb_indexer.py --scan` to generate the `kb_catalog.yaml` index.

### First-time configuration

On first run, taw guides you through KB-path configuration.

### Modify configuration

```bash
# Permanently change the default KB path
/taw --set-kb /data/company-kb

# Verify config
cat ~/.config/tender-workflow/config.yaml
```

### Temporary override

```bash
# This run only; does not modify config
/taw --outline output/ --report output/ --chapter 1.3 --kb /tmp/test-kb
```

---

## KB index build

The KB index is auto-generated by `skills/taw/tools/kb_indexer.py`.

```bash
# Generate Local-KnowledgeBase directory index
/taw --build-kb-index
python skills/taw/tools/kb_indexer.py --scan
```

---

## Chapter-number format detail

taw supports four chapter-spec formats.

### Full chapter sequence

```
一 (1) → 1.1  1.2  1.3  1.4  1.5  1.6  1.7  1.8  1.9  1.10  1.11
```

### Format 1: single section

```bash
/taw output/ --chapter 1.3    # Write 1.3 Overall Design
/taw output/ --chapter 1.10   # Write 1.10 After-sales Service
```

### Format 2: full chapter

```bash
/taw output/ --chapter 一     # Write all 11 sub-sections of the technical section (1.1-1.11)
/taw output/ --chapter 1      # Same, numeric alias
```

### Format 3: range

```bash
/taw output/ --chapter 1.1-1.9      # 1.1 to 1.9, 9 sections total
/taw output/ --chapter 1.1 到 1.9     # Same, with Chinese 到
```

### Format 4: all

```bash
/taw output/ --chapter all    # Write all 11 sections
```

---

## Usage scenario examples

### Scenario 1: routine single-chapter writing (directory shorthand)

```bash
/taw output/ --chapter 1.3
```

### Scenario 2: bulk technical section writing (explicit paths)

```bash
/taw --outline output/bid_outline_20260305.docx --report output/tender_analysis_report_20260305.md --chapter 一
```

### Scenario 3: range writing

```bash
/taw output/ --chapter 1.1 到 1.9
```

### Scenario 4: multi-vendor perspective switch (--vendor)

```bash
# Write technical chapter from BoCloud's perspective
/taw output/ --chapter 1.3 --vendor "BoCloud"
```

### Scenario 5: custom search terms (--query)

```bash
/taw output/ --chapter 1.7 --query "MLPS 2.0 container security zero-trust architecture"
```

### Scenario 6: image-source control

```bash
# Use AI-generated images
/taw output/ --chapter 1.3 --image-source ai

# Use draw.io diagrams
/taw output/ --chapter 1.3 --image-source drawio

# Auto (default; picked per H3 sub-section context)
/taw output/ --chapter 1.3
```

### Scenario 7: no KB, internet only

```bash
/taw output/ --chapter 1.3 --kb-source none
```

### Scenario 8: MCP search-tool selection

```bash
# Force Tavily Search
/taw output/ --chapter 1.3 --search-tool tavily

# Force Exa Search
/taw output/ --chapter 1.3 --search-tool exa

# Auto (default)
/taw output/ --chapter 1.3
```

### Scenario 9: custom word counts and image quotas

```bash
# L2 chapter 6000 words, L3 sub-section 1200 words
/taw output/ --chapter 1.3 --l2-words 6000 --l3-words 1200

# Custom L4 / L5 sub-section words
/taw output/ --chapter 1.11 --l4-words 800 --l5-words 500

# Custom image quotas: L2 chapter 3 images, L3 sub-section 1 each
/taw output/ --chapter 1.3 --l2-images 3 --l3-images 1

# Combined: more words + more images
/taw output/ --chapter 1.3 --l2-words 6000 --l2-images 4
```

---

## Output file spec

### Location

Output path: `./drafts/`

### Naming convention

| Mode | Filename pattern | Example |
|---|---|---|
| Single section | `<num>_<name>.docx` | `1.3_overall-design.docx` |
| Full chapter | `<start>-<end>_merged.docx` | `1.1-1.11_merged.docx` |
| Range | `<start>-<end>_merged.docx` | `1.1-1.9_merged.docx` |

---

## Workflow integration

taw is the third stage in the four-role bid workflow:

```
tpl (Planner)  →  Tender doc
                       ↓
              taa (Analyst)  →  Tender analysis report + bid outline
                                          ↓
                              taw (Writer)  →  Chapter draft DOCX
                                                       ↓
                                          trv (Reviewer)  →  Review report
```

### Connecting with taa

```bash
# taa output
output/tender_analysis_report_YYYYMMDD.md
output/bid_outline_YYYYMMDD.docx

# taw call
/taw output/ --chapter 1.3
```

### Connecting with trv

```bash
# Single-chapter review
/trv drafts/5.3_overall-design.docx --type chapter --reference output/tender_analysis_report.md
```

---

## Quality assurance mechanisms

After each chapter is generated, a basic self-check runs:

| Self-check item | Pass criterion |
|---|---|
| Scoring coverage | M4 relevant scoring points 100% have substantive responses |
| M7 keyword coverage | ≥ 80% |
| Disqualification red line | Zero violations of M5 clauses and M7.5 red lines |
| Overpromise detection | Zero absolute wording |
| To-confirm tagging | All unsupported content is tagged |

---

## FAQ

**Q: After running, it can't find the analysis report or outline. What do I do?**

Use `--outline` and `--report` to specify files explicitly. If they don't exist, run `/taa <tender-doc>` first.

**Q: KB matching returns 0 hits, is that normal?**

Yes. taw automatically falls back to internet search; specific data points in generated content will be tagged `[Internet source, please verify]`.

**Q: What's the difference between `--kb-source` and `--kb`?**

- `--kb-source` controls the **source type** (AnythingLLM / local index / none)
- `--kb` specifies the **specific path** (overrides config temporarily)

**Q: The generated content is too generic, not project-specific?**

Check whether M7 in the analysis report is complete; or pass more precise search terms via `--query`.

**Q: How do I configure the AI image generation API key?**

```bash
# Env var (recommended)
export ARK_API_KEY="sk-xxxxx"

# Or config file
echo "ark_api_key: sk-xxxxx" >> ~/.config/tender-workflow/config.yaml
```

---

*taw v3.0.0 | Bid-document Writing Assistant*
