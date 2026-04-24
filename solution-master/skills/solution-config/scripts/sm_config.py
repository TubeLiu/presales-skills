#!/usr/bin/env python3
"""
Solution Master 统一配置管理工具

配置文件：~/.config/solution-master/config.yaml
支持 CLI 调用和 Python import 两种方式。

CLI 用法：
    python3 sm_config.py show
    python3 sm_config.py get <key> [default]
    python3 sm_config.py set <key> <value>
    python3 sm_config.py validate
    python3 sm_config.py models [provider]
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

CONFIG_PATH = Path.home() / ".config" / "solution-master" / "config.yaml"

# 路径定位：从脚本位置反推，适配所有 solution-master 安装模式
# - plugin 模式：<plugin_root>/skills/solution-config/scripts/sm_config.py
# - npx 项目模式：<project>/.claude/skills/solution-config/scripts/sm_config.py
# - npx 全局模式：~/.claude/skills/solution-config/scripts/sm_config.py
# 在每种模式下 _SKILLS_ROOT 都正确指向当前安装的 skills 目录，可用于
# sibling skill 查找（如 _SKILLS_ROOT / "drawio" / "SKILL.md"）。
_SCRIPTS_DIR = Path(__file__).resolve().parent          # .../scripts/
_SKILL_DIR = _SCRIPTS_DIR.parent                        # .../solution-config/
_SKILLS_ROOT = _SKILL_DIR.parent                        # .../skills/

# 规范 schema：所有配置段的默认值
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
    "cdp_sites": {"enabled": False, "sites": []},
    "drawio": {"cli_path": None},
}


def _read_yaml(path: Path) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"配置文件解析失败 {path}: {e}")
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


# ── 核心 API ─────────────────────────────────────────

def load() -> Dict:
    """读取统一配置文件，缺失项补默认值"""
    cfg = _read_yaml(CONFIG_PATH)
    # 补充默认值
    for section, defaults in DEFAULTS.items():
        if section not in cfg:
            cfg[section] = dict(defaults) if isinstance(defaults, dict) else defaults
        elif isinstance(defaults, dict) and isinstance(cfg[section], dict):
            for k, v in defaults.items():
                if k not in cfg[section]:
                    cfg[section][k] = dict(v) if isinstance(v, dict) else v
    return cfg


def get(key: str, default: Any = None) -> Any:
    """
    获取配置值。

    查找顺序：
    1. 配置文件（支持 dot notation）
    2. 环境变量（特定 key 有映射）
    3. 默认值
    """
    cfg = load()

    # dot notation 通用查找
    val = _deep_get(cfg, key)
    if val is not None:
        return val

    # 环境变量 fallback
    env_mapping = {
        "api_keys.ark": "ARK_API_KEY",
        "api_keys.dashscope": "DASHSCOPE_API_KEY",
        "api_keys.gemini": "GEMINI_API_KEY",
        "anythingllm.workspace": "SM_ANYTHINGLLM_WS",
    }
    env_key = env_mapping.get(key)
    if env_key:
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val

    return default


def set_value(key: str, value: Any) -> None:
    """写入配置值到统一配置文件（支持 dot notation）"""
    cfg = load()
    _deep_set(cfg, key, value)
    _write_yaml(CONFIG_PATH, cfg)


def show() -> str:
    """格式化输出当前生效配置"""
    cfg = load()

    if not cfg:
        return "未找到配置文件。运行 /solution-config setup 进行初始配置。"

    lines = []
    lines.append("# Solution Master 配置")
    lines.append(f"# 配置文件: {CONFIG_PATH}")
    lines.append("")

    # 敏感 key 名集合
    sensitive_keys = {"ark", "dashscope", "gemini"}

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
    cfg = load()

    if not cfg:
        issues.append("配置文件不存在或为空。运行 /solution-config setup 进行初始配置。")
        return issues

    # 检查 localkb.path
    lib_path = _deep_get(cfg, "localkb.path")
    if lib_path:
        p = Path(lib_path)
        if not p.exists():
            issues.append(f"知识库路径不存在: {lib_path}")
        elif not (p / ".index").exists():
            issues.append(f"知识库索引目录不存在: {lib_path}/.index（可运行 kb_indexer.py --scan 构建）")
    else:
        issues.append("localkb.path 未设置（可选，但建议配置以启用本地知识库检索）")

    # 检查 API keys
    ark = _deep_get(cfg, "api_keys.ark")
    dashscope = _deep_get(cfg, "api_keys.dashscope")
    gemini = _deep_get(cfg, "api_keys.gemini")
    if (not ark and not dashscope and not gemini
            and not os.environ.get("ARK_API_KEY")
            and not os.environ.get("DASHSCOPE_API_KEY")
            and not os.environ.get("GEMINI_API_KEY")):
        issues.append("未配置任何 AI 生图 API Key（api_keys.ark / dashscope / gemini）——可选，但建议至少配置一个")

    # 检查默认供应商对应的 API Key
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
        allm_registered = False
        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            try:
                cj = json.loads(claude_json.read_text())
                allm_registered = "anythingllm" in cj.get("mcpServers", {})
            except Exception:
                pass
        if not allm_registered and not shutil.which("mcp-anythingllm"):
            issues.append("mcp-anythingllm 未注册（运行 /solution-config setup 或手动配置 ~/.claude.json）")

    # 检查 CDP 站点配置
    cdp = cfg.get("cdp_sites", {})
    if cdp.get("enabled"):
        sites = cdp.get("sites", [])
        if not sites:
            issues.append("cdp_sites 已启用但未配置任何站点（运行 /solution-config setup 添加站点）")
        else:
            for i, site in enumerate(sites):
                if not site.get("name"):
                    issues.append(f"cdp_sites.sites[{i}] 缺少 name 字段")
                if not site.get("search_url"):
                    issues.append(f"cdp_sites.sites[{i}] 缺少 search_url 字段")
                elif "{query}" not in site.get("search_url", ""):
                    issues.append(f"cdp_sites.sites[{i}].search_url 中缺少 {{query}} 占位符")
        # 检查 web-access skill 是否可用
        # 优先 sibling-skill 查找（_SKILLS_ROOT 在所有安装模式下都正确），
        # 再回退到用户全局目录以兼容 "插件安装 + 用户额外自定义全局 skill" 场景
        wa_candidates = [
            _SKILLS_ROOT / "web-access" / "SKILL.md",
            Path.home() / ".claude" / "skills" / "web-access" / "SKILL.md",
        ]
        if not any(p.exists() for p in wa_candidates):
            issues.append("web-access skill 未安装（CDP 站点检索依赖此 skill）")

    # 检查 drawio plugin 是否已随 umbrella marketplace 安装
    # drawio 自 Milestone C 起已抽为独立 plugin；solution-master/skills/drawio/ 不再存在
    # 候选位置：
    #   1. Umbrella marketplace sibling：_SKILLS_ROOT.parent.parent / "drawio" / "skills" / "drawio" / "SKILL.md"
    #   2. 用户 home 全局安装：~/.claude/skills/drawio/SKILL.md
    drawio_candidates = [
        _SKILLS_ROOT.parent.parent / "drawio" / "skills" / "drawio" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "drawio" / "SKILL.md",
    ]
    drawio_skill_installed = any(p.exists() for p in drawio_candidates)

    if not drawio_skill_installed:
        issues.append("drawio plugin 未安装（架构图/流程图将降级为 AI 生成）。请执行 /plugin install drawio@presales-skills")
    else:
        # skill 已安装时才检查 CLI 配置
        drawio_path = _deep_get(cfg, "drawio.cli_path")
        if drawio_path and not Path(drawio_path).exists():
            issues.append(f"draw.io CLI 路径不存在: {drawio_path}")
        elif not drawio_path:
            issues.append("draw.io skill 已安装但 CLI 路径未配置（drawio.cli_path），.drawio 文件无法自动导出为 PNG")

    return issues


# ── 模型注册表 ──────────────────────────────────────

def _find_models_yaml() -> Optional[Path]:
    """定位 ai_image_models.yaml 文件"""
    candidates = [
        _SKILLS_ROOT / "solution-writing" / "prompts" / "ai_image_models.yaml",
        _SKILLS_ROOT / "image-generation" / "prompts" / "ai_image_models.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _render_models(provider_filter: Optional[str] = None) -> str:
    """读取模型注册表 YAML，渲染固定格式表格"""
    yaml_path = _find_models_yaml()
    if not yaml_path:
        return "错误：未找到模型注册表文件 ai_image_models.yaml"

    registry = _read_yaml(yaml_path)
    if not registry or "providers" not in registry:
        return "错误：模型注册表文件格式异常"

    cfg = load()
    user_models = _deep_get(cfg, "ai_image.models") or {}
    user_default_provider = _deep_get(cfg, "ai_image.default_provider") or "ark"

    display = registry.get("display", {})
    status_map = display.get("status_map", {})

    lines = []
    lines.append(display.get("header", "## AI 图片生成模型列表\n").rstrip())
    lines.append("")
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
            if mid == user_default:
                status_label = display.get("user_default_marker", "● 当前默认")
            provider_col = pname if i == 0 else ""
            lines.append(f"| {provider_col} | `{mid}` | {mname} | {res} | {price} | {features} | {status_label} |")

    lines.append("")
    lines.append(display.get("footer", "").rstrip())

    last_updated = registry.get("last_updated")
    if last_updated:
        try:
            from datetime import datetime
            updated_date = datetime.strptime(str(last_updated), "%Y-%m-%d")
            days_ago = (datetime.now() - updated_date).days
            if days_ago > 90:
                lines.append("")
                lines.append(f"> 模型列表最后更新于 {last_updated}（{days_ago} 天前），可能已过期。运行 `/solution-config models --refresh` 刷新。")
        except (ValueError, TypeError):
            pass

    return "\n".join(lines)


# ── CLI 入口 ─────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 sm_config.py show")
        print("  python3 sm_config.py get <key> [default]")
        print("  python3 sm_config.py set <key> <value>")
        print("  python3 sm_config.py validate")
        print("  python3 sm_config.py models [provider]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "show":
        print(show())

    elif cmd == "get":
        if len(sys.argv) < 3:
            print("用法: python3 sm_config.py get <key> [default]", file=sys.stderr)
            sys.exit(1)
        key = sys.argv[2]
        default = sys.argv[3] if len(sys.argv) > 3 else ""
        val = get(key, default)
        if isinstance(val, list):
            print(yaml.dump(val, default_flow_style=True, allow_unicode=True).strip())
        elif isinstance(val, dict):
            print(yaml.dump(val, default_flow_style=False, allow_unicode=True).strip())
        else:
            print(val if val is not None else default)

    elif cmd == "set":
        if len(sys.argv) < 4:
            print("用法: python3 sm_config.py set <key> <value>", file=sys.stderr)
            sys.exit(1)
        key = sys.argv[2]
        value = _parse_value(sys.argv[3])
        set_value(key, value)
        print(f"已设置 {key} = {value}")
        print(f"配置文件: {CONFIG_PATH}")

    elif cmd == "validate":
        issues = validate()
        if not issues:
            print("配置验证通过")
        else:
            print(f"发现 {len(issues)} 个问题：")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            sys.exit(1)

    elif cmd == "models":
        provider_filter = sys.argv[2] if len(sys.argv) > 2 else None
        print(_render_models(provider_filter))

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
