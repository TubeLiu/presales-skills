"""Plugin 依赖自动化安装 bootstrap（共享脚本，跨 plugin 字节相同）。

入口脚本（image_gen.py / ai_image_config.py / svg_to_pptx.py / ...）在最开头：

    from _ensure_deps import ensure_deps
    ensure_deps()

逻辑：
  1. 读同 skill root 的 `requirements.txt`
  2. marker 文件（<skill_root>/.deps-installed）已存在 → skip
  3. **解析 requirements 名单，用 importlib.metadata 检查每个包是否已注册**
     （已通过 pipx / venv / 系统包管理器 / --break-system-packages 等任何途径
     装好都算）；全部已装 → 直接 touch marker，不跑 pip
  4. 否则拿 .deps-installing.lock 排他锁（避免并发调用打架）
  5. 调用 `sys.executable -m pip install -r <requirements.txt>`
  6. 无论成功失败都 touch marker：成功是真装好；失败常见于 PEP 668
     externally-managed-environment（macOS Homebrew / Debian 系统 Python），
     重试无用，让脚本继续，由其自身 ImportError 暴露具体缺哪个包

Marker 位于 skill 根目录。plugin 升级时由于 cache dir 路径带 version（如
~/.claude/plugins/cache/presales-skills/ai-image/<commit-sha>/），marker 不会跨版本继承，
自动触发新 requirements 的重检测。

# F-020 / F-051: 本文件在 ai-image / ppt-master 两 plugin 中字节相同。
# tests/test_ensure_deps_identity.py lint 强制 enforce identity，避免未来某次
# 只改一份漂移。如需修改，必须两份同步改 + 跑 pytest 验证 lint 通过。
# 本脚本是依赖 bootstrap 入口，不能依赖第三方包（portalocker / filelock 等）。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from importlib.metadata import PackageNotFoundError, distribution
except ImportError:  # Python < 3.8 fallback (项目要求 3.8+，仅防御)
    distribution = None
    PackageNotFoundError = Exception  # type: ignore

_SCRIPTS_DIR = Path(__file__).resolve().parent
# v1.0.0：requirements.txt 已迁入 skill 内部（与 scripts/ 同处 skill root，1 级 parent）。
# 旧名 _PLUGIN_ROOT 改名为 _SKILL_DIR，反映 vercel CLI 装到 Codex 时拷贝单元是 skill/。
_SKILL_DIR = _SCRIPTS_DIR.parent
_REQ = _SKILL_DIR / "requirements.txt"
_MARKER = _SKILL_DIR / ".deps-installed"
_LOCK = _SKILL_DIR / ".deps-installing.lock"

# Plugin label 用于日志：从 <plugin>/skills/<skill> 反推 plugin 名。
# 用 parent.parent.name 避免硬编码各 plugin 名，让两份脚本字节相同。
_PLUGIN_LABEL = _SKILL_DIR.parent.parent.name

# 允许环境变量强制跳过（CI、容器、用户已手动管理依赖等场景）
_SKIP_ENV = "PRESALES_SKILLS_SKIP_AUTO_INSTALL"

# requirements.txt 行解析：剥掉注释 / 空行 / 选项行 / extras / version specifier
# 拿到的是 PyPI distribution name（importlib.metadata 按这个名查）
_NAME_SPLIT_RE = re.compile(r"[<>=!~;\[\s]")


def _required_distributions(req_path: Path) -> list[str]:
    """从 requirements.txt 解析出 PyPI distribution name 列表。"""
    names: list[str] = []
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):  # 空行 / -r / -e / --option
            continue
        # 拆出包名（剥掉 version specifier、extras []、environment markers ;）
        name = _NAME_SPLIT_RE.split(line, 1)[0].strip()
        if name:
            names.append(name)
    return names


def _all_installed(req_path: Path) -> bool:
    """所有 requirements 都已通过任何途径装好则 True。"""
    if distribution is None:  # Py < 3.8 fallback：不检测，按老逻辑跑 pip
        return False
    try:
        for name in _required_distributions(req_path):
            try:
                distribution(name)
            except PackageNotFoundError:
                return False
        return True
    except OSError:
        # requirements.txt 读失败（极端场景）；交给老路径处理
        return False


def ensure_deps(quiet: bool = True) -> None:
    """Install requirements.txt once per plugin version. Idempotent + concurrent-safe."""
    if os.environ.get(_SKIP_ENV):
        return
    if _MARKER.exists() or not _REQ.exists():
        return

    # 快速通道：依赖已经齐了（pipx / venv / 系统包管理器 / --break-system-packages
    # 等任何途径装好都算）→ 直接 touch marker，不打 pip，不打 WARN。
    if _all_installed(_REQ):
        try:
            _MARKER.touch()
        except OSError:
            pass
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
                f"[{_PLUGIN_LABEL}] WARN: 锁等待 30s 超时，可能另一进程卡住未清理。"
                f"继续无锁尝试 install 兜底（pip 内部锁会兜底，worst case 二者都成功 install 同一份依赖，幂等）。",
                file=sys.stderr,
            )
            # fall-through 到 install（不 return，本进程接管）
    except (OSError, PermissionError):
        # 只读 cache（如 Nix store） / 权限不足 → fall-through 无锁 install
        pass

    try:
        print(
            f"[{_PLUGIN_LABEL}] First-time setup: installing Python dependencies from {_REQ.name}…",
            file=sys.stderr,
        )
        args = [sys.executable, "-m", "pip", "install", "-r", str(_REQ)]
        if quiet:
            args.append("--quiet")

        try:
            subprocess.check_call(args)
            print(f"[{_PLUGIN_LABEL}] Dependencies installed.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            # PEP 668 (Homebrew Python on macOS / system Python on Debian) / 权限不足等
            # "环境锁定"错误重试无用，每次重试只会持续骚扰用户。打一次警告就够了——
            # 如果依赖真缺会被脚本自身的 ImportError 暴露；如果用户已通过 pipx / venv /
            # --break-system-packages / 系统包管理器 装好了，那就皆大欢喜。
            print(
                f"[{_PLUGIN_LABEL}] WARN: pip install failed (exit {e.returncode}). "
                f"Marker touched anyway to suppress retries; if imports fail later, "
                f"run manually: pip install -r {_REQ}",
                file=sys.stderr,
            )
            print(
                f"  Set {_SKIP_ENV}=1 to bypass this bootstrap on future runs.",
                file=sys.stderr,
            )

        try:
            _MARKER.touch()
        except OSError:
            # 缓存目录可能只读（极端场景）；不 fatal，仅下次会重试
            pass
    finally:
        # 仅当本进程拿到锁时才清，避免误删他人的锁
        if lock_acquired:
            try:
                _LOCK.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    ensure_deps(quiet=False)
