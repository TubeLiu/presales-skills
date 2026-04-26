# CLAUDE.md

本文件为 Claude Code 提供项目上下文和工作指引。

## 项目概述

Solution Master 是一个 AI 辅助**通用解决方案**撰写框架，本身是一个 **Claude Code 插件**（`.claude-plugin/plugin.json`），同时支持通过 vercel-labs/skills CLI 安装到 Cursor / Codex / OpenCode 等其它 agent。
适用于技术方案、业务方案、咨询报告、项目建议书、招投标方案等各类结构化文档撰写。

核心能力：

- 苏格拉底式需求提取（workflow/brainstorming.md）
- 任务分解与验收标准（workflow/planning.md）
- 子智能体隔离撰写（workflow/writing.md + agents/writer.md）
- 两阶段审查——内容正确性 + 写作质量（workflow/spec-review.md + workflow/quality-review.md + agents/spec-reviewer.md + agents/quality-reviewer.md）
- 多源知识检索与智能融合——本地 KB / AnythingLLM / Web 搜索 / CDP 登录态站点（workflow/knowledge-retrieval.md）
- 上下文感知配图（通过 ai-image plugin 的 `image_gen.py` 与 drawio plugin 的 `drawio_generator.py` 调用）
- 双格式输出：Markdown + DOCX（workflow/docx.md + scripts/docx_writer.py）
- **SessionStart hook 注入铁律**（Claude Code + Cursor）：每次会话启动自动把主 SKILL.md 注入 additionalContext，铁律无法被遗忘或绕过

## 目录结构（v0.2.0+ 形态）

```
solution-master/
├── .claude-plugin/
│   └── plugin.json                       # 插件元信息
├── hooks/                                # Claude Code + Cursor 共用
│   ├── hooks.json                        # 注册 SessionStart hook (Claude Code)
│   ├── hooks-cursor.json                 # Cursor 1.x camelCase schema
│   ├── session-start                     # SessionStart bash 脚本（自定位 + 项目门禁）
│   ├── run-hook.cmd                      # 跨平台包装器
│   └── hooks-cursor.README.md            # Cursor hook 说明
├── skills/
│   └── solution-master/                  # 主 SKILL（11 个原子 skill 合并而来）
│       ├── SKILL.md                      # 主入口：description / 铁律 / 文件导航 / 子智能体调度
│       ├── workflow/                     # 按需 Read 的子工作流
│       │   ├── brainstorming.md          # 阶段 1：苏格拉底式需求提取
│       │   ├── planning.md               # 阶段 2：任务分解
│       │   ├── writing.md                # 阶段 3：撰写主流程 + 子智能体调度
│       │   ├── knowledge-retrieval.md    # 多源知识检索
│       │   ├── spec-review.md            # 内容正确性审查
│       │   ├── quality-review.md         # 写作质量审查
│       │   ├── docx.md                   # DOCX 输出 + 字体规范
│       │   └── config.md                 # 配置管理
│       ├── agents/                       # 子智能体角色定义（Task tool prompt body）
│       │   ├── writer.md
│       │   ├── spec-reviewer.md
│       │   └── quality-reviewer.md
│       ├── scripts/                      # Python 工具脚本
│       │   ├── docx_writer.py
│       │   ├── kb_indexer.py
│       │   └── sm_config.py
│       └── prompts/                      # YAML 模板（撰写规范、配图护栏等）
│           ├── writing_core.yaml
│           ├── image_guidelines.yaml
│           ├── source_ranking.yaml
│           └── fusion_strategy.yaml
├── docs/
│   ├── writing-skills.md                 # maintainer 文档（如何为本框架创建/编辑技能）
│   ├── workflow.dot                      # 工作流图 (Graphviz)
│   └── graphviz-conventions.dot          # dot 文件约定
├── tests/                                # 自动化测试 + fixtures
├── Local-KnowledgeBase/                  # 本地知识库（用户项目内）
├── output/                               # 最终产出（用户项目内）
├── drafts/                               # 章节草稿（用户项目内）
└── docs/specs/                           # 设计规格（brainstorming 产出）
```

## 安装

**Claude Code**（主要用户）：

```
/plugin marketplace add Alauda-io/presales-skills     # 或本地路径 /path/to/presales-skills
/plugin install solution-master@presales-skills
/reload-plugins
```

**其它 agent**（Cursor / Codex / OpenCode 等）：

```bash
npx skills add Alauda-io/presales-skills -a <agent>   # vercel-labs/skills CLI
```

完整安装说明见仓库外层 README.md。

## 防脱轨机制

Solution Master 的防脱轨依赖两层相互加强的机制：

### 1. SessionStart hook — 注入铁律（Claude Code + Cursor 专属）
- 匹配 `startup|clear|compact`
- 执行 `hooks/session-start`，读取 `skills/sm/SKILL.md` 全文并作为 `additionalContext` 注入到上下文
- **项目门禁**（4 条任一满足即触发）：当前 cwd 含以下任一时触发，全局安装下不会污染非 SM 项目：
  1. `drafts/` 目录
  2. `docs/specs/` 目录
  3. `skills/sm/SKILL.md`（plugin 模式 / 源码 clone 模式）
  4. `.claude/skills/sm/SKILL.md`（npx 安装模式）
- 这样任何会话启动时（含 `/clear`、`/compact`），主 SKILL.md 的铁律、文件导航、红线清单、"不信任报告"原则都会被强制注入——无法被遗忘、无法被合理化绕过
- **其它 agent（Codex / OpenCode 等）暂无 hook 机制**，铁律仅在用户首句触发 SKILL description 时被加载（best-effort）

### 2. 强化的子智能体 prompt（Layer 2）
- 主 SKILL.md 的"子智能体调度"段定义完整流程图、强制状态汇报（DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED）
- `agents/spec-reviewer.md` 和 `agents/quality-reviewer.md` 都保留**"不要信任报告"原文段**——审查者被明确要求不信任撰写者的自述，必须用 Read 工具打开 draft 文件逐条核对
- 这一层完全靠 prompt 约束 + 子智能体上下文隔离（Claude Code Task tool 真隔离 / 其它 agent best-effort `---RESET---` 边界），不依赖任何 hook

## 核心工作流

```
开始 → workflow/brainstorming.md（苏格拉底式提问）
     → 用户批准设计
     → workflow/planning.md（任务分解 + 验收标准）
     → 用户批准计划
     → 对每个章节任务（独立子智能体，按 workflow/writing.md 流程）：
         workflow/knowledge-retrieval.md（检索素材）
         → drawio plugin / ai-image plugin（如需配图）
         → writer 子智能体（撰写 drafts/<name>.md）
         → spec-reviewer 子智能体（PASS?）
         → quality-reviewer 子智能体（PASS?）
         → 下一个任务
     → 最终组装
     → workflow/docx.md + scripts/docx_writer.py（输出 MD/DOCX）
     → 完成
```

详细工作流图见 `docs/workflow.dot`。

## 触发场景

主 SKILL `solution-master` 的 description 已覆盖所有触发场景。用户说以下任一关键词时会自动加载本 SKILL：

| 场景 | 关键词 |
|------|---------|
| 启动方案撰写 | 写方案 / 撰写方案 / 写解决方案 / 写技术方案 / write solution / draft proposal |
| 头脑风暴 | 头脑风暴 / 澄清需求 / brainstorm |
| 任务分解 | 任务分解 / 章节计划 / planning |
| 章节撰写 | 写下一章 / 撰写章节 / write next chapter |
| 双阶段审查 | 审一下方案 / 检查章节 / spec review / quality review |
| 知识库检索 | 知识库检索 / 找资料 / search KB |
| DOCX 输出 | 导出 Word / 输出 DOCX / export docx |
| 配置管理 | 配置 solution-master / show config / validate config |

加载主 SKILL 后，按场景 Read 对应 `workflow/*.md` 子文件。

<EXTREMELY-IMPORTANT>
如果你认为某个 workflow 子文件有哪怕 1% 的可能适用于当前任务，你必须 Read 它并按指引执行。这不是可选的。你不能通过合理化来逃避。
</EXTREMELY-IMPORTANT>

## 子智能体隔离原则

- 每个撰写任务分派一个全新子智能体，具有隔离的上下文（Claude Code 用 Task tool 真隔离）
- 子智能体不继承父会话的历史记录——精确构造它们所需的一切
- 审查由独立子智能体执行，不与撰写者共享上下文
- 子智能体可以在工作前/中提问
- **审查者必须亲自打开 draft 文件和证据目录逐项核对**，不能只看撰写者的报告（"不信任报告"原则，见 `agents/spec-reviewer.md` 和 `agents/quality-reviewer.md`）
- 不支持 Task tool 的 agent：在主上下文顺序执行，章节之间显式输出 `---RESET CONTEXT FOR <章节名>---` 边界（近似隔离，非真隔离）

## 统一配置

**配置文件**：`~/.config/presales-skills/config.yaml`（统一路径，迁移自旧 `~/.config/solution-master/config.yaml`）

**管理**：通过 ai-image plugin 的 `ai_image_config.py` 子命令统一管理（auto-migrate 会自动合并旧路径）：

```bash
# 解析 ai-image SKILL_DIR 后：
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup     # 首次配置（含 auto-migrate）
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" show      # 查看配置
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set <key> <value>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate  # 健康检查
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models    # 列出 AI 生图模型
```

也可通过 SKILL 自然语言触发："配置 ai-image"、"我刚装新版需要初始化"、"迁移旧配置"。

详细配置工具：`skills/sm/scripts/sm_config.py`（solution-master 自家的配置读取/迁移辅助）

## DOCX 字体规范

详见 `workflow/docx.md`。摘要：标题 H1-H5 自动多级编号（1, 1.1, 1.1.1...）、宋体、H1 16pt H2 15pt H3 14pt H4 13pt 加粗、H5/正文 12pt、A4、页边距 2.5/2.4cm、1.5 倍行距。

## 关键约束

- 纯 CLI/Skill 模式，无 Web 界面
- 知识库检索结果写入检索报告（展示给用户），**方案正文中禁止出现任何括号形式的来源标注**
- 全中文工作语言（SKILL.md、提示词、产出物均为中文）
- 输出格式：Markdown（默认）或 DOCX（遵循上述字体规范）

## HARD-GATE 约定

部分 workflow 文件使用 `<HARD-GATE>` 标记不可绕过的检查点。语义为"硬性闸门 — 不能合理化绕过"。Claude 在解析这些标记时应严格遵守，不得 short-circuit。

例如 `workflow/brainstorming.md` 用 `<HARD-GATE>` 框住"在你展示设计方案并获得用户批准之前，不要调用任何撰写 workflow"——即使用户表达了"赶紧开始写"的意愿，Claude 也不能跳过头脑风暴阶段。

`<HARD-GATE>` 标签**不是** Claude Code 的官方机制；它依赖 SKILL.md / workflow/*.md 自身的 prompt engineering 强制约束 + 子智能体上下文隔离。
