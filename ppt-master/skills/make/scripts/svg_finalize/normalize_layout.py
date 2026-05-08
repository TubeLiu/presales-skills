"""Normalize semantic layout slots before PPTX export.

The old pass operated directly on rect/color/height combinations.  This pass
uses the shared layout semantics layer instead:

component -> slot -> text

Shape geometry still matters, but only as fallback evidence when explicit
``data-role`` / ``data-slot`` metadata is absent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from svg_finalize.layout_semantics import (
    Box,
    ShapeNode,
    SlotNode,
    TextNode,
    build_layout_semantics,
    estimate_text_width,
    visual_text_center_x,
)


SLOT_TEXT_X_INSET = 3.0
SLOT_PARENT_INSET = 6.0
MIN_SLOT_FONT_SIZE = 8.5
SLOT_FIT_BUFFER = 0.75
COMPONENT_CONTENT_PADDING = 8.0
COMPONENT_SPILL_TOLERANCE = 48.0
FOOTER_ZONE_MARGIN = 40.0
SEMANTIC_SIBLING_MIN_GAP = 12.0
SEMANTIC_SIBLING_MIN_AXIS_OVERLAP = 0.22
COLLISION_MIN_OVERLAP_AREA = 32.0
COLLISION_RESOLVE_MAX_ITERATIONS = 3
COMPONENT_EMPHASIS_MIN_FONT_SIZE = 24.0
COMPONENT_EMPHASIS_TOP_BAND_RATIO = 0.42
COMPONENT_EMPHASIS_MIN_WIDTH_RATIO = 0.32


def normalize_colored_block_text_in_file(svg_file: Path, verbose: bool = False) -> int:
    content = svg_file.read_text(encoding="utf-8")
    # Strip decorative overflow BEFORE normalize — otherwise normalize
    # grows content cards to contain background circles/ellipses that
    # extend past the viewBox.
    content, clip_count = clip_viewbox_overflow(content)
    processed, count = normalize_colored_block_text(content)
    count += clip_count
    if count:
        svg_file.write_text(processed, encoding="utf-8")
        if verbose:
            print(f"   [OK] {svg_file.name}: {count} semantic layout text item(s) normalized")
    return count


def normalize_colored_block_text(content: str) -> tuple[str, int]:
    semantics = build_layout_semantics(content)
    replacements: Dict[int, str] = {}
    insertions: Dict[int, List[str]] = {}

    for slot in semantics.slots:
        if slot.policy == "center":
            _normalize_center_slot(slot, semantics.shapes, replacements, insertions)
        elif slot.policy == "center-stack":
            _normalize_stack_slot(slot, semantics.shapes, replacements)

    _normalize_component_content_bounds(semantics, replacements)
    _normalize_direct_component_emphasis_alignment(semantics, replacements)
    _normalize_direct_component_text_fit(semantics, replacements)

    change_count = len(replacements)
    if replacements or insertions:
        content = _apply_replacements_and_insertions(content, replacements, insertions)

    spacing_replacements: Dict[int, str] = {}
    _normalize_semantic_sibling_spacing(build_layout_semantics(content), spacing_replacements)
    if spacing_replacements:
        content = _apply_replacements_and_insertions(content, spacing_replacements, {})
        change_count += len(spacing_replacements)

    # Resolve any remaining component-on-component overlaps created by
    # earlier passes (e.g. _normalize_component_content_bounds growing a
    # component into a neighbour).
    collision_replacements: Dict[int, str] = {}
    _resolve_component_collisions(build_layout_semantics(content), collision_replacements)
    if collision_replacements:
        content = _apply_replacements_and_insertions(content, collision_replacements, {})
        change_count += len(collision_replacements)

    return content, change_count


def _normalize_center_slot(
    slot: SlotNode,
    shapes: List[ShapeNode],
    replacements: Dict[int, str],
    insertions: Dict[int, List[str]],
) -> None:
    if not slot.texts:
        return

    if len(slot.texts) == 1:
        text = slot.texts[0]
        target_box = _fit_slot_box_to_text(slot, text, shapes, replacements)
        font_size = _font_size_for_slot(text, target_box)
        replacements[text.start] = _centered_text_tag(text, target_box.cx, target_box.cy, font_size)
        return

    if slot.box.height > 80:
        return

    sorted_texts = sorted(slot.texts, key=visual_text_center_x)
    bounds = _virtual_slot_bounds(slot.box, sorted_texts)
    slot_rects = []
    for index, (text, (x1, x2)) in enumerate(zip(sorted_texts, bounds)):
        replacements[text.start] = _centered_text_tag(text, (x1 + x2) / 2, slot.box.cy)
        slot_rects.append(
            _slot_rect_tag(
                x=x1,
                y=slot.box.y1,
                width=x2 - x1,
                height=slot.box.height,
                fill=slot.shape.fill,
                slot_index=index,
            )
        )
    if slot_rects and not slot.shape.is_transparent_slot:
        insertions.setdefault(slot.shape.end, []).extend(slot_rects)


def _normalize_stack_slot(
    slot: SlotNode,
    shapes: List[ShapeNode],
    replacements: Dict[int, str],
) -> None:
    child_badges = [
        shape
        for shape in shapes
        if shape is not slot.shape
        and slot.box.contains_box(shape.box)
        and _is_neutral_badge_shape(shape)
    ]
    if len(slot.texts) < 2:
        return

    assigned_text_starts = set()
    items: list[dict] = []
    for badge in sorted(child_badges, key=lambda shape: (shape.box.y1, shape.box.x1)):
        badge_texts = [
            text
            for text in slot.texts
            if badge.box.contains_point(text.x, text.y)
        ]
        if not badge_texts:
            continue
        for text in badge_texts:
            assigned_text_starts.add(text.start)
        items.append({"kind": "badge", "shape": badge, "texts": badge_texts})

    for text in slot.texts:
        if text.start not in assigned_text_starts:
            items.append({"kind": "text", "text": text})

    if len(items) < 2:
        return

    items.sort(key=_stack_item_center_y)
    group_y1 = min(_stack_item_bounds(item)[0] for item in items)
    group_y2 = max(_stack_item_bounds(item)[1] for item in items)
    dy = slot.box.cy - ((group_y1 + group_y2) / 2)

    for item in items:
        if item["kind"] == "badge":
            badge = item["shape"]
            badge_x = slot.box.cx - badge.box.width / 2
            badge_y = badge.box.y1 + dy
            replacements[badge.start] = _shape_tag_with_xy(badge, badge_x, badge_y)
            for text in item["texts"]:
                target_box = Box(badge_x, badge_y, badge_x + badge.box.width, badge_y + badge.box.height)
                font_size = _font_size_for_slot(text, target_box)
                replacements[text.start] = _centered_text_tag(text, slot.box.cx, badge_y + badge.box.height / 2, font_size)
        else:
            text = item["text"]
            replacements[text.start] = _centered_text_tag(text, slot.box.cx, text.y + dy)


def _fit_slot_box_to_text(
    slot: SlotNode,
    text: TextNode,
    shapes: List[ShapeNode],
    replacements: Dict[int, str],
) -> Box:
    """Expand a direct semantic slot when its single-line label needs room.

    This keeps the repair at the component -> slot -> text level.  It never
    keys off strings, colors, page numbers, or template-specific coordinates:
    if a label-like slot carries one text item and has room inside its semantic
    parent, the slot may grow up to the parent's inner width before the text is
    reduced.
    """
    box = slot.box
    text_width = estimate_text_width(text.text, text.font_size, text.font_weight)
    required_width = text_width + SLOT_TEXT_X_INSET * 2 + SLOT_FIT_BUFFER
    if required_width <= box.width or slot.shape.kind != "rect":
        return box

    parent = _nearest_component_parent(slot.shape, shapes)
    if not parent:
        return box

    max_x1 = parent.box.x1 + SLOT_PARENT_INSET
    max_x2 = parent.box.x2 - SLOT_PARENT_INSET
    max_width = max(max_x2 - max_x1, box.width)
    target_width = min(required_width, max_width)
    if target_width <= box.width:
        return box

    x1 = box.cx - target_width / 2
    x1 = max(max_x1, min(x1, max_x2 - target_width))
    target_box = Box(x1, box.y1, x1 + target_width, box.y2)
    replacements[slot.shape.start] = _shape_tag_with_box(slot.shape, target_box)
    return target_box


def _font_size_for_slot(text: TextNode, box: Box) -> float:
    available_width = max(box.width - SLOT_TEXT_X_INSET * 2 - SLOT_FIT_BUFFER, 1.0)
    text_width = estimate_text_width(text.text, text.font_size, text.font_weight)
    if text_width <= available_width:
        return text.font_size
    return max(MIN_SLOT_FONT_SIZE, text.font_size * available_width / text_width)


def _nearest_component_parent(shape: ShapeNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    candidates = [
        candidate
        for candidate in shapes
        if candidate is not shape
        and candidate.box.area > shape.box.area * 1.18
        and candidate.box.contains_box(shape.box, pad=1)
        and _is_component_parent(candidate)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item.box.area)


def _is_component_parent(shape: ShapeNode) -> bool:
    if shape.role in {
        "content-card",
        "bridge",
        "process-step",
        "metric-card",
        "risk-quadrant",
        "risk-matrix",
        "table",
        "mapping-row",
        "architecture-layer",
        "layer-stack",
        "callout-content",
        "section",
        "panel",
    }:
        return True
    return shape.slot in {"panel", "layer", "body-slot"}


def _is_semantic_layout_box(shape: ShapeNode) -> bool:
    if _is_component_parent(shape):
        return True
    if shape.role in {"label", "header", "table-header", "header-cell", "table-cell", "badge", "tag", "label-slot"}:
        return True
    if shape.slot in {"label", "header", "cell", "badge", "tag"}:
        return True
    return False


def _is_page_or_decorative(shape: ShapeNode) -> bool:
    if shape.role in {
        "page-background",
        "background",
        "geometric-accent",
        "decorative-accent",
        "decoration",
        "accent-background",
        "accent-bar",
    }:
        return True
    if shape.fill_opacity < 0.1:
        return True
    if shape.kind == "rect" and shape.box.width >= 1000 and shape.box.height >= 600:
        return True
    return False


def _canvas_height(shapes: List[ShapeNode]) -> float:
    for shape in shapes:
        if shape.kind == "rect" and shape.box.width >= 1000 and shape.box.height >= 600:
            return shape.box.y2
    return 0.0


def _normalize_component_content_bounds(semantics, replacements: Dict[int, str]) -> None:
    canvas_h = _canvas_height(semantics.shapes)
    footer_y = canvas_h - FOOTER_ZONE_MARGIN if canvas_h > 0 else 0.0
    for shape in semantics.shapes:
        if shape.kind != "rect" or not _is_component_parent(shape):
            continue
        needed_y2 = shape.box.y2
        for child in semantics.shapes:
            if child is shape or child.box.area >= shape.box.area * 0.92:
                continue
            if _is_component_parent(child) or _is_page_or_decorative(child):
                continue
            child_parent = _nearest_spill_shape_component_parent(child, semantics.shapes)
            if child_parent is not shape:
                continue
            if _box_belongs_to_component(child.box, shape.box):
                needed_y2 = max(needed_y2, child.box.y2 + COMPONENT_CONTENT_PADDING)
        for text in semantics.texts:
            if footer_y > 0 and text.y >= footer_y:
                continue
            text_parent = _nearest_spill_text_component_parent(text, semantics.shapes)
            if text_parent is not shape:
                continue
            text_box = _text_box(text)
            if _box_belongs_to_component(text_box, shape.box):
                needed_y2 = max(needed_y2, text_box.y2 + COMPONENT_CONTENT_PADDING)

        if needed_y2 <= shape.box.y2 + 0.5:
            continue
        parent = _nearest_component_parent(shape, semantics.shapes)
        max_y2 = parent.box.y2 - SLOT_PARENT_INSET if parent else needed_y2
        target_y2 = min(needed_y2, max_y2)
        if target_y2 > shape.box.y2 + 0.5:
            replacements[shape.start] = _shape_tag_with_box(
                shape,
                Box(shape.box.x1, shape.box.y1, shape.box.x2, target_y2),
            )


def _normalize_direct_component_text_fit(semantics, replacements: Dict[int, str]) -> None:
    slots = {slot.shape.shape_id: slot for slot in semantics.slots}
    for text in semantics.texts:
        if text.start in replacements:
            continue
        parent = _nearest_text_component_parent(text, semantics.shapes)
        if not parent:
            continue
        # Text inside an explicit slot is handled by _normalize_center_slot.
        slot_shape = _smallest_shape_containing_text(text, semantics.shapes)
        if slot_shape and slot_shape.shape_id in slots and slot_shape.shape_id != parent.shape_id:
            continue
        text_box = _text_box(text)
        if (
            text_box.x1 >= parent.box.x1 + COMPONENT_CONTENT_PADDING
            and text_box.x2 <= parent.box.x2 - COMPONENT_CONTENT_PADDING
        ):
            continue
        available_width = _available_width_for_text(text, parent.box)
        if available_width <= 1:
            continue
        text_width = estimate_text_width(text.text, text.font_size, text.font_weight)
        if text_width <= available_width:
            continue
        font_size = max(MIN_SLOT_FONT_SIZE, text.font_size * available_width / text_width)
        replacements[text.start] = _text_tag_with_font_size(text, font_size)


def _normalize_direct_component_emphasis_alignment(semantics, replacements: Dict[int, str]) -> None:
    slots = {slot.shape.shape_id: slot for slot in semantics.slots}
    for text in semantics.texts:
        if text.start in replacements:
            continue
        parent = _nearest_text_component_parent(text, semantics.shapes)
        if not parent:
            continue
        slot_shape = _smallest_shape_containing_text(text, semantics.shapes)
        if slot_shape and slot_shape.shape_id in slots and slot_shape.shape_id != parent.shape_id:
            continue
        if not _is_direct_component_emphasis(text, parent, semantics.shapes):
            continue
        text_box = _text_box(text)
        font_size = _font_size_for_component_text(text, parent.box)
        replacements[text.start] = _centered_text_tag(text, parent.box.cx, text_box.cy, font_size)


def _normalize_semantic_sibling_spacing(semantics, replacements: Dict[int, str]) -> None:
    """Move sibling semantic boxes down when a repair creates overlap.

    The normalizer may grow a component to contain its child labels.  That is
    safer than letting text escape, but it can consume the gutter before the
    next semantic box.  Resolve this at the same component -> slot -> text
    layer by comparing siblings that share the nearest containing semantic
    parent; no page names, colors, or text literals are involved.
    """
    shapes = [
        shape
        for shape in semantics.shapes
        if shape.kind == "rect"
        and _is_semantic_layout_box(shape)
        and not _is_page_or_decorative(shape)
    ]
    if len(shapes) < 2:
        return

    parents: dict[str, ShapeNode | None] = {}
    groups: dict[str, list[dict]] = {}
    for shape in shapes:
        parent = _nearest_containing_semantic_parent(shape, shapes)
        parents[shape.shape_id] = parent
        parent_id = parent.shape_id if parent else "__root__"
        groups.setdefault(parent_id, []).append({"shape": shape, "box": shape.box})

    for parent_id, siblings in groups.items():
        if len(siblings) < 2:
            continue
        parent = None
        if parent_id != "__root__":
            parent = next((shape for shape in shapes if shape.shape_id == parent_id), None)
        siblings.sort(key=lambda item: (item["box"].y1, item["box"].x1, item["box"].area))
        for index, item in enumerate(siblings):
            shift = 0.0
            for previous in siblings[:index]:
                if _horizontal_overlap_ratio(previous["box"], item["box"]) < SEMANTIC_SIBLING_MIN_AXIS_OVERLAP:
                    continue
                gap = _semantic_sibling_required_gap(previous["shape"], item["shape"])
                needed = previous["box"].y2 + gap - item["box"].y1
                if needed > shift:
                    shift = needed
            if shift <= 0:
                continue
            shape = item["shape"]
            if parent and shape.box.y2 + shift > parent.box.y2 - SLOT_PARENT_INSET:
                continue
            _shift_semantic_shape_tree(shape, shift, semantics, replacements)
            item["box"] = Box(
                item["box"].x1,
                item["box"].y1 + shift,
                item["box"].x2,
                item["box"].y2 + shift,
            )


def _collision_overlap_area(a: Box, b: Box) -> float:
    """Return the intersection area of two boxes (0.0 if no overlap)."""
    inter_w = min(a.x2, b.x2) - max(a.x1, b.x1)
    inter_h = min(a.y2, b.y2) - max(a.y1, b.y1)
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    return inter_w * inter_h


def _resolve_component_collisions(semantics, replacements: Dict[int, str]) -> None:
    """Push overlapping sibling rect components apart.

    ``_normalize_component_content_bounds`` may grow a component to contain
    its children.  ``_normalize_semantic_sibling_spacing`` handles minor gap
    deficiency but not true rect-on-rect overlaps.  This pass detects actual
    area intersections between semantic layout siblings and resolves them by
    shifting the lower component (and its entire child tree) downward.
    """
    shapes = [
        shape
        for shape in semantics.shapes
        if shape.kind == "rect"
        and _is_semantic_layout_box(shape)
        and not _is_page_or_decorative(shape)
    ]
    if len(shapes) < 2:
        return

    # Group siblings by nearest containing semantic parent, same strategy as
    # _normalize_semantic_sibling_spacing.
    groups: dict[str, list[dict]] = {}
    for shape in shapes:
        parent = _nearest_containing_semantic_parent(shape, shapes)
        parent_id = parent.shape_id if parent else "__root__"
        groups.setdefault(parent_id, []).append({"shape": shape, "box": shape.box})

    for parent_id, siblings in groups.items():
        if len(siblings) < 2:
            continue
        parent = None
        if parent_id != "__root__":
            parent = next((s for s in shapes if s.shape_id == parent_id), None)

        # Sort by top edge so we always shift the lower sibling.
        siblings.sort(key=lambda item: (item["box"].y1, item["box"].x1, item["box"].area))

        for _iteration in range(COLLISION_RESOLVE_MAX_ITERATIONS):
            any_shifted = False
            for index in range(1, len(siblings)):
                item = siblings[index]
                shift = 0.0
                for previous in siblings[:index]:
                    overlap = _collision_overlap_area(previous["box"], item["box"])
                    if overlap < COLLISION_MIN_OVERLAP_AREA:
                        continue
                    # Only resolve if they share meaningful horizontal space
                    if _horizontal_overlap_ratio(previous["box"], item["box"]) < SEMANTIC_SIBLING_MIN_AXIS_OVERLAP:
                        continue
                    # The amount the lower box must move down: clear the upper
                    # box's bottom edge plus the minimum gap.
                    needed = previous["box"].y2 + SEMANTIC_SIBLING_MIN_GAP - item["box"].y1
                    if needed > shift:
                        shift = needed

                if shift <= 0:
                    continue

                shape = item["shape"]

                # Respect parent bounds: if the shift would push the
                # component below the parent's bottom, try compressing the
                # overlapping upper sibling's height first.
                if parent and item["box"].y2 + shift > parent.box.y2 - SLOT_PARENT_INSET:
                    overflow = (item["box"].y2 + shift) - (parent.box.y2 - SLOT_PARENT_INSET)
                    # Try to recover space by shrinking the upper sibling
                    # that caused the collision.
                    for previous in siblings[:index]:
                        if _collision_overlap_area(previous["box"], item["box"]) < COLLISION_MIN_OVERLAP_AREA:
                            continue
                        shrink = min(overflow, previous["box"].height * 0.3)
                        if shrink > 0.5:
                            prev_shape = previous["shape"]
                            new_prev_box = Box(
                                previous["box"].x1,
                                previous["box"].y1,
                                previous["box"].x2,
                                previous["box"].y2 - shrink,
                            )
                            replacements[prev_shape.start] = _shape_tag_with_box(prev_shape, new_prev_box)
                            previous["box"] = new_prev_box
                            shift = max(0.0, shift - shrink)
                            overflow -= shrink
                        if overflow <= 0:
                            break
                    if shift <= 0:
                        continue
                    # After shrinking, if shift still overflows, skip to
                    # avoid pushing content outside the parent.
                    if parent and item["box"].y2 + shift > parent.box.y2 - SLOT_PARENT_INSET:
                        continue

                _shift_semantic_shape_tree(shape, shift, semantics, replacements)
                item["box"] = Box(
                    item["box"].x1,
                    item["box"].y1 + shift,
                    item["box"].x2,
                    item["box"].y2 + shift,
                )
                any_shifted = True

            if not any_shifted:
                break


def _shift_semantic_shape_tree(
    shape: ShapeNode,
    dy: float,
    semantics,
    replacements: Dict[int, str],
) -> None:
    replacements[shape.start] = _shape_tag_with_xy(shape, shape.box.x1, shape.box.y1 + dy)
    for child in semantics.shapes:
        if child is shape or child.kind != "rect":
            continue
        if shape.box.contains_box(child.box, pad=1):
            replacements[child.start] = _shape_tag_with_xy(child, child.box.x1, child.box.y1 + dy)
    for text in semantics.texts:
        if shape.box.contains_point(text.x, text.y, pad=1):
            replacements[text.start] = _text_tag_with_y(text, text.y + dy)


def _box_belongs_to_component(box: Box, component_box: Box) -> bool:
    if box.width > component_box.width * 1.18:
        return False
    x_overlap = min(box.x2, component_box.x2) - max(box.x1, component_box.x1)
    if x_overlap <= 0 or x_overlap < min(box.width, component_box.width) * 0.45:
        return False
    return (
        box.y1 >= component_box.y1 - COMPONENT_SPILL_TOLERANCE
        and box.y1 <= component_box.y2 + COMPONENT_SPILL_TOLERANCE
    )


def _nearest_text_component_parent(text: TextNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    text_box = _text_box(text)
    candidates = [
        shape
        for shape in shapes
        if _is_component_parent(shape)
        and shape.box.area > text_box.area * 1.18
        and shape.box.contains_point(text.x, text.y, pad=1)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda shape: shape.box.area)


def _text_is_sheltered(text: TextNode, exclude: ShapeNode, shapes: List[ShapeNode]) -> bool:
    """True when *text* sits inside a non-component, non-decorative shape.

    This prevents a remote component from adopting a text that visually
    belongs to a closer sibling shape (e.g. a risk-strip, a banner, or any
    other filled rect that is not itself a component-parent).  Shapes that
    ARE component-parents are excluded — the normal smallest-area candidate
    selection already handles nested components correctly.
    """
    for shape in shapes:
        if shape is exclude:
            continue
        if _is_page_or_decorative(shape):
            continue
        if _is_component_parent(shape):
            continue
        if shape.box.area < 200:
            continue
        if shape.box.contains_point(text.x, text.y, pad=1):
            return True
    return False


def _nearest_spill_text_component_parent(text: TextNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    text_box = _text_box(text)
    candidates = [
        shape
        for shape in shapes
        if _is_component_parent(shape)
        and shape.box.area > text_box.area * 1.18
        and _box_belongs_to_component(text_box, shape.box)
    ]
    if not candidates:
        return None
    best = min(
        candidates,
        key=lambda shape: (
            shape.box.area,
            0 if shape.box.contains_point(text.x, text.y, pad=1) else 1,
        ),
    )
    if not best.box.contains_point(text.x, text.y, pad=1) and _text_is_sheltered(text, best, shapes):
        return None
    return best


def _nearest_spill_shape_component_parent(child: ShapeNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    candidates = [
        shape
        for shape in shapes
        if shape is not child
        and _is_component_parent(shape)
        and shape.box.area > child.box.area * 1.18
        and _box_belongs_to_component(child.box, shape.box)
    ]
    if not candidates:
        return None
    cx = child.box.cx
    cy = child.box.cy
    return min(
        candidates,
        key=lambda shape: (
            shape.box.area,
            0 if shape.box.contains_point(cx, cy, pad=1) else 1,
        ),
    )


def _nearest_containing_semantic_parent(shape: ShapeNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    candidates = [
        candidate
        for candidate in shapes
        if candidate is not shape
        and candidate.box.area > shape.box.area * 1.18
        and candidate.box.contains_box(shape.box, pad=1)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item.box.area)


def _smallest_shape_containing_text(text: TextNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    candidates = [shape for shape in shapes if shape.box.contains_point(text.x, text.y, pad=1)]
    if not candidates:
        return None
    return min(candidates, key=lambda shape: shape.box.area)


def _available_width_for_text(text: TextNode, box: Box) -> float:
    if text.anchor == "middle":
        return max((min(text.x - box.x1, box.x2 - text.x) - COMPONENT_CONTENT_PADDING) * 2, 1.0)
    if text.anchor == "end":
        return max(text.x - box.x1 - COMPONENT_CONTENT_PADDING, 1.0)
    return max(box.x2 - text.x - COMPONENT_CONTENT_PADDING, 1.0)


def _font_size_for_component_text(text: TextNode, box: Box) -> float:
    available_width = max(box.width - COMPONENT_CONTENT_PADDING * 2, 1.0)
    text_width = estimate_text_width(text.text, text.font_size, text.font_weight)
    if text_width <= available_width:
        return text.font_size
    return max(MIN_SLOT_FONT_SIZE, text.font_size * available_width / text_width)


def _text_box(text: TextNode) -> Box:
    width = estimate_text_width(text.text, text.font_size, text.font_weight)
    height = max(text.font_size * 1.25, text.font_size)
    if text.anchor == "middle":
        x1 = text.x - width / 2
    elif text.anchor == "end":
        x1 = text.x - width
    else:
        x1 = text.x
    if text.dominant in {"middle", "central"}:
        y1 = text.y - height / 2
    else:
        y1 = text.y - text.font_size
    return Box(x1, y1, x1 + width, y1 + height)


def _virtual_slot_bounds(box: Box, texts: List[TextNode]) -> List[tuple[float, float]]:
    centers = [visual_text_center_x(text) for text in texts]
    bounds = [box.x1]
    for left, right in zip(centers, centers[1:]):
        midpoint = (left + right) / 2
        bounds.append(min(max(midpoint, box.x1), box.x2))
    bounds.append(box.x2)
    return [(bounds[index], bounds[index + 1]) for index in range(len(texts))]


def _horizontal_overlap_ratio(a: Box, b: Box) -> float:
    inter_w = min(a.x2, b.x2) - max(a.x1, b.x1)
    if inter_w <= 0:
        return 0.0
    return inter_w / max(min(a.width, b.width), 1.0)


def _is_direct_component_emphasis(text: TextNode, parent: ShapeNode, shapes: List[ShapeNode]) -> bool:
    if parent.slot in {"layer", "body-slot"}:
        return False
    if (
        parent.text_align in {"left", "left-aligned", "content", "callout-content"}
        and not _is_headered_display_component(parent, shapes)
    ):
        return False
    if text.text_align in {"left", "left-aligned", "content", "callout-content"}:
        return False
    if text.role in {"content", "callout-content", "body"}:
        return False
    if text.font_size < COMPONENT_EMPHASIS_MIN_FONT_SIZE:
        return False
    if parent.box.height <= 0:
        return False
    relative_y = (text.y - parent.box.y1) / parent.box.height
    if relative_y > COMPONENT_EMPHASIS_TOP_BAND_RATIO:
        return False
    text_box = _text_box(text)
    if text_box.width < parent.box.width * COMPONENT_EMPHASIS_MIN_WIDTH_RATIO and text.font_size < 28:
        return False
    if _has_same_band_companion_shape(text_box, parent, shapes):
        return False
    return True


def _is_headered_display_component(parent: ShapeNode, shapes: List[ShapeNode]) -> bool:
    for shape in shapes:
        if shape is parent:
            continue
        if not parent.box.contains_box(shape.box, pad=1):
            continue
        if shape.role not in {"label", "header", "table-header"} and shape.slot not in {"label", "header"}:
            continue
        if shape.box.height > 72:
            continue
        if shape.box.width < parent.box.width * 0.65:
            continue
        if abs(shape.box.y1 - parent.box.y1) > 4:
            continue
        return True
    return False


def _has_same_band_companion_shape(text_box: Box, parent: ShapeNode, shapes: List[ShapeNode]) -> bool:
    for shape in shapes:
        if shape is parent:
            continue
        if not parent.box.contains_box(shape.box, pad=1):
            continue
        if _is_page_or_decorative(shape):
            continue
        if shape.role in {"label", "header", "table-header", "header-cell", "table-cell", "label-slot"}:
            continue
        if shape.slot in {"label", "header", "cell", "badge", "tag"}:
            continue
        inter_h = min(text_box.y2, shape.box.y2) - max(text_box.y1, shape.box.y1)
        if inter_h <= 0:
            continue
        if inter_h / max(min(text_box.height, shape.box.height), 1.0) < 0.25:
            continue
        return True
    return False


def _semantic_sibling_required_gap(a: ShapeNode, b: ShapeNode) -> float:
    if _is_compact_label(a) and _is_compact_label(b):
        return 6.0
    return SEMANTIC_SIBLING_MIN_GAP


def _is_compact_label(shape: ShapeNode) -> bool:
    return (
        shape.box.height <= 40
        and (shape.role in {"label", "badge", "tag", "label-slot"} or shape.slot in {"label", "badge", "tag"})
    )


def _is_neutral_badge_shape(shape: ShapeNode) -> bool:
    fill = (shape.fill or "").strip().upper()
    return shape.box.width <= 180 and shape.box.height <= 44 and fill in {"#FFF", "#FFFFFF", "WHITE"}


def _stack_item_center_y(item: dict) -> float:
    y1, y2 = _stack_item_bounds(item)
    return (y1 + y2) / 2


def _stack_item_bounds(item: dict) -> tuple[float, float]:
    if item["kind"] == "badge":
        box = item["shape"].box
        return box.y1, box.y2
    text = item["text"]
    return text.y - text.font_size * 0.7, text.y + text.font_size * 0.35


def _centered_text_tag(text: TextNode, x: float, y: float, font_size: float | None = None) -> str:
    attrs = _set_attr(text.attrs, "x", f"{x:g}")
    attrs = _set_attr(attrs, "y", f"{y:g}")
    attrs = _set_attr(attrs, "text-anchor", "middle")
    attrs = _set_attr(attrs, "dominant-baseline", "middle")
    if font_size is not None and abs(font_size - text.font_size) > 0.05:
        attrs = _set_attr(attrs, "font-size", _format_number(font_size))
    return f"<text{attrs}>{text.inner}</text>"


def _text_tag_with_font_size(text: TextNode, font_size: float) -> str:
    if abs(font_size - text.font_size) <= 0.05:
        return f"<text{text.attrs}>{text.inner}</text>"
    attrs = _set_attr(text.attrs, "font-size", _format_number(font_size))
    return f"<text{attrs}>{text.inner}</text>"


def _text_tag_with_y(text: TextNode, y: float) -> str:
    attrs = _set_attr(text.attrs, "y", _format_number(y))
    return f"<text{attrs}>{text.inner}</text>"


def _shape_tag_with_xy(shape: ShapeNode, x: float, y: float) -> str:
    if shape.kind != "rect":
        return _original_tag_placeholder(shape)
    attrs = shape.attrs.rstrip()
    if attrs.endswith("/"):
        attrs = attrs[:-1].rstrip()
    attrs = _set_attr(attrs, "x", f"{x:g}")
    attrs = _set_attr(attrs, "y", f"{y:g}")
    return f"<rect{attrs}/>"


def _shape_tag_with_box(shape: ShapeNode, box: Box) -> str:
    if shape.kind != "rect":
        return _original_tag_placeholder(shape)
    attrs = shape.attrs.rstrip()
    if attrs.endswith("/"):
        attrs = attrs[:-1].rstrip()
    attrs = _set_attr(attrs, "x", _format_number(box.x1))
    attrs = _set_attr(attrs, "y", _format_number(box.y1))
    attrs = _set_attr(attrs, "width", _format_number(box.width))
    attrs = _set_attr(attrs, "height", _format_number(box.height))
    return f"<rect{attrs}/>"


def _original_tag_placeholder(shape: ShapeNode) -> str:
    # Current stack badge movement is defined for rect badges.  For other shape
    # kinds, leave the shape intact; text centering still proceeds.
    return ""


def _slot_rect_tag(x: float, y: float, width: float, height: float, fill: str, slot_index: int) -> str:
    return (
        f'\n<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        f'fill="{fill}" fill-opacity="0" data-role="label-slot" data-slot-index="{slot_index}"/>'
    )


def _apply_replacements_and_insertions(
    content: str,
    replacements: Dict[int, str],
    insertions: Dict[int, List[str]],
) -> str:
    spans = []
    for start, replacement in replacements.items():
        if not replacement:
            continue
        end = _replacement_end_at(content, start)
        if end is not None:
            spans.append((start, end, replacement))

    parts = []
    cursor = 0
    edit_positions = sorted({start for start, _, _ in spans} | set(insertions))
    span_by_start = {start: (end, replacement) for start, end, replacement in spans}
    for pos in edit_positions:
        if pos in span_by_start:
            end, replacement = span_by_start[pos]
            if pos < cursor:
                continue
            parts.append(content[cursor:pos])
            parts.append(replacement)
            cursor = end
        if pos in insertions:
            parts.append(content[cursor:pos])
            parts.extend(insertions[pos])
            cursor = pos
    parts.append(content[cursor:])
    return "".join(parts)


def _replacement_end_at(content: str, start: int) -> int | None:
    if content.startswith("<text", start):
        end = content.find("</text>", start)
        return None if end == -1 else end + len("</text>")
    if content.startswith("<rect", start):
        end = content.find(">", start)
        return None if end == -1 else end + 1
    return None


def _set_attr(attrs: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\b{name}\s*=\s*(["\']).*?\1')
    replacement = f'{name}="{value}"'
    if pattern.search(attrs):
        return pattern.sub(replacement, attrs, count=1)
    return attrs.rstrip() + f" {replacement}"


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# viewBox overflow clipping
# ---------------------------------------------------------------------------
# SVG viewBox clips shapes in browsers, but PPTX has no such clipping.
# Shapes that extend past the viewBox become visible in PowerPoint as shapes
# protruding beyond the slide boundary.  This pass removes or trims them.

_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"([^"]+)"')
_CIRCLE_RE = re.compile(r'<circle\b([^>]*)/?>')
_ELLIPSE_RE = re.compile(r'<ellipse\b([^>]*)/?>')
_RECT_TAG_RE = re.compile(r'<rect\b([^>]*)/?>')

VIEWBOX_OVERFLOW_TOLERANCE = 2.0


def _parse_viewbox(content: str) -> tuple[float, float, float, float] | None:
    m = _VIEWBOX_RE.search(content)
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _attr_float(attrs: str, name: str) -> float | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _shape_is_decorative_bg(attrs: str) -> bool:
    """True if the shape is a low-opacity background decoration."""
    opacity = _attr_float(attrs, "fill-opacity")
    if opacity is not None and opacity < 0.1:
        return True
    role_m = re.search(r'data-role\s*=\s*"([^"]*)"', attrs)
    if role_m and role_m.group(1) in ("bg-decoration", "background"):
        return True
    return False


def clip_viewbox_overflow(content: str) -> tuple[str, int]:
    """Remove shapes that extend significantly past the SVG viewBox.

    Only removes shapes that are both (a) clearly outside the canvas AND
    (b) decorative / low-opacity.  Content shapes that overflow are left
    for the quality checker to flag — auto-removing content would be lossy.
    """
    vb = _parse_viewbox(content)
    if not vb:
        return content, 0

    vb_x, vb_y, vb_w, vb_h = vb
    removed = 0

    def _exceeds_viewbox(cx: float, cy: float, rx: float, ry: float) -> bool:
        return (
            cx - rx < vb_x - VIEWBOX_OVERFLOW_TOLERANCE
            or cy - ry < vb_y - VIEWBOX_OVERFLOW_TOLERANCE
            or cx + rx > vb_x + vb_w + VIEWBOX_OVERFLOW_TOLERANCE
            or cy + ry > vb_y + vb_h + VIEWBOX_OVERFLOW_TOLERANCE
        )

    # Remove circles that overflow and are decorative
    def _filter_circle(m: re.Match) -> str:
        nonlocal removed
        attrs = m.group(1)
        if not _shape_is_decorative_bg(attrs):
            return m.group(0)
        cx = _attr_float(attrs, "cx") or 0
        cy = _attr_float(attrs, "cy") or 0
        r = _attr_float(attrs, "r") or 0
        if _exceeds_viewbox(cx, cy, r, r):
            removed += 1
            return ""
        return m.group(0)

    content = _CIRCLE_RE.sub(_filter_circle, content)

    # Remove ellipses that overflow and are decorative
    def _filter_ellipse(m: re.Match) -> str:
        nonlocal removed
        attrs = m.group(1)
        if not _shape_is_decorative_bg(attrs):
            return m.group(0)
        cx = _attr_float(attrs, "cx") or 0
        cy = _attr_float(attrs, "cy") or 0
        rx = _attr_float(attrs, "rx") or 0
        ry = _attr_float(attrs, "ry") or 0
        if _exceeds_viewbox(cx, cy, rx, ry):
            removed += 1
            return ""
        return m.group(0)

    content = _ELLIPSE_RE.sub(_filter_ellipse, content)

    # Remove rects that overflow and are decorative
    def _filter_rect(m: re.Match) -> str:
        nonlocal removed
        attrs = m.group(1)
        if not _shape_is_decorative_bg(attrs):
            return m.group(0)
        x = _attr_float(attrs, "x") or 0
        y = _attr_float(attrs, "y") or 0
        w = _attr_float(attrs, "width") or 0
        h = _attr_float(attrs, "height") or 0
        if (x + w > vb_x + vb_w + VIEWBOX_OVERFLOW_TOLERANCE
                or y + h > vb_y + vb_h + VIEWBOX_OVERFLOW_TOLERANCE
                or x < vb_x - VIEWBOX_OVERFLOW_TOLERANCE
                or y < vb_y - VIEWBOX_OVERFLOW_TOLERANCE):
            removed += 1
            return ""
        return m.group(0)

    content = _RECT_TAG_RE.sub(_filter_rect, content)

    if removed:
        content = re.sub(r'\n\s*\n', '\n', content)

    return content, removed
