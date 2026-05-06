import json
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
    assert "density_profile" in design_spec
    assert "component_primitives" in design_spec
    assert "connector_policy" in design_spec
    assert "route_quality_rules" in design_spec
    assert "## visual_system" in spec_lock
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


def test_svg_to_pptx_maps_middle_baseline_to_vertical_center_anchor():
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
    assert 'anchor="ctr"' in result.xml
    assert 'anchorCtr="1"' in result.xml
    assert '<a:pPr algn="ctr"/>' in result.xml


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

    assert "fixtures: 9/9 passed" in completed.stdout
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["fixtureSummary"] == {"total": 9, "passed": 9, "failed": 0}
    assert any(case["name"] == "connector_text_lane" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "visible_internal_metadata" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "shape_text_centering" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "multi_label_strip_centering" and case["passed"] for case in report["fixtures"])
    assert any(case["name"] == "pale_colored_block_centering" and case["passed"] for case in report["fixtures"])
    assert (output_dir / "report.md").exists()
