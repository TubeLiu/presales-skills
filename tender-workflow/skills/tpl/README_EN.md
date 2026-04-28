# Tender Planner — Tender-planning Assistant

[中文](./README.md) | **English**

> One command, from product feature list to a tender technical spec + scoring rules with no control-bid traces.

**Tender Planner** is a **Claude Code** AI Skill built for the buyer side. It auto-converts a vendor product feature list into a buyer-side tender technical spec and scoring rules. Its core capability is **anti-control-bid conversion** — strip brand traces, neutralize terminology, rationalize metrics — producing natural, compliant tender documents.

## Why use it

| Traditional approach | With Tender Planner |
|---|---|
| Manually rewrite product feature descriptions, easily leaving control-bid traces | AI auto-runs the anti-control-bid conversion; zero brand residue |
| Decide metric reasonableness by intuition, easily challenged | Metric rationalization (lower-bound expression, 70-85% float) |
| Scoring rules disconnected from technical spec | Auto-map scoring dimensions from the technical spec, with cross-checking |
| Different industries have different requirements, hard to balance | 4 industry templates (government / finance / SOE / generic enterprise) |
| Same template for big and small projects | 4 detail levels (detailed / standard / general / brief) |

## Highlights

**Anti-control-bid conversion (core capability)** — 4-step transformation: term neutralization (strip brand names) → metric rationalization (lower-bound expression) → requirement generalization (function-result-oriented) → distribution balancing (multi-domain coverage), with an auto-self-check report.

**Forced inclusion of control points** — items tagged "control point" in the product feature description are exempt from level compression, retain core technical metrics, and are prioritized as high-weight scoring items.

**Industry-template differentiation** — 4 industry templates auto-inject industry-specific sections: government (cybersecurity classification / domestic IT), finance (active-active DR / regulatory compliance), SOE (autonomy / localization), generic enterprise (flexible deployment / fast delivery).

**Auto-generated scoring rules** — auto-map technical scoring dimensions from the spec; quantitative requirements → objective scoring items, descriptive requirements → subjective scoring items, with mandatory↔scoring cross-check.

## Usage

```bash
# Basic usage (government, standard detail)
/tpl features.txt --template government

# With project background, finance, detailed
/tpl features.txt --project overview.txt --template finance --level detailed

# Use KB product index
/tpl --kb --template soe --level brief

# File + KB combined input, technical spec only
/tpl features.txt --kb --template enterprise --no-scoring

# Help
/tpl -h
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `<product-feature-list>` | positional | Required (or `--kb`). Product feature file (.txt / .md / .xlsx / .pdf) |
| `--kb` | flag | Optional. Use the KB product index; combinable with file input |
| `--project <file>` | path | Optional. Project overview (background, budget, scale) |
| `--template <industry>` | string | Required. Industry type (see table below) |
| `--level <level>` | string | Optional, default `standard`. Detail level (see table below) |
| `--no-scoring` | flag | Optional. Skip scoring rules; generate technical spec only |
| `-h, --help` | flag | Optional. Show help |

### Industry templates

| Template | Use case | Industry-specific sections | Tech weight |
|---|---|---|---|
| `government` | Government / public-sector | Cybersecurity classification, domestic IT requirements | 50% |
| `finance` | Bank / insurance / securities | Finance-grade HA, finance-grade security, regulatory compliance | 50% |
| `soe` | Central / state-owned enterprises | Autonomous / controllable tech stack, localization, long-term tech support | 45% |
| `enterprise` | Private / foreign-invested enterprises | Flexible deployment, fast delivery, cost optimization | 40% |

### Detail levels

| Level | Technical spec pages | Functional items | Use case |
|---|---|---|---|
| `detailed` | 15-20 pages | 40-60 items | Large projects > 5M RMB |
| `standard` (default) | 8-12 pages | 15-25 items | Medium projects 1-5M RMB |
| `general` | 4-6 pages | 8-12 items | Small projects 0.5-1M RMB |
| `brief` | 2-3 pages | 5-8 items | < 0.5M RMB or internal reference |

## Workflow

```
Phase 0  Parse args → read product feature list (file / KB / combined) → load industry template
Phase 1  Feature analysis → identify control points → extract quantitative metrics → build feature registry
Phase 2  Anti-control-bid conversion (core) → term neutralization → metric rationalization → requirement generalization → distribution balancing → self-check
Phase 3  Technical spec generation → control depth by level → inject industry-specific sections → consistency check
Phase 4  Scoring rules generation → map scoring dimensions from spec → cross-check (unless --no-scoring)
Phase 5  DOCX output → final anti-control-bid check → file delivery
```

Output files are saved in `./output/tpl/` (CLI environment).

## Output files

| Mode | Filename |
|---|---|
| With scoring rules (default) | `Technical_Spec_and_Scoring_<project>_<timestamp>.docx` |
| Technical spec only (`--no-scoring`) | `Technical_Spec_<project>_<timestamp>.docx` |

Document structure: cover → TOC → Part 1: Technical spec and requirements → Part 2: Scoring rules (if any)

## Integration with trv

After tpl generation, deep review through trv is recommended:

```bash
# Step 1: Generate technical spec and scoring rules
/tpl features.txt --template government

# Step 2: Review (anti-control-bid compliance + scoring-rules compliance + internal consistency)
/trv output/tpl/Technical_Spec_and_Scoring_<project>_20260313.docx --type tender_doc
```

**Division of labor**:

- **tpl's anti-control-bid self-check** (during generation): brand-residue check, distribution-concentration check, requirement-level-ratio check
- **trv's deep review** (during review): in-depth anti-control-bid compliance review, mapping check between technical scoring and technical spec, internal-consistency risk identification

## Project structure

```
tpl/
├── README.md                    # This file
├── SKILL.md                     # Claude Code Skill main file (full Phase 0-5 prompt)
├── prompts/
│   ├── anti_control.yaml        # Anti-control-bid conversion rules (core)
│   ├── level_rules.yaml         # 4-level detail definitions
│   ├── technical.yaml           # Technical spec writing rules
│   └── scoring.yaml             # Scoring-rules design rules
└── templates/
    ├── README.md                # Template usage guide (detailed)
    ├── government.yaml          # Government template
    ├── finance.yaml             # Finance template
    ├── soe.yaml                 # SOE template
    └── enterprise.yaml          # Generic enterprise template
```

## Version

**Current**: v2.0.0 · **Updated**: 2026-03-13 · **Maintainer**: 刘子佼 tubeliu@gmail.com
