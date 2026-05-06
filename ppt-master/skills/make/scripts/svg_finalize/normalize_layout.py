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


def normalize_colored_block_text_in_file(svg_file: Path, verbose: bool = False) -> int:
    content = svg_file.read_text(encoding="utf-8")
    processed, count = normalize_colored_block_text(content)
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
            _normalize_center_slot(slot, replacements, insertions)
        elif slot.policy == "center-stack":
            _normalize_stack_slot(slot, semantics.shapes, replacements)

    if not replacements and not insertions:
        return content, 0

    return _apply_replacements_and_insertions(content, replacements, insertions), len(replacements)


def _normalize_center_slot(
    slot: SlotNode,
    replacements: Dict[int, str],
    insertions: Dict[int, List[str]],
) -> None:
    if not slot.texts:
        return

    if len(slot.texts) == 1:
        text = slot.texts[0]
        replacements[text.start] = _centered_text_tag(text, slot.box.cx, slot.box.cy)
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
                replacements[text.start] = _centered_text_tag(text, slot.box.cx, badge_y + badge.box.height / 2)
        else:
            text = item["text"]
            replacements[text.start] = _centered_text_tag(text, slot.box.cx, text.y + dy)


def _virtual_slot_bounds(box: Box, texts: List[TextNode]) -> List[tuple[float, float]]:
    centers = [visual_text_center_x(text) for text in texts]
    bounds = [box.x1]
    for left, right in zip(centers, centers[1:]):
        midpoint = (left + right) / 2
        bounds.append(min(max(midpoint, box.x1), box.x2))
    bounds.append(box.x2)
    return [(bounds[index], bounds[index + 1]) for index in range(len(texts))]


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


def _centered_text_tag(text: TextNode, x: float, y: float) -> str:
    attrs = _set_attr(text.attrs, "x", f"{x:g}")
    attrs = _set_attr(attrs, "y", f"{y:g}")
    attrs = _set_attr(attrs, "text-anchor", "middle")
    attrs = _set_attr(attrs, "dominant-baseline", "middle")
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
