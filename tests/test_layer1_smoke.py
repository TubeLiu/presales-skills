"""Layer 1 smoke + workflow 文档结构 lint。

覆盖三类轻量回归（无 API key、无外部依赖即可跑）：

1. **solution-master sm_config CRUD 烟测**——pure-python 配置 CRUD 在 tmp 文件下 round-trip，
   覆盖 DEFAULTS schema、_normalize_mcp_search 老别名迁移、ai-image 字段拒写护栏。
   solution-master/tests/ 是空的，本文件填补主 plugin 测试覆盖。

2. **ppt-master project_utils 烟测**——确认核心 helper 模块可 import 且 CANVAS_FORMATS 完整。
   ppt-master/tests/ 不存在，本文件填补该 plugin 最低限度测试覆盖。

3. **knowledge-retrieval 文档结构 lint**——solution-master 的 knowledge-retrieval workflow 是
   prompt-driven 不是 python 函数，所以"测试"只能落到文档结构：四层检索 header 全在、
   AnythingLLM 降级矩阵 5 行齐全、ANYTHINGLLM_AVAILABLE 判定关键词存在。一旦有人误删
   降级语义，本测试立即报失败。

跑：
    cd presales-skills/
    python3 -m pytest tests/test_layer1_smoke.py -v
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. solution-master sm_config CRUD 烟测
# ---------------------------------------------------------------------------

SM_CONFIG_PATH = REPO_ROOT / "solution-master/skills/go/scripts/sm_config.py"


def _import_sm_config(monkeypatch, tmp_path: Path):
    """以独立模块身份 import sm_config，并将 CONFIG_PATH redirect 到 tmp。

    用 importlib.util 避免 sys.modules 污染（多个测试可独立 fixture）。
    """
    spec = importlib.util.spec_from_file_location(
        f"sm_config_test_{tmp_path.name}", SM_CONFIG_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    # 先把 _ensure_deps 短路（避免本测试触发 pip install）
    parent = SM_CONFIG_PATH.parent
    monkeypatch.syspath_prepend(str(parent))
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "CONFIG_PATH", tmp_path / "config.yaml")
    return mod


def test_sm_config_defaults_schema(tmp_path, monkeypatch):
    """DEFAULTS 必须含 5 个 section，每个有正确默认值。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    expected_sections = {"localkb", "anythingllm", "mcp_search", "cdp_sites", "drawio"}
    assert set(sm.DEFAULTS.keys()) == expected_sections, (
        f"DEFAULTS 应有 5 段：{expected_sections}，实际 {set(sm.DEFAULTS.keys())}"
    )
    assert sm.DEFAULTS["localkb"] == {"path": None}
    assert sm.DEFAULTS["mcp_search"] == {"priority": []}
    assert sm.DEFAULTS["cdp_sites"]["enabled"] is False


def test_sm_config_load_empty_returns_defaults(tmp_path, monkeypatch):
    """空 config（不存在文件）→ load() 返回 DEFAULTS 副本，不崩溃。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    cfg = sm.load()
    assert "localkb" in cfg
    assert "anythingllm" in cfg
    assert "mcp_search" in cfg
    assert cfg["mcp_search"] == {"priority": []}


def test_sm_config_set_get_roundtrip(tmp_path, monkeypatch):
    """set_value → load round-trip 保留值。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    sm.set_value("localkb.path", "/tmp/my-kb")
    cfg = sm.load()
    assert cfg["localkb"]["path"] == "/tmp/my-kb"


def test_sm_config_normalize_mcp_search_legacy_alias(tmp_path, monkeypatch):
    """LEGACY_ALIAS 透明迁移：tavily_search → mcp__tavily__tavily_search 等。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    out = sm._normalize_mcp_search({
        "priority": ["tavily_search", "exa_search", "minimax_search", "websearch"]
    })
    assert out["priority"] == [
        "mcp__tavily__tavily_search",
        "mcp__exa__web_search_exa",
        "mcp__minimax__web_search",
        "WebSearch",
    ]


def test_sm_config_normalize_mcp_search_robust_to_garbage(tmp_path, monkeypatch):
    """非 dict / 非 list / 非 str 元素不应导致崩溃。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    assert sm._normalize_mcp_search(None)["priority"] == []
    assert sm._normalize_mcp_search("not-a-dict")["priority"] == []
    assert sm._normalize_mcp_search({"priority": "not-a-list"})["priority"] == []
    assert sm._normalize_mcp_search({"priority": [None, 42, "", "  ", "WebSearch"]})["priority"] == ["WebSearch"]


def test_sm_config_set_value_blocks_ai_image_keys(tmp_path, monkeypatch):
    """护栏：set_value 不允许写 api_keys.* / ai_image.*（这些归 ai-image plugin 管）。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="ai-image plugin"):
        sm.set_value("api_keys.ark", "sk-fake")
    with pytest.raises(ValueError, match="ai-image plugin"):
        sm.set_value("ai_image.default_provider", "ark")


def test_sm_config_unknown_priority_kept_as_is(tmp_path, monkeypatch):
    """未知字符串（非 mcp__ / 非 WebSearch / 非 LEGACY_ALIAS）原样保留——不丢用户配置。"""
    sm = _import_sm_config(monkeypatch, tmp_path)
    out = sm._normalize_mcp_search({"priority": ["mcp__custom__search", "RandomString"]})
    assert "mcp__custom__search" in out["priority"]
    assert "RandomString" in out["priority"]


# ---------------------------------------------------------------------------
# 2. ppt-master project_utils 烟测
# ---------------------------------------------------------------------------

PPT_PROJECT_UTILS = REPO_ROOT / "ppt-master/skills/make/scripts/project_utils.py"


def _import_ppt_project_utils(monkeypatch):
    """import ppt-master 的 project_utils（pure-python，无 cairo / pandoc 依赖）。"""
    spec = importlib.util.spec_from_file_location("ppt_project_utils", PPT_PROJECT_UTILS)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.syspath_prepend(str(PPT_PROJECT_UTILS.parent))
    spec.loader.exec_module(mod)
    return mod


def test_ppt_project_utils_imports(monkeypatch):
    """project_utils 模块本身可 import 不崩溃（CANVAS_FORMATS / parse_project_info 等可见）。"""
    pu = _import_ppt_project_utils(monkeypatch)
    assert hasattr(pu, "CANVAS_FORMATS"), "应导出 CANVAS_FORMATS"


def test_ppt_canvas_formats_includes_ppt169_and_ppt43(monkeypatch):
    """CANVAS_FORMATS 至少含 ppt169（16:9 默认）+ ppt43。结构必含 name / aspect_ratio / dimensions。"""
    pu = _import_ppt_project_utils(monkeypatch)
    assert "ppt169" in pu.CANVAS_FORMATS, "16:9 是默认 PPT 比例，必须存在"
    assert "ppt43" in pu.CANVAS_FORMATS, "4:3 是另一常用 PPT 比例，必须存在"

    for key in ("ppt169", "ppt43"):
        fmt = pu.CANVAS_FORMATS[key]
        assert "name" in fmt
        assert "aspect_ratio" in fmt
        assert "dimensions" in fmt


# ---------------------------------------------------------------------------
# 3. knowledge-retrieval workflow 文档结构 lint
# ---------------------------------------------------------------------------

KNOWLEDGE_RETRIEVAL_DOC = REPO_ROOT / "solution-master/skills/go/workflow/knowledge-retrieval.md"


@pytest.fixture(scope="module")
def kr_text() -> str:
    assert KNOWLEDGE_RETRIEVAL_DOC.exists(), f"缺 workflow 文档：{KNOWLEDGE_RETRIEVAL_DOC}"
    return KNOWLEDGE_RETRIEVAL_DOC.read_text(encoding="utf-8")


def test_kr_doc_has_four_layer_headers(kr_text):
    """四层检索架构必须各自有独立 H2 章节——任何一层被删除都视为退化。"""
    expected_layer_headers = [
        "## 第一层：本地 KB",
        "## 第二层：AnythingLLM",
        "## 第三层：Web 搜索",
        "## 第四层",  # CDP 浏览器检索（标题可能含或不含 CDP 字样，取共同前缀）
    ]
    for header in expected_layer_headers:
        assert header in kr_text, f"缺四层检索章节：{header!r}"


def test_kr_doc_anythingllm_fallback_matrix(kr_text):
    """AnythingLLM 降级矩阵必须含全部 5 个 --kb-source 模式。

    模式枚举：anythingllm / auto / local / cdp / none。删了任何一行 = 降级语义残缺。
    """
    expected_modes = ["anythingllm", "auto", "local", "cdp", "none"]
    # 仅在"降级矩阵"上下文里搜，避免误匹配（搜更具体的标志：` 降级矩阵 ` + 后续表格内容）
    matrix_idx = kr_text.find("降级矩阵")
    assert matrix_idx > 0, "缺 'AnythingLLM 降级矩阵' 段"
    matrix_block = kr_text[matrix_idx : matrix_idx + 2000]
    for mode in expected_modes:
        assert f"`{mode}`" in matrix_block, (
            f"AnythingLLM 降级矩阵缺 --kb-source `{mode}` 行"
        )


def test_kr_doc_has_anythingllm_available_branch(kr_text):
    """ANYTHINGLLM_AVAILABLE 判定逻辑必须存在——这是降级关键开关。"""
    assert "ANYTHINGLLM_AVAILABLE" in kr_text, (
        "缺 ANYTHINGLLM_AVAILABLE 检测语义；删了它意味着 AnythingLLM 缺失时无法软降级"
    )
    # 致命错误 + 自动降级 是降级矩阵的核心动词，缺一不可
    assert "致命错误" in kr_text or "致命" in kr_text
    assert "自动降级" in kr_text or "降级" in kr_text


def test_kr_doc_mentions_subagent_tool_restriction(kr_text):
    """主 session 直接执行检索（subagent pre-approval 限制）—— 这是工具限制 + 上下文边界，
    误删会导致 subagent NEEDS_CONTEXT 报错浪费一轮。"""
    assert "auto-deny" in kr_text or "auto deny" in kr_text or "pre-approval" in kr_text, (
        "缺 subagent pre-approval / auto-deny 语义提示"
    )
    assert "主 session" in kr_text or "主上下文" in kr_text
