"""Tests for v1.6.0 Pillar K: page_skeleton_seeder.py.

The seeder physically copies template variant SVGs into svg_output/ as
.skeleton.svg files so Step 6 Executor edits chrome in place rather than
re-creating from scratch. These tests cover the seeding logic + edge cases.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "ppt-master/skills/make/scripts"
ALAUDA_DIR = ROOT / "ppt-master/skills/make/templates/layouts/alauda"


def _run_seeder(project_path: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "page_skeleton_seeder.py"), str(project_path), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _seed_alauda_project(tmp_path: Path, *, with_routes: list[str] | None = None) -> Path:
    """Create a project with Alauda templates copied + minimal spec_lock.

    with_routes: list of "P02:platform_panorama:03_content_panorama.svg" tuples to include.
    """
    project = tmp_path / "alauda_seed_test"
    project.mkdir()
    (project / "templates").mkdir()
    (project / "svg_output").mkdir()
    (project / ".gates").mkdir()

    for name in [
        "01_cover.svg",
        "03_content.svg",
        "03_content_panorama.svg",
        "03_content_architecture.svg",
        "03_content_migration.svg",
    ]:
        src = ALAUDA_DIR / name
        if src.exists():
            shutil.copy(src, project / "templates" / name)

    spec_lock_lines = [
        "## template_lock",
        "- template: alauda",
        "- source_dir: templates",
        "- routes_required: true",
        "- variant_files_present: 5",
        "",
        "## canvas",
        "- viewBox: 0 0 1280 720",
        "- format: PPT 16:9",
        "",
        "## page_rhythm",
        "- P01: anchor",
        "- P02: dense",
        "- P03: dense",
        "- P04: dense",
        "",
    ]
    if with_routes:
        spec_lock_lines.append("## semantic_routes")
        for r in with_routes:
            spec_lock_lines.append(f"- {r}")

    (project / "spec_lock.md").write_text("\n".join(spec_lock_lines), encoding="utf-8")
    return project


# ---------- happy path ----------

def test_seeder_seeds_routed_pages_and_anchor_cover(tmp_path: Path) -> None:
    project = _seed_alauda_project(
        tmp_path,
        with_routes=[
            "P02: platform_panorama | 03_content_panorama.svg | grammar | budget",
            "P03: architecture_stack | 03_content_architecture.svg | grammar | budget",
            "P04: migration_bridge | 03_content_migration.svg | grammar | budget",
        ],
    )
    code, stdout, stderr = _run_seeder(project)
    assert code == 0, f"seeder failed: stdout={stdout} stderr={stderr}"

    # P01 anchor → 01_cover.svg seeded
    assert (project / "svg_output" / "slide_01_cover.skeleton.svg").exists()
    # P02-P04 routed → respective variants seeded
    assert (project / "svg_output" / "slide_02_platform_panorama.skeleton.svg").exists()
    assert (project / "svg_output" / "slide_03_architecture_stack.skeleton.svg").exists()
    assert (project / "svg_output" / "slide_04_migration_bridge.skeleton.svg").exists()


def test_seeder_writes_gate_log(tmp_path: Path) -> None:
    project = _seed_alauda_project(
        tmp_path,
        with_routes=["P02: platform_panorama | 03_content_panorama.svg | grammar | budget"],
    )
    code, _, _ = _run_seeder(project)
    assert code == 0
    log_path = project / ".gates" / "skeletons_seeded.json"
    assert log_path.exists()
    log = json.loads(log_path.read_text(encoding="utf-8"))
    assert log["template"] == "alauda"
    pages = {entry["page"] for entry in log["seeded_pages"]}
    assert "P01" in pages and "P02" in pages


def test_seeder_skeleton_preserves_chrome_replaces_content_text(tmp_path: Path) -> None:
    """Skeleton preserves chrome (accent bar / footer / decor circles) verbatim
    but content slots get placeholders."""
    project = _seed_alauda_project(
        tmp_path,
        with_routes=["P02: platform_panorama | 03_content_panorama.svg | grammar | budget"],
    )
    code, _, _ = _run_seeder(project)
    assert code == 0
    skeleton = (project / "svg_output" / "slide_02_platform_panorama.skeleton.svg").read_text(encoding="utf-8")
    # Chrome must be present: accent bar + footer rule + decor shapes (2 circles + 1 ellipse in panorama variant)
    assert 'x="0" y="29" width="22" height="45" fill="#3BAEE3"' in skeleton
    assert 'data-role="footer-rule"' in skeleton
    decor_shape_count = skeleton.count("<circle") + skeleton.count("<ellipse")
    assert decor_shape_count >= 3, f"expected >=3 decor shapes, got {decor_shape_count}"


# ---------- free design ----------

def test_seeder_skips_when_template_is_free_design(tmp_path: Path) -> None:
    project = tmp_path / "free_design_proj"
    project.mkdir()
    (project / "svg_output").mkdir()
    (project / "spec_lock.md").write_text(
        '## template_lock\n- template: ""\n- source_dir: templates\n- routes_required: false\n- variant_files_present: 0\n\n'
        '## canvas\n- viewBox: 0 0 1280 720\n- format: PPT 16:9\n\n'
        '## page_rhythm\n- P01: anchor\n- P02: dense\n',
        encoding="utf-8",
    )
    code, stdout, _ = _run_seeder(project)
    assert code == 0
    assert "free design" in stdout.lower() or "no skeletons" in stdout.lower()
    # No skeleton files created
    assert list((project / "svg_output").glob("*.skeleton.svg")) == []


# ---------- error paths ----------

def test_seeder_fails_when_declared_variant_missing(tmp_path: Path) -> None:
    project = _seed_alauda_project(
        tmp_path,
        with_routes=["P02: nonexistent_intent | 99_nonexistent.svg | grammar | budget"],
    )
    code, _, stderr = _run_seeder(project)
    assert code == 1
    assert "99_nonexistent.svg" in stderr or "not found" in stderr


def test_seeder_returns_2_when_spec_lock_missing(tmp_path: Path) -> None:
    project = tmp_path / "no_spec"
    project.mkdir()
    code, _, stderr = _run_seeder(project)
    assert code == 2
    assert "spec_lock.md" in stderr


def test_seeder_returns_2_when_template_lock_missing(tmp_path: Path) -> None:
    project = tmp_path / "no_template_lock"
    project.mkdir()
    (project / "spec_lock.md").write_text("## canvas\n- viewBox: 0 0 1280 720\n", encoding="utf-8")
    code, _, stderr = _run_seeder(project)
    assert code == 2
    assert "template_lock" in stderr


def test_seeder_dry_run_does_not_write_files(tmp_path: Path) -> None:
    project = _seed_alauda_project(
        tmp_path,
        with_routes=["P02: platform_panorama | 03_content_panorama.svg | grammar | budget"],
    )
    code, stdout, _ = _run_seeder(project, "--dry-run")
    assert code == 0
    assert "[DRY]" in stdout
    assert not (project / "svg_output" / "slide_02_platform_panorama.skeleton.svg").exists()
    # Gate log should NOT be written in dry run
    assert not (project / ".gates" / "skeletons_seeded.json").exists()


def test_seeder_skips_existing_skeleton_unless_forced(tmp_path: Path) -> None:
    project = _seed_alauda_project(
        tmp_path,
        with_routes=["P02: platform_panorama | 03_content_panorama.svg | grammar | budget"],
    )
    # Pre-create a stale skeleton with a marker
    skeleton_path = project / "svg_output" / "slide_02_platform_panorama.skeleton.svg"
    skeleton_path.write_text("<svg>STALE_MARKER</svg>", encoding="utf-8")

    code, stdout, _ = _run_seeder(project)
    assert code == 0
    assert "SKIP" in stdout
    assert "STALE_MARKER" in skeleton_path.read_text(encoding="utf-8")  # not overwritten

    # With --force, it overwrites
    code, _, _ = _run_seeder(project, "--force")
    assert code == 0
    assert "STALE_MARKER" not in skeleton_path.read_text(encoding="utf-8")
