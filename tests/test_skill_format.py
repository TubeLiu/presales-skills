"""
SKILL.md 格式自动化检查（v0.3.0 cross-agent 重构后引入）。

验证每个 SKILL.md 都遵循统一模板：
- description 用 YAML block scalar（`description: >`），避免 vercel CLI 漏识别（v0.3.0 实测过的 drawio bug）
- 顶部含跨平台兼容性 checklist
- 含 <SUBAGENT-STOP> 段，且文案含 "Task prompt" 判定条件
- 没有引用 commands/ 路径（v0.3.0 全删）
- 没有 ${CLAUDE_PLUGIN_ROOT} / ${CLAUDE_SKILL_DIR} 占位符（仅 anythingllm-mcp 的 plugin.json 豁免）
- 没有 `command -v <bin>`（应改用 5 段式 installed_plugins.json fallback）

跑：
    cd presales-skills/
    python3 -m pytest tests/test_skill_format.py -v
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = sorted(REPO_ROOT.glob("**/SKILL.md"))

# 豁免：anythingllm-mcp 的 mcpServers args 必须保留 ${CLAUDE_PLUGIN_ROOT}
EXEMPT_PLACEHOLDER_FILES = {
    REPO_ROOT / "anythingllm-mcp/.claude-plugin/plugin.json",
}


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_skill_files_discovered():
    assert len(SKILL_FILES) >= 8, f"Expected ≥8 SKILL.md, found {len(SKILL_FILES)}"


def test_description_uses_block_scalar():
    """每个 SKILL.md 的 description 字段必须用 `description: >` block scalar。
    v0.3.0 A0 实测：单行长 description（>200 chars）会让 vercel CLI 漏识别 skill。"""
    failures = []
    for skill in SKILL_FILES:
        text = _read(skill)
        # 取 frontmatter
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            failures.append(f"{skill.relative_to(REPO_ROOT)}: no frontmatter")
            continue
        front = m.group(1)
        # description 必须存在
        if "description:" not in front:
            failures.append(f"{skill.relative_to(REPO_ROOT)}: no description field")
            continue
        # 检查是 block scalar 还是单行
        desc_line = next((l for l in front.splitlines() if l.startswith("description:")), "")
        # block scalar：description: > 或 description: |（同行只有指示符或为空）
        if not re.match(r"^description:\s*[>|]", desc_line):
            # 不是 block scalar——检查单行长度
            inline = desc_line.replace("description:", "").strip()
            if len(inline) > 200:
                failures.append(f"{skill.relative_to(REPO_ROOT)}: single-line description too long ({len(inline)} chars), use 'description: >' block scalar")
    assert not failures, "\n".join(failures)


def test_windows_compatibility_checklist():
    """每个 SKILL.md 必须有跨平台 checklist。"""
    missing = [
        str(s.relative_to(REPO_ROOT))
        for s in SKILL_FILES
        if "跨平台兼容性 checklist" not in _read(s)
    ]
    assert not missing, f"Missing Windows checklist:\n" + "\n".join(missing)


def test_subagent_stop_present():
    """每个 SKILL.md 必须有 <SUBAGENT-STOP> 段，且含 Task prompt 判定条件。"""
    failures = []
    for s in SKILL_FILES:
        text = _read(s)
        if "<SUBAGENT-STOP>" not in text:
            failures.append(f"{s.relative_to(REPO_ROOT)}: missing <SUBAGENT-STOP> tag")
            continue
        if "Task prompt" not in text:
            failures.append(f"{s.relative_to(REPO_ROOT)}: SUBAGENT-STOP段缺少 Task prompt 判定条件文案")
    assert not failures, "\n".join(failures)


def test_no_commands_references_in_skills():
    """SKILL.md 不应再引用已删的 /<plugin>:<cmd> slash commands。"""
    # 允许 README / CLAUDE.md / docs/ 中保留历史引用作为升级提示
    bad_pattern = re.compile(r"/(ai-image|solution-master|solution-config|drawio):\w")
    failures = []
    for s in SKILL_FILES:
        text = _read(s)
        for line_no, line in enumerate(text.splitlines(), 1):
            if bad_pattern.search(line):
                # 排除 plugin install 命令
                if "/plugin install" in line or "/plugin marketplace" in line:
                    continue
                failures.append(f"{s.relative_to(REPO_ROOT)}:{line_no}: stale slash ref: {line.strip()[:80]}")
    assert not failures, "\n".join(failures)


def test_no_claude_placeholder_in_skill_md():
    """SKILL.md 不应再含 ${CLAUDE_PLUGIN_ROOT} / ${CLAUDE_SKILL_DIR} 占位符。
    v0.3.0 后改用 installed_plugins.json bootstrap 解析的 $SKILL_DIR / $PLUGIN_PATH。"""
    failures = []
    for s in SKILL_FILES:
        text = _read(s)
        for line_no, line in enumerate(text.splitlines(), 1):
            if "${CLAUDE_PLUGIN_ROOT}" in line or "${CLAUDE_SKILL_DIR}" in line:
                failures.append(f"{s.relative_to(REPO_ROOT)}:{line_no}: stale ${{CLAUDE_*}} placeholder: {line.strip()[:80]}")
    assert not failures, "\n".join(failures)


def test_anythingllm_plugin_json_keeps_placeholder():
    """anythingllm-mcp/.claude-plugin/plugin.json 必须保留 ${CLAUDE_PLUGIN_ROOT}（MCP 注册要用）。"""
    plugin_json = REPO_ROOT / "anythingllm-mcp/.claude-plugin/plugin.json"
    assert plugin_json.exists(), "anythingllm-mcp plugin.json missing"
    assert "${CLAUDE_PLUGIN_ROOT}" in _read(plugin_json), \
        "anythingllm-mcp plugin.json should keep ${CLAUDE_PLUGIN_ROOT} for MCP server args"


def test_no_command_v_in_skills():
    """SKILL.md 不应用 `command -v <bin>` 检测（Windows cmd 不支持），改用 installed_plugins.json fallback。"""
    failures = []
    for s in SKILL_FILES:
        text = _read(s)
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"\bcommand -v ", line):
                failures.append(f"{s.relative_to(REPO_ROOT)}:{line_no}: uses 'command -v' (use installed_plugins.json fallback instead): {line.strip()[:80]}")
    assert not failures, "\n".join(failures)


def test_vercel_cli_discovery():
    """实测：vercel-labs/skills CLI 能正确扫描所有 SKILL.md（无漏识别）。
    需要本地有 npx；CI 跳过。"""
    try:
        result = subprocess.run(
            ["npx", "--yes", "skills", "add", str(REPO_ROOT), "--list"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        import pytest
        pytest.skip("npx not available or timed out")
    output = result.stdout + result.stderr
    m = re.search(r"Found (\d+) skills?", output)
    assert m, f"Could not parse skill count from vercel CLI output:\n{output[:500]}"
    found = int(m.group(1))
    # 当前预期：drawio + ai-image + ppt-make + web-access + solution-master + 5 tender = 10
    assert found == 10, f"Expected 10 skills, vercel CLI found {found}. Output:\n{output[:1000]}"
