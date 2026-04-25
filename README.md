# presales-skills — 售前工作流 Claude Code plugin 集

一个 umbrella marketplace，把售前场景下的 AI 辅助工作流按职责拆成 7 个独立的 Claude Code plugin，通过同一个 marketplace 统一分发。

## 包含的 7 个 plugin

| plugin | 类型 | 用途 |
|---|---|---|
| **solution-master** | 主 plugin | 通用解决方案撰写框架：苏格拉底式需求提取、子智能体驱动撰写、双重审查、多源知识检索、上下文感知配图、Markdown/DOCX 输出 |
| **ppt-master** | 主 plugin | 从 PDF / DOCX / URL / Markdown 等多源文档生成原生可编辑 PPTX（SVG 流水线） |
| **tender-workflow** | 主 plugin | 四角色招投标工作流：`tpl`（招标策划）/ `taa`（招标分析）/ `taw`（标书撰稿）/ `trv`（审核）+ `twc`（配置） |
| **drawio** | 共享 plugin | Draw.io 图表生成（`.drawio` XML + PNG/SVG/PDF 导出）。被 solution-master / tender-workflow 依赖 |
| **ai-image** | 共享 plugin | 统一 AI 图片生成：13 个后端（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter）+ 共享 YAML 模型注册表 + `/ai-image-config-*` 配置管理。被三个主 plugin 依赖 |
| **anythingllm-mcp** | 共享 plugin | AnythingLLM MCP server：知识库语义搜索 + workspace 列举。被 solution-master / tender-workflow 可选依赖；不装则降级为本地 YAML 索引或联网检索 |
| **web-access** | 独立 plugin | 联网操作 + CDP 浏览器自动化（vendored from [eze-is/web-access](https://github.com/eze-is/web-access)）。solution-master 可选依赖，仅在启用 `cdp_sites` 登录态站点检索时必需 |

---

## 安装

### Step 1：注册 marketplace

在 Claude Code 会话里执行：

```
/plugin marketplace add Alauda-io/presales-skills
```

（也支持本地路径：`/plugin marketplace add /path/to/presales-skills`）

### Step 2：装齐 7 个 plugin

**依赖顺序**：先装共享 plugin（drawio / ai-image / anythingllm-mcp / web-access），再装主 plugin——否则主 plugin 会因为找不到依赖而运行失败（anythingllm-mcp 和 web-access 都是可选依赖：anythingllm-mcp 不装能降级为本地索引/联网检索；web-access 仅在启用 solution-master 的 `cdp_sites` 登录态站点检索时才必需，不用此功能可以不装）。

```
/plugin install drawio@presales-skills
/plugin install ai-image@presales-skills
/plugin install anythingllm-mcp@presales-skills
/plugin install web-access@presales-skills          # 可选：需要 CDP 登录态检索时装
/plugin install solution-master@presales-skills
/plugin install ppt-master@presales-skills
/plugin install tender-workflow@presales-skills
```

### Step 3：让 hook / MCP / PATH 生效

```
/reload-plugins
```

预期 reload 输出：`7 plugins · XX skills · 8 agents · 1 hook · 1 plugin MCP server`（数量含本 marketplace 的 7 个 plugin；若还装了其他 marketplace 的 plugin 或 baseline，总数会更多）
- 1 hook：solution-master 的 SessionStart 铁律注入
- MCP：`anythingllm`（由 anythingllm-mcp plugin 统一注册，solution-master 和 tender-workflow 共用；若未装 anythingllm-mcp 则无此 server）
- PATH：`drawio` 的 `drawio-gen`、`web-access` 的 `web-access-check` / `web-access-match-site` 入口会自动上 PATH，供 solution-master / tender-workflow 跨 plugin 调用

### Step 4：配置 AI 图片生成（首次使用前一次性完成）

```
/ai-image-config-setup                      # 创建 ~/.config/presales-skills/config.yaml 骨架
/ai-image-config-set api_keys.ark <key>     # 火山方舟
/ai-image-config-set api_keys.dashscope <key>   # 阿里云
/ai-image-config-set api_keys.gemini <key>      # Google Gemini
/ai-image-config-validate                   # 验证 key 已配置
```

若之前用过 solution-master / tender-workflow 的独立版本（`~/.config/solution-master/` 或 `~/.config/tender-workflow/`），可一次性迁移：

```
/ai-image-config-migrate
```

### Step 5：依赖（全自动）

**所有 Python 依赖由入口脚本首次调用时自动 `pip install`**，无需手动预装。

- ppt-master / ai-image 的每个入口脚本开头都调用 `_ensure_deps.py`：检查 `<plugin>/.deps-installed` marker，不存在则 `pip install -r requirements.txt`，装完 touch marker 跳过后续调用
- Plugin 升级（如 0.1.3 → 0.1.4）时 cache dir 带版本号，marker 不跨版本继承，自动触发新依赖的重装
- tender-workflow 的 `/twc` 类似逻辑：首次运行自动安装 `pyyaml`
- MCP server（AnythingLLM）纯 Node 内置模块实现，零 npm 依赖
- drawio plugin：若需导出 PNG/SVG/PDF，额外装一次 `drawio-cli` 或 draw.io 桌面版（见下一节"使用"）

**控制自动安装**：设 `PRESALES_SKILLS_SKIP_AUTO_INSTALL=1` 可禁用自动 pip（适合 CI、容器、用户自己管 venv 的场景）。这时所需依赖请手动装：

```bash
# 仅在 PRESALES_SKILLS_SKIP_AUTO_INSTALL=1 时需要手动跑
pip install -r ~/.claude/plugins/cache/presales-skills/ppt-master/*/requirements.txt
pip install -r ~/.claude/plugins/cache/presales-skills/ai-image/*/requirements.txt
```

### Step 6：Windows 支持

**推荐方式（二选一）**：

- **WSL 2**：零改动，原生 Linux 体验。IT 策略允许 WSL 的首选
- **Windows 原生 + [Git for Windows](https://git-scm.com/downloads/win)**：Claude Code 官方要求宿主必装 Git Bash，Claude Code 自身"internally uses Git Bash to execute commands regardless of where you launched it"（参见 https://docs.claude.com/en/docs/claude-code/setup）。装完 Git for Windows 和 Python ≥ 3.10 即可

**不支持**：纯 PowerShell / CMD + **不**装 Git for Windows。Claude Code 自身就依赖 Git Bash，这一层我方无法绕开。

**依赖说明**：

- `ppt-master` 需要系统级 pandoc + cairo：
  - WSL 2：`apt install pandoc libcairo2-dev`（最简单）
  - Windows 原生：`choco install pandoc` + [GTK runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer) 提供 cairo
- SKILL.md 示例中出现的 `python3` 命令在 Windows 原生 Git Bash 下若没有 `python3` 别名，请替换为 `python` 或 `py`
- **不要用 MSYS2 Python 代替原生 Windows Python**：`platform.system()` 在 MSYS2 Python 下返回 `MSYS_NT-10.0`，会触发 `ppt-master/pptx_template_import.py` 的非 Windows 异常分支

### 更新

远程订阅默认不自动更新：

```
/plugin marketplace update presales-skills
/reload-plugins
```

### 从 0.1.5 及更早版本升级到当前版本

本仓库在 `solution-master 0.1.6` 版本里把 `web-access` skill 拆成了独立的 `web-access` plugin。如果你之前装的是 `solution-master ≤ 0.1.5` 且启用了 CDP 登录态站点检索（`/solution-config` 里打开了 `cdp_sites.enabled`），升级后需要额外一步：

```
/plugin install web-access@presales-skills
/reload-plugins
```

否则 `/solution-config validate` 会报 `web-access plugin 未安装`，且 `knowledge-retrieval` 的第四层（CDP 登录态检索）会自动跳过。不使用 CDP 登录态检索的用户无需安装 `web-access`。

---

## 使用

### solution-master — 写解决方案

会话里直接描述你的项目需求，比如"帮我写一份面向金融行业的容器云技术方案"。solution-master 的 SessionStart hook 会自动注入铁律 + 技能路由，之后按工作流走：

```
solution-brainstorming（苏格拉底式提问）
    ↓
solution-planning（拆任务 + 验收标准）
    ↓
每章循环：knowledge-retrieval + ai-image 配图 + writer 子智能体
    ↓
spec-reviewing（内容审查）+ quality-reviewing（写作审查）
    ↓
docx-formatting（输出 DOCX）
```

配置管理：`/solution-config setup / show / models / validate`

### ppt-master — 生成 PPT

会话里直接让 AI "从这份 PDF 做 10 页 PPT"、"把这个微信公众号文章做成演示"等。ppt-master skill 自动响应。工作流：

```
源文档 → 项目初始化 → 模板选择 → 策略师（strategist）→ 图片生成器 → 执行者 → 后处理 → 导出 PPTX
```

详细规则见 `ppt-master/skills/ppt-master/SKILL.md`。

### tender-workflow — 招投标文档

四个角色按场景触发：

| 命令 | 角色 | 服务对象 |
|---|---|---|
| `/tpl <产品能力清单>` | 策划者 | 甲方：生成招标技术规格 + 评标办法（无控标痕迹），DOCX 格式 |
| `/taa <招标文件>` | 分析者 | 乙方：分析招标内容 + 生成投标大纲（Markdown + DOCX） |
| `/taw <大纲>` | 撰稿者 | 乙方：按大纲 + 知识库 + AI 配图撰写章节内容（DOCX） |
| `/trv <产出物>` | 审核者 | 甲乙双方：多维度审核各阶段产出 |

配置管理：`/twc setup / show / set / models / validate / migrate`

### drawio — 画图

会话里说"画一个架构图：用户 → 网关 → 微服务"等，自动触发 drawio skill。生成 `.drawio` 源文件；若本机装了 `drawio-cli` 或 draw.io 桌面版，同时导出 PNG/SVG/PDF。

安装 CLI：
```bash
brew install --cask drawio          # macOS
npm install -g @drawio/drawio-desktop-cli   # 跨平台
```

### ai-image — 生图 + 配置中心

直接触发："生成一张图"、"画一张某某主题的图"。根据 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider` 选 provider，走 `ai_image_generator.py` 调用。

配置管理的 7 个命令：
- `/ai-image-config-setup` — 交互式首次配置
- `/ai-image-config-show [section]` — 展示当前配置（API keys 自动 mask）
- `/ai-image-config-set <key> <value>` — 按 dotted path 设值
- `/ai-image-config-models [provider]` — 展示 13 provider 的模型注册表
- `/ai-image-config-add-model <provider> <yaml>` — 追加自定义模型到用户级 override 文件
- `/ai-image-config-validate [provider]` — 验证 API key 是否可用
- `/ai-image-config-migrate` — 合并旧的 solution-master / tender-workflow 配置到统一位置

---

## 目录结构

```
presales-skills/                           # umbrella marketplace（本仓库）
├── .claude-plugin/
│   └── marketplace.json                   # 声明 7 个 plugin 的入口
├── README.md                              # 本文件
│
├── drawio/                                # 共享 plugin：Draw.io 图表生成
│   ├── .claude-plugin/plugin.json
│   ├── bin/drawio-gen                     # PATH 命令：drawio-gen（wrapper → scripts/drawio_generator.py）
│   ├── skills/drawio/SKILL.md             # 用户触发的 skill（"画流程图"等）
│   └── scripts/drawio_generator.py        # Python 实现（调 drawio-cli 生成 .drawio + 导出）
│
├── ai-image/                              # 共享 plugin：统一 AI 图片生成
│   ├── .claude-plugin/plugin.json
│   ├── bin/
│   │   ├── image-gen                      # PATH 命令：image-gen
│   │   └── ai-image-config                # PATH 命令：ai-image-config
│   ├── skills/
│   │   └── ai-image/SKILL.md              # "生成图片"触发语
│   ├── commands/                          # 7 个 slash command 文件
│   │   ├── ai-image-config-setup.md
│   │   ├── ai-image-config-show.md
│   │   ├── ai-image-config-set.md
│   │   ├── ai-image-config-models.md
│   │   ├── ai-image-config-add-model.md
│   │   ├── ai-image-config-validate.md
│   │   └── ai-image-config-migrate.md
│   ├── prompts/
│   │   └── ai_image_models.yaml           # 13 provider 共享注册表
│   ├── scripts/
│   │   ├── image_gen.py                   # env-var 驱动的多 backend 分发器
│   │   ├── image_backends/                # 13 个 backend 实现（gemini/openai/...）
│   │   └── ai_image_config.py             # 配置 CLI（setup/show/set/models/migrate/validate）
│   └── requirements.txt
│
├── anythingllm-mcp/                       # 共享 plugin：AnythingLLM MCP server
│   ├── .claude-plugin/plugin.json         # 含 mcpServers.anythingllm（无前缀，统一注册）
│   ├── README.md
│   └── tools/mcp-anythingllm/             # Node MCP server（纯内置模块，零 npm 依赖）
│       ├── index.js
│       └── package.json
│
├── solution-master/                       # 主 plugin：解决方案撰写框架
│   ├── .claude-plugin/plugin.json
│   ├── agents/                            # 3 个子智能体角色（writer / spec-reviewer / quality-reviewer）
│   ├── hooks/
│   │   ├── hooks.json                     # SessionStart hook 注册
│   │   └── session-start                  # 铁律注入脚本
│   └── skills/                            # 11 个 skill
│       ├── using-solution-master/         # SessionStart 注入的铁律 + 技能路由
│       ├── subagent-driven-writing/
│       ├── solution-brainstorming/
│       ├── solution-planning/
│       ├── solution-writing/
│       ├── spec-reviewing/
│       ├── quality-reviewing/
│       ├── knowledge-retrieval/           # 通过 mcp__anythingllm__* 调 anythingllm-mcp plugin
│       ├── docx-formatting/
│       ├── solution-config/               # /solution-config 相关，含 sm_config.py
│       └── writing-skills/
│       # （web-access 已抽为独立 plugin；见下方 `web-access/` 顶层目录）
│
├── web-access/                           # 共享 plugin：联网 + CDP 浏览器自动化（vendored from eze-is/web-access v2.5.0）
│   ├── .claude-plugin/plugin.json
│   ├── bin/
│   │   ├── web-access-check              # 环境自检 + 启动 CDP Proxy（跨 plugin 入口）
│   │   └── web-access-match-site         # 按 domain 查询站点经验（跨 plugin 入口）
│   ├── THIRD_PARTY_NOTICES.md
│   └── skills/web-access/
│
├── ppt-master/                            # 主 plugin：PPT 生成
│   ├── .claude-plugin/plugin.json
│   └── skills/ppt-master/
│       ├── SKILL.md
│       ├── references/                    # 角色定义 + 技术规范
│       ├── scripts/                       # PPT 生成 pipeline 脚本（source_to_md / project_manager / svg_* / total_md_split 等）
│       └── templates/                     # layout / chart / 640+ 图标库
│
└── tender-workflow/                       # 主 plugin：招投标工作流
    ├── .claude-plugin/plugin.json
    ├── skills/
    │   ├── tpl/SKILL.md                   # /tpl 招标文件生成
    │   ├── taa/SKILL.md                   # /taa 招标分析（通过 mcp__anythingllm__* 调 anythingllm-mcp）
    │   ├── taw/SKILL.md                   # /taw 标书撰稿（同上）
    │   ├── trv/SKILL.md                   # /trv 审核
    │   └── twc/SKILL.md                   # /twc 配置管理
    └── tools/
        └── tw_config.py                   # 配置工具（/twc 委托）
```

---

## Plugin 规范（开发/扩展时参考）

本仓库的 plugin 布局严格遵循 Claude Code 官方约定，并采用以下**经过实测验证**的最佳实践。

### 1. plugin 根目录结构

每个 plugin 根目录必须有 `.claude-plugin/plugin.json` 作为 manifest。其他目录按约定自动被 Claude Code 识别：

| 目录 | 作用 | 注册方式 |
|---|---|---|
| `.claude-plugin/plugin.json` | **必需**。plugin 元数据（name / description / version / author / keywords）| marketplace 读取 |
| `skills/<name>/SKILL.md` | 主要触发入口，Claude 按 `description` 匹配用户输入 | 自动扫描 |
| `commands/<name>.md` | slash command 文件（`/<name>` 手动触发）| 自动扫描 |
| `agents/<name>.md` | 子智能体定义（被 skill 通过 Task tool 调用）| 自动扫描 |
| `hooks/hooks.json` | 声明式 hook 注册（SessionStart / PostToolUse 等）| 自动扫描 |
| `bin/<executable>` | **shell 可执行文件**，会被自动加到 PATH | 自动扫描 |
| `tools/mcp-*/` | MCP server 代码目录。在 `plugin.json` 的 `mcpServers` 字段里显式注册 | 手动声明 |

### 2. 路径引用规范

Claude Code 在 SKILL.md / commands.md / hooks.json / mcpServers 配置里做**文本替换**，注入以下变量：

| 变量 | 指向 | 用于 |
|---|---|---|
| `${CLAUDE_SKILL_DIR}` | 当前 skill 的 SKILL.md 所在目录 | SKILL.md 内部引用自家资源：`Read \`${CLAUDE_SKILL_DIR}/prompts/foo.yaml\`` |
| `${CLAUDE_PLUGIN_ROOT}` | 当前 plugin 根目录 | hooks.json / mcpServers.args 里定位 plugin 内脚本 |

**关键坑（实测定论）**：

- ✅ **必须带花括号**：`${CLAUDE_SKILL_DIR}` 才被替换；`$CLAUDE_SKILL_DIR` 不替换
- ❌ **子脚本不继承**：`!bash $CLAUDE_SKILL_DIR/run.sh` 调起的 `run.sh` 里 `$CLAUDE_SKILL_DIR` 是空的。必须显式 export 或 argv 传参
- ❌ **跨 plugin 禁止用 `${CLAUDE_PLUGIN_ROOT}/../<sibling>/`**：本地 marketplace 下能工作，但远程 marketplace cache 路径带 `<version>/` 层级，`..` 会落到错误目录

### 3. 跨 plugin 调用约定（本仓库的核心设计）

本 marketplace 里三个主 plugin 按需依赖共享 plugin（`ai-image` 被三个主 plugin 共享；`drawio` 被 solution-master / tender-workflow 依赖；`anythingllm-mcp` 被 solution-master / tender-workflow 可选依赖；`web-access` 被 solution-master 可选依赖）。跨 plugin 调用通过 **`bin/` + PATH** 机制实现，不走相对路径：

```bash
# ❌ 错误：硬编码相对路径（远程 marketplace 下失效）
python3 ${CLAUDE_PLUGIN_ROOT}/../ai-image/scripts/image_gen.py "提示词" ...

# ✅ 正确：共享 plugin 把执行入口放 bin/ 下，Claude Code 自动加 PATH，按名字调用
image-gen "提示词" ...
drawio-gen --type ... --topic ...
ai-image-config models
```

`bin/<command>` 是一个 shell wrapper：
```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/../scripts/<actual_script>.py" "$@"
```

它通过 `BASH_SOURCE` **自定位**，跟 plugin 被安装到哪（本地仓库 vs 远程 cache vs 用户 home）无关。

### 4. 跨 plugin **数据文件**定位（无法走 PATH 时）

Python 代码里需要读 sibling plugin 的数据文件（如 `ai-image/prompts/ai_image_models.yaml`），走 **候选列表 + glob** 模式：

```python
candidates = [
    # 1. 本地 marketplace（monorepo 布局）
    monorepo_root / "ai-image" / "prompts" / "ai_image_models.yaml",
    # 2. 远程 marketplace cache（glob 匹配 version 目录）
    *Path.home().glob(".claude/plugins/cache/*/ai-image/*/prompts/ai_image_models.yaml"),
    # 3. 用户级 override
    Path.home() / ".config" / "presales-skills" / "ai_image_models.yaml",
    # 4. 全局 skill fallback
    Path.home() / ".claude" / "skills" / "ai-image" / "prompts" / "ai_image_models.yaml",
]
for p in candidates:
    if p.exists():
        return p
```

solution-master 的 `sm_config.py._find_models_yaml()` 和 tender-workflow 的 `tw_config.py._find_models_yaml()` 都是这个模式的范例实现。

### 5. marketplace 缓存约定

Claude Code 的 plugin 缓存按 **(plugin-name, version)** 做 key。修改任何 plugin 内容后**必须 bump version**，否则 `/plugin marketplace update` 不会重新 clone：

```
.claude-plugin/plugin.json:  "version": "0.1.2"  →  "0.1.3"
.claude-plugin/marketplace.json:  同步更新对应 plugin 条目的 version
```

早期本仓库所有 plugin 的 version 保持同步（monorepo 统一升级）；随着 `anythingllm-mcp`、`web-access` 等共享 plugin 被单独维护，现策略改为"谁改 bump 谁"——见下方"开发者提醒"。

### 6. MCP server 的分发与共享

多个 plugin 不应重复内嵌同一个 MCP server 实现——否则要么各自注册名冲突、要么用 `-sm` / `-tw` 之类前缀命名 hack。本仓库采用**独立共享 plugin** 模式：

- `anythingllm-mcp` 是一个独立 plugin，`.claude-plugin/plugin.json` 注册无前缀的 `anythingllm` MCP server
- 消费方（solution-master / tender-workflow）的 `plugin.json` 不再含 `mcpServers` 字段，相应 SKILL.md 用 `mcp__anythingllm__anythingllm_search` / `mcp__anythingllm__anythingllm_list_workspaces` 调用工具
- 升级 MCP 代码只需改 `anythingllm-mcp`，不必同步修改多处
- 用户可选择不装 `anythingllm-mcp`——消费方 skill 会在工具不可用时降级为本地 YAML 索引或联网检索，不 hard-fail

### 7. 版本

各 plugin 独立 bump；marketplace 自身也有 `metadata.version`，任一 plugin bump 都要顺带 bump marketplace（见下方"开发者提醒"的"三个版本号"规则）。权威版本号**永远以 `.claude-plugin/marketplace.json` 为准**，本表只是快照——凡有分歧信任 marketplace.json。

| 组件 | 当前版本 | 说明 |
|---|---|---|
| `marketplace.metadata.version` | `0.1.14` | 客户端 `/plugin marketplace update` 的触发信号 |
| `drawio` | `0.1.10` | 共享 plugin |
| `ai-image` | `0.1.8` | 共享 plugin |
| `anythingllm-mcp` | `0.1.1` | 可选 MCP plugin |
| `web-access` | `0.1.0` | 可选共享 plugin（从 solution-master 0.1.5 抽出，首发） |
| `solution-master` | `0.1.6` | 主 plugin |
| `ppt-master` | `0.1.6` | 主 plugin |
| `tender-workflow` | `0.1.6` | 主 plugin |

> 如需程序化获取最新版本：`python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); print(d['metadata']['version']); [print(p['name'], p['version']) for p in d['plugins']]"`

---

## 开发者提醒

每次改了某个组件的代码，要在 **三个版本号** 上都 +1：

1. **组件自己的版本号**（如 `ai-image/.claude-plugin/plugin.json`）—— 告诉客户端"这个组件有新版了"
2. **商店目录里该组件的版本号**（`.claude-plugin/marketplace.json` 里那一条）—— 告诉商店"目录该更新啦"
3. **商店自己的版本号**（`.claude-plugin/marketplace.json` 的 `metadata.version`）—— 告诉客户端"商店目录有改动，来重新抓一下"

打个比方：

- **组件** = 一本书的新版
- **商店目录** = 书店的书单
- **商店版本** = 书单的修订号

书出了新版，你不光要把书本身换成新版，还得让书店在书单上把那本书标成新版本，更要告诉大家"书单我更新过了，来重新拿一份看看"。三步缺一步，客户那边就还以为是老版本，继续按老的买。

**只改了哪个组件就只 bump 那一个的版本号**，其他组件版本号不动——这样别人升级时只会拿到你改的那个，不会被误更新到别的。

### 8. 为什么只有 solution-master 注册 hook（F-055）

solution-master 是 7 个 plugin 中**唯一**注册 SessionStart hook 的（`solution-master/hooks/hooks.json`）。其他 plugin 不重复注册的设计理由：

- **单点注入避免会话启动累加延迟**：hook 配置 `async: false`（同步阻塞），多个 plugin 各自注册会让会话启动时间线性叠加。solution-master 的 hook 注入"防脱轨铁律"已经是核心需求，其他 plugin 的提示性内容用 SKILL description 承载即可
- **铁律单点维护**：使用 Solution Master 时铁律来自一处（`skills/using-solution-master/SKILL.md`）；使用 ppt-master / tender-workflow 时不需要"铁律"，依赖 Claude 路由 + SKILL description 自身的触发条件即可
- **Cursor 等编辑器跨平台兼容性**：每多一个 hook 就多一处 polyglot wrapper（参见 `solution-master/hooks/run-hook.cmd`）的维护负担，单点更稳

未来若新增主 plugin（如类似 solution-master 的复杂工作流框架）真需要 hook，建议先评估"是否能放进 SKILL.md description + 子智能体 prompt"，确认必要再注册。

---

## 开发者工具：`/plugin-review`

仓库内置了一条针对本 monorepo 量身定制的深度 review slash command（`.claude/commands/plugin-review.md`），用于在发版或重构前对**待发布的某个 plugin 或全部 plugin** 做穷尽式体检，产出 `REVIEW_FINDINGS.md` 供后续 plan 模式直接消费。**只读不写**：不会改代码、不会改 marketplace.json、不会 commit、不会 `/reload-plugins`。

### 用法

- 全量审查：直接输入 `/plugin-review`
- 聚焦某个 plugin：`/plugin-review solution-master`（元数据一致性与跨 plugin 依赖两个维度仍会跨 plugin 扫，因为这两维度本身就跨插件）

### 触发后会发生什么

1. **阶段 1 速写**（Bash/Read，串行）→ 15 行项目快照：从 `marketplace.json` 实际枚举的所有 plugin `name@version`、skill 总数、bin 清单、hook/MCP 清单、最近 commit、可疑未跟踪物
2. **阶段 2 并行 8 个 Explore agent**（单条消息并发 spawn）→ 每个维度独立深挖，主上下文只收摘要：
   - A. 元数据一致性审计（marketplace.json ↔ plugin.json ↔ README 三处版本号）
   - B. Skill frontmatter 与触发质量（description 能否被 Claude 正确识别）
   - C. Plugin runtime 陷阱（`$VAR` 不带花括号的**静默失效 bug**、bin 命名冲突、shebang）
   - D. 跨 plugin 依赖健康度（可选依赖的降级分支是否真的实现）
   - E. Bin 脚本质量（subprocess 安全、跨平台路径、密钥泄露、`_ensure_deps.py` 健壮性）
   - F. Hook 安全与稳定性（SessionStart 注入失败阻塞会话风险）
   - G. MCP server 与配置管理（`~/.config/` 多路径迁移覆盖度、密钥权限）
   - H. 发布物卫生（ppt-master 曾有 92MB bundled examples 的惨案，警惕复发）
3. **阶段 3 交叉验证** → 把 `[推断]` 用 Read/Grep 核实或降级删除，跨 agent 去重
4. **阶段 4 落盘** → 生成 `REVIEW_FINDINGS.md`（已在 `.gitignore` 中，不入库），含缺陷清单、按 plugin/维度分组索引、修复批次建议（Batch A/B/C/D）
5. **阶段 5 交接** → 6 行总结 + 建议进 plan 模式处理 Batch A

### 维护提醒

下次插件拓扑变化（新增 plugin、调整依赖、引入新 hook 或 MCP）时，记得回头更新 `.claude/commands/plugin-review.md` 里的"**项目知识底座**"章节——它是给 agent 的事实基线，过时会误导审查。
