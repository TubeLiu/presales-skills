#!/usr/bin/env python3
"""Page-level design quality checks for PPT Master SVG output.

The SVG quality checker catches hard rendering failures: unsupported SVG,
overflow, collisions, connector intrusions, and shape-label alignment.  This
module evaluates a different layer: whether a page has enough design semantics
to look like a human-authored client slide.

It intentionally works from general layout semantics instead of route-specific
if/else rules:

    page -> component -> slot -> text

Explicit ``data-role`` / ``data-slot`` attributes are preferred.  Geometry is
used as a fallback so legacy SVGs can still be assessed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps

ensure_deps()

from svg_finalize.layout_semantics import (  # noqa: E402
    Box,
    build_layout_semantics,
    estimate_text_width,
    text_lines,
)
from svg_quality_checker import SVGQualityChecker  # noqa: E402


METADATA_RE = re.compile(
    r"(?:样张\s*P\d+|"
    r"\b(?:platform_panorama|architecture_stack|migration_bridge|mapping_table|process_flow|timeline|"
    r"capability_canvas|comparison|evidence_argument|kpi_metrics|risk_matrix|code_sample|"
    r"screenshot_evidence|parallel_value|dense_technical|balanced_technical|breathing_argument)\b)"
)


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    evidence: dict = field(default_factory=dict)


@dataclass
class TextItem:
    text: str
    box: Box
    x: float
    y: float
    font_size: float
    anchor: str
    role: str = ""
    slot: str = ""


@dataclass
class PageDesignModel:
    path: Path
    viewbox: Box
    texts: list[TextItem]
    semantics_slots: int
    text_slot_hits: int
    explicit_role_hits: int
    shape_count: int
    visual_shapes: int
    colored_shapes: int
    medium_components: list[Box]
    large_components: list[Box]
    roles: Counter[str]
    intents: Counter[str]
    archetype: str


def issue_key(message: str) -> str:
    """Mirror the eval harness issue keys without importing private helpers."""
    mapping = [
        ("connector arrow(s) sharing a text lane", "connector_text_lane"),
        ("shape-over-text occlusion", "shape_over_text"),
        ("text container overflow", "container_overflow"),
        ("text overlap/collision", "text_overlap"),
        ("visible eval/internal metadata", "metadata_leak"),
        ("shape text centering issue", "shape_text_centering"),
        ("connector arrow(s) intruding into card/container border", "connector_border_intrusion"),
    ]
    for needle, key in mapping:
        if needle in message:
            return key
    return "other"


class DesignQualityChecker:
    """Evaluate page-level design quality and semantic execution discipline."""

    def __init__(self, expected_format: str = "ppt169") -> None:
        self.expected_format = expected_format
        self.svg_checker = SVGQualityChecker()

    def check_file(self, svg_file: str | Path) -> dict:
        path = Path(svg_file)
        content = path.read_text(encoding="utf-8", errors="replace")
        technical = SVGQualityChecker().check_file(str(path), expected_format=self.expected_format)
        model = build_page_design_model(path, content)
        metrics = self._score_model(model, technical)
        issues = self._issues(model, technical, metrics)
        score = max(0, round(sum(metrics.values()) / len(metrics)))
        readiness = (
            "release_candidate"
            if score >= 82 and not any(issue.severity == "error" for issue in issues)
            else "needs_revision"
        )
        return {
            "file": path.name,
            "path": str(path),
            "archetype": model.archetype,
            "score": score,
            "readiness": readiness,
            "metrics": metrics,
            "issues": [issue.__dict__ for issue in issues],
            "technical": {
                "passed": technical["passed"],
                "warnings": technical["warnings"],
                "errors": technical["errors"],
            },
            "model": {
                "textCount": len(model.texts),
                "shapeCount": model.shape_count,
                "visualShapes": model.visual_shapes,
                "coloredShapes": model.colored_shapes,
                "mediumComponents": len(model.medium_components),
                "largeComponents": len(model.large_components),
                "slotCount": model.semantics_slots,
                "textSlotHits": model.text_slot_hits,
                "explicitRoleHits": model.explicit_role_hits,
                "roles": dict(sorted(model.roles.items())),
                "intents": dict(sorted(model.intents.items())),
            },
        }

    def check_target(self, target: str | Path, svg_dir_name: str = "svg_final") -> dict:
        target_path = Path(target).expanduser().resolve()
        if target_path.is_file():
            svg_files = [target_path]
            svg_dir = target_path.parent
        else:
            svg_dir = target_path / svg_dir_name
            if not svg_dir.exists() and svg_dir_name == "svg_final":
                svg_dir = target_path / "svg_output"
            if not svg_dir.exists():
                svg_dir = target_path
            svg_files = sorted(svg_dir.glob("*.svg"))

        pages = [self.check_file(path) for path in svg_files]
        scores = [page["score"] for page in pages]
        issue_counts = Counter(issue["code"] for page in pages for issue in page["issues"])
        technical_counts = Counter()
        for page in pages:
            for message in page["technical"]["warnings"] + page["technical"]["errors"]:
                technical_counts[issue_key(message)] += 1
        diversity = self._deck_diversity(pages)

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "target": str(target_path),
            "svgDir": str(svg_dir),
            "totalFiles": len(pages),
            "averageScore": round(sum(scores) / len(scores), 1) if scores else 0,
            "releaseCandidates": sum(1 for page in pages if page["readiness"] == "release_candidate"),
            "needsRevision": sum(1 for page in pages if page["readiness"] == "needs_revision"),
            "issueCounts": dict(sorted(issue_counts.items())),
            "technicalIssueCounts": dict(sorted(technical_counts.items())),
            "deckDiversity": diversity,
            "pages": pages,
        }

    def _deck_diversity(self, pages: list[dict]) -> dict:
        total = len(pages)
        if total == 0:
            return {"score": 0, "archetypeCounts": {}, "issues": []}
        counts = Counter(page["archetype"] for page in pages)
        dominant, dominant_count = counts.most_common(1)[0]
        unique = len(counts)
        dominant_ratio = dominant_count / total
        entropy = _entropy(counts.values()) / max(math.log2(max(total, 2)), 1)
        score = round(40 + min(35, unique * 8) + entropy * 25 - max(0, dominant_ratio - 0.45) * 80)
        issues = []
        if total >= 6 and unique < 3:
            issues.append(
                Issue(
                    "warning",
                    "low_archetype_variety",
                    "Deck uses too few visual archetypes for a multi-page technical narrative.",
                    {"uniqueArchetypes": unique},
                ).__dict__
            )
        if total >= 6 and dominant_ratio > 0.55:
            issues.append(
                Issue(
                    "warning",
                    "repeated_visual_archetype",
                    "One visual archetype dominates the deck; this often indicates template overfitting.",
                    {"archetype": dominant, "ratio": round(dominant_ratio, 2)},
                ).__dict__
            )
        if counts.get("card_grid", 0) / total > 0.45:
            issues.append(
                Issue(
                    "warning",
                    "card_grid_overuse",
                    "Too many pages use card-grid structure; route content into diagrams, tables, flows, code, or argument pages where appropriate.",
                    {"ratio": round(counts["card_grid"] / total, 2)},
                ).__dict__
            )
        return {
            "score": _clamp(score),
            "archetypeCounts": dict(sorted(counts.items())),
            "dominantArchetype": dominant,
            "dominantRatio": round(dominant_ratio, 2),
            "issues": issues,
        }

    def _score_model(self, model: PageDesignModel, technical: dict) -> dict[str, int]:
        return {
            "visualHierarchy": self._score_hierarchy(model),
            "semanticGrouping": self._score_grouping(model),
            "densityBalance": self._score_density(model),
            "negativeSpace": self._score_negative_space(model),
            "alignmentDiscipline": self._score_alignment(technical),
            "designSemantics": self._score_semantic_coverage(model),
            "clientReadiness": self._score_client_readiness(model, technical),
        }

    def _score_hierarchy(self, model: PageDesignModel) -> int:
        if not model.texts:
            return 0
        top_texts = [text for text in model.texts if text.box.y1 <= 150]
        max_size = max(text.font_size for text in model.texts)
        median_size = _median(text.font_size for text in model.texts)
        title_like = [text for text in top_texts if text.font_size >= 28]
        ratio = max_size / max(median_size, 1)
        score = 45
        if title_like:
            score += 25
        if ratio >= 1.8:
            score += 20
        elif ratio >= 1.45:
            score += 12
        if _has_clear_subtitle(top_texts, title_like):
            score += 10
        return min(score, 100)

    def _score_grouping(self, model: PageDesignModel) -> int:
        text_count = len(model.texts)
        if text_count == 0:
            return 0
        medium = len(model.medium_components)
        large = len(model.large_components)
        base = 45
        if medium + large >= 2:
            base += 20
        if medium + large >= 4:
            base += 10
        if model.text_slot_hits / max(text_count, 1) >= 0.45:
            base += 15
        if _too_many_peer_boxes(model.medium_components):
            base -= 18
        return _clamp(base)

    def _score_density(self, model: PageDesignModel) -> int:
        text_count = len(model.texts)
        micro_count = sum(1 for text in model.texts if text.font_size <= 14)
        visual_count = model.visual_shapes
        score = 88
        if text_count > 80:
            score -= 25
        elif text_count > 58:
            score -= 14
        elif text_count < 6:
            score -= 10
        if micro_count > 34:
            score -= 18
        if visual_count > 95:
            score -= 16
        return _clamp(score)

    def _score_negative_space(self, model: PageDesignModel) -> int:
        content = _union_boxes([text.box for text in model.texts] + model.medium_components + model.large_components)
        if not content:
            return 60
        page_area = model.viewbox.area or 1
        content_ratio = content.area / page_area
        margin_left = content.x1 - model.viewbox.x1
        margin_right = model.viewbox.x2 - content.x2
        margin_top = content.y1 - model.viewbox.y1
        margin_bottom = model.viewbox.y2 - content.y2
        score = 90
        if content_ratio > 0.78:
            score -= 24
        elif content_ratio > 0.66:
            score -= 10
        if min(margin_left, margin_right) < 36:
            score -= 12
        if margin_top < 24 or margin_bottom < 28:
            score -= 10
        return _clamp(score)

    def _score_alignment(self, technical: dict) -> int:
        score = 96
        penalties = {
            "shape_text_centering": 16,
            "connector_border_intrusion": 12,
            "connector_text_lane": 14,
            "shape_over_text": 24,
            "text_overlap": 24,
            "container_overflow": 18,
        }
        for message in technical["warnings"] + technical["errors"]:
            score -= penalties.get(issue_key(message), 4)
        return _clamp(score)

    def _score_semantic_coverage(self, model: PageDesignModel) -> int:
        text_count = len(model.texts)
        if text_count == 0:
            return 0
        slot_ratio = model.text_slot_hits / text_count
        explicit_ratio = model.explicit_role_hits / max(model.shape_count + text_count, 1)
        score = 42 + min(38, int(slot_ratio * 60)) + min(20, int(explicit_ratio * 120))
        return _clamp(score)

    def _score_client_readiness(self, model: PageDesignModel, technical: dict) -> int:
        score = 92
        if technical["errors"]:
            score -= 35
        if technical["warnings"]:
            score -= min(34, len(technical["warnings"]) * 7)
        if any(METADATA_RE.search(text.text) for text in model.texts):
            score -= 30
        if not _has_main_message(model):
            score -= 16
        return _clamp(score)

    def _issues(self, model: PageDesignModel, technical: dict, metrics: dict[str, int]) -> list[Issue]:
        issues: list[Issue] = []
        if technical["errors"]:
            issues.append(Issue("error", "technical_errors", "SVG technical checker found blocking errors."))
        for key, score in metrics.items():
            if score < 70:
                issues.append(Issue("warning", f"low_{_snake(key)}", f"{key} score is low ({score})."))
        if not _has_main_message(model):
            issues.append(
                Issue(
                    "warning",
                    "missing_main_message",
                    "Page lacks a clear top-level message or title hierarchy.",
                )
            )
        if _too_many_peer_boxes(model.medium_components):
            issues.append(
                Issue(
                    "warning",
                    "flat_peer_grid",
                    "Page uses many similarly sized peer boxes without a clear primary visual focus.",
                    {"peerBoxes": len(model.medium_components)},
                )
            )
        leaked = [text.text for text in model.texts if METADATA_RE.search(text.text)]
        if leaked:
            issues.append(
                Issue(
                    "warning",
                    "visible_internal_metadata",
                    "Customer-facing canvas contains internal route/eval metadata.",
                    {"examples": leaked[:3]},
                )
            )
        for message in technical["warnings"]:
            key = issue_key(message)
            if key != "other":
                issues.append(Issue("warning", key, message))
        return issues


def build_page_design_model(path: Path, content: str) -> PageDesignModel:
    viewbox = _parse_viewbox(content) or Box(0, 0, 1280, 720)
    semantics = build_layout_semantics(content)
    texts = _extract_text_items(content)
    text_slot_hits = sum(1 for text in texts if any(slot.box.contains_point(text.x, text.y, pad=2) for slot in semantics.slots))
    explicit_role_hits = sum(1 for text in texts if text.role or text.slot)
    explicit_role_hits += sum(1 for shape in semantics.shapes if shape.role or shape.slot)
    visual_shapes = [
        shape
        for shape in semantics.shapes
        if shape.box.area >= 120
        and not (shape.box.width >= viewbox.width * 0.88 and shape.box.height >= viewbox.height * 0.82)
    ]
    colored_shapes = [shape for shape in visual_shapes if _is_visible_fill(shape.fill)]
    roles = Counter(_extract_data_values(content, "role"))
    roles.update(_extract_data_values(content, "slot"))
    intents = Counter(_extract_data_values(content, "intent"))
    medium = [
        shape.box
        for shape in visual_shapes
        if 2600 <= shape.box.area <= 85000
        and shape.box.width >= 48
        and shape.box.height >= 24
    ]
    large = [
        shape.box
        for shape in visual_shapes
        if shape.box.area > 85000
        and shape.box.width < viewbox.width * 0.92
        and shape.box.height < viewbox.height * 0.82
    ]
    archetype = classify_archetype(path, roles, intents, medium, large, texts, content)
    return PageDesignModel(
        path=path,
        viewbox=viewbox,
        texts=texts,
        semantics_slots=len(semantics.slots),
        text_slot_hits=text_slot_hits,
        explicit_role_hits=explicit_role_hits,
        shape_count=len(semantics.shapes),
        visual_shapes=len(visual_shapes),
        colored_shapes=len(colored_shapes),
        medium_components=medium,
        large_components=large,
        roles=roles,
        intents=intents,
        archetype=archetype,
    )


def classify_archetype(
    path: Path,
    roles: Counter[str],
    intents: Counter[str],
    medium_components: list[Box],
    large_components: list[Box],
    texts: list[TextItem],
    content: str,
) -> str:
    """Classify the page's visual grammar from semantic roles first."""
    tokens = " ".join(
        [path.stem.lower()]
        + list(roles.keys())
        + list(intents.keys())
        + [text.text.lower() for text in texts[:12]]
    )
    if roles.get("table") or roles.get("table-header") or roles.get("table-row") or roles.get("header-cell"):
        return "matrix_table"
    if "code" in roles or "terminal" in roles or "yaml" in tokens or "virtualservice" in tokens:
        return "code_annotation"
    if roles.get("process-step", 0) >= 3 or "process" in intents or "流程" in tokens:
        return "process_flow"
    if roles.get("metric-card", 0) >= 3 or "kpi" in intents or re.search(r"[≤≥]\s*\d|%|sla", tokens):
        return "kpi_dashboard"
    if any(key in roles for key in ("layer-stack", "layer-header", "architecture-layer")) or "架构" in tokens or "architecture" in tokens:
        return "architecture_stack"
    if {"current", "target"} & set(intents) or "bridge" in roles or "现状" in tokens and "目标" in tokens:
        return "comparison_bridge"
    if roles.get("risk-quadrant", 0) >= 2 or "risk" in intents or "风险" in tokens and "矩阵" in tokens:
        return "risk_matrix"
    if roles.get("thesis") or "why" in intents or "为什么" in tokens or "判断" in tokens:
        return "argument_thesis"
    if _too_many_peer_boxes(medium_components) or roles.get("content-card", 0) >= 4:
        return "card_grid"
    if large_components and len(texts) <= 12:
        return "hero_argument"
    return "custom_layout"


def _extract_text_items(content: str) -> list[TextItem]:
    items: list[TextItem] = []
    for match in re.finditer(r"<text\b([^>]*)>(.*?)</text>", content, re.IGNORECASE | re.DOTALL):
        attrs = match.group(1) or ""
        x = _attr_float(attrs, "x")
        y = _attr_float(attrs, "y")
        if x is None or y is None:
            continue
        font_size = _attr_float(attrs, "font-size", 16.0) or 16.0
        anchor = (_attr_value(attrs, "text-anchor") or "start").lower()
        role = (_attr_value(attrs, "data-role") or "").lower()
        slot = (_attr_value(attrs, "data-slot") or "").lower()
        lines = _line_payloads(match.group(2) or "")
        if not lines:
            continue
        for index, (line, lx, ly) in enumerate(lines):
            tx = x if lx is None else lx
            ty = y + index * font_size * 1.25 if ly is None else ly
            width = estimate_text_width(line, font_size)
            if anchor == "middle":
                x1, x2 = tx - width / 2, tx + width / 2
            elif anchor == "end":
                x1, x2 = tx - width, tx
            else:
                x1, x2 = tx, tx + width
            box = Box(x1, ty - font_size * 0.85, x2, ty + font_size * 0.25)
            items.append(TextItem(line, box, tx, ty, font_size, anchor, role, slot))
    return items


def _line_payloads(inner: str) -> list[tuple[str, float | None, float | None]]:
    tspan_matches = list(re.finditer(r"<tspan\b([^>]*)>(.*?)</tspan>", inner, re.IGNORECASE | re.DOTALL))
    if tspan_matches:
        payloads = []
        for match in tspan_matches:
            line = re.sub(r"<[^>]+>", "", match.group(2))
            line = re.sub(r"\s+", " ", line).strip()
            if not line:
                continue
            attrs = match.group(1) or ""
            payloads.append((line, _attr_float(attrs, "x"), _attr_float(attrs, "y")))
        return payloads
    return [(line, None, None) for line in text_lines(inner)]


def write_reports(output_dir: Path, report: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "design_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# PPT Master Design Quality Report",
        "",
        f"- generatedAt: {report['generatedAt']}",
        f"- target: `{report['target']}`",
        f"- svgDir: `{report['svgDir']}`",
        f"- averageScore: {report['averageScore']}",
        f"- releaseCandidates: {report['releaseCandidates']}/{report['totalFiles']}",
        f"- diversityScore: {report['deckDiversity']['score']}",
        "",
        "## Deck Diversity",
        "",
        f"- dominantArchetype: {report['deckDiversity']['dominantArchetype']} ({report['deckDiversity']['dominantRatio']})",
        "",
        "| Archetype | Count |",
        "|---|---:|",
    ]
    for archetype, count in report["deckDiversity"]["archetypeCounts"].items():
        lines.append(f"| {archetype} | {count} |")
    if report["deckDiversity"]["issues"]:
        lines.extend(["", "### Diversity Issues", ""])
        for issue in report["deckDiversity"]["issues"]:
            lines.append(f"- `{issue['code']}`: {issue['message']}")
    lines.extend(
        [
            "",
        "## Pages",
        "",
            "| File | Archetype | Score | Readiness | Low Metrics | Key Issues |",
            "|---|---|---:|---|---|---|",
        ]
    )
    for page in report["pages"]:
        low_metrics = ", ".join(f"{k}:{v}" for k, v in page["metrics"].items() if v < 70) or "-"
        issues = ", ".join(issue["code"] for issue in page["issues"][:5]) or "-"
        lines.append(f"| {page['file']} | {page['archetype']} | {page['score']} | {page['readiness']} | {low_metrics} | {issues} |")
    if report["issueCounts"]:
        lines.extend(["", "## Issue Counts", "", "| Issue | Count |", "|---|---:|"])
        for key, count in report["issueCounts"].items():
            lines.append(f"| {key} | {count} |")
    (output_dir / "design_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_viewbox(content: str) -> Box | None:
    match = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        return None
    nums = [float(part) for part in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]
    if len(nums) != 4:
        return None
    x, y, w, h = nums
    return Box(x, y, x + w, y + h)


def _attr_value(attrs: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', attrs, re.IGNORECASE | re.DOTALL)
    return match.group(2) if match else None


def _attr_float(attrs: str, name: str, default: float | None = None) -> float | None:
    value = _attr_value(attrs, name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _is_visible_fill(fill: str) -> bool:
    value = (fill or "").strip().upper()
    return value not in {"", "NONE", "#FFFFFF", "WHITE", "TRANSPARENT"}


def _extract_data_values(content: str, name: str) -> list[str]:
    values: list[str] = []
    for _quote, value in re.findall(rf'\bdata-{name}\s*=\s*(["\'])(.*?)\1', content, re.IGNORECASE | re.DOTALL):
        value = value.strip().lower()
        if value:
            values.append(value)
    return values


def _median(values: Iterable[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _has_clear_subtitle(top_texts: list[TextItem], title_like: list[TextItem]) -> bool:
    if not title_like:
        return False
    title_bottom = max(text.box.y2 for text in title_like)
    return any(title_bottom <= text.box.y1 <= title_bottom + 70 and 14 <= text.font_size <= 24 for text in top_texts)


def _has_main_message(model: PageDesignModel) -> bool:
    return any(text.font_size >= 28 and text.box.y1 <= 150 for text in model.texts)


def _too_many_peer_boxes(boxes: list[Box]) -> bool:
    if len(boxes) < 6:
        return False
    buckets = Counter((round(box.width / 20) * 20, round(box.height / 20) * 20) for box in boxes)
    return any(count >= 6 for count in buckets.values())


def _union_boxes(boxes: Iterable[Box]) -> Box | None:
    boxes = [box for box in boxes if box.area > 0 and math.isfinite(box.area)]
    if not boxes:
        return None
    return Box(min(box.x1 for box in boxes), min(box.y1 for box in boxes), max(box.x2 for box in boxes), max(box.y2 for box in boxes))


def _snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _entropy(values: Iterable[int]) -> float:
    values = [value for value in values if value > 0]
    total = sum(values)
    if total <= 0:
        return 0.0
    return -sum((value / total) * math.log2(value / total) for value in values)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run page-level design quality checks on PPT Master SVG output.")
    parser.add_argument("target", help="SVG file, SVG directory, or PPT Master project directory.")
    parser.add_argument("--svg-dir", default="svg_final", help="SVG directory under a project (default: svg_final, fallback: svg_output).")
    parser.add_argument("--format", default="ppt169", help="Expected canvas format.")
    parser.add_argument("--output-dir", help="Optional directory for design_report.md/json.")
    args = parser.parse_args()

    checker = DesignQualityChecker(expected_format=args.format)
    report = checker.check_target(args.target, svg_dir_name=args.svg_dir)

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path(args.target).expanduser().resolve() / "exports" / "design_quality"
    write_reports(output_dir, report)
    print(f"[design-quality] files: {report['totalFiles']}")
    print(f"[design-quality] averageScore: {report['averageScore']}")
    print(f"[design-quality] diversityScore: {report['deckDiversity']['score']}")
    print(f"[design-quality] releaseCandidates: {report['releaseCandidates']}/{report['totalFiles']}")
    print(f"[design-quality] report: {output_dir / 'design_report.md'}")
    return 0 if report["needsRevision"] == 0 and not report["deckDiversity"]["issues"] else 1


if __name__ == "__main__":
    sys.exit(main())
