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
# v1.0.0 起两份 _SKILL_DIR 计算一致（都 1 级 parent）；仍需人工 sync 核心逻辑。
# 本脚本是依赖 bootstrap 入口，不能依赖第三方包（portalocker / filelock 等）。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# _ensure_deps.py 位于 ppt-master/skills/make/scripts/
# v1.0.0：requirements.txt 已迁入 skill 内部（与 scripts/ 同处 skill root，1 级 parent）。
# 旧名 _PLUGIN_ROOT 改名为 _SKILL_DIR，与 ai-image 同款 layout（旧两份 parent 深度差异已消除）。
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPTS_DIR.parent
_REQ = _SKILL_DIR / "requirements.txt"
_MARKER = _SKILL_DIR / ".deps-installed"
_LOCK = _SKILL_DIR / ".deps-installing.lock"

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
