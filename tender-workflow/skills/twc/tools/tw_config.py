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
# api_keys / ai_image 由 ai-image plugin 管理（~/.config/presales-skills/config.yaml），
# 此处不再持有。
DEFAULTS = {
    "localkb": {"path": None},
    "anythingllm": {"enabled": False, "base_url": "http://localhost:3001", "workspace": None},
    "mcp_search": {"priority": ["tavily_search", "exa_search"]},
    "drawio": {},  # cli_path 字段已废弃（v1.0.0 删 drawio-gen bin 后由 drawio plugin 自定位）；保留空 dict 兼容旧 config
    "taa": {"vendor": "灵雀云", "kb_source": "auto", "anythingllm_workspace": None},
    "taw": {"kb_source": "auto", "image_source": "auto", "anythingllm_workspace": None},
    "tpl": {"default_template": None, "default_level": "standard"},
    "trv": {"default_level": "all"},
}

SKILLS = ("taa", "taw", "tpl", "trv")


def _read_yaml(path: Path) -> Dict:
    """读 yaml：文件不存在返 {}；YAML 解析失败 → 打印友好错误并 sys.exit(1)
    （避免 setup 在坏文件上覆盖丢数据）；其他 OSError 抛出不吞。"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"错误：tender-workflow config YAML 解析失败 ({path}): {e}", file=sys.stderr)
        print(f"  请修复 {path} 后重试（避免 setup 在坏文件上覆盖丢数据）。", file=sys.stderr)
        sys.exit(1)


def _write_yaml(path: Path, data: Dict) -> None:
    """F-021: tmp + os.replace 原子写。半截写入崩溃不会让用户 config 损坏。"""
    import time
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
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
    # F-011: API key 明文存盘的最低权限保护（同机多用户可见性）；非 POSIX FS 失败时 silent 忽略
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


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
    - anythingllm.taa_workspace / taw_workspace -> anythingllm.workspace + skill 覆盖
    - taa.kb_path -> localkb.path（如果 localkb.path 已设置则忽略）
    - ai_keys.ark_api_key / dashscope_api_key 等老老字段 -> api_keys.* 透传
      （api_keys / ai_image 块由 ai-image plugin 管理，但 normalize 仍把超老字段
      映射成规范 api_keys，确保 /ai-image:migrate 能看到密钥不会丢）
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

    # 4. api_keys / ai_image 由 ai-image plugin 管理；normalize 不再持有 schema，
    #    仅做两件事：
    #    (a) 透传现有 api_keys / ai_image 块（让 /ai-image:migrate 看见）
    #    (b) 把超老字段 ai_keys.ark_api_key / dashscope_api_key 映射成 api_keys.*，
    #        防止从未跑过新 schema 的老用户密钥被静默丢
    api_keys = dict(cfg.get("api_keys") or {})
    legacy_ai_keys = cfg.get("ai_keys") or {}
    if isinstance(legacy_ai_keys, dict):
        for legacy_field, target in (
            ("ark_api_key", "ark"),
            ("dashscope_api_key", "dashscope"),
            ("gemini_api_key", "gemini"),
        ):
            if not api_keys.get(target) and legacy_ai_keys.get(legacy_field):
                api_keys[target] = legacy_ai_keys[legacy_field]
    if api_keys:
        result["api_keys"] = api_keys
    if "ai_image" in cfg:
        result["ai_image"] = cfg["ai_image"]
    # 注意：故意不透传 cfg["ai_keys"]——只在上方做一次性 lift。
    # 如果保留 ai_keys 顶层字段，会与 /ai-image:migrate 形成循环：
    # migrate 抽走 api_keys，下次 normalize 又从 ai_keys 重新生成 api_keys。

    # 6. mcp_search
    result["mcp_search"] = cfg.get("mcp_search", dict(DEFAULTS["mcp_search"]))

    # 7. drawio — 规范化 key
    # cli_path 字段已废弃（v1.0.0 删 drawio-gen bin 后 drawio plugin 自定位 CLI）
    # 旧字段 desktop_cli_path / cli_path 保留兼容性 strip：normalize 时自动剥离
    drawio = dict(cfg.get("drawio", {}))
    drawio.pop("desktop_cli_path", None)
    drawio.pop("cli_path", None)
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

    注意：skill 视图**不包含** api_keys / ai_image 块（这两块由 ai-image plugin 管理）；
    `get(skill, "api_keys.ark")` 走 deep_get 兜底，正常返回 default。如需访问这两块，
    使用 `load_raw()` 拿透传后的原始字段（仅供 /ai-image:migrate 检测残留），
    或调用 ai-image plugin 的入口。
    """
    raw = load_raw()

    if skill is None:
        return raw

    if skill not in SKILLS:
        return raw

    # 构造 skill 视图
    result = {}
    for section in ("localkb", "anythingllm", "mcp_search", "drawio"):
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
    # api_keys.* / ai_image.* 由 ai-image plugin 管理，不在此处暴露
    key_mapping = {
        "localkb.path": ("localkb", "path"),
        "kb_path": ("localkb", "path"),
        "anythingllm_workspace": ("anythingllm", "workspace"),
        "anythingllm.workspace": ("anythingllm", "workspace"),
        "anythingllm.base_url": ("anythingllm", "base_url"),
        "anythingllm.enabled": ("anythingllm", "enabled"),
        "mcp_search.priority": ("mcp_search", "priority"),
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
        "anythingllm.workspace": "TAA_ANYTHINGLLM_WS" if skill == "taa" else "TAW_ANYTHINGLLM_WS",
    }
    env_key = env_mapping.get(key)
    if env_key:
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val

    return default


def set_value(key: str, value: Any) -> None:
    """写入配置值到统一配置文件（支持 dot notation）。

    F-310：不走 load_raw / normalize，避免 normalize 副作用（清理 anythingllm 子字段、
    lift ai_keys 等）混入只设一个 key 的简单操作；schema 整体规范化只在显式
    `normalize` / `migrate` 命令时发生。
    """
    if key.startswith(("api_keys.", "ai_image.")) or key in ("api_keys", "ai_image"):
        raise ValueError(
            f"'{key}' 由 ai-image plugin 管理，不在 tender-workflow config 范围内。\n"
            f"请改用：/ai-image:set {key} <value>"
        )
    cfg = _read_yaml(CONFIG_PATH)
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

    # AI 生图配置由 ai-image plugin 管理；轻量检查 ~/.config/presales-skills/config.yaml 是否存在
    ai_image_cfg = Path.home() / ".config" / "presales-skills" / "config.yaml"
    if not ai_image_cfg.exists():
        issues.append(
            "AI 生图配置文件不存在（~/.config/presales-skills/config.yaml）。"
            "如需配图请运行 /ai-image:setup"
        )
    elif "api_keys" in cfg or "ai_image" in cfg:
        issues.append(
            "~/.config/tender-workflow/config.yaml 仍包含 api_keys / ai_image 块（由 ai-image plugin 管理）。"
            "请运行 /ai-image:migrate 整理"
        )

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
            issues.append("AnythingLLM MCP 未注册（安装独立 plugin：/plugin install anythingllm-mcp@presales-skills）")

    # 检查 drawio：cli_path 字段已废弃（v1.0.0 后 drawio plugin 自定位 CLI）
    drawio_path = _deep_get(cfg, "drawio.cli_path")
    if drawio_path:
        issues.append("drawio.cli_path 字段已废弃（drawio plugin 自定位 CLI），建议运行 normalize 自动清理")

    return issues


def migrate() -> Dict[str, Any]:
    """
    从旧 per-skill 配置迁移到统一配置文件，然后删除旧文件。
    同时规范化现有统一配置文件的 schema。
    """
    # F-041: 推荐顺序提示
    print(
        "提示：跑完此命令后，建议跑 /ai-image:migrate 把 tw 配置合并到统一的 presales-skills 路径。",
        file=sys.stderr,
    )
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
        try:
            set_value(key, value)
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
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
            print(
                "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
                "如需测试 API 连通性，请触发实际生成（自然语言：'生成图片：test'）",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
            "如需测试 API 连通性，请触发实际生成（自然语言：'生成图片：test'）",
            file=sys.stderr,
        )

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
        # v1.0.0：原 shutil.which("ai-image-config") orphan caller（commit c983037 删 bin 后失效）。
        # 改为重定向到 ai-image plugin 的对应 skill 直接调用。
        print(
            "[tender-workflow] 子命令 'models' 已转交给 ai-image plugin。\n"
            "请运行 Skill(skill=\"ai-image:gen\") 子命令 models，\n"
            "或自然语言触发：'列出图片模型'。",
            file=sys.stderr,
        )
        sys.exit(0)

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
