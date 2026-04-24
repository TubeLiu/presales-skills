#!/usr/bin/env python3
"""
Tender Workflow 统一配置管理工具

配置文件：~/.config/tender-workflow/config.yaml
支持 CLI 调用和 Python import 两种方式。

CLI 用法：
    python3 tools/tw_config.py show [skill]
    python3 tools/tw_config.py get <skill> <key> [default]
    python3 tools/tw_config.py set <key> <value>
    python3 tools/tw_config.py validate
    python3 tools/tw_config.py migrate
    python3 tools/tw_config.py normalize
"""

import json
import os
import sys
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
        )
    except subprocess.CalledProcessError:
        print("错误：缺少 pyyaml 依赖且自动安装失败，请手动执行：", file=sys.stderr)
        print(f"  {sys.executable} -m pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    import yaml

CONFIG_PATH = Path.home() / ".config" / "tender-workflow" / "config.yaml"

LEGACY_PATHS = {
    "taw": Path.home() / ".config" / "taw" / "config.yaml",
    "taa": Path.home() / ".config" / "taa" / "config.yaml",
}

# 规范 schema：所有 skill 和全局节的默认值
DEFAULTS = {
    "localkb": {"path": None},
    "anythingllm": {"enabled": False, "base_url": "http://localhost:3001", "workspace": None},
    "api_keys": {"ark": None, "dashscope": None, "gemini": None},
    "ai_image": {
        "default_provider": "ark",
        "size": "2048x2048",
        "max_retries": 2,
        "timeout": 60,
        "models": {
            "ark": "doubao-seedream-5-0-260128",
            "dashscope": "qwen-image-2.0-pro",
            "gemini": "gemini-2.5-flash-image",
        },
    },
    "mcp_search": {"priority": ["tavily_search", "exa_search"]},
    "drawio": {"cli_path": None},
    "taa": {"vendor": "灵雀云", "kb_source": "auto", "anythingllm_workspace": None},
    "taw": {"kb_source": "auto", "image_source": "auto", "anythingllm_workspace": None},
    "tpl": {"default_template": None, "default_level": "standard"},
    "trv": {"default_level": "all"},
}

SKILLS = ("taa", "taw", "tpl", "trv")


def _read_yaml(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _deep_get(d: Dict, dotted_key: str, default: Any = None) -> Any:
    """支持 dot notation 的字典取值"""
    keys = dotted_key.split(".")
    current = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k)
        if current is None:
            return default
    return current


def _deep_set(d: Dict, dotted_key: str, value: Any) -> None:
    """支持 dot notation 的字典写入"""
    keys = dotted_key.split(".")
    current = d
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


def _parse_value(raw: str) -> Any:
    """尝试将字符串解析为 Python 类型"""
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False
    if raw.lower() in ("null", "none", "~"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.startswith("[") and raw.endswith("]"):
        items = [s.strip().strip("'\"") for s in raw[1:-1].split(",")]
        return [i for i in items if i]
    return raw


# ── Schema 规范化 ────────────────────────────────────

def normalize(cfg: Dict) -> Dict:
    """
    将旧 schema 的 key 名映射到规范 schema。

    旧 schema 问题：
    - ai_keys.ark_api_key -> api_keys.ark
    - ai_keys.dashscope_api_key -> api_keys.dashscope
    - ai_keys 下混合了 image 配置 -> 拆分到 api_keys + ai_image
    - anythingllm.taa_workspace / taw_workspace -> anythingllm.workspace + skill 覆盖
    - taa.kb_path -> localkb.path（如果 localkb.path 已设置则忽略）
    """
    result = {}

    # 1. installation 保持原样
    if "installation" in cfg:
        result["installation"] = cfg["installation"]

    # 2. localkb
    lib = dict(cfg.get("localkb", {}))
    # 旧 taa.kb_path 迁移
    old_taa_kb = _deep_get(cfg, "taa.kb_path")
    if old_taa_kb and not lib.get("path"):
        lib["path"] = old_taa_kb
    result["localkb"] = lib

    # 3. anythingllm — 统一 workspace
    allm = dict(cfg.get("anythingllm", {}))
    # 旧 schema: taa_workspace / taw_workspace -> workspace
    if not allm.get("workspace"):
        # 优先用 taa_workspace（两者共享时相同）
        ws = allm.pop("taa_workspace", None) or allm.pop("taw_workspace", None)
        if ws:
            allm["workspace"] = ws
    else:
        allm.pop("taa_workspace", None)
        allm.pop("taw_workspace", None)
    # 清理非规范 key
    allm.pop("workspace_shared", None)
    allm.pop("claude_config_path", None)
    allm.pop("mcp_server_name", None)
    allm.pop("connected", None)
    result["anythingllm"] = allm

    # 4. api_keys — 从旧 ai_keys 拆出
    old_ai_keys = cfg.get("ai_keys", {})
    api_keys = dict(cfg.get("api_keys", {}))
    # 旧 ark_api_key / dashscope_api_key
    if not api_keys.get("ark"):
        val = old_ai_keys.get("ark_api_key")
        if val is None:
            val = old_ai_keys.get("ark")
        api_keys["ark"] = val
    if not api_keys.get("dashscope"):
        val = old_ai_keys.get("dashscope_api_key")
        if val is None:
            val = old_ai_keys.get("dashscope")
        api_keys["dashscope"] = val
    result["api_keys"] = api_keys

    # 5. ai_image — 从旧 ai_keys 拆出 image 配置
    ai_image = dict(cfg.get("ai_image", {}))
    for img_key in ("default_provider", "size", "max_retries", "timeout"):
        if img_key not in ai_image and img_key in old_ai_keys:
            ai_image[img_key] = old_ai_keys[img_key]
    # 迁移旧 provider_priority 列表 → default_provider 字符串
    if "provider_priority" in ai_image and "default_provider" not in ai_image:
        old_list = ai_image.pop("provider_priority")
        if isinstance(old_list, list) and old_list:
            ai_image["default_provider"] = old_list[0]
    elif "provider_priority" in ai_image:
        ai_image.pop("provider_priority")  # 清理旧字段
    # 填充默认值
    for k, v in DEFAULTS["ai_image"].items():
        if k not in ai_image:
            if isinstance(v, dict):
                ai_image[k] = dict(v)
            else:
                ai_image[k] = v
    # 确保 models 子字典完整（旧配置可能缺少 gemini）
    if "models" in ai_image and isinstance(ai_image["models"], dict):
        for provider, default_model in DEFAULTS["ai_image"]["models"].items():
            if provider not in ai_image["models"]:
                ai_image["models"][provider] = default_model
    result["ai_image"] = ai_image

    # 6. mcp_search
    result["mcp_search"] = cfg.get("mcp_search", dict(DEFAULTS["mcp_search"]))

    # 7. drawio — 规范化 key
    drawio = dict(cfg.get("drawio", {}))
    # 旧 desktop_cli_path -> cli_path
    if not drawio.get("cli_path") and drawio.get("desktop_cli_path"):
        drawio["cli_path"] = drawio.pop("desktop_cli_path")
    elif "desktop_cli_path" in drawio:
        drawio.pop("desktop_cli_path")
    # 保留安装信息
    result["drawio"] = drawio

    # 8. skill 节
    for skill_name in SKILLS:
        skill_cfg = dict(cfg.get(skill_name, {}))
        # 清理旧 key
        skill_cfg.pop("kb_path", None)  # 已迁移到 localkb.path
        result[skill_name] = skill_cfg

    return result


def normalize_file() -> bool:
    """规范化配置文件 schema，返回是否有变更"""
    cfg = _read_yaml(CONFIG_PATH)
    if not cfg:
        return False
    normalized = normalize(cfg)
    if normalized != cfg:
        _write_yaml(CONFIG_PATH, normalized)
        return True
    return False


# ── 核心 API ─────────────────────────────────────────

def load_raw() -> Dict:
    """读取并规范化统一配置文件"""
    cfg = _read_yaml(CONFIG_PATH)
    if not cfg:
        return {}
    return normalize(cfg)


def load(skill: Optional[str] = None) -> Dict:
    """
    加载合并后的配置。

    若指定 skill，返回合并后的 skill 视图：
    全局节作为基底，skill 专属节覆盖同名 key，
    同时将 skill 专属的 anythingllm_workspace（若非 null）覆盖 anythingllm.workspace。
    """
    raw = load_raw()

    if skill is None:
        return raw

    if skill not in SKILLS:
        return raw

    # 构造 skill 视图
    result = {}
    for section in ("localkb", "anythingllm", "api_keys", "ai_image", "mcp_search", "drawio"):
        val = raw.get(section, DEFAULTS.get(section, {}))
        if isinstance(val, dict):
            base = dict(DEFAULTS.get(section, {}))
            base.update({k: v for k, v in val.items() if v is not None})
            result[section] = base
        else:
            result[section] = val

    # skill 专属节
    skill_defaults = dict(DEFAULTS.get(skill, {}))
    skill_section = raw.get(skill, {}) or {}
    skill_defaults.update({k: v for k, v in skill_section.items() if v is not None})
    result[skill] = skill_defaults

    # skill 的 anythingllm_workspace 覆盖全局
    skill_ws = skill_defaults.get("anythingllm_workspace")
    if skill_ws:
        result["anythingllm"]["workspace"] = skill_ws

    return result


def get(skill: str, key: str, default: Any = None) -> Any:
    """
    获取 skill 视角下的配置值。

    查找顺序：
    1. 统一配置 skill 节的 key
    2. 统一配置全局节的 key（支持 dot notation）
    3. 环境变量（特定 key 有映射）
    4. 默认值
    """
    cfg = load(skill)

    # 先在 skill 节查找
    skill_section = cfg.get(skill, {})
    if key in skill_section and skill_section[key] is not None:
        return skill_section[key]

    # 特殊映射：skill 常用 key -> 全局节
    key_mapping = {
        "localkb.path": ("localkb", "path"),
        "kb_path": ("localkb", "path"),
        "anythingllm_workspace": ("anythingllm", "workspace"),
        "anythingllm.workspace": ("anythingllm", "workspace"),
        "anythingllm.base_url": ("anythingllm", "base_url"),
        "anythingllm.enabled": ("anythingllm", "enabled"),
        "api_keys.ark": ("api_keys", "ark"),
        "api_keys.dashscope": ("api_keys", "dashscope"),
        "api_keys.gemini": ("api_keys", "gemini"),
        "mcp_search.priority": ("mcp_search", "priority"),
        "ai_image.default_provider": ("ai_image", "default_provider"),
        "ai_image.size": ("ai_image", "size"),
        "ai_image.timeout": ("ai_image", "timeout"),
        "drawio.cli_path": ("drawio", "cli_path"),
    }

    if key in key_mapping:
        section, subkey = key_mapping[key]
        val = cfg.get(section, {}).get(subkey)
        if val is not None:
            return val

    # dot notation 通用查找
    val = _deep_get(cfg, key)
    if val is not None:
        return val

    # 环境变量 fallback
    env_mapping = {
        "api_keys.ark": "ARK_API_KEY",
        "api_keys.dashscope": "DASHSCOPE_API_KEY",
        "api_keys.gemini": "GEMINI_API_KEY",
        "anythingllm.workspace": "TAA_ANYTHINGLLM_WS" if skill == "taa" else "TAW_ANYTHINGLLM_WS",
    }
    env_key = env_mapping.get(key)
    if env_key:
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val

    return default


def set_value(key: str, value: Any) -> None:
    """写入配置值到统一配置文件（支持 dot notation）"""
    cfg = load_raw()
    _deep_set(cfg, key, value)
    _write_yaml(CONFIG_PATH, cfg)


def show(skill: Optional[str] = None) -> str:
    """格式化输出当前生效配置"""
    cfg = load(skill) if skill else load_raw()

    if not cfg:
        return "未找到配置文件。运行 /twc setup 进行初始配置。"

    lines = []
    if skill:
        lines.append(f"# {skill} 生效配置")
    else:
        lines.append("# Tender Workflow 统一配置")
    lines.append(f"# 配置文件: {CONFIG_PATH}")
    lines.append("")

    # 敏感 key 名集合
    sensitive_keys = {"ark", "dashscope", "gemini", "ark_api_key", "dashscope_api_key", "gemini_api_key", "api_key"}

    def _format(data: Dict, indent: int = 0) -> None:
        prefix = "  " * indent
        for k, v in data.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                _format(v, indent + 1)
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}: [{', '.join(str(i) for i in v)}]")
            elif v is None:
                lines.append(f"{prefix}{k}: (未设置)")
            elif isinstance(v, str) and k in sensitive_keys:
                if len(v) > 8:
                    lines.append(f"{prefix}{k}: {v[:4]}...{v[-4:]}")
                else:
                    lines.append(f"{prefix}{k}: ***")
            else:
                lines.append(f"{prefix}{k}: {v}")

    _format(cfg)
    return "\n".join(lines)


def validate() -> List[str]:
    """验证配置，返回问题列表（空列表 = 全部通过）"""
    issues = []
    cfg = load_raw()

    if not cfg:
        issues.append("配置文件不存在或为空。运行 /twc setup 进行初始配置。")
        return issues

    # 检查 localkb.path
    lib_path = _deep_get(cfg, "localkb.path")
    if lib_path:
        p = Path(lib_path)
        if not p.exists():
            issues.append(f"知识库路径不存在: {lib_path}")
        elif not (p / ".index").exists():
            issues.append(f"知识库索引目录不存在: {lib_path}/.index（可运行 /taa --build-index 构建）")
    else:
        issues.append("localkb.path 未设置")

    # 检查 API keys
    ark = _deep_get(cfg, "api_keys.ark")
    dashscope = _deep_get(cfg, "api_keys.dashscope")
    gemini = _deep_get(cfg, "api_keys.gemini")
    if (not ark and not dashscope and not gemini
            and not os.environ.get("ARK_API_KEY")
            and not os.environ.get("DASHSCOPE_API_KEY")
            and not os.environ.get("GEMINI_API_KEY")):
        issues.append("未配置任何 AI 生图 API Key（api_keys.ark / api_keys.dashscope / api_keys.gemini）")

    # 检查默认供应商对应的 API Key 是否已配置
    default_provider = _deep_get(cfg, "ai_image.default_provider")
    if default_provider:
        env_map = {"ark": "ARK_API_KEY", "dashscope": "DASHSCOPE_API_KEY", "gemini": "GEMINI_API_KEY"}
        key_val = _deep_get(cfg, f"api_keys.{default_provider}") or os.environ.get(env_map.get(default_provider, ""))
        if not key_val:
            issues.append(f"默认 AI 生图供应商 '{default_provider}' 的 API Key 未配置")

    # 检查 AnythingLLM
    allm = cfg.get("anythingllm", {})
    if allm.get("enabled"):
        if not allm.get("workspace"):
            issues.append("AnythingLLM 已启用但未设置 workspace")
        # 检查 MCP Server 是否已注册（~/.claude.json 或全局安装）
        allm_registered = False
        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            try:
                cj = json.loads(claude_json.read_text())
                allm_registered = "anythingllm" in cj.get("mcpServers", {})
            except Exception:
                pass
        if not allm_registered and not shutil.which("mcp-anythingllm"):
            issues.append("mcp-anythingllm 未注册（运行 /twc setup 或手动配置 ~/.claude.json）")

    # 检查 drawio
    drawio_path = _deep_get(cfg, "drawio.cli_path")
    if drawio_path and not Path(drawio_path).exists():
        issues.append(f"draw.io CLI 路径不存在: {drawio_path}")

    return issues


def migrate() -> Dict[str, Any]:
    """
    从旧 per-skill 配置迁移到统一配置文件，然后删除旧文件。
    同时规范化现有统一配置文件的 schema。
    """
    result = {"migrated_keys": [], "deleted_files": [], "skipped": [], "normalized": False}

    cfg = _read_yaml(CONFIG_PATH)

    # 迁移旧 per-skill 配置
    for skill_name, legacy_path in LEGACY_PATHS.items():
        if not legacy_path.exists():
            result["skipped"].append(str(legacy_path))
            continue

        old = _read_yaml(legacy_path)
        if not old:
            legacy_path.unlink()
            result["deleted_files"].append(str(legacy_path))
            continue

        for key, value in old.items():
            if value is None:
                continue

            if key == "kb_path":
                if not _deep_get(cfg, "localkb.path"):
                    _deep_set(cfg, "localkb.path", value)
                    result["migrated_keys"].append(f"{skill_name}.kb_path -> localkb.path")

            elif key == "anythingllm_workspace":
                if not _deep_get(cfg, "anythingllm.workspace"):
                    _deep_set(cfg, "anythingllm.workspace", value)
                    result["migrated_keys"].append(f"{skill_name}.anythingllm_workspace -> anythingllm.workspace")

            elif key == "ark_api_key":
                if not _deep_get(cfg, "api_keys.ark"):
                    _deep_set(cfg, "api_keys.ark", value)
                    result["migrated_keys"].append(f"{skill_name}.ark_api_key -> api_keys.ark")

            elif key == "dashscope_api_key":
                if not _deep_get(cfg, "api_keys.dashscope"):
                    _deep_set(cfg, "api_keys.dashscope", value)
                    result["migrated_keys"].append(f"{skill_name}.dashscope_api_key -> api_keys.dashscope")

            elif key == "ai_image_config":
                if isinstance(value, dict):
                    for sub_k, sub_v in value.items():
                        target_key = f"ai_image.{sub_k}"
                        if not _deep_get(cfg, target_key):
                            _deep_set(cfg, target_key, sub_v)
                            result["migrated_keys"].append(f"{skill_name}.ai_image_config.{sub_k} -> {target_key}")

            elif key == "mcp_search":
                if isinstance(value, dict) and "priority" in value:
                    if not _deep_get(cfg, "mcp_search.priority"):
                        _deep_set(cfg, "mcp_search.priority", value["priority"])
                        result["migrated_keys"].append(f"{skill_name}.mcp_search.priority -> mcp_search.priority")

        # 删除旧配置文件
        legacy_path.unlink()
        result["deleted_files"].append(str(legacy_path))
        try:
            legacy_path.parent.rmdir()
        except OSError:
            pass

    # 规范化现有统一配置
    normalized = normalize(cfg)
    if normalized != cfg:
        result["normalized"] = True
    _write_yaml(CONFIG_PATH, normalized)

    return result


# ── 模型注册表 ──────────────────────────────────────

def _find_models_yaml() -> Optional[Path]:
    """定位 ai_image_models.yaml 文件"""
    # 方式1：相对于本脚本 (tools/tw_config.py -> 项目根)
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / ".claude" / "skills" / "taw" / "prompts" / "ai_image_models.yaml",
        project_root / "skills" / "taw" / "prompts" / "ai_image_models.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    # 方式2：通过 git
    try:
        import subprocess
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        p = Path(root) / ".claude" / "skills" / "taw" / "prompts" / "ai_image_models.yaml"
        if p.exists():
            return p
    except Exception:
        pass
    return None


def _render_models(provider_filter: Optional[str] = None) -> str:
    """读取模型注册表 YAML，渲染固定格式表格"""
    yaml_path = _find_models_yaml()
    if not yaml_path:
        return "错误：未找到模型注册表文件 ai_image_models.yaml"

    registry = _read_yaml(yaml_path)
    if not registry or "providers" not in registry:
        return "错误：模型注册表文件格式异常"

    # 读取当前用户配置的默认模型
    cfg = load_raw()
    user_models = _deep_get(cfg, "ai_image.models") or {}
    user_default_provider = _deep_get(cfg, "ai_image.default_provider") or "ark"

    display = registry.get("display", {})
    status_map = display.get("status_map", {})

    lines = []
    lines.append(display.get("header", "## AI 图片生成模型列表\n").rstrip())
    lines.append("")

    # 默认供应商信息
    lines.append(f"当前默认供应商：**{user_default_provider}**")
    lines.append("")

    lines.append(display.get("table_header", "| 提供商 | 模型 ID | 名称 | 最大分辨率 | 价格 | 特点 | 状态 |"))
    lines.append(display.get("table_separator", "|--------|---------|------|-----------|------|------|------|"))

    providers = registry.get("providers", {})
    for pkey, pdata in providers.items():
        if provider_filter and pkey != provider_filter:
            continue

        pname = pdata.get("name", pkey)
        models = pdata.get("models", [])
        user_default = user_models.get(pkey, "")

        for i, m in enumerate(models):
            mid = m.get("id", "")
            mname = m.get("name", "")
            res = m.get("max_resolution", "")
            price = m.get("price", "")
            features = m.get("features", "")
            status_key = m.get("status", "available")
            status_label = status_map.get(status_key, status_key)

            # 用户配置的默认模型：覆盖注册表状态，显示为"● 当前默认"
            user_default_marker = display.get("user_default_marker", "● 当前默认")
            if mid == user_default:
                status_label = user_default_marker

            # 第一行显示供应商名，后续行留空
            provider_col = pname if i == 0 else ""
            lines.append(f"| {provider_col} | `{mid}` | {mname} | {res} | {price} | {features} | {status_label} |")

    lines.append("")
    lines.append(display.get("footer", "").rstrip())

    # 过期检测：last_updated 超过 90 天时警告
    last_updated = registry.get("last_updated")
    if last_updated:
        try:
            from datetime import datetime, timedelta
            updated_date = datetime.strptime(str(last_updated), "%Y-%m-%d")
            days_ago = (datetime.now() - updated_date).days
            if days_ago > 90:
                lines.append("")
                lines.append(f"> ⚠️ 模型列表最后更新于 {last_updated}（{days_ago} 天前），可能已过期。运行 `/twc models --refresh` 刷新。")
        except (ValueError, TypeError):
            pass

    return "\n".join(lines)


# ── CLI 入口 ─────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 tools/tw_config.py show [skill]")
        print("  python3 tools/tw_config.py get <skill> <key> [default]")
        print("  python3 tools/tw_config.py set <key> <value>")
        print("  python3 tools/tw_config.py validate")
        print("  python3 tools/tw_config.py migrate")
        print("  python3 tools/tw_config.py normalize")
        print("  python3 tools/tw_config.py models [provider]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "show":
        skill = sys.argv[2] if len(sys.argv) > 2 else None
        print(show(skill))

    elif cmd == "get":
        if len(sys.argv) < 4:
            print("用法: python3 tools/tw_config.py get <skill> <key> [default]", file=sys.stderr)
            sys.exit(1)
        skill = sys.argv[2]
        key = sys.argv[3]
        default = sys.argv[4] if len(sys.argv) > 4 else ""
        val = get(skill, key, default)
        if isinstance(val, list):
            print(yaml.dump(val, default_flow_style=True, allow_unicode=True).strip())
        elif isinstance(val, dict):
            print(yaml.dump(val, default_flow_style=False, allow_unicode=True).strip())
        else:
            print(val if val is not None else default)

    elif cmd == "set":
        if len(sys.argv) < 4:
            print("用法: python3 tools/tw_config.py set <key> <value>", file=sys.stderr)
            sys.exit(1)
        key = sys.argv[2]
        value = _parse_value(sys.argv[3])
        set_value(key, value)
        print(f"已设置 {key} = {value}")
        print(f"配置文件: {CONFIG_PATH}")

    elif cmd == "validate":
        issues = validate()
        if not issues:
            print("✅ 配置验证通过")
        else:
            print(f"发现 {len(issues)} 个问题：")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            sys.exit(1)

    elif cmd == "migrate":
        result = migrate()
        if result["migrated_keys"]:
            print("已迁移配置项：")
            for k in result["migrated_keys"]:
                print(f"  {k}")
        if result["deleted_files"]:
            print("已删除旧配置文件：")
            for f in result["deleted_files"]:
                print(f"  {f}")
        if result["normalized"]:
            print("已规范化配置文件 schema")
        if result["skipped"]:
            print("跳过（文件不存在）：")
            for f in result["skipped"]:
                print(f"  {f}")
        if not result["migrated_keys"] and not result["deleted_files"] and not result["normalized"]:
            print("无需迁移：未发现旧配置文件，schema 已规范。")

    elif cmd == "models":
        provider_filter = sys.argv[2] if len(sys.argv) > 2 else None
        print(_render_models(provider_filter))

    elif cmd == "normalize":
        changed = normalize_file()
        if changed:
            print("已规范化配置文件 schema")
            print(show())
        else:
            print("配置文件 schema 已是规范格式，无需变更。")

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
