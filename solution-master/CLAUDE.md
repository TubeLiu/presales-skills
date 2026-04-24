# CLAUDE.md

本文件为 Claude Code 提供项目上下文和工作指引。

## 项目概述

Solution Master 是一个 AI 辅助**通用解决方案**撰写框架，本身是一个 **Claude Code 插件**（`.claude-plugin/plugin.json`），采用技能驱动架构（Skill-Based Architecture）。
适用于技术方案、业务方案、咨询报告、项目建议书等各类结构化文档撰写。

核心能力：

- 苏格拉底式需求提取（solution-brainstorming）
- 任务分解与验收标准（solution-planning）
- 子智能体隔离撰写（solution-writing + subagent-driven-writing）
- 两阶段审查——内容正确性 + 写作质量（spec-reviewing + quality-reviewing）
- 多源知识检索与智能融合——本地KB/AnythingLLM/Web 搜索/CDP 登录态站点（knowledge-retrieval）
- 上下文感知配图（image-generation）
- 双格式输出：Markdown + DOCX（docx-formatting）
- **SessionStart hook 注入铁律**：每次会话启动自动把 using-solution-master SKILL 注入 Claude 的 additionalContext，铁律无法被遗忘或绕过

## 目录结构（插件形态）

```
solution-master/
├── .claude-plugin/
│   ├── plugin.json                   # 插件元信息
│   └── marketplace.json              # marketplace 清单
├── hooks/
│   ├── hooks.json                    # 注册 SessionStart hook
│   ├── session-start                 # SessionStart bash 脚本（自定位 + 项目门禁）
│   ├── run-hook.cmd                  # 跨平台包装器
│   └── hooks-cursor.json             # Cursor 变体
├── skills/                           # 顶层技能目录（非 .claude/skills/）
│   ├── using-solution-master/        # 铁律 + 红线清单 + 技能路由，由 SessionStart 注入
│   ├── subagent-driven-writing/      # 子智能体驱动撰写流程（vendored）
│   ├── solution-brainstorming/
│   ├── solution-planning/
│   ├── solution-writing/
│   ├── spec-reviewing/
│   ├── quality-reviewing/
│   ├── knowledge-retrieval/
│   ├── image-generation/
│   ├── docx-formatting/
│   ├── solution-config/
│   ├── writing-skills/
│   └── web-access/
│   # (drawio 已抽为独立 plugin `drawio`，位于 presales-skills marketplace 的 ../drawio/)
├── agents/                           # 子智能体角色定义
│   ├── writer.md
│   ├── spec-reviewer.md
│   └── quality-reviewer.md
├── bin/
│   └── solution-master.js            # npx 安装器（fallback 模式）
├── tests/                            # 自动化测试脚本 + fixtures
├── Local-KnowledgeBase/               # 本地知识库
├── output/                            # 最终产出
├── drafts/                            # 章节草稿
└── docs/specs/                        # 设计规格（solution-brainstorming 产出）
```

## 铁律

详见 `skills/using-solution-master/SKILL.md`。该 SKILL 的全文会在每次会话启动时由 SessionStart hook 自动注入，你无需主动读取。

如果你正在阅读 CLAUDE.md 但会话启动时没看到 `using-solution-master` 的注入，说明 hook 未生效——这通常意味着 Solution Master 未以插件方式安装。正确的安装命令（本 plugin 作为 `presales-skills` umbrella marketplace 的成员分发）：

```
/plugin marketplace add Alauda-io/presales-skills     # 或本地路径 /path/to/presales-skills
/plugin install solution-master@presales-skills
/reload-plugins
```

完整安装说明见仓库外层 README.md。

## 防脱轨机制

Solution Master 的防脱轨依赖两层相互加强的机制：

### 1. SessionStart hook — 注入铁律（唯一的 hook）
- 匹配 `startup|clear|compact`
- 执行 `hooks/session-start`，读取 `skills/using-solution-master/SKILL.md` 并作为 `additionalContext` 注入到 Claude 的上下文
- **项目门禁**：仅在当前 cwd 有 `drafts/`、`docs/specs/` 或 `skills/solution-writing/SKILL.md` 时才触发；全局安装下不会污染非 Solution Master 项目
- 这样任何会话启动时（含 `/clear`、`/compact`），Solution Master 的 7 条铁律、技能路由表、红线清单、"不信任报告"原则都会被强制注入——无法被遗忘、无法被合理化绕过

### 2. 强化的子智能体 prompt（Layer 2）
- `subagent-driven-writing` SKILL 定义完整流程图、红线清单、强制状态汇报（DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT）
- `agents/spec-reviewer.md` 和 `agents/quality-reviewer.md` 都保留 vendored from superpowers-zh 的**"不要信任报告"原文段**——审查者被明确要求不信任撰写者的自述，必须用 Read 工具打开 draft 文件逐条核对
- 这一层完全靠 prompt 约束 + 子智能体上下文隔离，不依赖任何 hook

这种组合跟 superpowers-zh 一致（对比 obra/superpowers 20 个 skills 同样只用 SessionStart hook，经过 110k+ star 实战验证），既稳健又简洁。

## 核心工作流

```
开始 → solution-brainstorming（苏格拉底式提问）
     → 用户批准设计
     → solution-planning（任务分解 + 验收标准）
     → 用户批准计划
     → 对每个章节任务（独立子智能体，subagent-driven-writing 流程）：
         knowledge-retrieval（检索素材）
         → image-generation（如需配图）
         → writer 子智能体（撰写 drafts/<name>.md）
         → spec-reviewer 子智能体（PASS?）
         → quality-reviewer 子智能体（PASS?）
         → 下一个任务
     → 最终组装
     → docx-formatting（输出 MD/DOCX）
     → 完成
```

详细工作流图见 `docs/workflow.dot`

## 技能触发场景

所有技能位于 `skills/`，扁平命名空间。技能通过 YAML frontmatter 中的 description 字段自动触发。

| 技能 | 触发场景 |
|------|---------|
| using-solution-master | 会话启动时自动注入，无需手动调用 |
| subagent-driven-writing | 执行多章节撰写计划时（底层流程） |
| solution-brainstorming | 开始新方案、用户描述项目需求、需要澄清设计思路 |
| solution-planning | 方案设计已批准，需要分解为撰写任务 |
| solution-writing | 有具体章节任务需要撰写（领域层流程） |
| spec-reviewing | 章节撰写完成，需要内容正确性审查 |
| quality-reviewing | 内容审查通过，需要写作质量审查 |
| knowledge-retrieval | 头脑风暴时获取领域知识、撰写前检索相关内容 |
| image-generation | 章节需要配图 |
| docx-formatting | 需要输出 DOCX 格式文件 |
| drawio | 由独立 plugin `drawio` 提供（需配套安装），需要绘制架构图/流程图/拓扑图等时触发 |
| solution-config | 配置管理需求，`/solution-config` 手动调用 |
| writing-skills | 需要创建或编辑 Solution Master 技能 |
| web-access | 联网、浏览器自动化、CDP 登录态操作 |

<EXTREMELY-IMPORTANT>
如果你认为某个技能有哪怕 1% 的可能适用于当前任务，你必须调用该技能。这不是可选的。你不能通过合理化来逃避。
</EXTREMELY-IMPORTANT>

## 子智能体隔离原则

- 每个撰写任务分派一个全新子智能体，具有隔离的上下文
- 子智能体不继承父会话的历史记录——精确构造它们所需的一切
- 审查由独立子智能体执行，不与撰写者共享上下文
- 子智能体可以在工作前/中提问
- **审查者必须亲自打开 draft 文件和证据目录逐项核对**，不能只看撰写者的报告（"不信任报告"原则，参见 `agents/spec-reviewer.md` 和 `agents/quality-reviewer.md`）

## 统一配置

**配置文件**：`~/.config/solution-master/config.yaml`

**管理命令**：

```bash
/solution-config setup              # 交互式首次配置
/solution-config show               # 查看当前配置
/solution-config set <key> <value>  # 设置配置项
/solution-config validate           # 健康检查
/solution-config models [provider]  # 列出 AI 生图模型
/solution-config models --refresh   # 联网刷新模型注册表
```

**配置工具**：`skills/solution-config/scripts/sm_config.py`

## DOCX 字体规范

详见 `docx-formatting` 技能。标题自动多级列表编号（1, 1.1, 1.1.1...）。

## 关键约束

- 纯 CLI/Skill 模式，无 Web 界面
- 知识库检索结果写入检索报告（展示给用户），**方案正文中禁止出现任何括号形式的来源标注**
- 全中文工作语言（SKILL.md、提示词、产出物均为中文）
- 输出格式：Markdown（默认）或 DOCX（遵循上述字体规范）
