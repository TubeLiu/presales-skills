"""ai-image plugin 的依赖自动化安装 bootstrap。

入口脚本（image_gen.py / ai_image_config.py / ...）在最开头 import 并调用：

    from _ensure_deps import ensure_deps
    ensure_deps()

逻辑：
  1. 读同目录的 `../requirements.txt`
  2. 存在 marker 文件（<plugin_root>/.deps-installed）则 skip
  3. 否则调用 `sys.executable -m pip install -r <requirements.txt>`
  4. 成功后 touch marker；失败打印警告但不 abort（让脚本继续，由其自身 ImportError 暴露具体缺哪个包）

Marker 位于 plugin 根目录。plugin 升级时由于 cache dir 路径带 version（如
~/.claude/plugins/cache/presales-skills/ai-image/0.1.3/），marker 不会跨版本继承，
自动触发新 requirements 的重装。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT = _SCRIPTS_DIR.parent
_REQ = _PLUGIN_ROOT / "requirements.txt"
_MARKER = _PLUGIN_ROOT / ".deps-installed"

# 允许环境变量强制跳过（CI、容器、用户已手动管理依赖等场景）
_SKIP_ENV = "PRESALES_SKILLS_SKIP_AUTO_INSTALL"


def ensure_deps(quiet: bool = True) -> None:
    """Install requirements.txt once per plugin version. Idempotent."""
    if os.environ.get(_SKIP_ENV):
        return
    if _MARKER.exists() or not _REQ.exists():
        return

    print(
        f"[{_PLUGIN_ROOT.name}] First-time setup: installing Python dependencies from {_REQ.name}…",
        file=sys.stderr,
    )
    args = [sys.executable, "-m", "pip", "install", "-r", str(_REQ)]
    if quiet:
        args.append("--quiet")

    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError as e:
        print(
            f"[{_PLUGIN_ROOT.name}] WARN: pip install failed (exit {e.returncode}). "
            f"Run manually: pip install -r {_REQ}",
            file=sys.stderr,
        )
        print(
            f"  Set {_SKIP_ENV}=1 to suppress this attempt on future runs.",
            file=sys.stderr,
        )
        return

    try:
        _MARKER.touch()
    except OSError:
        # 缓存目录可能只读（极端场景）；不 fatal，仅下次会重试
        pass

    print(f"[{_PLUGIN_ROOT.name}] Dependencies installed.", file=sys.stderr)


if __name__ == "__main__":
    ensure_deps(quiet=False)
