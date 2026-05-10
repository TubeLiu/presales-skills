#!/usr/bin/env python3
"""PPT Master - spec_lock.md template_lock + semantic_routes validator.

Enforces the template-routing contract that prevents Alauda (or any branded
template) from silently degrading into "color palette only" output. This is the
machine-checkable counterpart to the prose contract in
`templates/spec_lock_reference.md ## template_lock`.

Usage:
    python3 spec_lock_validator.py <project_path>
    python3 spec_lock_validator.py <project_path> --quiet   # exit code only

Exit codes:
    0 — spec_lock.md template contract is satisfied (or free design declared)
    1 — contract violation (details on stderr)
    2 — spec_lock.md missing or unparseable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable


STRUCTURAL_INTENTS = {"cover", "toc", "chapter", "ending", "chapter_opener"}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_section(spec_lock_text: str, section_name: str) -> list[str]:
    """Return the raw `- ...` lines under `## <section_name>`, blockquotes stripped."""
    pattern = re.compile(
        r"^##\s+" + re.escape(section_name) + r"\s*$(?P<body>.*?)(?=^##\s+\S|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(spec_lock_text)
    if not match:
        return []
    body = match.group("body")
    lines: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("- "):
            lines.append(stripped[2:].strip())
    return lines


def _parse_kv_section(lines: Iterable[str]) -> dict[str, str]:
    """Parse `key: value` pairs from a section's `- key: value` lines."""
    out: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.split("#", 1)[0].strip().strip('"')
    return out


def _parse_route_lines(lines: Iterable[str]) -> dict[str, dict[str, str]]:
    """Parse `## semantic_routes` page entries into {P02: {intent, variant, grammar, budget}}."""
    out: dict[str, dict[str, str]] = {}
    page_re = re.compile(r"^(P\d{2,3})\s*:\s*(.+)$")
    for line in lines:
        m = page_re.match(line)
        if not m:
            continue
        page = m.group(1)
        parts = [p.strip() for p in m.group(2).split("|")]
        if len(parts) < 2:
            continue
        out[page] = {
            "page_intent": parts[0] if len(parts) > 0 else "",
            "template_variant": parts[1] if len(parts) > 1 else "",
            "visual_grammar": parts[2] if len(parts) > 2 else "",
            "payload_budget": parts[3] if len(parts) > 3 else "",
        }
    return out


def _parse_page_rhythm(lines: Iterable[str]) -> dict[str, str]:
    """Return {P01: anchor, P02: dense, ...}."""
    out: dict[str, str] = {}
    pat = re.compile(r"^(P\d{2,3})\s*:\s*(\w+)")
    for line in lines:
        m = pat.match(line)
        if m:
            out[m.group(1)] = m.group(2).lower()
    return out


def _emit_error(messages: list[str], msg: str) -> None:
    messages.append(msg)


def validate_spec_lock(project_path: Path) -> tuple[int, list[str]]:
    """Return (exit_code, error_messages). exit_code 0 = pass."""
    errors: list[str] = []
    spec_lock_path = project_path / "spec_lock.md"

    if not spec_lock_path.exists():
        return 2, [f"spec_lock.md not found at {spec_lock_path}"]

    try:
        text = _read_text(spec_lock_path)
    except OSError as exc:
        return 2, [f"failed to read spec_lock.md: {exc}"]

    template_lock = _parse_kv_section(_parse_section(text, "template_lock"))

    if not template_lock:
        _emit_error(
            errors,
            "spec_lock.md is missing the `## template_lock` section. "
            "Strategist MUST declare the template choice up front; "
            "see templates/spec_lock_reference.md for the canonical skeleton.",
        )
        return 1, errors

    template_name = template_lock.get("template", "").strip()
    routes_required_raw = template_lock.get("routes_required", "").lower()
    routes_required = routes_required_raw in {"true", "yes", "1"}

    # Free-design path: explicitly opted out of template routing.
    if not template_name:
        if routes_required:
            _emit_error(
                errors,
                "template_lock.template is empty (free design) but routes_required=true. "
                "These must agree: free design implies routes_required=false.",
            )
            return 1, errors
        return 0, []

    # Branded template path — verify template assets are actually present.
    template_dir = project_path / template_lock.get("source_dir", "templates").strip("/")
    semantic_routes_json = template_dir / "semantic_routes.json"

    if not template_dir.exists():
        _emit_error(
            errors,
            f"template_lock.template={template_name!r} but {template_dir} is missing. "
            "Did Step 3 actually copy the template package into the project?",
        )
        return 1, errors

    if not semantic_routes_json.exists():
        # Template package without a route catalog (e.g. legacy minimal template).
        # routes_required must be false in this case; otherwise it's a contradiction.
        if routes_required:
            _emit_error(
                errors,
                f"{semantic_routes_json} not found, but template_lock.routes_required=true. "
                "Either the template has no semantic_routes.json (set routes_required=false) "
                "or Step 3 didn't copy it (re-run template setup).",
            )
            return 1, errors
        return 0, []

    # We have semantic_routes.json — the contract requires spec_lock to mirror it.
    try:
        catalog = json.loads(_read_text(semantic_routes_json))
    except (OSError, json.JSONDecodeError) as exc:
        _emit_error(
            errors,
            f"failed to parse {semantic_routes_json}: {exc}",
        )
        return 1, errors

    catalog_intents = {r.get("pageIntent") for r in catalog.get("routes", [])}
    default_route = catalog.get("defaultRoute", {})
    if default_route.get("pageIntent"):
        catalog_intents.add(default_route["pageIntent"])

    catalog_variants = {r.get("variantFile") for r in catalog.get("routes", [])}
    if default_route.get("variantFile"):
        catalog_variants.add(default_route["variantFile"])

    spec_routes = _parse_route_lines(_parse_section(text, "semantic_routes"))

    if not spec_routes:
        _emit_error(
            errors,
            "spec_lock.md ## semantic_routes is empty/missing. "
            f"Template {template_name!r} provides {semantic_routes_json.name} with "
            f"{len(catalog.get('routes', []))} routes — Strategist MUST declare a "
            "P<NN>: page_intent | template_variant | visual_grammar | payload_budget "
            "line for every non-structural content page (cover/toc/chapter/ending excluded).",
        )
        return 1, errors

    # Cross-check: every page in semantic_routes must reference a real variant + valid intent.
    rhythm = _parse_page_rhythm(_parse_section(text, "page_rhythm"))
    structural_pages = {p for p, tag in rhythm.items() if tag == "anchor"}

    available_variants = {p.name for p in template_dir.glob("*.svg")}

    for page, route in sorted(spec_routes.items()):
        intent = route["page_intent"]
        variant = route["template_variant"]

        if intent not in catalog_intents and intent != "custom_content":
            _emit_error(
                errors,
                f"{page}: page_intent={intent!r} is not in {semantic_routes_json.name} "
                f"(known: {sorted(catalog_intents)[:8]}{'...' if len(catalog_intents) > 8 else ''}). "
                "Either pick a catalog intent or use 'custom_content' with the default variant.",
            )

        if variant and variant not in available_variants:
            _emit_error(
                errors,
                f"{page}: template_variant={variant!r} does not exist in {template_dir}. "
                f"Available variants: {sorted(available_variants)[:6]}{'...' if len(available_variants) > 6 else ''}.",
            )

    # Coverage: every non-structural page in page_rhythm should have a route entry.
    if rhythm:
        non_structural = sorted(set(rhythm) - structural_pages)
        missing_routes = [p for p in non_structural if p not in spec_routes]
        if missing_routes:
            _emit_error(
                errors,
                "Non-structural pages without a semantic_routes entry: "
                f"{missing_routes}. Each content page MUST be routed (use 'custom_content | "
                "03_content.svg | ...' if no specific route fits).",
            )

    return (1 if errors else 0), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate spec_lock.md template_lock + semantic_routes contract.",
    )
    parser.add_argument("project_path", help="Path to the PPT project directory")
    parser.add_argument("--quiet", action="store_true", help="Exit code only; no output")
    args = parser.parse_args(argv)

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"[ERROR] project path not found: {project_path}", file=sys.stderr)
        return 2

    code, errors = validate_spec_lock(project_path)

    if args.quiet:
        return code

    if code == 0:
        print(f"[OK] spec_lock.md template contract satisfied for {project_path}")
        return 0

    print(f"[FAIL] spec_lock.md template contract violation in {project_path}", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    print(
        "\nSee templates/spec_lock_reference.md ## template_lock for the contract.",
        file=sys.stderr,
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
