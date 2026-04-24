"""ppt-master 的依赖自动化安装 bootstrap。

每个入口脚本在最开头插入：

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))  # 或父目录（子目录脚本）
    from _ensure_deps import ensure_deps
    ensure_deps()

首次调用时读 ppt-master 根目录的 `requirements.txt`，pip install 全部依赖，touch 一个
marker 文件跳过后续调用。升级 plugin（cache dir 带 version 号）时 marker 不继承，自动
重装新版依赖。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# _ensure_deps.py 位于 ppt-master/skills/ppt-master/scripts/
# PLUGIN_ROOT = 3 个 parent 上去（scripts → ppt-master → skills → ppt-master plugin 根）
_SCRIPTS_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT = _SCRIPTS_DIR.parent.parent.parent
_REQ = _PLUGIN_ROOT / "requirements.txt"
_MARKER = _PLUGIN_ROOT / ".deps-installed"

_SKIP_ENV = "PRESALES_SKILLS_SKIP_AUTO_INSTALL"


def ensure_deps(quiet: bool = True) -> None:
    """Install requirements.txt once per plugin version. Idempotent."""
    if os.environ.get(_SKIP_ENV):
        return
    if _MARKER.exists() or not _REQ.exists():
        return

    print(
        f"[ppt-master] First-time setup: installing Python dependencies from {_REQ.name}…",
        file=sys.stderr,
    )
    args = [sys.executable, "-m", "pip", "install", "-r", str(_REQ)]
    if quiet:
        args.append("--quiet")

    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError as e:
        print(
            f"[ppt-master] WARN: pip install failed (exit {e.returncode}). "
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
        pass

    print(f"[ppt-master] Dependencies installed.", file=sys.stderr)


if __name__ == "__main__":
    ensure_deps(quiet=False)
