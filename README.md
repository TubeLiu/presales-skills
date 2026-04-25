# presales-skills — 售前工作流多 agent SKILL 集

按职责拆分的 7 个 plugin 通过同一个 marketplace 统一分发。同时兼容 **Claude Code**（marketplace 安装）和 **Cursor / Codex / OpenCode** 等其它 agent（vercel-labs/skills CLI 安装）。

## 包含的 7 个 plugin

| plugin | 类型 | 用途 |
|---|---|---|
| **solution-master** | 主 plugin | 通用解决方案撰写框架：苏格拉底式需求提取、子智能体驱动撰写、双重审查、多源知识检索、上下文感知配图、Markdown/DOCX 输出 |
| **ppt-master** | 主 plugin | 从 PDF / DOCX / URL / Markdown 等多源文档生成原生可编辑 PPTX（SVG 流水线） |
| **tender-workflow** | 主 plugin | 四角色招投标工作流：`tpl`（招标策划）/ `taa`（招标分析）/ `taw`（标书撰稿）/ `trv`（审核）+ `twc`（配置） |
| **drawio** | 共享 plugin | Draw.io 图表生成（`.drawio` XML + PNG/SVG/PDF 导出）。被 solution-master / tender-workflow 依赖 |
| **ai-image** | 共享 plugin | 统一 AI 图片生成：13 个后端（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter）+ 共享 YAML 模型注册表。被三个主 plugin 依赖 |
| **anythingllm-mcp** | 共享 plugin | AnythingLLM MCP server：知识库语义搜索 + workspace 列举。可选——不装则降级为本地 YAML 索引 + 联网检索 |
| **web-access** | 共享 plugin | 联网操作 + CDP 浏览器自动化（vendored from [eze-is/web-access](https://github.com/eze-is/web-access)）。可选——仅在启用 solution-master 的 `cdp_sites` 登录态站点检索时必需 |

10 个用户可触发 SKILL：`solution-master` / `image-gen` / `draw-diagram` / `ppt-make` / `web-access` / `taa` / `taw` / `trv` / `tpl` / `twc`。

---

## 安装

### 路径 A：Claude Code（主要使用方式）

```
/plugin marketplace add Alauda-io/presales-skills
/plugin install drawio@presales-skills
/plugin install ai-image@presales-skills
/plugin install anythingllm-mcp@presales-skills        # 可选
/plugin install web-access@presales-skills             # 可选（CDP 登录态检索时必需）
/plugin install solution-master@presales-skills
/plugin install ppt-master@presales-skills
/plugin install tender-workflow@presales-skills
/reload-plugins
```

依赖顺序：先装共享 plugin（drawio / ai-image / anythingllm-mcp / web-access），再装主 plugin。

预期 reload 输出：`7 plugins · 10 skills · 1 hook · 1 plugin MCP server`
- 1 hook：solution-master 的 SessionStart 注入主 SKILL（在 SM 项目内 cwd 时触发）
- MCP：`anythingllm`（来自 anythingllm-mcp plugin；不装时无此 server）

也支持本地路径：`/plugin marketplace add /path/to/presales-skills`

### 路径 B：Cursor / Codex / OpenCode 等其它 agent

```bash
npx --yes skills add Alauda-io/presales-skills -a cursor
npx --yes skills add Alauda-io/presales-skills -a codex
npx --yes skills add Alauda-io/presales-skills -a opencode
```

vercel-labs/skills CLI 会扫描所有 SKILL.md 并 symlink/copy 到目标 agent 的标准目录（如 `.cursor/skills/` / `.agents/skills/`）。

**与 Claude Code 安装的差异**：
- Cursor 使用 `hooks-cursor.json` 同款 SessionStart 注入；Codex / OpenCode 等无 hook 机制（靠 SKILL description 触发）
- anythingllm-mcp 不会自动注册——按目标 agent 各自 MCP 注册方式手工配置（如 Cursor 在 `.cursor/mcp.json` 加 anythingllm 条目）

> 端到端流程在 Cursor / Codex / OpenCode 上**未经维护者完整验证**——欢迎社区反馈到 issue tracker。

---

## 配置

3 个 plugin 自带交互式配置向导。在会话里直接说自然语言：

| 你说什么 | Claude 引导你完成 |
|---|---|
| `帮我配置 ai-image` | API keys（按需选 13 provider 的任意一个或多个）→ 默认 provider → 默认尺寸 → validate |
| `帮我配置 solution-master` | localkb 路径 → AnythingLLM（可选）→ MCP 搜索优先级 → CDP 登录态站点（可选）→ draw.io CLI 路径 → validate |
| `帮我配置 tender-workflow` 或 `配置工作流` | 6 步 tender 专属配置（localkb / anythingllm / drawio CLI / mcp_search / skill 默认值） |

每个向导都会一步步问、立即写入、立即验证，跳过任何"可选"字段都允许。

**其它 plugin 不需要专属配置**：
- `ppt-master`：API keys 共享自 ai-image；画布尺寸 / 配色 / 行业模板内置
- `drawio`：仅需 CLI 路径，由 solution-master 向导一并问
- `web-access`：CDP 启用流程在 SKILL.md 内置前置检查中引导
- `anythingllm-mcp`：MCP server 自身在 plugin.json 注册；启用与否是 solution-master 的字段

### 配置文件

| 文件 | 字段 | 由哪个工具管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml` | `api_keys` / `ai_image` / `ai_keys`（共享） | ai-image 的 `ai_image_config.py` |
| `~/.config/solution-master/config.yaml` | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search` | solution-master 的 `sm_config.py` |
| `~/.config/tender-workflow/config.yaml` | tender 专属字段 | tender-workflow 的 `tw_config.py` |

升级老用户：之前用过 `~/.config/{solution-master,tender-workflow}/config.yaml` 的 API keys 字段会被 ai-image `setup` 第一次跑时**自动 migrate** 到统一路径，无需手动操作。

### 纯 CLI 配置（不走 Claude，给 power user）

```bash
# ai-image 共享配置
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup            # 含 auto-migrate
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate

# solution-master 专属配置
python3 "$SM_DIR/scripts/sm_config.py" set localkb.path <path>
python3 "$SM_DIR/scripts/sm_config.py" validate
```

`$AI_IMAGE_DIR` 与 `$SM_DIR` 通过各自 SKILL.md 顶部的 §路径自定位 段（`installed_plugins.json` 五段式 fallback）解析。

---

## 使用

所有触发都是自然语言——没有 slash command。

### solution-master — 写解决方案

> 帮我写一份面向金融行业的容器云技术方案。

solution-master SKILL（在 SM 项目内 cwd 时由 SessionStart hook 自动注入铁律）按工作流走：

```
brainstorming（苏格拉底式提问）
  ↓
planning（拆任务 + 验收标准）
  ↓
每章循环：knowledge-retrieval + ai-image / drawio 配图 + writer 子智能体
  ↓
spec-review（内容审查）+ quality-review（写作审查）
  ↓
docx 输出
```

工作流文件：`solution-master/skills/solution-master/workflow/{brainstorming,planning,writing,spec-review,quality-review,knowledge-retrieval,docx,config}.md`，按需 Read。子智能体角色定义：`agents/{writer,spec-reviewer,quality-reviewer}.md`。

### ppt-master — 生成 PPT

> 把这份 PDF 做成 10 页 PPT。
> 把这个微信公众号文章做成演示。

工作流：`源文档 → 项目初始化 → 模板选择 → 策略师 → 图片生成器 → 执行者 → 后处理 → 导出 PPTX`。

详细规则见 `ppt-master/skills/ppt-master/SKILL.md`。

### tender-workflow — 招投标文档

四个 SKILL 按场景触发：

| SKILL | 角色 | 服务对象 | 触发示例 |
|---|---|---|---|
| `tpl` | 策划者 | 甲方 | "根据这份产品功能清单生成招标技术规格 + 评标办法" |
| `taa` | 分析者 | 乙方 | "分析这份招标文件" / "看看这份招标文件" |
| `taw` | 撰稿者 | 乙方 | "帮我写标书 / 写投标方案" |
| `trv` | 审核者 | 甲乙双方 | "审一下这份标书 / 检查投标文件" |

配置由 `twc` SKILL 引导（"配置工作流"）。

### drawio — 画图

> 画一张架构图：用户 → 网关 → 微服务。
> 生成一张数据库 ER 图。

生成 `.drawio` 源文件；若本机装了 draw.io 桌面版或 `drawio-cli`，同时导出 PNG/SVG/PDF。

安装 CLI：
```bash
brew install --cask drawio          # macOS
npm install -g @drawio/drawio-desktop-cli   # 跨平台
```

### ai-image — 生图

> 生成一张图：xxx 主题。
> 用 ark 生成一张 K8s 架构示意图。

按 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider` 选 provider；可在自然语言中显式指定 provider 名（ark / dashscope / gemini / openai / ...）。

### web-access — 联网 / CDP

> 帮我搜一下 X 的最新动态。
> 抓一下这个小红书帖子的内容（需要登录态）。

详细 CDP 启用流程见 `web-access/skills/web-access/SKILL.md`。

---

## 跨平台

### macOS / Linux

零特殊步骤，按上面"安装"路径走即可。`ppt-master` 需要系统级 pandoc + cairo：

```bash
# macOS
brew install pandoc cairo
# Debian / Ubuntu
apt install pandoc libcairo2-dev
```

### Windows

**推荐方式（二选一）**：
- **WSL 2**：零改动，原生 Linux 体验
- **Windows 原生 + [Git for Windows](https://git-scm.com/downloads/win)**：Claude Code 自身依赖 Git Bash 来执行命令（[官方说明](https://docs.claude.com/en/docs/claude-code/setup)）。装完 Git for Windows + Python ≥ 3.10 即可

**不支持**：纯 PowerShell / CMD + 不装 Git for Windows。Claude Code 自身就依赖 Git Bash，这一层无法绕开。

**Windows 适配点**（每个 SKILL.md 顶部都有 §跨平台兼容性 checklist 段提醒）：
- `python3` 命令在 Windows 原生若不可识别，用 `python` 或 `py -3`
- `ppt-master` 需要 pandoc + GTK runtime（`choco install pandoc` + [GTK runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)）
- `web-access` 的 CDP 自动化在 Windows 原生 cmd / PowerShell best-effort——优先在 Git Bash / WSL2 中运行
- 不要用 MSYS2 Python 代替原生 Windows Python（`platform.system()` 在 MSYS2 下返回 `MSYS_NT-10.0`，会触发 ppt-master 的非 Windows 异常分支）

### 自动依赖安装

所有 Python 依赖由入口脚本首次调用时自动 `pip install`（每个脚本开头调 `_ensure_deps.py`：检查 `<plugin>/.deps-installed` marker，不存在则装）。Plugin 升级时 cache 路径带版本号，marker 不跨版本继承，自动触发新依赖重装。

设 `PRESALES_SKILLS_SKIP_AUTO_INSTALL=1` 可禁用自动 pip（适合 CI / 容器 / 自管 venv）：

```bash
pip install -r ~/.claude/plugins/cache/presales-skills/ppt-master/*/requirements.txt
pip install -r ~/.claude/plugins/cache/presales-skills/ai-image/*/requirements.txt
```

---

## 更新

```
/plugin marketplace update presales-skills
/reload-plugins
```

---

## 目录结构

```
presales-skills/
├── .claude-plugin/marketplace.json    # 7 个 plugin 入口 + 顶层版本
├── README.md
├── tests/
│   └── test_skill_format.py           # SKILL.md 格式自动化检查
│
├── drawio/
│   ├── .claude-plugin/plugin.json
│   ├── skills/drawio/
│   │   ├── SKILL.md                   # 名为 draw-diagram
│   │   └── xml-reference.md
│   └── scripts/drawio_generator.py
│
├── ai-image/
│   ├── .claude-plugin/plugin.json
│   ├── skills/ai-image/
│   │   ├── SKILL.md                   # 名为 image-gen
│   │   └── scripts/
│   │       ├── image_gen.py            # 13 backend 分发器
│   │       ├── ai_image_config.py      # 配置工具（含 auto-migrate）
│   │       ├── _ensure_deps.py
│   │       └── image_backends/         # 13 backend 实现
│   ├── prompts/ai_image_models.yaml    # 共享模型注册表
│   └── requirements.txt
│
├── anythingllm-mcp/
│   ├── .claude-plugin/plugin.json     # mcpServers.anythingllm（无前缀，统一注册）
│   └── tools/mcp-anythingllm/         # Node MCP server，零 npm 依赖
│
├── web-access/
│   ├── .claude-plugin/plugin.json
│   └── skills/web-access/
│       ├── SKILL.md
│       ├── scripts/                   # CDP proxy / find-url / match-site / check-deps
│       └── references/cdp-api.md
│
├── solution-master/
│   ├── .claude-plugin/plugin.json
│   ├── docs/                          # writing-skills 维护文档 + workflow.dot
│   ├── hooks/
│   │   ├── hooks.json                 # SessionStart 注册 (Claude Code)
│   │   ├── hooks-cursor.json          # 同款 (Cursor)
│   │   ├── session-start              # 注入主 SKILL.md 内容到 additionalContext
│   │   └── run-hook.cmd               # Windows 跨平台 wrapper
│   └── skills/solution-master/
│       ├── SKILL.md                   # 主入口（铁律 + 文件导航 + 子智能体调度）
│       ├── workflow/                  # 8 个按需 Read 的子流程
│       │   ├── brainstorming.md
│       │   ├── planning.md
│       │   ├── writing.md
│       │   ├── knowledge-retrieval.md
│       │   ├── spec-review.md
│       │   ├── quality-review.md
│       │   ├── docx.md
│       │   └── config.md
│       ├── agents/                    # Task tool prompt body
│       │   ├── writer.md
│       │   ├── spec-reviewer.md
│       │   └── quality-reviewer.md
│       ├── scripts/
│       │   ├── docx_writer.py
│       │   ├── kb_indexer.py
│       │   └── sm_config.py
│       └── prompts/                   # YAML 模板（撰写规范、配图护栏、章节模板）
│           ├── writing_core.yaml
│           ├── image_guidelines.yaml
│           ├── source_ranking.yaml
│           ├── fusion_strategy.yaml
│           └── section_templates/
│               ├── business.yaml
│               ├── consulting.yaml
│               ├── proposal.yaml
│               └── technical.yaml
│
├── ppt-master/
│   ├── .claude-plugin/plugin.json
│   └── skills/ppt-master/
│       ├── SKILL.md                   # 名为 ppt-make
│       ├── references/                # 角色定义 + 技术规范
│       ├── scripts/                   # source_to_md / project_manager / svg_* / total_md_split
│       └── templates/                 # layout / chart / 640+ 图标库
│
└── tender-workflow/
    ├── .claude-plugin/plugin.json
    ├── skills/
    │   ├── tpl/SKILL.md
    │   ├── taa/SKILL.md
    │   ├── taw/SKILL.md
    │   ├── trv/SKILL.md
    │   └── twc/SKILL.md
    └── tools/tw_config.py
```

---

## 开发者参考

### SKILL.md 统一模板

每个 SKILL.md 顶部按统一模板写，包含：
- frontmatter：`description: >` block scalar（避免 vercel CLI 解析单行长 description 失败）
- §跨平台兼容性 checklist：5 项（python 命令名 / 路径自定位 / 可执行检测 / Bash heredoc / 路径分隔符）
- `<SUBAGENT-STOP>` 标签（含"Task prompt"判定条件，让被分派的子智能体跳过主流程编排）
- 铁律段（如适用）：`<EXTREMELY-IMPORTANT>` 包裹的不可绕过规则
- §路径自定位 bootstrap：installed_plugins.json 五段式 fallback 解析 SKILL_DIR

模板文件：`/Users/tubeliu/.claude/plans/SKILL-template.md`（仓库外 maintainer 资料）。

### 跨 plugin 调用约定

跨 plugin 调用通过查询 `~/.claude/plugins/installed_plugins.json` 拿到对方 plugin 的 `installPath`，再拼脚本绝对路径。**不假设兄弟相对路径**——Claude Code 的 cache 布局是 `<plugin>/<version>/skills/<skill>/`，跨 plugin 不是兄弟；Cursor / OpenCode 装出来又是另一种结构。

五段式 fallback（每个 SKILL.md §路径自定位 段提供）：

1. `~/.claude/plugins/installed_plugins.json`（Claude Code 权威来源，精确指向当前激活版本）
2. `~/.cursor/skills` / `~/.agents/skills` / `.cursor/skills` / `.agents/skills`（vercel CLI 标准目录）
3. 用户预设环境变量 `<PLUGIN>_PLUGIN_PATH`（如 `DRAWIO_PLUGIN_PATH`）
4. cwd 相对 `./` 和 `../`（dev 态）
5. 全失败 → 输出诊断 + 退出 1（让 Claude 转述给用户，要求 export 环境变量或安装缺失 plugin）

### 子智能体调度

solution-master 的子智能体（writer / spec-reviewer / quality-reviewer）通过 **Task tool** 委派——把 `agents/<role>.md` 完整内容作为 Task prompt body 传入：

```python
Task(
  subagent_type="general-purpose",
  description="撰写章节 N: <章节名>",
  prompt="""<agents/writer.md 完整内容>

  ## 你的任务
  ...
  """
)
```

不支持 Task tool 的 agent：在主上下文顺序执行，章节之间显式输出 `---RESET CONTEXT FOR <章节名>---` 边界（近似隔离，非真隔离）。

### MCP server 共享

`anythingllm-mcp` 是独立 plugin，注册无前缀的 `anythingllm` MCP server。消费方（solution-master / tender-workflow）的 `plugin.json` 不含 `mcpServers` 字段，直接通过 `mcp__anythingllm__anythingllm_search` / `mcp__anythingllm__anythingllm_list_workspaces` 调用。

未装 `anythingllm-mcp` 时，消费方 SKILL 自动降级为本地 YAML 索引 + 联网检索（不 hard-fail）。

### 版本号 bump 规则

破坏性变更（删 SKILL / 改命令字符串 / 改公开入口）= **minor +1**。任一 plugin minor bump 后，**marketplace 顶层至少跟随子 plugin 最高级别**（取所有子 plugin 新 minor 的最大值作为顶层 minor）。

施工日复核：

```bash
grep '"version"' .claude-plugin/marketplace.json */.claude-plugin/plugin.json
```

marketplace.json 顶层 `metadata.version` + 各 plugin entry 的 `version` 必须与各 plugin 自己的 `plugin.json` `version` 字段保持一致。

### SessionStart hook（仅 solution-master）

7 个 plugin 中**仅 solution-master** 注册 SessionStart hook（Claude Code 用 `hooks.json`，Cursor 用 `hooks-cursor.json`）：

- 项目门禁：仅当 cwd 含 `drafts/` / `docs/specs/` / `skills/solution-master/SKILL.md` / `.claude/skills/solution-master/SKILL.md` 任一时触发
- 触发后 cat 主 SKILL.md 全文注入到 additionalContext（铁律 + 文件导航 + 子智能体调度全量）
- 其它 plugin 不重复注册——多个同步 hook 会让会话启动时间线性叠加；其它 plugin 的提示性内容用 SKILL description 承载即可

其它 agent（Codex / OpenCode）暂无 hook 机制；铁律靠主 SKILL.md description 自然语言匹配触发（best-effort）。

### 测试

```bash
python3 -m pytest tests/test_skill_format.py -v
```

9 项断言：每个 SKILL.md 必须用 block scalar description / 含 Windows checklist / 含 `<SUBAGENT-STOP>` + Task prompt 判定 / 不引用已删 slash / 不含 `${CLAUDE_*}` 占位符（仅 anythingllm-mcp plugin.json 豁免）/ 不用 `command -v` / vercel CLI 实测识别 10 skills。
