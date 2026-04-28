# Solution Master

**一个让 Claude Code 写出真正能交付的方案文档的插件。** Solution Master 不是"再来一个 prompt 模板"——它把苏格拉底式需求提取、子智能体隔离撰写、双阶段独立审查、四路知识融合与企业级 DOCX 排版组装成一条可追溯的流水线，让每一份方案都经过"写—审内容—审质量"的闭环，而不是一次性"写完就交"。

### 为什么不是"直接让 Claude 写一份方案"

- **苏格拉底式需求提取**：开写之前先把项目类型、范围、约束、读者、验收标准问清楚，避免无根据的通用话术（`skills/go/workflow/brainstorming.md`）
- **子智能体隔离 + 双阶段审查**：每个章节由独立子智能体撰写，然后由 **spec-reviewer** 审内容正确性、**quality-reviewer** 审写作质量；审查者被强制"**不信任报告**"——必须亲自用 Read 打开 draft 文件逐条核对，而不是看撰写者的自述（`skills/go/agents/spec-reviewer.md` · `skills/go/agents/quality-reviewer.md`）
- **四路知识融合**：本地知识库 + AnythingLLM 语义检索 + Web 搜索（Tavily/Exa）+ CDP 登录态浏览器（可进 Confluence 等企业内网），按相关性/权威性/完整性/时效性四维打分、跨源语义去重、缺口补检（`skills/go/workflow/knowledge-retrieval.md`）
- **铁律 + SessionStart Hook 自动注入**：每次会话启动（含 `/clear`、`/compact`）自动把铁律、红线清单、技能路由表注入 Claude 上下文——无法被遗忘、无法被"合理化"绕过（`skills/go/SKILL.md` · `hooks/session-start`）
- **上下文感知配图 + 多供应商 AI 生图**：架构图走 draw.io、概念图走 AI 生图、产品截图走本地资产，按章节语义自动选型；AI 生图支持 13 个 provider（ByteDance、阿里、Google、OpenAI、Replicate 等），通过 `/ai-image:gen` 子命令 models 管理模型注册表（`ai-image plugin` · `drawio plugin` · `skills/go/scripts/sm_config.py`）。**结构化配图（信息图 / UI 截图 / 学术图形摘要 / 神经网络架构 / 论文图表）自动走 ai-image 内置 79 个模板**，避免每次重写 prompt
- **企业级 DOCX 一键产出**：Markdown 默认输出，DOCX 输出遵循中英文分离字体、H1–H5 多级自动编号、draw.io PNG 自动嵌入——省去手工调格式（`skills/go/workflow/docx.md` · `skills/go/scripts/docx_writer.py`）

**工作流**：`brainstorming`（问清楚）→ `planning`（拆任务 + 验收标准）→ 每章 `knowledge-retrieval` + ai-image / drawio plugin（跨 plugin 引用）+ writer 子智能体 → `spec-review` → `quality-review` → 组装 → `docx` → 完成。详细工作流图见 [`docs/workflow.dot`](./docs/workflow.dot)。

## 适用场景

- 技术解决方案
- 业务方案
- 咨询报告
- 项目建议书
- 其他需要结构化撰写的文档

## 核心特性

### Skill 结构（v1.0.0）

主 skill `solution-master`（slash 入口 `/solution-master:go`）含一个统一 SKILL.md + 按需加载的 workflow 子文件：

| 文件 | 说明 |
|------|------|
| `skills/go/SKILL.md` | 主入口：description / 铁律 / 文件导航 / 子智能体调度 |
| `skills/go/workflow/brainstorming.md` | 阶段 1：苏格拉底式需求提取 |
| `skills/go/workflow/planning.md` | 阶段 2：任务分解 + 验收标准 |
| `skills/go/workflow/writing.md` | 阶段 3：撰写主流程 + 子智能体调度 |
| `skills/go/workflow/knowledge-retrieval.md` | 多源知识检索 |
| `skills/go/workflow/spec-review.md` | 内容正确性审查 |
| `skills/go/workflow/quality-review.md` | 写作质量审查 |
| `skills/go/workflow/docx.md` | DOCX 输出 + 字体规范 |
| `skills/go/workflow/config.md` | 配置管理 |
| `skills/go/agents/{writer,spec-reviewer,quality-reviewer}.md` | Task 子智能体角色 prompt |
| `skills/go/scripts/{sm_config,kb_indexer,docx_writer}.py` | Python 工具脚本 |
| `skills/go/prompts/*.yaml` | 撰写规范 / 配图护栏 / 信源排序 / 融合策略 |

**共享依赖**（按需同时安装）：

| plugin | 作用 | 何时必需 |
|------|------|------|
| `drawio` | 架构图/流程图/拓扑图绘制 | 始终 |
| `ai-image` | 统一 AI 图片生成（13 provider）| 始终 |
| `anythingllm-mcp` | 知识库语义搜索 | 可选——AnythingLLM 启用时（auto/`--kb-source anythingllm`）；不装则降级本地 KB |
| `web-access` | 联网 + CDP 浏览器自动化 | 可选——仅 `cdp_sites.enabled=true`（登录态站点检索）时必需 |

### 防脱轨机制

1. **SessionStart hook** — 每次会话启动（含 `/clear`、`/compact`）自动把 `skills/go/SKILL.md` 注入到 Claude 的 `additionalContext`，铁律 + 红线清单 + workflow 导航表 + "不信任报告"原则无法被遗忘或合理化绕过。hook 含**项目门禁**：只在 cwd 有 `drafts/` / `docs/specs/` / `skills/go/SKILL.md` 标志时触发，非 SM 项目不会被污染。
2. **强化的子智能体 prompts** — `agents/spec-reviewer.md` + `agents/quality-reviewer.md` 保留 vendored from superpowers-zh 的"不要信任报告"原文段，强制审查者亲自 Read 文件逐条核对。
3. **HARD-GATE 标签** — `workflow/brainstorming.md` 等用 `<HARD-GATE>` 框住"不可绕过"检查点（如"未获用户批准前不能开写"），prompt engineering 强制约束。

## 安装

### Claude Code（主要用户）

```
/plugin marketplace add TubeLiu/presales-skills     # 或本地路径 /path/to/presales-skills
/plugin install solution-master@presales-skills
/reload-plugins
```

安装后 Claude Code 会自动：
- 设置 `${CLAUDE_PLUGIN_ROOT}` 指向 plugin 目录
- 加载 `.claude-plugin/plugin.json`
- 注册 `hooks/hooks.json` 中的 SessionStart hook
- 发现 `skills/go/SKILL.md`

**验证**：`/plugin list`

**卸载**：`/plugin uninstall solution-master@presales-skills` + `/plugin marketplace remove presales-skills`

### Cursor / Codex / OpenCode（其它 agent）

```bash
npx skills add TubeLiu/presales-skills -a <agent>   # vercel-labs/skills CLI
```

注：vercel CLI 装到 Codex/Cursor 时按 SKILL.md `name:` 字段建 `.agents/skills/<name>/`。本 plugin 是 `name: solution-master`，slash 短形式 `/solution-master`（distinctive，与 Claude Code canonical `/solution-master:go` 互补）。

完整跨 agent 兼容性矩阵见仓库外层 [README.md](https://github.com/TubeLiu/presales-skills#readme)。

## 快速开始

安装完成后：

1. 配置 ai-image：对 Claude 说"配置 ai-image"（首次）或"设置 ai-image \<key\> 为 \<value\>"
2. 开始撰写：描述你的项目，比如"写一份 GitOps 蓝绿发布技术方案"——SKILL 会自动触发，从 `brainstorming` 开始

## 配置

**统一配置文件**：`~/.config/presales-skills/config.yaml`（旧 `~/.config/solution-master/config.yaml` 会自动 migrate）

**管理**：通过 ai-image plugin 子命令统一管理（auto-migrate 会合并旧路径）：

```bash
# Claude Code slash（推荐）
/ai-image:gen setup       # 首次配置（含 auto-migrate）
/ai-image:gen show        # 查看配置
/ai-image:gen validate    # 健康检查

# 或自然语言触发：
"配置 ai-image"
"我刚装新版需要初始化"
"迁移旧配置"
```

solution-master 自家配置工具：`skills/go/scripts/sm_config.py`（供 SKILL.md 调用 + 在 ai-image plugin 之上 wrap 一层 sm 专属字段）

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

修改 SKILL / agent / hook / workflow 后，跑 `/reload-plugins` 即可热更新（部分场景需要重启 Claude Code）。
