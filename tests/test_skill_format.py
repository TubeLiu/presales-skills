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


# ──────────────────────────────────────────────────────────────────────
# taw 重构（C8 新 lint）：标题去编号 / reviewer STATUS / image_plan 字段
# / 单章节模式声明 / SKILL ≤500 行 / docs 已删 / 无残链
# ──────────────────────────────────────────────────────────────────────


def test_taw_writer_emits_correct_heading_format():
    """taw writer.md 必须强约束 ### {h3_title} 起跳、不写编号。

    背景：subagent 自起 `# 1.2` 会让 Word 把 H3 渲染成 H1 / Title；
    多级列表自动加编号时若 heading text 含编号会双重叠加。

    `{h3_numbering}` 占位符可出现在 task description / 上下文识别（让
    subagent 知道自己负责的是哪一节），但**不得**出现在"输出格式"
    指令里——即不得作为标题文本的一部分。
    """
    p = REPO_ROOT / "tender-workflow/skills/taw/agents/writer.md"
    assert p.exists(), f"{p} 不存在"
    content = _read(p)
    assert "### {h3_title}" in content, "writer.md 缺 `### {h3_title}` 输出格式约束"
    # 不允许把 numbering 写进输出标题模板
    bad_patterns = ["### {h3_numbering} {h3_title}", "### {h3_numbering}"]
    for bp in bad_patterns:
        assert bp not in content, (
            f"writer.md 含输出格式 `{bp}`（应删除编号；编号由 docx 多级列表自动生成）"
        )
    assert "禁止使用 `#` 或 `##`" in content, "writer.md 缺禁用 # / ## 顶级标题的强约束"


def test_taw_review_subagents_have_status_protocol():
    """spec/quality reviewer 必须输出 STATUS: DONE / NEEDS_REVISION 协议。"""
    failures = []
    for name in ("spec-reviewer.md", "quality-reviewer.md"):
        p = REPO_ROOT / "tender-workflow/skills/taw/agents" / name
        if not p.exists():
            failures.append(f"{name}: 文件不存在")
            continue
        text = _read(p)
        if "STATUS: DONE" not in text:
            failures.append(f"{name}: 缺 `STATUS: DONE`")
        if "STATUS: NEEDS_REVISION" not in text:
            failures.append(f"{name}: 缺 `STATUS: NEEDS_REVISION`")
    assert not failures, "reviewer STATUS 协议缺失：\n" + "\n".join(failures)


def test_taw_image_plan_field_structure():
    """writing_brief_template.yaml 的 image_plan 列必须用字段化格式
    （path/caption/placement_hint），example 中无图改用空数组 `[]`。
    """
    p = REPO_ROOT / "tender-workflow/skills/taw/prompts/writing_brief_template.yaml"
    assert p.exists()
    content = _read(p)
    assert "path" in content and "caption" in content and "placement_hint" in content, (
        "image_plan 描述缺 path/caption/placement_hint 字段"
    )
    # example 行（| 1.3.x | ... |）中不得用 "无图" / "无" / "待生成" 等字符串
    # 占位（应改为空数组 [] 或字段化对象）
    in_example = False
    for line in content.splitlines():
        if line.strip().startswith("example:"):
            in_example = True
            continue
        if in_example and line.strip().startswith("|"):
            cells = line.split("|")
            if cells:
                last = cells[-2].strip() if len(cells) >= 2 else ""
                bad = ("无图", "无", "待生成", "drawio:待生成", "KB:")
                if last and any(last.startswith(b) for b in bad):
                    raise AssertionError(
                        f"image_plan example 行第 N 列仍用字符串占位 `{last}`，应改为字段化对象或 `[]`"
                    )
        if in_example and line and not line.startswith(" ") and not line.startswith("|"):
            in_example = False


def test_tender_workflow_readme_documents_single_chapter_test_only():
    """tender-workflow/README.md 必须含'单章节模式仅供测试'类说明，
    避免用户在生产用 --chapter 1.3 standalone 然后纠结编号不对。
    """
    p = REPO_ROOT / "tender-workflow/README.md"
    assert p.exists()
    content = _read(p)
    assert "单章" in content and ("测试" in content or "预览" in content), (
        "README 缺单章节 standalone 模式 = 测试/预览 用途的说明"
    )


def test_taw_skill_md_under_500_lines():
    """taw SKILL.md 必须 ≤ 500 行（Anthropic 官方 progressive disclosure 准则）。"""
    p = REPO_ROOT / "tender-workflow/skills/taw/SKILL.md"
    assert p.exists()
    line_count = len(_read(p).splitlines())
    assert line_count <= 500, (
        f"taw SKILL.md {line_count} 行 > 500（按 chujianyun/skill-optimizer 准则需 progressive disclosure 拆分到 references/）"
    )


def test_no_docs_directory_in_tender_workflow():
    """tender-workflow/docs/ 必须不存在（user 要求轻量化 + 删 docs/）。"""
    docs_dir = REPO_ROOT / "tender-workflow/docs"
    assert not docs_dir.exists(), (
        f"{docs_dir} 应已删除（运行时必需信息已迁入 SKILL.md / README.md / docx_writer.py）"
    )


def test_no_dangling_docs_refs_in_tender_workflow():
    """tender-workflow 内任何 .md/.py/.yaml 不得再含 'docs/<name>.md' 或类似残链。

    例外：根 README 列其它 plugin 的链接（不属于 tender-workflow），不在本检查内。
    """
    failures = []
    tw_root = REPO_ROOT / "tender-workflow"
    pat = re.compile(r"docs/[A-Za-z0-9_\-\.]+\.md")
    for p in tw_root.rglob("*"):
        if not p.is_file() or p.suffix not in {".md", ".py", ".yaml"}:
            continue
        try:
            text = _read(p)
        except Exception:
            continue
        for m in pat.finditer(text):
            # 跳过：路径里有 'examples/' / 'tests/'（非生产文档）；
            # 跳过 .py 注释里偶发的 docs 提示
            ctx_line = next((l for l in text.splitlines() if m.group() in l), "")
            failures.append(f"{p.relative_to(REPO_ROOT)}: 残链 `{m.group()}` ({ctx_line.strip()[:80]})")
    assert not failures, "tender-workflow 内残留 docs/ 链接：\n" + "\n".join(failures)


# ════════════════════════════════════════════════════════
# MCP wizard（mcp_installer.py + setup.md Step 4）lint
# ════════════════════════════════════════════════════════

def test_mcp_installer_exists_with_three_providers():
    """web-access mcp_installer.py 必须含 tavily / exa / minimax 三 provider TEMPLATES。"""
    p = REPO_ROOT / "web-access/skills/browse/scripts/mcp_installer.py"
    assert p.exists(), f"{p} 缺失"
    text = _read(p)
    for provider, env_key in (("tavily", "TAVILY_API_KEY"),
                              ("exa", "EXA_API_KEY"),
                              ("minimax", "MINIMAX_API_KEY")):
        assert f'"{provider}":' in text, f"TEMPLATES 缺 {provider}"
        assert env_key in text, f"{provider} 缺 env key {env_key}"
    # minimax 必须含 sk-cp- 校验
    assert "sk-cp-" in text, "minimax 必须强校验 sk-cp- 前缀"
    # 必须含 understand_image（minimax test 双 tool）
    assert "understand_image" in text and "web_search" in text, \
        "minimax test 必须同时跑 web_search + understand_image"


def test_twc_setup_uses_mcp_installer_for_minimax():
    """tender-workflow twc setup.md Step 4 必须含 minimax + sk-cp- + 探针变量。"""
    p = REPO_ROOT / "tender-workflow/skills/twc/setup.md"
    text = _read(p)
    assert "minimax" in text.lower(), "Step 4 应支持 minimax"
    assert "sk-cp-" in text, "minimax key 必须强约束 sk-cp- 前缀"
    assert "WA_INSTALLER" in text or "mcp_installer.py" in text, \
        "Step 4 必须探针引用 web-access mcp_installer，不能 inline 复制 register 逻辑"


def test_sm_setup_uses_mcp_installer_for_minimax():
    """solution-master setup.md §4 必须与 twc 对称：含 minimax + sk-cp- + 探针。"""
    p = REPO_ROOT / "solution-master/skills/go/workflow/setup.md"
    text = _read(p)
    assert "minimax" in text.lower(), "§4 应支持 minimax"
    assert "sk-cp-" in text, "minimax key 必须强约束 sk-cp- 前缀"
    assert "WA_INSTALLER" in text or "mcp_installer.py" in text, \
        "§4 必须探针引用 web-access mcp_installer"


def test_web_access_readme_documents_mcp_installer():
    """web-access README 必须暴露 mcp_installer.py 给外部读者（被其他 wizard 调用）。"""
    p = REPO_ROOT / "web-access/skills/browse/README.md"
    text = _read(p)
    assert "mcp_installer" in text, \
        "web-access README 应说明 mcp_installer.py（presales-skills 集成段）"


def test_tender_workflow_readme_lists_minimax():
    """tender-workflow README 的 ### MCP 搜索工具 段必须把 minimax 列入 provider 表。

    收紧到段内匹配，避免 README 别处偶发提到 'minimax' 字符串（如 ai-image
    后端列表里也含 minimax）造成假阳性。
    """
    p = REPO_ROOT / "tender-workflow/README.md"
    text = _read(p)
    m = re.search(r"###\s+MCP[^\n]*\n([\s\S]+?)(?=\n##\s|\Z)", text)
    assert m, "README 缺 '### MCP …' 小节"
    section = m.group(1)
    assert "minimax" in section.lower(), "MCP 段必须列 minimax provider"
    assert "sk-cp-" in section, "MCP 段必须说明 minimax key 必须 sk-cp- 前缀"


def test_web_access_setup_includes_mcp_step():
    """web-access setup.md 必须含 MCP 搜索工具配置步骤（tavily/exa/minimax + sk-cp-）。

    回归历史：用户报告 `配置 web-access` 只走完 CDP 就结束，没引导 MCP。
    web-access 是 mcp_installer.py 的宿主 plugin，setup wizard 必须主动询问。
    """
    p = REPO_ROOT / "web-access/skills/browse/setup.md"
    text = _read(p)
    assert "mcp_installer.py" in text, \
        "setup.md 必须引用 $SKILL_DIR/scripts/mcp_installer.py"
    for provider in ("tavily", "exa", "minimax"):
        assert provider in text.lower(), f"setup.md 必须列 {provider} provider"
    assert "sk-cp-" in text, "setup.md 必须说明 minimax key 的 sk-cp- 前缀校验"
    assert "SKIP_MCP" in text, \
        "setup.md MCP 步骤必须有 SKIP_MCP 短路标记，避免 AI 跳过该步"


# ════════════════════════════════════════════════════════
# 动态发现 + 选默认 search MCP（list-search-tools 集成）lint
# ════════════════════════════════════════════════════════

def test_taw_allowed_tools_does_not_pin_search_mcp():
    """taw SKILL.md frontmatter 不应在 allowed-tools 里写死 mcp__tavily/exa——
    这违反 'Claude Code 里有什么用什么' 设计：白名单写死会挡住用户后装的新 MCP。
    保留 anythingllm 工具（项目内必需）。
    """
    p = REPO_ROOT / "tender-workflow/skills/taw/SKILL.md"
    text = _read(p)
    m = re.search(r"^allowed-tools:\s*(.+)$", text, re.MULTILINE)
    assert m, "taw SKILL.md 必须有 allowed-tools frontmatter"
    allowed = m.group(1)
    forbidden = ("mcp__tavily__", "mcp__exa__", "mcp__minimax__")
    for tool in forbidden:
        assert tool not in allowed, (
            f"allowed-tools 不应写死 {tool}（动态发现+用户选默认设计要求依赖会话级权限，"
            "首次调用 permission prompt 一次后持久 ok）"
        )
    # 但 anythingllm 工具必须保留
    assert "mcp__plugin_anythingllm" in allowed, \
        "anythingllm 工具是 plugin 内置 MCP（名字稳定+项目内必需），必须保留"


def test_setups_invoke_list_search_tools():
    """twc / sm setup.md §4.4 必须跑 list-search-tools 让用户选默认。
    回归：删了这一步 → priority 永远空 → 工作流只能用 WebSearch，浪费用户配的 MCP。
    """
    for path_rel in (
        "tender-workflow/skills/twc/setup.md",
        "solution-master/skills/go/workflow/setup.md",
    ):
        p = REPO_ROOT / path_rel
        text = _read(p)
        assert "list-search-tools" in text, \
            f"{path_rel} §4.4 必须跑 mcp_installer.py list-search-tools 实时枚举"
        assert "mcp__" in text, \
            f"{path_rel} 必须示例 FQN 格式 mcp__<server>__<tool>"


def test_config_defaults_priority_is_empty():
    """tw_config.py / sm_config.py DEFAULTS.mcp_search.priority 必须是空 []，
    避免老用户更新后被注入硬编码 ['tavily_search', 'exa_search']。
    """
    import importlib.util

    for rel, mod_name in (
        ("tender-workflow/skills/twc/tools/tw_config.py", "tw_cfg_lint"),
        ("solution-master/skills/go/scripts/sm_config.py", "sm_cfg_lint"),
    ):
        spec = importlib.util.spec_from_file_location(mod_name, REPO_ROOT / rel)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        assert m.DEFAULTS["mcp_search"]["priority"] == [], (
            f"{rel} DEFAULTS.mcp_search.priority 必须是 []（让 setup wizard 显式写入）；"
            f"实际：{m.DEFAULTS['mcp_search']['priority']}"
        )
        # LEGACY_ALIAS 表必须存在（兼容老 config）
        assert hasattr(m, "LEGACY_ALIAS"), \
            f"{rel} 必须导出 LEGACY_ALIAS 表（透明迁移老别名 → FQN）"
        assert m.LEGACY_ALIAS["tavily_search"] == "mcp__tavily__tavily_search"
        assert m.LEGACY_ALIAS["exa_search"] == "mcp__exa__web_search_exa"


def test_mcp_installer_has_list_search_tools_subcommand():
    """mcp_installer.py 必须含 list-search-tools 子命令（C1 加的）"""
    p = REPO_ROOT / "web-access/skills/browse/scripts/mcp_installer.py"
    text = _read(p)
    assert "list-search-tools" in text, \
        "mcp_installer.py 必须注册 list-search-tools 子命令"
    assert "_is_web_search_tool" in text, \
        "mcp_installer.py 必须含 _is_web_search_tool 启发式过滤函数"


def test_ai_image_default_size_is_legal_preset():
    """ai_image_config.DEFAULT_CONFIG.default_size 必须是 ALL_IMAGE_SIZES 之一。

    回归 user 报告的 bug：v1.0.0 默认值是字面像素 '2048x2048'，但
    image_gen.py --image_size 只接受 preset (512px/1K/2K/4K)，传字面像素 argparse 拒。
    """
    import importlib.util
    p = REPO_ROOT / "ai-image/skills/gen/scripts/ai_image_config.py"
    spec = importlib.util.spec_from_file_location("ai_image_config_lint", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    size = m.DEFAULT_CONFIG["ai_image"]["default_size"]
    assert size in m.ALL_IMAGE_SIZES, (
        f"DEFAULT_CONFIG.ai_image.default_size = {size!r} 不在 ALL_IMAGE_SIZES "
        f"= {m.ALL_IMAGE_SIZES}；image_gen.py --image_size 会被 argparse 拒"
    )
    ratio = m.DEFAULT_CONFIG["ai_image"].get("default_aspect_ratio")
    assert ratio is not None, \
        "DEFAULT_CONFIG.ai_image 必须含 default_aspect_ratio 字段（C9 加的）"
    assert ratio in m.ALL_ASPECT_RATIOS, (
        f"default_aspect_ratio = {ratio!r} 不在 ALL_ASPECT_RATIOS"
    )


def test_skill_md_bootstrap_uses_heredoc_not_python_dash_c():
    """所有 SKILL.md 的 SKILL_DIR bootstrap 必须用 heredoc（python - <<'PYEOF' ...）
    而不是 $(python3 -c "<多行字符串带引号>")。

    回归历史：用户在 Git Bash on Windows 跑 ai-image setup 时报
        /usr/bin/bash: eval: line 25: syntax error near unexpected token ')'
    根因：Claude Code Bash 工具用 eval 包脚本，eval 处理 $(python -c "...")
    多行字符串内嵌单/双引号时，bash 引号匹配深度算错，把 python 字符串里的 ')'
    误判为 $() 命令替换的结尾。heredoc <<'PYEOF' 把 python 脚本喂 stdin，
    内层不再有引号嵌套，eval 解析稳定。
    """
    pattern_old = 'SKILL_DIR=$(python3 -c "'
    bad_files = []
    for skill_md in REPO_ROOT.glob("*/skills/*/SKILL.md"):
        text = _read(skill_md)
        if pattern_old in text:
            bad_files.append(str(skill_md.relative_to(REPO_ROOT)))
    assert not bad_files, (
        f"以下 SKILL.md 仍用 $(python3 -c \"...\") 写法，Git Bash on Windows 会引号嵌套出错。"
        f"改成 $(python3 - <<'PYEOF'\\n...\\nPYEOF\\n)：\n  " + "\n  ".join(bad_files)
    )


def test_ai_image_setup_md_does_not_offer_pixel_literal():
    """ai-image setup.md §5 不应该列字面像素（'2048x2048' / '1024x1024'）作为 size 候选——
    这些值传给 image_gen.py --image_size 会被 argparse 拒。

    回归 user 报告："默认图片尺寸？（推荐 2048x2048，可选 1K/1024x1024/16:9/9:16 等）"
    这种问法把字面像素和 aspect ratio 混进 size preset 选项。
    """
    p = REPO_ROOT / "ai-image/skills/gen/setup.md"
    text = _read(p)
    # 找 §5 段（"步骤 5" 到下一个 "## " 之间）
    m = re.search(r"##\s*步骤\s*5[^\n]*\n([\s\S]+?)(?=\n##\s|\Z)", text)
    assert m, "setup.md 缺步骤 5 段"
    section = m.group(1)
    forbidden_pixels = ["2048x2048", "1024x1024", "512x512", "4096x4096"]
    for px in forbidden_pixels:
        assert px not in section, (
            f"setup.md §5 不应列字面像素 {px!r}（image_gen.py --image_size "
            f"只接受 preset 1K/2K/4K；字面像素会被 argparse 拒）"
        )
    # 必须含 supported_sizes_for_model 调用（按 model max 过滤候选）
    assert "supported_sizes_for_model" in section, (
        "setup.md §5 必须调 ai_image_config.supported_sizes_for_model 按 model max "
        "过滤候选 size（用户选 model 不支持的 preset → 生图被 model 拒，最差体验）"
    )
    # 必须有 default_aspect_ratio 单独问
    assert "default_aspect_ratio" in section, (
        "setup.md §5 必须单独问 default_aspect_ratio（与 default_size 是独立参数）"
    )
