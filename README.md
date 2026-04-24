# presales-skills — 售前工作流 Claude Code plugin 集

一个 umbrella marketplace，把售前场景下的 AI 辅助工作流按职责拆成 6 个独立的 Claude Code plugin，通过同一个 marketplace 统一分发。

## 包含的 6 个 plugin

| plugin | 类型 | 用途 |
|---|---|---|
| **solution-master** | 主 plugin | 通用解决方案撰写框架：苏格拉底式需求提取、子智能体驱动撰写、双重审查、多源知识检索、上下文感知配图、Markdown/DOCX 输出 |
| **ppt-master** | 主 plugin | 从 PDF / DOCX / URL / Markdown 等多源文档生成原生可编辑 PPTX（SVG 流水线） |
| **tender-workflow** | 主 plugin | 四角色招投标工作流：`tpl`（招标策划）/ `taa`（招标分析）/ `taw`（标书撰稿）/ `trv`（审核）+ `twc`（配置） |
| **drawio** | 共享 plugin | Draw.io 图表生成（`.drawio` XML + PNG/SVG/PDF 导出）。被 solution-master / tender-workflow 依赖 |
| **ai-image** | 共享 plugin | 统一 AI 图片生成：13 个后端（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter）+ 共享 YAML 模型注册表 + `/ai-image-config-*` 配置管理。被三个主 plugin 依赖 |
| **anythingllm-mcp** | 共享 plugin | AnythingLLM MCP server：知识库语义搜索 + workspace 列举。被 solution-master / tender-workflow 可选依赖；不装则降级为本地 YAML 索引或联网检索 |

---

## 安装

### Step 1：注册 marketplace

在 Claude Code 会话里执行：

```
/plugin marketplace add Alauda-io/presales-skills
```

（也支持本地路径：`/plugin marketplace add /path/to/presales-skills`）

### Step 2：装齐 6 个 plugin

**依赖顺序**：先装共享 plugin（drawio / ai-image / anythingllm-mcp），再装主 plugin——否则主 plugin 会因为找不到依赖而运行失败（anythingllm-mcp 是可选依赖，不装也能降级，但装了更好）。

```
/plugin install drawio@presales-skills
/plugin install ai-image@presales-skills
/plugin install anythingllm-mcp@presales-skills
/plugin install solution-master@presales-skills
/plugin install ppt-master@presales-skills
/plugin install tender-workflow@presales-skills
```

### Step 3：让 hook / MCP / PATH 生效

```
/reload-plugins
```

预期 reload 输出：`6 plugins · XX skills · 8 agents · 1 hook · 1 plugin MCP server`（数量含本 marketplace 的 6 个 plugin；若还装了其他 marketplace 的 plugin 或 baseline，总数会更多）
- 1 hook：solution-master 的 SessionStart 铁律注入
- MCP：`anythingllm`（由 anythingllm-mcp plugin 统一注册，solution-master 和 tender-workflow 共用；若未装 anythingllm-mcp 则无此 server）

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
│   └── marketplace.json                   # 声明 6 个 plugin 的入口
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
│   └── skills/                            # 12 个 skill
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
│       ├── writing-skills/
│       └── web-access/
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

本 marketplace 里三个主 plugin 都依赖共享 plugin（drawio / ai-image）。跨 plugin 调用通过 **`bin/` + PATH** 机制实现，不走相对路径：

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

本仓库所有 5 个 plugin 的 version 保持同步（monorepo 统一升级）。

### 6. MCP server 的分发与共享

多个 plugin 不应重复内嵌同一个 MCP server 实现——否则要么各自注册名冲突、要么用 `-sm` / `-tw` 之类前缀命名 hack。本仓库采用**独立共享 plugin** 模式：

- `anythingllm-mcp` 是一个独立 plugin，`.claude-plugin/plugin.json` 注册无前缀的 `anythingllm` MCP server
- 消费方（solution-master / tender-workflow）的 `plugin.json` 不再含 `mcpServers` 字段，相应 SKILL.md 用 `mcp__anythingllm__anythingllm_search` / `mcp__anythingllm__anythingllm_list_workspaces` 调用工具
- 升级 MCP 代码只需改 `anythingllm-mcp`，不必同步修改多处
- 用户可选择不装 `anythingllm-mcp`——消费方 skill 会在工具不可用时降级为本地 YAML 索引或联网检索，不 hard-fail

### 7. 版本

当前版本：**v0.1.5**（5 个主/核心 plugin 同步至 0.1.5；`anythingllm-mcp` 首发 v0.1.0）
