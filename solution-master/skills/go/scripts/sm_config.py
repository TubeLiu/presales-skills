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
    python3 sm_config.py migrate              # 转发到 ai_image_config.py migrate
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
# api_keys / ai_image 由 ai-image plugin 管理（~/.config/presales-skills/config.yaml），
# 此处不再持有。
DEFAULTS = {
    "localkb": {"path": None},
    "anythingllm": {"enabled": False, "base_url": "http://localhost:3001", "workspace": None},
    "mcp_search": {"priority": ["tavily_search", "exa_search"]},
    "cdp_sites": {"enabled": False, "sites": []},
    "drawio": {},  # F-035: cli_path 字段已废弃（drawio-gen 自定位 CLI），从 DEFAULTS 移除以避免 setup 写入旧字段
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
    # F-011: API key 明文存盘的最低权限保护（同机多用户可见性）
    # F-030: 失败时 stderr warn（之前 silent pass），让 Windows / 异构 FS 用户能感知
    try:
        os.chmod(path, 0o600)
    except OSError as e:
        sys.stderr.write(
            f"[sm_config] WARN: chmod 0600 failed on {path}: {e}\n"
            f"  config 文件含 API keys 明文，但权限保护未启用（同机多用户可见）。\n"
            f"  常见原因：Windows NTFS / FAT / SMB 等非 POSIX 文件系统。\n"
        )


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
    if key.startswith(("api_keys.", "ai_image.")) or key in ("api_keys", "ai_image"):
        raise ValueError(
            f"'{key}' 由 ai-image plugin 管理，不在 solution-master config 范围内。\n"
            f"请改用：{_ai_image_script('ai_image_config.py')} set {key} <value>"
        )
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

    # 敏感 key 名集合（F-024：原仅 3 个，扩到全 13 ai-image provider 覆盖）
    sensitive_keys = {
        "ark", "dashscope", "gemini",                    # 原 3 个
        "openai", "minimax", "stability", "bfl",         # F-024 扩展
        "ideogram", "zhipu", "siliconflow",
        "fal", "replicate", "openrouter",
    }

    # F-024 兜底：父节点是 api_keys 时，其下任意 string 子节点都视为敏感（防漏覆盖
    # 用户自定义 provider 名）。沿调用链传 path 实现。
    def _is_sensitive(path_segs: list, k: str) -> bool:
        if k in sensitive_keys:
            return True
        if path_segs and path_segs[-1] == "api_keys":
            return True
        return False

    def _format(data: Dict, indent: int = 0, path_segs: list = None) -> None:
        path_segs = path_segs or []
        prefix = "  " * indent
        for k, v in data.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                _format(v, indent + 1, path_segs + [k])
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}: [{', '.join(str(i) for i in v)}]")
            elif v is None:
                lines.append(f"{prefix}{k}: (未设置)")
            elif isinstance(v, str) and _is_sensitive(path_segs, k):
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

    # AI 生图配置由 ai-image plugin 管理；轻量检查 ~/.config/presales-skills/config.yaml 是否存在
    ai_image_cfg = Path.home() / ".config" / "presales-skills" / "config.yaml"
    if not ai_image_cfg.exists():
        issues.append(
            "AI 生图配置文件不存在（~/.config/presales-skills/config.yaml）。"
            f"如需配图请运行：{_ai_image_script('ai_image_config.py')} setup"
        )
    elif "api_keys" in cfg or "ai_image" in cfg:
        issues.append(
            "~/.config/solution-master/config.yaml 仍包含 api_keys / ai_image 块（由 ai-image plugin 管理）。"
            f"请运行：{_ai_image_script('ai_image_config.py')} migrate"
        )

    # 检查 AnythingLLM
    allm = cfg.get("anythingllm", {})
    if allm.get("enabled"):
        if not allm.get("workspace"):
            issues.append("AnythingLLM 已启用但未设置 workspace")
        if not is_plugin_installed("anythingllm-mcp"):
            issues.append("AnythingLLM MCP 未注册（安装独立 plugin：/plugin install anythingllm-mcp@presales-skills）")

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
        if not is_plugin_installed("web-access"):
            issues.append("web-access plugin 未安装（CDP 站点检索依赖此 plugin）。请执行 /plugin install web-access@presales-skills")

    # 检查 drawio plugin 是否已随 umbrella marketplace 安装
    if not is_plugin_installed("drawio"):
        # F-035: 删除"降级为 AI 生成"的错误承诺（SKILL 没实现此分支）
        issues.append("drawio plugin 未安装（架构图/流程图功能将不可用）。请执行 /plugin install drawio@presales-skills")
    else:
        # F-035: drawio.cli_path 字段已废弃（drawio-gen 自定位 CLI）；deprecation warn 提示用户从 config 删除
        drawio_path_legacy = _deep_get(cfg, "drawio.cli_path")
        if drawio_path_legacy:
            issues.append(
                "drawio.cli_path 字段已废弃（drawio-gen 自定位 CLI），请从 config.yaml 中删除"
            )

    return issues


# ── Plugin 探针 ─────────────────────────────────────────
# v1.0.0 删除了所有 bin/ 目录后，跨 plugin 检测从 PATH 探针（如 `command -v
# web-access-check`）改为文件存在性探针。三种安装形态：
#   - 本地 marketplace（in-place 加载）：<monorepo_root>/<plugin>/...
#   - 远程 marketplace cache：~/.claude/plugins/cache/*/<plugin>/<version>/...
#   - 用户 home 全局：~/.claude/plugins/<plugin>/...

# 各 plugin 的 marker 相对路径（marker 必须是 plugin 安装后必然存在的文件）
_PLUGIN_MARKERS: Dict[str, str] = {
    "web-access": "skills/browse/SKILL.md",
    "drawio": "skills/draw/SKILL.md",
    "anythingllm-mcp": "tools/mcp-anythingllm/index.js",
    "ai-image": "skills/gen/SKILL.md",
    "ppt-master": "skills/make/SKILL.md",
    "tender-workflow": "skills/twc/SKILL.md",
    "solution-master": "skills/go/SKILL.md",
}


def _plugin_marker_candidates(plugin_name: str) -> List[Path]:
    """所有可能的 marker 路径（不判存在）；exposed for find_plugin_skill_dir 复用。"""
    marker_rel = _PLUGIN_MARKERS.get(plugin_name)
    if not marker_rel:
        return []
    candidates = [
        # 1. 本地 marketplace sibling（_SKILLS_ROOT.parent.parent = monorepo 根）
        _SKILLS_ROOT.parent.parent / plugin_name / marker_rel,
        # 2. 用户 home 全局
        Path.home() / ".claude" / "plugins" / plugin_name / marker_rel,
    ]
    cache_dir = Path.home() / ".claude" / "plugins" / "cache"
    if cache_dir.exists():
        # 3. 远程 marketplace cache（版本号在路径里，glob 匹配）
        candidates.extend(cache_dir.glob(f"*/{plugin_name}/*/{marker_rel}"))
    return candidates


def is_plugin_installed(plugin_name: str) -> bool:
    """检测指定 plugin 是否已通过任何形态安装。"""
    if any(p.exists() for p in _plugin_marker_candidates(plugin_name)):
        return True
    # anythingllm-mcp 的特殊 fallback：顶层 mcpServers fuzzy key + PATH executable
    # （Claude Code 装了 anythingllm-mcp plugin 会注册成
    # `plugin_anythingllm-mcp_anythingllm` 前缀，不是裸 `anythingllm` key）
    if plugin_name == "anythingllm-mcp":
        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            try:
                cj = json.loads(claude_json.read_text())
                if any("anythingllm" in k.lower() for k in cj.get("mcpServers", {})):
                    return True
            except Exception:
                pass
        if shutil.which("mcp-anythingllm"):
            return True
    return False


def find_plugin_skill_dir(plugin_name: str) -> Optional[Path]:
    """返回 plugin 已安装的 SKILL.md 所在目录（SKILL_DIR）；未装返回 None。

    用于在错误提示里给出可直接执行的绝对路径，避免错位的"对 Claude 说 X"
    自指提示——AI 在脚本上下文看到自指指令会困惑。
    """
    for marker in _plugin_marker_candidates(plugin_name):
        if marker.exists():
            return marker.parent
    return None


def _ai_image_script(script_name: str) -> str:
    """返回 ai-image plugin 内某脚本的可执行命令字符串（用于错误提示）。"""
    skill_dir = find_plugin_skill_dir("ai-image")
    if skill_dir:
        return f'python3 "{skill_dir}/scripts/{script_name}"'
    return f'python3 "<ai-image-skill-dir>/scripts/{script_name}"（ai-image plugin 未安装：/plugin install ai-image@presales-skills）'


# ── CLI 入口 ─────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 sm_config.py show")
        print("  python3 sm_config.py get <key> [default]")
        print("  python3 sm_config.py set <key> <value>")
        print("  python3 sm_config.py validate")
        print("  python3 sm_config.py check-plugin <plugin-name>")
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
            print("配置验证通过")
        else:
            print(f"发现 {len(issues)} 个问题：")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            print(
                "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
                f"如需测试 API 连通性，请触发实际生成（{_ai_image_script('image_gen.py')} \"test\" -o /tmp/）",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "注：本命令仅检查配置字段格式与必填项，不验证 API key 是否真实可用；"
            f"如需测试 API 连通性，请触发实际生成（{_ai_image_script('image_gen.py')} \"test\" -o /tmp/）",
            file=sys.stderr,
        )

    elif cmd == "check-plugin":
        if len(sys.argv) < 3:
            print("用法: python3 sm_config.py check-plugin <plugin-name>", file=sys.stderr)
            print(f"可选 plugin: {', '.join(sorted(_PLUGIN_MARKERS))}", file=sys.stderr)
            sys.exit(2)
        pname = sys.argv[2]
        if pname not in _PLUGIN_MARKERS:
            print(f"未知 plugin: {pname}", file=sys.stderr)
            print(f"可选: {', '.join(sorted(_PLUGIN_MARKERS))}", file=sys.stderr)
            sys.exit(2)
        if is_plugin_installed(pname):
            print(f"{pname}: installed")
            sys.exit(0)
        else:
            print(f"{pname}: not installed", file=sys.stderr)
            sys.exit(1)

    elif cmd in ("models", "migrate"):
        # v1.0.0：原 shutil.which("ai-image-config") orphan caller（commit c983037 删 bin 后失效）。
        # 重定向到 ai-image plugin 的 ai_image_config.py（带探针解析的绝对路径，
        # 用户能复制即跑、AI 能直接 subprocess）。
        print(
            f"[solution-master] 子命令 {cmd!r} 已转交给 ai-image plugin。\n"
            f"请运行：{_ai_image_script('ai_image_config.py')} {cmd}",
            file=sys.stderr,
        )
        sys.exit(0)

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
