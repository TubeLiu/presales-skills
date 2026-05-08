import json
import re
import sys
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALAuda_DIR = ROOT / "ppt-master/skills/make/templates/layouts/alauda"
ROUTES_PATH = ALAuda_DIR / "semantic_routes.json"
VISUAL_SYSTEM_PATH = ALAuda_DIR / "visual_system.json"
HUMAN_QUALITY_PATH = ALAuda_DIR / "human_quality_rubric.json"
ICON_DIR = ROOT / "ppt-master/skills/make/templates/icons/chunk"


def load_routes():
    return json.loads(ROUTES_PATH.read_text(encoding="utf-8"))


def load_visual_system():
    return json.loads(VISUAL_SYSTEM_PATH.read_text(encoding="utf-8"))


def load_human_quality():
    return json.loads(HUMAN_QUALITY_PATH.read_text(encoding="utf-8"))


def route_by_best_for(brief: str, routes: list[dict]) -> tuple[str, int]:
    """Tiny deterministic proxy for the Strategist's semantic route lookup.

    This is not a replacement for model judgment. It verifies that the route
    catalog contains enough bilingual trigger language for Chinese presales
    briefs to retrieve the intended Alauda variant.
    """
    brief_lower = brief.lower()
    best_intent = ""
    best_score = -1
    for route in routes:
        score = 0
        for keyword in route.get("bestFor", []):
            if keyword.lower() in brief_lower:
                score += len(keyword)
        if score > best_score:
            best_score = score
            best_intent = route["pageIntent"]
    return best_intent, best_score


def test_alauda_route_catalog_is_bilingual_and_resolves_variants():
    catalog = load_routes()
    assert catalog["template"] == "alauda"

    for route in catalog["routes"]:
        variant = ALAuda_DIR / route["variantFile"]
        assert variant.exists(), f"missing variant file: {variant.name}"
        assert route.get("visualGrammar"), route["pageIntent"]
        assert route.get("payloadBudget", {}).get("notesOverflow") is True
        assert any(any("\u4e00" <= ch <= "\u9fff" for ch in item) for item in route["bestFor"]), (
            f"{route['pageIntent']} lacks Chinese bestFor terms"
        )

    route_payloads = {route["pageIntent"]: route["payloadBudget"] for route in catalog["routes"]}
    assert "anchorThesis" in route_payloads["platform_panorama"]
    assert "dependencyDirection" in route_payloads["architecture_stack"]
    assert "decisionCue" in route_payloads["mapping_table"]
    assert "bridgeEmphasis" in route_payloads["migration_bridge"]
    assert "axisVisibility" in route_payloads["risk_matrix"]
    assert "stepOutput" in route_payloads["process_flow"]


def test_ocp_to_acp_mini_eval_routes_core_pages():
    catalog = load_routes()
    routes = catalog["routes"]

    cases = [
        {
            "name": "target-platform-panorama",
            "brief": "ACP 产品全景与能力地图：容器、DevOps、服务治理、虚拟化与 AI 能力收敛到统一治理平台底座。",
            "expected": "platform_panorama",
        },
        {
            "name": "architecture-layering",
            "brief": "OCP 到 ACP 的架构分层对齐：控制面、工作负载面、平台能力栈和基础设施适配。",
            "expected": "architecture_stack",
        },
        {
            "name": "migration-bridge",
            "brief": "迁移路径采用双轨并进和灰度迁移，从 OCP 现状到 ACP 目标态，中间建立迁移桥。",
            "expected": "migration_bridge",
        },
        {
            "name": "object-mapping-table",
            "brief": "术语对照和对象映射：Route、SCC、BuildConfig、ImageStream 转换到 ACP 对应对象。",
            "expected": "mapping_table",
        },
        {
            "name": "poc-process",
            "brief": "PoC 试点实施流程：资产扫描、目标环境、迁移验证、灰度切流四步完成低风险试点。",
            "expected": "process_flow",
        },
        {
            "name": "risk-classification",
            "brief": "迁移范围分类需要按复杂度影响做风险矩阵，识别高风险工作负载和回退优先级。",
            "expected": "risk_matrix",
        },
        {
            "name": "yaml-conversion-sample",
            "brief": "展示 Route 到 Ingress 的 YAML 转换、CLI 示例和 API 映射，便于开发团队改造清单。",
            "expected": "code_sample",
        },
    ]

    for case in cases:
        actual, score = route_by_best_for(case["brief"], routes)
        assert score > 0, case["name"]
        assert actual == case["expected"], f"{case['name']}: expected {case['expected']}, got {actual}"


def test_route_contract_is_documented_in_strategy_and_execution_refs():
    design_spec = (ROOT / "ppt-master/skills/make/templates/design_spec_reference.md").read_text(encoding="utf-8")
    spec_lock = (ROOT / "ppt-master/skills/make/templates/spec_lock_reference.md").read_text(encoding="utf-8")
    strategist = (ROOT / "ppt-master/skills/make/references/strategist.md").read_text(encoding="utf-8")
    executor = (ROOT / "ppt-master/skills/make/references/executor-base.md").read_text(encoding="utf-8")

    assert "**Semantic Route**" in design_spec
    assert "## semantic_routes" in spec_lock
    assert "templates/semantic_routes.json" in strategist
    assert "payload_budget" in executor


def test_alauda_visual_system_covers_routes_icons_and_density():
    routes = load_routes()["routes"]
    visual_system = load_visual_system()

    assert visual_system["template"] == "alauda"
    assert visual_system["componentLibrary"] == "component_library.md"
    assert visual_system["iconSystem"]["library"] == "chunk"

    route_defaults = visual_system["routeDefaults"]
    route_intents = {route["pageIntent"] for route in routes}
    assert route_intents <= set(route_defaults), "visual_system must cover every semantic route"
    approved_components = set(visual_system["componentPrimitives"])
    assert "layer_header_bar" in approved_components
    assert "code_terminal_block" in approved_components

    for profile_name, profile in visual_system["densityProfiles"].items():
        assert profile["relatedGapPx"] >= 12, profile_name
        assert profile["groupGapPx"] > profile["relatedGapPx"], profile_name
        assert profile["minTextBoxHeightPx"] >= 22, profile_name
        assert profile["maxNestedLevels"] <= 3, profile_name
        assert profile["notesOverflow"] is True, profile_name

    approved_icons = set(visual_system["iconSystem"]["inventory"])
    for icon_name in approved_icons:
        assert (ICON_DIR / f"{icon_name}.svg").exists(), f"missing chunk icon: {icon_name}"

    for intent, route_default in route_defaults.items():
        assert route_default["density"] in visual_system["densityProfiles"], intent
        assert route_default["components"], intent
        assert set(route_default["components"]) <= approved_components, intent
        assert set(route_default["icons"]) <= approved_icons, intent

    assert any("connector arrows" in item and "text rows" in item for item in visual_system["antiPatterns"])
    assert visual_system["connectorPolicy"]["minTextLaneGapPx"] >= 72
    assert visual_system["connectorPolicy"]["minContainerBorderGapPx"] >= 8
    assert "centered by default" in visual_system["shapeTextPolicy"]["defaultRule"]
    assert "light blue" in visual_system["shapeTextPolicy"]["coloredBlockScope"]
    assert "dominant-baseline=\"middle\"" in visual_system["shapeTextPolicy"]["requiredSvgAttrs"]
    assert visual_system["deliveryMode"]["customerCanvas"]["visibleInternalMetadata"] == "forbidden"
    assert "platform_panorama" in visual_system["routeQualityRules"]
    assert "architecture_stack" in visual_system["routeQualityRules"]
    assert "mapping_table" in visual_system["routeQualityRules"]
    assert "migration_bridge" in visual_system["routeQualityRules"]
    assert "risk_matrix" in visual_system["routeQualityRules"]
    assert "process_flow" in visual_system["routeQualityRules"]


def test_visual_system_contract_is_copied_and_documented():
    skill = (ROOT / "ppt-master/skills/make/SKILL.md").read_text(encoding="utf-8")
    design_spec = (ROOT / "ppt-master/skills/make/templates/design_spec_reference.md").read_text(encoding="utf-8")
    spec_lock = (ROOT / "ppt-master/skills/make/templates/spec_lock_reference.md").read_text(encoding="utf-8")
    strategist = (ROOT / "ppt-master/skills/make/references/strategist.md").read_text(encoding="utf-8")
    executor = (ROOT / "ppt-master/skills/make/references/executor-base.md").read_text(encoding="utf-8")
    alauda_spec = (ALAuda_DIR / "design_spec.md").read_text(encoding="utf-8")

    assert "visual_system.json <project_path>/templates/" in skill
    assert "human_quality_rubric.json <project_path>/templates/" in skill
    assert "design_quality_checker.py" in skill
    assert "ppt_master_eval.py --target <project_path> --design" in skill
    assert "density_profile" in design_spec
    assert "component_primitives" in design_spec
    assert "connector_policy" in design_spec
    assert "design_semantics" in design_spec
    assert "visual_archetype" in design_spec
    assert "route_quality_rules" in design_spec
    assert "## visual_system" in spec_lock
    assert "## design_diversity" in spec_lock
    assert "## design_semantics" in spec_lock
    assert "connector_policy" in spec_lock
    assert "customer_canvas" in spec_lock
    assert "## quality_samples" in spec_lock
    assert "templates/visual_system.json" in strategist
    assert "Connector routing is a page-level contract" in strategist
    assert "Customer-facing canvases must not display eval/internal metadata" in strategist
    assert "templates/human_quality_rubric.json" in strategist
    assert "spec_lock.md ## visual_system" in strategist
    assert "spec_lock.md ## quality_samples" in strategist
    assert "Density and collision discipline" in executor
    assert "connectorPolicy" in executor
    assert "minContainerBorderGapPx" in executor
    assert "shapeTextPolicy" in executor
    assert "data-text-align=\"left\"" in executor
    assert "routeQualityRules" in executor
    assert "component → slot → text" in executor
    assert "design_diversity" in executor
    assert "样张 P05" in executor
    assert "connector arrows sharing a text lane" in executor
    assert "Human-quality sample discipline" in executor
    assert "Visual System Contract" in alauda_spec
    assert "Human Quality Rubric" in alauda_spec


def test_alauda_human_quality_rubric_rotates_sample_intents():
    routes = load_routes()["routes"]
    route_intents = {route["pageIntent"] for route in routes}
    visual_system = load_visual_system()
    rubric = load_human_quality()

    assert rubric["template"] == "alauda"
    assert rubric["qualitySampleRotation"]["sampleSize"] == 3
    assert len(rubric["qualityDimensions"]) >= 6
    assert rubric["releaseBar"]["minimumScore"] >= 80
    assert any("same generated SVG" in stop or "same SVG" in stop for stop in rubric["qualitySampleRotation"]["policy"])

    archetype_intents = set(rubric["pageArchetypes"])
    assert route_intents <= archetype_intents

    for intent_set in rubric["qualitySampleRotation"]["preferredIntentSets"]:
        assert len(intent_set) == len(set(intent_set)), intent_set
        assert set(intent_set) <= route_intents, intent_set
        assert any(visual_system["routeDefaults"][intent]["density"] == "dense_technical" for intent in intent_set), (
            f"sample set lacks a dense technical page: {intent_set}"
        )


def test_svg_quality_checker_reports_icon_drift_from_spec_lock(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    (project / "spec_lock.md").write_text(
        """## canvas
- viewBox: 0 0 1280 720
## colors
- bg: #FFFFFF
- primary: #3BAEE3
- text: #334155
## typography
- font_family: "Microsoft YaHei", Arial, sans-serif
- body: 18
- title: 32
- annotation: 14
## icons
- library: chunk
- inventory: cube, server
## visual_system
- icon_inventory: cube, server, route
""",
        encoding="utf-8",
    )
    svg_path = svg_dir / "01_test.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="40" y="60" fill="#334155" font-family="&quot;Microsoft YaHei&quot;, Arial, sans-serif" font-size="32">Test</text>
  <use data-icon="tabler-filled/home" x="80" y="90" width="24" height="24" fill="#3BAEE3"/>
  <!-- icon: chunk/robot -->
</svg>
""",
        encoding="utf-8",
    )

    checker = SVGQualityChecker()
    result = checker.check_file(str(svg_path), expected_format="ppt169")

    assert any("icon(s)" in warning for warning in result["warnings"])
    assert "tabler-filled/home" in checker._drift_summary["icons"]
    assert "chunk/robot" in checker._drift_summary["icons"]


def test_svg_quality_checker_warns_on_obvious_text_overlap(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "overlap.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="120" y="120" fill="#334155" font-family="Arial, sans-serif" font-size="32">Kubernetes 组件</text>
  <text x="128" y="122" fill="#334155" font-family="Arial, sans-serif" font-size="32">DevOps 组件</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("text overlap/collision" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_on_text_container_overflow(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "container_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="90" height="34" fill="#F8FAFC" rx="4"/>
  <text x="108" y="123" fill="#334155" font-family="Arial, sans-serif" font-size="16">DeploymentConfig</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("text container overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_uses_finalized_path_container_for_header_text(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "finalized_header_path.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <path fill="#3BAEE3" d="M72,132 H876 A8,8 0 0 1 884,140 V166 A8,8 0 0 1 876,174 H72 A8,8 0 0 1 64,166 V140 A8,8 0 0 1 72,132 Z"/>
  <rect x="64" y="154" width="820" height="20" fill="#3BAEE3"/>
  <text x="88" y="160" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="15">OCP 对象</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("text container overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_on_visible_internal_metadata(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "metadata_leak.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="60" y="706" fill="#94A3B8" font-family="Arial, sans-serif" font-size="12">样张 P05 · mapping_table · dense_technical</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("visible eval/internal metadata" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_when_later_shape_covers_text(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "shape_occlusion.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="410" y="282" width="284" height="38" fill="#FFFFFF" rx="5" stroke="#E2E8F0"/>
  <text x="430" y="307" fill="#475569" font-family="Arial, sans-serif" font-size="15">资产扫描与分级</text>
  <polygon points="400,305 444,280 444,294 520,294 520,316 444,316 444,330" fill="#3BAEE3"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("shape-over-text occlusion" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_when_arrow_tip_intrudes_text_safety_zone(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "arrow_tip_intrusion.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="490" y="282" width="284" height="38" fill="#FFFFFF" rx="5" stroke="#E2E8F0"/>
  <text x="510" y="307" fill="#475569" font-family="Arial, sans-serif" font-size="15">资产扫描与分级</text>
  <polygon points="516,320 478,296 478,309 432,309 432,331 478,331 478,344" fill="#3BAEE3"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("shape-over-text occlusion" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_when_connector_shares_text_lane_without_overlap(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "connector_lane.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="900" y="250" width="240" height="120" fill="#F0FDF4" rx="6"/>
  <text x="940" y="305" fill="#334155" font-family="Arial, sans-serif" font-size="30">目标 ACP</text>
  <polygon points="884,300 840,274 840,290 806,290 806,310 840,310 840,326" fill="#3BAEE3"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("shape-over-text occlusion" in warning for warning in result["warnings"])
    assert any("connector arrow(s) sharing a text lane" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_when_connector_intrudes_container_border(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "connector_container_intrusion.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="70" y="152" width="275" height="316" fill="#FEF2F2" stroke="#FECACA" rx="8"/>
  <rect x="390" y="132" width="500" height="356" fill="#EFF6FF" stroke="#BFDBFE" rx="10"/>
  <polygon points="376,302 352,286 352,296 332,296 332,308 352,308 352,318" fill="#3BAEE3"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("connector arrow(s) intruding into card/container border safe zone" in warning for warning in result["warnings"])


def test_svg_quality_checker_allows_connector_in_clean_gutter(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "connector_clean_gutter.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="70" y="152" width="275" height="316" fill="#FEF2F2" stroke="#FECACA" rx="8"/>
  <rect x="430" y="132" width="500" height="356" fill="#EFF6FF" stroke="#BFDBFE" rx="10"/>
  <polygon points="396,302 376,290 376,298 356,298 356,306 376,306 376,314" fill="#3BAEE3"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("connector arrow(s) intruding into card/container border safe zone" in warning for warning in result["warnings"])


def test_svg_quality_checker_warns_on_shape_text_not_geometrically_centered(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "shape_text_not_centered.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <circle cx="120" cy="120" r="24" fill="#3BAEE3"/>
  <text x="120" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="18" text-anchor="middle">1</text>
  <rect x="220" y="96" width="260" height="48" fill="#3BAEE3" rx="6"/>
  <text x="252" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17">迁移桥：标准化转换通道</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("shape text centering issue" in warning for warning in result["warnings"])


def test_svg_quality_checker_allows_geometrically_centered_shape_text(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "shape_text_centered.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <circle cx="120" cy="120" r="24" fill="#3BAEE3"/>
  <text x="120" y="120" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="18" text-anchor="middle" dominant-baseline="middle">1</text>
  <rect x="220" y="96" width="260" height="48" fill="#3BAEE3" rx="6"/>
  <text x="350" y="120" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" text-anchor="middle" dominant-baseline="middle">迁移桥：标准化转换通道</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_svg_quality_checker_ignores_page_chrome_accent_for_shape_text_centering(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "page_chrome_accent.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <circle cx="1210" cy="560" r="260" fill="#EEF8FC" data-role="geometric-accent"/>
  <text x="1188" y="686" fill="#8AA0B8" font-family="Arial, sans-serif" font-size="12" text-anchor="end" data-role="page-number">P01</text>
  <rect x="220" y="220" width="260" height="48" fill="#3BAEE3" rx="6"/>
  <text x="350" y="244" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" text-anchor="middle" dominant-baseline="middle">主体标签</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_child_shape_overflowing_semantic_parent(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "child_shape_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="160" y="220" width="240" height="120" fill="#FFFFFF" stroke="#DCE6F2" rx="6" data-role="content-card"/>
  <rect x="190" y="310" width="180" height="38" fill="#D8EFF9" rx="6" data-role="label" data-slot="label"/>
  <text x="280" y="329" font-family="Arial, sans-serif" font-size="16" fill="#125B7D" text-anchor="middle" dominant-baseline="middle">越界标签</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_large_text_overflowing_semantic_parent(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "large_text_parent_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="470" y="160" width="300" height="240" fill="#EFF6FF" stroke="#BFDBFE" rx="8" data-role="bridge"/>
  <text x="510" y="260" font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#334155">5% → 20% → 50% → 100%</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_allows_header_flush_inside_semantic_parent(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "header_flush_parent.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="470" y="160" width="300" height="240" fill="#EFF6FF" stroke="#BFDBFE" rx="8" data-role="bridge"/>
  <rect x="470" y="160" width="300" height="44" fill="#3BAEE3" rx="8" data-role="label" data-slot="header"/>
  <text x="620" y="182" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">迁移桥</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_text_overflowing_intermediate_slot(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "intermediate_slot_text_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="124" y="226" width="148" height="276" rx="6" fill="#EAF5FF" stroke="#DDE6F1" data-role="content-card"/>
  <rect x="142" y="312" width="112" height="28" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="label" data-slot="label"/>
  <text x="198" y="326" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#2F3E52" text-anchor="middle" dominant-baseline="middle">Prometheus / Jaeger / Loki</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_borderline_bold_text_overflowing_bridge(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "bold_bridge_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="478" y="146" width="326" height="497" fill="#EAF5FF" stroke="#B8D9FB" data-role="bridge"/>
  <text x="520" y="230" font-family="Arial, sans-serif" font-size="23.59" font-weight="bold" fill="#2F3E52" text-anchor="start">5% → 20% → 50% → 100%</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_semantic_sibling_overlap(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "semantic_sibling_overlap.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="88" y="152" width="1104" height="464" rx="6" fill="#EAF5FF" stroke="#B8D9FB" data-role="content-card"/>
  <rect x="122" y="254" width="226" height="144" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="content-card"/>
  <rect x="148" y="394" width="984" height="38" rx="6" fill="#F4F7FA" stroke="#DDE6F1" data-role="label" data-slot="label"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic component overlap/spacing" in warning for warning in result["warnings"])


def test_svg_quality_checker_allows_nested_semantic_label_without_sibling_overlap(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "nested_semantic_label.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="122" y="254" width="226" height="144" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="content-card"/>
  <rect x="144" y="318" width="174" height="20" rx="6" fill="#D8F0FA" data-role="label" data-slot="label"/>
  <rect x="144" y="344" width="174" height="20" rx="6" fill="#D8F0FA" data-role="label" data-slot="label"/>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("semantic component overlap/spacing" in warning for warning in result["warnings"])


def test_svg_quality_checker_keeps_semantic_path_slots_after_finalize(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "finalized_path_slot_text_overflow.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <path fill="#EAF5FF" stroke="#DDE6F1" data-role="content-card" d="M130,226 H266 A6,6 0 0 1 272,232 V496 A6,6 0 0 1 266,502 H130 A6,6 0 0 1 124,496 V232 A6,6 0 0 1 130,226 Z"/>
  <path fill="#FFFFFF" stroke="#DDE6F1" data-role="label" data-slot="label" d="M148,312 H248 A6,6 0 0 1 254,318 V334 A6,6 0 0 1 248,340 H148 A6,6 0 0 1 142,334 V318 A6,6 0 0 1 148,312 Z"/>
  <text x="198" y="326" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#2F3E52" text-anchor="middle" dominant-baseline="middle">Nginx → ASM Gateway</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("semantic parent overflow" in warning for warning in result["warnings"])


def test_svg_quality_checker_uses_semantic_path_component_for_centering(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    bad_svg = tmp_path / "path_header_bad.svg"
    bad_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <path fill="#3BAEE3" d="M400,132 H880 A10,10 0 0 1 890,142 V176 A10,10 0 0 1 880,186 H400 A10,10 0 0 1 390,176 V142 A10,10 0 0 1 400,132 Z"/>
  <rect x="390" y="160" width="500" height="26" fill="#3BAEE3"/>
  <text x="640" y="173" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" font-weight="700" text-anchor="middle" dominant-baseline="middle">迁移桥：标准化转换通道</text>
</svg>
""",
        encoding="utf-8",
    )

    bad_result = SVGQualityChecker().check_file(str(bad_svg), expected_format="ppt169")
    assert any("shape text centering issue" in warning for warning in bad_result["warnings"])

    good_svg = tmp_path / "path_header_good.svg"
    good_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <path fill="#3BAEE3" d="M400,132 H880 A10,10 0 0 1 890,142 V176 A10,10 0 0 1 880,186 H400 A10,10 0 0 1 390,176 V142 A10,10 0 0 1 400,132 Z"/>
  <rect x="390" y="160" width="500" height="26" fill="#3BAEE3"/>
  <text x="640" y="159" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" font-weight="700" text-anchor="middle" dominant-baseline="middle">迁移桥：标准化转换通道</text>
</svg>
""",
        encoding="utf-8",
    )

    good_result = SVGQualityChecker().check_file(str(good_svg), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in good_result["warnings"])


def test_layout_semantics_preserves_explicit_header_slots(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "header_slots.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="520" height="44" fill="#3BAEE3" rx="6"/>
  <rect x="100" y="100" width="160" height="44" fill="#3BAEE3" fill-opacity="0" data-role="header-cell"/>
  <rect x="260" y="100" width="180" height="44" fill="#3BAEE3" fill-opacity="0" data-role="header-cell"/>
  <rect x="440" y="100" width="180" height="44" fill="#3BAEE3" fill-opacity="0" data-role="header-cell"/>
  <text x="180" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">OCP 对象</text>
  <text x="350" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">ACP 对象</text>
  <text x="530" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">风险</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_svg_quality_checker_requires_centered_text_in_multi_label_strips(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    bad_svg = tmp_path / "multi_label_strip_bad.svg"
    bad_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="520" height="44" fill="#3BAEE3" rx="6"/>
  <text x="128" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">OCP 对象</text>
  <text x="278" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">ACP 对象</text>
  <text x="458" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">风险</text>
</svg>
""",
        encoding="utf-8",
    )
    bad_result = SVGQualityChecker().check_file(str(bad_svg), expected_format="ppt169")
    assert any("shape text centering issue" in warning for warning in bad_result["warnings"])

    good_svg = tmp_path / "multi_label_strip_good.svg"
    good_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="100" y="100" width="520" height="44" fill="#3BAEE3" rx="6"/>
  <rect x="100" y="100" width="160" height="44" fill="#3BAEE3"/>
  <rect x="260" y="100" width="180" height="44" fill="#3BAEE3"/>
  <rect x="440" y="100" width="180" height="44" fill="#3BAEE3"/>
  <text x="180" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">OCP 对象</text>
  <text x="350" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">ACP 对象</text>
  <text x="530" y="122" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">风险</text>
</svg>
""",
        encoding="utf-8",
    )
    good_result = SVGQualityChecker().check_file(str(good_svg), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in good_result["warnings"])


def test_svg_quality_checker_treats_pale_colored_blocks_as_centered_by_default(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    bad_svg = tmp_path / "pale_label_bad.svg"
    bad_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="128" y="324" width="188" height="26" fill="#D8EFF9" rx="4"/>
  <text x="142" y="343" fill="#125B7D" font-family="Arial, sans-serif" font-size="14">应用发布</text>
  <rect x="128" y="366" width="188" height="26" fill="#F0FDF4" rx="4"/>
  <text x="142" y="385" fill="#25B273" font-family="Arial, sans-serif" font-size="14">确认范围</text>
</svg>
""",
        encoding="utf-8",
    )
    bad_result = SVGQualityChecker().check_file(str(bad_svg), expected_format="ppt169")
    assert any("shape text centering issue" in warning for warning in bad_result["warnings"])

    good_svg = tmp_path / "pale_label_good.svg"
    good_svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="128" y="324" width="188" height="26" fill="#D8EFF9" rx="4"/>
  <text x="222" y="337" fill="#125B7D" font-family="Arial, sans-serif" font-size="14" text-anchor="middle" dominant-baseline="middle">应用发布</text>
  <rect x="128" y="366" width="188" height="26" fill="#F0FDF4" rx="4"/>
  <text x="222" y="379" fill="#25B273" font-family="Arial, sans-serif" font-size="14" text-anchor="middle" dominant-baseline="middle">确认范围</text>
</svg>
""",
        encoding="utf-8",
    )
    good_result = SVGQualityChecker().check_file(str(good_svg), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in good_result["warnings"])


def test_svg_quality_checker_allows_explicit_left_aligned_colored_content_exception(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "colored_callout_left_exception.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="220" y="520" width="840" height="54" fill="#EFF6FF" stroke="#BFDBFE" rx="6" data-role="callout-content"/>
  <text x="280" y="548" fill="#334155" font-family="Arial, sans-serif" font-size="18" font-weight="700">只有当对象清单、转换脚本和验证报告同时闭环，才进入生产迁移。</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_centers_colored_block_text(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_test.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="128" y="324" width="188" height="26" fill="#D8EFF9" rx="4"/>
  <text x="142" y="343" fill="#125B7D" font-family="Arial, sans-serif" font-size="14">应用发布</text>
  <rect x="100" y="100" width="520" height="44" fill="#3BAEE3" rx="6"/>
  <text x="128" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">OCP 对象</text>
  <text x="278" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">ACP 对象</text>
  <text x="458" y="128" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16">风险</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_test.svg").read_text(encoding="utf-8")
    assert 'text-anchor="middle"' in final_svg
    assert 'dominant-baseline="middle"' in final_svg
    assert 'data-role="label-slot"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_test.svg"), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_uses_full_header_not_helper_rect(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_header.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="390" y="132" width="500" height="54" fill="#3BAEE3" rx="10"/>
  <rect x="390" y="160" width="500" height="26" fill="#3BAEE3"/>
  <text x="640" y="173" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="17" font-weight="700" text-anchor="middle" dominant-baseline="middle">迁移桥：标准化转换通道</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_header.svg").read_text(encoding="utf-8")
    assert 'x="640"' in final_svg
    assert 'y="159"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_header.svg"), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_centers_colored_card_stack(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_card.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="150" y="218" width="250" height="130" fill="#F0FDF4" stroke="#BBF7D0" stroke-width="1" rx="8"/>
  <rect x="168" y="238" width="98" height="24" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1" rx="4"/>
  <text x="178" y="255" font-family="Arial, sans-serif" font-size="12" fill="#475569" font-weight="700">低复杂 / 高影响</text>
  <text x="174" y="290" font-family="Arial, sans-serif" font-size="24" fill="#334155" font-weight="700">优先试点</text>
  <text x="174" y="322" font-family="Arial, sans-serif" font-size="14" fill="#475569">无状态核心服务，验证收益</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_card.svg").read_text(encoding="utf-8")
    assert '<rect x="226"' in final_svg
    assert 'x="275"' in final_svg
    assert 'text-anchor="middle"' in final_svg
    assert 'dominant-baseline="middle"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_card.svg"), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_fits_text_inside_semantic_label_slot(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_slot_fit.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="124" y="226" width="148" height="276" rx="6" fill="#EAF5FF" stroke="#DDE6F1" data-role="content-card"/>
  <rect x="142" y="312" width="112" height="28" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="label" data-slot="label"/>
  <text x="198" y="326" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#2F3E52" text-anchor="middle" dominant-baseline="middle">Prometheus / Jaeger / Loki</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_slot_fit.svg").read_text(encoding="utf-8")
    assert 'width="136"' in final_svg
    assert 'font-size="8.' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_slot_fit.svg"), expected_format="ppt169")
    assert not any("semantic parent overflow" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_expands_component_to_direct_content(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_component_fit.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="88" y="152" width="1104" height="458" rx="6" fill="#EAF5FF" stroke="#B8D9FB" data-role="content-card"/>
  <rect x="128" y="460" width="300" height="76" fill="#4EA9DC" opacity="0.18" data-role="content-card" data-text-align="left"/>
  <text x="146" y="488" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#2F3E52">容器平台</text>
  <text x="146" y="516" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#5D6B7C">已容器化无状态服务</text>
  <text x="146" y="540" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#1E6684">灰度治理主战场</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_component_fit.svg").read_text(encoding="utf-8")
    assert 'height="91.25"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_component_fit.svg"), expected_format="ppt169")
    assert not any("semantic parent overflow" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_fits_direct_component_text_width(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_bridge_text_fit.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="478" y="146" width="326" height="400" fill="#EAF5FF" stroke="#B8D9FB" data-role="bridge"/>
  <text x="520" y="230" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#2F3E52" text-anchor="start">5% → 20% → 50% → 100%</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_bridge_text_fit.svg").read_text(encoding="utf-8")
    assert 'x="641" y="220.25"' in final_svg
    assert 'font-size="24.' in final_svg
    assert 'text-anchor="middle"' in final_svg
    assert 'dominant-baseline="middle"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_bridge_text_fit.svg"), expected_format="ppt169")
    assert not any("text container overflow" in warning for warning in result["warnings"])
    assert not any("semantic parent overflow" in warning for warning in result["warnings"])
    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_svg_quality_checker_flags_uncentered_direct_component_emphasis(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    svg_path = tmp_path / "uncentered_emphasis.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="92" y="166" width="286" height="370" fill="#FFF1F0" stroke="#F4C9C5" data-role="content-card" data-text-align="left"/>
  <rect x="92" y="166" width="286" height="44" fill="#F0524A" data-role="label" data-slot="label"/>
  <text x="235" y="188" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">当前发布模式</text>
  <text x="122" y="244" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#F0524A" text-anchor="start">23:00-06:00</text>
</svg>
""",
        encoding="utf-8",
    )

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    assert any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_centers_direct_component_emphasis(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_emphasis_center.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="92" y="166" width="286" height="370" fill="#FFF1F0" stroke="#F4C9C5" data-role="content-card" data-text-align="left"/>
  <rect x="92" y="166" width="286" height="44" fill="#F0524A" data-role="label" data-slot="label"/>
  <text x="235" y="188" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">当前发布模式</text>
  <text x="122" y="244" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#F0524A" text-anchor="start">23:00-06:00</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_emphasis_center.svg").read_text(encoding="utf-8")
    assert 'x="235" y="232.75"' in final_svg
    assert 'text-anchor="middle"' in final_svg
    assert 'dominant-baseline="middle"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_emphasis_center.svg"), expected_format="ppt169")
    assert not any("shape text centering issue" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_respects_left_aligned_component_emphasis_exception(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_left_exception.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="128" y="460" width="300" height="76" fill="#4EA9DC" data-role="content-card" data-text-align="left"/>
  <text x="146" y="488" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#2F3E52" text-anchor="start">容器平台</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_left_exception.svg").read_text(encoding="utf-8")
    assert 'x="146" y="488"' in final_svg
    assert 'text-anchor="start"' in final_svg


def test_finalize_normalize_layout_preserves_sibling_gap_after_component_growth(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_sibling_gap.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="88" y="152" width="1104" height="464" rx="6" fill="#EAF5FF" stroke="#B8D9FB" data-role="content-card"/>
  <rect x="122" y="254" width="226" height="112" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="content-card"/>
  <rect x="144" y="318" width="174" height="20" rx="6" fill="#D8F0FA" data-role="label" data-slot="label"/>
  <rect x="144" y="344" width="174" height="20" rx="6" fill="#D8F0FA" data-role="label" data-slot="label"/>
  <rect x="144" y="370" width="174" height="20" rx="6" fill="#D8F0FA" data-role="label" data-slot="label"/>
  <rect x="148" y="394" width="984" height="38" rx="6" fill="#F4F7FA" stroke="#DDE6F1" data-role="label" data-slot="label"/>
  <text x="640" y="413" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#2F3E52" text-anchor="middle" dominant-baseline="middle">运行形态：单体 + Spring Cloud 微服务 + Python/PHP 历史模块 + RocketMQ 容器化</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_sibling_gap.svg").read_text(encoding="utf-8")
    assert 'x="148" y="410" width="984" height="38"' in final_svg
    assert 'x="640" y="429"' in final_svg

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_sibling_gap.svg"), expected_format="ppt169")
    assert not any("semantic component overlap/spacing" in warning for warning in result["warnings"])


def test_finalize_normalize_layout_does_not_expand_layer_from_sibling_text(tmp_path):
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_layer_stack.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="92" y="150" width="1096" height="430" rx="6" fill="#EAF5FF" stroke="#B8D9FB" data-role="content-card"/>
  <rect x="142" y="184" width="996" height="58" rx="6" fill="#4EA9DC" data-role="content-card" data-slot="layer"/>
  <text x="168" y="220" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#2F3E52">南北向入口层</text>
  <rect x="142" y="268" width="996" height="58" rx="6" fill="#40B879" data-role="content-card" data-slot="layer"/>
  <text x="168" y="304" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#2F3E52">服务网格层</text>
  <rect x="142" y="352" width="996" height="58" rx="6" fill="#F5C43A" data-role="content-card" data-slot="layer"/>
  <text x="168" y="388" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#2F3E52">业务应用层</text>
  <rect x="142" y="436" width="996" height="58" rx="6" fill="#4EA9DC" data-role="content-card" data-slot="layer"/>
  <text x="168" y="472" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#2F3E52">观测平台层</text>
  <rect x="168" y="524" width="244" height="42" rx="6" fill="#FFFFFF" stroke="#DDE6F1" data-role="content-card"/>
  <text x="186" y="551" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#2F3E52">控制面声明</text>
</svg>
""",
        encoding="utf-8",
    )

    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    final_svg = (project / "svg_final/01_layer_stack.svg").read_text(encoding="utf-8")
    assert final_svg.count('height="58"') == 4

    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)
    result = SVGQualityChecker().check_file(str(project / "svg_final/01_layer_stack.svg"), expected_format="ppt169")
    assert not any("semantic component overlap/spacing" in warning for warning in result["warnings"])


def test_svg_to_pptx_maps_middle_baseline_to_vertical_center_anchor():
    """Vertical centering for `dominant-baseline="middle"`.

    Two equivalent implementations are accepted:
      A. PowerPoint text-frame anchor: `anchor="ctr"` + `anchorCtr="1"`
      B. Geometric offset: `anchor="t"` + the xfrm `<a:off y=…/>` is shifted
         upward so the text's visual midline lands at the requested y.

    Upstream `hugohe3/ppt-master` v2.6.0 uses approach B (more faithful to
    SVG's coordinate semantics). Either approach delivers vertically centered
    text in PowerPoint. The horizontal centering paragraph property is the
    same across both: `<a:pPr algn="ctr"/>`.
    """
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from xml.etree import ElementTree as ET
        from svg_to_pptx.drawingml_context import ConvertContext
        from svg_to_pptx.drawingml_elements import convert_text
    finally:
        sys.path.pop(0)

    elem = ET.fromstring(
        '<text x="120" y="80" font-size="18" fill="#334155" '
        'font-family="Arial, sans-serif" text-anchor="middle" '
        'dominant-baseline="middle">居中文本</text>'
    )

    result = convert_text(elem, ConvertContext())

    assert result is not None
    # Horizontal centering is unchanged regardless of vertical strategy.
    assert '<a:pPr algn="ctr"/>' in result.xml
    # Accept either A (anchor=ctr) or B (geometric offset via xfrm y shift).
    has_text_anchor_ctr = 'anchor="ctr"' in result.xml and 'anchorCtr="1"' in result.xml
    has_geometric_offset = 'anchor="t"' in result.xml and '<a:off ' in result.xml
    assert has_text_anchor_ctr or has_geometric_offset, (
        "Expected either anchor=ctr+anchorCtr=1 (legacy) or "
        "anchor=t with xfrm offset (upstream). Got:\n" + result.xml
    )


def test_ppt_master_eval_runs_fixture_suite(tmp_path):
    script = ROOT / "ppt-master/skills/make/scripts/ppt_master_eval.py"
    output_dir = tmp_path / "eval"

    completed = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "fixtures: 10/10 passed" in completed.stdout
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["fixtureSummary"] == {"total": 10, "passed": 10, "failed": 0}
    assert any(case["name"] == "connector_text_lane" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "visible_internal_metadata" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "shape_text_centering" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "multi_label_strip_centering" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "pale_colored_block_centering" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "component_emphasis_centering" and case["passed"] for case in report["fixtures"])
    assert (output_dir / "report.md").exists()


def test_design_quality_checker_rewards_semantic_human_like_page(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    svg = tmp_path / "semantic_page.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="72" y="78" font-family="Arial, sans-serif" font-size="40" font-weight="700" fill="#334155">白天灰度发布能力建设路径</text>
  <text x="72" y="118" font-family="Arial, sans-serif" font-size="20" fill="#475569">从凌晨窗口切换到可观测、可回滚的分钟级发布</text>
  <rect x="90" y="174" width="1100" height="360" fill="#EEF6FF" stroke="#BFDBFE" rx="10" data-role="content-card" data-text-align="left"/>
  <rect x="126" y="218" width="226" height="84" fill="#3BAEE3" rx="6" data-role="label"/>
  <text x="239" y="260" font-family="Arial, sans-serif" font-size="22" fill="#FFFFFF" font-weight="700" text-anchor="middle" dominant-baseline="middle">入口接管</text>
  <rect x="392" y="218" width="226" height="84" fill="#3BAEE3" rx="6" data-role="label"/>
  <text x="505" y="260" font-family="Arial, sans-serif" font-size="22" fill="#FFFFFF" font-weight="700" text-anchor="middle" dominant-baseline="middle">灰度路由</text>
  <rect x="658" y="218" width="226" height="84" fill="#25B273" rx="6" data-role="label"/>
  <text x="771" y="260" font-family="Arial, sans-serif" font-size="22" fill="#FFFFFF" font-weight="700" text-anchor="middle" dominant-baseline="middle">指标门禁</text>
  <rect x="924" y="218" width="226" height="84" fill="#25B273" rx="6" data-role="label"/>
  <text x="1037" y="260" font-family="Arial, sans-serif" font-size="22" fill="#FFFFFF" font-weight="700" text-anchor="middle" dominant-baseline="middle">快速回滚</text>
  <rect x="142" y="386" width="980" height="74" fill="#FFFFFF" stroke="#DCE6F2" rx="8" data-role="callout-content"/>
  <text x="172" y="430" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#125B7D" data-text-align="left">交付判断</text>
  <text x="320" y="430" font-family="Arial, sans-serif" font-size="20" fill="#334155" data-text-align="left">只有流量、链路、指标和回滚闭环同时成立，才进入生产迁移。</text>
</svg>
""",
        encoding="utf-8",
    )

    result = DesignQualityChecker().check_file(svg)

    assert result["score"] >= 80
    assert result["metrics"]["visualHierarchy"] >= 80
    assert result["metrics"]["alignmentDiscipline"] >= 80
    assert not any(issue["code"] == "flat_peer_grid" for issue in result["issues"])


def test_design_quality_checker_negative_space_excludes_page_chrome(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    svg = tmp_path / "page_chrome.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <circle cx="1200" cy="560" r="240" fill="#EEF8FC" data-role="geometric-accent"/>
  <rect x="44" y="44" width="20" height="46" fill="#3BAEE3" data-role="accent-bar"/>
  <text x="76" y="78" font-family="Arial, sans-serif" font-size="36" font-weight="700" fill="#334155">灰度发布能力建设</text>
  <text x="76" y="116" font-family="Arial, sans-serif" font-size="18" fill="#64748B">页眉页脚不应污染主体内容的留白判断</text>
  <rect x="140" y="196" width="450" height="220" fill="#EEF6FF" stroke="#BFDBFE" data-role="content-card" data-text-align="left"/>
  <rect x="170" y="236" width="180" height="48" fill="#3BAEE3" data-role="label"/>
  <text x="260" y="260" font-family="Arial, sans-serif" font-size="20" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">主体内容</text>
  <text x="170" y="332" font-family="Arial, sans-serif" font-size="18" fill="#334155" data-text-align="left">只用这块卡片评估页面主体填充。</text>
  <line x1="80" y1="662" x2="1200" y2="662" stroke="#DDE6F1"/>
  <text x="80" y="686" font-family="Arial, sans-serif" font-size="12" fill="#8AA0B8" data-role="footer">Alauda</text>
  <text x="1188" y="686" font-family="Arial, sans-serif" font-size="12" fill="#8AA0B8" text-anchor="end" data-role="page-number">P01</text>
</svg>
""",
        encoding="utf-8",
    )

    result = DesignQualityChecker().check_file(svg)

    assert result["metrics"]["negativeSpace"] >= 80
    assert result["model"]["contentFillRatio"] < 0.40


def test_design_quality_checker_flags_flat_unsemantic_grid(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    cards = []
    for row, y in enumerate((150, 290)):
        for col, x in enumerate((80, 330, 580, 830)):
            idx = row * 4 + col + 1
            cards.append(f'<rect x="{x}" y="{y}" width="200" height="92" fill="#EEF6FF" stroke="#DCE6F2" rx="6"/>')
            cards.append(f'<text x="{x + 18}" y="{y + 52}" font-family="Arial, sans-serif" font-size="18" fill="#334155">模块 {idx}</text>')
    svg = tmp_path / "flat_grid.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">'
        '<rect width="1280" height="720" fill="#FFFFFF"/>'
        + "".join(cards)
        + "</svg>",
        encoding="utf-8",
    )

    result = DesignQualityChecker().check_file(svg)

    assert result["score"] < 78
    assert result["metrics"]["visualFocus"] < 70
    assert any(issue["code"] in {"flat_peer_grid", "missing_main_message", "low_visual_hierarchy"} for issue in result["issues"])
    assert any(issue["code"] == "low_visual_focus" for issue in result["issues"])
    guidance_codes = {item["code"] for item in result["generationGuidance"]}
    assert "regenerate_with_visual_focus" in guidance_codes
    assert "strengthen_component_slot_semantics" in guidance_codes


def test_design_quality_checker_does_not_flag_structured_process_as_flat_grid(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    steps = []
    for idx, x in enumerate((100, 380, 660, 940), start=1):
        steps.append(f'<rect x="{x}" y="210" width="220" height="210" fill="#FFFFFF" stroke="#DCE6F2" rx="6" data-role="process-step" data-intent="process"/>')
        steps.append(f'<circle cx="{x + 36}" cy="250" r="24" fill="#3BAEE3" data-role="label"/>')
        steps.append(f'<text x="{x + 36}" y="250" font-family="Arial, sans-serif" font-size="16" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">{idx}</text>')
        steps.append(f'<text x="{x + 74}" y="258" font-family="Arial, sans-serif" font-size="20" fill="#334155" font-weight="700">阶段 {idx}</text>')
        steps.append(f'<text x="{x + 24}" y="326" font-family="Arial, sans-serif" font-size="17" fill="#475569">交付物 / 验收门禁</text>')
    svg = tmp_path / "structured_process.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">'
        '<rect width="1280" height="720" fill="#FFFFFF"/>'
        '<text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">四阶段灰度验证流程</text>'
        + "".join(steps)
        + "</svg>",
        encoding="utf-8",
    )

    result = DesignQualityChecker().check_file(svg)

    assert result["archetype"] == "process_flow"
    assert result["metrics"]["visualFocus"] >= 70
    assert not any(issue["code"] == "flat_peer_grid" for issue in result["issues"])
    assert not any(issue["code"] == "low_visual_focus" for issue in result["issues"])
    assert not any(item["code"] == "regenerate_with_visual_focus" for item in result["generationGuidance"])


def test_design_quality_checker_flags_repetitive_micro_label_stacks(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    cards = []
    for col, x in enumerate((110, 370, 630, 890)):
        cards.append(f'<rect x="{x}" y="210" width="210" height="150" fill="#FFFFFF" stroke="#DCE6F2" rx="6" data-role="content-card"/>')
        cards.append(f'<text x="{x + 24}" y="248" font-family="Arial, sans-serif" font-size="20" fill="#334155" font-weight="700">能力组 {col + 1}</text>')
        for row, label in enumerate(("标签一", "标签二", "标签三")):
            y = 278 + row * 28
            cards.append(f'<rect x="{x + 24}" y="{y}" width="160" height="20" fill="#D8EFF9" rx="4" data-role="label" data-slot="label"/>')
            cards.append(f'<text x="{x + 104}" y="{y + 10}" font-family="Arial, sans-serif" font-size="12" fill="#125B7D" text-anchor="middle" dominant-baseline="middle">{label}</text>')
    svg = tmp_path / "micro_stacks.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">'
        '<rect width="1280" height="720" fill="#FFFFFF"/>'
        '<text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">微标签堆叠反模式</text>'
        + "".join(cards)
        + "</svg>",
        encoding="utf-8",
    )

    result = DesignQualityChecker().check_file(svg)

    assert result["model"]["repetitiveLabelStacks"] == 4
    assert result["model"]["stackedLabelCount"] == 12
    assert any(issue["code"] == "repetitive_micro_label_stacks" for issue in result["issues"])
    assert any(item["code"] == "replace_repetitive_micro_label_stacks" for item in result["generationGuidance"])


def test_ppt_master_eval_can_include_design_quality_summary(tmp_path):
    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    (svg_dir / "01_page.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">灰度发布闭环</text>
  <rect x="120" y="200" width="320" height="70" fill="#3BAEE3" rx="6" data-role="label"/>
  <text x="280" y="235" font-family="Arial, sans-serif" font-size="20" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">流量治理</text>
</svg>
""",
        encoding="utf-8",
    )
    output_dir = tmp_path / "eval"
    script = ROOT / "ppt-master/skills/make/scripts/ppt_master_eval.py"

    completed = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output_dir), "--target", str(project), "--svg-dir", "svg_output", "--design"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert "design" in report
    assert report["design"]["totalFiles"] == 1
    assert "design average:" in completed.stdout
    assert "diversity score:" in completed.stdout
    assert "## Design Quality" in (output_dir / "report.md").read_text(encoding="utf-8")
    assert "Regeneration Guidance" in (output_dir / "report.md").read_text(encoding="utf-8")


def _write_archetype_svg(path: Path, body: str) -> None:
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">多样性测试页面</text>
  <text x="72" y="118" font-family="Arial, sans-serif" font-size="18" fill="#64748B">不同内容应触发不同视觉语法</text>
  {body}
</svg>
""",
        encoding="utf-8",
    )


def test_design_quality_checker_scores_deck_level_archetype_diversity(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    _write_archetype_svg(svg_dir / "01_compare.svg", '<rect x="120" y="220" width="260" height="160" fill="#EEF6FF" data-intent="current" data-role="content-card"/><rect x="840" y="220" width="260" height="160" fill="#EAF8F0" data-intent="target" data-role="content-card"/>')
    _write_archetype_svg(svg_dir / "02_kpi.svg", ''.join(f'<rect x="{120+i*210}" y="220" width="160" height="90" fill="#FFFFFF" data-role="metric-card" data-intent="kpi"/>' for i in range(4)))
    _write_archetype_svg(svg_dir / "03_arch.svg", '<rect x="160" y="210" width="860" height="54" fill="#EEF6FF" data-role="layer-stack"/><rect x="160" y="290" width="860" height="54" fill="#EEF6FF" data-role="architecture-layer"/>')
    _write_archetype_svg(svg_dir / "04_process.svg", ''.join(f'<rect x="{120+i*220}" y="230" width="160" height="90" fill="#FFFFFF" data-role="process-step" data-intent="process"/>' for i in range(4)))
    _write_archetype_svg(svg_dir / "05_matrix.svg", '<rect x="120" y="210" width="900" height="48" fill="#3BAEE3" data-role="table-header"/><rect x="120" y="270" width="900" height="54" fill="#FFFFFF" data-role="table-row"/>')
    _write_archetype_svg(svg_dir / "06_code.svg", '<rect x="140" y="210" width="760" height="260" fill="#0F172A" data-role="code"/><text x="172" y="260" font-family="Consolas, monospace" font-size="18" fill="#E2E8F0">kind: VirtualService</text>')

    report = DesignQualityChecker().check_target(project, svg_dir_name="svg_output")

    assert report["deckDiversity"]["score"] >= 85
    assert len(report["deckDiversity"]["archetypeCounts"]) >= 5
    assert not report["deckDiversity"]["issues"]


def test_design_quality_checker_flags_repeated_card_grid_deck(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    card_body = ''.join(
        f'<rect x="{110 + (i % 3) * 260}" y="{210 + (i // 3) * 120}" width="210" height="82" fill="#FFFFFF" data-role="content-card"/>'
        for i in range(6)
    )
    for index in range(6):
        _write_archetype_svg(svg_dir / f"{index + 1:02d}_cards.svg", card_body)

    report = DesignQualityChecker().check_target(project, svg_dir_name="svg_output")

    assert report["deckDiversity"]["score"] < 70
    issue_codes = {issue["code"] for issue in report["deckDiversity"]["issues"]}
    assert {"low_archetype_variety", "repeated_visual_archetype", "card_grid_overuse"} <= issue_codes
    guidance_codes = {item["code"] for item in report["deckGenerationGuidance"]}
    assert {"rebalance_deck_archetypes", "reduce_card_grid_overuse"} <= guidance_codes


def test_design_archetype_planner_maps_mixed_source_to_distinct_archetypes():
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_archetype_planner import plan_archetypes
    finally:
        sys.path.pop(0)

    source = """# 技术方案

## 现状与目标
当前只能凌晨发布，目标是白天安全灰度发布。

## 建设指标
灰度精度 ≤0.1%，染色覆盖 ≥95%，回滚时间 ≤2 分钟。

## 总体架构
方案包含 Ingress Gateway、控制面 istiod、Envoy Sidecar、观测平台层。

## 实施流程
第一阶段试点接入，第二阶段策略固化，第三阶段推广。

## 对象映射
| OCP 对象 | ACP 对象 | 风险 |
|---|---|---|
| Route | Ingress | 中 |

## YAML 示例
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
```

## 为什么选择 ASM
Kubernetes 滚动更新无法满足请求级灰度验证。
"""

    report = plan_archetypes(source, page_count=7)
    archetypes = {page["visualArchetype"] for page in report["pages"]}

    assert {"comparison_bridge", "kpi_dashboard", "architecture_stack", "process_flow", "matrix_table", "code_annotation", "argument_thesis"} <= archetypes
    assert "## design_diversity" in report["specLockSnippet"]
    assert "## density_contract" in report["specLockSnippet"]
    assert all("densityContract" in page for page in report["pages"])
    dense_pages = [page for page in report["pages"] if page["densityContract"]["visibleLabelsMin"] >= 12]
    assert len(dense_pages) >= 4
    assert any(page["contentLedger"]["visibleObjects"] for page in report["pages"])


def test_design_quality_checker_flags_sparse_page_against_density_contract(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    (project / "spec_lock.md").write_text(
        """## density_contract
- source: test
- P01: visible_claims>=3; visible_objects>=8; visible_labels>=12; evidence_items>=3; relationships>=3; notes_only_ratio<=0.35; fill=0.50-0.72 | expose=Route,SCC,Ingress
""",
        encoding="utf-8",
    )
    (svg_dir / "01_sparse.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">迁移方案</text>
  <rect x="160" y="240" width="280" height="100" fill="#FFFFFF" rx="6" data-role="content-card"/>
  <text x="300" y="295" font-family="Arial, sans-serif" font-size="22" fill="#334155" text-anchor="middle" dominant-baseline="middle">标准化承载</text>
</svg>
""",
        encoding="utf-8",
    )

    report = DesignQualityChecker().check_target(project, svg_dir_name="svg_output")
    page = report["pages"][0]
    issue_codes = {issue["code"] for issue in page["issues"]}

    assert page["metrics"]["informationDensity"] < 70
    assert "low_information_density" in issue_codes
    assert any(item["code"] == "raise_visible_density_from_contract" for item in page["generationGuidance"])


def test_design_quality_checker_accepts_dense_page_against_density_contract(tmp_path):
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from design_quality_checker import DesignQualityChecker
    finally:
        sys.path.pop(0)

    project = tmp_path / "project"
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True)
    (project / "spec_lock.md").write_text(
        """## density_contract
- source: test
- P01: visible_claims>=3; visible_objects>=8; visible_labels>=12; evidence_items>=3; relationships>=3; notes_only_ratio<=0.35; fill=0.30-0.74 | expose=Route,SCC,Ingress
""",
        encoding="utf-8",
    )
    labels = [
        ("Route -> Ingress", "对象映射", "风险中", "回退点1"),
        ("SCC -> PSS", "安全约束", "策略组", "人工复核"),
        ("ImageStream -> Harbor", "镜像仓库", "风险低", "保留仓库"),
        ("BuildConfig -> Tekton", "流水线", "风险中", "双轨验证"),
    ]
    rows = []
    for row, values in enumerate(labels):
        y = 210 + row * 72
        rows.append(f'<rect x="120" y="{y}" width="920" height="52" fill="#FFFFFF" stroke="#DDE8F3" data-role="table-row"/>')
        for col, value in enumerate(values):
            rows.append(f'<text x="{150 + col * 220}" y="{y + 32}" font-family="Arial, sans-serif" font-size="17" fill="#334155">{value}</text>')
    (svg_dir / "01_dense.svg").write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <text x="72" y="80" font-family="Arial, sans-serif" font-size="38" fill="#334155" font-weight="700">OCP 对象到 ACP 标准对象映射</text>
  <text x="72" y="118" font-family="Arial, sans-serif" font-size="18" fill="#64748B">4 类对象按自动化程度、风险级别和回退点切分批次</text>
  <rect x="120" y="150" width="920" height="44" fill="#3BAEE3" data-role="table-header"/>
  <text x="150" y="178" font-family="Arial, sans-serif" font-size="17" fill="#FFFFFF">OCP 对象</text>
  <text x="370" y="178" font-family="Arial, sans-serif" font-size="17" fill="#FFFFFF">ACP 对象</text>
  <text x="590" y="178" font-family="Arial, sans-serif" font-size="17" fill="#FFFFFF">风险 / 责任</text>
  <text x="810" y="178" font-family="Arial, sans-serif" font-size="17" fill="#FFFFFF">回退点</text>
  {''.join(rows)}
  <text x="120" y="560" font-family="Arial, sans-serif" font-size="18" fill="#334155">证据：4类对象、2个中风险项、1个低风险项、Go/No-Go 门禁。</text>
</svg>
""",
        encoding="utf-8",
    )

    report = DesignQualityChecker().check_target(project, svg_dir_name="svg_output")
    page = report["pages"][0]

    assert page["metrics"]["informationDensity"] >= 78
    assert not any(issue["code"] == "low_information_density" for issue in page["issues"])


def test_ppt_master_eval_can_plan_source_archetypes(tmp_path):
    project = tmp_path / "project"
    sources = project / "sources"
    svg_dir = project / "svg_output"
    sources.mkdir(parents=True)
    svg_dir.mkdir()
    (sources / "source.md").write_text(
        """# 方案

## 架构
Ingress Gateway、Sidecar、控制面和观测平台分层。

## YAML
```yaml
kind: VirtualService
```
""",
        encoding="utf-8",
    )
    (svg_dir / "01.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#FFFFFF"/><text x="72" y="80" font-size="38" font-family="Arial" fill="#334155">测试</text></svg>',
        encoding="utf-8",
    )
    output_dir = tmp_path / "eval"
    script = ROOT / "ppt-master/skills/make/scripts/ppt_master_eval.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(output_dir),
            "--target",
            str(project),
            "--svg-dir",
            "svg_output",
            "--plan-archetypes",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert "archetypePlan" in report
    assert report["archetypePlan"]["pageCount"] >= 1
    assert "densityContract" in report["archetypePlan"]["pages"][0]
    assert "planned archetypes:" in completed.stdout
    assert "density contracts:" in completed.stdout


# ---------------------------------------------------------------------------
# Closed-loop tests: normalize pipeline resolves detected problems
# ---------------------------------------------------------------------------

def _extract_rect_attrs(svg: str) -> list[dict]:
    """Parse all <rect> elements and return a list of attribute dicts."""
    rects = []
    for m in re.finditer(r"<rect\b([^>]*)/>", svg):
        attrs: dict = {}
        for attr_m in re.finditer(r'(\w[\w-]*)="([^"]*)"', m.group(1)):
            key, val = attr_m.group(1), attr_m.group(2)
            if key in ("x", "y", "width", "height"):
                attrs[key] = float(val)
            else:
                attrs[key] = val
        rects.append(attrs)
    return rects


def _extract_text_attrs(svg: str) -> list[dict]:
    """Parse all <text> elements and return a list of attribute dicts."""
    texts = []
    for m in re.finditer(r"<text\b([^>]*)>([^<]*)</text>", svg):
        attrs: dict = {"_content": m.group(2)}
        for attr_m in re.finditer(r'(\w[\w-]*)="([^"]*)"', m.group(1)):
            key, val = attr_m.group(1), attr_m.group(2)
            if key in ("x", "y"):
                attrs[key] = float(val)
            elif key == "font-size":
                attrs["font-size"] = float(val)
            else:
                attrs[key] = val
        texts.append(attrs)
    return texts


def test_normalize_resolves_overlapping_sibling_cards():
    """After normalize, overlapping sibling content-cards must be separated
    by at least SEMANTIC_SIBLING_MIN_GAP (12 px)."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import (
            normalize_colored_block_text,
            SEMANTIC_SIBLING_MIN_GAP,
        )
    finally:
        sys.path.pop(0)

    overlapping_svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <rect x="100" y="120" width="400" height="200" fill="#3BAEE3" rx="6" data-role="content-card"/>
  <text x="300" y="200" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card A Title</text>
  <text x="300" y="260" font-size="14" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card A content</text>
  <rect x="100" y="310" width="400" height="200" fill="#2196F3" rx="6" data-role="content-card"/>
  <text x="300" y="380" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card B Title</text>
  <text x="300" y="440" font-size="14" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card B content</text>
</svg>"""

    processed, change_count = normalize_colored_block_text(overlapping_svg)

    rects = _extract_rect_attrs(processed)
    cards = [r for r in rects if r.get("data-role") == "content-card"]
    assert len(cards) == 2, f"Expected 2 content-cards, found {len(cards)}"

    card_a = cards[0]
    card_b = cards[1]
    card_a_bottom = card_a["y"] + card_a["height"]
    card_b_top = card_b["y"]

    assert card_b_top >= card_a_bottom + SEMANTIC_SIBLING_MIN_GAP, (
        f"Card B top ({card_b_top}) must be >= Card A bottom ({card_a_bottom}) "
        f"+ gap ({SEMANTIC_SIBLING_MIN_GAP}), but gap is only {card_b_top - card_a_bottom}"
    )


def test_normalize_resolves_text_exceeding_card_boundary():
    """After normalize, text that overflows a narrow card must have its
    font-size reduced so it fits within the card width."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import normalize_colored_block_text
    finally:
        sys.path.pop(0)

    overflow_svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <rect x="100" y="120" width="300" height="80" fill="#3BAEE3" rx="6" data-role="content-card"/>
  <text x="250" y="155" font-size="22" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">这是一段非常长的中文标题文字需要缩小</text>
</svg>"""

    processed, _count = normalize_colored_block_text(overflow_svg)

    texts = _extract_text_attrs(processed)
    card_texts = [t for t in texts if "这是" in t.get("_content", "")]
    assert len(card_texts) >= 1, "Expected the long-title text element in output"

    final_font_size = card_texts[0].get("font-size", 22)
    assert final_font_size < 22, (
        f"Font-size should be reduced from 22 to fit card width, "
        f"but got {final_font_size}"
    )


def test_normalize_fixes_then_checker_finds_no_overlap_warnings(tmp_path):
    """Full closed-loop: overlapping cards -> normalize -> checker -> zero
    overlap/spacing warnings."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import normalize_colored_block_text
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    cascade_svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <rect x="100" y="120" width="400" height="200" fill="#3BAEE3" rx="6" data-role="content-card"/>
  <text x="300" y="220" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card 1</text>
  <rect x="100" y="310" width="400" height="200" fill="#2196F3" rx="6" data-role="content-card"/>
  <text x="300" y="410" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card 2</text>
  <rect x="100" y="500" width="400" height="200" fill="#1976D2" rx="6" data-role="content-card"/>
  <text x="300" y="600" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Card 3</text>
</svg>"""

    processed, _count = normalize_colored_block_text(cascade_svg)

    svg_path = tmp_path / "cascade_fixed.svg"
    svg_path.write_text(processed, encoding="utf-8")

    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    overlap_warnings = [
        w for w in result["warnings"]
        if "semantic component overlap/spacing" in w
    ]
    assert not overlap_warnings, (
        f"Expected 0 overlap/spacing warnings after normalize, "
        f"but found: {overlap_warnings}"
    )


def test_normalize_cascade_overlap_resolves_within_parent(tmp_path):
    """When cards sit inside a parent panel, normalize must not push
    children beyond the parent's bottom edge (minus SLOT_PARENT_INSET)."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import (
            normalize_colored_block_text,
            SLOT_PARENT_INSET,
        )
        from svg_quality_checker import SVGQualityChecker
    finally:
        sys.path.pop(0)

    parent_svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF" data-role="page-background"/>
  <rect x="80" y="100" width="500" height="500" fill="#F0F4F8" rx="8" data-role="panel"/>
  <rect x="100" y="120" width="460" height="150" fill="#3BAEE3" rx="6" data-role="content-card"/>
  <text x="330" y="195" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Upper Card</text>
  <rect x="100" y="250" width="460" height="150" fill="#2196F3" rx="6" data-role="content-card"/>
  <text x="330" y="325" font-size="18" font-family="Arial" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">Lower Card</text>
</svg>"""

    processed, _count = normalize_colored_block_text(parent_svg)

    rects = _extract_rect_attrs(processed)
    panels = [r for r in rects if r.get("data-role") == "panel"]
    cards = [r for r in rects if r.get("data-role") == "content-card"]

    assert len(panels) >= 1, "Expected at least 1 panel rect"
    assert len(cards) == 2, f"Expected 2 content-cards, found {len(cards)}"

    panel = panels[0]
    panel_bottom = panel["y"] + panel["height"]
    lower_card = cards[1]
    lower_card_bottom = lower_card["y"] + lower_card["height"]

    assert lower_card_bottom <= panel_bottom - SLOT_PARENT_INSET, (
        f"Lower card bottom ({lower_card_bottom}) exceeds panel bottom "
        f"({panel_bottom}) minus SLOT_PARENT_INSET ({SLOT_PARENT_INSET})"
    )

    svg_path = tmp_path / "parent_constrained.svg"
    svg_path.write_text(processed, encoding="utf-8")
    result = SVGQualityChecker().check_file(str(svg_path), expected_format="ppt169")

    overlap_warnings = [
        w for w in result["warnings"]
        if "semantic component overlap/spacing" in w
    ]
    assert not overlap_warnings, (
        f"Expected 0 overlap/spacing warnings, but found: {overlap_warnings}"
    )


# ---------------------------------------------------------------------------
# viewBox overflow clipping — decorative shapes past canvas are removed
# ---------------------------------------------------------------------------

def test_clip_viewbox_overflow_removes_decorative_circles():
    """Low-opacity circles extending past viewBox should be removed during normalize."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import clip_viewbox_overflow
    finally:
        sys.path.pop(0)

    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <circle cx="1350" cy="600" r="280" fill="#3BAEE3" fill-opacity="0.04"/>
  <circle cx="1400" cy="250" r="220" fill="#3BAEE3" fill-opacity="0.03"/>
  <ellipse cx="1150" cy="780" rx="350" ry="130" fill="#3BAEE3" fill-opacity="0.02"/>
  <rect x="60" y="120" width="200" height="100" fill="#F8FAFC" rx="8" data-role="kpi-card"/>
</svg>"""

    clipped, count = clip_viewbox_overflow(svg)
    assert count == 3, f"Expected 3 decorative shapes removed, got {count}"
    assert "<circle" not in clipped, "Decorative circles should be removed"
    assert "<ellipse" not in clipped, "Decorative ellipse should be removed"
    assert "kpi-card" in clipped, "Content rect must be preserved"


def test_clip_viewbox_overflow_preserves_content_shapes():
    """Non-decorative shapes (no fill-opacity < 0.1) should survive even if overflowing."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_finalize.normalize_layout import clip_viewbox_overflow
    finally:
        sys.path.pop(0)

    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="60" y="460" width="1160" height="458" fill="#F1F5F9" rx="8" data-role="content-card"/>
</svg>"""

    clipped, count = clip_viewbox_overflow(svg)
    assert count == 0, "Content rect should not be removed even if overflowing"
    assert "content-card" in clipped


def test_checker_detects_viewbox_overflow():
    """svg_quality_checker should warn about shapes past viewBox."""
    scripts_dir = ROOT / "ppt-master/skills/make/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from svg_quality_checker import SVGQualityChecker as Checker
    finally:
        sys.path.pop(0)

    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <circle cx="1350" cy="600" r="280" fill="#3BAEE3" fill-opacity="0.04"/>
  <ellipse cx="1150" cy="780" rx="350" ry="130" fill="#3BAEE3" fill-opacity="0.02"/>
  <rect x="60" y="460" width="1160" height="458" fill="#F1F5F9" rx="8" data-role="content-card"/>
</svg>"""

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
        f.write(svg)
        tmp_path = f.name

    try:
        result = Checker().check_file(tmp_path, expected_format="ppt169")
        overflow_warnings = [w for w in result["warnings"] if "viewBox boundary" in w]
        assert len(overflow_warnings) == 1, f"Expected 1 viewBox overflow warning, got {len(overflow_warnings)}"
    finally:
        os.unlink(tmp_path)


def test_normalize_shelter_guard_prevents_cross_component_adoption(tmp_path):
    """Text inside a non-component shape (e.g. risk-strip) must not be adopted
    by a nearby component-parent, which would cause the component to grow."""
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_shelter.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="60" y="410" width="525" height="148" rx="6" fill="#FFFFFF" data-role="callout-content"/>
  <rect x="60" y="586" width="1160" height="72" fill="#FEF7ED" data-role="risk-strip"/>
  <text x="120" y="614" font-family="Arial" font-size="14" font-weight="bold" fill="#B45309">Risk warning text</text>
</svg>
""",
        encoding="utf-8",
    )
    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    final_svg = (project / "svg_final/01_shelter.svg").read_text(encoding="utf-8")
    assert 'height="148"' in final_svg, "Callout should keep original height — risk-strip text must not expand it"


def test_normalize_footer_zone_not_adopted(tmp_path):
    """Footer texts (Alauda, page number) near canvas bottom must not be
    adopted by content cards above, which would cause the cards to grow."""
    project = tmp_path / "project"
    svg_output = project / "svg_output"
    svg_output.mkdir(parents=True)
    (svg_output / "01_footer.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="60" y="600" width="780" height="71" rx="6" fill="#F1F5F9" data-role="callout-content"/>
  <text x="80" y="625" font-family="Arial" font-size="14" fill="#475569">Caption inside card</text>
  <line x1="0" y1="682" x2="1280" y2="683" stroke="#E2E8F0"/>
  <text x="60" y="706" font-family="Arial" font-size="11" fill="#94A3B8">Alauda</text>
  <text x="1220" y="706" font-family="Arial" font-size="11" fill="#94A3B8">08</text>
</svg>
""",
        encoding="utf-8",
    )
    script = ROOT / "ppt-master/skills/make/scripts/finalize_svg.py"
    subprocess.run(
        [sys.executable, str(script), str(project), "--only", "normalize-layout", "--quiet"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    final_svg = (project / "svg_final/01_footer.svg").read_text(encoding="utf-8")
    assert 'height="71"' in final_svg, "Callout should keep original height — footer texts must not expand it"
