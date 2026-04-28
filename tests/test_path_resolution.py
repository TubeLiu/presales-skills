"""Layer 1 — 5 段式路径自定位 fallback 行为矩阵。

每个 SKILL.md 顶部的 §路径自定位 段是 plugin 安装位置的权威解析逻辑。
本文件用 synthetic `installed_plugins.json` / HOME / env / cwd 跑遍 5 层 fallback，
断言每层各自工作 + 上层失败时正确降级到下层。

测试矩阵（以 ai-image SKILL.md 为 canonical fixture）：

    L1 happy path       installed_plugins.json 指向 fake plugin → SKILL_DIR 解析为该路径
    L1 file missing     ~/.claude/ 不存在 → 静默降级到 L2/L3/L4
    L1 malformed JSON   文件存在但非合法 JSON → 静默降级（python heredoc 有 2>/dev/null）
    L1 plugin missing   合法 JSON 但 plugins 表里没本 plugin → 静默降级
    L2 vercel cursor    ~/.cursor/skills/image-gen/ 存在 → 命中
    L2 vercel agents    ~/.agents/skills/<plugin>/skills/<sub>/ 存在 → 命中
    L3 env var          <PLUGIN>_PLUGIN_PATH 指向 dir → 命中
    L4 cwd dev          cwd/<plugin>/skills/<sub>/ 存在 → 命中
    L5 all fail         全空 → exit 1 + 错误消息含 "找不到" + "PLUGIN_PATH"

最后再做"全 SKILL.md 行为一致性"参数化检查：
    每个 SKILL.md 的 bootstrap 在同一 fixture 下表现一致（仅 plugin 名 / sub-skill dir 替换）。

跑：
    cd presales-skills/
    python3 -m pytest tests/test_path_resolution.py -v
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = sorted(REPO_ROOT.glob("**/SKILL.md"))


def _extract_bootstrap(skill_md: Path) -> str | None:
    """从 SKILL.md 抽出 ## 路径自定位 后第一个 ```bash 块原文。无此 section 返回 None。"""
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"##\s*路径自定位.*?```bash\n(.*?)\n```", text, re.DOTALL)
    return m.group(1) if m else None


def _is_canonical_bootstrap(bash_block: str) -> bool:
    """判断是否是 canonical 5 段式 bootstrap（含 installed_plugins.json heredoc + 退出诊断）。

    drawio 等"lite bootstrap"（纯 bash glob + 无 exit 1）不在矩阵内——
    它们是有意设计的软降级路径，不应套用本测试的硬性断言。
    """
    return (
        "installed_plugins.json" in bash_block
        and "exit 1" in bash_block
    )


def _run(bash_block: str, env: dict, cwd: Path) -> tuple[int, str, str]:
    """跑 bash bootstrap，附加 echo SKILL_DIR_RESULT，返回 (rc, stdout, stderr)。"""
    full = bash_block + '\necho "SKILL_DIR_RESULT=${SKILL_DIR}"\n'
    p = subprocess.run(
        ["bash", "-c", full],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=15,
    )
    return p.returncode, p.stdout, p.stderr


def _parse_skill_dir(stdout: str) -> str:
    m = re.search(r"^SKILL_DIR_RESULT=(.*)$", stdout, re.MULTILINE)
    return m.group(1) if m else ""


def _make_installed_plugins_json(fake_install_path: Path, plugin_name: str) -> dict:
    """生成符合 Claude Code installed_plugins.json schema 的 fixture。"""
    return {
        "plugins": {
            "presales-skills": [
                {"name": plugin_name, "installPath": str(fake_install_path)}
            ]
        }
    }


def _base_env(home: Path) -> dict:
    """干净 env：仅保留 PATH / LANG，HOME 指向 tmp。"""
    return {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "LANG": "en_US.UTF-8",
    }


# ---------------------------------------------------------------------------
# Canonical SKILL = ai-image/skills/gen (alias name 'image-gen')
# ---------------------------------------------------------------------------

CANONICAL_SKILL = REPO_ROOT / "ai-image/skills/gen/SKILL.md"
CANONICAL_PLUGIN = "ai-image"
CANONICAL_SUB = "gen"
CANONICAL_ALIAS = "image-gen"
CANONICAL_ENV_VAR = "AI_IMAGE_PLUGIN_PATH"


@pytest.fixture(scope="module")
def bootstrap() -> str:
    bs = _extract_bootstrap(CANONICAL_SKILL)
    assert bs is not None, "canonical SKILL 必须有 ## 路径自定位 段"
    assert _is_canonical_bootstrap(bs), "canonical SKILL 必须用 5 段式 bootstrap"
    return bs


def test_l1_happy_path(tmp_path, bootstrap):
    """L1: installed_plugins.json 指向真实 plugin install path → 解析。"""
    fake_install = tmp_path / "fake-cache/ai-image/1.0.0"
    (fake_install / "skills/gen").mkdir(parents=True)

    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text(
        json.dumps(_make_installed_plugins_json(fake_install, CANONICAL_PLUGIN))
    )

    rc, out, _err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 0, f"expected success, got rc={rc}"
    assert _parse_skill_dir(out) == str(fake_install / "skills/gen")


def test_l1_file_missing_falls_through(tmp_path, bootstrap):
    """L1: ~/.claude 不存在 → 不报错，降级到下层（这里下层全空 → 最终 exit 1）。"""
    home = tmp_path / "empty-home"
    home.mkdir()
    rc, _out, err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 1, "all 4 layers fail → exit 1"
    assert "找不到" in err
    assert CANONICAL_ENV_VAR in err


def test_l1_malformed_json_falls_through(tmp_path, bootstrap):
    """L1: installed_plugins.json 是非法 JSON → python heredoc 静默退出（有 2>/dev/null）→ 降级。"""
    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text("not-valid-json{{")

    fake_install = tmp_path / "via-env/ai-image"
    (fake_install / "skills/gen").mkdir(parents=True)
    env = _base_env(home)
    env[CANONICAL_ENV_VAR] = str(fake_install)

    rc, out, _err = _run(bootstrap, env, tmp_path)
    assert rc == 0, "malformed JSON should not block; env var should resolve"
    assert _parse_skill_dir(out) == str(fake_install / "skills/gen")


def test_l1_plugin_not_in_registry_falls_through(tmp_path, bootstrap):
    """L1: 合法 JSON 但 plugins 表里没本 plugin（installPath 路径不含 /ai-image/）→ 降级。"""
    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text(
        json.dumps({
            "plugins": {
                "other-marketplace": [
                    {"name": "drawio", "installPath": "/some/path/drawio/1.0.0"}
                ]
            }
        })
    )

    rc, _out, err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 1
    assert "找不到" in err


def test_l2_vercel_cursor_dir(tmp_path, bootstrap):
    """L2: ~/.cursor/skills/<plugin>/skills/<sub>/ 命中。"""
    home = tmp_path / "home"
    (home / ".cursor/skills" / CANONICAL_PLUGIN / "skills" / CANONICAL_SUB).mkdir(parents=True)

    rc, out, _err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 0
    assert _parse_skill_dir(out).endswith(f"{CANONICAL_PLUGIN}/skills/{CANONICAL_SUB}")


def test_l2_vercel_alias_dir(tmp_path, bootstrap):
    """L2: ~/.cursor/skills/<alias>/ 命中（vercel CLI 按 SKILL.md `name:` 命名 dir）。"""
    home = tmp_path / "home"
    (home / ".cursor/skills" / CANONICAL_ALIAS).mkdir(parents=True)

    rc, out, _err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 0
    assert _parse_skill_dir(out).endswith(f".cursor/skills/{CANONICAL_ALIAS}")


def test_l3_env_var(tmp_path, bootstrap):
    """L3: <PLUGIN>_PLUGIN_PATH 指向 plugin root → 拼 /skills/<sub>/。"""
    home = tmp_path / "empty-home"
    home.mkdir()
    fake_root = tmp_path / "via-env/ai-image"
    (fake_root / "skills/gen").mkdir(parents=True)

    env = _base_env(home)
    env[CANONICAL_ENV_VAR] = str(fake_root)

    rc, out, _err = _run(bootstrap, env, tmp_path)
    assert rc == 0
    assert _parse_skill_dir(out) == str(fake_root / "skills/gen")


def test_l4_cwd_dev(tmp_path, bootstrap):
    """L4: cwd 含 ./<plugin>/skills/<sub>/ → 命中（dev 态）。"""
    home = tmp_path / "empty-home"
    home.mkdir()
    dev_repo = tmp_path / "dev-repo"
    (dev_repo / CANONICAL_PLUGIN / "skills" / CANONICAL_SUB).mkdir(parents=True)

    rc, out, _err = _run(bootstrap, _base_env(home), dev_repo)
    assert rc == 0
    assert _parse_skill_dir(out).endswith(f"{CANONICAL_PLUGIN}/skills/{CANONICAL_SUB}")


def test_l5_all_fail_exits_one(tmp_path, bootstrap):
    """L5: 4 层全空 → exit 1 + stderr 含诊断指引。"""
    home = tmp_path / "empty-home"
    home.mkdir()
    cwd_no_plugin = tmp_path / "elsewhere"
    cwd_no_plugin.mkdir()

    rc, _out, err = _run(bootstrap, _base_env(home), cwd_no_plugin)
    assert rc == 1
    assert "找不到" in err, f"stderr 缺诊断指引: {err!r}"
    assert CANONICAL_ENV_VAR in err, "stderr 应提示 export 环境变量名"


def test_l1_priority_over_lower_layers(tmp_path, bootstrap):
    """L1 命中时不应被 L3/L4 覆盖（优先级最高）。"""
    fake_l1 = tmp_path / "from-l1/ai-image/1.0.0"
    (fake_l1 / "skills/gen").mkdir(parents=True)

    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text(
        json.dumps(_make_installed_plugins_json(fake_l1, CANONICAL_PLUGIN))
    )

    # 同时设 env var 指向另一个路径
    fake_l3 = tmp_path / "from-l3/ai-image"
    (fake_l3 / "skills/gen").mkdir(parents=True)
    env = _base_env(home)
    env[CANONICAL_ENV_VAR] = str(fake_l3)

    # 同时 cwd 也含 ai-image dev
    dev_repo = tmp_path / "dev-repo"
    (dev_repo / CANONICAL_PLUGIN / "skills" / CANONICAL_SUB).mkdir(parents=True)

    rc, out, _err = _run(bootstrap, env, dev_repo)
    assert rc == 0
    assert _parse_skill_dir(out) == str(fake_l1 / "skills/gen"), \
        "L1 必须优先于 L3 / L4"


# ---------------------------------------------------------------------------
# 跨 SKILL.md 一致性：每个 SKILL.md 的 bootstrap 都能在 happy path 下解析
# ---------------------------------------------------------------------------

def _plugin_meta_for_skill(skill_md: Path) -> tuple[str, str, str]:
    """从 SKILL.md 路径推断 (plugin_name, sub_dir, env_var_name)。

    路径形如 <plugin>/skills/<sub>/SKILL.md → plugin = parts[-4], sub = parts[-2]
    env_var = <PLUGIN>_PLUGIN_PATH（破折号转下划线，全大写）
    """
    rel = skill_md.relative_to(REPO_ROOT)
    parts = rel.parts
    plugin = parts[0]
    sub = parts[2]  # <plugin>/skills/<sub>/SKILL.md
    env_var = plugin.upper().replace("-", "_") + "_PLUGIN_PATH"
    return plugin, sub, env_var


# 仅对采用 canonical 5 段式 bootstrap 的 SKILL.md 跑参数化矩阵。
# drawio = lite bash glob + soft fallback；skill-optimizer = 纯 markdown 无 bootstrap。
# 这两类是有意设计，不应套硬性断言。
_CANONICAL_SKILLS = []
_LITE_OR_NO_BOOTSTRAP = []
for _s in SKILL_FILES:
    _bs = _extract_bootstrap(_s)
    if _bs is None or not _is_canonical_bootstrap(_bs):
        _LITE_OR_NO_BOOTSTRAP.append(_s)
    else:
        _CANONICAL_SKILLS.append(_s)


@pytest.mark.parametrize("skill_md", _CANONICAL_SKILLS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_each_canonical_bootstrap_l1_resolves(tmp_path, skill_md):
    """每个采用 canonical 5 段式 bootstrap 的 SKILL.md 在 L1 happy path 下都能正确解析。"""
    plugin, sub, _env_var = _plugin_meta_for_skill(skill_md)
    bootstrap = _extract_bootstrap(skill_md)

    fake_install = tmp_path / f"fake-cache/{plugin}/1.0.0"
    (fake_install / "skills" / sub).mkdir(parents=True)

    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text(
        json.dumps(_make_installed_plugins_json(fake_install, plugin))
    )

    rc, out, err = _run(bootstrap, _base_env(home), tmp_path)
    assert rc == 0, (
        f"{skill_md.relative_to(REPO_ROOT)}: bootstrap 应解析成功\n"
        f"stdout={out!r}\nstderr={err!r}"
    )
    resolved = _parse_skill_dir(out)
    assert resolved == str(fake_install / "skills" / sub), (
        f"{skill_md.relative_to(REPO_ROOT)}: 解析路径不符\n"
        f"expected={fake_install / 'skills' / sub}\nactual={resolved}"
    )


@pytest.mark.parametrize("skill_md", _CANONICAL_SKILLS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_each_canonical_bootstrap_l5_diagnostic(tmp_path, skill_md):
    """每个 canonical SKILL.md 全 fallback 失败时必须 exit 1 + stderr 含 '找不到' + 环境变量名提示。"""
    plugin, _sub, env_var = _plugin_meta_for_skill(skill_md)
    bootstrap = _extract_bootstrap(skill_md)

    home = tmp_path / "empty-home"
    home.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    rc, _out, err = _run(bootstrap, _base_env(home), elsewhere)
    assert rc == 1, f"{skill_md.relative_to(REPO_ROOT)}: 应 exit 1"
    assert "找不到" in err, f"{skill_md.relative_to(REPO_ROOT)}: stderr 缺诊断"
    assert env_var in err, (
        f"{skill_md.relative_to(REPO_ROOT)}: stderr 应提示 export {env_var}"
    )


def test_lite_bootstrap_skills_documented():
    """记录哪些 SKILL.md 用了 lite/no bootstrap（drawio / skill-optimizer），让未来调整时显式可见。

    如果以后这两个 plugin 的 bootstrap 升级为 canonical 5 段式，本测试会失败提醒更新。
    """
    expected_lite = {
        "drawio/skills/draw/SKILL.md",          # 纯 bash glob + ${CLAUDE_PLUGIN_ROOT:-./drawio} 软降级
        "skill-optimizer/skills/optimize/SKILL.md",  # 纯 markdown 无 bootstrap
    }
    actual_lite = {
        s.relative_to(REPO_ROOT).as_posix() for s in _LITE_OR_NO_BOOTSTRAP
    }
    assert actual_lite == expected_lite, (
        f"lite/no-bootstrap 集合变化（预期 {expected_lite}，实际 {actual_lite}）。\n"
        f"如果是有意改动，更新本测试的 expected_lite；如果是 bug，恢复 SKILL.md 的 bootstrap。"
    )
