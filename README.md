# presales-skills — 售前工作流 SKILL 集

按职责拆分的 7 个 plugin 通过同一个 marketplace 统一分发。同时兼容 **Claude Code**（marketplace 安装）和 **Cursor / Codex / OpenCode** 等其它 agent（[vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 安装）。

10 个用户可触发 SKILL，覆盖：写方案 / 做 PPT / 招投标 / 画图 / 生图 / 联网 / 知识库。

---

## 7 个 plugin 一览

| plugin | 类型 | Slash 入口（canonical / 短 alias）| 功能 |
|---|---|---|---|
| **solution-master** | 主 | `/solution-master:go`（短 alias `/solution-master`）| 通用解决方案撰写：苏格拉底式提问 / 子智能体并行撰写 / 双阶段审查 / 多源知识检索 / 配图 / Markdown + DOCX 输出 |
| **ppt-master** | 主 | `/ppt-master:make`（短 alias `/make`）| 多源文档 → 原生可编辑 PPTX（SVG 流水线 + 真实 PowerPoint shape）。**默认 Alauda 模板** |
| **tender-workflow** | 主 | `/tender-workflow:taa` / `:taw` / `:tpl` / `:trv` / `:twc` | 四角色招投标：tpl 招标策划 / taa 招标分析 / taw 标书撰稿 / trv 多维度审核 / twc 配置 |
| **drawio** | 共享 | `/drawio:draw`（短 alias `/draw`）| Draw.io 图表（.drawio XML + PNG/SVG/PDF 导出）。被 solution-master / tender-workflow 依赖 |
| **ai-image** | 共享 | `/ai-image:gen`（短 alias `/image-gen`）| 13 backend 统一 AI 生图（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter）。被三个主 plugin 依赖 |
| **anythingllm-mcp** | 共享 | （MCP server，无 slash）| AnythingLLM 知识库语义搜索 + workspace 列举。可选——不装则 solution-master/tender-workflow 降级为本地 YAML 索引 + 联网检索 |
| **web-access** | 共享 | `/web-access:browse`（短 alias `/browse`）| 联网操作 + CDP 浏览器自动化（搜索 / 抓取 / 登录态 / CDP 远程调试）。可选——仅 solution-master `cdp_sites.enabled=true` 时必需 |

> **Slash 形式说明**：`/<plugin>:<sub-skill>` 是 Claude Code canonical 形式（marketplace 注册）；短 alias 来自 SKILL.md `name:` 字段，由 Claude Code 自动补全为 canonical。Codex/Cursor/OpenCode 通过 vercel CLI 装到 `.agents/skills/<sub-skill>/` 等 flat layout，slash 形式直接是 `/<sub-skill>` 短形式。

> **自然语言 auto-trigger 永远可用**：每个 SKILL.md 的 `description:` 字段含触发关键词，"画一张架构图" / "生成图片" / "做 PPT" / "写方案" 等都能直接触发对应 sub-skill。

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

#### Granular install 示例

只装一两个 plugin 也完全可行（每个 plugin 独立运行）：

```
/plugin install drawio@presales-skills              # 仅画图
/plugin install ai-image@presales-skills            # 仅 AI 生图
/plugin install ppt-master@presales-skills + ai-image@presales-skills   # 做 PPT 含 AI 配图
```

### 路径 B：Cursor / Codex / OpenCode 等其它 agent

```bash
npx --yes skills add Alauda-io/presales-skills -a cursor   # Cursor
npx --yes skills add Alauda-io/presales-skills -a codex    # Codex
npx --yes skills add Alauda-io/presales-skills -a opencode # OpenCode
```

vercel-labs/skills CLI 会扫描所有 SKILL.md 并 symlink/copy 到目标 agent 的标准目录。**默认装到 cwd `.agents/skills/`**（项目级），加 `-g` 装到 `~/.agents/skills/`（全局）。

只装部分 sub-skill：`-s '*'` 装全部，或 `-s image-gen,draw,make` 指定。

完整 CLI 参数：`npx --yes skills --help`。

---

## 快速开始

每个 plugin 一个示例。Slash 入口与自然语言 trigger 都列出。

### `/drawio:draw` 画图

```
> 画一张架构图：用户 → API 网关 → 微服务集群 → 数据库
> /drawio:draw "GitOps 蓝绿发布流程图"
```

输出 `.drawio` 源文件；本机若装了 draw.io 桌面版或 `drawio-cli`，同时导出 PNG/SVG/PDF。

CLI 安装：
```bash
brew install --cask drawio          # macOS
npm install -g @drawio/drawio-desktop-cli   # 跨平台
```

### `/ai-image:gen` 生图

```
> 生成一张图：现代简约风的容器云架构示意
> 用 ark 生成一张 K8s 网络拓扑图
> /ai-image:gen "futuristic cloud platform dashboard, hi-tech aesthetic"
```

按 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider` 选 provider；可在自然语言中显式指定 provider 名（ark / dashscope / gemini / openai / ...）。

子命令通过 description auto-trigger 路由：
- "配置 ai-image" / "首次配置" → setup workflow
- "查看图片配置" / "show config" → show
- "列出图片模型" → models
- "验证 API key" → validate

### `/ppt-master:make` 做 PPT

```
> 把这份 PDF 做成 12 页 PPT
> 把这个微信公众号文章做成演示稿
> /ppt-master:make /path/to/source.pdf
```

**默认套 Alauda 模板**（v1.0.0 起的 default path）。如需别的，明说：

```
> 用 mckinsey 模板做这份 PPT          # 切换到 mckinsey 模板
> 自由设计，不要模板，做个艺术风       # 退出模板路径
> 有哪些模板可以用                    # 列模板
```

**全局默认覆盖**（在 `~/.config/presales-skills/config.yaml` 加）：
```yaml
ppt_master:
  default_layout: china_telecom_template   # 或别的内置模板名
```

### `/solution-master:go` 写方案

```
> 帮我写一份面向金融行业的容器云技术方案
> /solution-master:go "GitOps 蓝绿发布技术方案"
```

solution-master 在 SM 项目目录（含 `drafts/` / `docs/specs/` / 装了 `solution-master:go` 的 SKILL）触发 SessionStart hook 自动注入铁律，按工作流走：

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

详细工作流见 `solution-master/skills/go/workflow/{brainstorming,planning,writing,spec-review,quality-review,knowledge-retrieval,docx,config}.md`，按需 Read。

### `/tender-workflow:*` 招投标

四角色 + 一个配置入口，按场景触发：

```
> 看看这份招标文件                       # → /tender-workflow:taa 招标分析
> 帮我写标书的第三章                      # → /tender-workflow:taw 撰稿
> 根据这份产品功能清单生成招标技术规格      # → /tender-workflow:tpl 策划（甲方）
> 审一下这份投标方案                      # → /tender-workflow:trv 审核
> 配置工作流                             # → /tender-workflow:twc 配置
```

### `/web-access:browse` 联网 / CDP

```
> 帮我搜一下 X 的最新动态
> 抓一下这个小红书帖子的内容（需要登录态）
> /web-access:browse "https://www.example.com/page"
```

详细 CDP 启用流程见 `web-access/skills/browse/SKILL.md`。

### anythingllm-mcp（MCP server）

无 slash —— 装上后自动注册 `anythingllm` MCP server，主 plugin（solution-master / tender-workflow）通过 `mcp__anythingllm__anythingllm_search` 直接调。

未装时 → 自动降级为本地 YAML 索引 + 联网检索（不 hard-fail）。

---

## 跨 agent 兼容性矩阵

| Feature | Claude Code | Cursor (skills CLI) | Codex (skills CLI) | OpenCode (skills CLI) |
|---|---|---|---|---|
| `/<plugin>:<sub-skill>` slash 形式 | ✅ canonical | ✅（短形式 `/<sub-skill>`）| ✅（短形式 `/<sub-skill>`）| ✅（短形式 `/<sub-skill>`） |
| 自然语言 auto-trigger（SKILL.md description）| ✅ | ✅ | ✅ | ✅ |
| `${CLAUDE_PLUGIN_ROOT}` 占位符 | ✅ | ❌（无替换）| ❌ | ❌ |
| SessionStart hook（solution-master）| ✅ `hooks.json` | ✅ `hooks-cursor.json` | ❌ | ❌ |
| MCP server（anythingllm-mcp） | ✅ 自动 `plugin.json mcpServers` | ❌ 需手动 `.cursor/mcp.json` | ❌ 需手动配 | ❌ 需手动配 |
| `installed_plugins.json` 自定位 | ✅ | ❌（用 `.cursor/skills/` fallback）| ❌（用 `.agents/skills/` fallback）| ❌ |
| 跨 sub-skill 引用 `$SKILL_DIR/../<other>/` | ✅（同 plugin 内）| ✅（flat layout 兄弟）| ✅（flat layout 兄弟）| ✅ |
| 跨 plugin 引用 | ✅ 用 `installed_plugins.json` | ⚠ 用自然语言 / `Skill(skill="<plugin>:<sub>")` | ⚠ 同上 | ⚠ 同上 |

> 端到端流程在 Cursor / Codex / OpenCode 上**未经维护者完整验证**——欢迎社区反馈到 issue tracker。

---

## 配置

3 个 plugin 自带交互式配置向导。在会话里直接说自然语言：

| 你说什么 | Claude 引导你完成 |
|---|---|
| `配置 ai-image` / `首次配置` | API keys（按需选 13 provider 任一）→ 默认 provider → 默认尺寸 → validate |
| `配置 solution-master` | localkb 路径 → AnythingLLM（可选）→ MCP 搜索优先级 → CDP 登录态站点（可选）→ draw.io CLI 路径 → validate |
| `配置工作流` / `配置 tender` | 6 步 tender 专属配置（localkb / anythingllm / drawio CLI / mcp_search / skill 默认值） |

每个向导都会一步步问、立即写入、立即验证；任何"可选"字段都允许跳过。

**其它 plugin 不需要专属配置**：
- `ppt-master`：API keys 共享自 ai-image；画布尺寸 / 配色 / 行业模板内置
- `drawio`：仅需 CLI 路径，由 solution-master 向导一并问
- `web-access`：CDP 启用流程在 SKILL.md 内置前置检查中引导
- `anythingllm-mcp`：MCP server 自身在 plugin.json 注册；启用与否是 solution-master / tender-workflow 的字段

### 配置文件

| 文件 | 字段 | 由哪个工具管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml` | `api_keys` / `ai_image` / `ppt_master.default_layout` / `ai_keys`（共享） | ai-image 的 `ai_image_config.py` |
| `~/.config/solution-master/config.yaml` | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search` | solution-master 的 `sm_config.py` |
| `~/.config/tender-workflow/config.yaml` | tender 专属字段 | tender-workflow 的 `tw_config.py` |

### 纯 CLI 配置（不走 Claude，给 power user）

```bash
# ai-image 共享配置（含 auto-migrate 旧 plugin 配置）
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate

# solution-master 专属配置
python3 "$SM_DIR/scripts/sm_config.py" set localkb.path <path>
python3 "$SM_DIR/scripts/sm_config.py" validate

# tender-workflow 专属配置
python3 "$TW_DIR/skills/twc/tools/tw_config.py" set localkb.path <path>
python3 "$TW_DIR/skills/twc/tools/tw_config.py" validate
```

`$AI_IMAGE_DIR` / `$SM_DIR` / `$TW_DIR` 通过各自 SKILL.md 顶部的 §路径自定位 段（`installed_plugins.json` 五段式 fallback）解析。

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

所有 Python 依赖由入口脚本首次调用时自动 `pip install`（每个脚本开头调 `_ensure_deps.py`：检查 `<skill>/.deps-installed` marker，不存在则装）。Plugin 升级时 cache 路径带版本号，marker 不跨版本继承，自动触发新依赖重装。

设 `PRESALES_SKILLS_SKIP_AUTO_INSTALL=1` 可禁用自动 pip（适合 CI / 容器 / 自管 venv）：

```bash
pip install -r ~/.claude/plugins/cache/presales-skills/ppt-master/*/skills/make/requirements.txt
pip install -r ~/.claude/plugins/cache/presales-skills/ai-image/*/skills/gen/requirements.txt
```

---

## 目录结构

```
presales-skills/
├── .claude-plugin/marketplace.json    # 7 个 plugin 入口 + 顶层版本
├── README.md
├── tests/
│   └── test_skill_format.py           # SKILL.md 格式自动化检查（10 项断言）
│
├── drawio/
│   ├── .claude-plugin/plugin.json
│   ├── README.md                      # plugin 简介 + 6 种 preset + 安装 draw.io CLI
│   └── skills/draw/                   # 注册为 drawio:draw
│       ├── SKILL.md                   # name: draw（含 6 preset / animated / ML / style presets / 自定义 output dir）
│       ├── xml-reference.md           # 本仓原有 XML reference
│       ├── references/style-extraction.md   # 风格提取 reference
│       ├── styles/                          # built-in style preset (default/corporate/handdrawn) + schema.json
│       └── assets/                          # 6 个 .drawio demo（每 preset 一个最小代表样本）
│
├── ai-image/
│   ├── .claude-plugin/plugin.json
│   └── skills/gen/                    # 注册为 ai-image:gen
│       ├── SKILL.md                   # name: image-gen（短 alias）
│       ├── setup.md
│       ├── prompts/ai_image_models.yaml   # 共享模型注册表
│       ├── requirements.txt
│       └── scripts/
│           ├── image_gen.py           # 13 backend 分发器
│           ├── ai_image_config.py     # 配置工具（含 auto-migrate）
│           ├── _ensure_deps.py
│           └── image_backends/        # 13 backend 实现
│
├── anythingllm-mcp/
│   ├── .claude-plugin/plugin.json     # mcpServers.anythingllm（无前缀，统一注册）
│   └── tools/mcp-anythingllm/         # Node MCP server，零 npm 依赖
│
├── web-access/
│   ├── .claude-plugin/plugin.json
│   └── skills/browse/                 # 注册为 web-access:browse
│       ├── SKILL.md                   # name: browse
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
│   └── skills/go/                     # 注册为 solution-master:go
│       ├── SKILL.md                   # name: solution-master（短 alias）
│       ├── workflow/                  # 8 个按需 Read 的子流程
│       │   ├── brainstorming.md / planning.md / writing.md
│       │   ├── knowledge-retrieval.md / spec-review.md / quality-review.md
│       │   └── docx.md / config.md
│       ├── agents/                    # Task tool prompt body
│       │   ├── writer.md / spec-reviewer.md / quality-reviewer.md
│       ├── scripts/
│       │   ├── docx_writer.py / kb_indexer.py / sm_config.py
│       └── prompts/                   # YAML 模板（撰写规范、配图护栏、章节模板）
│
├── ppt-master/
│   ├── .claude-plugin/plugin.json
│   └── skills/make/                   # 注册为 ppt-master:make
│       ├── SKILL.md                   # name: make（短 alias）
│       ├── requirements.txt
│       ├── references/                # 角色定义 + 技术规范
│       ├── scripts/                   # source_to_md / project_manager / svg_* / total_md_split
│       └── templates/                 # layouts/{alauda,china_telecom_template,...} / icons / charts
│
└── tender-workflow/
    ├── .claude-plugin/plugin.json
    ├── git-hooks/pre-commit           # repo dev hook（与 Claude 无关）
    ├── tools/tw_config.py             # deprecation shim（11 行 stub，转发至 skills/twc/tools/）
    └── skills/                        # 5 个 sub-skill flat 排布
        ├── tpl/SKILL.md
        ├── taa/SKILL.md  + tools/{indexer_v2,docx_outline_template}.py
        ├── taw/SKILL.md  + tools/{docx_writer,kb_indexer}.py
        ├── trv/SKILL.md
        └── twc/SKILL.md  + tools/{tw_config,tpl_docx_writer,trv_docx_reviser,docx_encoding_check}.py
```

---

## 架构原理

### 仅用 `skills/`（不用 `commands/` / `agents/`）

5 个有用户入口的 plugin（drawio / ai-image / ppt-master / solution-master / web-access）和 5 个 tender-workflow sub-skill 全部用 `skills/<X>/SKILL.md` 注册。**不用** Claude Code 的 `commands/` 或 `agents/` 机制，原因：
- `skills/` 是唯一被 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 识别 + 拷贝的格式 → 同一 SKILL.md 既给 Claude Code 用又给 Cursor / Codex / OpenCode 用
- `description:` 字段提供自然语言 auto-trigger，省去用户记忆 slash 名
- `commands/` 仅 Claude Code 识别，加了它 = Cursor/Codex 用户体验降级

参考：[anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) 中的 frontend-design / mcp-server-dev / claude-code-setup 都是同款"仅 skills/"设计。

### Skill 命名约定

每个 sub-skill 目录名 ≠ plugin 名（消除 `<plugin>:<plugin>` 双名）。Claude Code 注册形式：
- canonical = `<plugin>:<dir-name>`（如 `/ai-image:gen`）
- alias = SKILL.md `name:` 字段（如 `/image-gen` 自动补全到 `/ai-image:gen`）

vercel CLI 装到 Codex/Cursor 时按 SKILL.md `name:` 命名 dir，slash 直接是 `/<name>` 短形式（无 plugin 前缀）。

### 跨 plugin 调用约定

跨 plugin 调用通过查询 `~/.claude/plugins/installed_plugins.json` 拿到对方 plugin 的 `installPath`，再拼脚本绝对路径。**不假设兄弟相对路径**——Claude Code 的 cache 布局是 `<plugin>/<version>/skills/<sub-skill>/`，跨 plugin 不是兄弟。

每个 SKILL.md §路径自定位 段提供五段式 fallback：

1. `~/.claude/plugins/installed_plugins.json`（Claude Code 权威来源，精确指向当前激活版本）
2. `~/.cursor/skills` / `~/.agents/skills` / `.cursor/skills` / `.agents/skills`（vercel CLI 标准目录）
3. 用户预设环境变量 `<PLUGIN>_PLUGIN_PATH`（如 `DRAWIO_PLUGIN_PATH`）
4. cwd 相对 `./` 和 `../`（dev 态）
5. 全失败 → 输出诊断 + 退出 1（让 Claude 转述给用户，要求 export 环境变量或安装缺失 plugin）

### 跨 sub-skill 引用（同 plugin 内）

同 plugin 内的 sub-skill 之间用 `$SKILL_DIR/../<sibling>/...` 兄弟相对路径。Claude Code marketplace cache 与 Cursor/Codex flat layout 下都成立（同 plugin 的 sub-skill 总是兄弟）。tests/test_skill_format.py 第 10 项断言 `test_cross_skill_refs_within_plugin` 强制此规则。

### SessionStart hook（仅 solution-master）

7 个 plugin 中**仅 solution-master** 注册 SessionStart hook（Claude Code 用 `hooks.json`，Cursor 用 `hooks-cursor.json`）：

- 项目门禁：仅当 cwd 含 `drafts/` / `docs/specs/` / `skills/go/SKILL.md` / `.claude/skills/go/SKILL.md` 任一时触发
- 触发后 cat 主 SKILL.md 全文注入到 additionalContext（铁律 + 文件导航 + 子智能体调度全量）
- 其它 plugin 不重复注册——多个同步 hook 会让会话启动时间线性叠加；其它 plugin 的提示性内容用 SKILL description 承载即可

其它 agent（Codex / OpenCode）暂无 hook 机制；铁律靠主 SKILL.md description 自然语言匹配触发（best-effort）。

### 子智能体调度（仅 solution-master）

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

---

## 开发者参考

### 开发者工具（先看这两个）

#### `/plugin-review`：发版前深度体检

仓库内置一条针对本 monorepo 量身定制的深度 review slash command（`.claude/commands/plugin-review.md`），用于在发版或重构前对**待发布的某个 plugin 或全部 plugin** 做穷尽式体检，产出 `REVIEW_FINDINGS.md` 供后续 plan 模式直接消费。**只读不写**：不改代码、不改 marketplace.json、不 commit、不 `/reload-plugins`。

**用法**（在 Claude Code 会话里）：
- 全量审查：`/plugin-review`
- 聚焦某个 plugin：`/plugin-review solution-master`（元数据一致性与跨 plugin 依赖两个维度仍会跨 plugin 扫，因为这两维度本身就跨插件）

**触发后会发生什么**：
1. **阶段 1 速写**（Bash/Read 串行）→ 15 行项目快照：从 `marketplace.json` 实际枚举的所有 plugin `name@version`、SKILL 总数、bin / hook / MCP 清单、最近 commit、可疑未跟踪物
2. **阶段 2 并行 8 个 Explore agent**（单条消息并发 spawn）→ 每个维度独立深挖，主上下文只收摘要：
   - A. 元数据一致性审计（marketplace.json ↔ plugin.json ↔ README 三处版本号）
   - B. SKILL frontmatter 与触发质量（description 能否被 Claude 正确识别）
   - C. Plugin runtime 陷阱（`$VAR` 不带花括号的静默失效 bug、bin 命名冲突、shebang）
   - D. 跨 plugin 依赖健康度（可选依赖的降级分支是否真的实现）
   - E. Bin 脚本质量（subprocess 安全、跨平台路径、密钥泄露、`_ensure_deps.py` 健壮性）
   - F. Hook 安全与稳定性（SessionStart 注入失败阻塞会话风险）
   - G. MCP server 与配置管理（`~/.config/` 多路径迁移覆盖度、密钥权限）
   - H. 发布物卫生（避免 bundled 大体积资产复发）
3. **阶段 3 交叉验证** → 把 `[推断]` 用 Read/Grep 核实或降级删除，跨 agent 去重
4. **阶段 4 落盘** → 生成 `REVIEW_FINDINGS.md`（已在 `.gitignore` 中，不入库），含缺陷清单、按 plugin / 维度分组索引、修复批次建议（Batch A/B/C/D）
5. **阶段 5 交接** → 6 行总结 + 建议进 plan 模式处理 Batch A

**维护提醒**：下次插件拓扑变化（新增 plugin、调整依赖、引入新 hook 或 MCP）时，记得回头更新 `.claude/commands/plugin-review.md` 里的"项目知识底座"章节——它是给 agent 的事实基线，过时会误导审查。

#### `tests/test_skill_format.py`：SKILL.md 格式自动化检查

```bash
python3 -m pytest tests/test_skill_format.py -v
```

10 项断言：
1. 每个 SKILL.md 必须用 block scalar description（`description: >`），避免 vercel CLI 解析单行长 description 失败
2. 含 §跨平台兼容性 checklist 段
3. 含 `<SUBAGENT-STOP>` 段，且文案含 "Task prompt" 判定条件
4. 不引用已删的 `commands/` 路径
5. 不含 `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}` 占位符（仅 anythingllm-mcp 的 `plugin.json` 豁免）
6. anythingllm-mcp `plugin.json` 含 `${CLAUDE_PLUGIN_ROOT}`（专门豁免，验证它在）
7. 不用 `command -v <bin>`（应改用 5 段式 installed_plugins.json fallback）
8. vercel CLI 实测识别 10 skills（draw / image-gen / browse / solution-master / make / taa / taw / tpl / trv / twc）
9. 全部 `description: >` 段下首行不为空（YAML block scalar 语法要求）
10. **跨 sub-skill 引用 `$SKILL_DIR/../<sibling>/` 与 `${...:-$SKILL_DIR/..}/skills/<sibling>/` 中 `<sibling>` 必须是同 plugin 的真实 sub-skill 目录**（防回归跨 plugin 假设）

CI / 提 PR 前必跑。

---

### 版本号 bump 规则

每次改了某个 plugin 的代码，要在 **三个版本号** 上都 +1：

1. **plugin 自己的版本号**（如 `ai-image/.claude-plugin/plugin.json` 的 `version`）—— 告诉客户端"这个 plugin 有新版了"
2. **marketplace 目录里该 plugin 的版本号**（`.claude-plugin/marketplace.json` 里 `plugins[]` 数组中那一条的 `version`）—— 告诉商店"目录该更新啦"
3. **marketplace 自己的版本号**（`.claude-plugin/marketplace.json` 的 `metadata.version`）—— 告诉客户端"商店目录有改动，来重新抓一下"

打个比方：

- **plugin** = 一本书的新版
- **marketplace 目录里的 entry** = 书店的书单
- **marketplace 顶层版本** = 书单的修订号

书出了新版，你不光要把书本身换成新版，还得让书店在书单上把那本书标成新版本，更要告诉大家"书单我更新过了，来重新拿一份看看"。三步缺一步，客户那边就还以为是老版本，继续按老的买。

**只改了哪个 plugin 就只 bump 那一个的 entry**，其他 plugin 版本号不动——这样别人升级时只会拿到你改的那个，不会被误更新到别的。

**bump level 规则**：
- 修 bug / 文档 / 内部重构 = **patch +1**（如 `1.0.0 → 1.0.1`）
- 破坏性变更（删 SKILL / 改命令字符串 / 改 sub-skill dir 名 / 改公开入口）= **minor +1**（如 `1.0.0 → 1.1.0`）
- 仓库整体大重构（marketplace breaking）= **major +1**（如 `1.x → 2.0.0`）—— 要在 commit message + marketplace.json description 醒目说明
- marketplace 顶层 bump level **至少跟随子 plugin 最高级别**——任一 plugin minor bump 时，顶层也至少 minor

施工日复核：

```bash
grep '"version"' .claude-plugin/marketplace.json */.claude-plugin/plugin.json
```

三处版本号必须保持一致：marketplace.json 顶层 `metadata.version` + 各 plugin entry 的 `version` + 各 plugin 自己的 `plugin.json` 的 `version`。
