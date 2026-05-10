#!/usr/bin/env python3
"""PPT Master - Page skeleton seeder.

Physically pre-seeds each page's SVG with the corresponding template variant's
chrome (left accent bar, footer rule, decorative circles, logo, header bar) so
that Step 6 Executor cannot start from a blank file and silently degrade a
branded template into "color palette only" output. This is the v1.6.0 fix for
the failure mode where the model writes correct spec_lock.md ## semantic_routes
yet hand-writes each page from scratch in Step 6.

Workflow:
    Step 6 GATE → spec_lock_validator.py → gate_check.py → page_skeleton_seeder.py
    → Executor opens svg_output/slide_<NN>_<intent>.skeleton.svg, edits in place,
    renames to slide_<NN>_<intent>.svg.

Usage:
    python3 page_skeleton_seeder.py <project_path>
    python3 page_skeleton_seeder.py <project_path> --dry-run  # report what would be seeded
    python3 page_skeleton_seeder.py <project_path> --force    # overwrite existing skeletons

Exit codes:
    0 — all routed pages seeded (or free design / no work)
    1 — at least one variant SVG missing or unreadable
    2 — spec_lock.md missing / unparseable / project path invalid
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


CONTENT_TEXT_PLACEHOLDER_MAP = [
    # (regex on inner text, placeholder)
    (re.compile(r"\{\{[A-Z_]+\}\}"), None),  # already a placeholder, leave alone
    (re.compile(r"^Page Title|页面标题|Title$", re.IGNORECASE), "{{TITLE}}"),
    (re.compile(r"^Key Message|关键信息|Subtitle$", re.IGNORECASE), "{{KEY_MESSAGE}}"),
]

ANCHOR_PAGE_DEFAULTS = {
    # page intent → variant filename
    "cover": "01_cover.svg",
    "toc": "02_toc.svg",
    "chapter": "02_chapter.svg",
    "chapter_opener": "02_chapter.svg",
    "ending": "04_ending.svg",
}


def _parse_section(spec_lock_text: str, name: str) -> list[str]:
    pattern = re.compile(
        r"^##\s+" + re.escape(name) + r"\s*$(?P<body>.*?)(?=^##\s+\S|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(spec_lock_text)
    if not match:
        return []
    out: list[str] = []
    for raw in match.group("body").splitlines():
        s = raw.strip()
        if not s or s.startswith(">"):
            continue
        if s.startswith("- "):
            out.append(s[2:].strip())
    return out


def _parse_kv(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.split("#", 1)[0].strip().strip('"')
    return out


def _parse_routes(lines: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    page_re = re.compile(r"^(P\d{2,3})\s*:\s*(.+)$")
    for line in lines:
        m = page_re.match(line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split("|")]
        if len(parts) < 2:
            continue
        out[m.group(1)] = {
            "page_intent": parts[0],
            "template_variant": parts[1],
            "visual_grammar": parts[2] if len(parts) > 2 else "",
        }
    return out


def _parse_rhythm(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    pat = re.compile(r"^(P\d{2,3})\s*:\s*(\w+)")
    for line in lines:
        m = pat.match(line)
        if m:
            out[m.group(1)] = m.group(2).lower()
    return out


def _slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text.lower() or "page"


def _replace_content_text_with_placeholders(svg_text: str) -> str:
    """Replace text inside `data-role="content-*"` <text> nodes with placeholders.

    Chrome elements (footer text, accent bar, decor circles) are left untouched.
    Content slots are wiped to clean placeholders so Executor sees a clear edit
    surface and doesn't accidentally inherit template's sample copy.
    """
    # Match <text ... data-slot="content-*" ...>inner</text> or content-bearing data-role
    content_text_re = re.compile(
        r'(<text\b[^>]*data-(?:slot|role)="(?:content-|body-|message-|title-)[^"]*"[^>]*>)'
        r'([^<]*?)'
        r'(</text>)',
        re.DOTALL,
    )

    def _replace(m: re.Match) -> str:
        tag_open, _inner, tag_close = m.group(1), m.group(2), m.group(3)
        # Pick placeholder based on slot/role hint in the tag
        slot_match = re.search(r'data-(?:slot|role)="([^"]+)"', tag_open)
        slot = slot_match.group(1) if slot_match else "content"
        if "title" in slot:
            ph = "{{TITLE}}"
        elif "message" in slot or "subtitle" in slot:
            ph = "{{KEY_MESSAGE}}"
        else:
            ph = "{{CONTENT}}"
        return f"{tag_open}{ph}{tag_close}"

    return content_text_re.sub(_replace, svg_text)


def _resolve_variant_for_page(
    page: str,
    rhythm: dict[str, str],
    routes: dict[str, dict[str, str]],
    page_intent_hint: str | None = None,
) -> str | None:
    """Resolve which template variant SVG to seed for a given page.

    Order:
    1. If page is in routes (semantic_routes), use the declared template_variant.
    2. If page is anchor and has an inferable structural intent, use the
       ANCHOR_PAGE_DEFAULTS map (cover/toc/chapter/ending).
    3. Otherwise return None (page should be skipped — likely a free-content
       page in a deck without semantic routes).
    """
    if page in routes:
        return routes[page]["template_variant"]
    if rhythm.get(page) == "anchor":
        # Page intent hint should come from somewhere reliable; for now infer
        # from page index (P01 = cover, last anchor = ending) — Strategist
        # SHOULD add explicit anchor_intent in spec_lock; this is a fallback.
        if page == "P01":
            return ANCHOR_PAGE_DEFAULTS["cover"]
        # All other anchor pages need explicit intent; can't safely guess.
        return None
    return None


def seed_project(project_path: Path, *, dry_run: bool, force: bool) -> tuple[int, list[str]]:
    """Return (exit_code, messages). Code 0 = ok, 1 = variant missing, 2 = spec_lock issue."""
    msgs: list[str] = []

    spec_lock = project_path / "spec_lock.md"
    if not spec_lock.exists():
        return 2, [f"spec_lock.md not found at {spec_lock}"]

    text = spec_lock.read_text(encoding="utf-8")
    template_lock = _parse_kv(_parse_section(text, "template_lock"))

    if not template_lock:
        return 2, [
            "spec_lock.md is missing the `## template_lock` section. "
            "Run spec_lock_validator.py first; if branded template, Strategist must populate template_lock."
        ]

    template_name = template_lock.get("template", "").strip()
    if not template_name:
        msgs.append("[OK] template_lock.template = \"\" (free design); no skeletons to seed.")
        return 0, msgs

    template_dir = project_path / template_lock.get("source_dir", "templates").strip("/")
    if not template_dir.exists():
        return 1, [f"template directory missing: {template_dir}"]

    rhythm = _parse_rhythm(_parse_section(text, "page_rhythm"))
    routes = _parse_routes(_parse_section(text, "semantic_routes"))

    if not rhythm:
        return 2, [
            "spec_lock.md ## page_rhythm is empty/missing — cannot determine which pages need seeding."
        ]

    svg_output_dir = project_path / "svg_output"
    svg_output_dir.mkdir(parents=True, exist_ok=True)

    seeded_log: list[dict] = []
    failed: list[str] = []

    # Sort pages numerically for deterministic seeding order.
    for page in sorted(rhythm.keys(), key=lambda p: int(p[1:])):
        variant = _resolve_variant_for_page(page, rhythm, routes)
        if not variant:
            msgs.append(f"[SKIP] {page} (rhythm={rhythm[page]}): no variant resolved")
            continue

        variant_path = template_dir / variant
        if not variant_path.exists():
            failed.append(f"{page}: declared variant {variant!r} not found at {variant_path}")
            continue

        # Determine output skeleton filename: slide_<NN>_<intent>.skeleton.svg
        page_num = page[1:].zfill(2)
        if page in routes:
            intent_slug = _slugify(routes[page]["page_intent"])
        elif rhythm[page] == "anchor" and page == "P01":
            intent_slug = "cover"
        else:
            intent_slug = "page"
        skeleton_path = svg_output_dir / f"slide_{page_num}_{intent_slug}.skeleton.svg"

        if skeleton_path.exists() and not force:
            msgs.append(f"[SKIP] {skeleton_path.name} exists; use --force to overwrite")
            continue

        try:
            variant_text = variant_path.read_text(encoding="utf-8")
            templated = _replace_content_text_with_placeholders(variant_text)
            if not dry_run:
                skeleton_path.write_text(templated, encoding="utf-8")
            seeded_log.append({
                "page": page,
                "variant": variant,
                "skeleton_path": str(skeleton_path.relative_to(project_path)),
                "intent": intent_slug,
            })
            msgs.append(
                f"[{'DRY' if dry_run else 'SEEDED'}] {page} → {skeleton_path.name} (from {variant})"
            )
        except OSError as exc:
            failed.append(f"{page}: failed to read/write {variant} → {skeleton_path}: {exc}")

    if not dry_run and seeded_log:
        gates_dir = project_path / ".gates"
        gates_dir.mkdir(exist_ok=True)
        log_path = gates_dir / "skeletons_seeded.json"
        log_path.write_text(
            json.dumps(
                {
                    "seeded_pages": seeded_log,
                    "template": template_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        msgs.append(f"[OK] wrote {log_path.relative_to(project_path)} with {len(seeded_log)} entries")

    if failed:
        return 1, msgs + ["[FAIL] " + f for f in failed]
    return 0, msgs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed page SVG skeletons from template variants for ppt-master Step 6."
    )
    parser.add_argument("project_path", help="PPT project directory path")
    parser.add_argument("--dry-run", action="store_true", help="Report planned seeds without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .skeleton.svg files")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    args = parser.parse_args(argv)

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"[ERROR] project path not found: {project_path}", file=sys.stderr)
        return 2

    code, msgs = seed_project(project_path, dry_run=args.dry_run, force=args.force)

    if code != 0:
        for m in msgs:
            stream = sys.stderr if m.startswith("[FAIL]") else sys.stdout
            print(m, file=stream)
        if code == 1:
            print(
                "\nFix: ensure each declared template_variant exists under templates/, "
                "then re-run. spec_lock_validator.py will also catch missing variants.",
                file=sys.stderr,
            )
        elif code == 2:
            print(
                "\nFix: run spec_lock_validator.py first; Strategist must produce a complete "
                "spec_lock.md with template_lock + page_rhythm + (if applicable) semantic_routes.",
                file=sys.stderr,
            )
        return code

    if not args.quiet:
        for m in msgs:
            print(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
