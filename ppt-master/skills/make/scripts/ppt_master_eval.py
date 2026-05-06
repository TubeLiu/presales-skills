#!/usr/bin/env python3
"""
PPT Master eval harness.

This script turns recurring visual defects into repeatable checks. It does not
try to judge whether a deck is beautiful; it verifies that known hard failures
are caught by svg_quality_checker.py and optionally summarizes checker output
for a generated project.

Usage:
    python3 scripts/ppt_master_eval.py --output-dir /tmp/ppt-master-eval
    python3 scripts/ppt_master_eval.py --target /path/to/project --svg-dir svg_output
    python3 scripts/ppt_master_eval.py --target /path/to/project --design
"""

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps

ensure_deps()

from svg_quality_checker import SVGQualityChecker
from design_quality_checker import DesignQualityChecker
from design_archetype_planner import plan_archetypes, resolve_markdown_target


FIXTURES = [
    {
        "name": "clean_connector_lane",
        "expect": [],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="900" y="250" width="240" height="120" fill="#F0FDF4" rx="6"/>
  <text x="1020" y="310" fill="#334155" font-family="Arial, sans-serif" font-size="30" text-anchor="middle" dominant-baseline="middle">目标 ACP</text>
  <polygon points="884,220 840,194 840,210 806,210 806,230 840,230 840,246" fill="#3BAEE3"/>
</svg>
""",
    },
    {
        "name": "connector_text_lane",
        "expect": ["connector arrow(s) sharing a text lane"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="900" y="250" width="240" height="120" fill="#F0FDF4" rx="6"/>
  <text x="1020" y="310" fill="#334155" font-family="Arial, sans-serif" font-size="30" text-anchor="middle" dominant-baseline="middle">目标 ACP</text>
  <polygon points="890,300 846,274 846,290 812,290 812,310 846,310 846,326" fill="#3BAEE3"/>
</svg>
""",
    },
    {
        "name": "shape_over_text",
        "expect": ["shape-over-text occlusion"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="410" y="282" width="284" height="38" fill="#FFFFFF" rx="5" stroke="#E2E8F0"/>
  <text x="430" y="307" fill="#475569" font-family="Arial, sans-serif" font-size="15">资产扫描与分级</text>
  <polygon points="400,305 444,280 444,294 520,294 520,316 444,316 444,330" fill="#3BAEE3"/>
</svg>
""",
    },
    {
        "name": "container_overflow",
        "expect": ["text container overflow"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="90" height="34" fill="#F8FAFC" rx="4"/>
  <text x="108" y="123" fill="#334155" font-family="Arial, sans-serif" font-size="16">DeploymentConfig</text>
</svg>
""",
    },
    {
        "name": "text_overlap",
        "expect": ["text overlap/collision"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="120" y="120" fill="#334155" font-family="Arial, sans-serif" font-size="32">Kubernetes 组件</text>
  <text x="128" y="122" fill="#334155" font-family="Arial, sans-serif" font-size="32">DevOps 组件</text>
</svg>
""",
    },
    {
        "name": "visible_internal_metadata",
        "expect": ["visible eval/internal metadata"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="60" y="706" fill="#94A3B8" font-family="Arial, sans-serif" font-size="12">样张 P05 · mapping_table · dense_technical</text>
</svg>
""",
    },
    {
        "name": "shape_text_centering",
        "expect": ["shape text centering issue"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <circle cx="120" cy="120" r="24" fill="#3BAEE3"/>
  <text x="120" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="18" text-anchor="middle">1</text>
  <rect x="220" y="96" width="260" height="48" fill="#3BAEE3" rx="6"/>
  <text x="252" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17">迁移桥：标准化转换通道</text>
</svg>
""",
    },
    {
        "name": "multi_label_strip_centering",
        "expect": ["shape text centering issue"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="520" height="44" fill="#3BAEE3" rx="6"/>
  <text x="128" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">OCP 对象</text>
  <text x="278" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">ACP 对象</text>
  <text x="458" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">风险</text>
</svg>
""",
    },
    {
        "name": "pale_colored_block_centering",
        "expect": ["shape text centering issue"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="128" y="324" width="188" height="26" fill="#D8EFF9" rx="4"/>
  <text x="142" y="343" fill="#125B7D" font-family="Arial, sans-serif" font-size="14">应用发布</text>
  <rect x="128" y="366" width="188" height="26" fill="#F0FDF4" rx="4"/>
  <text x="142" y="385" fill="#25B273" font-family="Arial, sans-serif" font-size="14">确认范围</text>
</svg>
""",
    },
    {
        "name": "component_emphasis_centering",
        "expect": ["shape text centering issue"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="92" y="166" width="286" height="370" fill="#FFF1F0" stroke="#F4C9C5" data-role="content-card" data-text-align="left"/>
  <rect x="92" y="166" width="286" height="44" fill="#F0524A" data-role="label" data-slot="label"/>
  <text x="235" y="188" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" font-weight="700" text-anchor="middle" dominant-baseline="middle">当前发布模式</text>
  <text x="122" y="244" fill="#F0524A" font-family="Arial, sans-serif" font-size="30" font-weight="700" text-anchor="start">23:00-06:00</text>
</svg>
""",
    },
]


def issue_key(message: str) -> str:
    mapping = [
        ("connector arrow(s) sharing a text lane", "connector_text_lane"),
        ("shape-over-text occlusion", "shape_over_text"),
        ("text container overflow", "container_overflow"),
        ("text overlap/collision", "text_overlap"),
        ("visible eval/internal metadata", "metadata_leak"),
        ("shape text centering issue", "shape_text_centering"),
        ("spec_lock drift", "spec_lock_drift"),
        ("viewBox mismatch", "viewbox"),
        ("forbidden", "forbidden_svg"),
    ]
    for needle, key in mapping:
        if needle in message:
            return key
    return "other"


def write_fixtures(output_dir: Path) -> Path:
    fixture_dir = output_dir / "fixtures"
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    fixture_dir.mkdir(parents=True)
    for fixture in FIXTURES:
        (fixture_dir / f"{fixture['name']}.svg").write_text(fixture["svg"], encoding="utf-8")
    return fixture_dir


def run_fixture_eval(fixture_dir: Path) -> List[Dict]:
    cases = []
    for fixture in FIXTURES:
        svg_path = fixture_dir / f"{fixture['name']}.svg"
        result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")
        messages = result["errors"] + result["warnings"]
        missing = [needle for needle in fixture["expect"] if not any(needle in msg for msg in messages)]
        unexpected = []
        if not fixture["expect"]:
            unexpected = messages
        cases.append(
            {
                "name": fixture["name"],
                "path": str(svg_path),
                "expected": fixture["expect"],
                "passed": not missing and not unexpected and result["passed"],
                "missingExpected": missing,
                "unexpectedMessages": unexpected,
                "warnings": result["warnings"],
                "errors": result["errors"],
            }
        )
    return cases


def run_target_eval(target: Path, svg_dir_name: str) -> Dict:
    svg_dir = target / svg_dir_name
    checker = SVGQualityChecker()
    results = []
    for svg_path in sorted(svg_dir.glob("*.svg")):
        results.append(checker.check_file(str(svg_path), expected_format="ppt169"))

    issue_counts = Counter()
    for result in results:
        for message in result["errors"] + result["warnings"]:
            issue_counts[issue_key(message)] += 1

    return {
        "target": str(target),
        "svgDir": str(svg_dir),
        "totalFiles": len(results),
        "passedFiles": sum(1 for r in results if r["passed"] and not r["warnings"]),
        "warningFiles": sum(1 for r in results if r["passed"] and r["warnings"]),
        "errorFiles": sum(1 for r in results if not r["passed"]),
        "issueCounts": dict(sorted(issue_counts.items())),
        "files": [
            {
                "file": r["file"],
                "passed": r["passed"],
                "warnings": r["warnings"],
                "errors": r["errors"],
            }
            for r in results
        ],
    }


def run_design_eval(target: Path, svg_dir_name: str) -> Dict:
    return DesignQualityChecker(expected_format="ppt169").check_target(target, svg_dir_name=svg_dir_name)


def run_archetype_plan(target: Path, page_count: int) -> Dict:
    markdown_path = resolve_markdown_target(target)
    report = plan_archetypes(markdown_path.read_text(encoding="utf-8", errors="replace"), page_count=page_count)
    report["source"] = str(markdown_path)
    return report


def write_reports(output_dir: Path, report: Dict) -> None:
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# PPT Master Eval Report",
        "",
        f"- generatedAt: {report['generatedAt']}",
        f"- fixturePass: {report['fixtureSummary']['passed']}/{report['fixtureSummary']['total']}",
        "",
        "## Fixture Checks",
        "",
        "| Case | Expected | Result | Messages |",
        "|---|---|---|---|",
    ]
    for case in report["fixtures"]:
        expected = ", ".join(case["expected"]) if case["expected"] else "clean"
        status = "PASS" if case["passed"] else "FAIL"
        messages = "; ".join(case["errors"] + case["warnings"])
        lines.append(f"| {case['name']} | {expected} | {status} | {messages or '-'} |")

    if report.get("target"):
        target = report["target"]
        lines.extend(
            [
                "",
                "## Target Project",
                "",
                f"- target: `{target['target']}`",
                f"- svgDir: `{target['svgDir']}`",
                f"- files: {target['totalFiles']}",
                f"- clean/warn/error: {target['passedFiles']}/{target['warningFiles']}/{target['errorFiles']}",
                "",
                "### Issue Counts",
                "",
                "| Issue | Count |",
                "|---|---:|",
            ]
        )
        for key, count in target["issueCounts"].items():
            lines.append(f"| {key} | {count} |")

    if report.get("design"):
        design = report["design"]
        lines.extend(
            [
                "",
                "## Design Quality",
                "",
                f"- target: `{design['target']}`",
                f"- svgDir: `{design['svgDir']}`",
                f"- files: {design['totalFiles']}",
                f"- averageScore: {design['averageScore']}",
                f"- diversityScore: {design['deckDiversity']['score']}",
                f"- releaseCandidates: {design['releaseCandidates']}/{design['totalFiles']}",
                "",
                "### Archetypes",
                "",
                "| Archetype | Count |",
                "|---|---:|",
            ]
        )
        for archetype, count in design["deckDiversity"]["archetypeCounts"].items():
            lines.append(f"| {archetype} | {count} |")
        if design["deckDiversity"]["issues"]:
            lines.extend(["", "### Diversity Issues", ""])
            for issue in design["deckDiversity"]["issues"]:
                lines.append(f"- `{issue['code']}`: {issue['message']}")
        if design.get("deckGenerationGuidance"):
            lines.extend(["", "### Deck Generation Guidance", ""])
            for item in design["deckGenerationGuidance"]:
                lines.append(f"- `{item['code']}` ({item['priority']}): {item['action']}")
        lines.extend(
            [
                "",
                "### Page Scores",
                "",
                "| File | Archetype | Score | Readiness | Low Metrics | Key Issues | Regeneration Guidance |",
                "|---|---|---:|---|---|---|---|",
            ]
        )
        for page in design["pages"]:
            low_metrics = ", ".join(f"{k}:{v}" for k, v in page["metrics"].items() if v < 70) or "-"
            issues = ", ".join(issue["code"] for issue in page["issues"][:5]) or "-"
            guidance = ", ".join(item["code"] for item in page.get("generationGuidance", [])[:4]) or "-"
            lines.append(f"| {page['file']} | {page['archetype']} | {page['score']} | {page['readiness']} | {low_metrics} | {issues} | {guidance} |")

    if report.get("archetypePlan"):
        plan = report["archetypePlan"]
        lines.extend(
            [
                "",
                "## Source Archetype Plan",
                "",
                f"- source: `{plan['source']}`",
                f"- pages: {plan['pageCount']}",
                "",
                "| Page | Planned Archetype | Density | Source Heading |",
                "|---|---|---|---|",
            ]
        )
        for page in plan["pages"]:
            density = page.get("densityContract", {}).get("densityLevel", "-")
            lines.append(f"| {page['page']} | {page['visualArchetype']} | {density} | {page['sourceHeading']} |")
        lines.extend(
            [
                "",
                "### Planned Density Contracts",
                "",
                "| Page | Claims | Objects | Labels | Evidence | Relationships | Fill |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for page in plan["pages"]:
            contract = page.get("densityContract", {})
            lines.append(
                f"| {page['page']} | {contract.get('visibleClaimsMin', '-')} | {contract.get('visibleObjectsMin', '-')} | "
                f"{contract.get('visibleLabelsMin', '-')} | {contract.get('evidenceItemsMin', '-')} | "
                f"{contract.get('relationshipsMin', '-')} | {contract.get('contentAreaFillTarget', '-')} |"
            )

    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PPT Master visual quality eval fixtures.")
    parser.add_argument("--output-dir", default="ppt_master_eval_output", help="Directory for fixtures and reports.")
    parser.add_argument("--target", help="Optional generated project directory to summarize.")
    parser.add_argument("--svg-dir", default="svg_output", help="SVG directory under --target.")
    parser.add_argument("--design", action="store_true", help="Also run page-level design quality checks.")
    parser.add_argument("--plan-archetypes", action="store_true", help="Also plan visual archetypes from the target project's Markdown source.")
    parser.add_argument("--plan-pages", type=int, default=10, help="Maximum pages for --plan-archetypes.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    fixture_dir = write_fixtures(output_dir)
    fixture_cases = run_fixture_eval(fixture_dir)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "fixturesDir": str(fixture_dir),
        "fixtureSummary": {
            "total": len(fixture_cases),
            "passed": sum(1 for case in fixture_cases if case["passed"]),
            "failed": sum(1 for case in fixture_cases if not case["passed"]),
        },
        "fixtures": fixture_cases,
    }

    if args.target:
        target_path = Path(args.target).expanduser().resolve()
        report["target"] = run_target_eval(target_path, args.svg_dir)
        if args.design:
            report["design"] = run_design_eval(target_path, args.svg_dir)
        if args.plan_archetypes:
            report["archetypePlan"] = run_archetype_plan(target_path, args.plan_pages)

    write_reports(output_dir, report)

    print(f"[ppt-master-eval] fixtures: {report['fixtureSummary']['passed']}/{report['fixtureSummary']['total']} passed")
    if report.get("design"):
        print(f"[ppt-master-eval] design average: {report['design']['averageScore']}")
        print(f"[ppt-master-eval] diversity score: {report['design']['deckDiversity']['score']}")
    if report.get("archetypePlan"):
        print(f"[ppt-master-eval] planned archetypes: {', '.join(report['archetypePlan']['archetypeCounts'])}")
        dense_pages = sum(1 for page in report["archetypePlan"]["pages"] if page.get("densityContract", {}).get("densityLevel") == "dense")
        print(f"[ppt-master-eval] density contracts: {len(report['archetypePlan']['pages'])} pages ({dense_pages} dense)")
    print(f"[ppt-master-eval] report: {output_dir / 'report.md'}")
    print(f"[ppt-master-eval] json:   {output_dir / 'report.json'}")
    return 0 if report["fixtureSummary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
