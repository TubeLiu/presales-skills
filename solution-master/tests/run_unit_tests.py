#!/usr/bin/env python3
"""Solution Master plugin unit test runner (U1–U17).

Runs the automated unit test suite and writes a human-readable Markdown
report to ~/Documents/solution-master-plugin-test-report-<YYYYMMDD-HHMM>.md.

The suite covers Layer 1 (SessionStart hook) and packaging artifacts.
Layer 3 (evidence file contract + PostToolUse/Stop hooks) was removed in
the 2026-04-14 rollback — see git history and
docs/specs/eager-bubbling-rabin.md for context.

Exit code:
    0 — all tests PASS
    1 — one or more tests FAIL

Usage:
    python3 tests/run_unit_tests.py
    python3 tests/run_unit_tests.py --no-report    # skip report writing
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
SESSION_START = HOOKS_DIR / "session-start"
BIN_JS = REPO_ROOT / "bin" / "solution-master.js"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
HOOKS_JSON = HOOKS_DIR / "hooks.json"
PACKAGE_JSON = REPO_ROOT / "package.json"
USING_SKILL = REPO_ROOT / "skills" / "using-solution-master" / "SKILL.md"
SDW_SKILL = REPO_ROOT / "skills" / "subagent-driven-writing" / "SKILL.md"
THIRD_PARTY_NOTICES = REPO_ROOT / "THIRD_PARTY_NOTICES.md"


@dataclass
class TestResult:
    id: str
    name: str
    command: str
    expected: str
    actual: str = ""
    status: str = "FAIL"  # PASS | FAIL | SKIP
    error: str = ""

    def ok(self, actual: str = "") -> None:
        self.status = "PASS"
        if actual:
            self.actual = actual

    def fail(self, actual: str = "", error: str = "") -> None:
        self.status = "FAIL"
        if actual:
            self.actual = actual
        if error:
            self.error = error


def run_bash(script: Path, *, cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    env_final = os.environ.copy()
    if env:
        env_final.update(env)
    return subprocess.run(
        ["bash", str(script)],
        cwd=str(cwd) if cwd else None,
        env=env_final,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_node(script: Path, args: list[str], *, cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: int = 60) -> subprocess.CompletedProcess:
    env_final = os.environ.copy()
    if env:
        env_final.update(env)
    return subprocess.run(
        ["node", str(script), *args],
        cwd=str(cwd) if cwd else None,
        env=env_final,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------- Test cases ----------

def test_u1_session_start_injection() -> TestResult:
    r = TestResult(
        id="U1",
        name="session-start 注入 Claude Code 格式（hookSpecificOutput）",
        command="bash hooks/session-start (in SM project, no env var)",
        expected="hookSpecificOutput.additionalContext 含 SKILL 内容",
    )
    try:
        # Explicitly unset both platform env vars to simulate npx mode
        # (where neither CLAUDE_PLUGIN_ROOT nor CURSOR_PLUGIN_ROOT is set).
        # The script must default to Claude Code's documented format.
        env = {"CLAUDE_PLUGIN_ROOT": "", "CURSOR_PLUGIN_ROOT": ""}
        cp = run_bash(SESSION_START, cwd=REPO_ROOT, env=env)
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"exit {cp.returncode}")
            return r
        try:
            obj = json.loads(cp.stdout)
        except json.JSONDecodeError as exc:
            r.fail(cp.stdout[:500], f"invalid JSON: {exc}")
            return r
        if "hookSpecificOutput" not in obj:
            r.fail(cp.stdout[:500], "expected hookSpecificOutput at top level (Claude Code format)")
            return r
        hso = obj["hookSpecificOutput"]
        if hso.get("hookEventName") != "SessionStart":
            r.fail(str(hso)[:500], "hookEventName != SessionStart")
            return r
        ctx = hso.get("additionalContext", "")
        if "using-solution-master" in ctx or "Solution Master" in ctx:
            r.ok(f"hookSpecificOutput OK, additionalContext len={len(ctx)}")
        else:
            r.fail(ctx[:500], "additionalContext missing SM marker")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u2_session_start_gate(base: Path) -> TestResult:
    r = TestResult(
        id="U2",
        name="session-start 项目门禁（非 SM 项目静默）",
        command="bash hooks/session-start (in empty dir)",
        expected="无输出, exit 0",
    )
    try:
        empty = base / "empty-proj"
        empty.mkdir(exist_ok=True)
        cp = run_bash(SESSION_START, cwd=empty)
        if cp.returncode == 0 and cp.stdout.strip() == "":
            r.ok("no output, exit 0")
        else:
            r.fail(cp.stdout[:500], f"exit {cp.returncode}, stdout non-empty")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u3_session_start_json() -> TestResult:
    r = TestResult(
        id="U3",
        name="session-start 输出是合法 JSON",
        command="bash hooks/session-start | json.loads(...)",
        expected="解析无异常",
    )
    try:
        cp = run_bash(SESSION_START, cwd=REPO_ROOT)
        if cp.returncode != 0:
            r.fail(error=f"session-start exit {cp.returncode}")
            return r
        json.loads(cp.stdout)
        r.ok("JSON parsed")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u4_plugin_json() -> TestResult:
    r = TestResult(
        id="U4",
        name="plugin.json schema 有效",
        command="json.load(.claude-plugin/plugin.json)",
        expected="解析成功",
    )
    try:
        obj = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        if "name" in obj and "version" in obj:
            r.ok(f"name={obj['name']} version={obj['version']}")
        else:
            r.fail(str(obj), "missing name/version")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u5_hooks_json() -> TestResult:
    r = TestResult(
        id="U5",
        name="hooks.json 仅注册 SessionStart",
        command="json.load(hooks/hooks.json)",
        expected="含 SessionStart 但不含 PostToolUse/Stop",
    )
    try:
        obj = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        hooks = obj.get("hooks", {})
        if "SessionStart" not in hooks:
            r.fail(str(hooks.keys()), "SessionStart missing")
            return r
        if "PostToolUse" in hooks or "Stop" in hooks:
            r.fail(str(hooks.keys()), "PostToolUse/Stop should not be present (Layer 3 was rolled back)")
            return r
        r.ok("only SessionStart registered")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u6_package_json() -> TestResult:
    r = TestResult(
        id="U6",
        name="package.json + bin 字段",
        command="json.load(package.json)",
        expected="bin.solution-master 存在",
    )
    try:
        obj = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
        binf = obj.get("bin", {}).get("solution-master", "")
        if binf == "bin/solution-master.js":
            r.ok(f"bin.solution-master={binf}")
        else:
            r.fail(str(obj.get("bin")), "bin.solution-master mismatch")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u7_bin_help() -> TestResult:
    r = TestResult(
        id="U7",
        name="bin/solution-master.js --help",
        command="node bin/solution-master.js --help",
        expected="包含用法说明",
    )
    try:
        cp = run_node(BIN_JS, ["--help"])
        if cp.returncode == 0 and "用法" in cp.stdout:
            r.ok("help shown")
        else:
            r.fail(cp.stdout[:500], f"exit {cp.returncode}")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u8_bin_version() -> TestResult:
    r = TestResult(
        id="U8",
        name="bin/solution-master.js --version",
        command="node bin/solution-master.js --version",
        expected="semver 字符串",
    )
    try:
        import re
        cp = run_node(BIN_JS, ["--version"])
        if cp.returncode == 0 and re.match(r"^\d+\.\d+\.\d+", cp.stdout.strip()):
            r.ok(cp.stdout.strip())
        else:
            r.fail(cp.stdout.strip(), "not a semver")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u9_npx_project_install(base: Path) -> TestResult:
    r = TestResult(
        id="U9",
        name="npx 项目模式安装",
        command="node bin/... (cwd=临时项目)",
        expected=".claude/{skills,agents,hooks,settings.json} 就位 + 命令经由 run-hook.cmd",
    )
    try:
        proj = base / "u9-proj"
        proj.mkdir(exist_ok=True)
        cp = run_node(BIN_JS, [], cwd=proj)
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"install exit {cp.returncode}")
            return r
        checks = [
            proj / ".claude" / "skills" / "using-solution-master" / "SKILL.md",
            proj / ".claude" / "agents" / "writer.md",
            proj / ".claude" / "hooks" / "session-start",
            proj / ".claude" / "hooks" / "run-hook.cmd",
            proj / ".claude" / "settings.json",
        ]
        missing = [str(p.relative_to(proj)) for p in checks if not p.exists()]
        if missing:
            r.fail(str(missing), "files missing after install")
            return r
        if (proj / ".claude" / "hooks" / "check_evidence.py").exists():
            r.fail("", "check_evidence.py should not exist after rollback")
            return r
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        hooks = settings.get("hooks", {})
        if "SessionStart" not in hooks:
            r.fail(str(hooks), "settings.json missing SessionStart hook")
            return r
        if "PostToolUse" in hooks or "Stop" in hooks:
            r.fail(str(hooks), "PostToolUse/Stop should not be registered")
            return r
        # Verify the registered command path goes through run-hook.cmd wrapper
        # (Windows cross-platform compatibility; matches plugin-mode hooks.json).
        groups = hooks.get("SessionStart") or []
        cmds = [h.get("command", "") for g in groups for h in g.get("hooks", [])]
        if not any("run-hook.cmd" in c and "session-start" in c for c in cmds):
            r.fail(str(cmds), "SessionStart command should use run-hook.cmd wrapper")
            return r
        r.ok("all files present + command uses run-hook.cmd wrapper")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u10_npx_backup(base: Path) -> TestResult:
    r = TestResult(
        id="U10",
        name="npx 安装时备份 settings.json",
        command="预先有 settings.json，再安装",
        expected=".bak.* 存在",
    )
    try:
        proj = base / "u10-proj"
        proj.mkdir(exist_ok=True)
        (proj / ".claude").mkdir(exist_ok=True)
        (proj / ".claude" / "settings.json").write_text(
            '{"permissions":{"allow":["Read"]}}', encoding="utf-8"
        )
        cp = run_node(BIN_JS, [], cwd=proj)
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"install exit {cp.returncode}")
            return r
        baks = list((proj / ".claude").glob("settings.json.bak.*"))
        if baks:
            r.ok(f"backup: {baks[0].name}")
        else:
            r.fail("", "no backup file created")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u11_npx_merge_preserves_permissions(base: Path) -> TestResult:
    r = TestResult(
        id="U11",
        name="npx 安装保留已有 permissions",
        command="pre-existing permissions + 安装后验证",
        expected="permissions 仍在 + hook 新增",
    )
    try:
        proj = base / "u11-proj"
        proj.mkdir(exist_ok=True)
        (proj / ".claude").mkdir(exist_ok=True)
        (proj / ".claude" / "settings.json").write_text(
            json.dumps({"permissions": {"allow": ["Read", "Grep"]}, "env": {"DEBUG": "1"}}),
            encoding="utf-8",
        )
        cp = run_node(BIN_JS, [], cwd=proj)
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"install exit {cp.returncode}")
            return r
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        if settings.get("permissions", {}).get("allow") != ["Read", "Grep"]:
            r.fail(str(settings), "permissions not preserved")
            return r
        if settings.get("env", {}).get("DEBUG") != "1":
            r.fail(str(settings), "env not preserved")
            return r
        if "hooks" not in settings or "SessionStart" not in settings["hooks"]:
            r.fail(str(settings), "SessionStart hook not added")
            return r
        r.ok("permissions + env preserved, hook added")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u12_npx_uninstall(base: Path) -> TestResult:
    r = TestResult(
        id="U12",
        name="npx --uninstall 精确清理",
        command="install 后 uninstall",
        expected="SM 资产移除 + permissions 保留",
    )
    try:
        proj = base / "u12-proj"
        proj.mkdir(exist_ok=True)
        (proj / ".claude").mkdir(exist_ok=True)
        (proj / ".claude" / "settings.json").write_text(
            json.dumps({"permissions": {"allow": ["Read"]}}),
            encoding="utf-8",
        )
        cp1 = run_node(BIN_JS, [], cwd=proj)
        if cp1.returncode != 0:
            r.fail(cp1.stdout + cp1.stderr, "install failed")
            return r
        cp2 = run_node(BIN_JS, ["--uninstall"], cwd=proj)
        if cp2.returncode != 0:
            r.fail(cp2.stdout + cp2.stderr, "uninstall failed")
            return r
        sm_skill = proj / ".claude" / "skills" / "using-solution-master"
        if sm_skill.exists():
            r.fail("", f"{sm_skill} still exists after uninstall")
            return r
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        if settings.get("permissions", {}).get("allow") != ["Read"]:
            r.fail(str(settings), "permissions lost")
            return r
        hooks = settings.get("hooks", {})
        has_sm_hook = False
        for event, groups in hooks.items():
            for g in groups or []:
                for h in g.get("hooks", []):
                    if h.get("_owner") == "solution-master":
                        has_sm_hook = True
        if has_sm_hook:
            r.fail(str(hooks), "SM hook still in settings")
            return r
        r.ok("uninstall clean")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u13_npx_global_install(base: Path) -> TestResult:
    r = TestResult(
        id="U13",
        name="npx --global 安装",
        command="HOME=<tmp> node bin ... --global",
        expected="~/.claude/{skills,agents,hooks,settings.json} 就位",
    )
    try:
        fake_home = base / "u13-home"
        fake_home.mkdir(exist_ok=True)
        cp = run_node(BIN_JS, ["--global"], env={"HOME": str(fake_home)})
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"exit {cp.returncode}")
            return r
        checks = [
            fake_home / ".claude" / "skills" / "using-solution-master" / "SKILL.md",
            fake_home / ".claude" / "hooks" / "session-start",
            fake_home / ".claude" / "settings.json",
        ]
        missing = [str(p.relative_to(fake_home)) for p in checks if not p.exists()]
        if missing:
            r.fail(str(missing), "global install artifacts missing")
        elif (fake_home / ".claude" / "hooks" / "check_evidence.py").exists():
            r.fail("", "check_evidence.py should not be installed after rollback")
        else:
            r.ok("global install ok")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u14_npx_global_uninstall(base: Path) -> TestResult:
    r = TestResult(
        id="U14",
        name="npx --uninstall --global",
        command="install 后 uninstall 全局",
        expected="SM 资产移除；用户原配置保留",
    )
    try:
        fake_home = base / "u14-home"
        fake_home.mkdir(exist_ok=True)
        (fake_home / ".claude").mkdir(exist_ok=True)
        (fake_home / ".claude" / "settings.json").write_text(
            json.dumps({"permissions": {"allow": ["Read"]}}),
            encoding="utf-8",
        )
        cp1 = run_node(BIN_JS, ["--global"], env={"HOME": str(fake_home)})
        if cp1.returncode != 0:
            r.fail(cp1.stdout + cp1.stderr, "install failed")
            return r
        cp2 = run_node(BIN_JS, ["--uninstall", "--global"], env={"HOME": str(fake_home)})
        if cp2.returncode != 0:
            r.fail(cp2.stdout + cp2.stderr, "uninstall failed")
            return r
        if (fake_home / ".claude" / "skills" / "using-solution-master").exists():
            r.fail("", "SM skill still present")
            return r
        settings = json.loads(
            (fake_home / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        if settings.get("permissions", {}).get("allow") != ["Read"]:
            r.fail(str(settings), "user permissions lost")
            return r
        r.ok("global uninstall clean")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u15_vendor_attribution() -> TestResult:
    r = TestResult(
        id="U15",
        name="vendored 文件头部出处标注",
        command="grep 'superpowers-zh' 关键文件",
        expected="全部命中",
    )
    try:
        files = [SESSION_START, USING_SKILL, SDW_SKILL]
        missing = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            if "superpowers-zh" not in text:
                missing.append(str(f.relative_to(REPO_ROOT)))
        if missing:
            r.fail(str(missing), "attribution missing")
        else:
            r.ok("all 3 files attributed")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u16_third_party_notices() -> TestResult:
    r = TestResult(
        id="U16",
        name="THIRD_PARTY_NOTICES.md 存在并列出 superpowers-zh",
        command="grep 'superpowers-zh' THIRD_PARTY_NOTICES.md",
        expected="命中",
    )
    try:
        text = THIRD_PARTY_NOTICES.read_text(encoding="utf-8")
        if "superpowers-zh" in text:
            r.ok(f"found (file len={len(text)})")
        else:
            r.fail("", "superpowers-zh not mentioned")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u17_drawio_check_reports_installed() -> TestResult:
    r = TestResult(
        id="U17",
        name="solution-writing Phase 0 的 drawio 检查报告 INSTALLED",
        command="bash -c <snippet from solution-writing/SKILL.md>",
        expected="输出以 'INSTALLED' 开头（drawio 已随 solution-master 捆绑）",
    )
    try:
        # Extract the ```python code fence from solution-writing/SKILL.md,
        # strip markdown list indentation, and execute the snippet via bash.
        # The snippet is a `python3 -c "..."` shell command embedded inside
        # the code fence, so we can run it as a shell command directly.
        skill = (REPO_ROOT / "skills" / "solution-writing" / "SKILL.md").read_text(encoding="utf-8")
        import re
        match = re.search(r'```python\n(.*?)\n\s*```', skill, re.DOTALL)
        if not match:
            r.fail("", "could not find ```python fence in SKILL.md")
            return r
        raw = match.group(1)
        # Strip the common leading whitespace from each line (markdown list indent)
        import textwrap
        snippet = textwrap.dedent(raw)
        # Run as a shell command (it's `python3 -c "..."`)
        # Use a temp dir as cwd so the .claude/skills/drawio/ override check
        # doesn't accidentally pick up the repo's own skills/drawio/.
        with tempfile.TemporaryDirectory() as tmp:
            cp = subprocess.run(
                ["bash", "-c", snippet],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmp,
            )
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"snippet exited {cp.returncode}")
            return r
        out = cp.stdout.strip()
        if out.startswith("INSTALLED"):
            r.ok(out)
        else:
            r.fail(out, "drawio check did not report INSTALLED")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u18_solution_writing_no_stale_claude_paths() -> TestResult:
    r = TestResult(
        id="U18",
        name="solution-writing SKILL 不含 .claude/agents/ 残留路径",
        command="grep '.claude/agents/' skills/solution-writing/SKILL.md",
        expected="不命中",
    )
    try:
        text = (REPO_ROOT / "skills" / "solution-writing" / "SKILL.md").read_text(encoding="utf-8")
        if ".claude/agents/" in text:
            # Find offending lines
            offending = [
                f"L{i+1}: {line}"
                for i, line in enumerate(text.split("\n"))
                if ".claude/agents/" in line
            ]
            r.fail("\n".join(offending[:5]), "stale .claude/agents/ path references")
        else:
            r.ok("no .claude/agents/ references")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u19_session_start_cursor_format(base: Path) -> TestResult:
    r = TestResult(
        id="U19",
        name="session-start Cursor 格式（CURSOR_PLUGIN_ROOT 触发）",
        command="CURSOR_PLUGIN_ROOT=/tmp bash hooks/session-start",
        expected="输出含 additional_context 键而非 hookSpecificOutput",
    )
    try:
        env = {"CURSOR_PLUGIN_ROOT": "/tmp"}
        cp = run_bash(SESSION_START, cwd=REPO_ROOT, env=env)
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"exit {cp.returncode}")
            return r
        obj = json.loads(cp.stdout)
        if "additional_context" in obj and "hookSpecificOutput" not in obj:
            r.ok("Cursor format emitted, Claude Code format absent")
        else:
            r.fail(str(list(obj.keys())), "expected additional_context only")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u20_sm_config_validate_no_false_missing(base: Path) -> TestResult:
    r = TestResult(
        id="U20",
        name="sm_config.py validate 不误报 web-access/drawio 缺失",
        command="python3 skills/solution-config/scripts/sm_config.py validate",
        expected="输出不包含 'web-access plugin 未安装'（或旧版 'skill 未安装'）或 'draw.io skill 未安装'",
    )
    try:
        sm_config = REPO_ROOT / "skills" / "solution-config" / "scripts" / "sm_config.py"
        # Run in a throwaway HOME/XDG_CONFIG to avoid depending on user's real
        # solution-master config (which may or may not exist).
        fake_home = base / "u20-home"
        fake_home.mkdir(exist_ok=True)
        cp = subprocess.run(
            ["python3", str(sm_config), "validate"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
            env={**os.environ, "HOME": str(fake_home)},
        )
        out = cp.stdout + cp.stderr
        bad = []
        # Accept both the old "skill 未安装" wording and the new "plugin 未安装"
        # wording (web-access was promoted from a solution-master skill to an
        # independent plugin in 0.1.6, which shifted the error message).
        if "web-access plugin 未安装" in out or "web-access skill 未安装" in out:
            bad.append("falsely reported web-access as missing")
        if "draw.io skill 未安装" in out or "drawio skill 未安装" in out:
            bad.append("falsely reported drawio as missing")
        if bad:
            r.fail(out[:500], "; ".join(bad))
        else:
            r.ok(f"validate output clean (len={len(out)})")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u24_sm_config_validate_web_access_probe(base: Path) -> TestResult:
    """Exercise the `cdp_sites.enabled=true` branch that U20 does not touch.

    U20 runs with an empty fake HOME, so `cdp_sites.enabled` defaults to
    False and sm_config.py's web-access probe is never entered. This test
    seeds a realistic config fixture with `cdp_sites.enabled: true` + one
    site, forces the probe to fire, and asserts it locates web-access at
    the monorepo sibling candidate (<monorepo>/web-access/skills/web-access/SKILL.md)
    without emitting a 'web-access plugin 未安装' false-miss.
    """
    r = TestResult(
        id="U24",
        name="sm_config.py validate 的 web-access probe 能命中本地 marketplace sibling",
        command="python3 skills/solution-config/scripts/sm_config.py validate (cdp_sites.enabled=true)",
        expected="probe 触发且不误报 'web-access plugin 未安装'",
    )
    try:
        sm_config = REPO_ROOT / "skills" / "solution-config" / "scripts" / "sm_config.py"
        fake_home = base / "u24-home"
        config_dir = fake_home / ".config" / "solution-master"
        config_dir.mkdir(parents=True, exist_ok=True)
        # 用 fake_home 下一个真实存在的目录作为 localkb path（含 .index/ 子目录），
        # 让 validate 的 localkb 检查通过——这样 issues 列表完全为空，rc=0，
        # 测试的"crash detection"启发式（drawio in out）就不再受 issue list 内容影响
        kb_dir = fake_home / "kb"
        (kb_dir / ".index").mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            "localkb:\n"
            f"  path: {kb_dir}\n"
            "cdp_sites:\n"
            "  enabled: true\n"
            "  sites:\n"
            "    - name: Test Site\n"
            "      search_url: https://example.com/search?q={query}\n",
            encoding="utf-8",
        )
        # AI 生图配置由 ai-image plugin 管理；touch 一个空文件以满足 sm_config.validate
        # 的轻量存在检查（绕开"AI 生图配置文件不存在"提示），让测试聚焦 web-access probe
        ai_image_dir = fake_home / ".config" / "presales-skills"
        ai_image_dir.mkdir(parents=True, exist_ok=True)
        (ai_image_dir / "config.yaml").write_text("# placeholder for U24 fixture\n", encoding="utf-8")

        cp = subprocess.run(
            ["python3", str(sm_config), "validate"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
            env={**os.environ, "HOME": str(fake_home)},
        )
        out = cp.stdout + cp.stderr

        # Positive signal that the probe branch actually executed. sm_config.py
        # always runs the drawio probe further down (lines ~311-327), and its
        # output mentions "drawio" somewhere (either as an issue listing
        # drawio.cli_path or as cleanly resolved). Absence of any "drawio"
        # token would indicate sm_config died before validate finished — e.g.
        # pyyaml import failure or subprocess crash — in which case our
        # web-access substring checks would be tautological.
        if cp.returncode != 0 and "drawio" not in out.lower():
            r.fail(out[:500], f"sm_config.py validate crashed before probe ran (rc={cp.returncode})")
            return r

        # Also confirm our config made it to sm_config (enabled + site present).
        # If sm_config silently fell back to defaults (cdp_sites.enabled=False),
        # the web-access branch would never fire and this test would be a
        # tautology. The "cdp_sites 已启用但未配置任何站点" issue only appears
        # when enabled=true AND sites is empty, so its ABSENCE here is expected
        # — what we need is evidence that enabled=true was observed. Reading
        # back the written config directly sidesteps any sm_config quirks.
        if "enabled: true" not in config_path.read_text(encoding="utf-8"):
            r.fail(config_path.read_text(encoding="utf-8")[:200], "fixture config not written as expected")
            return r

        # Core assertion: probe found web-access (no false-miss). Accept
        # both old 'skill' and new 'plugin' wording for forward-compat.
        if "web-access plugin 未安装" in out or "web-access skill 未安装" in out:
            r.fail(out[:500], "probe failed to locate web-access at monorepo sibling — candidate #1 broken?")
            return r

        # Belt-and-suspenders: the monorepo sibling candidate must exist on
        # disk, otherwise a future refactor could make the above assertion
        # vacuously true (e.g., a different candidate found it, or the issue
        # string got renamed).
        sibling = REPO_ROOT.parent / "web-access" / "skills" / "web-access" / "SKILL.md"
        if not sibling.exists():
            r.fail(str(sibling), "monorepo sibling web-access/SKILL.md missing — test env assumption broken")
            return r

        r.ok(f"probe fired, web-access located at sibling (validate output len={len(out)})")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u21_backup_timestamp_millisecond_uniqueness(base: Path) -> TestResult:
    r = TestResult(
        id="U21",
        name="npx 安装连续两次产生不同的 settings.json 备份文件名",
        command="install 两次（同秒内），检查两个 .bak.* 都存在",
        expected="两个备份文件名不同（毫秒级粒度防止覆盖）",
    )
    try:
        proj = base / "u21-proj"
        proj.mkdir(exist_ok=True)
        (proj / ".claude").mkdir(exist_ok=True)
        (proj / ".claude" / "settings.json").write_text(
            '{"permissions":{"allow":["Read"]}}', encoding="utf-8"
        )
        cp1 = run_node(BIN_JS, [], cwd=proj)
        if cp1.returncode != 0:
            r.fail(cp1.stdout + cp1.stderr, "first install failed")
            return r
        cp2 = run_node(BIN_JS, [], cwd=proj)
        if cp2.returncode != 0:
            r.fail(cp2.stdout + cp2.stderr, "second install failed")
            return r
        baks = sorted((proj / ".claude").glob("settings.json.bak.*"))
        if len(baks) < 2:
            r.fail(str([b.name for b in baks]), f"expected ≥2 backup files, got {len(baks)}")
            return r
        r.ok(f"{len(baks)} distinct backups: {[b.name for b in baks]}")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u22_escape_for_json_control_chars(base: Path) -> TestResult:
    r = TestResult(
        id="U22",
        name="session-start 对 SKILL 中的 \\b/\\f 控制字符正确 JSON 转义",
        command="临时用含 \\b\\f 的 SKILL 跑 session-start, 结果必须是合法 JSON",
        expected="stdout 是合法 JSON（Python json.loads 不抛异常）",
    )
    try:
        # Build an isolated SM-like project with a custom using-solution-master
        # SKILL that contains \b and \f control characters.
        proj = base / "u22-proj"
        skill_dir = proj / "skills" / "using-solution-master"
        sw_dir = proj / "skills" / "solution-writing"
        drafts_dir = proj / "drafts"
        hooks_dir = proj / "hooks"
        for d in (skill_dir, sw_dir, drafts_dir, hooks_dir):
            d.mkdir(parents=True, exist_ok=True)
        # SKILL content containing literal \b (0x08) and \f (0x0c) bytes
        content = "header\x08inline\x0cbody\nnext line"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        # Dummy marker so the project gate passes via skills/solution-writing/
        (sw_dir / "SKILL.md").write_text("---\nname: solution-writing\n---\n", encoding="utf-8")
        # Copy session-start into the test project so self-locate points here
        test_hook = hooks_dir / "session-start"
        test_hook.write_bytes(SESSION_START.read_bytes())
        test_hook.chmod(0o755)

        cp = run_bash(test_hook, cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)})
        if cp.returncode != 0:
            r.fail(cp.stdout + cp.stderr, f"exit {cp.returncode}")
            return r
        try:
            obj = json.loads(cp.stdout)
        except json.JSONDecodeError as exc:
            r.fail(cp.stdout[:500], f"invalid JSON: {exc}")
            return r
        hso = obj.get("hookSpecificOutput", {})
        ctx = hso.get("additionalContext", "")
        # After decoding back through JSON, the original control chars should appear
        if "\x08" not in ctx or "\x0c" not in ctx:
            r.fail(repr(ctx)[:500], "expected decoded \\b and \\f to round-trip through JSON")
            return r
        r.ok(f"JSON parse ok, \\b+\\f round-tripped (ctx len={len(ctx)})")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


def test_u23_uninstall_uses_dynamic_skill_list(base: Path) -> TestResult:
    r = TestResult(
        id="U23",
        name="npx --uninstall 动态派生技能列表（drawio 等非硬编码）",
        command="install+uninstall, 确保 skills/drawio 也被清理",
        expected="所有源 skills/ 下的目录都被 uninstall 清理",
    )
    try:
        proj = base / "u23-proj"
        proj.mkdir(exist_ok=True)
        cp1 = run_node(BIN_JS, [], cwd=proj)
        if cp1.returncode != 0:
            r.fail(cp1.stdout + cp1.stderr, "install failed")
            return r
        cp2 = run_node(BIN_JS, ["--uninstall"], cwd=proj)
        if cp2.returncode != 0:
            r.fail(cp2.stdout + cp2.stderr, "uninstall failed")
            return r
        skills_after = proj / ".claude" / "skills"
        if skills_after.exists():
            remaining = [p.name for p in skills_after.iterdir() if p.is_dir()]
            if remaining:
                r.fail(str(remaining), f"leftover skill dirs: {remaining}")
                return r
        r.ok("no leftover skills after uninstall")
    except Exception as exc:
        r.fail(error=str(exc))
    return r


ALL_TESTS: list[tuple[str, Callable]] = [
    ("u1", test_u1_session_start_injection),
    ("u2", test_u2_session_start_gate),
    ("u3", test_u3_session_start_json),
    ("u4", test_u4_plugin_json),
    ("u5", test_u5_hooks_json),
    ("u6", test_u6_package_json),
    ("u7", test_u7_bin_help),
    ("u8", test_u8_bin_version),
    ("u9", test_u9_npx_project_install),
    ("u10", test_u10_npx_backup),
    ("u11", test_u11_npx_merge_preserves_permissions),
    ("u12", test_u12_npx_uninstall),
    ("u13", test_u13_npx_global_install),
    ("u14", test_u14_npx_global_uninstall),
    ("u15", test_u15_vendor_attribution),
    ("u16", test_u16_third_party_notices),
    ("u17", test_u17_drawio_check_reports_installed),
    ("u18", test_u18_solution_writing_no_stale_claude_paths),
    ("u19", test_u19_session_start_cursor_format),
    ("u20", test_u20_sm_config_validate_no_false_missing),
    ("u21", test_u21_backup_timestamp_millisecond_uniqueness),
    ("u22", test_u22_escape_for_json_control_chars),
    ("u23", test_u23_uninstall_uses_dynamic_skill_list),
    ("u24", test_u24_sm_config_validate_web_access_probe),
]


def collect_env_info() -> dict:
    def safe(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return "(n/a)"

    git_sha = "(n/a)"
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        pass

    return {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "bash": safe(["bash", "--version"]).split("\n")[0],
        "node": safe(["node", "--version"]),
        "git_sha": git_sha,
        "cwd": str(REPO_ROOT),
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def render_report(results: list[TestResult], env: dict, e2e_checklist: str) -> str:
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")

    lines: list[str] = []
    lines.append("# Solution Master Plugin 测试报告")
    lines.append("")
    lines.append(f"**生成时间**：{env['timestamp']}")
    lines.append("")
    lines.append("> **重要变更**：2026-04-14 回退了 Layer 3（evidence 文件契约 + PostToolUse/Stop hook）。")
    lines.append("> 本套件现在只覆盖 Layer 1（SessionStart hook 注入铁律）+ 打包制品。")
    lines.append("> Layer 2（强化的子智能体 prompt、不信任报告原则）属于 prompt 工程，在手工 E2E 清单中验证。")
    lines.append("")
    lines.append("## 环境信息")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 操作系统 | {env['os']} |")
    lines.append(f"| Python | {env['python']} |")
    lines.append(f"| Bash | {env['bash']} |")
    lines.append(f"| Node.js | {env['node']} |")
    lines.append(f"| 项目路径 | `{env['cwd']}` |")
    lines.append(f"| Git commit | `{env['git_sha']}` |")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 总用例：**{total}**")
    lines.append(f"- 通过：**{passed}** ✅")
    lines.append(f"- 失败：**{failed}** {'❌' if failed else ''}")
    lines.append("")
    if failed == 0:
        lines.append("**结论：所有自动化单元测试通过。**")
    else:
        lines.append(f"**结论：{failed} 个测试未通过，详见下方失败用例。**")
    lines.append("")
    lines.append("## 测试用例详情")
    lines.append("")
    lines.append("| ID | 名称 | 预期 | 实际 | 结果 |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        expected_short = r.expected.replace("|", "\\|").replace("\n", " ")[:80]
        actual_short = (r.actual or "(empty)").replace("|", "\\|").replace("\n", " ")[:80]
        emoji = {"PASS": "✅", "FAIL": "❌"}.get(r.status, "?")
        lines.append(f"| {r.id} | {r.name} | {expected_short} | {actual_short} | {emoji} {r.status} |")
    lines.append("")

    fails = [r for r in results if r.status == "FAIL"]
    if fails:
        lines.append("## 失败用例完整输出")
        lines.append("")
        for r in fails:
            lines.append(f"### {r.id} — {r.name}")
            lines.append("")
            lines.append(f"- 命令：`{r.command}`")
            lines.append(f"- 预期：{r.expected}")
            if r.actual:
                lines.append("- 实际 stdout/stderr：")
                lines.append("")
                lines.append("```")
                lines.append(r.actual[:2000])
                lines.append("```")
            if r.error:
                lines.append(f"- 错误：{r.error}")
            lines.append("")

    lines.append("## 端到端手工验证清单")
    lines.append("")
    lines.append(
        "以下测试必须在真实 Claude Code 会话中执行，无法自动化。请按步骤跑完并在每项后填写"
        "`PASS` 或 `FAIL` + 备注。"
    )
    lines.append("")
    lines.append(e2e_checklist)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-report", action="store_true", help="skip writing report to ~/Documents")
    parser.add_argument("--report-path", help="override report output path")
    args = parser.parse_args()

    env = collect_env_info()
    print(f"Solution Master plugin test runner @ {env['timestamp']}")
    print(f"  repo: {env['cwd']}")
    print(f"  git: {env['git_sha']}")
    print()

    results: list[TestResult] = []
    with tempfile.TemporaryDirectory(prefix="sm-test-") as tmp:
        tmp_path = Path(tmp)
        for test_id, func in ALL_TESTS:
            try:
                sig_count = func.__code__.co_argcount
                if sig_count == 1:
                    r = func(tmp_path)
                else:
                    r = func()
            except Exception as exc:
                r = TestResult(id=test_id.upper(), name=func.__name__, command="(internal)",
                               expected="(internal)", actual="", status="FAIL", error=str(exc))
            results.append(r)
            emoji = {"PASS": "✅", "FAIL": "❌"}.get(r.status, "?")
            print(f"  {emoji} {r.id}: {r.name}")
            if r.status == "FAIL":
                if r.error:
                    print(f"       error: {r.error}")
                if r.actual:
                    snippet = r.actual.replace("\n", " ")[:200]
                    print(f"       actual: {snippet}")

    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    total = len(results)
    print()
    print(f"Result: {passed}/{total} PASS, {failed} FAIL")

    if not args.no_report:
        e2e_path = REPO_ROOT / "tests" / "run_e2e_checklist.md"
        e2e_text = e2e_path.read_text(encoding="utf-8") if e2e_path.exists() else "(E2E checklist missing)"
        report_md = render_report(results, env, e2e_text)

        if args.report_path:
            report_path = Path(args.report_path).expanduser().resolve()
        else:
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
            report_path = Path.home() / "Documents" / f"solution-master-plugin-test-report-{stamp}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
        print(f"Report written to: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
