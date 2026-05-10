#!/usr/bin/env python3
"""PPT Master - workflow gate state checker.

Reads `<project_path>/.gates/*.json` files written by Strategist after each
BLOCKING confirmation point and asserts that downstream Steps may proceed.
This is the machine-readable counterpart to SKILL.md's prose `⛔ BLOCKING`
markers — it exists because weak models routinely "remember" a confirmation
the user never gave. Gate state files override AI memory.

Gate file shape (canonical):
    {
      "passed": true,
      "verdict": "explicit_confirmation",
      "user_reply_snippet": "...",
      "items_locked": ["canvas:ppt169", "template:alauda", ...],
      "timestamp": "2026-05-10T12:34:56Z"
    }

Recognized gates:
    nine_confirmations  — Step 4 result (formerly "eight_confirmations")
    design_review       — Step 4.5 result
    audio_choice        — Step 4.5 ⑤ audio decision (passed=true means a choice
                          was made, regardless of audio_mode value)

Usage:
    python3 gate_check.py <project_path> --require nine_confirmations
    python3 gate_check.py <project_path> --require nine_confirmations,design_review
    python3 gate_check.py <project_path> --status   # print all gate states

Exit codes:
    0 — all required gates passed
    1 — at least one required gate is missing or passed=false
    2 — project path or .gates directory missing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KNOWN_GATES = ("nine_confirmations", "design_review", "audio_choice")


def _read_gate(gates_dir: Path, name: str) -> tuple[str, dict | None]:
    """Return (state_label, raw_dict_or_None). state_label ∈ missing|invalid|failed|passed."""
    path = gates_dir / f"{name}.json"
    if not path.exists():
        return "missing", None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid", None
    if not isinstance(data, dict):
        return "invalid", None
    if data.get("passed") is True:
        return "passed", data
    return "failed", data


def _print_status(gates_dir: Path) -> int:
    print(f"Gates under {gates_dir}:")
    if not gates_dir.exists():
        print("  (.gates/ directory does not exist)")
        return 2
    for name in KNOWN_GATES:
        state, data = _read_gate(gates_dir, name)
        if state == "passed":
            verdict = data.get("verdict", "?") if data else "?"
            print(f"  [{state.upper():7}] {name}  (verdict={verdict})")
        elif state == "failed":
            verdict = data.get("verdict", "?") if data else "?"
            print(f"  [{state.upper():7}] {name}  (verdict={verdict}; passed={data.get('passed')!r})")
        else:
            print(f"  [{state.upper():7}] {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check workflow gate state files for ppt-master.",
    )
    parser.add_argument("project_path", help="Path to the PPT project directory")
    parser.add_argument(
        "--require",
        default="",
        help="Comma-separated list of gate names that must be passed (nine_confirmations,design_review,audio_choice)",
    )
    parser.add_argument("--status", action="store_true", help="Print state of all gates and exit 0")
    parser.add_argument("--quiet", action="store_true", help="Exit code only; no output")
    args = parser.parse_args(argv)

    project_path = Path(args.project_path)
    if not project_path.exists():
        if not args.quiet:
            print(f"[ERROR] project path not found: {project_path}", file=sys.stderr)
        return 2

    gates_dir = project_path / ".gates"

    if args.status:
        return _print_status(gates_dir)

    required = [g.strip() for g in args.require.split(",") if g.strip()]
    if not required:
        if not args.quiet:
            print("[ERROR] specify --require <gate>[,<gate>...] or --status", file=sys.stderr)
        return 2

    unknown = [g for g in required if g not in KNOWN_GATES]
    if unknown:
        if not args.quiet:
            print(
                f"[ERROR] unknown gate(s): {unknown}. Known: {list(KNOWN_GATES)}",
                file=sys.stderr,
            )
        return 2

    if not gates_dir.exists():
        if not args.quiet:
            print(
                f"[FAIL] {gates_dir} does not exist. "
                "Strategist must write .gates/*.json after each BLOCKING confirmation; "
                "this is the contract that lets weak models prove they actually waited "
                "for the user instead of inventing a confirmation.",
                file=sys.stderr,
            )
        return 1

    failures: list[str] = []
    for name in required:
        state, data = _read_gate(gates_dir, name)
        if state == "passed":
            continue
        if state == "missing":
            failures.append(
                f"{name}: gate file .gates/{name}.json is missing — "
                "Strategist did not record an explicit user confirmation. "
                "Stop and ask the user; do NOT proceed."
            )
        elif state == "invalid":
            failures.append(
                f"{name}: .gates/{name}.json is not valid JSON or not an object."
            )
        else:  # failed
            verdict = data.get("verdict", "(no verdict)") if data else "(no data)"
            failures.append(
                f"{name}: passed={data.get('passed')!r} (verdict={verdict}). "
                "User changed their mind or never explicitly confirmed; "
                "re-present the relevant items and wait for explicit reply."
            )

    if not failures:
        if not args.quiet:
            print(f"[OK] required gates passed: {required}")
        return 0

    if not args.quiet:
        print(f"[FAIL] gate check blocked {project_path}:", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        print(
            "\nGate state files OVERRIDE AI memory. If you 'remember' the user confirmed, "
            "but the file says otherwise, the file wins. Re-ask the user.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
