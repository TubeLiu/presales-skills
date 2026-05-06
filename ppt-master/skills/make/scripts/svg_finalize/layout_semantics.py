"""Infer layout components, slots, and text nodes from generated SVG.

This module is intentionally small and deterministic.  It does not try to
"understand" every SVG primitive; it builds the minimum semantic layer needed by
the PPT pipeline:

component -> slot -> text

Rules that depend on colors or dimensions live here as fallback inference only.
When SVG carries explicit ``data-role`` / ``data-slot`` attributes, those win.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List


HEX_VALUE_RE = re.compile(r"#[0-9A-Fa-f]{3,8}")
CENTER_TOLERANCE = 3.0
STACK_TOLERANCE = 8.0
COMPONENT_EMPHASIS_MIN_FONT_SIZE = 24.0
COMPONENT_EMPHASIS_TOP_BAND_RATIO = 0.42
COMPONENT_EMPHASIS_MIN_WIDTH_RATIO = 0.32


@dataclass
class Box:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(self.x2 - self.x1, 0.0)

    @property
    def height(self) -> float:
        return max(self.y2 - self.y1, 0.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    def contains_point(self, x: float, y: float, pad: float = 0.0) -> bool:
        return self.x1 - pad <= x <= self.x2 + pad and self.y1 - pad <= y <= self.y2 + pad

    def contains_box(self, other: "Box", pad: float = 0.0) -> bool:
        return (
            self.x1 - pad <= other.x1
            and self.y1 - pad <= other.y1
            and self.x2 + pad >= other.x2
            and self.y2 + pad >= other.y2
        )


@dataclass
class ShapeNode:
    index: int
    start: int
    end: int
    kind: str
    attrs: str
    box: Box
    fill: str = ""
    fill_opacity: float = 1.0
    role: str = ""
    slot: str = ""
    text_align: str = ""

    @property
    def shape_id(self) -> str:
        return f"{self.kind}:{self.index}"

    @property
    def is_transparent_slot(self) -> bool:
        return self.fill_opacity == 0 or self.role in {"label-slot", "header-cell", "table-cell"}


@dataclass
class TextNode:
    start: int
    end: int
    attrs: str
    inner: str
    text: str
    x: float
    y: float
    font_size: float
    font_weight: str
    anchor: str
    dominant: str
    role: str = ""
    slot: str = ""
    text_align: str = ""


@dataclass
class SlotNode:
    role: str
    policy: str
    box: Box
    shape: ShapeNode
    texts: List[TextNode] = field(default_factory=list)
    component_role: str = ""

    @property
    def slot_id(self) -> str:
        return self.shape.shape_id


@dataclass
class ComponentNode:
    role: str
    box: Box
    shape: ShapeNode
    slots: List[SlotNode] = field(default_factory=list)


@dataclass
class LayoutSemantics:
    shapes: List[ShapeNode]
    texts: List[TextNode]
    slots: List[SlotNode]
    components: List[ComponentNode]


def build_layout_semantics(content: str) -> LayoutSemantics:
    shapes = extract_shapes(content)
    texts = extract_texts(content)
    slots_by_shape: dict[str, SlotNode] = {}

    for text in texts:
        candidates = [shape for shape in shapes if shape.box.contains_point(text.x, text.y, pad=1)]
        shape = choose_slot_shape(candidates)
        if not shape:
            continue
        role, policy, component_role = infer_slot_policy(shape, candidates, text)
        if policy == "ignore":
            continue
        slot = slots_by_shape.get(shape.shape_id)
        if not slot:
            slot = SlotNode(
                role=role,
                policy=policy,
                box=shape.box,
                shape=shape,
                component_role=component_role,
            )
            slots_by_shape[shape.shape_id] = slot
        slot.texts.append(text)

    components = [
        ComponentNode(role=slot.component_role or slot.role, box=slot.box, shape=slot.shape, slots=[slot])
        for slot in slots_by_shape.values()
    ]
    return LayoutSemantics(shapes=shapes, texts=texts, slots=list(slots_by_shape.values()), components=components)


def extract_shapes(content: str) -> List[ShapeNode]:
    shapes: List[ShapeNode] = []
    for match in re.finditer(r"<(rect|path|circle|ellipse)\b([^>]*)/?>", content, re.IGNORECASE):
        kind = match.group(1).lower()
        attrs = match.group(2) or ""
        box = _shape_box(kind, attrs)
        if not box or box.area < 1:
            continue
        shapes.append(
            ShapeNode(
                index=len(shapes),
                start=match.start(),
                end=match.end(),
                kind=kind,
                attrs=attrs,
                box=box,
                fill=_attr_value(attrs, "fill") or "",
                fill_opacity=_attr_float(attrs, "fill-opacity", 1.0) or 0.0,
                role=(_attr_value(attrs, "data-role") or "").strip().lower(),
                slot=(_attr_value(attrs, "data-slot") or "").strip().lower(),
                text_align=(_attr_value(attrs, "data-text-align") or "").strip().lower(),
            )
        )
    return shapes


def extract_texts(content: str) -> List[TextNode]:
    texts: List[TextNode] = []
    for match in re.finditer(r"<text\b([^>]*)>(.*?)</text>", content, re.IGNORECASE | re.DOTALL):
        attrs = match.group(1) or ""
        if "rotate" in (_attr_value(attrs, "transform") or ""):
            continue
        x = _attr_float(attrs, "x")
        y = _attr_float(attrs, "y")
        if x is None or y is None:
            continue
        lines = text_lines(match.group(2) or "")
        if len(lines) != 1:
            continue
        texts.append(
            TextNode(
                start=match.start(),
                end=match.end(),
                attrs=attrs,
                inner=match.group(2) or "",
                text=lines[0],
                x=x,
                y=y,
                font_size=_attr_float(attrs, "font-size", 16.0) or 16.0,
                font_weight=(_attr_value(attrs, "font-weight") or "").strip().lower(),
                anchor=(_attr_value(attrs, "text-anchor") or "start").strip().lower(),
                dominant=(
                    _attr_value(attrs, "dominant-baseline")
                    or _attr_value(attrs, "alignment-baseline")
                    or ""
                ).strip().lower(),
                role=(_attr_value(attrs, "data-role") or "").strip().lower(),
                slot=(_attr_value(attrs, "data-slot") or "").strip().lower(),
                text_align=(_attr_value(attrs, "data-text-align") or "").strip().lower(),
            )
        )
    return texts


def choose_slot_shape(candidates: Iterable[ShapeNode]) -> ShapeNode | None:
    candidates = [
        shape
        for shape in candidates
        if not _is_page_background(shape)
        and not _is_decorative_background_shape(shape)
    ]
    if not candidates:
        return None

    explicit = [
        shape
        for shape in candidates
        if shape.role in {"label", "header", "table-header", "header-cell", "table-cell", "label-slot"}
        or shape.slot
        or shape.is_transparent_slot
    ]
    if explicit:
        return min(explicit, key=lambda shape: shape.box.area)

    colored = [shape for shape in candidates if is_colored_fill(shape.fill)]
    if colored:
        smallest = min(colored, key=lambda shape: shape.box.area)
        same_fill = [
            shape
            for shape in colored
            if _same_fill(shape.fill, smallest.fill)
            and shape.box.height <= max(80.0, smallest.box.height * 2.5)
            and shape.box.area <= max(smallest.box.area * 3.5, 50000.0)
        ]
        if same_fill and smallest.box.area < 0.72 * max(shape.box.area for shape in same_fill):
            largest = max(same_fill, key=lambda shape: shape.box.area)
            if (
                abs(smallest.box.y1 - largest.box.y1) <= 1
                and abs(smallest.box.height - largest.box.height) <= 1
                and smallest.box.width <= largest.box.width * 0.85
            ):
                return smallest
            return max(same_fill, key=lambda shape: shape.box.area)
        return smallest

    structural = [
        shape
        for shape in candidates
        if shape.kind in {"rect", "path"}
        and not _is_white_or_neutral_container(shape)
        and shape.box.height <= 70
        and shape.box.width <= 950
    ]
    if structural:
        return min(structural, key=lambda shape: shape.box.area)

    circles = [shape for shape in candidates if shape.kind in {"circle", "ellipse"}]
    if circles:
        return min(circles, key=lambda shape: shape.box.area)

    return None


def infer_slot_policy(
    shape: ShapeNode,
    candidates: Iterable[ShapeNode],
    text: TextNode,
) -> tuple[str, str, str]:
    if declares_left_aligned_exception(shape, text):
        return "body", "left", "content-card"

    role_values = {shape.role, text.role, shape.slot, text.slot}
    if role_values & {"content-card", "callout-content", "body", "body-slot"}:
        return "body", "left", "content-card"
    if role_values & {"table-cell", "header-cell", "label-slot"}:
        return "table-cell", "center", "table-header"
    if role_values & {"label", "header", "table-header", "badge", "step"}:
        return "label", "center", "label"

    if shape.is_transparent_slot:
        return "slot", "center", "table-header"

    if shape.kind in {"circle", "ellipse"}:
        return "label", "center", "label"

    if is_colored_fill(shape.fill):
        if shape.box.height <= 80:
            return "label", "center", "label"
        if shape.box.height <= 180 and shape.box.width <= 420:
            return "compact-card", "center-stack", "content-card"
        return "content-card", "left", "content-card"

    if _looks_like_structure_row(shape):
        return "structure-row", "left", "two-column-row"

    return "unknown", "ignore", "unknown"


def centered_text_ok(text: TextNode, box: Box, tolerance: float = CENTER_TOLERANCE) -> bool:
    return (
        text.anchor == "middle"
        and text.dominant in {"middle", "central"}
        and abs(text.x - box.cx) <= tolerance
        and abs(text.y - box.cy) <= tolerance
    )


def alignment_issues(content: str) -> List[dict]:
    semantics = build_layout_semantics(content)
    issues: List[dict] = []
    for slot in semantics.slots:
        if slot.policy not in {"center", "center-stack"}:
            continue
        if slot.policy == "center-stack" and len(slot.texts) > 1:
            for text in slot.texts:
                horizontal_ok = text.anchor == "middle" and abs(text.x - slot.box.cx) <= STACK_TOLERANCE
                vertical_ok = text.dominant in {"middle", "central"}
                if not horizontal_ok or not vertical_ok:
                    issues.append(_issue(slot, text))
            continue
        if len(slot.texts) > 1 and not slot.shape.is_transparent_slot:
            for text in slot.texts:
                issues.append(_issue(slot, text))
            continue
        for text in slot.texts:
            if not centered_text_ok(text, slot.box):
                issues.append(_issue(slot, text))
    return issues


def component_emphasis_alignment_issues(content: str) -> List[dict]:
    shapes = extract_shapes(content)
    texts = extract_texts(content)
    issues: List[dict] = []
    for text in texts:
        parent = _nearest_text_component_parent(text, shapes)
        if not parent:
            continue
        slot_shape = _smallest_shape_containing_text(text, shapes)
        if slot_shape and slot_shape is not parent and _is_slot_shape(slot_shape):
            continue
        if not _is_direct_component_emphasis(text, parent, shapes):
            continue
        if text.anchor != "middle" or abs(text.x - parent.box.cx) > CENTER_TOLERANCE:
            issues.append(
                {
                    "text": text.text,
                    "component": parent.role or parent.slot or "component",
                    "slot": "component-emphasis",
                    "shape": parent.kind,
                    "anchor_x": text.x,
                    "anchor_y": text.y,
                    "center_x": parent.box.cx,
                    "center_y": parent.box.cy,
                }
            )
    return issues


def _issue(slot: SlotNode, text: TextNode) -> dict:
    return {
        "text": text.text,
        "component": slot.component_role or slot.role,
        "slot": slot.role,
        "shape": slot.shape.kind,
        "anchor_x": text.x,
        "anchor_y": text.y,
        "center_x": slot.box.cx,
        "center_y": slot.box.cy,
    }


def declares_left_aligned_exception(shape: ShapeNode, text: TextNode) -> bool:
    values = {
        shape.text_align,
        shape.role,
        text.text_align,
        text.role,
    }
    return bool(values & {"left", "left-aligned", "content", "callout-content"})


def text_lines(inner: str) -> List[str]:
    stripped = re.sub(r"<[^>]+>", "", inner)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return [stripped] if stripped else []


def estimate_text_width(text: str, font_size: float, font_weight: str | float | int | None = None) -> float:
    width = 0.0
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            width += font_size
        elif char.isspace():
            width += font_size * 0.32
        elif char in "ilI.,:;!|":
            width += font_size * 0.35
        elif char in "mwMW@#%":
            width += font_size * 0.85
        else:
            width += font_size * 0.58
    if _is_bold_weight(font_weight):
        width *= 1.08
    return width


def _is_bold_weight(font_weight: str | float | int | None) -> bool:
    if font_weight is None:
        return False
    if isinstance(font_weight, (int, float)):
        return font_weight >= 600
    value = str(font_weight).strip().lower()
    if value in {"bold", "bolder", "heavy", "black"}:
        return True
    if value.isdigit():
        return int(value) >= 600
    return False


def visual_text_center_x(text: TextNode) -> float:
    width = estimate_text_width(text.text, text.font_size, text.font_weight)
    if text.anchor == "middle":
        return text.x
    if text.anchor == "end":
        return text.x - width / 2
    return text.x + width / 2


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


def _smallest_shape_containing_text(text: TextNode, shapes: List[ShapeNode]) -> ShapeNode | None:
    candidates = [shape for shape in shapes if shape.box.contains_point(text.x, text.y, pad=1)]
    if not candidates:
        return None
    return min(candidates, key=lambda shape: shape.box.area)


def _is_direct_component_emphasis(text: TextNode, parent: ShapeNode, shapes: List[ShapeNode]) -> bool:
    if parent.slot in {"layer", "body-slot"}:
        return False
    if declares_left_aligned_exception(parent, text) and not _is_headered_display_component(parent, shapes):
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


def _is_slot_shape(shape: ShapeNode) -> bool:
    return (
        shape.role in {"label", "header", "table-header", "header-cell", "table-cell", "badge", "tag", "label-slot"}
        or shape.slot in {"label", "header", "cell", "badge", "tag"}
        or shape.is_transparent_slot
    )


def _has_same_band_companion_shape(text_box: Box, parent: ShapeNode, shapes: List[ShapeNode]) -> bool:
    for shape in shapes:
        if shape is parent:
            continue
        if not parent.box.contains_box(shape.box, pad=1):
            continue
        if _is_page_background(shape) or _is_decorative_background_shape(shape) or _is_slot_shape(shape):
            continue
        inter_h = min(text_box.y2, shape.box.y2) - max(text_box.y1, shape.box.y1)
        if inter_h <= 0:
            continue
        if inter_h / max(min(text_box.height, shape.box.height), 1.0) < 0.25:
            continue
        return True
    return False


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


def is_colored_fill(fill: str) -> bool:
    if not HEX_VALUE_RE.fullmatch(fill or ""):
        return False
    raw = fill.lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) < 6:
        return False
    r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    chroma = max(r, g, b) - min(r, g, b)
    saturation = chroma / max(max(r, g, b), 1)
    if r >= 248 and g >= 248 and b >= 248:
        return False
    if chroma < 12 and saturation < 0.06:
        return False
    return True


def _shape_box(kind: str, attrs: str) -> Box | None:
    if kind == "rect":
        x = _attr_float(attrs, "x", 0.0) or 0.0
        y = _attr_float(attrs, "y", 0.0) or 0.0
        width = _attr_float(attrs, "width")
        height = _attr_float(attrs, "height")
        if width is None or height is None or width <= 0 or height <= 0:
            return None
        return Box(x, y, x + width, y + height)
    if kind == "circle":
        cx = _attr_float(attrs, "cx")
        cy = _attr_float(attrs, "cy")
        radius = _attr_float(attrs, "r")
        if cx is None or cy is None or radius is None or radius <= 0:
            return None
        return Box(cx - radius, cy - radius, cx + radius, cy + radius)
    if kind == "ellipse":
        cx = _attr_float(attrs, "cx")
        cy = _attr_float(attrs, "cy")
        rx = _attr_float(attrs, "rx")
        ry = _attr_float(attrs, "ry")
        if cx is None or cy is None or rx is None or ry is None or rx <= 0 or ry <= 0:
            return None
        return Box(cx - rx, cy - ry, cx + rx, cy + ry)
    if kind == "path":
        d = _attr_value(attrs, "d")
        if not d:
            return None
        return _path_endpoint_box(d)
    return None


def _path_endpoint_box(d: str) -> Box | None:
    tokens = re.findall(r"[MmLlHhVvAaZz]|-?\d+(?:\.\d+)?", d)
    index = 0
    cmd = None
    x = y = 0.0
    points: list[tuple[float, float]] = []

    def num() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[index]):
            cmd = tokens[index]
            index += 1
            if cmd in {"Z", "z"}:
                continue
        try:
            if cmd in {"M", "m", "L", "l"}:
                if index + 1 >= len(tokens):
                    break
                nx, ny = num(), num()
                if cmd.islower():
                    x += nx
                    y += ny
                else:
                    x, y = nx, ny
                points.append((x, y))
                if cmd == "M":
                    cmd = "L"
                elif cmd == "m":
                    cmd = "l"
            elif cmd in {"H", "h"}:
                nx = num()
                x = x + nx if cmd.islower() else nx
                points.append((x, y))
            elif cmd in {"V", "v"}:
                ny = num()
                y = y + ny if cmd.islower() else ny
                points.append((x, y))
            elif cmd in {"A", "a"}:
                if index + 6 >= len(tokens):
                    break
                _rx, _ry, _rot, _large, _sweep, nx, ny = num(), num(), num(), num(), num(), num(), num()
                if cmd.islower():
                    x += nx
                    y += ny
                else:
                    x, y = nx, ny
                points.append((x, y))
            else:
                index += 1
        except (ValueError, IndexError):
            break

    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return Box(min(xs), min(ys), max(xs), max(ys))


def _looks_like_structure_row(shape: ShapeNode) -> bool:
    return (
        shape.kind in {"rect", "path"}
        and shape.box.height <= 70
        and shape.box.width <= 950
        and not _is_white_or_neutral_container(shape)
    )


def _is_white_or_neutral_container(shape: ShapeNode) -> bool:
    fill = (shape.fill or "").strip().upper()
    return fill in {"", "NONE", "#FFF", "#FFFFFF", "WHITE"}


def _is_page_background(shape: ShapeNode) -> bool:
    if shape.role in {"page-background", "background"}:
        return True
    fill = (shape.fill or "").strip().upper()
    return fill in {"#FFFFFF", "WHITE"} and shape.box.width >= 1000 and shape.box.height >= 600


def _is_decorative_background_shape(shape: ShapeNode) -> bool:
    if shape.role in {"geometric-accent", "decorative-accent", "decoration", "accent-background"}:
        return True
    if shape.role or shape.slot or (shape.fill_opacity == 0 and shape.box.height <= 100):
        return False
    if shape.fill_opacity >= 0.15:
        return False
    return shape.box.width >= 180 or shape.box.height >= 180


def _same_fill(left: str, right: str) -> bool:
    return (left or "").strip().lower() == (right or "").strip().lower()


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
