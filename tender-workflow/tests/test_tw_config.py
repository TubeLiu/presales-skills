#!/usr/bin/env python3
"""tw_config.py 单元测试"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from tw_config import (
    _deep_get, _deep_set, _parse_value, normalize, validate,
    show, get, load, load_raw, set_value, CONFIG_PATH, DEFAULTS,
)


class TestDeepGet:
    def test_simple_key(self):
        assert _deep_get({"a": 1}, "a") == 1

    def test_nested_key(self):
        assert _deep_get({"a": {"b": {"c": 3}}}, "a.b.c") == 3

    def test_missing_key_returns_default(self):
        assert _deep_get({"a": 1}, "b") is None
        assert _deep_get({"a": 1}, "b", "fallback") == "fallback"

    def test_missing_nested_key(self):
        assert _deep_get({"a": {"b": 1}}, "a.c") is None

    def test_non_dict_intermediate(self):
        assert _deep_get({"a": "string"}, "a.b") is None

    def test_empty_dict(self):
        assert _deep_get({}, "a.b.c") is None


class TestDeepSet:
    def test_simple_set(self):
        d = {}
        _deep_set(d, "a", 1)
        assert d == {"a": 1}

    def test_nested_set(self):
        d = {}
        _deep_set(d, "a.b.c", 3)
        assert d == {"a": {"b": {"c": 3}}}

    def test_overwrite_existing(self):
        d = {"a": {"b": 1}}
        _deep_set(d, "a.b", 2)
        assert d["a"]["b"] == 2

    def test_create_intermediate_dicts(self):
        d = {"a": "not_a_dict"}
        _deep_set(d, "a.b", 1)
        assert d == {"a": {"b": 1}}


class TestParseValue:
    def test_bool_true(self):
        assert _parse_value("true") is True
        assert _parse_value("yes") is True
        assert _parse_value("True") is True

    def test_bool_false(self):
        assert _parse_value("false") is False
        assert _parse_value("no") is False

    def test_null(self):
        assert _parse_value("null") is None
        assert _parse_value("none") is None
        assert _parse_value("~") is None

    def test_int(self):
        assert _parse_value("42") == 42
        assert _parse_value("0") == 0

    def test_float(self):
        assert _parse_value("3.14") == 3.14

    def test_list(self):
        assert _parse_value("[a, b, c]") == ["a", "b", "c"]
        assert _parse_value("['ark', 'dashscope']") == ["ark", "dashscope"]

    def test_empty_list(self):
        assert _parse_value("[]") == []

    def test_string(self):
        assert _parse_value("hello") == "hello"
        assert _parse_value("/path/to/file") == "/path/to/file"


class TestNormalize:
    def test_empty_config(self):
        result = normalize({})
        assert "localkb" in result
        # api_keys / ai_image 由 ai-image plugin 管理，normalize 不再主动构造这两块。

    def test_api_keys_passthrough(self):
        # normalize 透传 api_keys 块（让 /ai-image:migrate 能看到它做后续整理）
        cfg = {"api_keys": {"ark": "user-key"}}
        result = normalize(cfg)
        assert result["api_keys"]["ark"] == "user-key"

    def test_legacy_ai_keys_lifted_to_api_keys(self):
        # 超老字段 ai_keys.ark_api_key 等 → 映射到 api_keys.* 防止 migrate 看不到
        cfg = {"ai_keys": {"ark_api_key": "sk-old", "dashscope_api_key": "sk-dash"}}
        result = normalize(cfg)
        assert result["api_keys"]["ark"] == "sk-old"
        assert result["api_keys"]["dashscope"] == "sk-dash"

    def test_new_api_keys_takes_precedence_over_legacy(self):
        cfg = {
            "api_keys": {"ark": "new-key"},
            "ai_keys": {"ark_api_key": "old-key"},
        }
        result = normalize(cfg)
        assert result["api_keys"]["ark"] == "new-key"

    def test_legacy_taa_kb_path(self):
        cfg = {"taa": {"kb_path": "/old/path"}}
        result = normalize(cfg)
        assert result["localkb"]["path"] == "/old/path"

    def test_library_path_takes_precedence(self):
        cfg = {
            "localkb": {"path": "/new/path"},
            "taa": {"kb_path": "/old/path"},
        }
        result = normalize(cfg)
        assert result["localkb"]["path"] == "/new/path"

    def test_anythingllm_workspace_merge(self):
        cfg = {"anythingllm": {"taa_workspace": "ws1"}}
        result = normalize(cfg)
        assert result["anythingllm"]["workspace"] == "ws1"
        assert "taa_workspace" not in result["anythingllm"]

    def test_skill_sections_preserved(self):
        cfg = {"taa": {"vendor": "博云"}, "tpl": {"default_template": "government"}}
        result = normalize(cfg)
        assert result["taa"]["vendor"] == "博云"
        assert result["tpl"]["default_template"] == "government"


class TestValidate:
    def test_empty_config(self):
        with patch('tw_config.load_raw', return_value={}):
            issues = validate()
            assert any("不存在或为空" in i for i in issues)

    def test_missing_library_path(self):
        with patch('tw_config.load_raw', return_value={"localkb": {"path": None}}):
            issues = validate()
            assert any("localkb.path" in i for i in issues)

    def test_nonexistent_library_path(self):
        with patch('tw_config.load_raw', return_value={"localkb": {"path": "/nonexistent/path"}}):
            issues = validate()
            assert any("不存在" in i for i in issues)


class TestShow:
    def test_empty_config(self):
        with patch('tw_config.load_raw', return_value={}):
            result = show()
            assert "未找到配置" in result

    def test_masks_api_keys(self):
        cfg = {"api_keys": {"ark": "sk-1234567890abcdef"}}
        with patch('tw_config.load_raw', return_value=cfg):
            result = show()
            assert "sk-1" in result
            assert "cdef" in result
            assert "1234567890abcdef" not in result

    def test_masks_short_api_keys(self):
        cfg = {"api_keys": {"ark": "short"}}
        with patch('tw_config.load_raw', return_value=cfg):
            result = show()
            assert "***" in result
            assert "short" not in result

    def test_shows_none_as_unset(self):
        cfg = {"localkb": {"path": None}}
        with patch('tw_config.load_raw', return_value=cfg):
            result = show()
            assert "未设置" in result


class TestGet:
    def test_skill_section_key(self):
        cfg = {"taa": {"vendor": "灵雀云"}}
        with patch('tw_config.load', return_value=cfg):
            assert get("taa", "vendor") == "灵雀云"

    def test_global_key_mapping(self):
        cfg = {"localkb": {"path": "/test/path"}, "taa": {}}
        with patch('tw_config.load', return_value=cfg):
            assert get("taa", "localkb.path") == "/test/path"

    def test_default_value(self):
        cfg = {"taa": {}}
        with patch('tw_config.load', return_value=cfg):
            assert get("taa", "nonexistent", "default") == "default"


class TestSetValueGuard:
    """守卫：api_keys.* / ai_image.* 由 ai-image plugin 管理，不允许从 tw 写入"""

    def test_rejects_api_keys_dot_path(self):
        with pytest.raises(ValueError, match="ai-image plugin 管理"):
            set_value("api_keys.ark", "sk-test")

    def test_rejects_ai_image_dot_path(self):
        with pytest.raises(ValueError, match="ai-image plugin 管理"):
            set_value("ai_image.default_provider", "gemini")

    def test_rejects_top_level_keys(self):
        for k in ("api_keys", "ai_image"):
            with pytest.raises(ValueError):
                set_value(k, {})

    def test_normal_keys_pass_through(self, tmp_path, monkeypatch):
        # 用 tmp_path 替代真实 CONFIG_PATH 避免污染用户配置
        fake_config = tmp_path / "config.yaml"
        monkeypatch.setattr("tw_config.CONFIG_PATH", fake_config)
        set_value("tpl.default_template", "government")
        # 写入成功不抛
        assert fake_config.exists()


class TestNormalizeAiImagePassthrough:
    def test_ai_image_block_passthrough(self):
        cfg = {"ai_image": {"default_provider": "gemini", "models": {"gemini": "x"}}}
        result = normalize(cfg)
        assert result["ai_image"]["default_provider"] == "gemini"
        assert result["ai_image"]["models"]["gemini"] == "x"


class TestLoadSkillView:
    def test_skill_view_excludes_api_keys_and_ai_image(self):
        # load(skill) 不应在视图里包含 api_keys / ai_image 块（这两块由 ai-image plugin 持有）
        raw = {
            "localkb": {"path": "/p"},
            "anythingllm": {"workspace": "ws"},
            "api_keys": {"ark": "sk-x"},
            "ai_image": {"default_provider": "ark"},
            "taw": {"image_source": "ai"},
        }
        with patch("tw_config.load_raw", return_value=raw):
            view = load("taw")
        assert "api_keys" not in view, "skill 视图不应暴露 api_keys（由 ai-image plugin 持有）"
        assert "ai_image" not in view, "skill 视图不应暴露 ai_image（由 ai-image plugin 持有）"
        assert view["localkb"]["path"] == "/p"
        assert view["taw"]["image_source"] == "ai"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
