#!/usr/bin/env python3
"""PPT Master - Step 4.5 ⑤ audio decision validator.

Verifies that the design_review.md output (Step 4.5 deliverable) actually
includes the ⑤ audio strategy section AND that the corresponding gate file
.gates/audio_choice.json was written. This closes the v1.5.0 gap where the
audio decision was added to the workflow but Strategist could (and did)
silently skip writing item ⑤ when generating design_review.md, leaving
Step 7.3 with no audio choice and forcing the AI to either skip audio
entirely or ad-hoc ask the user too late.

Usage:
    python3 audio_decision_validator.py <project_path>
    python3 audio_decision_validator.py <project_path> --quiet

Exit codes:
    0 — design_review.md ⑤ section present AND .gates/audio_choice.json exists
    1 — one or both missing (Strategist must redo Step 4.5)
    2 — design_review.md missing entirely (Strategist hasn't started Step 4.5)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Regex catches the ⑤ audio section under any of: ## 配音 / ## 音频 / ## audio
# / a heading containing "audio_mode", or an explicit "⑤" marker. Case- and
# whitespace-tolerant. Tested against the design-review-gate.md sample format.
AUDIO_SECTION_PATTERNS = [
    re.compile(r'^##\s*[⑤5]?[\s.]*配音', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^##\s*[⑤5]?[\s.]*音频', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^##\s*[⑤5]?[\s.]*audio\b', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\s*-?\s*\*?\*?audio_mode\*?\*?\s*[:：]', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^[⑤5]\s*[.、]?\s*(配音|音频|audio)', re.MULTILINE | re.IGNORECASE),
]

VALID_AUDIO_MODES = {'none', 'edge_default', 'cloud_quality', 'recorded_existing'}


def _has_audio_section(design_review_text: str) -> bool:
    return any(p.search(design_review_text) for p in AUDIO_SECTION_PATTERNS)


def validate(project_path: Path) -> tuple[int, list[str]]:
    errors: list[str] = []

    design_review = project_path / 'design_review.md'
    if not design_review.exists():
        return 2, [
            f"design_review.md not found at {design_review} — "
            "Strategist hasn't produced the Step 4.5 deliverable yet."
        ]

    try:
        review_text = design_review.read_text(encoding='utf-8')
    except OSError as exc:
        return 2, [f"failed to read design_review.md: {exc}"]

    if not _has_audio_section(review_text):
        errors.append(
            "design_review.md is missing the ⑤ 配音 / 音频 strategy section. "
            "Strategist MUST add it before user confirmation — even when the "
            "user's original command did not mention audio. The default value "
            "(audio_mode: edge_default) is a decision; silence is not. See "
            "references/design-review-gate.md ⑤ for the required format."
        )

    audio_gate = project_path / '.gates' / 'audio_choice.json'
    if not audio_gate.exists():
        errors.append(
            f".gates/audio_choice.json missing — even if ⑤ section is in "
            "design_review.md, Strategist MUST persist the user's audio "
            "decision to this gate file with shape "
            "{'passed': true, 'audio_mode': '<one of "
            f"{sorted(VALID_AUDIO_MODES)}>', ...}}. Step 7.3 reads this file "
            "to dispatch notes_to_audio.py + svg_to_pptx --recorded-narration."
        )
    else:
        try:
            data = json.loads(audio_gate.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(
                f".gates/audio_choice.json exists but is unreadable/invalid JSON: {exc}"
            )
        else:
            mode = data.get('audio_mode')
            if mode not in VALID_AUDIO_MODES:
                errors.append(
                    f".gates/audio_choice.json has audio_mode={mode!r}; must be one of "
                    f"{sorted(VALID_AUDIO_MODES)}"
                )
            if data.get('passed') is not True:
                errors.append(
                    ".gates/audio_choice.json has passed != true; user has not yet "
                    "confirmed the audio choice. Re-present design_review.md ⑤."
                )

    return (1 if errors else 0), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Step 4.5 ⑤ audio decision capture for ppt-master."
    )
    parser.add_argument('project_path', help='PPT project directory')
    parser.add_argument('--quiet', action='store_true', help='Exit code only')
    args = parser.parse_args(argv)

    project_path = Path(args.project_path)
    if not project_path.exists():
        if not args.quiet:
            print(f'[ERROR] project path not found: {project_path}', file=sys.stderr)
        return 2

    code, errors = validate(project_path)

    if args.quiet:
        return code

    if code == 0:
        print(f'[OK] design_review.md ⑤ + .gates/audio_choice.json both present at {project_path}')
        return 0

    print(f'[FAIL] audio decision capture incomplete in {project_path}', file=sys.stderr)
    for err in errors:
        print(f'  - {err}', file=sys.stderr)
    print(
        '\nFix: Strategist must (1) add ⑤ audio section to design_review.md, '
        '(2) wait for user confirmation, (3) write .gates/audio_choice.json '
        'with the chosen audio_mode. See references/design-review-gate.md ⑤.',
        file=sys.stderr,
    )
    return code


if __name__ == '__main__':
    sys.exit(main())
