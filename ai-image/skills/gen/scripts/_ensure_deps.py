"""ai-image plugin 的依赖自动化安装 bootstrap。

入口脚本（image_gen.py / ai_image_config.py / ...）在最开头 import 并调用：

    from _ensure_deps import ensure_deps
    ensure_deps()

逻辑：
  1. 读同目录的 `../requirements.txt`
  2. 存在 marker 文件（<plugin_root>/.deps-installed）则 skip
  3. 拿 .deps-installing.lock 排他锁（F-013，避免并发调用打架）
  4. 调用 `sys.executable -m pip install -r <requirements.txt>`
  5. 成功后 touch marker；失败打印警告但不 abort（让脚本继续，由其自身 ImportError 暴露具体缺哪个包）

Marker 位于 plugin 根目录。plugin 升级时由于 cache dir 路径带 version（如
~/.claude/plugins/cache/presales-skills/ai-image/0.1.3/），marker 不会跨版本继承，
自动触发新 requirements 的重装。

# TODO(F-051): 两份 _ensure_deps.py（ai-image + ppt-master）后续考虑抽公共 lib。
# 改任一份的核心逻辑必须人工 sync 到另一份；不可机械 copy 整段。
# 本脚本是依赖 bootstrap 入口，不能依赖第三方包（portalocker / filelock 等）。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
# v1.0.0：requirements.txt 已迁入 skill 内部（与 scripts/ 同处 skill root，1 级 parent）。
# 旧名 _PLUGIN_ROOT 改名为 _SKILL_DIR，反映 vercel CLI 装到 Codex 时拷贝单元是 skill/。
_SKILL_DIR = _SCRIPTS_DIR.parent
_REQ = _SKILL_DIR / "requirements.txt"
_MARKER = _SKILL_DIR / ".deps-installed"
_LOCK = _SKILL_DIR / ".deps-installing.lock"

# 允许环境变量强制跳过（CI、容器、用户已手动管理依赖等场景）
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
                f"[{_SKILL_DIR.name}] WARN: 锁等待 30s 超时，可能另一进程卡住未清理。"
                f"继续无锁尝试 install 兜底（pip 内部锁会兜底，worst case 二者都成功 install 同一份依赖，幂等）。",
                file=sys.stderr,
            )
            # fall-through 到 install（不 return，本进程接管）
    except (OSError, PermissionError):
        # 只读 cache（如 Nix store） / 权限不足 → fall-through 无锁 install
        pass

    try:
        print(
            f"[{_SKILL_DIR.name}] First-time setup: installing Python dependencies from {_REQ.name}…",
            file=sys.stderr,
        )
        args = [sys.executable, "-m", "pip", "install", "-r", str(_REQ)]
        if quiet:
            args.append("--quiet")

        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError as e:
            print(
                f"[{_SKILL_DIR.name}] WARN: pip install failed (exit {e.returncode}). "
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

        print(f"[{_SKILL_DIR.name}] Dependencies installed.", file=sys.stderr)
    finally:
        # 仅当本进程拿到锁时才清，避免误删他人的锁
        if lock_acquired:
            try:
                _LOCK.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    ensure_deps(quiet=False)
