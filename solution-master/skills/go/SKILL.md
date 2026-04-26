---
name: solution-master
description: >
  AI 辅助通用解决方案撰写框架。覆盖技术方案 / 业务方案 / 咨询报告 /
  项目建议书 / 招投标方案等结构化文档全流程。
  触发场景：
  「写方案 / 撰写方案 / 写解决方案 / 写技术方案 / 写业务方案 / 写项目建议书 /
  写咨询报告 / draft solution / write solution / technical proposal /
  business proposal」（启动方案撰写）；
  「头脑风暴 / 澄清需求 / brainstorm / clarify requirement」（需求提取）；
  「任务分解 / 章节计划 / planning / break down」（计划阶段）；
  「写下一章 / 撰写章节 / write next chapter」（章节撰写）；
  「审一下方案 / 检查方案 / 检查章节 / spec review / quality review」（双阶段审查）；
  「知识库检索 / 找资料 / search knowledge base / search KB」（素材检索）；
  「导出 Word / 输出 DOCX / export docx / 把方案打成 Word」（输出阶段）；
  「配置 solution-master / 设置 / show config / validate config」（配置管理）。
  通过苏格拉底式提问 → 任务分解 → 子智能体并行撰写 → 双阶段审查 → 组装输出，
  产出高质量方案文档。依赖 ai-image / drawio / web-access / anythingllm-mcp（可选）插件。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

# Solution Master — 解决方案撰写框架

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
如果你认为哪怕只有 1% 的可能性某个 workflow 或子智能体适用于你正在做的事情，你绝对必须按本 SKILL 的工作流走。

如果一个 workflow 适用于你的任务，你没有选择。你必须使用它。

这不可协商。这不是可选的。你不能通过合理化来逃避。
</EXTREMELY-IMPORTANT>

## 路径自定位

**首次调用本 skill 的脚本前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/scripts/...`、`$SKILL_DIR/agents/...`、`$SKILL_DIR/prompts/...`）：

```bash
SKILL_DIR=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/solution-master/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/go'); sys.exit(0)
" 2>/dev/null)

# vercel CLI fallback (skill subdir is 'go'; SKILL.md name is 'solution-master' so vercel
# CLI installs the standalone skill at ~/.<agent>/skills/solution-master/)
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/solution-master/skills/go" ] && SKILL_DIR="$d/solution-master/skills/go" && break
    [ -d "$d/solution-master" ] && SKILL_DIR="$d/solution-master" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${SOLUTION_MASTER_PLUGIN_PATH:-}" ] && SKILL_DIR="$SOLUTION_MASTER_PLUGIN_PATH/skills/go"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./solution-master/skills/go" ] && SKILL_DIR="$(pwd)/solution-master/skills/go"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 solution-master skill 安装位置。" >&2
    echo "请设置：export SOLUTION_MASTER_PLUGIN_PATH=/path/to/solution-master" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install solution-master@presales-skills` 或手工 export 环境变量。

## 首次触发的导引（必须执行）

当此技能触发时，先向用户展示工作流概览，再开始提问：

> 我将通过以下步骤帮你完成方案撰写：
> 1. **需求提取**（通过几个问题澄清项目细节）
> 2. **设计规格**（形成方案设计，你审核后批准）
> 3. **任务分解**（拆分为可执行章节，你审核后批准）
> 4. **逐章撰写**（每章自动检索、撰写、两阶段审查，过程中汇报进度）
> 5. **组装输出**（Markdown 或 DOCX）
>
> 你随时可以说"暂停/停止/取消"中断流程。
>
> 让我先了解你的需求。

然后按 `workflow/brainstorming.md` 进入阶段 1。

## 工作流程总览

```
用户描述需求
  → 阶段 1：头脑风暴（workflow/brainstorming.md）
  → 用户批准设计
  → 阶段 2：任务分解（workflow/planning.md）
  → 用户批准计划
  → 阶段 3：逐章执行（workflow/writing.md，含子智能体调度）
      每个章节：
        knowledge-retrieval（workflow/knowledge-retrieval.md）
        → 配图（drawio plugin / ai-image plugin / 占位符）
        → 分派 writer 子智能体（agents/writer.md）
        → 分派 spec-reviewer 子智能体（agents/spec-reviewer.md）
        → 分派 quality-reviewer 子智能体（agents/quality-reviewer.md）
        → FAIL 则修复后重审
  → 阶段 4：组装 + 输出（workflow/docx.md）
```

## 文件导航

调用各阶段时用 Read 工具加载对应文件，遵循其指引；不要凭记忆执行。

| 场景 | 读取文件 |
|------|---------|
| 开始新方案、需求提取、用户描述项目需求 | `$SKILL_DIR/workflow/brainstorming.md` |
| 设计已批准，分解任务、章节计划 | `$SKILL_DIR/workflow/planning.md` |
| 执行章节撰写、子智能体调度、并行撰写 | `$SKILL_DIR/workflow/writing.md` |
| 撰写前检索领域知识、找资料 | `$SKILL_DIR/workflow/knowledge-retrieval.md` |
| 章节内容正确性审查 | `$SKILL_DIR/workflow/spec-review.md` |
| 章节写作质量审查 | `$SKILL_DIR/workflow/quality-review.md` |
| 导出 DOCX / 输出 Word / 字体规范 | `$SKILL_DIR/workflow/docx.md` |
| 配置管理 / setup / show / set / validate | `$SKILL_DIR/workflow/config.md` |
| 生成架构图 / 流程图 / 拓扑图 | drawio plugin（按其 SKILL.md 指引） |
| 生成业务配图 / 概念示意 / 海报 | ai-image plugin（按其 SKILL.md 指引） |
| 浏览器操作 / 访问登录态站点 / Confluence 等 | web-access plugin（按其 SKILL.md 指引） |
| 维护本框架本身（创建新 workflow / 编辑现有 workflow） | `$SKILL_DIR/../../docs/writing-skills.md` |

## 子智能体工具限制（铁律）

<HARD-GATE>
Claude Code background subagent（Task tool 派发）有 **pre-approval** 机制：启动前 Claude Code 把 subagent 要用的工具权限列给用户预批准；启动后**未在 allowlist 中的 Skill / mcp__\* / WebFetch / WebSearch 调用 auto-deny**。

**分派子 Agent 前必须先在主 session 跑完所有需要这些工具的步骤**（配图调 `Skill(skill="ai-image:gen")`、知识库检索调 `mcp__plugin_anythingllm-mcp_anythingllm__anythingllm_search`、Web 检索调 `WebSearch`/`mcp__tavily*`/`mcp__exa*`/`WebFetch`），把结果拼到 Task prompt 里。子 Agent prompt 不能含"调 Skill / 调 mcp__\* / 调 Web\*"指令——subagent 端 `agents/*.md` §工具限制 已自检会 NEEDS_CONTEXT 报回，浪费一轮。

反模式：派 writer 时让它"顺便调一下 Skill 配图"——已知踩坑（用户 2026-04-27 实测）。

参考：claude-code-guide 2026-04-27 查证（`sub-agents.md` 第 38, 279, 365, 647 行；`permissions.md` 全文）。如用户希望 subagent 直接调这些工具，可在 `~/.claude/settings.json` 加 `permissions.allow` 预批准（见主 README）。
</HARD-GATE>

## 子智能体调度

按 `workflow/writing.md` 流程，对每个章节任务分派一个全新隔离子智能体。

**Claude Code 优先：用 Task tool**，把 agents/<role>.md 的完整内容作为 prompt body 传入：

```
Task(
  subagent_type="general-purpose",
  description="撰写章节 N: <章节名>",
  prompt="""<$SKILL_DIR/agents/writer.md 的完整内容>

  ## 你的任务
  [任务完整文本]

  ## 方案上下文
  [方案名称、整体结构、当前章节位置]

  ## 知识库素材
  [knowledge-retrieval 的检索结果]

  ## 配图方案
  [配图方案]

  ## 撰写规范
  [$SKILL_DIR/prompts/writing_core.yaml 内容]

  ## 配图护栏
  [$SKILL_DIR/prompts/image_guidelines.yaml 内容]

  ## 输出要求
  - Markdown 格式
  - 保存到：drafts/[章节编号]_[章节名称].md
  - 图片路径：../output/images/xxx.png（相对于 drafts/）
  - 正文中禁止来源标注
  - 完成后汇报状态：DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
  """
)
```

**降级路径**（其它 agent 无 Task tool 时）：在主上下文顺序执行，章节之间显式输出 `---RESET CONTEXT FOR <章节名>---` 边界 + 强制重读章节计划。**这是"近似隔离"，不是真隔离**——reviewer 角色被 writer 思路污染的风险存在。质量要求高时建议在 Claude Code 上跑（有真隔离）。

## Solution Master 铁律（IRON RULES）

<EXTREMELY-IMPORTANT>
以下规则不可违反、不可绕过、不可合理化。违反规则的字面意思就是违反规则的精神。

1. **不可跳过审查** — 每个章节必须经过 spec-review 和 quality-review 两道审查，无论章节多短多简单
2. **不可自审** — 撰写子智能体不能审查自己的产出，必须由独立子智能体执行审查
3. **审查顺序不可颠倒** — 内容正确性审查（spec-review）必须先于写作质量审查（quality-review）。规格审查没通过之前，不能启动质量审查
4. **未修复不可继续** — 审查发现的问题必须修复并重新通过审查后，才能进入下一个任务
5. **不可跳过头脑风暴** — 任何方案撰写前必须经过 brainstorming 提取需求，无论需求看起来多明确
6. **不可跳过知识检索** — 撰写前必须执行 knowledge-retrieval，检索结果必须反映在撰写子智能体拿到的素材中
7. **不可跳过配图规划** — 撰写前必须检查计划中的配图需求字段，若需要配图则必须生成配图方案（drawio / ai-image 调用）并传给撰写子智能体（配图需求明确为"无"的任务除外）。ASCII 文本图表不能替代正式配图

不要以"太简单"、"已经很清楚"、"自己检查过"、"先写完再说"等借口绕过任何规则。
</EXTREMELY-IMPORTANT>

## 红线（合理化警报）

以下想法意味着停下——你在合理化：

| 想法 | 现实 |
|------|------|
| "这只是一个简单的方案" | 问题就是任务。先走工作流。 |
| "我需要先了解更多上下文" | 工作流的 brainstorming 阶段就是为了获取上下文。先开始。 |
| "让我先探索一下需求" | 工作流的 brainstorming 阶段就是为了探索。不要绕开。 |
| "章节这么短，不用审查" | 每个章节必须经过双重审查，无一例外。 |
| "我已经检查过产出了" | 自审不算审查。必须由独立子智能体审查。 |
| "先写完所有章节再一起审查" | 每个章节完成后立即审查，不可批量跳过。 |
| "这次的方案没必要跑知识检索" | 方案撰写前必须执行 knowledge-retrieval。 |
| "这次的方案没必要配图" | 配图需求在计划阶段就已经确定，撰写时不能改。 |
| "让我先做这一件事" | 在做任何事之前先检查工作流。 |
| "我记得这个工作流" | 工作流会迭代更新。阅读当前版本。 |

## 输出规范

- **工作语言：** 中文
- **正文中禁止来源标注：** 知识库素材可以使用，但正文中不能出现 `（出处：xxx）`、`（来源：xxx）` 等括号标注
- **草稿目录：** `drafts/`（用户项目根目录下），每个章节一个文件
- **图片目录：** `output/images/`（用户项目根目录下）
- **草稿中图片路径：** `../output/images/xxx.png`（相对于 drafts/）
- **最终输出：** `output/方案名称.md`（组装后图片路径改为 `output/images/xxx.png`）
- **标题不含编号：** 编号由 DOCX 自动生成
- **设计规格与计划：** 保存到 `docs/specs/`

## DOCX 输出（简表）

需要 DOCX 时（详见 `workflow/docx.md`）：

```bash
python3 "$SKILL_DIR/scripts/docx_writer.py" output/方案名称.md output/方案名称.docx --title "方案标题"
```

字体规范摘要（详见 `workflow/docx.md`）：标题 H1-H5 自动多级编号、宋体（H1-H4 加粗 16-13pt，正文 12pt 宋体）、页边距 2.5/2.4cm、1.5 倍行距、A4。

## 配置（可选）

solution-master 的配置分**两个文件分工**：

| 文件 | 字段 | 由谁管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml` | `api_keys` / `ai_image` / `ai_keys`（共享） | ai-image plugin 的 `ai_image_config.py`（对 ai-image SKILL 说"配置 ai-image"触发其向导） |
| `~/.config/solution-master/config.yaml` | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search`（专属） | solution-master 自家的 `sm_config.py` |

未配置时，AI 图片功能降级为占位符，其他功能正常。

**完整 setup wizard 见 `$SKILL_DIR/workflow/setup.md`。** 当用户说「配置 solution-master / 帮我配置 solution-master / 初始化 solution-master / setup solution-master / 我刚装好需要配置」时：

1. 用 Read 工具加载 `$SKILL_DIR/workflow/setup.md`（路径 `$SKILL_DIR` 由 §路径自定位 段解析）
2. 严格按 setup.md 引导用户完成配置（含 Python 依赖前置 + localkb / anythingllm / mcp_search 试调引导 / CDP 委托 web-access wizard + 站点循环 + 实测 / drawio CLI 多分支 / API keys 透传 / validate）
3. 不要凭记忆执行 — 每次都 Read 当前版本

## SessionStart hook（Claude Code + Cursor 专属增强）

仓库 `hooks/` 目录注册了 SessionStart hook，会话启动时（含 `/clear`、`/compact`）自动注入本 SKILL.md 的铁律到上下文，先于任何 skill 触发。

**项目门禁**：仅当 cwd 含以下任一时触发，全局安装下不会污染非 SM 项目：
1. `drafts/` 目录
2. `docs/specs/` 目录
3. `skills/go/SKILL.md`（本文件存在即触发）
4. `.claude/skills/go/SKILL.md`（npx 安装模式）

其它 agent（vercel CLI 装到 Codex / OpenCode 等）无 hook 机制；用户首句若不含触发词，需手动调用 SKILL。Cursor 用 `hooks-cursor.json` 同款机制。
