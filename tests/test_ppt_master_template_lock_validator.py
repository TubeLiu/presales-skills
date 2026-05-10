"""Tests for spec_lock_validator.py + gate_check.py.

Covers the v1.5.0 contracts that prevent (a) branded templates from silently
degrading into "color palette only" output and (b) weak models from skipping
the BLOCKING confirmation gates. Each test is a fixture-style assertion, not
a sample patch — per CLAUDE.md §6 anti-hardcoding rule.
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


def _run_validator(project_path: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "spec_lock_validator.py"), str(project_path)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_gate_check(project_path: Path, require: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "gate_check.py"),
            str(project_path),
            "--require",
            require,
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _seed_alauda_project(tmp_path: Path, *, with_routes: bool, with_template_lock: bool) -> Path:
    """Build a minimal project that mimics what Step 3 + Step 4 produce."""
    project = tmp_path / "alauda_project"
    project.mkdir()
    templates_dir = project / "templates"
    templates_dir.mkdir()

    # Copy a representative subset of Alauda template assets.
    for name in (
        "semantic_routes.json",
        "visual_system.json",
        "03_content.svg",
        "03_content_panorama.svg",
        "03_content_architecture.svg",
        "03_content_migration.svg",
        "03_content_table.svg",
    ):
        src = ALAUDA_DIR / name
        if src.exists():
            shutil.copy(src, templates_dir / name)

    if not with_routes:
        (templates_dir / "semantic_routes.json").unlink(missing_ok=True)

    spec_lock_lines: list[str] = []
    if with_template_lock:
        spec_lock_lines.extend(
            [
                "## template_lock",
                "- template: alauda",
                "- source_dir: templates",
                f"- routes_required: {'true' if with_routes else 'false'}",
                "- variant_files_present: 5",
                "",
            ]
        )

    spec_lock_lines.extend(
        [
            "## canvas",
            "- viewBox: 0 0 1280 720",
            "- format: PPT 16:9",
            "",
            "## page_rhythm",
            "- P01: anchor",
            "- P02: dense",
            "- P03: dense",
            "- P04: dense",
            "- P05: anchor",
            "",
        ]
    )

    if with_routes and with_template_lock:
        spec_lock_lines.extend(
            [
                "## semantic_routes",
                "- P02: platform_panorama | 03_content_panorama.svg | domain_row_platform_core_infra_row | title<=18; notes_overflow=yes",
                "- P03: architecture_stack | 03_content_architecture.svg | four_layer_stack_with_downward_dependency | layer_title<=12; notes_overflow=yes",
                "- P04: migration_bridge | 03_content_migration.svg | before_bridge_after | panel_title<=12; notes_overflow=yes",
                "",
            ]
        )

    (project / "spec_lock.md").write_text("\n".join(spec_lock_lines), encoding="utf-8")
    return project


# ---------- spec_lock_validator.py ----------


def test_validator_accepts_complete_alauda_project(tmp_path: Path) -> None:
    project = _seed_alauda_project(tmp_path, with_routes=True, with_template_lock=True)
    code, stdout, stderr = _run_validator(project)
    assert code == 0, f"expected pass, got code={code}\nstdout={stdout}\nstderr={stderr}"
    assert "satisfied" in stdout


def test_validator_blocks_when_template_lock_missing(tmp_path: Path) -> None:
    project = _seed_alauda_project(tmp_path, with_routes=True, with_template_lock=False)
    code, _, stderr = _run_validator(project)
    assert code == 1, "missing template_lock must block"
    assert "template_lock" in stderr


def test_validator_blocks_when_branded_template_lacks_semantic_routes(tmp_path: Path) -> None:
    project = _seed_alauda_project(tmp_path, with_routes=True, with_template_lock=True)
    text = (project / "spec_lock.md").read_text(encoding="utf-8")
    text = text.replace("## semantic_routes\n", "")
    # Strip the route entry lines too.
    cleaned = []
    for line in text.splitlines():
        if line.startswith("- P02:") and "platform_panorama" in line:
            continue
        if line.startswith("- P03:") and "architecture_stack" in line:
            continue
        if line.startswith("- P04:") and "migration_bridge" in line:
            continue
        cleaned.append(line)
    (project / "spec_lock.md").write_text("\n".join(cleaned), encoding="utf-8")

    code, _, stderr = _run_validator(project)
    assert code == 1, "branded template without semantic_routes must block"
    assert "semantic_routes" in stderr


def test_validator_accepts_free_design_when_consistently_declared(tmp_path: Path) -> None:
    project = tmp_path / "free_design_project"
    project.mkdir()
    (project / "spec_lock.md").write_text(
        "\n".join(
            [
                "## template_lock",
                "- template: \"\"",
                "- source_dir: templates",
                "- routes_required: false",
                "- variant_files_present: 0",
                "",
                "## canvas",
                "- viewBox: 0 0 1280 720",
                "- format: PPT 16:9",
                "",
            ]
        ),
        encoding="utf-8",
    )
    code, stdout, _ = _run_validator(project)
    assert code == 0, "consistent free design must pass"
    assert "satisfied" in stdout


def test_validator_rejects_contradictory_free_design(tmp_path: Path) -> None:
    project = tmp_path / "contradictory_project"
    project.mkdir()
    (project / "spec_lock.md").write_text(
        "\n".join(
            [
                "## template_lock",
                "- template: \"\"",
                "- source_dir: templates",
                "- routes_required: true",  # contradicts empty template
                "- variant_files_present: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    code, _, stderr = _run_validator(project)
    assert code == 1, "free design + routes_required=true is a contradiction"
    assert "free design" in stderr or "routes_required" in stderr


def test_validator_rejects_unknown_variant_file(tmp_path: Path) -> None:
    project = _seed_alauda_project(tmp_path, with_routes=True, with_template_lock=True)
    text = (project / "spec_lock.md").read_text(encoding="utf-8")
    text = text.replace(
        "03_content_migration.svg",
        "03_content_nonexistent.svg",
    )
    (project / "spec_lock.md").write_text(text, encoding="utf-8")

    code, _, stderr = _run_validator(project)
    assert code == 1, "unknown variant file must block"
    assert "03_content_nonexistent.svg" in stderr


def test_validator_returns_2_when_spec_lock_missing(tmp_path: Path) -> None:
    project = tmp_path / "empty_project"
    project.mkdir()
    code, _, stderr = _run_validator(project)
    assert code == 2
    assert "spec_lock.md" in stderr


# ---------- gate_check.py ----------


def _write_gate(project: Path, name: str, payload: dict) -> None:
    gates_dir = project / ".gates"
    gates_dir.mkdir(exist_ok=True)
    (gates_dir / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_gate_check_passes_when_required_files_have_passed_true(tmp_path: Path) -> None:
    project = tmp_path / "gated_project"
    project.mkdir()
    _write_gate(project, "nine_confirmations", {"passed": True, "verdict": "explicit_confirmation"})
    _write_gate(project, "design_review", {"passed": True, "verdict": "explicit_confirmation"})
    code, stdout, _ = _run_gate_check(project, "nine_confirmations,design_review")
    assert code == 0
    assert "passed" in stdout


def test_gate_check_blocks_when_gate_file_missing(tmp_path: Path) -> None:
    project = tmp_path / "gated_project"
    project.mkdir()
    (project / ".gates").mkdir()
    _write_gate(project, "nine_confirmations", {"passed": True})
    code, _, stderr = _run_gate_check(project, "nine_confirmations,design_review")
    assert code == 1
    assert "design_review" in stderr
    assert "missing" in stderr


def test_gate_check_blocks_when_passed_is_false(tmp_path: Path) -> None:
    project = tmp_path / "gated_project"
    project.mkdir()
    _write_gate(project, "nine_confirmations", {"passed": False, "verdict": "user_requested_modification"})
    code, _, stderr = _run_gate_check(project, "nine_confirmations")
    assert code == 1
    assert "nine_confirmations" in stderr


def test_gate_check_blocks_when_gates_dir_missing(tmp_path: Path) -> None:
    project = tmp_path / "no_gates_project"
    project.mkdir()
    code, _, stderr = _run_gate_check(project, "nine_confirmations")
    assert code == 1
    assert ".gates" in stderr


def test_gate_check_recognizes_audio_choice_with_none_mode(tmp_path: Path) -> None:
    """audio_mode=none is still a valid user decision; passed must be true."""
    project = tmp_path / "audio_none_project"
    project.mkdir()
    _write_gate(
        project,
        "audio_choice",
        {"passed": True, "verdict": "explicit_confirmation", "audio_mode": "none"},
    )
    code, _, _ = _run_gate_check(project, "audio_choice")
    assert code == 0


# ---------- end-to-end integration: project_manager init creates .gates ----------


def test_project_manager_init_creates_gates_dir(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "project_manager.py"),
            "init",
            "validator_smoke_test",
            "--format",
            "ppt169",
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"init failed: {proc.stderr}"
    # find the created project
    created = next(tmp_path.glob("validator_smoke_test_*"))
    gates_dir = created / ".gates"
    assert gates_dir.exists() and gates_dir.is_dir(), ".gates/ should be auto-created"
    assert (gates_dir / "README.md").exists(), ".gates/README.md should explain the contract"


# ---------- contract documentation cross-checks ----------


def test_skill_md_references_new_validator_and_gate_check() -> None:
    skill_md = (ROOT / "ppt-master/skills/make/SKILL.md").read_text(encoding="utf-8")
    assert "spec_lock_validator.py" in skill_md, (
        "SKILL.md must invoke spec_lock_validator.py at Step 5/6 GATE"
    )
    assert "gate_check.py" in skill_md, (
        "SKILL.md must invoke gate_check.py at Step 5/6/7 GATE"
    )
    assert "Nine Confirmations" in skill_md, "SKILL.md should use new 'Nine Confirmations' wording"
    # Make sure the old wording was actually replaced everywhere it counted.
    assert "Eight Confirmations" not in skill_md, (
        "SKILL.md still has stale 'Eight Confirmations' references"
    )


def test_strategist_md_describes_template_layout_grammar_subsection() -> None:
    strategist = (ROOT / "ppt-master/skills/make/references/strategist.md").read_text(encoding="utf-8")
    assert "Template + Layout Grammar" in strategist, (
        "strategist.md must describe the new 4th confirmation"
    )
    assert "Nine Confirmations Process" in strategist
