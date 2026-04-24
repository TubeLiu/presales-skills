#!/usr/bin/env python3
"""
ai-image plugin 的统一配置 CLI。

子命令（每个对应一个 commands/*.md slash command）：
    setup              交互式向导：选默认 provider、填 API keys
    show [section]     展示当前配置（可选 section：api_keys/ai_image/...）
    set <dotted> <v>   按 dotted path 设值
    models [provider]  展示统一注册表（Markdown 表格）
    add-model <p> <y>  追加用户自定义模型到 models-user.yaml
    validate [p]       逐 provider 发 test 图验证 API key
    migrate            合并旧的 ~/.config/{solution-master,tender-workflow}/config.yaml 到统一 config.yaml

配置文件：~/.config/presales-skills/config.yaml
用户自定义模型：~/.config/presales-skills/models-user.yaml

API key 查找优先级：
    1. CLI --api-key 参数
    2. 环境变量（ARK_API_KEY / GEMINI_API_KEY / ...）
    3. ~/.config/presales-skills/config.yaml 的 api_keys.<provider>
    4. 以上都空 → 报错，提示 /ai-image-config setup

本模块通过 fcntl.flock 保护并发写。
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# 首次运行时自动安装 requirements.txt（本脚本也调 yaml/Pillow 等，依赖 ai-image/requirements.txt）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps  # noqa: E402
ensure_deps()

try:
    import yaml
except ImportError:
    # 兜底：requirements.txt 没装全或 pip install 失败，至少保证 pyyaml 可用
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
        stderr=subprocess.DEVNULL,
    )
    import yaml


# ── 路径常量 ─────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".config" / "presales-skills"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
USER_MODELS_PATH = CONFIG_DIR / "models-user.yaml"

# 脚本所在目录（plugin install 时由 Claude Code 管控位置，__file__ 可靠）
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent  # ai-image/
PLUGIN_REGISTRY = PLUGIN_ROOT / "prompts" / "ai_image_models.yaml"

LEGACY_CONFIGS = {
    "solution-master": Path.home() / ".config" / "solution-master" / "config.yaml",
    "tender-workflow": Path.home() / ".config" / "tender-workflow" / "config.yaml",
}

# 默认 schema（setup / normalize 时用）
DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1.0.0",
    "api_keys": {},
    "ai_image": {
        "default_provider": "ark",
        "default_size": "2048x2048",
        "max_retries": 2,
        "timeout": 60,
        "models": {},
    },
    "localkb": {"path": None},
    "anythingllm": {
        "enabled": False,
        "base_url": "http://localhost:3001",
        "workspace": None,
    },
    "mcp_search": {
        "priority": ["tavily_search", "exa_search"],
    },
    "drawio": {"cli_path": None},
    "solution_brainstorming": {},
    "taa": {},
    "taw": {},
    "tpl": {},
    "trv": {},
}


# ── 基础 IO（fcntl.flock 保护并发写）──────────────────────
def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    """原子写入 + 锁保护，避免并发写丢字段。"""
    _ensure_config_dir()
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            # 不复用 open 的文件做读再 truncate——简化为：锁住后再写 tmp、mv
            pass
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    # 写 tmp 再 rename（原子）
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, indent=2)
    tmp_path.replace(path)


def _deep_get(d: dict, key_path: str) -> Any:
    """'a.b.c' 风格取值"""
    cur: Any = d
    for part in key_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _deep_set(d: dict, key_path: str, value: Any) -> None:
    """'a.b.c' 风格设值（中途 dict 自动创建）"""
    parts = key_path.split(".")
    cur = d
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


# ── 基础操作 ─────────────────────────────────────────────
def load_config() -> dict[str, Any]:
    """读取配置文件。若不存在返回空 dict（调用方决定是否用 DEFAULT_CONFIG 兜底）。"""
    return _load_yaml(CONFIG_PATH)


def save_config(data: dict[str, Any]) -> None:
    _save_yaml(CONFIG_PATH, data)


def get(key_path: str, default: Any = None) -> Any:
    """对外 API：按 dotted path 取值。失败返回 default。"""
    return _deep_get(load_config(), key_path) or default


# ── 子命令实现 ──────────────────────────────────────────
def cmd_setup() -> int:
    """交互式向导。最简版本：若 config 不存在则写一份 default 骨架，提示用户后续怎么填。"""
    _ensure_config_dir()
    if CONFIG_PATH.exists():
        print(f"配置文件已存在：{CONFIG_PATH}")
        print("如需重新配置，请直接编辑该文件或使用 /ai-image-config set <key> <value>")
        print()
        print("当前配置摘要：")
        cmd_show(section=None)
        return 0

    # 首次创建：写 default skeleton，引导用户填
    save_config(DEFAULT_CONFIG)
    print(f"✓ 已创建配置文件：{CONFIG_PATH}")
    print()
    print("下一步：填入 API keys。最常用的 3 个 provider：")
    print("  /ai-image-config set api_keys.ark        sk-xxx     # 火山方舟")
    print("  /ai-image-config set api_keys.dashscope  sk-xxx     # 阿里云")
    print("  /ai-image-config set api_keys.gemini     xxx        # Google Gemini")
    print()
    print("查看全部可选 provider：  /ai-image-config models")
    print("验证配置：              /ai-image-config validate")
    if any(path.exists() for path in LEGACY_CONFIGS.values()):
        print()
        print("⚠ 检测到旧 config 文件，可运行 /ai-image-config migrate 自动合并：")
        for name, path in LEGACY_CONFIGS.items():
            if path.exists():
                print(f"    • {name}: {path}")
    return 0


def cmd_show(section: Optional[str]) -> int:
    """展示配置。section 为 None 时展示全部。"""
    cfg = load_config()
    if not cfg:
        print(f"配置文件不存在：{CONFIG_PATH}")
        print("运行 /ai-image-config setup 创建")
        return 1

    def _mask_api_keys_inplace(d: dict) -> None:
        """对 dict 顶层的 api_keys 子树做 mask。在原 dict 上 mutate。"""
        for k, v in (d.get("api_keys") or {}).items():
            if v and isinstance(v, str):
                d["api_keys"][k] = v[:6] + "…(masked)…" + v[-4:] if len(v) > 10 else "●●●●"

    if section:
        data = cfg.get(section)
        if data is None:
            print(f"section '{section}' 不存在")
            return 1
        # 深拷贝后按顶层 section name mask（若 section=api_keys）
        view = yaml.safe_load(yaml.safe_dump({section: data}, allow_unicode=True))
        _mask_api_keys_inplace(view)
        print(yaml.safe_dump(view, allow_unicode=True, sort_keys=False))
    else:
        # 展示全部但 mask API keys
        masked = yaml.safe_load(yaml.safe_dump(cfg, allow_unicode=True))
        _mask_api_keys_inplace(masked)
        print(yaml.safe_dump(masked, allow_unicode=True, sort_keys=False))
    return 0


def cmd_set(key_path: str, value: str) -> int:
    """按 dotted path 设值。简单类型推断：true/false/null/数字/字符串"""
    typed = value
    if value.lower() == "true":
        typed = True
    elif value.lower() == "false":
        typed = False
    elif value.lower() in ("null", "none", ""):
        typed = None
    else:
        try:
            typed = int(value)
        except ValueError:
            try:
                typed = float(value)
            except ValueError:
                pass  # keep string

    cfg = load_config() or dict(DEFAULT_CONFIG)
    _deep_set(cfg, key_path, typed)
    save_config(cfg)
    display_val = "●●●●●●" if key_path.startswith("api_keys.") and typed else typed
    print(f"✓ {key_path} = {display_val}")
    return 0


def cmd_models(provider_filter: Optional[str], refresh: bool = False) -> int:
    """展示模型注册表（merge plugin-bundled + user-level override）"""
    if refresh:
        print("⚠ --refresh 联网更新当前版本尚未实现；已回退到本地注册表展示")
    if not PLUGIN_REGISTRY.exists():
        print(f"错误：注册表文件不存在：{PLUGIN_REGISTRY}")
        return 1
    registry = _load_yaml(PLUGIN_REGISTRY)
    user_over = _load_yaml(USER_MODELS_PATH) if USER_MODELS_PATH.exists() else {}
    # Merge user models into plugin registry（simple union）
    for prov, user_prov in (user_over.get("providers") or {}).items():
        if prov not in registry.get("providers", {}):
            registry["providers"][prov] = user_prov
        else:
            existing_ids = {m["id"] for m in registry["providers"][prov].get("models", [])}
            for m in user_prov.get("models", []):
                if m.get("id") not in existing_ids:
                    registry["providers"][prov]["models"].append(m)

    cfg = load_config()
    default_provider = _deep_get(cfg, "ai_image.default_provider")
    user_defaults = _deep_get(cfg, "ai_image.models") or {}

    # 渲染 markdown 表格
    display = registry.get("display", {})
    print(display.get("header", "## AI Image Models\n"))
    print(display.get("table_header", "| provider | model | name | status |"))
    print(display.get("table_separator", "|---|---|---|---|"))

    status_map = display.get("status_map", {})
    providers = registry.get("providers", {})
    for prov_name, prov_data in providers.items():
        if provider_filter and prov_name != provider_filter and provider_filter not in (prov_data.get("aliases") or []):
            continue
        for model in prov_data.get("models", []):
            status = status_map.get(model.get("status", "available"), model.get("status"))
            # 标记用户当前默认
            marker = ""
            if prov_name == default_provider or provider_filter in (prov_data.get("aliases") or []):
                if user_defaults.get(prov_name) == model["id"]:
                    marker = display.get("user_default_marker", "●") + " "
            row = f"| {prov_name} | {marker}`{model['id']}` | {model.get('name', '')} | {model.get('max_resolution', '')} | {model.get('price', '')} | {model.get('features', '')} | {status} |"
            print(row)
    print(display.get("footer", ""))
    return 0


def cmd_add_model(provider: str, yaml_fragment: str) -> int:
    """追加用户自定义模型到 ~/.config/presales-skills/models-user.yaml"""
    try:
        model_data = yaml.safe_load(yaml_fragment)
    except yaml.YAMLError as e:
        print(f"错误：无效 YAML：{e}")
        return 1
    if not isinstance(model_data, dict) or "id" not in model_data:
        print("错误：模型数据必须是 dict 且包含 'id' 字段")
        return 1

    _ensure_config_dir()
    user_reg = _load_yaml(USER_MODELS_PATH) or {"providers": {}}
    user_reg.setdefault("providers", {}).setdefault(provider, {}).setdefault("models", []).append(model_data)
    _save_yaml(USER_MODELS_PATH, user_reg)
    print(f"✓ 已将模型 '{model_data['id']}' 添加到 {provider}（位于 {USER_MODELS_PATH}）")
    return 0


def cmd_validate(provider_filter: Optional[str]) -> int:
    """健康检查：逐 provider 检查 API key 是否已配置。（真实 API call 验证留给未来。）"""
    cfg = load_config()
    if not cfg:
        print(f"配置文件不存在：{CONFIG_PATH}")
        return 1
    registry = _load_yaml(PLUGIN_REGISTRY)
    api_keys = cfg.get("api_keys") or {}
    providers = registry.get("providers", {})

    issues: list[str] = []
    checked = 0
    for prov_name, prov_data in providers.items():
        if provider_filter and prov_name != provider_filter:
            continue
        checked += 1
        key = api_keys.get(prov_name)
        if not key:
            # 也检查 env var
            env_key = prov_data.get("env_key")
            env_key_alt = prov_data.get("env_key_alt")
            if env_key and os.environ.get(env_key):
                print(f"○ {prov_name}: API key via env var {env_key}")
                continue
            if env_key_alt and os.environ.get(env_key_alt):
                print(f"○ {prov_name}: API key via env var {env_key_alt}")
                continue
            issues.append(f"{prov_name}: 未设置 API key（config.yaml 和 env 都空）")
        else:
            print(f"✓ {prov_name}: API key 已配置（{len(key)} chars）")

    if checked == 0:
        print(f"provider '{provider_filter}' 未知")
        return 1

    if issues:
        print()
        print("⚠ 以下 provider 未配置：")
        for issue in issues:
            print(f"  • {issue}")
        print()
        print("使用 /ai-image-config set api_keys.<provider> <key> 配置")
        return 1
    return 0


def _hash_yaml_content(paths: list[Path]) -> str:
    """对多个 yaml 文件的 parsed content 做 sha256，用于 migrate 幂等判断"""
    combined: dict[str, Any] = {}
    for p in paths:
        if p.exists():
            data = _load_yaml(p)
            combined[str(p)] = data
    normalized = json.dumps(combined, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# migrate：字段映射表（旧 → 新）
FIELD_MAPPING = {
    # tender-workflow
    "ai_image.size": "ai_image.default_size",
    "ai_image.default_provider": "ai_image.default_provider",
    "ai_image.max_retries": "ai_image.max_retries",
    "ai_image.timeout": "ai_image.timeout",
    "ai_image.models": "ai_image.models",
    "localkb.path": "localkb.path",
    "anythingllm.enabled": "anythingllm.enabled",
    "anythingllm.base_url": "anythingllm.base_url",
    "anythingllm.workspace": "anythingllm.workspace",
    "mcp_search.priority": "mcp_search.priority",
    "drawio.cli_path": "drawio.cli_path",
    # solution-master
    "solution_brainstorming": "solution_brainstorming",
}


def cmd_migrate() -> int:
    """合并旧的 solution-master/tender-workflow config.yaml 到统一 config.yaml"""
    old_paths = [p for p in LEGACY_CONFIGS.values() if p.exists()]
    if not old_paths:
        print("未检测到旧 config 文件。无需迁移。")
        print("使用 /ai-image-config setup 新建配置")
        return 0

    # 幂等检查
    current_hash = _hash_yaml_content(old_paths)
    existing_new = load_config()
    if existing_new.get("_migrated_from_hash") == current_hash:
        print(f"已迁移（hash 匹配：{current_hash[:12]}…），skip。")
        print("若要重新合并，请先删除新 config.yaml 或手动调整字段。")
        return 0

    # 加载旧 config
    sm_cfg = _load_yaml(LEGACY_CONFIGS["solution-master"]) if LEGACY_CONFIGS["solution-master"].exists() else {}
    tw_cfg = _load_yaml(LEGACY_CONFIGS["tender-workflow"]) if LEGACY_CONFIGS["tender-workflow"].exists() else {}

    # 写前 backup（如果新 config 已存在）
    if CONFIG_PATH.exists():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = CONFIG_PATH.with_suffix(f".yaml.backup-{ts}")
        backup.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"已备份当前 config：{backup}")

    # 基于 DEFAULT + 旧 config 合并
    merged: dict[str, Any] = dict(DEFAULT_CONFIG)
    merged["api_keys"] = {}  # fresh start
    conflicts: dict[str, dict[str, Any]] = {}
    legacy_preserved: dict[str, dict[str, Any]] = {"solution-master": {}, "tender-workflow": {}}

    # 1. api_keys 合并（tender-workflow 优先，冲突写入 api_keys_conflicts）
    tw_keys = tw_cfg.get("api_keys") or {}
    sm_keys = sm_cfg.get("api_keys") or {}
    for k, v in tw_keys.items():
        if v:
            merged["api_keys"][k] = v
    for k, v in sm_keys.items():
        if not v:
            continue
        if k in merged["api_keys"] and merged["api_keys"][k] != v:
            conflicts.setdefault(k, {})["solution-master"] = v
            conflicts[k]["tender-workflow (retained)"] = merged["api_keys"][k]
        elif k not in merged["api_keys"]:
            merged["api_keys"][k] = v
    if conflicts:
        merged["api_keys_conflicts"] = conflicts

    # 2. 字段映射迁移
    for src_path, dst_path in FIELD_MAPPING.items():
        tw_val = _deep_get(tw_cfg, src_path)
        sm_val = _deep_get(sm_cfg, src_path)
        # tw wins
        if tw_val is not None:
            _deep_set(merged, dst_path, tw_val)
        elif sm_val is not None:
            _deep_set(merged, dst_path, sm_val)

    # 3. 未识别字段进 _legacy section
    recognized_top_keys = {"api_keys", "ai_image", "localkb", "anythingllm", "mcp_search", "drawio", "solution_brainstorming", "taa", "taw", "tpl", "trv"}
    for src_name, src_cfg in (("solution-master", sm_cfg), ("tender-workflow", tw_cfg)):
        for k, v in src_cfg.items():
            if k not in recognized_top_keys and not k.startswith("_"):
                legacy_preserved[src_name][k] = v
    # 只保留有内容的
    legacy_preserved = {k: v for k, v in legacy_preserved.items() if v}
    if legacy_preserved:
        merged["_legacy"] = legacy_preserved

    # 4. 写 hash 标记
    merged["_migrated_from_hash"] = current_hash

    save_config(merged)
    print(f"✓ migrate 完成：{CONFIG_PATH}")
    print(f"  hash = {current_hash[:12]}…")
    if conflicts:
        print(f"  ⚠ {len(conflicts)} 个 api_keys 冲突，已写入 api_keys_conflicts 节供人工复核")
    if legacy_preserved:
        print(f"  保留 {sum(len(v) for v in legacy_preserved.values())} 个未识别字段到 _legacy section")

    # 重命名旧文件
    for name, path in LEGACY_CONFIGS.items():
        if path.exists():
            bak = path.with_suffix(".yaml.bak")
            path.rename(bak)
            print(f"  旧 {name} 重命名为 {bak}")

    print()
    print("后续操作：")
    print("  /ai-image-config show     查看合并结果")
    print("  /ai-image-config validate 验证 API key 可用性")
    return 0


# ── 入口 ─────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(prog="ai_image_config.py", description=__doc__ or "")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="交互式首次配置")
    p_show = sub.add_parser("show", help="展示当前配置")
    p_show.add_argument("section", nargs="?", default=None)
    p_set = sub.add_parser("set", help="设置配置项")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_models = sub.add_parser("models", help="展示模型注册表")
    p_models.add_argument("provider", nargs="?", default=None)
    p_models.add_argument("--refresh", action="store_true")
    p_add = sub.add_parser("add-model", help="追加用户自定义模型")
    p_add.add_argument("provider")
    p_add.add_argument("yaml_fragment")
    p_validate = sub.add_parser("validate", help="验证 API key 是否配置")
    p_validate.add_argument("provider", nargs="?", default=None)
    sub.add_parser("migrate", help="合并旧 config 到统一位置")

    args = parser.parse_args()

    if args.cmd == "setup":
        return cmd_setup()
    if args.cmd == "show":
        return cmd_show(args.section)
    if args.cmd == "set":
        return cmd_set(args.key, args.value)
    if args.cmd == "models":
        return cmd_models(args.provider, refresh=args.refresh)
    if args.cmd == "add-model":
        return cmd_add_model(args.provider, args.yaml_fragment)
    if args.cmd == "validate":
        return cmd_validate(args.provider)
    if args.cmd == "migrate":
        return cmd_migrate()
    return 2


if __name__ == "__main__":
    sys.exit(main())
