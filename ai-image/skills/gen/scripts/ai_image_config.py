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
    4. 以上都空 → 报错，提示用户运行 `ai_image_config.py setup`

本模块通过 tmp 文件 + 原子 rename 保护配置写入；Windows 下 rename 遇到目标被占用时重试一次。
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
import time
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
# v1.0.0：prompts/ 与 requirements.txt 已迁入 skill 内部（与 scripts/ 同处 skill root，1 级 parent）。
# 旧名 PLUGIN_ROOT 改名为 SKILL_DIR，反映新 layout。
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_REGISTRY = SKILL_DIR / "prompts" / "ai_image_models.yaml"

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
    "drawio": {},  # cli_path 已废弃（v1.0.0 删 drawio-gen bin 后由 drawio plugin 自定位）；与 sm_config / tw_config 一致
    "solution_brainstorming": {},
    "taa": {},
    "taw": {},
    "tpl": {},
    "trv": {},
}


# ── 基础 IO（原子 tmp + rename 写入，跨平台）──────────────────────
def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _safe_load(path: Path, ctx_name: str = "") -> dict[str, Any]:
    """读 yaml 的统一入口：文件不存在返 {}；YAML 解析失败时给可读错误并 sys.exit(1)。
    其他 OSError（权限/IO）抛出不吞——让调用方决定。
    """
    if not path.exists():
        return {}
    try:
        return _load_yaml(path)
    except yaml.YAMLError as e:
        ctx = f"{ctx_name} " if ctx_name else ""
        print(f"错误：{ctx}config YAML 解析失败 ({path}): {e}", file=sys.stderr)
        print(f"  请修复 {path} 后重试。", file=sys.stderr)
        sys.exit(1)


def _chmod_600(path: Path) -> None:
    """API key 明文文件最低权限保护（F-011）；F-030 失败时 stderr warn。"""
    try:
        os.chmod(path, 0o600)
    except OSError as e:
        sys.stderr.write(
            f"[ai_image_config] WARN: chmod 0600 failed on {path}: {e}\n"
            f"  config 文件含 API keys 明文，但权限保护未启用（同机多用户可见）。\n"
            f"  常见原因：Windows NTFS / FAT / SMB 等非 POSIX 文件系统。\n"
        )


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    _ensure_config_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, indent=2)
    # Windows: MoveFileEx 遇到目标被另一进程占用会 PermissionError，重试一次
    for attempt in range(2):
        try:
            tmp_path.replace(path)
            break
        except PermissionError:
            if attempt == 0:
                time.sleep(0.1)
            else:
                raise
    # F-011: API key 明文存盘的最低权限保护（同机多用户可见性）
    # F-030: 失败时 stderr warn（之前 silent pass），让 Windows / 异构 FS 用户能感知
    try:
        os.chmod(path, 0o600)
    except OSError as e:
        sys.stderr.write(
            f"[ai_image_config] WARN: chmod 0600 failed on {path}: {e}\n"
            f"  config 文件含 API keys 明文，但权限保护未启用。\n"
        )


def _mask_api_key(value: str) -> str:
    """Industry-standard 4+4 mask. Used by cmd_show / cmd_migrate (F-014) / cmd_set."""
    if not isinstance(value, str) or not value:
        return value
    if len(value) >= 8:
        return value[:4] + "***" + value[-4:]
    return "***"


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
    """读取配置文件。若不存在返回空 dict（调用方决定是否用 DEFAULT_CONFIG 兜底）。
    YAML 解析失败时给可读错误并 sys.exit(1)，避免 traceback 让 cmd_show/validate/set/setup 无法 debug。
    """
    return _safe_load(CONFIG_PATH, "presales-skills")


def save_config(data: dict[str, Any]) -> None:
    _save_yaml(CONFIG_PATH, data)


def get(key_path: str, default: Any = None) -> Any:
    """对外 API：按 dotted path 取值。失败返回 default。"""
    return _deep_get(load_config(), key_path) or default


# ── 子命令实现 ──────────────────────────────────────────
def cmd_setup() -> int:
    """交互式向导。
    - 若新 config 不存在但旧 config（solution-master / tender-workflow）含 api_keys：自动 migrate。
    - 若新 config 存在但 api_keys 为空 + 旧 config 有 api_keys：自动 migrate（避免用户手工 setup 写空骨架后 ark key 永远丢）。
    - 否则若新 config 不存在：写 default 骨架。
    - 否则：展示当前配置摘要。
    """
    _ensure_config_dir()

    # ===== auto-migrate 兜底（v2.9 PASS 修订）=====
    new_keys_empty = True
    if CONFIG_PATH.exists():
        try:
            existing = _load_yaml(CONFIG_PATH)
            new_keys_empty = not (existing.get("api_keys") or {})
        except yaml.YAMLError:
            new_keys_empty = True  # 坏 yaml 视作空，让 migrate 处理
    legacy_with_keys = []
    for name, path in LEGACY_CONFIGS.items():
        if not path.exists():
            continue
        try:
            sibling = _load_yaml(path)
        except yaml.YAMLError:
            continue
        if (sibling.get("api_keys") or {}) or (sibling.get("ai_image") or {}) or (sibling.get("ai_keys") or {}):
            legacy_with_keys.append((name, path))
    if (not CONFIG_PATH.exists() or new_keys_empty) and legacy_with_keys:
        print("[setup] 检测到旧版本 config 含可迁移内容（或新 config api_keys 为空）：")
        for name, path in legacy_with_keys:
            print(f"    • {name}: {path}")
        print("[setup] 自动调用 migrate 合并到统一路径...")
        print()
        rc = cmd_migrate()
        if rc == 0:
            print()
            print(f"[setup] 迁移完成。已合并到 {CONFIG_PATH}")
            print("[setup] 检查配置：python3 ai_image_config.py show")
            print("[setup] 验证 API keys：python3 ai_image_config.py validate")
        return rc
    # ===== auto-migrate 兜底结束 =====

    if CONFIG_PATH.exists():
        print(f"配置文件已存在：{CONFIG_PATH}")
        print("如需重新配置，请直接编辑该文件或运行：python3 ai_image_config.py set <key> <value>")
        print()
        print("当前配置摘要：")
        cmd_show(section=None)
        return 0

    # 首次创建：写 default skeleton，引导用户填（deepcopy 避免后续修改污染常量）
    save_config(copy.deepcopy(DEFAULT_CONFIG))
    print(f"✓ 已创建配置文件：{CONFIG_PATH}")
    print()
    print("下一步：填入 API keys。最常用的 3 个 provider：")
    print("  python3 ai_image_config.py set api_keys.ark        sk-xxx     # 火山方舟")
    print("  python3 ai_image_config.py set api_keys.dashscope  sk-xxx     # 阿里云")
    print("  python3 ai_image_config.py set api_keys.gemini     xxx        # Google Gemini")
    print()
    print("查看全部可选 provider：  python3 ai_image_config.py models")
    print("验证配置：              python3 ai_image_config.py validate")
    return 0


def cmd_show(section: Optional[str]) -> int:
    """展示配置。section 为 None 时展示全部。"""
    cfg = load_config()
    if not cfg:
        print(f"配置文件不存在：{CONFIG_PATH}")
        print(f'运行 "python3 {__file__} setup" 创建')
        return 1

    def _mask_api_keys_inplace(d: dict) -> None:
        """对 dict 顶层的 api_keys 子树做 mask（复用 module-level _mask_api_key，F-014）。
        同时 mask migrate 写入的 api_keys_conflicts 块，避免 cmd_show 打印明文密钥。"""
        for k, v in (d.get("api_keys") or {}).items():
            d["api_keys"][k] = _mask_api_key(v)
        for prov, sources in (d.get("api_keys_conflicts") or {}).items():
            if isinstance(sources, dict):
                for src, val in sources.items():
                    sources[src] = _mask_api_key(val)

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


def cmd_set(key_path: str, value: str, force: bool = False) -> int:
    """按 dotted path 设值。简单类型推断：true/false/null/数字/字符串

    F-052: api_keys.* 长度 < 4 警告（仍写入，warn-only；--force 跳过警告）
    """
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

    # F-052: API key 长度校验（warn-only，不阻塞写入）
    if (
        key_path.startswith("api_keys.")
        and isinstance(typed, str)
        and len(typed) < 4
        and not force
    ):
        print(
            f"⚠  {key_path} 的值长度 {len(typed)} 字符，看起来不像合法 API key。"
            f"已写入；下次加 --force 可消除此提示。",
            file=sys.stderr,
        )

    cfg = load_config() or copy.deepcopy(DEFAULT_CONFIG)
    _deep_set(cfg, key_path, typed)
    save_config(cfg)
    display_val = _mask_api_key(typed) if key_path.startswith("api_keys.") and isinstance(typed, str) and typed else typed
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
    print(display.get("table_header", "| provider | model | name | max_resolution | price | features | status |"))
    print(display.get("table_separator", "|---|---|---|---|---|---|---|"))

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
    """健康检查：逐 provider 检查 API key 是否已配置。（真实 API call 验证留给未来。）

    F-028: 末尾打印提示，明示本命令不验证 API key 真实可用性。
    """
    cfg = load_config()
    if not cfg:
        print(f"配置文件不存在：{CONFIG_PATH}")
        return 1
    if not PLUGIN_REGISTRY.exists():
        print(f"错误：注册表文件不存在：{PLUGIN_REGISTRY}", file=sys.stderr)
        print("  这通常是 plugin 安装不完整或 SKILL_DIR 路径解析有误（旧称 PLUGIN_ROOT）。", file=sys.stderr)
        return 1
    registry = _load_yaml(PLUGIN_REGISTRY)
    api_keys = cfg.get("api_keys") or {}
    providers = registry.get("providers", {})

    if not providers:
        print(f"错误：注册表 {PLUGIN_REGISTRY} 中无 providers 字段或为空。", file=sys.stderr)
        return 1

    if provider_filter and provider_filter not in providers:
        known = ", ".join(sorted(providers.keys()))
        print(f"错误：provider '{provider_filter}' 不在注册表中。", file=sys.stderr)
        print(f"  已知 provider: {known}", file=sys.stderr)
        return 1

    issues: list[str] = []
    for prov_name, prov_data in providers.items():
        if provider_filter and prov_name != provider_filter:
            continue
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

    if issues:
        print()
        print("⚠ 以下 provider 未配置：")
        for issue in issues:
            print(f"  • {issue}")
        print()
        print(f'运行 "python3 {__file__} set api_keys.<provider> <key>" 配置')
        print(
            "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
            "如需测试 API 连通性，请触发实际生成（如 image-gen \"test\" -o /tmp/）",
            file=sys.stderr,
        )
        return 1
    print(
        "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
        "如需测试 API 连通性，请触发实际生成（如 image-gen \"test\" -o /tmp/）",
        file=sys.stderr,
    )
    return 0


def cmd_migrate() -> int:
    """从 ~/.config/{solution-master,tender-workflow}/config.yaml 抽取 api_keys 和
    ai_image 两个块到 ~/.config/presales-skills/config.yaml；之后从源文件移除这两个
    块（仅这两个块——cdp_sites / taa / taw / tpl / trv / localkb / anythingllm /
    drawio 等 plugin 专属字段不动）。

    AI 生图配置由 ai-image plugin 管理；solution-master 与 tender-workflow 不再持有
    api_keys 和 ai_image，本命令负责一次性把这两个块的内容整理到 ai-image plugin 的
    config 文件。
    """
    sm_path = LEGACY_CONFIGS["solution-master"]
    tw_path = LEGACY_CONFIGS["tender-workflow"]
    sm_cfg = _safe_load(sm_path, "solution-master")
    tw_cfg = _safe_load(tw_path, "tender-workflow")

    # Lift 超老字段 ai_keys.{ark,dashscope,gemini}_api_key → api_keys.*，避免与
    # tw_config.normalize 形成循环（normalize 会 lift 后 validate 报"残留"，但
    # 本命令若不识别 ai_keys 则原文件没 api_keys 即跳过——密钥静默丢）。
    def _lift_legacy_ai_keys(cfg: dict) -> None:
        legacy = cfg.get("ai_keys")
        if not isinstance(legacy, dict):
            return
        cfg.setdefault("api_keys", {})
        for legacy_field, target in (
            ("ark_api_key", "ark"),
            ("dashscope_api_key", "dashscope"),
            ("gemini_api_key", "gemini"),
        ):
            v = legacy.get(legacy_field)
            if v and not cfg["api_keys"].get(target):
                cfg["api_keys"][target] = v

    _lift_legacy_ai_keys(sm_cfg)
    _lift_legacy_ai_keys(tw_cfg)

    sm_has = any(k in sm_cfg for k in ("api_keys", "ai_image", "ai_keys"))
    tw_has = any(k in tw_cfg for k in ("api_keys", "ai_image", "ai_keys"))
    if not sm_has and not tw_has:
        print("solution-master 与 tender-workflow 的 config 中均无 api_keys / ai_image / ai_keys 块；无需处理。")
        return 0

    # 1. 加载 presales-skills/config.yaml
    # - 已存在：保留所有现有值（包括用户主动设的字段）；只填补缺失字段
    # - 不存在：以最小骨架起步，避免 DEFAULT_CONFIG 的占位值挡住 sm/tw 真实数据
    new_cfg = load_config() or {}
    # 每轮重新构造 api_keys_conflicts：避免上一轮残留与当前实际冲突状态不一致
    new_cfg.pop("api_keys_conflicts", None)
    new_cfg.setdefault("api_keys", {})
    new_cfg.setdefault("ai_image", {})
    new_cfg["ai_image"].setdefault("models", {})

    # 2. 合并 api_keys —— 优先级：presales-skills 现有值 > tw > sm
    conflicts: dict[str, dict[str, Any]] = {}

    def _absorb_keys(src_name: str, src_keys: dict) -> None:
        for k, v in src_keys.items():
            if not v:
                continue
            existing = new_cfg["api_keys"].get(k)
            if existing and existing != v:
                conflicts.setdefault(k, {"presales-skills (retained)": existing})[src_name] = v
            elif not existing:
                new_cfg["api_keys"][k] = v

    _absorb_keys("tender-workflow", tw_cfg.get("api_keys") or {})
    _absorb_keys("solution-master", sm_cfg.get("api_keys") or {})

    if conflicts:
        print(f"⚠ 检测到 {len(conflicts)} 个 api_keys 冲突（保留 presales-skills 已有值，差异写入 api_keys_conflicts）：", file=sys.stderr)
        for k, sources in conflicts.items():
            for src, val in sources.items():
                print(f"  - api_keys.{k} from {src}: {_mask_api_key(val)}", file=sys.stderr)
        print(f"  如需采用其他来源的值，请手工编辑 {CONFIG_PATH}", file=sys.stderr)
        new_cfg["api_keys_conflicts"] = conflicts

    # 3. 合并 ai_image —— 只填补 None / 缺失字段；绝不覆盖 presales-skills 已有非空值
    def _absorb_ai_image(src_ai: dict) -> None:
        for k, v in src_ai.items():
            if v is None:
                continue
            target = "default_size" if k == "size" else k  # F-027 旧字段 rename
            if target == "models" and isinstance(v, dict):
                for prov, model_id in v.items():
                    new_cfg["ai_image"]["models"].setdefault(prov, model_id)
            elif new_cfg["ai_image"].get(target) is None:
                new_cfg["ai_image"][target] = v

    _absorb_ai_image(tw_cfg.get("ai_image") or {})
    _absorb_ai_image(sm_cfg.get("ai_image") or {})

    # 4. 备份并写回 presales-skills/config.yaml
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if CONFIG_PATH.exists():
        backup = CONFIG_PATH.parent / f"{CONFIG_PATH.name}.backup-{ts}"
        backup.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        _chmod_600(backup)  # F-011: backup 含明文 API key，同步收 0o600
        print(f"已备份 {CONFIG_PATH}：{backup.name}")
    save_config(new_cfg)
    print(f"✓ api_keys + ai_image 合并到 {CONFIG_PATH}")

    # 5. prune 源 config 中的 api_keys / ai_image / ai_keys 三个顶层块（备份原文件，不删其他键）
    #    ai_keys 也清掉，避免老用户 normalize 后再生 api_keys 形成循环
    pruned_any = False
    for name, path, cfg in (("solution-master", sm_path, sm_cfg), ("tender-workflow", tw_path, tw_cfg)):
        if not path.exists():
            continue
        # 注意：cfg 此时已被 _lift_legacy_ai_keys 修改过（含 lifted api_keys），
        # 但 backup 用的是 path 的原始磁盘内容（path.read_text），保留 lift 前状态
        if not any(k in cfg for k in ("api_keys", "ai_image", "ai_keys")):
            continue
        backup = path.parent / f"{path.name}.backup-{ts}"
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        _chmod_600(backup)
        pruned = {k: v for k, v in cfg.items() if k not in ("api_keys", "ai_image", "ai_keys")}
        _save_yaml(path, pruned)
        print(f"  ✓ {name}: 备份到 {backup.name}，已从原文件移除 api_keys / ai_image / ai_keys 块")
        pruned_any = True

    if pruned_any:
        print(
            "注：YAML 注释、字段顺序、multi-document 结构在 yaml.safe_load+safe_dump 处理后会丢失；"
            "如需保留请手工对照 .backup-* 备份恢复。",
            file=sys.stderr,
        )

    print()
    print("后续操作：")
    print(f'  python3 {__file__} show       # 查看合并结果')
    print(f'  python3 {__file__} validate   # 验证 API key 配置完整性')
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
    p_set.add_argument("--force", action="store_true", help="F-052: 跳过 API key 长度校验警告")
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
        return cmd_set(args.key, args.value, force=args.force)
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
