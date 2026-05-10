#!/usr/bin/env python3
"""PPT Master - Template chrome signature extractor.

Pure-function module shared by `svg_quality_checker.py` (Dimension 11
template_chrome_fidelity) and any future tooling that needs to reason about
"what counts as chrome" in an SVG (footer rule / left accent bar /
decorative circles / logo / header bar).

Chrome = the persistent visual frame of a branded template. It is what makes
a deck "look like Alauda" rather than "look like Alauda's color palette".
A page is faithful to its template variant when the generated SVG preserves
chrome at the same coordinates, with the same fills, and (where present) with
the same `data-role` markers.

Public API:
    extract_chrome_signatures(svg_path: Path) -> dict[str, list[dict]]
        Returns categorized chrome elements: accent_bars, footer_rules,
        decor_circles, logos_and_chrome_images, data_role_chrome.

    compare_signatures(expected, actual, *, coord_tolerance=4,
                       footer_tolerance=2) -> list[dict]
        Returns a list of mismatch records (missing / displaced /
        wrong_color). Empty list = perfect inheritance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
NS_RE = re.compile(r"^\{[^}]+\}")

CHROME_DATA_ROLE_PREFIXES = ("chrome", "footer", "accent", "decor", "header")


def _strip_ns(tag: str) -> str:
    return NS_RE.sub("", tag)


def _parse_viewbox(svg_root: ET.Element) -> tuple[float, float, float, float]:
    vb = svg_root.get("viewBox", "0 0 1280 720")
    parts = vb.split()
    if len(parts) != 4:
        return (0.0, 0.0, 1280.0, 720.0)
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return (0.0, 0.0, 1280.0, 720.0)


def _safe_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value.strip().rstrip("px"))
    except (ValueError, AttributeError):
        return default


def _normalize_color(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in ("none", "transparent"):
        return None
    return v


def _data_role(elem: ET.Element) -> str | None:
    return elem.get("data-role") or elem.get("{http://www.w3.org/2000/svg}data-role")


def _data_slot(elem: ET.Element) -> str | None:
    return elem.get("data-slot") or elem.get("{http://www.w3.org/2000/svg}data-slot")


def _iter_all(svg_root: ET.Element) -> Iterable[ET.Element]:
    """Iterate all descendants (and the root)."""
    yield svg_root
    for elem in svg_root.iter():
        if elem is svg_root:
            continue
        yield elem


def extract_chrome_signatures(svg_path_or_text: Path | str) -> dict[str, list[dict]]:
    """Categorize chrome elements in an SVG.

    Args:
        svg_path_or_text: Either a Path to an SVG file or a raw SVG string.

    Returns:
        dict with keys:
            accent_bars             — left-edge or right-edge thin rects
            footer_rules            — bottom horizontal lines
            decor_circles           — translucent or off-canvas circles/ellipses
            logos_and_chrome_images — top-band <image> elements
            data_role_chrome        — any element with data-role=chrome|footer|accent|decor|header
    """
    if isinstance(svg_path_or_text, Path):
        text = svg_path_or_text.read_text(encoding="utf-8")
    else:
        text = svg_path_or_text

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {
            "accent_bars": [],
            "footer_rules": [],
            "decor_circles": [],
            "logos_and_chrome_images": [],
            "data_role_chrome": [],
        }

    vb_x, vb_y, vb_w, vb_h = _parse_viewbox(root)

    accent_bars: list[dict] = []
    footer_rules: list[dict] = []
    decor_circles: list[dict] = []
    logos_and_chrome_images: list[dict] = []
    data_role_chrome: list[dict] = []

    for elem in _iter_all(root):
        tag = _strip_ns(elem.tag)
        role = _data_role(elem)
        slot = _data_slot(elem)

        # Accent bars: thin <rect> on the left edge (x ∈ [0,2]) and short on at
        # least one axis. Allow either orientation (vertical bar / thin top rule).
        if tag == "rect":
            x = _safe_float(elem.get("x"), 0)
            y = _safe_float(elem.get("y"))
            w = _safe_float(elem.get("width"))
            h = _safe_float(elem.get("height"))
            fill = _normalize_color(elem.get("fill"))
            on_left_edge = x <= 2.0
            thin = (w <= 30 and w > 0) or (h <= 30 and h > 0)
            if on_left_edge and thin and fill:
                accent_bars.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "fill": fill, "data_role": role,
                })

        # Footer rules: <line> with y1 == y2 in the bottom 10% of the canvas.
        if tag == "line":
            y1 = _safe_float(elem.get("y1"))
            y2 = _safe_float(elem.get("y2"))
            x1 = _safe_float(elem.get("x1"))
            x2 = _safe_float(elem.get("x2"))
            stroke = _normalize_color(elem.get("stroke"))
            in_footer_band = y1 == y2 and y1 > vb_y + vb_h * 0.9
            spans_canvas = abs(x2 - x1) > vb_w * 0.5
            if in_footer_band and spans_canvas and stroke:
                footer_rules.append({
                    "y": y1, "x_extent": [x1, x2],
                    "stroke": stroke, "data_role": role,
                })

        # Decor circles: <circle>/<ellipse> with low opacity OR center off-canvas.
        if tag in ("circle", "ellipse"):
            cx = _safe_float(elem.get("cx"))
            cy = _safe_float(elem.get("cy"))
            r = _safe_float(elem.get("r")) or _safe_float(elem.get("rx"))
            fill = _normalize_color(elem.get("fill"))
            opacity = _safe_float(
                elem.get("fill-opacity") or elem.get("opacity"), 1.0
            )
            off_canvas = (cx > vb_x + vb_w * 0.95) or (cy > vb_y + vb_h * 0.95)
            translucent = opacity < 0.06
            if (off_canvas or translucent) and fill:
                decor_circles.append({
                    "cx": cx, "cy": cy, "r": r,
                    "fill": fill, "opacity": opacity,
                    "data_role": role,
                })

        # Logos / chrome images: <image> in the top 15% band.
        if tag == "image":
            y = _safe_float(elem.get("y"))
            x = _safe_float(elem.get("x"))
            w = _safe_float(elem.get("width"))
            h = _safe_float(elem.get("height"))
            href = elem.get("href") or elem.get("{http://www.w3.org/1999/xlink}href")
            if y < vb_y + vb_h * 0.15:
                logos_and_chrome_images.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "href": href, "data_role": role,
                })

        # Explicit data-role chrome — catch-all for elements the template author
        # marked as semantic chrome (regardless of geometry).
        if role and any(role.startswith(p) for p in CHROME_DATA_ROLE_PREFIXES):
            data_role_chrome.append({
                "tag": tag,
                "data_role": role,
                "data_slot": slot,
                "x": _safe_float(elem.get("x") or elem.get("cx") or elem.get("x1")),
                "y": _safe_float(elem.get("y") or elem.get("cy") or elem.get("y1")),
                "w": _safe_float(elem.get("width")),
                "h": _safe_float(elem.get("height")),
            })

    return {
        "accent_bars": accent_bars,
        "footer_rules": footer_rules,
        "decor_circles": decor_circles,
        "logos_and_chrome_images": logos_and_chrome_images,
        "data_role_chrome": data_role_chrome,
    }


def _match_within(
    expected: dict, candidates: list[dict], *,
    coord_keys: tuple[str, ...], tolerance: float,
) -> dict | None:
    """Return first candidate whose coord keys are all within tolerance of expected."""
    for cand in candidates:
        if all(
            abs(cand.get(k, 0) - expected.get(k, 0)) <= tolerance
            for k in coord_keys
        ):
            return cand
    return None


def compare_signatures(
    expected: dict[str, list[dict]],
    actual: dict[str, list[dict]],
    *,
    coord_tolerance: float = 4.0,
    footer_tolerance: float = 2.0,
) -> list[dict]:
    """Compare expected (template) vs actual (generated) chrome signatures.

    Returns a list of mismatch records, each with shape:
        {category, severity, kind, expected, actual_or_none, message}

    Severity:
        error   — chrome class missing entirely, count off by >50%, color mismatch
        warning — coordinate within tolerance but slightly off, or non-blocker drift
    """
    mismatches: list[dict] = []

    # ---- accent_bars: count + position + fill -----------------------------
    exp_bars = expected.get("accent_bars", [])
    act_bars = actual.get("accent_bars", [])
    for eb in exp_bars:
        match = _match_within(
            eb, act_bars, coord_keys=("x", "y"), tolerance=coord_tolerance,
        )
        if not match:
            mismatches.append({
                "category": "accent_bars",
                "severity": "error",
                "kind": "missing",
                "expected": eb,
                "message": (
                    f"accent_bar at x={eb['x']}, y={eb['y']} (fill={eb['fill']}) "
                    "is missing or displaced > tolerance from generated SVG"
                ),
            })
            continue
        # check fill verbatim
        if match["fill"] != eb["fill"]:
            mismatches.append({
                "category": "accent_bars",
                "severity": "error",
                "kind": "wrong_color",
                "expected": eb,
                "actual": match,
                "message": (
                    f"accent_bar at x={eb['x']}, y={eb['y']}: expected fill "
                    f"{eb['fill']!r} but got {match['fill']!r}"
                ),
            })

    # ---- footer_rules: tighter tolerance ----------------------------------
    exp_rules = expected.get("footer_rules", [])
    act_rules = actual.get("footer_rules", [])
    for er in exp_rules:
        match = _match_within(
            er, act_rules, coord_keys=("y",), tolerance=footer_tolerance,
        )
        if not match:
            mismatches.append({
                "category": "footer_rules",
                "severity": "error",
                "kind": "missing",
                "expected": er,
                "message": (
                    f"footer_rule at y={er['y']} (stroke={er['stroke']}) "
                    "is missing or displaced > footer_tolerance"
                ),
            })
            continue
        if match["stroke"] != er["stroke"]:
            mismatches.append({
                "category": "footer_rules",
                "severity": "error",
                "kind": "wrong_color",
                "expected": er, "actual": match,
                "message": (
                    f"footer_rule at y={er['y']}: expected stroke {er['stroke']!r} "
                    f"but got {match['stroke']!r}"
                ),
            })

    # ---- decor_circles: count check; coordinate tolerance ------------------
    exp_circles = expected.get("decor_circles", [])
    act_circles = actual.get("decor_circles", [])
    if len(exp_circles) > 0 and len(act_circles) < len(exp_circles):
        mismatches.append({
            "category": "decor_circles",
            "severity": "error",
            "kind": "missing",
            "expected": {"count": len(exp_circles)},
            "actual": {"count": len(act_circles)},
            "message": (
                f"decor_circles count mismatch: template has {len(exp_circles)}, "
                f"generated has {len(act_circles)}"
            ),
        })
    else:
        for ec in exp_circles:
            match = _match_within(
                ec, act_circles, coord_keys=("cx", "cy"), tolerance=coord_tolerance,
            )
            if not match:
                mismatches.append({
                    "category": "decor_circles",
                    "severity": "warning",
                    "kind": "displaced",
                    "expected": ec,
                    "message": (
                        f"decor_circle at cx={ec['cx']}, cy={ec['cy']} not found "
                        "within coordinate tolerance"
                    ),
                })
            elif match["fill"] != ec["fill"]:
                mismatches.append({
                    "category": "decor_circles",
                    "severity": "error",
                    "kind": "wrong_color",
                    "expected": ec, "actual": match,
                    "message": (
                        f"decor_circle at cx={ec['cx']}: expected fill "
                        f"{ec['fill']!r} but got {match['fill']!r}"
                    ),
                })

    # ---- logos / chrome images --------------------------------------------
    exp_imgs = expected.get("logos_and_chrome_images", [])
    act_imgs = actual.get("logos_and_chrome_images", [])
    for ei in exp_imgs:
        match = _match_within(
            ei, act_imgs, coord_keys=("x", "y"), tolerance=coord_tolerance,
        )
        if not match:
            mismatches.append({
                "category": "logos_and_chrome_images",
                "severity": "error",
                "kind": "missing",
                "expected": ei,
                "message": (
                    f"logo/chrome image at x={ei['x']}, y={ei['y']} (href={ei['href']}) "
                    "is missing or displaced > tolerance"
                ),
            })

    # ---- data_role_chrome: presence-only check ----------------------------
    exp_roles = {r["data_role"] for r in expected.get("data_role_chrome", [])}
    act_roles = {r["data_role"] for r in actual.get("data_role_chrome", [])}
    for missing_role in exp_roles - act_roles:
        mismatches.append({
            "category": "data_role_chrome",
            "severity": "error",
            "kind": "missing",
            "expected": {"data_role": missing_role},
            "message": (
                f"semantic chrome marker data-role={missing_role!r} is not present "
                "in generated SVG (template uses it as a chrome anchor)"
            ),
        })

    return mismatches


__all__ = [
    "extract_chrome_signatures",
    "compare_signatures",
    "CHROME_DATA_ROLE_PREFIXES",
]
