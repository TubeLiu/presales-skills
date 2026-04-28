# presales-skills — 灵雀云售前工作 skill 集合

灵雀云（Alauda）售前与市场团队建设和维护的 SKILL 集合，统一通过 marketplace 分发。

**目标用户**：灵雀云售前 / 解决方案 / 市场团队成员，希望帮助大家少掉头发，多产输出；少熬夜加班，多陪陪自己和家人。

**兼容性**：同时支持 **Claude Code**（marketplace 直装）和 **Cursor / Codex / OpenCode**（[vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 装）。

---

## 8 个 plugin 一览

按角色拆分：4 个**共享 plugin** 提供底层能力（被主 plugin 调用，也可独立使用），3 个**主 plugin** 串成端到端业务流程，1 个**开发者工具 plugin** 用于审查和优化 skill 自身。

### 共享 plugin（底层能力 / 4 个）

| plugin | 入口 | 一句话 |
|---|---|---|
| **ai-image** | `/ai-image:gen` 或 `/image-gen` | 统一 AI 生图引擎——13 个后端（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter）共享一份模型注册表与配置。被 solution-master / ppt-master / tender-workflow 共同依赖 |
| **web-access** | `/web-access:browse` 或 `/browse` | 联网操作 + CDP 浏览器自动化（搜索 / 抓取 / 登录态 / 浏览器自动化），并提供 `mcp_installer.py` 把 tavily / exa / minimax 等搜索类 MCP server 一键注册到 `~/.claude.json`，且支持 `list-search-tools` 子命令实时枚举当前会话所有可用搜索 MCP（让 sm/tw setup 动态选默认） |
| **drawio** | `/drawio:draw` 或 `/draw` | Draw.io 图表（`.drawio` XML + 可选 PNG/SVG/PDF 导出），覆盖架构图 / 流程图 / 时序图 / ER 图 / 拓扑图 / ML 模型图等 |
| **anythingllm-mcp** | （MCP server，无 slash） | AnythingLLM 知识库语义搜索——装上自动注册 `anythingllm` MCP server，主 plugin 通过 `mcp__anythingllm__*` 工具直接调用 |

### 主 plugin（端到端业务流程 / 3 个）

| plugin | 入口 | 一句话 |
|---|---|---|
| **solution-master** | `/solution-master:go` 或 `/solution-master` | 通用解决方案撰写：苏格拉底式提问 → 任务分解 → 子智能体并行撰写 → 双阶段审查（spec + quality）→ 多源知识检索 → 配图 → Markdown + DOCX 输出 |
| **ppt-master** | `/ppt-master:make` 或 `/make` | 多源文档（PDF / DOCX / URL / Markdown）→ 原生可编辑 PPTX（SVG 流水线 + 真实 PowerPoint shape，**默认套灵雀云模板**） |
| **tender-workflow** | `/tender-workflow:taa` / `:taw` / `:tpl` / `:trv` / `:twc` | 四角色招投标 + 配置：`tpl` 招标策划（甲方）/ `taa` 招标分析（乙方）/ `taw` 标书撰稿（乙方，并行写）/ `trv` 多维度审核 / `twc` 配置 |

### 开发者工具 plugin（meta / 1 个）

| plugin | 入口 | 一句话 |
|---|---|---|
| **skill-optimizer** | `/skill-optimizer:optimize` 或 `/optimize` | Skill 审查与优化器——按 5 步流程（Scope → Review → Plan → Implement → Verify）审查目标 skill 的触发语义、工作流门槛、资源组织、安全边界、依赖可安装性与 README/SKILL 职责分层；默认先给诊断与计划，等用户明确说"按计划执行"才改文件。独立 plugin，不依赖其它 plugin |

> **触发方式两种皆可**：
> - **slash 命令**：`/<plugin>:<sub-skill>`（如 `/solution-master:go`），Claude Code 自动补全短 alias 到 canonical
> - **自然语言**：每个 SKILL.md 的 `description:` 字段含触发关键词，"画一张架构图" / "生成图片" / "做 PPT" / "写方案" / "看看这份招标文件" 等都能直接触发对应 sub-skill

---

## 安装

### 路径 A：Claude Code（主要使用方式）

```
/plugin marketplace add Alauda-io/presales-skills
/plugin install ai-image@presales-skills
/plugin install web-access@presales-skills
/plugin install drawio@presales-skills
/plugin install anythingllm-mcp@presales-skills        # 可选
/plugin install solution-master@presales-skills
/plugin install ppt-master@presales-skills
/plugin install tender-workflow@presales-skills
/plugin install skill-optimizer@presales-skills        # 可选（开发者工具：审查 / 优化 skill 自身）
/reload-plugins
```

依赖顺序：先装共享 plugin，再装主 plugin。`anythingllm-mcp` 可选，未装时主 plugin 自动降级为本地 YAML 索引 + 联网检索。`skill-optimizer` 可选，仅在你打算审查 / 优化 skill 时装。

预期 reload 输出：`8 plugins · 11 skills · 1 hook · 1 plugin MCP server`
- 1 hook：solution-master 的 SessionStart 注入主 SKILL（仅在 SM 项目内 cwd 时触发）
- 1 MCP server：`anythingllm`（来自 anythingllm-mcp plugin；不装时无）

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

vercel-labs/skills CLI 会扫描所有 SKILL.md 并 symlink/copy 到目标 agent 的标准目录。**默认装到 cwd `.agents/skills/`**（项目级），加 `-g` 装到 `~/.agents/skills/`（全局）。只装部分 sub-skill：`-s '*'` 装全部，或 `-s image-gen,draw,make,optimize` 指定。完整 CLI 参数：`npx --yes skills --help`。

---

## 快速开始

> **使用心法**：所有 plugin 的"配置"和"使用"都直接对 AI 说自然语言即可——不用记 CLI 参数，AI 会按对应的 setup wizard 一步步引导你完成。

### 第 1 步：先配置共享 plugin

#### `ai-image` —— 统一 AI 生图引擎

装好后**先让 AI 配置一下**：

```
> 配置 ai-image
```

AI 会引导你：选 13 个 provider 中你打算用的几个 → 填 API keys（按需）→ 选默认 provider → 选默认尺寸 → validate。配完后：

```
> 生成一张图：现代简约风的容器云架构示意
> 用 ark 生成一张 K8s 网络拓扑图
> /ai-image:gen "futuristic cloud platform dashboard, hi-tech aesthetic"
```

按 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider` 选 provider；自然语言中显式指定 provider 名（ark / dashscope / gemini / openai / ...）会覆盖默认。

#### `web-access` —— 联网 + 浏览器自动化 + MCP 搜索注册

装好后**先让 AI 配置一下**：

```
> 配置 web-access
```

AI 会引导你：检测 Node.js 22+（缺则自动装）→ 启用 Chrome remote debugging（按提示在 `chrome://inspect/#remote-debugging` 打勾，重启浏览器）→ 启动并验证 CDP Proxy（端口 :3456）→ 风险告知确认。配完后：

```
> 帮我搜一下 X 公司的最新动态
> 抓一下这个小红书帖子的内容（需要登录态）
> /web-access:browse "https://www.example.com/page"
```

**额外能力**：web-access 内置 `mcp_installer.py`，被 `/twc setup` 和 `/solution-master setup` 用来一键注册 tavily / exa / minimax-token-plan 三类 web 搜索 MCP server 到 `~/.claude.json`，缺 `node`/`uv` 时自动用户级安装，不用 sudo。

#### `drawio` —— 装上即用（无需 wizard）

drawio 装好就能用：

```
> 画一张架构图：用户 → API 网关 → 微服务集群 → 数据库
> /drawio:draw "GitOps 蓝绿发布流程图"
```

输出 `.drawio` 源文件；本机若装了 draw.io 桌面版或 `drawio-cli`，同时导出 PNG / SVG / PDF：

```bash
brew install --cask drawio                   # macOS
npm install -g @drawio/drawio-desktop-cli    # 跨平台
```

#### `anythingllm-mcp` —— 装上自动注册（无需 wizard）

无 slash 入口——装上后自动注册 `anythingllm` MCP server，主 plugin（solution-master / tender-workflow）通过 `mcp__anythingllm__anythingllm_search` 直接调用本地 / 远程的 AnythingLLM workspace。**未装时**主 plugin 自动降级为本地 YAML 索引 + 联网检索，不会 hard-fail。

需先在本机或远程跑 [AnythingLLM](https://anythingllm.com/) 服务并建好 workspace；workspace slug 在 solution-master / tender-workflow 各自的 setup wizard 里填。

---

### 第 2 步：配置并使用 `solution-master` —— 写方案

**先配置**：

```
> 配置 solution-master
```

AI 会引导你：本地知识库路径 → AnythingLLM workspace（可选）→ MCP 搜索工具优先级（tavily / exa / minimax，其中任一）→ CDP 登录态站点（可选）→ draw.io 桌面版检测 → API keys 透传到 ai-image → validate。

**再使用**：

```
> 帮我写一份面向金融行业的容器云技术方案
> /solution-master:go "GitOps 蓝绿发布技术方案"
```

solution-master 在 SM 项目目录（含 `drafts/` / `docs/specs/` / 装了 `solution-master:go` SKILL）内会触发 **SessionStart hook 自动注入主 SKILL.md 铁律**，按以下工作流走：

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

---

### 第 3 步：（可选）使用 `ppt-master` —— 做 PPT

**无专属配置**：API keys 共享自 ai-image，所以只要装好 `ai-image` plugin 并配过 keys，`ppt-master` 装上就能用。

**使用**：

```
> 把这份 PDF 做成 12 页 PPT
> 把这个微信公众号文章做成演示稿
> /ppt-master:make /path/to/source.pdf
```

**默认套灵雀云模板**（v1.0.0 起的 default path）。要切换或退出：

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

---

### 第 4 步：配置并使用 `tender-workflow` —— 招投标

**先配置**：

```
> 配置 tender                                   # 一次性配好 4 个角色（tpl/taa/taw/trv）共享的统一配置
```

AI 会引导 6 步：本地知识库路径 → AnythingLLM（可选）→ drawio 检测 → MCP 搜索工具（tavily / exa / minimax，调 `web-access` 的 `mcp_installer.py`）→ skill 默认值（taa 厂商名 / tpl 模板等）→ validate。

**再使用**（按场景对应触发）：

```
> 看看这份招标文件                        # → /tender-workflow:taa 招标分析
> 帮我写标书的第三章                       # → /tender-workflow:taw 撰稿
> 根据这份产品功能清单生成招标技术规格       # → /tender-workflow:tpl 策划（甲方）
> 审一下这份投标方案                       # → /tender-workflow:trv 审核
```

四角色细节见 `tender-workflow/README.md`。

---

### 第 5 步：（可选）使用 `skill-optimizer` —— 审查 / 优化 skill

**无专属配置**：skill-optimizer 是只读+按计划改的 meta 工具，装上即用。

**使用**：

```
> 优化这个 skill: <path/to/SKILL.md>
> 审一下 ai-image 的 SKILL.md
> 检查 solution-master skill 的触发语义
> /skill-optimizer:optimize tender-workflow/skills/taa
```

固定 5 步流程：

```
Scope（确认范围）
  ↓
Review（读 SKILL.md + 按需读 references / scripts）
  ↓
Plan（输出审查结论 + 优化计划）—— ⚠ 等你明确说"按计划执行"才进下一步
  ↓
Implement（小步改文件）
  ↓
Verify（多维校验 + 汇报）
```

**关键约束**："我看看"/"有道理"/"先这样"不算确认；只有"按计划执行"/"开始修改"/"确认修改"等明确的开始执行类语句才会真正改文件。审查阶段发现疑似敏感信息（API Key / Token / Cookie / 账号）只描述类型与位置，不回显完整值。

适用场景见 `skill-optimizer/README.md`。

---

## 跨 agent 兼容性矩阵

主用 Claude Code；其它 agent 通过 vercel-labs/skills CLI 装得到核心能力，但 hook / MCP / 跨 plugin 引用等高级特性会降级。

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
| `mcp_installer.py` 注册 web 搜索 MCP（tavily/exa/minimax） | ✅ 写 `~/.claude.json` reload 即生效 | ⚠ 配置文件位置不同，需手动套 schema | ⚠ 同上 | ⚠ 同上 |
| `mcp_installer.py list-search-tools` 动态发现已装 MCP（sm/tw setup 让用户选默认搜索工具） | ✅ 直接读 `~/.claude.json` + spawn 各 server `tools/list` | ❌ 不可用（脚本硬编码 `~/.claude.json` 路径，Cursor/Codex 无此文件）；用户需手写 `mcp_search.priority` FQN 列表 | ❌ 同上 | ❌ 同上 |

> **维护者承诺范围**：端到端流程**仅在 Claude Code 上完整验证**。Cursor / Codex / OpenCode 上通过 vercel-labs/skills CLI 安装能跑通基础场景；hook、MCP server 自动注册、跨 plugin 引用等需自行配置或绕开——欢迎社区把验证结果反馈到 issue tracker。

---

## 配置一览

4 个 plugin 自带交互式 setup wizard，全部对 AI 说自然语言即可触发：

| 你说什么 | 对应 wizard |
|---|---|
| `配置 ai-image` / `首次配置` | API keys（13 provider 任一）→ 默认 provider → 默认尺寸 → validate |
| `配置 web-access` / `启用 CDP` | Node.js 22+ → Chrome remote debugging → CDP Proxy 启动验证 → 风险告知 |
| `配置 solution-master` | localkb → AnythingLLM（可选）→ MCP 搜索注册（tavily/exa/minimax）→ **动态枚举所有已装 MCP 让你选默认** → CDP 登录态站点（可选）→ draw.io 检测 |
| `配置 tender` / `配置工作流` | 6 步 tender 专属配置（localkb / anythingllm / drawio / mcp_search 注册 + 选默认 / skill 默认值） |

每个 wizard 一步问、立即写入、立即验证；任何"可选"字段都允许跳过。

**其它 plugin 不需要专属配置**：`ppt-master` 复用 ai-image API keys；`drawio` 运行时自动检测桌面版 CLI；`anythingllm-mcp` 装上自动注册 MCP server；`skill-optimizer` 装上即用。

### 配置文件分布

| 文件 | 字段 | 由哪个工具管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml` | `api_keys` / `ai_image` / `ppt_master.default_layout`（共享） | ai-image 的 `ai_image_config.py` |
| `~/.config/solution-master/config.yaml` | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search` | solution-master 的 `sm_config.py` |
| `~/.config/tender-workflow/config.yaml` | tender 专属字段 | tender-workflow 的 `tw_config.py` |
| `~/.claude.json` 顶层 `mcpServers` | tavily / exa / minimax / anythingllm 等 MCP server 注册 | web-access 的 `mcp_installer.py`（搜索类）/ anythingllm-mcp `plugin.json`（自动） |

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

# web-access 注册 web 搜索 MCP server
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" check uv
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" register minimax --key=sk-cp-xxxx
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" test minimax
```

`$AI_IMAGE_DIR` / `$SM_DIR` / `$TW_DIR` / `$WA_DIR` 通过各自 SKILL.md 顶部的 §路径自定位 段（`installed_plugins.json` 五段式 fallback）解析。

---

## 跨平台

### macOS / Linux

零特殊步骤，按上面"安装"路径走即可。`ppt-master` 需要系统级 pandoc + cairo：

```bash
brew install pandoc cairo                 # macOS
apt install pandoc libcairo2-dev          # Debian / Ubuntu
```

### Windows

**推荐方式（二选一）**：
- **WSL 2**：零改动，原生 Linux 体验
- **Windows 原生 + [Git for Windows](https://git-scm.com/downloads/win)**：Claude Code 自身依赖 Git Bash（[官方说明](https://docs.claude.com/en/docs/claude-code/setup)）。装完 Git for Windows + Python ≥ 3.10 即可

**不支持**：纯 PowerShell / CMD + 不装 Git for Windows。

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

## 架构原理

### 仅用 `skills/`（不用 `commands/` / `agents/`）

6 个有用户入口的 plugin（drawio / ai-image / ppt-master / solution-master / web-access / skill-optimizer）和 5 个 tender-workflow sub-skill 全部用 `skills/<X>/SKILL.md` 注册。**不用** Claude Code 的 `commands/` 或 `agents/` 机制，原因：
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

同 plugin 内的 sub-skill 之间用 `$SKILL_DIR/../<sibling>/...` 兄弟相对路径。Claude Code marketplace cache 与 Cursor/Codex flat layout 下都成立（同 plugin 的 sub-skill 总是兄弟）。`tests/test_skill_format.py` 第 10 项断言 `test_cross_skill_refs_within_plugin` 强制此规则。

### SessionStart hook（仅 solution-master）

8 个 plugin 中**仅 solution-master** 注册 SessionStart hook（Claude Code 用 `hooks.json`，Cursor 用 `hooks-cursor.json`）：

- 项目门禁：仅当 cwd 含 `drafts/` / `docs/specs/` / `skills/go/SKILL.md` / `.claude/skills/go/SKILL.md` 任一时触发
- 触发后 cat 主 SKILL.md 全文注入到 additionalContext（铁律 + 文件导航 + 子智能体调度全量）
- 其它 plugin 不重复注册——多个同步 hook 会让会话启动时间线性叠加；其它 plugin 的提示性内容用 SKILL description 承载即可

其它 agent（Codex / OpenCode）暂无 hook 机制；铁律靠主 SKILL.md description 自然语言匹配触发（best-effort）。

### 子智能体调度（solution-master / tender-workflow taw）

solution-master 与 tender-workflow `taw` 的子智能体（writer / spec-reviewer / quality-reviewer）通过 **Task tool** 委派——把 `agents/<role>.md` 完整内容作为 Task prompt body 传入：

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

### web 搜索 MCP server 的统一注册

`web-access/skills/browse/scripts/mcp_installer.py` 提供 6 子命令 CLI（`check` / `auto-install` / `probe` / `register` / `test` / `unregister`），把 tavily / exa / minimax-token-plan 三类用户级 MCP server 统一注册到 `~/.claude.json`。tender-workflow / solution-master 的 setup wizard 通过 `installed_plugins.json` 探针定位本脚本调用，避免在两个 wizard 内重复 inline python。`auto-install` 走用户级路径（uv 用 astral.sh install.sh / install.ps1；node 优先 fnm/brew/winget）不要 sudo；`test` 子命令独立 spawn server 跑 MCP JSON-RPC 握手 + tools/call 实测，**不依赖 reload-plugins**。

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

#### `tests/test_skill_format.py`：SKILL.md / 文档自动化检查

```bash
python3 -m pytest tests/test_skill_format.py -v
```

24 项断言（含基础格式 + skill-specific 业务规则 + MCP wizard lint），每次提 PR 前必跑。覆盖：
- SKILL.md 必须用 block scalar `description: >`（避免 vercel CLI 解析失败）
- 含 §跨平台兼容性 checklist + `<SUBAGENT-STOP>` 段
- 不引用已删的 `commands/` 路径 / `${CLAUDE_PLUGIN_ROOT}` 占位符（仅 anythingllm-mcp 豁免）
- 不用 `command -v <bin>`（统一走 5 段式 installed_plugins.json fallback）
- vercel CLI 实测识别 11 skills（draw / image-gen / browse / solution-master / make / taa / taw / tpl / trv / twc / optimize）
- 跨 sub-skill `$SKILL_DIR/../<sibling>/` 引用必须是同 plugin 真实 sibling
- subagent prompt body 含工具限制段
- taw writer 标题去编号 / reviewer STATUS 协议 / image_plan 字段结构 / SKILL.md ≤500 行
- tender-workflow 无残留 `docs/` 链接
- mcp_installer.py 含三 provider TEMPLATES + sk-cp- 校验 + understand_image
- twc / sm setup.md 含 minimax + sk-cp- + WA_INSTALLER 探针
- web-access README 暴露 mcp_installer / tender-workflow README MCP 段含 minimax

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
