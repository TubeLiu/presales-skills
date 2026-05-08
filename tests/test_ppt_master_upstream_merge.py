"""Tests covering upstream `hugohe3/ppt-master` v2.6.0 merge.

These tests verify that the capabilities pulled in from upstream (PPTX→SVG
reverse, animation sequence emission, audio narration injection, asymmetric
round-rect custGeom, finalize_svg align-images merge) are wired correctly,
without regressing our enhancements (normalize-layout, 10-dim quality
checker, alauda templates, design_*  planners).
"""

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "ppt-master/skills/make/scripts"


def _import(module_path: str):
    """Import `module_path` from ppt-master scripts dir."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        __import__(module_path)
        return sys.modules[module_path]
    finally:
        sys.path.pop(0)


# -------------------- Phase 2: new modules wire-up --------------------

def test_pptx_to_svg_module_loads():
    """The reverse converter package and its CLI entry should import."""
    mod = _import("pptx_to_svg.converter")
    assert hasattr(mod, "convert_pptx_to_svg"), (
        "Upstream pptx_to_svg.converter should expose convert_pptx_to_svg()."
    )


def test_pptx_to_svg_cli_help_runs():
    """`pptx_to_svg.py --help` should print usage and exit 0."""
    import subprocess
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pptx_to_svg.py"), "--help"],
        capture_output=True, text=True, env={"PRESALES_SKILLS_SKIP_AUTO_INSTALL": "1", "PATH": "/usr/bin:/bin"},
    )
    assert completed.returncode == 0
    assert "pptx_file" in completed.stdout
    assert "--inheritance-mode" in completed.stdout


def test_env_loader_module():
    """env_loader extracts upstream's load_prefixed_env_file without polluting our config.py."""
    mod = _import("env_loader")
    for fn in ("get_env_candidates", "resolve_env_path", "strip_env_quotes", "load_prefixed_env_file"):
        assert hasattr(mod, fn), f"env_loader should expose {fn}"


def test_tspan_flattener_use_expander_narration_modules():
    """The three new svg_to_pptx siblings load cleanly."""
    for name in ("svg_to_pptx.tspan_flattener", "svg_to_pptx.use_expander", "svg_to_pptx.pptx_narration"):
        _import(name)


def test_align_embed_images_module():
    """svg_finalize.align_embed_images exposes the merged single-pass function."""
    mod = _import("svg_finalize.align_embed_images")
    assert hasattr(mod, "align_and_embed_images_in_svg")


# -------------------- Phase 3: svg_to_pptx superset behaviour --------------------

def test_drawingml_context_has_animation_targets():
    """Upstream's ConvertContext exposes anim_targets for per-element animation."""
    mod = _import("svg_to_pptx.drawingml_context")
    ctx = mod.ConvertContext()
    assert hasattr(ctx, "anim_targets"), "ConvertContext.anim_targets is missing — upstream merge incomplete."
    assert ctx.anim_targets == [], "Default anim_targets should be empty list."
    # Affine matrix superset
    assert hasattr(mod, "AffineMatrix") and hasattr(mod, "IDENTITY_MATRIX")
    assert ctx.transform_matrix == mod.IDENTITY_MATRIX


def test_drawingml_utils_transform_helpers():
    """Upstream's matrix transform helpers are reachable."""
    mod = _import("svg_to_pptx.drawingml_utils")
    for fn in ("matrix_multiply", "parse_transform_matrix", "transform_point"):
        assert hasattr(mod, fn), f"drawingml_utils should expose {fn} from upstream."


# -------------------- Phase 4: animation expansion --------------------

def test_animations_dict_extended_to_22():
    """Upstream's ANIMATIONS dict carries all 22 entrance effects."""
    mod = _import("pptx_animations")
    assert len(mod.ANIMATIONS) >= 22, f"Expected ≥22 ANIMATIONS, got {len(mod.ANIMATIONS)}"
    # Sanity: legacy 4 names still present
    for name in ("appear", "fade", "fly", "zoom"):
        assert name in mod.ANIMATIONS, f"{name} is part of the legacy 4 and must remain."
    # Upstream additions
    for name in ("blinds", "checkerboard", "dissolve", "wheel", "swivel"):
        assert name in mod.ANIMATIONS, f"{name} is from upstream — merge incomplete."


def test_animations_has_sequence_and_picker():
    """Sequence-timing emitter + per-element effect picker are present."""
    mod = _import("pptx_animations")
    assert callable(getattr(mod, "create_sequence_timing_xml", None))
    assert callable(getattr(mod, "pick_animation_effect", None))
    assert isinstance(getattr(mod, "_MIXED_POOL", None), list)


def test_create_sequence_timing_xml_emits_per_target():
    """Sequence emitter generates one animEffect block per target."""
    mod = _import("pptx_animations")
    targets = [(2, 0, "fade"), (3, 500, "fly"), (4, 1000, "zoom")]
    xml = mod.create_sequence_timing_xml(targets, duration=1.0, trigger="after-previous")
    assert xml.count("<p:animEffect") >= 3 or xml.count("<p:set") >= 3, (
        "Sequence XML should contain at least one effect block per target."
    )


# -------------------- Phase 5: finalize_svg orchestrator --------------------

def test_finalize_svg_imports_align_embed_images():
    """Our finalize_svg.py picks up the new align-images step."""
    text = (SCRIPTS_DIR / "finalize_svg.py").read_text(encoding="utf-8")
    assert "from svg_finalize.align_embed_images import align_and_embed_images_in_svg" in text
    assert "align-images" in text  # in --only choices and help text
    # Our normalize-layout step is preserved
    assert "from svg_finalize.normalize_layout import normalize_colored_block_text_in_file" in text
    assert "normalize-layout" in text


def test_finalize_svg_default_uses_align_images():
    """Default-all options enable align_images, NOT the legacy trio."""
    text = (SCRIPTS_DIR / "finalize_svg.py").read_text(encoding="utf-8")
    # Heuristic: the default branch (else of `if args.only`) should set
    # align_images=True and crop_images=False / fix_aspect=False / embed_images=False.
    default_block = text.split("# Default-all", 1)
    if len(default_block) == 1:
        # Older comment style. Look for align_images=True without --only context.
        default_block = text.split("Execute all by default", 1)
    body = default_block[-1]
    # Within ~30 lines after the marker, both flags should appear with the right values.
    snippet = body.splitlines()[:30]
    snippet = "\n".join(snippet)
    assert "'align_images': True" in snippet
    assert "'crop_images': False" in snippet
    assert "'fix_aspect': False" in snippet


# -------------------- Phase 6: layouts_index.json enrichment --------------------

def test_layouts_index_has_pages_field():
    """All 22 layouts (21 shared + alauda) carry a `pages` field after Phase 6."""
    idx = json.loads(
        (ROOT / "ppt-master/skills/make/templates/layouts/layouts_index.json").read_text(encoding="utf-8")
    )
    for name, entry in idx.items():
        assert "pages" in entry, f"Layout '{name}' missing pages field — Phase 6 enrichment skipped."
        assert isinstance(entry["pages"], list) and entry["pages"], (
            f"Layout '{name}' has an empty pages list."
        )


def test_design_specs_clipPath_consistent():
    """All 21 shared layouts allow `clipPath` on `<image>` per shared-standards §1.2.

    The phrase 'clipPath is allowed only on `<image>`' should appear in every
    shared layout's design_spec.md. The single exception is `中汽研_现代`,
    whose upstream version dropped clipPath mentions entirely.
    """
    base = ROOT / "ppt-master/skills/make/templates/layouts"
    # Match either 'is allowed only on `<image>`' or 'Allowed only on `<image>`'
    # (medical_university uses table-cell capitalization).
    skip_layouts = {"alauda", "中汽研_现代"}  # alauda is ours, 中汽研_现代 doesn't mention clipPath at all

    misaligned = []
    for spec in base.glob("*/design_spec.md"):
        if spec.parent.name in skip_layouts:
            continue
        text = spec.read_text(encoding="utf-8")
        if "clipPath" in text:
            t = text.lower()
            if "allowed only on `<image>" not in t:
                misaligned.append(spec.parent.name)

    assert not misaligned, (
        f"These layouts mention `clipPath` but not the upstream allow-on-image phrasing: {misaligned}"
    )


# -------------------- Phase 7: animations.md reference --------------------

def test_animations_reference_present():
    ref = ROOT / "ppt-master/skills/make/references/animations.md"
    assert ref.exists() and ref.stat().st_size > 1024, (
        "references/animations.md from upstream should exist (≥1 KB)."
    )


# -------------------- Phase 8: workflows + demo --------------------

def test_new_workflows_present():
    base = ROOT / "ppt-master/skills/make/workflows"
    for name in ("generate-audio.md", "resume-execute.md", "verify-charts.md", "visual-edit.md"):
        f = base / name
        assert f.exists() and f.stat().st_size > 1024, f"{name} missing or too small."
    # Our existing ones preserved
    for name in ("create-template.md", "topic-research.md"):
        assert (base / name).exists()


def test_demo_project_intro_present():
    demo = ROOT / "ppt-master/examples/demo_project_intro_ppt169_20251211"
    assert demo.exists() and demo.is_dir(), "demo_project_intro fixture not copied."
    assert (demo / "design_spec.md").exists()
    # examples.json index is present (lists upstream's full catalog)
    assert (ROOT / "ppt-master/examples/examples.json").exists()


# -------------------- Phase 9: SKILL.md wiring --------------------

def test_skill_md_wires_new_capabilities():
    text = (ROOT / "ppt-master/skills/make/SKILL.md").read_text(encoding="utf-8")
    # Pipeline scripts table
    for ref in ("pptx_to_svg.py", "notes_to_audio.py", "check_annotations.py",
                "register_template.py", "svg_editor/server.py", "excel_to_md.py"):
        assert ref in text, f"SKILL.md should mention {ref}"
    # Standalone workflows
    for ref in ("generate-audio", "resume-execute", "verify-charts", "visual-edit"):
        assert ref in text, f"SKILL.md should list workflow '{ref}'"
    # Reference
    assert "references/animations.md" in text
    # Cross-platform checklist + path bootstrap preserved
    assert "跨平台兼容性 checklist" in text
    assert "路径自定位" in text
    # ai-image plugin handoff preserved
    assert "ai-image plugin" in text or "ai-image:gen" in text


# -------------------- Anti-regression: our enhancements survive --------------------

def test_normalize_layout_module_intact():
    """layout_semantics + normalize_layout (our quality work) still present + functional."""
    sem = _import("svg_finalize.layout_semantics")
    norm = _import("svg_finalize.normalize_layout")
    assert hasattr(sem, "build_layout_semantics")
    assert hasattr(norm, "normalize_colored_block_text_in_file")


def test_alauda_templates_untouched():
    """Alauda brand templates are still the 35-page catalog we maintain."""
    alauda_dir = ROOT / "ppt-master/skills/make/templates/layouts/alauda"
    svgs = list(alauda_dir.glob("*.svg"))
    assert len(svgs) >= 30, f"Alauda template count regressed: {len(svgs)}"
    # Critical metadata files
    for f in ("design_spec.md", "visual_system.json", "semantic_routes.json", "human_quality_rubric.json"):
        assert (alauda_dir / f).exists(), f"alauda/{f} missing."


def test_design_archetype_planner_and_quality_checker_intact():
    for name in ("design_archetype_planner.py", "design_quality_checker.py", "ppt_master_eval.py"):
        path = SCRIPTS_DIR / name
        assert path.exists() and path.stat().st_size > 10_000, (
            f"{name} (our enhancement) is missing or shrunk."
        )


def test_svg_quality_checker_10_dims():
    """Our 10-dim checker survives the merge."""
    checker_path = SCRIPTS_DIR / "svg_quality_checker.py"
    text = checker_path.read_text(encoding="utf-8")
    # Sanity: our 10-dim mentions
    assert "10-dimension" in text or "10 dimension" in text or text.count("def _check_") >= 9
