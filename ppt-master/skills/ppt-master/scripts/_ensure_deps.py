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

F-013：跨进程锁（.deps-installing.lock）防止并发首次调用打架。

# TODO(F-051): 两份 _ensure_deps.py（ai-image + ppt-master）后续考虑抽公共 lib。
# 注意：两份的 _PLUGIN_ROOT 计算路径深度不同（ai-image: 1 级 parent；ppt-master: 3 级 parent）。
# 改任一份的核心逻辑必须人工 sync 到另一份；不可机械 copy 整段。
# 本脚本是依赖 bootstrap 入口，不能依赖第三方包（portalocker / filelock 等）。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# _ensure_deps.py 位于 ppt-master/skills/ppt-master/scripts/
# PLUGIN_ROOT = 3 个 parent 上去（scripts → ppt-master → skills → ppt-master plugin 根）
_SCRIPTS_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT = _SCRIPTS_DIR.parent.parent.parent
_REQ = _PLUGIN_ROOT / "requirements.txt"
_MARKER = _PLUGIN_ROOT / ".deps-installed"
_LOCK = _PLUGIN_ROOT / ".deps-installing.lock"

_SKIP_ENV = "PRESALES_SKILLS_SKIP_AUTO_INSTALL"


def ensure_deps(quiet: bool = True) -> None:
    """Install requirements.txt once per plugin version. Idempotent + concurrent-safe."""
    if os.environ.get(_SKIP_ENV):
        return
    if _MARKER.exists() or not _REQ.exists():
        return

    # F-013: 跨进程锁。原子创建 lock；冲突时轮询等 marker 出现
    lock_acquired = False
    try:
        fd = os.open(str(_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
        lock_acquired = True
    except FileExistsError:
        # 另一进程在装；轮询 30s 等 marker 出现
        for _ in range(60):
            time.sleep(0.5)
            if _MARKER.exists():
                return
            try:
                age = time.time() - _LOCK.stat().st_mtime
                if age > 300:  # 5 分钟 stale → 强制清理，让本进程兜底
                    _LOCK.unlink(missing_ok=True)
                    break
            except OSError:
                pass
        else:
            print(
                f"[ppt-master] WARN: 锁等待 30s 超时，可能另一进程卡住未清理。"
                f"继续无锁尝试 install 兜底（pip 内部锁会兜底，worst case 二者都成功 install 同一份依赖，幂等）。",
                file=sys.stderr,
            )
            # fall-through 到 install（不 return，本进程接管）
    except (OSError, PermissionError):
        # 只读 cache / 权限不足 → fall-through 无锁 install
        pass

    try:
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
    finally:
        if lock_acquired:
            try:
                _LOCK.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    ensure_deps(quiet=False)
