"""Tests for v1.6.0 Pillar L: audio_decision_validator.py.

Verifies that Step 4.5 ⑤ audio decision capture is enforced as a machine
contract — both design_review.md must contain the section AND
.gates/audio_choice.json must exist with a valid audio_mode.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "ppt-master/skills/make/scripts"


def _run(project_path: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "audio_decision_validator.py"), str(project_path)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _setup_project(
    tmp_path: Path,
    *,
    review_text: str | None = None,
    audio_choice: dict | None = None,
) -> Path:
    project = tmp_path / "audio_test_proj"
    project.mkdir()
    if review_text is not None:
        (project / "design_review.md").write_text(review_text, encoding="utf-8")
    if audio_choice is not None:
        (project / ".gates").mkdir()
        (project / ".gates" / "audio_choice.json").write_text(
            json.dumps(audio_choice), encoding="utf-8"
        )
    return project


def test_passes_when_review_has_section_and_gate_exists(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ① 选定模板\n- alauda\n\n## ⑤ 配音 / 音频策略\n- audio_mode: edge_default\n",
        audio_choice={"passed": True, "audio_mode": "edge_default", "verdict": "explicit_confirmation"},
    )
    code, stdout, _ = _run(project)
    assert code == 0, f"expected pass, got: {stdout}"


def test_blocks_when_design_review_missing_audio_section(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ① 选定模板\n- alauda\n\n## ④ 质量样张\n- P03 panorama\n",  # no ⑤!
        audio_choice={"passed": True, "audio_mode": "edge_default"},
    )
    code, _, stderr = _run(project)
    assert code == 1
    assert "⑤" in stderr or "audio" in stderr.lower() or "配音" in stderr


def test_blocks_when_audio_gate_file_missing(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ⑤ 配音\n- audio_mode: edge_default\n",
        audio_choice=None,  # no gate file
    )
    code, _, stderr = _run(project)
    assert code == 1
    assert "audio_choice.json" in stderr


def test_blocks_when_audio_mode_invalid(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ⑤ audio_mode: maybe\n",
        audio_choice={"passed": True, "audio_mode": "maybe"},  # not in VALID_AUDIO_MODES
    )
    code, _, stderr = _run(project)
    assert code == 1
    assert "audio_mode" in stderr


def test_blocks_when_passed_is_false(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ⑤ 配音\n- audio_mode: edge_default\n",
        audio_choice={"passed": False, "audio_mode": "edge_default"},
    )
    code, _, stderr = _run(project)
    assert code == 1
    assert "passed" in stderr


def test_returns_2_when_design_review_missing(tmp_path: Path) -> None:
    project = tmp_path / "no_review"
    project.mkdir()
    code, _, stderr = _run(project)
    assert code == 2
    assert "design_review.md" in stderr


def test_recognizes_audio_section_via_audio_mode_inline_marker(tmp_path: Path) -> None:
    """Even without a heading, an inline `audio_mode:` line counts as ⑤ section."""
    project = _setup_project(
        tmp_path,
        review_text="some prose\n- **audio_mode**: edge_default\nmore prose\n",
        audio_choice={"passed": True, "audio_mode": "edge_default"},
    )
    code, _, _ = _run(project)
    assert code == 0


def test_recognizes_english_audio_heading(tmp_path: Path) -> None:
    project = _setup_project(
        tmp_path,
        review_text="## ⑤ Audio Strategy\n- audio_mode: none\n",
        audio_choice={"passed": True, "audio_mode": "none"},
    )
    code, _, _ = _run(project)
    assert code == 0


def test_audio_mode_none_is_valid_user_decision(tmp_path: Path) -> None:
    """audio_mode=none means 'user decided no audio'; passed:true is required."""
    project = _setup_project(
        tmp_path,
        review_text="## ⑤ 配音\n- audio_mode: none — user prefers no narration\n",
        audio_choice={"passed": True, "audio_mode": "none"},
    )
    code, _, _ = _run(project)
    assert code == 0
