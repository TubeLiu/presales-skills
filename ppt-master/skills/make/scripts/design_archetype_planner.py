#!/usr/bin/env python3
"""Plan visual archetypes from source Markdown before SVG generation.

The design checker can detect whether a finished deck collapsed into repeated
card grids.  This planner pushes that discipline upstream: it scans source
Markdown, detects content semantics, and proposes page-level visual archetypes
for ``spec_lock.md ## design_diversity``.

It is deliberately heuristic and transparent.  The Strategist remains
responsible for narrative judgment, but the default plan should already avoid
turning every section into the same safe layout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps

ensure_deps()


ARCHETYPES = (
    "comparison_bridge",
    "kpi_dashboard",
    "architecture_stack",
    "process_flow",
    "matrix_table",
    "argument_thesis",
    "code_annotation",
    "risk_matrix",
    "hero_argument",
    "card_grid",
)

RELATIONSHIP_TERMS = (
    "映射",
    "迁移",
    "依赖",
    "替代",
    "转换",
    "回退",
    "验证",
    "治理",
    "承载",
    "接入",
    "发布",
    "观测",
    "from",
    "to",
    "depends",
    "maps",
)

GENERIC_TERMS = {
    "方案",
    "技术",
    "项目",
    "系统",
    "平台",
    "能力",
    "支持",
    "实现",
    "进行",
    "通过",
    "提供",
    "需要",
    "包括",
    "当前",
    "目标",
    "建设",
    "分析",
    "设计",
    "要求",
    "业务",
    "应用",
    "管理",
}

DENSITY_BASELINES = {
    "comparison_bridge": {"claims": 3, "objects": 8, "labels": 12, "evidence": 2, "relationships": 3, "fill": "0.50-0.72", "notes": 0.38},
    "kpi_dashboard": {"claims": 2, "objects": 6, "labels": 12, "evidence": 4, "relationships": 1, "fill": "0.48-0.68", "notes": 0.35},
    "architecture_stack": {"claims": 3, "objects": 10, "labels": 14, "evidence": 1, "relationships": 3, "fill": "0.52-0.74", "notes": 0.40},
    "process_flow": {"claims": 3, "objects": 8, "labels": 12, "evidence": 2, "relationships": 4, "fill": "0.50-0.72", "notes": 0.38},
    "matrix_table": {"claims": 3, "objects": 10, "labels": 16, "evidence": 2, "relationships": 3, "fill": "0.54-0.76", "notes": 0.32},
    "argument_thesis": {"claims": 4, "objects": 7, "labels": 9, "evidence": 2, "relationships": 2, "fill": "0.42-0.62", "notes": 0.45},
    "code_annotation": {"claims": 2, "objects": 8, "labels": 12, "evidence": 1, "relationships": 3, "fill": "0.50-0.72", "notes": 0.35},
    "risk_matrix": {"claims": 4, "objects": 8, "labels": 14, "evidence": 2, "relationships": 3, "fill": "0.52-0.74", "notes": 0.35},
    "hero_argument": {"claims": 2, "objects": 4, "labels": 5, "evidence": 1, "relationships": 1, "fill": "0.34-0.56", "notes": 0.55},
    "card_grid": {"claims": 3, "objects": 6, "labels": 9, "evidence": 1, "relationships": 1, "fill": "0.42-0.64", "notes": 0.45},
}

SIGNAL_RULES = {
    "code_annotation": [
        r"```",
        r"\bapiVersion\b",
        r"\bkind:\s*(VirtualService|DestinationRule|Gateway|ServiceEntry|Canary)",
        r"\bYAML\b|\bCRD\b|\bkubectl\b|\bHelm\b",
        r"VirtualService|DestinationRule|CanaryDelivery",
    ],
    "matrix_table": [
        r"(?m)^\s*\|.+\|",
        r"对比维度|关键指标|目标值|能力矩阵|对象映射|映射关系",
        r"类别\s*\n\s*关键指标\s*\n\s*目标值",
    ],
    "kpi_dashboard": [
        r"≤|≥|%|P95|P99|SLA|ms|分钟|小时|零事故",
        r"建设目标|量化|验收|指标|目标值|基线",
    ],
    "architecture_stack": [
        r"架构|拓扑|分层|控制面|数据面|Sidecar|Gateway|Ingress|istiod|Envoy|观测平台层",
        r"自上而下|层次|南北向|东西向",
    ],
    "process_flow": [
        r"流程|步骤|阶段|路线|实施|交付|试点|推广|回滚流程|发布流程",
        r"第\s*[一二三四五六七八九十0-9]+\s*阶段",
    ],
    "comparison_bridge": [
        r"现状|目标态|期望状态|从.+到|替代|迁移|vs\.?|VS|对比",
        r"当前.+目标|凌晨.+白天",
    ],
    "argument_thesis": [
        r"为什么|为何|选择|判断|结论|原则|不是.+而是|核心产品选型",
        r"无法满足|关键区别|投入价值",
    ],
    "risk_matrix": [
        r"风险|约束|假设|边界|排除|影响面|回退|兜底|熔断",
        r"高风险|中风险|低风险|风险等级",
    ],
    "hero_argument": [
        r"背景|业务价值|愿景|总体目标|核心观点|一句话",
    ],
}

PREFERRED_ORDER = {
    "comparison_bridge": 10,
    "kpi_dashboard": 20,
    "architecture_stack": 30,
    "process_flow": 40,
    "matrix_table": 50,
    "argument_thesis": 60,
    "code_annotation": 70,
    "risk_matrix": 80,
    "hero_argument": 90,
    "card_grid": 100,
}


@dataclass
class Section:
    level: int
    title: str
    body: str
    order: int


@dataclass
class Candidate:
    section: Section
    archetype: str
    score: int
    signals: list[str] = field(default_factory=list)


def split_markdown_sections(markdown: str) -> list[Section]:
    matches = list(re.finditer(r"(?m)^(#{1,4})\s+(.+?)\s*$", markdown))
    sections: list[Section] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = re.sub(r"\\([_+\\-])", r"\1", match.group(2)).strip()
        body = markdown[start:end].strip()
        if title in {"目录", "Table of Contents"}:
            continue
        if len(body) < 12:
            continue
        sections.append(Section(level=len(match.group(1)), title=title, body=body, order=len(sections)))
    if not sections and markdown.strip():
        sections.append(Section(level=1, title="Source", body=markdown.strip(), order=0))
    return sections


def classify_section(section: Section) -> Candidate:
    text = f"{section.title}\n{section.body}"
    best = Candidate(section=section, archetype="card_grid", score=0, signals=[])
    for archetype, patterns in SIGNAL_RULES.items():
        score = 0
        signals: list[str] = []
        for pattern in patterns:
            hits = re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if hits:
                score += min(3, len(hits)) * 4 + 4
                signals.append(pattern)
        if archetype == "kpi_dashboard":
            score += min(16, len(re.findall(r"(?:≤|≥|%|\d+\s*(?:ms|分钟|小时|个|台))", text)) * 2)
        if archetype == "matrix_table":
            score += min(12, len(re.findall(r"(?m)^\s*\-\-\-", text)) * 2)
        if archetype == "code_annotation":
            score += min(18, len(re.findall(r"(?m)^\s{2,}[-\\w]+:", text)) * 2)
        if score > best.score:
            best = Candidate(section=section, archetype=archetype, score=score, signals=signals)
    if best.score == 0 and len(section.body) < 450:
        best = Candidate(section=section, archetype="hero_argument", score=4, signals=["short section"])
    return best


def plan_archetypes(markdown: str, page_count: int = 10) -> dict:
    sections = split_markdown_sections(markdown)
    candidates = [classify_section(section) for section in sections]
    chosen = choose_candidates(candidates, page_count=page_count)
    counts = Counter(candidate.archetype for candidate in chosen)
    pages = []
    for index, candidate in enumerate(chosen, start=1):
        ledger = build_content_ledger(candidate.section)
        density_contract = build_density_contract(candidate, ledger)
        pages.append(
            {
                "page": f"P{index:02d}",
                "sourceHeading": candidate.section.title,
                "visualArchetype": candidate.archetype,
                "score": candidate.score,
                "signals": candidate.signals[:4],
                "rationale": rationale_for(candidate),
                "contentLedger": ledger,
                "densityContract": density_contract,
            }
        )
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "pageCount": len(pages),
        "archetypeCounts": dict(sorted(counts.items())),
        "pages": pages,
        "specLockSnippet": build_spec_lock_snippet(pages),
    }


def choose_candidates(candidates: list[Candidate], page_count: int) -> list[Candidate]:
    if page_count <= 0:
        return []
    scored = sorted(
        candidates,
        key=lambda item: (
            -item.score,
            PREFERRED_ORDER.get(item.archetype, 999),
            item.section.order,
        ),
    )
    chosen: list[Candidate] = []
    used_orders: set[int] = set()

    # First pass: preserve variety by taking the strongest section per archetype.
    for archetype in ARCHETYPES:
        for candidate in scored:
            if candidate.archetype == archetype and candidate.section.order not in used_orders:
                chosen.append(candidate)
                used_orders.add(candidate.section.order)
                break
        if len(chosen) >= page_count:
            break

    # Second pass: fill remaining slots by source order so the narrative still flows.
    for candidate in sorted(candidates, key=lambda item: item.section.order):
        if len(chosen) >= page_count:
            break
        if candidate.section.order not in used_orders:
            chosen.append(candidate)
            used_orders.add(candidate.section.order)

    return sorted(chosen[:page_count], key=lambda item: item.section.order)


def rationale_for(candidate: Candidate) -> str:
    title = candidate.section.title
    archetype = candidate.archetype
    rationale = {
        "comparison_bridge": "source contrasts current and target states, so a bridge/before-after grammar is safer than a generic list",
        "kpi_dashboard": "source contains measurable targets or thresholds, so metrics should be scanned as numbers first",
        "architecture_stack": "source explains layers, control/data planes, or topology, so a stack/topology grammar is required",
        "process_flow": "source is procedural or phased, so step gates and outputs should drive layout",
        "matrix_table": "source has mapping/comparison/decision rows, so a compact matrix supports review",
        "argument_thesis": "source answers a why/decision question, so thesis plus evidence is more appropriate than cards",
        "code_annotation": "source includes declarative examples or CRD/YAML, so code panel plus annotations is required",
        "risk_matrix": "source discusses constraints, risks, or rollback, so visible risk/action structure is needed",
        "hero_argument": "source carries a single high-level message and can breathe",
        "card_grid": "source is a balanced list without stronger structural signals",
    }.get(archetype, "source semantics match this archetype")
    return f"{title}: {rationale}"


def build_spec_lock_snippet(pages: list[dict]) -> str:
    lines = [
        "## design_diversity",
        "- source: design_archetype_planner.py",
        "- target_archetypes: at least 3 visual archetypes for mixed 6+ page decks",
        "- dominant_archetype_limit: <=55%",
        "- card_grid_limit: <=45%",
    ]
    for page in pages:
        lines.append(f"- {page['page']}: {page['visualArchetype']} | {page['sourceHeading']}")
    lines.extend(
        [
            "",
            "## density_contract",
            "- source: design_archetype_planner.py",
            "- policy: visible page content must expose source objects, relationships, and evidence; speaker notes are overflow, not the default hiding place",
            "- target: avoid AI-sparse slides by giving each page visible information minimums before SVG generation",
        ]
    )
    for page in pages:
        contract = page["densityContract"]
        expose = ",".join(page["contentLedger"]["visibleObjects"][:6]) or "source-specific terms"
        lines.append(
            "- {page}: visible_claims>={claims}; visible_objects>={objects}; "
            "visible_labels>={labels}; evidence_items>={evidence}; "
            "relationships>={relationships}; notes_only_ratio<={notes:.2f}; "
            "fill={fill} | expose={expose}".format(
                page=page["page"],
                claims=contract["visibleClaimsMin"],
                objects=contract["visibleObjectsMin"],
                labels=contract["visibleLabelsMin"],
                evidence=contract["evidenceItemsMin"],
                relationships=contract["relationshipsMin"],
                notes=contract["notesOnlyRatioMax"],
                fill=contract["contentAreaFillTarget"],
                expose=expose,
            )
        )
    return "\n".join(lines)


def build_content_ledger(section: Section) -> dict:
    text = f"{section.title}\n{section.body}"
    return {
        "headlineClaim": section.title,
        "visibleObjects": extract_visible_objects(text)[:18],
        "visibleRelationships": extract_relationships(text)[:10],
        "visibleEvidence": extract_evidence_items(text)[:10],
        "visibleLabels": extract_visible_labels(section)[:24],
        "claims": extract_claims(section.body)[:8],
    }


def build_density_contract(candidate: Candidate, ledger: dict) -> dict:
    base = DENSITY_BASELINES.get(candidate.archetype, DENSITY_BASELINES["card_grid"])
    object_count = len(ledger["visibleObjects"])
    label_count = len(ledger["visibleLabels"])
    evidence_count = len(ledger["visibleEvidence"])
    relationship_count = len(ledger["visibleRelationships"])
    claim_count = len(ledger["claims"])
    richness = object_count + label_count + evidence_count + relationship_count + claim_count
    density = "dense" if richness >= 34 else "balanced" if richness >= 18 else "breathing"
    return {
        "densityLevel": density,
        "visibleClaimsMin": max(base["claims"], min(6, claim_count)),
        "visibleObjectsMin": max(base["objects"], min(14, max(4, round(object_count * 0.55)))),
        "visibleLabelsMin": max(base["labels"], min(22, max(5, round((label_count + object_count) * 0.45)))),
        "evidenceItemsMin": max(base["evidence"], min(7, evidence_count)),
        "relationshipsMin": max(base["relationships"], min(6, relationship_count)),
        "notesOnlyRatioMax": base["notes"],
        "contentAreaFillTarget": base["fill"],
        "antiSparseRule": "do not reduce the page to summary cards when the ledger contains concrete objects or evidence",
    }


def extract_visible_objects(text: str) -> list[str]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_.:/+-]{2,}|[\u4e00-\u9fff]{2,}", text)
    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        clean = term.strip(" ，。、；：:()（）[]【】")
        if not clean or clean in GENERIC_TERMS:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", clean) and len(clean) > 14:
            continue
        if re.fullmatch(r"\d+", clean):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(clean)
    return terms


def extract_relationships(text: str) -> list[str]:
    relationships: list[str] = []
    for line in text.splitlines():
        compact = line.strip(" -\t")
        if not compact:
            continue
        if "->" in compact or "→" in compact or "=>" in compact:
            relationships.append(compact)
            continue
        if any(term.lower() in compact.lower() for term in RELATIONSHIP_TERMS):
            relationships.append(compact)
    return _dedupe(relationships)


def extract_evidence_items(text: str) -> list[str]:
    evidence: list[str] = []
    for match in re.finditer(r"(?:≤|≥|=|<|>)?\s*\d+(?:\.\d+)?\s*(?:%|ms|s|秒|分钟|小时|天|个|台|次|GB|MB|CPU|GPU)?", text):
        token = re.sub(r"\s+", "", match.group(0))
        if token and token not in evidence:
            evidence.append(token)
    for keyword in ("P95", "P99", "SLA", "RTO", "RPO", "Go/No-Go", "零事故"):
        if re.search(re.escape(keyword), text, flags=re.IGNORECASE):
            evidence.append(keyword)
    return _dedupe(evidence)


def extract_visible_labels(section: Section) -> list[str]:
    labels = [section.title]
    for line in section.body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            labels.extend(part.strip() for part in stripped.strip("|").split("|") if part.strip() and set(part.strip()) != {"-"})
        elif stripped.startswith(("-", "*", "+")):
            labels.append(stripped.lstrip("-*+ ").strip())
        elif re.match(r"^\d+[.)、]\s+", stripped):
            labels.append(re.sub(r"^\d+[.)、]\s+", "", stripped))
    return _dedupe([label for label in labels if len(label) <= 48])


def extract_claims(body: str) -> list[str]:
    candidates = re.split(r"[。；;\n]+", body)
    claims = []
    for item in candidates:
        clean = re.sub(r"\s+", " ", item.strip(" -\t"))
        if 8 <= len(clean) <= 90:
            claims.append(clean)
    return _dedupe(claims)


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def resolve_markdown_target(target: Path) -> Path:
    if target.is_file():
        return target
    sources_dir = target / "sources"
    markdown_files = sorted(sources_dir.glob("*.md")) if sources_dir.exists() else sorted(target.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"No Markdown source found under {target}")
    return max(markdown_files, key=lambda path: path.stat().st_size)


def write_reports(report: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = output.with_suffix(".md")
    lines = [
        "# Design Archetype Plan",
        "",
        f"- generatedAt: {report['generatedAt']}",
        f"- pageCount: {report['pageCount']}",
        "",
        "## Archetype Counts",
        "",
        "| Archetype | Count |",
        "|---|---:|",
    ]
    for archetype, count in report["archetypeCounts"].items():
        lines.append(f"| {archetype} | {count} |")
    lines.extend(["", "## Pages", "", "| Page | Archetype | Density | Source Heading | Rationale |", "|---|---|---|---|---|"])
    for page in report["pages"]:
        density = page["densityContract"]["densityLevel"]
        lines.append(f"| {page['page']} | {page['visualArchetype']} | {density} | {page['sourceHeading']} | {page['rationale']} |")
    lines.extend(["", "## Density Contracts", "", "| Page | Claims | Objects | Labels | Evidence | Relationships | Fill |", "|---|---:|---:|---:|---:|---:|---|"])
    for page in report["pages"]:
        contract = page["densityContract"]
        lines.append(
            f"| {page['page']} | {contract['visibleClaimsMin']} | {contract['visibleObjectsMin']} | "
            f"{contract['visibleLabelsMin']} | {contract['evidenceItemsMin']} | {contract['relationshipsMin']} | "
            f"{contract['contentAreaFillTarget']} |"
        )
    lines.extend(["", "## spec_lock.md Snippet", "", "```markdown", report["specLockSnippet"], "```"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan page visual archetypes from source Markdown.")
    parser.add_argument("target", help="Markdown file or PPT Master project directory.")
    parser.add_argument("--pages", type=int, default=10, help="Maximum planned content pages.")
    parser.add_argument("--output", help="Output JSON path. Default: <project>/exports/design_archetype_plan.json or sibling JSON.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    markdown_path = resolve_markdown_target(target)
    report = plan_archetypes(markdown_path.read_text(encoding="utf-8", errors="replace"), page_count=args.pages)
    report["source"] = str(markdown_path)

    if args.output:
        output = Path(args.output).expanduser().resolve()
    elif target.is_dir():
        output = target / "exports" / "design_archetype_plan.json"
    else:
        output = markdown_path.with_name(f"{markdown_path.stem}_design_archetype_plan.json")
    write_reports(report, output)
    print(f"[design-archetype-plan] source: {markdown_path}")
    print(f"[design-archetype-plan] pages: {report['pageCount']}")
    print(f"[design-archetype-plan] archetypes: {', '.join(report['archetypeCounts'])}")
    print(f"[design-archetype-plan] report: {output.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
