# trv — Tender Review Assistant

[中文](./README.md) | **English**

**trv** (Tender Reviewer) performs multi-axis review on tender documents, analysis reports, bid outlines, chapter drafts, and complete bids.

**Version**: v1.5.0 | **Detailed docs**: [SKILL.md](./SKILL.md)

---

## Quick start

```bash
# Review tender doc (buyer self-check)
/trv tender.docx --type tender_doc

# Review analysis report
/trv output/analysis_report.md --type analysis --reference tender.pdf

# Review bid outline
/trv output/bid_outline.docx --type outline --reference output/analysis_report.md

# Review chapter draft
/trv drafts/1.3_tech_solution.md --type chapter --reference output/analysis_report.md

# Review complete bid (final pre-submission check)
/trv drafts/full_bid.docx --type full_bid --reference tender.pdf

# Auto-generate revised DOCX after review
/trv drafts/full_bid.docx --type full_bid --reference tender.docx --level all --revise-docx --revise-scope must

# Quick check (critical issues only)
/trv tender.docx --type tender_doc --level critical

# Check a single dimension only
/trv outline.docx --type outline --reference analysis.md --focus scoring
```

---

## Parameter reference

| Parameter | Type | Description |
|---|---|---|
| `<file>` | path | **Required**. File to review (PDF/DOCX/Markdown) |
| `--type` | string | **Required**. `tender_doc` / `analysis` / `outline` / `chapter` / `full_bid` |
| `--reference` | path | Optional but recommended. Reference file for cross-checking |
| `--level` | string | Optional, default `all`. `critical` / `high` / `all` |
| `--focus` | string | Optional. `completeness` / `compliance` / `scoring` / `risk` |
| `--revise-docx` | flag | Optional. Auto-generate revised DOCX after review (only effective for `.docx` input) |
| `--revise-scope` | string | Optional. `must` / `all`, default `must` |

### Review type and recommended reference

| Review type | Stage | Recommended `--reference` |
|---|---|---|
| `tender_doc` | Tender doc finalization | None |
| `analysis` | After taa analysis | tender.pdf |
| `outline` | After outline generation | analysis_report.md |
| `chapter` | After taw writing | analysis_report.md |
| `full_bid` | Pre-submission | tender.pdf |

### Review level

| Level | Scope | Estimated time |
|---|---|---|
| `critical` | Critical issues only | 1-2 min |
| `high` | Critical + major issues | 3-5 min |
| `all` | Full check (default) | 5-10 min |

### Four review dimensions

| Dimension | Focus |
|---|---|
| `completeness` | Section / element completeness |
| `compliance` | Regulation / standard compliance |
| `scoring` | Alignment with scoring criteria |
| `risk` | Disqualification / performance / dispute risks |

---

## Output format

- **Filename**: `review_report_<type>_<timestamp>.md`
- **Location**: `./output/trv/`
- **Structure**: Conclusion → detailed results (4 dimensions) → issue list (by severity) → revision priority
- **Auto-revision output**: `./output/trv/<original-name>_revised_<timestamp>.docx` (when `--revise-docx` is enabled and input is supported)

Auto-revision uses **AI-driven** mode: Claude generates revision instructions on the fly during review, then a Python tool executes generic DOCX operations. Supports paragraph replacement (preserving formatting), table-cell replacement (by header position), full-text replacement, and paragraph insert / delete.

Fallback rules:

- Input is not `.docx`: skip revision, do not interrupt review
- Review type is not `outline` / `chapter` / `full_bid`: skip revision, do not interrupt review
- Some revision instructions don't match: matched instructions still apply; unmatched ones are listed in the output
- Revision encoding check fails: revised file is preserved with a manual-handling notice

---

## Workflow integration

```
Buyer:  tpl → trv(tender_doc) → Publish tender
Bidder: taa → trv(analysis) → trv(outline) → taw → trv(chapter) → trv(full_bid) → Submit
```

---

## Version history

| Version | Date | Major changes |
|---|---|---|
| v1.5.0 | 2026-04-07 | Refactored to AI-driven smart revision; removed all hardcoded rules; supports 6 instruction types |
| v1.4.1 | 2026-04-07 | Added `--revise-docx` / `--revise-scope`, auto-generates revised DOCX after review |
| v1.3.0 | 2026-04-02 | Adapted to taa v2.1-2.4 and taw v1.8 capability updates |
| v1.2.0 | 2026-03-13 | tender_doc aligned with tpl v2.0 (tech spec + scoring rules) |
| v1.1.0 | 2026-03-10 | outline / full_bid switched to dynamic relationship checks; removed non-technical-section review |
| v1.0.0 | 2026-03-10 | Initial version; 5 review types, 4 review dimensions |

> For detailed review-type explanations, dimension specifics, and scenario examples, see [SKILL.md](./SKILL.md).
