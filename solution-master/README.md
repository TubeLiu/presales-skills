# Solution Master

**一个让 Claude Code 写出真正能交付的方案文档的插件。** Solution Master 不是"再来一个 prompt 模板"——它把苏格拉底式需求提取、子智能体隔离撰写、双阶段独立审查、四路知识融合与企业级 DOCX 排版组装成一条可追溯的流水线，让每一份方案都经过"写—审内容—审质量"的闭环，而不是一次性"写完就交"。

### 为什么不是"直接让 Claude 写一份方案"

- **苏格拉底式需求提取**：开写之前先把项目类型、范围、约束、读者、验收标准问清楚，避免无根据的通用话术（`skills/solution-brainstorming`）
- **子智能体隔离 + 双阶段审查**：每个章节由独立子智能体撰写，然后由 **spec-reviewer** 审内容正确性、**quality-reviewer** 审写作质量；审查者被强制"**不信任报告**"——必须亲自用 Read 打开 draft 文件逐条核对，而不是看撰写者的自述（`agents/spec-reviewer.md` · `agents/quality-reviewer.md`）
- **四路知识融合**：本地知识库 + AnythingLLM 语义检索 + Web 搜索（Tavily/Exa）+ CDP 登录态浏览器（可进 Confluence 等企业内网），按相关性/权威性/完整性/时效性四维打分、跨源语义去重、缺口补检（`skills/knowledge-retrieval`）
- **7 条铁律 + SessionStart Hook 自动注入**：每次会话启动（含 `/clear`、`/compact`）自动把铁律、红线清单、技能路由表注入 Claude 上下文——无法被遗忘、无法被"合理化"绕过（`skills/using-solution-master` · `hooks/session-start`）
- **上下文感知配图 + 多供应商 AI 生图**：架构图走 draw.io、概念图走 AI 生图、产品截图走本地资产，按章节语义自动选型；AI 生图支持**多供应商多模型**（ByteDance、阿里、Google 等），通过 `/solution-config models` 统一管理模型注册表，可联网刷新；图源不可用时报警而非静默失败（`ai-image plugin` · `skills/drawio` · `skills/solution-config`）
- **企业级 DOCX 一键产出**：Markdown 默认输出，DOCX 输出遵循中英文分离字体、H1–H5 多级自动编号、draw.io PNG 自动嵌入——省去手工调格式（`skills/docx-formatting`）

**工作流**：`solution-brainstorming`（问清楚）→ `solution-planning`（拆任务 + 验收标准）→ 每章 `knowledge-retrieval` + ai-image plugin（跨 plugin 引用）+ writer 子智能体 → `spec-reviewing` → `quality-reviewing` → 组装 → `docx-formatting` → 完成。

## 适用场景

- 技术解决方案
- 业务方案
- 咨询报告
- 项目建议书
- 其他需要结构化撰写的文档

## 核心特性

### 技能系统（solution-master 自带 11 个技能 + 3 个共享 plugin）

| 技能 | 说明 |
|------|------|
| `using-solution-master` | 会话启动时自动注入的铁律 + 红线清单 + 技能路由 |
| `subagent-driven-writing` | 子智能体驱动撰写流程（vendored from superpowers-zh） |
| `solution-brainstorming` | 苏格拉底式提问，提取项目细节 |
| `solution-planning` | 任务分解，制定撰写计划 |
| `solution-writing` | 撰写方案章节（领域层流程） |
| `spec-reviewing` | 内容正确性审查 |
| `quality-reviewing` | 写作质量审查 |
| `knowledge-retrieval` | 多源知识检索与智能融合 |
| `docx-formatting` | DOCX 格式输出 |
| `solution-config` | 配置管理（`/solution-config`） |
| `writing-skills` | 元技能：创建新技能 |

**共享依赖**（按需同时安装）：
| plugin | 作用 | 何时必需 |
|------|------|------|
| `drawio` | 架构图/流程图/拓扑图绘制（原 solution-master skill，Milestone C 抽出）| 始终 |
| `ai-image` | 统一 AI 图片生成（原 image-generation skill，Milestone D 抽出；13 provider）| 始终 |
| `web-access` | 联网 + CDP 浏览器自动化（原 solution-master skill，本次抽出；vendored from eze-is/web-access）| 仅 `cdp_sites.enabled=true`（登录态站点检索）时必需 |

> **从 solution-master ≤ 0.1.5 升级的用户注意**：如果你之前启用了 `cdp_sites`，升级到 0.1.6 后需要额外运行 `/plugin install web-access@presales-skills` 把新抽出的 plugin 装上；不使用 CDP 登录态检索则无需安装。

### 防脱轨机制

1. **SessionStart hook** — 每次会话启动自动把 `using-solution-master` SKILL（包含 7 条铁律、红线清单、技能路由表、"不信任报告"原则）注入到 Claude 的 `additionalContext`，无法被遗忘或合理化绕过
2. **强化的子智能体 prompts** — `subagent-driven-writing` SKILL + `agents/spec-reviewer.md` + `agents/quality-reviewer.md` 里保留 vendored from superpowers-zh 的"不要信任报告"原文段，强制审查者亲自 Read 文件逐条核对

hook 脚本在 `hooks/` 目录——只有 SessionStart 一个 hook，和 superpowers-zh 的模式完全一致。

## 安装

Solution Master 支持三种安装方式：

### 方式 A：Claude Code 插件（推荐，最强）

solution-master 现作为 `presales-skills` umbrella marketplace 的成员 plugin 分发（与 `ppt-master`、`tender-workflow` 并列）。在任意目录启动 `claude` 后执行：

```
/plugin marketplace add Alauda-io/presales-skills    # 或本地路径 /path/to/presales-skills
/plugin install solution-master@presales-skills
/reload-plugins
```

- 第一个命令注册 umbrella marketplace（GitHub 短写或本地路径均可）
- 第二个命令从中安装 `solution-master` plugin
- 第三个命令让 SessionStart hook 立即生效（也可以退出会话后重新启动）

安装后 Claude Code 会自动：
- 设置 `${CLAUDE_PLUGIN_ROOT}` 指向插件目录
- 加载 `.claude-plugin/plugin.json`
- 注册 `hooks/hooks.json` 中的 SessionStart hook
- 发现 `skills/`、`agents/`、`commands/`

**验证安装**：
```
/plugin list
/plugin            # 打开插件管理器查看 Installed 列表
```

**卸载**：
```
/plugin uninstall solution-master@presales-skills --scope local
/plugin marketplace remove solution-master
```

### 方式 B：项目级 npx 安装（fallback）

```bash
cd /your-project
npx /path/to/solution-master
```

会把 `skills/`、`agents/`、`hooks/` 复制到 `<your-project>/.claude/` 下，并智能合并 `<your-project>/.claude/settings.json`，注册 SessionStart hook（带绝对路径）。已有配置会备份到 `settings.json.bak.<timestamp>`。

### 方式 C：全局 npx 安装

```bash
npx /path/to/solution-master --global
```

同上，但目标为 `~/.claude/`，对所有项目生效。hook 脚本自身有**项目门禁**——只在 cwd 有 `drafts/` 或 `docs/specs/` 标志的项目中触发，非 SM 项目不会被污染。

### 卸载

```bash
# 项目级
npx /path/to/solution-master --uninstall

# 全局
npx /path/to/solution-master --uninstall --global
```

精确移除 Solution Master 贡献的 skills/agents/hooks 与 settings.json 中的 hook 条目，保留用户其他配置。

## 快速开始

安装完成后：

1. 配置：`/solution-config setup`
2. 开始撰写：描述你的项目，框架会自动触发 `solution-brainstorming` 技能

## 配置

配置文件：`~/.config/solution-master/config.yaml`

```bash
/solution-config setup      # 交互式配置
/solution-config show       # 查看配置
/solution-config validate   # 健康检查
```

## 开发者模式

在本仓库内开发，用 umbrella marketplace 的本地路径加载：

```bash
cd /path/to/presales-skills     # umbrella marketplace 根目录
claude
```

然后在 Claude Code 会话里：
```
/plugin marketplace add .
/plugin install solution-master@presales-skills
/reload-plugins
```

修改 SKILL、agent、hook 后，跑 `/reload-plugins` 即可热更新（部分场景需要重启 Claude Code）。
