"""Tests for v1.6.0 Pillar H: chrome_extractor + svg_quality_checker dimension 11.

Strict mode: ±4px coord tolerance / ±2px footer / verbatim color. Per CLAUDE.md
§6 anti-hardcoding rule, fixtures span multiple chrome categories (accent bar,
footer rule, decor circles, logo, data-role chrome) so the harness rules
generalize rather than patching one sample SVG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "ppt-master/skills/make/scripts"
ALAUDA_DIR = ROOT / "ppt-master/skills/make/templates/layouts/alauda"

sys.path.insert(0, str(SCRIPTS_DIR))
from chrome_extractor import (  # noqa: E402
    extract_chrome_signatures,
    compare_signatures,
)


# ---------- chrome_extractor pure-function tests ----------

def test_extract_chrome_from_real_alauda_panorama_template() -> None:
    sig = extract_chrome_signatures(ALAUDA_DIR / "03_content_panorama.svg")
    # Hard-known signatures from the template (verified at plan time)
    assert len(sig["accent_bars"]) == 1
    assert sig["accent_bars"][0]["x"] == 0.0
    assert sig["accent_bars"][0]["w"] == 22.0
    assert sig["accent_bars"][0]["fill"] == "#3baee3"
    assert len(sig["footer_rules"]) == 1
    assert sig["footer_rules"][0]["y"] == 682.0
    assert sig["footer_rules"][0]["data_role"] == "footer-rule"
    assert len(sig["decor_circles"]) == 3


def test_extract_chrome_from_minimal_svg_string() -> None:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
        <rect x="0" y="29" width="22" height="45" fill="#3BAEE3"/>
        <line x1="0" y1="682" x2="1280" y2="682" stroke="#E2E8F0" data-role="footer-rule"/>
        <circle cx="1350" cy="600" r="280" fill="#3BAEE3" fill-opacity="0.04"/>
    </svg>'''
    sig = extract_chrome_signatures(svg)
    assert len(sig["accent_bars"]) == 1
    assert len(sig["footer_rules"]) == 1
    assert len(sig["decor_circles"]) == 1
    assert sig["data_role_chrome"][0]["data_role"] == "footer-rule"


def test_extract_returns_empty_for_invalid_svg() -> None:
    sig = extract_chrome_signatures("<not-svg>broken</not-svg")
    assert sig == {
        "accent_bars": [], "footer_rules": [], "decor_circles": [],
        "logos_and_chrome_images": [], "data_role_chrome": [],
    }


def test_extract_ignores_non_chrome_rects_in_content_area() -> None:
    """A rect at x=200 (not on left edge) is content, not chrome."""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
        <rect x="200" y="100" width="50" height="50" fill="#FF0000"/>
    </svg>'''
    sig = extract_chrome_signatures(svg)
    assert sig["accent_bars"] == []


# ---------- compare_signatures tests ----------

def test_compare_perfect_match_returns_no_mismatches() -> None:
    expected = extract_chrome_signatures(ALAUDA_DIR / "03_content_panorama.svg")
    actual = extract_chrome_signatures(ALAUDA_DIR / "03_content_panorama.svg")
    assert compare_signatures(expected, actual) == []


def test_compare_missing_accent_bar_is_error() -> None:
    expected = extract_chrome_signatures(ALAUDA_DIR / "03_content_panorama.svg")
    actual = {
        "accent_bars": [],  # missing!
        "footer_rules": expected["footer_rules"],
        "decor_circles": expected["decor_circles"],
        "logos_and_chrome_images": expected["logos_and_chrome_images"],
        "data_role_chrome": expected["data_role_chrome"],
    }
    mismatches = compare_signatures(expected, actual)
    accent_errors = [m for m in mismatches if m["category"] == "accent_bars"]
    assert len(accent_errors) == 1
    assert accent_errors[0]["severity"] == "error"
    assert accent_errors[0]["kind"] == "missing"


def test_compare_displaced_accent_bar_within_tolerance_passes() -> None:
    expected = {"accent_bars": [{"x": 0, "y": 29, "w": 22, "h": 45, "fill": "#3baee3"}],
                "footer_rules": [], "decor_circles": [],
                "logos_and_chrome_images": [], "data_role_chrome": []}
    actual = {"accent_bars": [{"x": 2, "y": 31, "w": 22, "h": 45, "fill": "#3baee3"}],  # +2/+2 within ±4
              "footer_rules": [], "decor_circles": [],
              "logos_and_chrome_images": [], "data_role_chrome": []}
    assert compare_signatures(expected, actual, coord_tolerance=4.0) == []


def test_compare_displaced_accent_bar_beyond_tolerance_is_error() -> None:
    expected = {"accent_bars": [{"x": 0, "y": 29, "w": 22, "h": 45, "fill": "#3baee3"}],
                "footer_rules": [], "decor_circles": [],
                "logos_and_chrome_images": [], "data_role_chrome": []}
    actual = {"accent_bars": [{"x": 0, "y": 50, "w": 22, "h": 45, "fill": "#3baee3"}],  # y off by 21
              "footer_rules": [], "decor_circles": [],
              "logos_and_chrome_images": [], "data_role_chrome": []}
    mismatches = compare_signatures(expected, actual, coord_tolerance=4.0)
    assert any(m["kind"] == "missing" and m["category"] == "accent_bars" for m in mismatches)


def test_compare_wrong_color_is_error() -> None:
    expected = {"accent_bars": [{"x": 0, "y": 29, "w": 22, "h": 45, "fill": "#3baee3"}],
                "footer_rules": [], "decor_circles": [],
                "logos_and_chrome_images": [], "data_role_chrome": []}
    actual = {"accent_bars": [{"x": 0, "y": 29, "w": 22, "h": 45, "fill": "#ff0000"}],  # red!
              "footer_rules": [], "decor_circles": [],
              "logos_and_chrome_images": [], "data_role_chrome": []}
    mismatches = compare_signatures(expected, actual)
    assert any(m["kind"] == "wrong_color" for m in mismatches)


def test_compare_footer_tolerance_tighter_than_coord_tolerance() -> None:
    expected = {"accent_bars": [], "footer_rules": [{"y": 682, "x_extent": [0, 1280], "stroke": "#e2e8f0"}],
                "decor_circles": [], "logos_and_chrome_images": [], "data_role_chrome": []}
    # ±2 footer tolerance: y=684 OK, y=685 fail
    actual_ok = {"accent_bars": [], "footer_rules": [{"y": 684, "x_extent": [0, 1280], "stroke": "#e2e8f0"}],
                 "decor_circles": [], "logos_and_chrome_images": [], "data_role_chrome": []}
    assert compare_signatures(expected, actual_ok, footer_tolerance=2.0) == []
    actual_bad = {"accent_bars": [], "footer_rules": [{"y": 690, "x_extent": [0, 1280], "stroke": "#e2e8f0"}],
                  "decor_circles": [], "logos_and_chrome_images": [], "data_role_chrome": []}
    assert any(m["category"] == "footer_rules" for m in compare_signatures(expected, actual_bad, footer_tolerance=2.0))


def test_compare_decor_circle_count_mismatch_is_error() -> None:
    expected = {"accent_bars": [], "footer_rules": [],
                "decor_circles": [{"cx": 1350, "cy": 600, "r": 280, "fill": "#3baee3", "opacity": 0.04},
                                  {"cx": 1400, "cy": 250, "r": 220, "fill": "#3baee3", "opacity": 0.03},
                                  {"cx": 1150, "cy": 780, "r": 350, "fill": "#3baee3", "opacity": 0.02}],
                "logos_and_chrome_images": [], "data_role_chrome": []}
    actual = {"accent_bars": [], "footer_rules": [],
              "decor_circles": [{"cx": 1350, "cy": 600, "r": 280, "fill": "#3baee3", "opacity": 0.04}],
              "logos_and_chrome_images": [], "data_role_chrome": []}
    mismatches = compare_signatures(expected, actual)
    assert any(m["category"] == "decor_circles" and m["kind"] == "missing" for m in mismatches)


def test_compare_data_role_chrome_marker_must_be_present() -> None:
    expected = {"accent_bars": [], "footer_rules": [], "decor_circles": [],
                "logos_and_chrome_images": [],
                "data_role_chrome": [{"data_role": "footer-rule", "tag": "line", "x": 0, "y": 682, "w": 0, "h": 0}]}
    actual = {"accent_bars": [], "footer_rules": [], "decor_circles": [],
              "logos_and_chrome_images": [], "data_role_chrome": []}
    mismatches = compare_signatures(expected, actual)
    assert any(m["category"] == "data_role_chrome" and m["kind"] == "missing" for m in mismatches)


# ---------- svg_quality_checker dimension 11 integration ----------

def _seed_minimal_alauda_project(tmp_path: Path, generated_svg: str) -> Path:
    """Build a minimal project where dimension 11 will run.

    Layout:
        <project>/spec_lock.md
        <project>/templates/03_content_panorama.svg  (real Alauda variant copy)
        <project>/svg_output/slide_02_overview.svg   (the generated SVG to test)
    """
    project = tmp_path / "alauda_e2e"
    project.mkdir()
    (project / "templates").mkdir()
    (project / "svg_output").mkdir()

    # Copy a real Alauda variant
    import shutil
    shutil.copy(
        ALAUDA_DIR / "03_content_panorama.svg",
        project / "templates" / "03_content_panorama.svg",
    )

    spec_lock = """## template_lock
- template: alauda
- source_dir: templates
- routes_required: true
- variant_files_present: 1

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## colors
- bg: #FFFFFF
- primary: #3BAEE3

## typography
- font_family: Arial, sans-serif
- body: 18

## page_rhythm
- P02: dense

## semantic_routes
- P02: platform_panorama | 03_content_panorama.svg | domain_row | title<=18; notes_overflow=yes
"""
    (project / "spec_lock.md").write_text(spec_lock, encoding="utf-8")
    (project / "svg_output" / "slide_02_overview.svg").write_text(generated_svg, encoding="utf-8")
    return project


def _run_dim11(generated_svg: str, tmp_path: Path) -> tuple[list[str], list[str]]:
    """Run svg_quality_checker on a single generated SVG; return (errors, warnings)."""
    from svg_quality_checker import SVGQualityChecker
    project = _seed_minimal_alauda_project(tmp_path, generated_svg)
    checker = SVGQualityChecker()
    result = checker.check_file(str(project / "svg_output" / "slide_02_overview.svg"))
    chrome_errors = [e for e in result["errors"] if "template_chrome" in e]
    chrome_warnings = [w for w in result["warnings"] if "template_chrome" in w]
    return chrome_errors, chrome_warnings


def test_dim11_passes_when_generated_svg_inherits_full_chrome(tmp_path: Path) -> None:
    """Generated SVG that copies template chrome verbatim → dimension 11 passes."""
    template_text = (ALAUDA_DIR / "03_content_panorama.svg").read_text(encoding="utf-8")
    errors, warnings = _run_dim11(template_text, tmp_path)
    assert errors == [], f"unexpected chrome errors: {errors}"
    # Warnings empty too: perfect inheritance


def test_dim11_blocks_when_generated_svg_omits_accent_bar(tmp_path: Path) -> None:
    """Generated SVG missing left accent bar → release blocker error."""
    template_text = (ALAUDA_DIR / "03_content_panorama.svg").read_text(encoding="utf-8")
    # Strip the accent bar rect line
    degraded = template_text.replace(
        '<rect x="0" y="29" width="22" height="45" fill="#3BAEE3"/>',
        "",
    )
    errors, _ = _run_dim11(degraded, tmp_path)
    assert any("accent_bar" in e for e in errors), f"expected accent_bar error, got: {errors}"


def test_dim11_blocks_when_chrome_color_drifted(tmp_path: Path) -> None:
    """Generated SVG with red accent bar (instead of Alauda blue) → release blocker."""
    template_text = (ALAUDA_DIR / "03_content_panorama.svg").read_text(encoding="utf-8")
    drifted = template_text.replace('fill="#3BAEE3"', 'fill="#FF0000"', 1)  # only first occurrence
    errors, _ = _run_dim11(drifted, tmp_path)
    assert any("wrong_color" in e or "fill" in e.lower() for e in errors), f"got: {errors}"


def test_dim11_skipped_for_free_design(tmp_path: Path) -> None:
    """When template_lock.template == "" (free design), dimension 11 silently skips."""
    project = tmp_path / "free_design_proj"
    project.mkdir()
    (project / "svg_output").mkdir()
    (project / "spec_lock.md").write_text(
        '## template_lock\n- template: ""\n- source_dir: templates\n- routes_required: false\n- variant_files_present: 0\n\n'
        '## canvas\n- viewBox: 0 0 1280 720\n- format: PPT 16:9\n\n'
        '## colors\n- bg: #FFFFFF\n\n'
        '## typography\n- font_family: Arial\n- body: 18\n',
        encoding="utf-8",
    )
    # Bare-bones SVG with no chrome whatsoever — should still pass
    bare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><text x="100" y="100">hi</text></svg>'
    (project / "svg_output" / "slide_02_freeform.svg").write_text(bare, encoding="utf-8")

    from svg_quality_checker import SVGQualityChecker
    result = SVGQualityChecker().check_file(str(project / "svg_output" / "slide_02_freeform.svg"))
    assert not any("template_chrome" in e for e in result["errors"]), result["errors"]
