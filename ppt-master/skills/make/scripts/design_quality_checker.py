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
    content_boxes: list[Box]
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
    content_fill_ratio: float
    visible_terms: int
    evidence_items: int
    relationships: int
    claim_like_texts: int
    visible_chars: int
    repetitive_label_stacks: int
    stacked_label_count: int
    component_scale_levels: int
    dominant_component_ratio: float
    component_scale_variation: float


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
        ("semantic parent overflow", "container_overflow"),
        ("semantic component overlap/spacing", "container_overlap"),
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

    def check_file(self, svg_file: str | Path, density_contract: dict | None = None) -> dict:
        path = Path(svg_file)
        content = path.read_text(encoding="utf-8", errors="replace")
        technical = SVGQualityChecker().check_file(str(path), expected_format=self.expected_format)
        model = build_page_design_model(path, content)
        metrics = self._score_model(model, technical, density_contract)
        issues = self._issues(model, technical, metrics, density_contract)
        guidance = self._generation_guidance(model, technical, metrics, issues, density_contract)
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
            "generationGuidance": guidance,
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
                "contentFillRatio": model.content_fill_ratio,
                "visibleTerms": model.visible_terms,
                "evidenceItems": model.evidence_items,
                "relationships": model.relationships,
                "claimLikeTexts": model.claim_like_texts,
                "visibleChars": model.visible_chars,
                "repetitiveLabelStacks": model.repetitive_label_stacks,
                "stackedLabelCount": model.stacked_label_count,
                "componentScaleLevels": model.component_scale_levels,
                "dominantComponentRatio": model.dominant_component_ratio,
                "componentScaleVariation": model.component_scale_variation,
            },
            "densityContract": density_contract or {},
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

        density_contracts = _load_density_contracts(target_path if target_path.is_dir() else target_path.parent)
        pages = [
            self.check_file(path, density_contract=density_contracts.get(f"P{index:02d}"))
            for index, path in enumerate(svg_files, start=1)
        ]
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
            "deckGenerationGuidance": _deck_generation_guidance(diversity),
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

    def _score_model(self, model: PageDesignModel, technical: dict, density_contract: dict | None) -> dict[str, int]:
        return {
            "visualHierarchy": self._score_hierarchy(model),
            "semanticGrouping": self._score_grouping(model),
            "densityBalance": self._score_density(model),
            "informationDensity": self._score_information_density(model, density_contract),
            "visualFocus": self._score_visual_focus(model),
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
        if model.repetitive_label_stacks >= 3:
            base -= 16
        elif model.repetitive_label_stacks >= 2 and model.stacked_label_count >= 8:
            base -= 10
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

    def _score_information_density(self, model: PageDesignModel, density_contract: dict | None) -> int:
        if not model.texts:
            return 0
        if not density_contract:
            score = 82
            if len(model.texts) < 7 and model.visible_chars < 120:
                score -= 18
            if model.visible_terms < 4 and len(model.texts) < 10:
                score -= 16
            if model.content_fill_ratio < 0.25 and len(model.texts) < 12:
                score -= 10
            return _clamp(score)

        requirements = {
            "visibleClaimsMin": model.claim_like_texts,
            "visibleObjectsMin": model.visible_terms,
            "visibleLabelsMin": len(model.texts),
            "evidenceItemsMin": model.evidence_items,
            "relationshipsMin": model.relationships,
        }
        weights = {
            "visibleClaimsMin": 0.18,
            "visibleObjectsMin": 0.24,
            "visibleLabelsMin": 0.22,
            "evidenceItemsMin": 0.18,
            "relationshipsMin": 0.18,
        }
        ratio_score = 0.0
        for key, observed in requirements.items():
            expected = max(0, int(density_contract.get(key, 0) or 0))
            if expected <= 0:
                ratio = 1.0
            else:
                ratio = min(1.0, observed / expected)
            ratio_score += ratio * weights[key]

        fill_score = _fill_target_score(model.content_fill_ratio, density_contract.get("contentAreaFillTarget", ""))
        score = round(ratio_score * 82 + fill_score * 18)
        return _clamp(score)

    def _score_visual_focus(self, model: PageDesignModel) -> int:
        component_count = len(model.medium_components) + len(model.large_components)
        if component_count <= 2:
            return 82

        score = 82
        if model.component_scale_levels >= 3:
            score += 12
        elif model.component_scale_levels == 2:
            score += 5
        else:
            score -= 14

        if model.dominant_component_ratio >= 0.38:
            score += 12
        elif model.dominant_component_ratio <= 0.23 and component_count >= 4:
            score -= 14

        if model.component_scale_variation >= 0.62:
            score += 8
        elif model.component_scale_variation <= 0.18 and component_count >= 4:
            score -= 10

        structured_layout = not _peer_boxes_are_unstructured(model)
        if model.archetype == "card_grid":
            score -= 10
        elif structured_layout:
            score += 8
            score = max(score, 74)

        if model.repetitive_label_stacks >= 3:
            score -= 10

        return _clamp(score)

    def _score_negative_space(self, model: PageDesignModel) -> int:
        content = _union_boxes(model.content_boxes)
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

    def _issues(self, model: PageDesignModel, technical: dict, metrics: dict[str, int], density_contract: dict | None) -> list[Issue]:
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
        if _too_many_peer_boxes(model.medium_components) and _peer_boxes_are_unstructured(model):
            issues.append(
                Issue(
                    "warning",
                    "flat_peer_grid",
                    "Page uses many similarly sized peer boxes without a clear primary visual focus.",
                    {"peerBoxes": len(model.medium_components)},
                )
            )
        if model.repetitive_label_stacks >= 3 or (
            model.repetitive_label_stacks >= 2 and model.stacked_label_count >= 8
        ):
            issues.append(
                Issue(
                    "warning",
                    "repetitive_micro_label_stacks",
                    "Page uses repeated micro-label stacks as a substitute for richer diagram structure.",
                    {
                        "stackCount": model.repetitive_label_stacks,
                        "labelCount": model.stacked_label_count,
                    },
                )
            )
        if density_contract and metrics.get("informationDensity", 100) < 72:
            issues.append(
                Issue(
                    "warning",
                    "low_information_density",
                    "Page is visibly sparse compared with its source density contract.",
                    {
                        "observed": {
                            "claims": model.claim_like_texts,
                            "objects": model.visible_terms,
                            "labels": len(model.texts),
                            "evidence": model.evidence_items,
                            "relationships": model.relationships,
                            "fill": model.content_fill_ratio,
                        },
                        "expected": density_contract,
                    },
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

    def _generation_guidance(
        self,
        model: PageDesignModel,
        technical: dict,
        metrics: dict[str, int],
        issues: list[Issue],
        density_contract: dict | None,
    ) -> list[dict]:
        """Return upstream regeneration actions, not coordinate patches.

        The checker should not merely say what is wrong.  It should translate
        recurring visual symptoms into component-level generation changes the
        Executor can apply before drawing the next SVG.
        """
        issue_codes = {issue.code for issue in issues}
        guidance: list[dict] = []
        technical_issue_keys = {
            issue_key(message)
            for message in technical["warnings"] + technical["errors"]
            if issue_key(message) != "other"
        }
        if technical["errors"] or technical_issue_keys:
            guidance.append(
                {
                    "code": "repair_rendering_before_design_iteration",
                    "priority": "blocking" if technical["errors"] else "high",
                    "action": "Fix hard rendering risks first: overflow, overlap, connector intrusion, or primitive text centering. Regenerate the affected component from its semantic parent instead of nudging single coordinates.",
                    "evidence": {"technicalIssues": sorted(technical_issue_keys), "errors": len(technical["errors"])},
                }
            )
        if metrics.get("visualFocus", 100) < 72 or {"low_visual_focus", "flat_peer_grid"} & issue_codes:
            guidance.append(
                {
                    "code": "regenerate_with_visual_focus",
                    "priority": "high",
                    "action": "Recompose the page around one dominant component or asymmetric component scale. Replace equal peer-card grids with the declared archetype: bridge, matrix, layer stack, swimlane, KPI rail, or argument panel.",
                    "evidence": {
                        "archetype": model.archetype,
                        "mediumComponents": len(model.medium_components),
                        "largeComponents": len(model.large_components),
                        "componentScaleLevels": model.component_scale_levels,
                        "dominantComponentRatio": model.dominant_component_ratio,
                        "componentScaleVariation": model.component_scale_variation,
                    },
                }
            )
        if "repetitive_micro_label_stacks" in issue_codes:
            guidance.append(
                {
                    "code": "replace_repetitive_micro_label_stacks",
                    "priority": "high",
                    "action": "Do not add spacing to the same repeated cards. Convert repeated vertical pill lists into matrix rows, grouped bands, scoped decision blocks, or a causal map so density comes from structure rather than cloned labels.",
                    "evidence": {
                        "stackCount": model.repetitive_label_stacks,
                        "labelCount": model.stacked_label_count,
                    },
                }
            )
        semantic_role_gap = model.explicit_role_hits == 0 and (len(model.medium_components) + len(model.large_components)) >= 4
        if metrics.get("semanticGrouping", 100) < 70 or metrics.get("designSemantics", 100) < 70 or semantic_role_gap:
            guidance.append(
                {
                    "code": "strengthen_component_slot_semantics",
                    "priority": "medium",
                    "action": "Before redrawing, name the component tree and mark shapes/text with data-role, data-slot, data-group, and data-intent. If a text belongs to a primitive, create an explicit slot; if it is paragraph content, mark the owning content area as the left-aligned exception.",
                    "evidence": {
                        "semanticGrouping": metrics.get("semanticGrouping"),
                        "designSemantics": metrics.get("designSemantics"),
                        "slotCount": model.semantics_slots,
                        "textSlotHits": model.text_slot_hits,
                        "textCount": len(model.texts),
                    },
                }
            )
        if density_contract and metrics.get("informationDensity", 100) < 72:
            guidance.append(
                {
                    "code": "raise_visible_density_from_contract",
                    "priority": "medium",
                    "action": "Expose more source-specific claims, objects, evidence, and relationships on the slide using compact tables, chips, annotations, KPI strips, or layer labels. Speaker notes are overflow, not the default place for concrete detail.",
                    "evidence": {
                        "observed": {
                            "claims": model.claim_like_texts,
                            "objects": model.visible_terms,
                            "labels": len(model.texts),
                            "evidence": model.evidence_items,
                            "relationships": model.relationships,
                            "fill": model.content_fill_ratio,
                        },
                        "expected": density_contract,
                    },
                }
            )
        if "missing_main_message" in issue_codes or metrics.get("visualHierarchy", 100) < 70:
            guidance.append(
                {
                    "code": "restore_page_message_hierarchy",
                    "priority": "medium",
                    "action": "Regenerate with a clear page title plus subtitle/claim. Do not start from body cards before the audience can read the page's one-sentence message.",
                    "evidence": {"visualHierarchy": metrics.get("visualHierarchy")},
                }
            )
        return guidance


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
    content_boxes = _content_boxes(viewbox, texts, visual_shapes)
    content_union = _union_boxes(content_boxes)
    content_fill_ratio = round((content_union.area / (viewbox.area or 1)) if content_union else 0, 3)
    visible_text = " ".join(text.text for text in texts if not METADATA_RE.search(text.text))
    repetitive_stacks, stacked_label_count = _repetitive_label_stack_summary(semantics.shapes, viewbox)
    scale_levels, dominant_ratio, scale_variation = _component_scale_profile(medium + large)
    return PageDesignModel(
        path=path,
        viewbox=viewbox,
        texts=texts,
        content_boxes=content_boxes,
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
        content_fill_ratio=content_fill_ratio,
        visible_terms=len(_visible_terms(visible_text)),
        evidence_items=len(_evidence_items(visible_text)),
        relationships=_relationship_count(visible_text, roles, intents),
        claim_like_texts=sum(1 for text in texts if 8 <= len(text.text) <= 80 and not METADATA_RE.search(text.text)),
        visible_chars=sum(len(text.text) for text in texts if not METADATA_RE.search(text.text)),
        repetitive_label_stacks=repetitive_stacks,
        stacked_label_count=stacked_label_count,
        component_scale_levels=scale_levels,
        dominant_component_ratio=dominant_ratio,
        component_scale_variation=scale_variation,
    )


def _repetitive_label_stack_summary(shapes: list, viewbox: Box) -> tuple[int, int]:
    containers = [
        shape
        for shape in shapes
        if shape.box.area >= 8000
        and shape.box.width >= 120
        and shape.box.height >= 70
        and not _is_page_chrome_shape(shape, viewbox)
    ]
    labels = [
        shape
        for shape in shapes
        if shape.box.width >= 60
        and 12 <= shape.box.height <= 34
        and shape.box.area <= 9000
        and (
            shape.role in {"label", "badge", "tag", "tag-badge"}
            or shape.slot in {"label", "badge", "tag"}
        )
    ]
    stack_count = 0
    label_count = 0
    for container in containers:
        nested = [
            label
            for label in labels
            if container.box.contains_box(label.box, pad=1)
            and label.box.y1 >= container.box.y1 + 24
        ]
        if len(nested) < 3:
            continue
        nested.sort(key=lambda shape: (round(shape.box.x1), shape.box.y1))
        widths = [round(label.box.width / 8) * 8 for label in nested]
        x_positions = [round(label.box.x1 / 8) * 8 for label in nested]
        same_width_ratio = max(Counter(widths).values()) / len(widths)
        same_x_ratio = max(Counter(x_positions).values()) / len(x_positions)
        if same_width_ratio >= 0.75 and same_x_ratio >= 0.75:
            stack_count += 1
            label_count += len(nested)
    return stack_count, label_count


def _component_scale_profile(boxes: list[Box]) -> tuple[int, float, float]:
    """Summarize whether a page has visual depth instead of only peer boxes."""
    areas = sorted(
        [box.area for box in boxes if box.area >= 2400 and math.isfinite(box.area)],
        reverse=True,
    )
    if not areas:
        return 0, 0.0, 0.0
    dominant_pool = areas[: min(12, len(areas))]
    total = sum(dominant_pool) or 1.0
    dominant_ratio = round(dominant_pool[0] / total, 3)
    buckets = {round(math.log(max(area, 1), 1.55)) for area in dominant_pool}
    mean = total / len(dominant_pool)
    variance = sum((area - mean) ** 2 for area in dominant_pool) / len(dominant_pool)
    coefficient = math.sqrt(variance) / mean if mean else 0.0
    return len(buckets), dominant_ratio, round(coefficient, 3)


def _content_boxes(viewbox: Box, texts: list[TextItem], shapes: list) -> list[Box]:
    """Return boxes that belong to the slide body, excluding stable page chrome.

    Negative-space and fill metrics are about the authored content canvas, not
    recurring page furniture.  Counting the title, footer brand, page number, or
    decorative background makes every normal Alauda page look artificially
    full-width/full-height and hides the real layout signal.
    """
    boxes: list[Box] = []
    for text in texts:
        if _is_page_chrome_text(text, viewbox):
            continue
        boxes.append(text.box)
    for shape in shapes:
        if _is_page_chrome_shape(shape, viewbox):
            continue
        boxes.append(shape.box)
    return boxes


def _is_page_chrome_text(text: TextItem, viewbox: Box) -> bool:
    role_values = {text.role, text.slot}
    if role_values & {"page-chrome", "page-header", "page-title", "footer", "page-footer", "page-number", "brand"}:
        return True
    if METADATA_RE.search(text.text):
        return True
    if text.font_size <= 14 and text.y >= viewbox.y2 - 58:
        return True
    if text.y <= viewbox.y1 + 128 and text.font_size >= 16:
        return True
    return False


def _is_page_chrome_shape(shape, viewbox: Box) -> bool:
    role_values = {shape.role, shape.slot}
    if role_values & {"page-chrome", "page-background", "geometric-accent", "accent-bar", "page-footer", "footer"}:
        return True
    if shape.box.width >= viewbox.width * 0.86 and shape.box.height >= viewbox.height * 0.76:
        return True
    if shape.box.area <= 2200 and (
        shape.box.y1 <= viewbox.y1 + 120
        or shape.box.y2 >= viewbox.y2 - 48
    ):
        return True
    return False


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


def _peer_boxes_are_unstructured(model: PageDesignModel) -> bool:
    """Return True only when peer boxes lack route/component semantics.

    A process flow, mapping/risk table, KPI dashboard, or comparison bridge may
    legitimately contain several similarly sized components.  The anti-pattern
    is not "many boxes"; it is many boxes with no page-level role, dominant
    object, or semantic route to explain why they are peers.
    """
    structured_archetypes = {
        "process_flow",
        "matrix_table",
        "risk_matrix",
        "comparison_bridge",
        "kpi_dashboard",
        "architecture_stack",
        "code_annotation",
    }
    if model.archetype in structured_archetypes:
        return False
    structured_roles = {
        "process-step",
        "table-row",
        "table-header",
        "risk-quadrant",
        "risk-matrix",
        "bridge",
        "metric-card",
        "architecture-layer",
        "layer-stack",
    }
    if any(model.roles.get(role, 0) for role in structured_roles):
        return False
    if any(model.intents.get(intent, 0) for intent in {"process", "risk", "current", "target", "kpi"}):
        return False
    return True


def _deck_generation_guidance(diversity: dict) -> list[dict]:
    guidance: list[dict] = []
    issue_codes = {issue.get("code") for issue in diversity.get("issues", [])}
    if "low_archetype_variety" in issue_codes or "repeated_visual_archetype" in issue_codes:
        guidance.append(
            {
                "code": "rebalance_deck_archetypes",
                "priority": "high",
                "action": "Go back to spec_lock.md ## design_diversity before regenerating. Reassign repeated pages to source-matched archetypes such as matrix_table, process_flow, architecture_stack, code_annotation, kpi_dashboard, comparison_bridge, risk_matrix, or argument_thesis.",
                "evidence": {
                    "archetypeCounts": diversity.get("archetypeCounts", {}),
                    "dominantArchetype": diversity.get("dominantArchetype"),
                    "dominantRatio": diversity.get("dominantRatio"),
                },
            }
        )
    if "card_grid_overuse" in issue_codes:
        guidance.append(
            {
                "code": "reduce_card_grid_overuse",
                "priority": "high",
                "action": "Do not regenerate more pages as generic card grids. Route content into tables, bridges, layer stacks, timelines, code annotations, KPI rails, or argument pages according to source semantics.",
                "evidence": {"archetypeCounts": diversity.get("archetypeCounts", {})},
            }
        )
    return guidance


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
    if report.get("deckGenerationGuidance"):
        lines.extend(["", "### Deck Generation Guidance", ""])
        for item in report["deckGenerationGuidance"]:
            lines.append(f"- `{item['code']}` ({item['priority']}): {item['action']}")
    lines.extend(
        [
            "",
        "## Pages",
        "",
            "| File | Archetype | Score | Readiness | Low Metrics | Key Issues | Regeneration Guidance |",
            "|---|---|---:|---|---|---|---|",
        ]
    )
    for page in report["pages"]:
        low_metrics = ", ".join(f"{k}:{v}" for k, v in page["metrics"].items() if v < 70) or "-"
        issues = ", ".join(issue["code"] for issue in page["issues"][:5]) or "-"
        guidance = ", ".join(item["code"] for item in page.get("generationGuidance", [])[:4]) or "-"
        lines.append(f"| {page['file']} | {page['archetype']} | {page['score']} | {page['readiness']} | {low_metrics} | {issues} | {guidance} |")
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


def _load_density_contracts(project_or_dir: Path) -> dict[str, dict]:
    root = project_or_dir.expanduser().resolve()
    candidates = []
    if root.is_dir():
        candidates.extend([root / "spec_lock.md", root.parent / "spec_lock.md"])
    else:
        candidates.append(root)
    spec_lock = next((path for path in candidates if path.exists() and path.name == "spec_lock.md"), None)
    if not spec_lock:
        return {}
    text = spec_lock.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?ms)^##\s+density_contract\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text)
    if not match:
        return {}
    contracts: dict[str, dict] = {}
    for line in match.group("body").splitlines():
        page_match = re.match(r"\s*-\s*(P\d{2})\s*:\s*(.+)$", line)
        if not page_match:
            continue
        page, payload = page_match.groups()
        contract: dict[str, object] = {}
        key_map = {
            "visible_claims": "visibleClaimsMin",
            "visible_objects": "visibleObjectsMin",
            "visible_labels": "visibleLabelsMin",
            "evidence_items": "evidenceItemsMin",
            "relationships": "relationshipsMin",
        }
        for raw_key, normalized in key_map.items():
            value_match = re.search(rf"{raw_key}\s*>=\s*(\d+)", payload)
            if value_match:
                contract[normalized] = int(value_match.group(1))
        notes_match = re.search(r"notes_only_ratio\s*<=\s*(0(?:\.\d+)?|1(?:\.0+)?)", payload)
        if notes_match:
            contract["notesOnlyRatioMax"] = float(notes_match.group(1))
        fill_match = re.search(r"fill\s*=\s*([0-9.]+-[0-9.]+)", payload)
        if fill_match:
            contract["contentAreaFillTarget"] = fill_match.group(1)
        if contract:
            contracts[page] = contract
    return contracts


def _visible_terms(text: str) -> set[str]:
    generic = {
        "方案",
        "技术",
        "项目",
        "系统",
        "平台",
        "能力",
        "支持",
        "实现",
        "通过",
        "提供",
        "需要",
        "当前",
        "目标",
        "业务",
        "应用",
        "管理",
    }
    terms = set()
    for term in re.findall(r"[A-Za-z][A-Za-z0-9_.:/+-]{2,}|[\u4e00-\u9fff]{2,}", text):
        clean = term.strip(" ，。、；：:()（）[]【】")
        if re.fullmatch(r"[\u4e00-\u9fff]+", clean) and len(clean) > 14:
            continue
        if clean and clean not in generic and not re.fullmatch(r"\d+", clean):
            terms.add(clean.lower())
    return terms


def _evidence_items(text: str) -> set[str]:
    evidence = {
        re.sub(r"\s+", "", match.group(0))
        for match in re.finditer(r"(?:≤|≥|=|<|>)?\s*\d+(?:\.\d+)?\s*(?:%|ms|s|秒|分钟|小时|天|个|台|次|GB|MB|CPU|GPU)?", text)
        if match.group(0).strip()
    }
    for keyword in ("P95", "P99", "SLA", "RTO", "RPO", "Go/No-Go", "零事故"):
        if re.search(re.escape(keyword), text, flags=re.IGNORECASE):
            evidence.add(keyword.lower())
    return evidence


def _relationship_count(text: str, roles: Counter[str], intents: Counter[str]) -> int:
    terms = ("映射", "迁移", "依赖", "替代", "转换", "回退", "验证", "治理", "承载", "接入", "发布", "观测")
    count = sum(text.count(term) for term in terms)
    count += len(re.findall(r"->|→|=>|/|到|从", text))
    count += roles.get("process-step", 0) + roles.get("table-row", 0) + roles.get("mapping-row", 0)
    count += intents.get("process", 0) + intents.get("current", 0) + intents.get("target", 0)
    return min(24, count)


def _fill_target_score(value: float, target: str) -> float:
    match = re.match(r"\s*([0-9.]+)\s*-\s*([0-9.]+)\s*$", str(target or ""))
    if not match:
        return 0.85
    low, high = float(match.group(1)), float(match.group(2))
    if low <= value <= high:
        return 1.0
    if value < low:
        return max(0.0, 1.0 - (low - value) / max(low, 0.01))
    return max(0.0, 1.0 - (value - high) / max(1 - high, 0.01))


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
