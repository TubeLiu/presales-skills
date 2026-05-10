---
name: make
description: >
  PPT 生成器——将 PDF/DOCX/URL/Markdown 等多源文档转换为原生可编辑的 PPTX
  （含真实 PowerPoint shape、文本框、图表，非图片）。
  触发场景：当用户说"做 PPT"、"生成 PPT"、"做演示稿"、"做 PowerPoint"、
  "把这份文档做成 PPT"、"生成PPT"、"制作演示文稿"、"generate PPT"、
  "create slides"、"make presentation"、"create deck" 时自动调用。
  SVG 中间层 + 13 provider AI 配图，支持 16:9 / 4:3 / 小红书 / 朋友圈 / Story 多版式。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# PPT Master Skill

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析（替代 `$SKILL_DIR`）。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

## 不可妥协的硬约束（首屏）

写第一行 SVG 之前必须先吃透这两条：

1. **SVG 输出禁用** `mask` / `<style>` / `class` / `<foreignObject>` / `textPath` / `@font-face` / `<animate*>` / `<script>` / `<iframe>` / `<symbol>+<use>`
   完整列表 + 替代方案见 `references/shared-standards.md` §1.1
   **执行拦截**：Step 6 Quality Check（全 7 维：`svg_quality_checker.py <project_path>`）+ Step 7.0 入口（3 维子集：`--lint`）双闸

2. **文字溢出 → 走 speaker notes**，**严禁缩字号 / 缩行高 / 写画布外**
   详细规则见 §Step 6.5 + `references/overflow-fallback.md`
   **执行拦截**：`svg_quality_checker.py` 第 5 维「文本换行」warning（proxy 信号；false negative 时 AI 必须按 Step 6.5 5 条禁令自查）

其它 3 条流程纪律（已写在文档其他位置，不重复）：
- `spec_lock.md` 颜色 / 字体 / 图标 re-read：见 §Global Execution Discipline
- 后处理三步 sequential、严禁 `cp` 替代 `finalize_svg.py`：见 §Step 7 + §Gotchas
- AI **不许直接 Read 图片**，必须走 `analyze_images.py`：见 §Step 5 + §Gotchas

---

## 路径自定位

**首次调用本 skill 的脚本前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/scripts/...`、`$SKILL_DIR/templates/...`）：

```bash
SKILL_DIR=$(python3 - <<'PYEOF' 2>/dev/null
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/ppt-master/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/make'); sys.exit(0)
PYEOF
)

# vercel CLI fallback (skill subdir is 'make'; SKILL.md name is also 'make')
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/ppt-master/skills/make" ] && SKILL_DIR="$d/ppt-master/skills/make" && break
    [ -d "$d/make" ] && SKILL_DIR="$d/make" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${PPT_MASTER_PLUGIN_PATH:-}" ] && SKILL_DIR="$PPT_MASTER_PLUGIN_PATH/skills/make"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./ppt-master/skills/make" ] && SKILL_DIR="$(pwd)/ppt-master/skills/make"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 ppt-master skill 安装位置。" >&2
    echo "请设置：export PPT_MASTER_PLUGIN_PATH=/path/to/ppt-master" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install ppt-master@presales-skills` 或手工 export 环境变量。

> AI-driven multi-format SVG content generation system. Converts source documents into high-quality SVG pages through multi-role collaboration and exports to PPTX.

**Core Pipeline**: `Source Document → Create Project → Template Option → Strategist → [Step 4.5 User Review Gate] → [Image_Generator] → Executor → Post-processing → Export`

> [!CAUTION]
> ## 🚨 Global Execution Discipline (MANDATORY)
>
> **This workflow is a strict serial pipeline. The following rules have the highest priority — violating any one of them constitutes execution failure:**
>
> 1. **SERIAL EXECUTION** — Steps MUST be executed in order; the output of each step is the input for the next. Non-BLOCKING adjacent steps may proceed continuously once prerequisites are met, without waiting for the user to say "continue"
> 2. **BLOCKING = HARD STOP** — Steps marked ⛔ BLOCKING require a full stop; the AI MUST wait for an explicit user response before proceeding and MUST NOT make any decisions on behalf of the user
> 3. **NO CROSS-PHASE BUNDLING** — Cross-phase bundling is FORBIDDEN. (Note: the Nine Confirmations in Step 4 are ⛔ BLOCKING — the AI MUST present recommendations and wait for explicit user confirmation before proceeding. Once the user confirms, all subsequent non-BLOCKING steps — design spec output, SVG generation, speaker notes, and post-processing — may proceed automatically without further user confirmation)
> 4. **GATE BEFORE ENTRY** — Each Step has prerequisites (🚧 GATE) listed at the top; these MUST be verified before starting that Step
> 5. **NO SPECULATIVE EXECUTION** — "Pre-preparing" content for subsequent Steps is FORBIDDEN (e.g., writing SVG code during the Strategist phase)
> 6. **NO SUB-AGENT SVG GENERATION** — Executor Step 6 SVG generation is context-dependent and MUST be completed by the current main agent end-to-end. Delegating page SVG generation to sub-agents is FORBIDDEN
> 7. **SEQUENTIAL PAGE GENERATION ONLY** — In Executor Step 6, after the global design context is confirmed, SVG pages MUST be generated sequentially page by page in one continuous pass. Grouped page batches (for example, 5 pages at a time) are FORBIDDEN
> 8. **SPEC_LOCK RE-READ PER PAGE** — Before generating each SVG page, Executor MUST `read_file <project_path>/spec_lock.md`. All colors / fonts / icons / images MUST come from this file — no values from memory or invented on the fly. Executor MUST also look up the current page's `page_rhythm` tag and apply the matching layout discipline (`anchor` / `dense` / `breathing` — see executor-base.md §2.1). This rule exists to resist context-compression drift on long decks and to break the uniform "every page is a card grid" default
> 9. **GATE STATE FILES OVERRIDE AI MEMORY** — Every BLOCKING confirmation (Step 4 nine confirmations, Step 4.5 design review, Step 4.5 ⑤ audio choice) must be persisted by Strategist to `<project_path>/.gates/<gate>.json` after the user replies with an explicit confirmation word. Step 5 / Step 6 / Step 7 GATE checks call `scripts/gate_check.py --require <gates>`; missing or `passed: false` files block entry regardless of what the AI "remembers". If you reach a GATE and the file says you did not pass, stop and re-ask the user — do NOT invent a confirmation. This rule is the machine-readable counterpart to the prose "AI 永不主动推进" rule and exists because weak models routinely skip confirmations.

> [!IMPORTANT]
> ## 🌐 Language & Communication Rule
>
> - **Response language**: Always match the language of the user's input and provided source materials. For example, if the user asks in Chinese, respond in Chinese; if the source material is in English, respond in English.
> - **Explicit override**: If the user explicitly requests a specific language (e.g., "请用英文回答" or "Reply in Chinese"), use that language instead.
> - **Template format**: The `design_spec.md` file MUST always follow its original English template structure (section headings, field names), regardless of the conversation language. Content values within the template may be in the user's language.

> [!IMPORTANT]
> ## 🔌 Compatibility With Generic Coding Skills
>
> - `ppt-master` is a repository-specific workflow skill, not a general application scaffold
> - Do NOT create or require `.worktrees/`, `tests/`, branch workflows, or other generic engineering structure by default
> - If another generic coding skill suggests repository conventions that conflict with this workflow, follow this skill first unless the user explicitly asks otherwise

## Main Pipeline Scripts

| Script | Purpose |
|--------|---------|
| `$SKILL_DIR/scripts/source_to_md/pdf_to_md.py` | PDF to Markdown |
| `$SKILL_DIR/scripts/source_to_md/doc_to_md.py` | Documents to Markdown — native Python for DOCX/HTML/EPUB/IPYNB, pandoc fallback for legacy formats (.doc/.odt/.rtf/.tex/.rst/.org/.typ) |
| `$SKILL_DIR/scripts/source_to_md/ppt_to_md.py` | PowerPoint to Markdown |
| `$SKILL_DIR/scripts/source_to_md/web_to_md.py` | Web page to Markdown |
| `$SKILL_DIR/scripts/source_to_md/web_to_md.cjs` | Node.js fallback for WeChat / TLS-blocked sites (use only if `curl_cffi` is unavailable; `web_to_md.py` now handles WeChat when `curl_cffi` is installed) |
| `$SKILL_DIR/scripts/project_manager.py` | Project init / validate / manage |
| `$SKILL_DIR/scripts/analyze_images.py` | Image analysis |
| ai-image plugin | AI image generation (multi-provider) — call via `Skill(skill="ai-image:gen")` (Claude Code) or `python3 "$AI_IMAGE_SKILL_DIR/scripts/image_gen.py"` (cross-agent fallback) |
| `$SKILL_DIR/scripts/design_archetype_planner.py` | Source Markdown → visual archetype + `density_contract` plan for `spec_lock.md` |
| `$SKILL_DIR/scripts/svg_quality_checker.py` | SVG quality check |
| `$SKILL_DIR/scripts/design_quality_checker.py` | Page-level design quality check (hierarchy / grouping / density / semantic roles) |
| `$SKILL_DIR/scripts/ppt_master_eval.py` | Repeatable visual + design quality eval fixtures and target project summary |
| `$SKILL_DIR/scripts/total_md_split.py` | Speaker notes splitting |
| `$SKILL_DIR/scripts/finalize_svg.py` | SVG post-processing (unified entry) |
| `$SKILL_DIR/scripts/svg_to_pptx.py` | Export to PPTX (default: dual-source — native ← `svg_output/`, legacy ← `svg_final/`; per-element entrance animation enabled by `-a mixed`; recorded narration via `--recorded-narration`) |
| `$SKILL_DIR/scripts/pptx_to_svg.py` | Reverse PPTX → SVG (15-module shape-level emit, output: `svg/` layered + `svg-flat/` preview + `assets/`) |
| `$SKILL_DIR/scripts/notes_to_audio.py` | Per-slide narration audio (default `edge-tts`, optional `elevenlabs` / `minimax` / `qwen` / `cosyvoice` backends — see `workflows/generate-audio.md`) |
| `$SKILL_DIR/scripts/check_annotations.py` | Visual edit annotation checker (used by `workflows/visual-edit.md`) |
| `$SKILL_DIR/scripts/source_to_md/excel_to_md.py` | Excel → Markdown ingestion |
| `$SKILL_DIR/scripts/svg_editor/server.py` | Localhost Flask SVG annotation editor (port 5000) — see `workflows/visual-edit.md` |
| `$SKILL_DIR/scripts/register_template.py` | Sync a layout's `design_spec.md` → `layouts_index.json` + `README.md` |
| `$SKILL_DIR/scripts/update_spec.py` | Propagate a `spec_lock.md` color / font_family change across all generated SVGs |

For complete tool documentation, see `$SKILL_DIR/scripts/README.md`.

## Template Index

| Index | Path | Purpose |
|-------|------|---------|
| Layout templates | `$SKILL_DIR/templates/layouts/layouts_index.json` | Query available page layout templates |
| Visualization templates | `$SKILL_DIR/templates/charts/charts_index.json` | Query available visualization SVG templates (charts, infographics, diagrams, frameworks) |
| Icon library | `$SKILL_DIR/templates/icons/` | Search icons on demand: `ls templates/icons/<library>/ \| grep <keyword>` (libraries: `chunk/`, `tabler-filled/`, `tabler-outline/`) |

## Standalone Workflows

| Workflow | Path | Purpose |
|----------|------|---------|
| `create-template` | `workflows/create-template.md` | Standalone template creation workflow |
| `topic-research` | `workflows/topic-research.md` | Pre-pipeline source-acquisition when user supplies only a topic (no source files) |
| `generate-audio` | `workflows/generate-audio.md` | Per-slide narration audio + recorded timing (post-pipeline; pairs with `svg_to_pptx.py --recorded-narration`) |
| `resume-execute` | `workflows/resume-execute.md` | Resume a partially-run pipeline from any phase |
| `verify-charts` | `workflows/verify-charts.md` | Visual chart verification gate |
| `visual-edit` | `workflows/visual-edit.md` | Browser-based SVG annotation editor (`svg_editor/`) + post-hoc applier (`check_annotations.py`) |

---

## Workflow

### Step 1: Source Content Processing

🚧 **GATE**: User has provided source material (PDF / DOCX / EPUB / URL / Markdown file / text description / conversation content — any form is acceptable).

When the user provides non-Markdown content, convert immediately:

| User Provides | Command |
|---------------|---------|
| PDF file | `python3 $SKILL_DIR/scripts/source_to_md/pdf_to_md.py <file>` |
| DOCX / Word / Office document | `python3 $SKILL_DIR/scripts/source_to_md/doc_to_md.py <file>` |
| PPTX / PowerPoint deck | `python3 $SKILL_DIR/scripts/source_to_md/ppt_to_md.py <file>` |
| EPUB / HTML / LaTeX / RST / other | `python3 $SKILL_DIR/scripts/source_to_md/doc_to_md.py <file>` |
| Web link | `python3 $SKILL_DIR/scripts/source_to_md/web_to_md.py <URL>` |
| WeChat / high-security site | `python3 $SKILL_DIR/scripts/source_to_md/web_to_md.py <URL>` (requires `curl_cffi`; falls back to `node web_to_md.cjs <URL>` only if that package is unavailable) |
| Markdown | Read directly |

**✅ Checkpoint — Confirm source content is ready, proceed to Step 2.**

---

### Step 2: Project Initialization

🚧 **GATE**: Step 1 complete; source content is ready (Markdown file, user-provided text, or requirements described in conversation are all valid).

```bash
python3 $SKILL_DIR/scripts/project_manager.py init <project_name> --format <format>
```

Format options: `ppt169` (default), `ppt43`, `xhs`, `story`, etc. For the full format list, see `references/canvas-formats.md`.

Import source content (choose based on the situation):

| Situation | Action |
|-----------|--------|
| Has source files (PDF/MD/etc.) | `python3 $SKILL_DIR/scripts/project_manager.py import-sources <project_path> <source_files...>` |
| User provided text directly in conversation | No import needed — content is already in conversation context; subsequent steps can reference it directly |

> 🛡️ **默认行为：保留用户原文件**。`import-sources` 不带 flag 时：
> - **用户提供的、位于 repo 之外**的源文件 → **复制**到 `sources/`，原位置文件保留（不要让用户丢文件）
> - 位于本 repo 内部的源文件（如 `examples/` 中的演示文件）→ 自动 move 进 `sources/` 并打 stderr note，避免误提交未跟踪产物
> - 显式 override：`--move` 强制 move（仅在用户明确要求"搬走原文件"时使用）；`--copy` 强制 copy
> - `_files/` 等伴生资源目录由 `import-sources` 自动同步处理

**✅ Checkpoint — Confirm project structure created successfully, `sources/` contains all source files, converted materials are ready. Proceed to Step 3.**

---

### Step 3: Template Option

🚧 **GATE**: Step 2 complete; project directory structure is ready.

**Default path — Alauda 模板（自 v1.4.0 起开箱即用）。** AI 直接套用 Alauda 品牌视觉规范（页面 footer + 左边竖条 accent + 装饰圆形 + 颜色/字体/卡片样式）。no per-page free-design discretion on chrome/footer/header — content area lays out freely within the alauda design contract.

> ⚠️ **覆盖优先级**：`~/.config/presales-skills/config.yaml` 中 `ppt_master.default_layout` 字段（如有）> 默认 `alauda`。设为空串 `""` 显式回退到 free design（无 chrome 模板）。

```bash
# 读 user 配置覆盖（如有），未配置 → 默认 alauda；显式空串 → free design（不拷模板）
DEFAULT_LAYOUT=$(python3 -c "
import os
try:
    import yaml
    p = os.path.expanduser('~/.config/presales-skills/config.yaml')
    d = yaml.safe_load(open(p)) or {}
    val = d.get('ppt_master', {}).get('default_layout', None)
    print('alauda' if val is None else val)
except Exception:
    print('alauda')
" 2>/dev/null || echo 'alauda')

if [ -n "$DEFAULT_LAYOUT" ]; then
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/*.svg <project_path>/templates/
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/design_spec.md <project_path>/templates/
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/semantic_routes.json <project_path>/templates/ 2>/dev/null || true
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/visual_system.json <project_path>/templates/ 2>/dev/null || true
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/human_quality_rubric.json <project_path>/templates/ 2>/dev/null || true
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/component_library.md <project_path>/templates/ 2>/dev/null || true
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/*.png <project_path>/images/ 2>/dev/null || true
    cp ${SKILL_DIR}/templates/layouts/${DEFAULT_LAYOUT}/*.jpg <project_path>/images/ 2>/dev/null || true
fi
```

Proceed to Step 4. 默认 = alauda；config 显式 override = 用 override；config 显式空串 = AI free design（极少数场景，例如做 internal 草图或纯 brand-neutral 输出）。

**切换到其它模板 — 三种 trigger：**

1. **用户明说具体模板**（如 "用 mckinsey 模板" / "use the academic_defense template"）—— 把命令中的 `$DEFAULT_LAYOUT` 替换为指定模板名
2. **用户明说风格 / brand 引用映射到某模板**（如 "McKinsey 那种" / "Google style" / "学术答辩样式"）—— 读 `$SKILL_DIR/templates/layouts/layouts_index.json` 解析匹配，把命令中的 `$DEFAULT_LAYOUT` 替换为匹配到的模板名
3. **用户问 "有哪些模板可以用"**（列表）—— 读 `$SKILL_DIR/templates/layouts/layouts_index.json`，列出所有可用模板，等用户选

**Soft hint (non-blocking, optional).** Before Step 4, if the user's content is a strong match for a NON-Alauda template (e.g., clearly an academic defense matching `academic_defense`, or a government-style report matching `government_blue`/`government_red`) AND the user has given no template signal, the AI MAY emit a single-sentence notice and continue with the default alauda without waiting:

> Note: 内容看起来更适合 `<name>` 模板（学术答辩 / 政府报告等非通用 B2B 场景）。说一声如果想换；否则我继续用默认的 Alauda。

This is a hint, not a question — do NOT block, do NOT require an answer. Skip the hint entirely when the content fits the default Alauda B2B-tech tone.

> To create a new global template, read `workflows/create-template.md`

**✅ Checkpoint — Default path copies Alauda template files to project (templates/, images/), then proceeds to Step 4 without user interaction. If a non-default template trigger fired, that template's files are copied instead.**

---

### Step 4: Strategist Phase (MANDATORY — cannot be skipped)

🚧 **GATE**: Step 3 complete; default Alauda template files copied to project (templates/ + images/), OR (if triggered) the user-selected template's files copied, OR (if config set `default_layout: ""`) no template files copied (free design).

First, read the role definition:
```
Read references/strategist.md
```

> ⚠️ **Mandatory gate in `strategist.md`**: Before writing `design_spec.md`, Strategist MUST `read_file templates/design_spec_reference.md` and produce the spec following its full I–XI section structure. See `strategist.md` Section 1 for the explicit gate rule.

**Must complete the Nine Confirmations** (full template structure in `templates/design_spec_reference.md`):

⛔ **BLOCKING**: The Nine Confirmations MUST be presented to the user as a bundled set of recommendations, and you MUST **wait for the user to confirm or modify** before outputting the Design Specification & Content Outline. This is the single core confirmation point in the workflow. Once the user explicitly confirms, Strategist MUST persist the result to `<project_path>/.gates/nine_confirmations.json` (see schema below); after that, subsequent non-BLOCKING script execution and slide generation proceed automatically.

1. Canvas format
2. Page count range
3. Target audience
4. **Template + Layout Grammar** — which template package was copied in Step 3 (default `alauda`, or any user-selected layout); for branded templates with a route catalog, declare that non-structural pages will be routed via `semantic_routes.json` to specific variants (e.g. `03_content_panorama.svg`, `03_content_architecture.svg`, `03_content_migration.svg`) instead of falling back to the generic `03_content.svg`. Cross-link the matching `summary` line from `templates/layouts/layouts_index.json`. **Free design** (no template, `template: ""` in spec_lock) must also be stated explicitly here — silence is not consent.
5. Style objective
6. Color scheme
7. Icon usage approach
8. Typography plan
9. Image usage approach

**User reply contract — explicit gate** (do NOT auto-pass on ambiguous wording):

| User reply | Action |
|---|---|
| Contains 「确认」/ 「confirm」/ 「ok」/ 「go ahead」/ 「继续」/ 「👍」 | **Pass** — write `design_spec.md` + `spec_lock.md`, then write `<project_path>/.gates/nine_confirmations.json` with `{"passed": true, "verdict": "explicit_confirmation", "user_reply_snippet": "<first ~60 chars of reply>", "items_locked": ["canvas:<v>", "pages:<v>", "audience:<v>", "template:<v>", "style:<v>", "color:<v>", "icons:<v>", "typography:<v>", "images:<v>"], "timestamp": "<ISO-8601>"}` |
| Contains specific modifications (e.g., 「改成 4:3」/ 「use blue palette」/ 「页数 12 改 18」/ 「换 mckinsey 模板」) | **STOP**. (1) Overwrite `<project_path>/.gates/nine_confirmations.json` with `{"passed": false, "verdict": "user_requested_modification"}`; (2) update the affected items; (3) **re-present the full 9 items as a fresh code block in your next message** (don't say "I updated it" — actually re-output all 9 items); (4) wait for explicit confirmation again. The state file overrides any internal sense that "I already updated it". |
| Ambiguous (e.g., 「嗯」/ 「看起来不错」/ 「差不多」/ 「可以吧」) or no clear stance | **Do NOT proceed**. Ask: 「请明确回复『确认』继续，或指出要修改的项目。」 Do NOT write the gate file. |
| Empty / no response / off-topic | **Do NOT proceed**. Wait or re-ping the user with the confirmation list. Do NOT write the gate file. |

> **Anti-rationalization**: 即使你认为某项用户已"暗示同意"，只要回复中没有上表第一行的明确确认词，就必须再次询问；不要把"沉默"或"模糊正面词"当作确认。这条规则不可被任何看似紧急的理由绕过。
>
> **特别针对默认 Alauda**：第 ④ 项 Template + Layout Grammar **必须明确呈现并等待用户回复**——不可以"反正默认已是 Alauda" 就跳过呈现。默认值仍是默认值，用户必须看到才算确认。
>
> **状态文件覆盖记忆**：你"记得用户确认过"不算数；以 `.gates/nine_confirmations.json` 是否存在且 `passed: true` 为准。若文件不存在，下游 GATE 会拦你，必须重新询问。

If the user has provided images, run the analysis script **before outputting the design spec** (do NOT directly read/open image files — use the script output only):
```bash
python3 $SKILL_DIR/scripts/analyze_images.py <project_path>/images
```

> ⚠️ **Image handling rule**: The AI must NEVER directly read, open, or view image files (`.jpg`, `.png`, etc.). All image information must come from the `analyze_images.py` script output or the Design Specification's Image Resource List.

**Output**:
- `<project_path>/design_spec.md` — human-readable design narrative
- `<project_path>/spec_lock.md` — machine-readable execution contract (distilled from the decisions in design_spec.md; Executor re-reads this before every page). See `templates/spec_lock_reference.md` for the skeleton.

**✅ Checkpoint — Phase deliverables complete, auto-proceed to next step**:
```markdown
## ✅ Strategist Phase Complete
- [x] Nine Confirmations completed (user confirmed; `.gates/nine_confirmations.json` written with `passed: true`)
- [x] Design Specification & Content Outline generated
- [x] Execution lock (spec_lock.md) generated
- [ ] **Next**: Step 4.5 design review gate, then [Image_Generator / Executor] phase
```

---

### Step 4.5: 设计方案用户复核 Gate (MANDATORY — 不可跳过)

🚧 **GATE**: Step 4 完成；九项确认通过且 `.gates/nine_confirmations.json` 存在 `passed: true`；Design Specification & Content Outline 已生成。

```bash
python3 $SKILL_DIR/scripts/gate_check.py <project_path> --require nine_confirmations
python3 $SKILL_DIR/scripts/spec_lock_validator.py <project_path>
```

非零退出 = 不可进入本步；按 stderr 提示回 Step 4 修复。

⛔ **BLOCKING**: 用户未明确确认 `design_review.md` 之前禁止进入 Step 5 / Step 6 / 单跑 ai-image。AI MUST wait for explicit user confirmation。

Strategist 必须输出 `<project_path>/design_review.md` 并暂停等待用户确认。

`design_review.md` 必含 5 项：① 选定模板 + 简短理由（cross-link `templates/layouts/layouts_index.json` 中本模板 entry 的 `summary` 字段）② 页数 + 一级大纲 ③ Image_Generator 触发列表 ④ 质量样张轮换页（来自 `spec_lock.md ## quality_samples`，用于人工感/客户可发布度检查）⑤ **配音 / 音频策略**（`audio_mode` ∈ `none | edge_default | cloud_quality | recorded_existing`，详见 `references/design-review-gate.md` ⑤ 节）。其它细节（主题色 / 字体 / 节奏）从 `spec_lock.md` 链接，不复述。

用户回复判定：**复用 Step 4 user reply contract**（同上文九项确认表）。用户明确确认后，Strategist MUST 写两份 gate 文件：`<project_path>/.gates/design_review.json` 与 `<project_path>/.gates/audio_choice.json`，schema 同 nine_confirmations.json（`audio_choice.json` 额外含 `audio_mode` 字段记录 ⑤ 项决策）。未确认前禁止进入 Step 5 / Step 6 / 单跑 ai-image。**AI 在等待用户确认时永不主动推进**——下次 AI 输出时优先追问而非继续执行（AI 无真实计时能力，不依赖"超时"概念）。

**写完 design_review.md 与两份 gate 文件后立即跑 audio decision 校验**（v1.6.0 新增——拦"AI 漏写 ⑤ 项 / 不写 audio_choice.json"的同源失效）：

```bash
python3 $SKILL_DIR/scripts/audio_decision_validator.py <project_path>
```

非零退出 = ⑤ 项缺失或 audio_choice.json 缺失，**必须**回 Step 4.5 重做 design_review.md（重新呈现 ⑤ 项给用户选）；不可以默认 `audio_mode == "none"` 跳过——「沉默 ≠ 不要音频」，沉默是「AI 漏问」。

详细产物模板与边界 case（用户改主意 / 模糊正面词不算确认）见 `references/design-review-gate.md`。

---

### Step 5: Image_Generator Phase (Conditional)

🚧 **GATE**: Step 4.5 complete; user has explicitly confirmed `design_review.md` and `.gates/design_review.json` shows `passed: true`.

```bash
python3 $SKILL_DIR/scripts/gate_check.py <project_path> --require nine_confirmations,design_review
```

非零退出 = 不可进入本步；按 stderr 提示回 Step 4.5 重新呈现 `design_review.md`。

> **Trigger condition**: Image approach includes "AI generation". If not triggered, skip directly to Step 6 (Step 6 GATE must still be satisfied).

Read `references/image-generator.md`

> 💡 **结构化场景优先用模板**：如设计 spec 里某张图是 Bento grid 信息图、聊天截图、ER 图、流程图、教育图解 slide、政策风 slide、图形摘要等结构化类型，**先 Read `$AI_IMAGE_SKILL_DIR/templates/<category>/<template>.md`**（17 个类别速查见 ai-image SKILL.md §模板驱动生成），按模板填槽位生成 prompt，再交 image_prompts.md / Skill 调用。模板能锁住 PPT 配图美学，避免每次靠自由 prompt 反复试。

1. Extract all images with status "pending generation" from the design spec
2. Generate prompt document → `<project_path>/images/image_prompts.md`
3. Generate images via the ai-image plugin (v1.0.0 已删 `image-gen` bin，c983037）。Claude Code 推荐用 Skill tool：
   ```
   Skill(skill="ai-image:gen")
   ```
   或自然语言："使用 ai-image 生成 <主题> 的 <16:9 / 1K> 图片到 `<project_path>/images/`"。

   跨 agent fallback（Cursor / Codex 等）：先按 ai-image SKILL.md §路径自定位 解析 `$AI_IMAGE_SKILL_DIR`，再调底层脚本：
   ```bash
   python3 "$AI_IMAGE_SKILL_DIR/scripts/image_gen.py" "<prompt>" \
     --aspect_ratio 16:9 --image_size 1K -o <project_path>/images
   ```

**✅ Checkpoint — Confirm all images are ready, proceed to Step 6**:
```markdown
## ✅ Image_Generator Phase Complete
- [x] Prompt document created
- [x] All images saved to images/
```

---

### Step 6: Executor Phase

🚧 **GATE**: Step 4.5 complete (user has explicitly confirmed `design_review.md`); Step 5 complete if triggered; all prerequisite deliverables are ready.

```bash
python3 $SKILL_DIR/scripts/gate_check.py <project_path> --require nine_confirmations,design_review
python3 $SKILL_DIR/scripts/spec_lock_validator.py <project_path>
python3 $SKILL_DIR/scripts/page_skeleton_seeder.py <project_path>
```

非零退出 = 不可进入本步。`spec_lock_validator.py` 是把"模板退化为只剩配色"的根因封死的硬契约——若 `## template_lock` 缺失或 `## semantic_routes` 与模板包不一致，必须回 Step 4 让 Strategist 修补 spec_lock.md。

> **新 (v1.6.0 — Pillar K 骨架预播)**：`page_skeleton_seeder.py` 自动把每页对应的模板 SVG 物理复制为 `<project>/svg_output/slide_<NN>_<intent>.skeleton.svg`，保留 chrome（左竖条 / footer 横线 / 装饰圆形 / logo）原样并把 content slot 文本替换为 `{{TITLE}}` / `{{KEY_MESSAGE}}` / `{{CONTENT}}` 占位符。**Executor 必须 `read_file` skeleton 文件，基于其增量修改**——不要新建空白 SVG 从零开始；不要删除 chrome 元素；生成完成后 rename `*.skeleton.svg` → `*.svg`。这把"读模板"从认知动作转化为物理起点。
>
> **新 (v1.6.0 — Pillar G + H Hard GATE + chrome checker)**：每页生成时 Executor 必须输出 `📐 Template chrome inherited: <variant> | <chrome-signature-summary>` 作为响应首行（格式见 `executor-base.md §1.1`）。Quality Check Gate 第 11 维 (template_chrome_fidelity) 会比对生成 SVG 的 accent bar / footer rule / decorative circles / logo 是否与模板 chrome 签名一致；缺失或 ±4px 外位移 / 颜色不一致都是 release blocker error。`spec_lock 填对 ≠ 实际继承`——必须 read_file + 物理保留 chrome。

Read the role definition based on the selected style:
```
Read references/executor-base.md          # REQUIRED: common guidelines
Read references/executor-general.md       # General flexible style
Read references/executor-consultant.md    # Consulting style
Read references/executor-consultant-top.md # Top consulting style (MBB level)
```

> Only need to read executor-base + one style file.

**Design Parameter Confirmation (Mandatory)**: Before generating the first SVG, the Executor MUST review and output key design parameters from the Design Specification (canvas dimensions, color scheme, font plan, body font size) to ensure spec adherence. See executor-base.md Section 2 for details.

**Per-page spec_lock re-read (Mandatory)**: Before generating **each** SVG page, Executor MUST `read_file <project_path>/spec_lock.md` and use only the colors / fonts / icons / images listed there. This resists context-compression drift on long decks. See executor-base.md §2.1 for details.

> ⚠️ **Main-agent only rule**: SVG generation in Step 6 MUST remain with the current main agent because page design depends on full upstream context (source content, design spec, template mapping, image decisions, and cross-page consistency). Do NOT delegate any slide SVG generation to sub-agents.
> ⚠️ **Generation rhythm rule**: After confirming the global design parameters, the Executor MUST generate pages sequentially, one page at a time, while staying in the same continuous main-agent context. Do NOT split Step 6 into grouped page batches such as 5 pages per batch.

**Visual Construction Phase**:
- Generate SVG pages sequentially, one page at a time, in one continuous pass → `<project_path>/svg_output/`
- For complex mixed-source decks, run `python3 $SKILL_DIR/scripts/design_archetype_planner.py <project_path>` before writing SVG and use its planned archetypes + `densityContract` when filling `spec_lock.md ## design_diversity` and `## density_contract`. This prevents unrelated sections from collapsing into the same card-grid mold and prevents source details from being hidden in speaker notes by default.

**Quality Check Gate (Mandatory)** — after all SVGs are generated and BEFORE speaker notes:
```bash
python3 $SKILL_DIR/scripts/svg_quality_checker.py <project_path>
```
- **Auto-repair pipeline**: `finalize_svg.py` Step 1 (normalize-layout) automatically resolves component overlaps, text boundary violations, and sibling spacing issues. However, severe structural problems (e.g., 5 cards stacked where only 3 fit) cannot be auto-repaired — the Executor must prevent these upstream by following the component placement grid discipline in `executor-base.md`.
- Any `error` (banned SVG features, viewBox mismatch, spec_lock drift, etc.) MUST be fixed on the offending page before proceeding — go back to Visual Construction, re-generate that page, re-run the check.
- `warning` entries (e.g., low-resolution image, non-PPT-safe font tail, possible text overlap, off-contract icon drift) should be reviewed and fixed when straightforward; for branded templates, text overlap / clipping / icon drift warnings are release blockers unless proven false positive.
- Running the checker against `svg_output/` is required — running it only after `finalize_svg.py` is too late (finalize rewrites SVG and some violations get masked).
- For human-quality review on generated decks, also run `python3 $SKILL_DIR/scripts/ppt_master_eval.py --target <project_path> --design`; the design section scores hierarchy, semantic grouping, density balance, information density against `density_contract`, visual focus / component scale hierarchy, whitespace, alignment discipline, explicit component→slot→text coverage, and deck-level visual-archetype diversity.
- Read `design.pages[].generationGuidance` and `design.deckGenerationGuidance` from the eval JSON before regenerating. These are upstream actions (route / component / slot / density changes), not requests to hand-adjust coordinates in one SVG.
- If `spec_lock.md ## quality_samples` exists, inspect those rotating sample pages first for human-made quality: narrative specificity, composition hierarchy, density control, brand-native execution, technical legibility, and client readiness. Do not repeatedly polish the same page across iterations; rotate sample page numbers and route intents according to the template rubric.
- When improving `ppt-master` itself or investigating repeated visual defects, run `python3 $SKILL_DIR/scripts/ppt_master_eval.py --target <project_path> --design` and use its fixture + target report as evidence. Do not judge capability changes only by one manually patched sample SVG.

**Logic Construction Phase**:
- Generate speaker notes → `<project_path>/notes/total.md`

**✅ Checkpoint — Confirm all SVGs and notes are fully generated and quality-checked. Proceed to Step 6.5 overflow check, then Step 7**:
```markdown
## ✅ Executor Phase Complete
- [x] All SVGs generated to svg_output/
- [x] svg_quality_checker.py passed (0 errors)
- [x] Speaker notes generated at notes/total.md
```

---

### Step 6.5 (HARD RULE)：溢出 fallback 子规则

> 这是 Step 6 的硬性子规则，**不是**独立步骤；判定信号在 Step 6 Quality Check 已经覆盖（第 5 维「文本换行」warning）。Executor 在每页 SVG 完成后必须自查本节 5 条禁令。

文字溢出时**禁止**缩字号 / 缩行高 / 压 padding / 写画布外 / 拆页不更新 page_count。
溢出段必须移入 `notes/total.md` 对应 H1 段（speaker notes 由 PPTX 原生承载）。

判定信号：`svg_quality_checker.py` 第 5 维「文本换行」warning（proxy 信号——检测的是「用了哪些换行机制」而非「实际溢出」；false negative 时 AI 必须按本节 5 条禁令逐页自查文本是否超出 viewBox 容量）。

详细 fallback 规则、5 个版式（16:9 / 4:3 / 小红书 / 朋友圈 / Story）下溢出表现差异、与 `total_md_split.py` H1 映射对齐说明，见 `references/overflow-fallback.md`。

---

### Step 7: Post-processing & Export

🚧 **GATE**: Step 6 complete (含 Step 6.5 overflow self-check); all SVGs generated to `svg_output/`; speaker notes `notes/total.md` generated.

```bash
python3 $SKILL_DIR/scripts/gate_check.py <project_path> --require nine_confirmations,design_review,audio_choice
```

非零退出 = 不可进入本步。`audio_choice` 是 Step 4.5 ⑤ 项决策的 gate：决定 Step 7.3 是否串入 `notes_to_audio.py` + `--recorded-narration`。

> ⚠️ The following three sub-steps MUST be **executed individually one at a time**. Each command must complete and be confirmed successful before running the next.
> ❌ **NEVER** put all three commands in a single code block or single shell invocation.

**Step 7.0** — Pre-flight lint（3 维子集：禁用元素 / 字体 / viewBox，<1 秒；finalize_svg.py 会重写 SVG 并 mask 部分违规，必须在它之前最后一次拦截）：
```bash
python3 $SKILL_DIR/scripts/svg_quality_checker.py --lint <project_path>
```
errors > 0 → 修到 0 才能进 Step 7.1。详见 §Gotchas「跳过 Step 7 入口 `--lint`」。

**Step 7.1** — Split speaker notes:
```bash
python3 $SKILL_DIR/scripts/total_md_split.py <project_path>
```

**Step 7.2** — SVG post-processing (icon embedding / image crop & embed / text flattening / rounded rect to path):
```bash
python3 $SKILL_DIR/scripts/finalize_svg.py <project_path>
```

**Step 7.3** — Export PPTX (embeds speaker notes + page transition + per-element entrance animation by default).

**Read the audio decision from Step 4.5 ⑤** (no need to re-ask the user — `.gates/audio_choice.json` already has it):

```bash
AUDIO_MODE=$(python3 -c "
import json, sys, pathlib
p = pathlib.Path('<project_path>/.gates/audio_choice.json')
print(json.loads(p.read_text()).get('audio_mode', 'none') if p.exists() else 'none')
")
```

| `AUDIO_MODE` | What to run |
|---|---|
| `none` | Skip audio. Just export. |
| `edge_default` | First: `python3 $SKILL_DIR/scripts/notes_to_audio.py <project_path>` (default `edge-tts`); then export with `--recorded-narration <project_path>/audio/`. |
| `cloud_quality` | First: `python3 $SKILL_DIR/scripts/notes_to_audio.py <project_path> --provider <chosen>` (provider name from `audio_choice.json.provider`); then export with `--recorded-narration`. Provider key must already be set per `workflows/generate-audio.md`. |
| `recorded_existing` | User supplied audio files at `<project_path>/audio/`. Skip generation; export with `--recorded-narration`. |

```bash
# Default export (no audio):
python3 $SKILL_DIR/scripts/svg_to_pptx.py <project_path>

# Force a single source for both versions:
python3 $SKILL_DIR/scripts/svg_to_pptx.py <project_path> -s final

# Skip per-element entrance animation:
python3 $SKILL_DIR/scripts/svg_to_pptx.py <project_path> -a none

# With pre-generated narration (chosen via Step 4.5 ⑤):
python3 $SKILL_DIR/scripts/svg_to_pptx.py <project_path> --recorded-narration <project_path>/audio/

# See: references/animations.md (effect catalog) + workflows/generate-audio.md (narration pipeline)
```

> 📁 **PPTX path layout**: `exports/<name>_<timestamp>.pptx` is the user-facing native PPTX. The legacy compatibility version (`<name>_svg.pptx`) now lives under `backup/<timestamp>/` — keeping `exports/` clean.
> ❌ **NEVER** use `cp` as a substitute for `finalize_svg.py` — it performs multiple critical processing steps
> ❌ **NEVER** add extra flags like `--only` unless you understand the legacy/rollback scope (see `--help`)

---

### Reverse Pipeline (PPTX → SVG)

When the user provides an existing `.pptx` and wants editable SVG (instead of starting from a Markdown source), use the reverse converter:

```bash
python3 $SKILL_DIR/scripts/pptx_to_svg.py <pptx_file> -o <output_dir>
```

Output structure (default `--inheritance-mode both`):
- `<output_dir>/svg/` — layered (master / layout / slide separate, machine-readable)
- `<output_dir>/svg-flat/` — preview (one self-contained SVG per slide)
- `<output_dir>/assets/` — extracted media (images, etc.)

Use cases: importing a customer's existing PPTX as a template, building an editable design surface from a deck, or round-trip fidelity testing of `svg_to_pptx.py`.

---

## Role Switching Protocol

Before switching roles, you **MUST first read** the corresponding reference file — skipping is FORBIDDEN. Output marker:

```markdown
## [Role Switch: <Role Name>]
📖 Reading role definition: references/<filename>.md
📋 Current task: <brief description>
```

---

## Reference Resources

| Resource | Path |
|----------|------|
| Shared technical constraints | `references/shared-standards.md` |
| Canvas format specification | `references/canvas-formats.md` |
| Image layout specification | `references/image-layout-spec.md` |
| SVG image embedding | `references/svg-image-embedding.md` |
| Step 4.5 design review gate | `references/design-review-gate.md` |
| Step 6.5 overflow fallback | `references/overflow-fallback.md` |
| Page transitions + per-element entrance animations | `references/animations.md` |

---

## Notes

- Do NOT add extra flags like `--only` to the post-processing commands — run them as-is
- Local preview: `python3 -m http.server -d <project_path>/svg_final 8000`
- **Troubleshooting**: If the user encounters issues during generation (layout overflow, export errors, blank images, etc.), recommend checking `docs/faq.md` — it contains known solutions sourced from real user reports and is continuously updated

---

## Gotchas（真坑沉淀，AI 高频犯错）

| Gotcha | 后果 | 正确做法 |
|---|---|---|
| **AI 直接 Read .jpg / .png 图片文件** | 浪费上下文 + 视觉解读不稳定 | 严禁直接打开图片；必须 `python3 $SKILL_DIR/scripts/analyze_images.py <project_path>/images`，**只看脚本输出**或 design_spec 的 Image Resource List |
| **Nine Confirmations 在用户回复"嗯/差不多"时通过** | 用户没真同意就被推进 Phase 2，后续返工成本高 | 必须等待表中的明确确认词（"确认"/"ok"/"continue"/"continue"/"👍" 等）；模糊回复必须 re-ping（详见 §Strategist Phase 八项确认 user reply contract） |
| **三步 post-processing 写在一个 shell block 或并发跑** | 中间 step 失败下一步用过期文件 → 输出错乱 | 必须**分别 sequential 执行**：`total_md_split.py` → 确认无错 → `finalize_svg.py` → 确认无错 → `svg_to_pptx.py -s final` |
| **用 `cp` 替代 `finalize_svg.py`** | 跳过最终化处理 → 导出 PPTX 缺样式 | 永远用 `finalize_svg.py`；导出永远从 `svg_final/` 而非 `svg_output/`，加 `-s final` 标志 |
| **Executor 写新 page 前不重读 spec_lock.md** | Executor 上下文越往后越容易 drift，违反 strategist 既定决策 | 每写一个新 page 前必须重新 `Read templates/spec_lock_reference.md` 对应路径 + 项目的 spec_lock.md |
| **SVG 用了 banned features**（mask / class / `<style>` / external CSS / `<animate*>` 等） | 导出 PPTX 时静默失败或样式丢失 | 严格遵守 `references/shared-standards.md` §1.1 banned 列表；rgba() 改 fill-opacity；`<g opacity>` 改逐元素 opacity |
| **跳过 Step 7 入口 `--lint`，直接进 `total_md_split` / `finalize_svg`** | `finalize_svg.py` 重写 SVG 后 mask 部分违规 → 后处理用脏 SVG → PPTX 静默失败或样式丢失 | Step 7 入口必须先跑 `svg_quality_checker.py --lint <project_path>`（3 维子集，<1 秒）；errors > 0 修到 0 才进三步 |
