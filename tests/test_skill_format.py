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


# ---------------------------------------------------------------------------
# v1.0.0 新增：第 10 项 — 跨 sub-skill 引用必须在同 plugin 内
# ---------------------------------------------------------------------------

# Pattern A: $SKILL_DIR/../<X>/...  或 ${SKILL_DIR}/../<X>/...
_PATTERN_A = re.compile(r'\$\{?SKILL_DIR\}?/\.\./([a-z0-9_-]+)/')
# Pattern B: ${...:-$SKILL_DIR/..}/skills/<X>/...（复合形式，如 workflow/knowledge-retrieval.md）
_PATTERN_B = re.compile(r'\$\{[^}]*\$SKILL_DIR/\.\.[^}]*\}/skills/([a-z0-9_-]+)/')


def _plugin_skills_root(md_path: Path):
    """从任意 markdown 路径反推 <plugin>/skills/。"""
    for ancestor in md_path.parents:
        if ancestor.name == "skills" and (ancestor.parent / ".claude-plugin" / "plugin.json").exists():
            return ancestor
    return None


def test_cross_skill_refs_within_plugin():
    """v1.0.0：$SKILL_DIR/../<X>/... 或 ${...:-$SKILL_DIR/..}/skills/<X>/ 中 <X>
    必须是同 plugin 的兄弟 sub-skill 目录。

    覆盖：SKILL.md / setup.md / workflow/*.md / 其它 skills/<X>/ 下的 markdown。
    禁止跨 plugin 用相对路径（Claude Code marketplace cache layout 下不是兄弟）。
    """
    violations = []
    md_files = []
    for plugin_json in REPO_ROOT.glob("*/.claude-plugin/plugin.json"):
        skills_dir = plugin_json.parent.parent / "skills"
        if skills_dir.is_dir():
            md_files.extend(skills_dir.rglob("*.md"))

    for md_path in md_files:
        plugin_skills = _plugin_skills_root(md_path)
        if plugin_skills is None:
            continue
        text = md_path.read_text(encoding="utf-8")
        for sibling in (*_PATTERN_A.findall(text), *_PATTERN_B.findall(text)):
            # 排除非目录段（如 ../tools/<X>.py 中的 tools，那不是跨 sub-skill 而是同 sub-skill 内子目录）
            # ⇒ 同 sub-skill 内 $SKILL_DIR/../tools/ 不应出现，应改 $SKILL_DIR/tools/；这种该报
            #   但跨 sub-skill 兄弟 $SKILL_DIR/../<sibling-skill>/ 应当存在 sibling 目录
            if not (plugin_skills / sibling).is_dir():
                violations.append(
                    f"{md_path.relative_to(REPO_ROOT)}: 引用 sibling sub-skill "
                    f"'{sibling}/' 不在同 plugin 兄弟目录中"
                )

    assert not violations, (
        "跨 sub-skill 引用违反同 plugin 限制（或写错 sibling 名）：\n"
        + "\n".join(violations)
    )


# 故意 name != dir 的 SKILL（distinctive Codex/Cursor slash 优先于 dir 一致性）
# key: SKILL.md 相对路径（POSIX）；value: 期望的 name 字段值（不能改成其它任意值）
_ALLOWED_NAME_DIR_MISMATCH = {
    "ai-image/skills/gen/SKILL.md": "image-gen",
    "solution-master/skills/go/SKILL.md": "solution-master",
}


def test_skill_name_matches_dir():
    """v1.0.0 物理改名后强约束：每个 SKILL.md frontmatter `name:` 字段必须等于
    父目录名。否则 vercel CLI 装到 Codex 时按 name 创建 .agents/skills/<name>/，
    与 Claude Code canonical /<plugin>:<dir> 割裂。

    白名单 _ALLOWED_NAME_DIR_MISMATCH 列出故意 mismatch 的 SKILL（理由：Codex 端
    distinctive slash 优先于 dir 一致性）。每条豁免锁定到 (path, expected_name)
    pair —— 改这两个 SKILL 的 name 也会被 lint 拦下，确保 mismatch 是有意识的。
    """
    failures = []
    for skill in SKILL_FILES:
        text = _read(skill)
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        front = m.group(1)
        name = None
        for line in front.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"').strip("'")
                break
        if name is None:
            continue
        rel = skill.relative_to(REPO_ROOT).as_posix()
        dir_name = skill.parent.name
        if rel in _ALLOWED_NAME_DIR_MISMATCH:
            expected = _ALLOWED_NAME_DIR_MISMATCH[rel]
            if name != expected:
                failures.append(
                    f"{rel}: 白名单要求 name={expected!r}，实际 name={name!r}（"
                    f"如需改 name 请同步更新 _ALLOWED_NAME_DIR_MISMATCH 并写明理由）"
                )
        elif name != dir_name:
            failures.append(
                f"{rel}: name={name!r} != dir={dir_name!r}（如有意 mismatch 请加白名单）"
            )
    assert not failures, "name vs dir 一致性违反：\n" + "\n".join(failures)


# 期望含 <!-- subagent-tool-limit-block --> marker 的 subagent prompt body 文件
# （注册表式 enforce，未来增减 subagent 时改这里 + 加 marker，二者必须同步）
_SUBAGENT_PROMPT_BODIES = [
    "solution-master/skills/go/agents/writer.md",
    "solution-master/skills/go/agents/spec-reviewer.md",
    "solution-master/skills/go/agents/quality-reviewer.md",
    "tender-workflow/skills/taw/agents/writer.md",
    "tender-workflow/skills/taw/agents/spec-reviewer.md",
    "tender-workflow/skills/taw/agents/quality-reviewer.md",
]


def test_subagent_prompt_bodies_have_tool_limit_block():
    """所有 subagent prompt body 文件必须含 <!-- subagent-tool-limit-block --> marker
    （工具限制铁律段）。

    背景：Claude Code background subagent pre-approval 机制下，未声明的 Skill /
    mcp__* / WebFetch / WebSearch 调用会 auto-deny。subagent prompt body 必须自检
    声明工具限制 + 报告 NEEDS_CONTEXT，避免 subagent 自己 try 浪费一轮。
    详见 solution-master/skills/go/SKILL.md §子智能体工具限制。
    """
    failures = []
    for rel in _SUBAGENT_PROMPT_BODIES:
        path = REPO_ROOT / rel
        if not path.exists():
            failures.append(f"{rel}: 文件不存在（_SUBAGENT_PROMPT_BODIES 注册表过时？）")
            continue
        if "subagent-tool-limit-block" not in _read(path):
            failures.append(f"{rel}: 缺少 <!-- subagent-tool-limit-block --> marker")
    assert not failures, "subagent 工具限制铁律段缺失：\n" + "\n".join(failures)
