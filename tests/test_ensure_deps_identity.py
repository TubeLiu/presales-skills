"""F-020 / F-051 lint：跨 plugin 共享的 _ensure_deps.py 必须字节相同。

vercel CLI 装到 Codex/Cursor 时按 skill 拷贝（每个 plugin 独立打包，无 shared dir），
所以无法做真正的 Python lib 共享。折中方案是把两份脚本做成字节相同 + 加本 lint
强制 enforce identity，避免未来某次只改一份漂移。

如需修改 _ensure_deps.py：必须两份同步改 + 跑 pytest 验证 lint 通过。

跑：
    cd presales-skills/
    python3 -m pytest tests/test_ensure_deps_identity.py -v
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_ENSURE_DEPS_PATHS = [
    REPO_ROOT / "ai-image/skills/gen/scripts/_ensure_deps.py",
    REPO_ROOT / "ppt-master/skills/make/scripts/_ensure_deps.py",
]


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ensure_deps_files_exist():
    """两份 _ensure_deps.py 都必须存在（任一缺失说明 plugin 损坏）。"""
    missing = [str(p.relative_to(REPO_ROOT)) for p in _ENSURE_DEPS_PATHS if not p.exists()]
    assert not missing, f"_ensure_deps.py 缺失：\n" + "\n".join(missing)


def test_ensure_deps_byte_identical():
    """所有 _ensure_deps.py 副本必须字节相同（plugin label 通过 _SKILL_DIR.parent.parent.name 推导）。

    若失败：你只改了一份。请把改动同步到另一份后重跑测试。
    """
    hashes = {p: _sha256_of(p) for p in _ENSURE_DEPS_PATHS}
    unique_hashes = set(hashes.values())
    if len(unique_hashes) > 1:
        msg = "副本字节不一致：\n" + "\n".join(
            f"  {p.relative_to(REPO_ROOT)}: {h}" for p, h in hashes.items()
        )
        msg += "\n\n请用 diff 检查并把改动同步到所有副本：\n"
        msg += "  diff " + " ".join(str(p.relative_to(REPO_ROOT)) for p in _ENSURE_DEPS_PATHS)
        raise AssertionError(msg)
