---
name: twc
description: >
  当用户说"配置工作流"、"配置 tender"、"设置配置"时触发。
  管理 tender-workflow 统一配置文件（~/.config/tender-workflow/config.yaml）。
  支持交互式初始配置（setup）、查看（show）、修改（set）、验证（validate）、旧配置迁移（migrate）、重置（reset）等子命令。
  AI 生图相关配置（API keys / 模型）由 ai-image plugin 管理。
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob
---

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析（替代 `$SKILL_DIR`）。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

## 路径自定位

**首次调用本 skill 的脚本/工具前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/tools/...`、`$SKILL_DIR/prompts/...`、`$SKILL_DIR/templates/...`）：

```bash
SKILL_DIR=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/tender-workflow/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/twc'); sys.exit(0)
" 2>/dev/null)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/tender-workflow/skills/twc" ] && SKILL_DIR="$d/tender-workflow/skills/twc" && break
    [ -d "$d/twc" ] && SKILL_DIR="$d/twc" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${TENDER_WORKFLOW_PLUGIN_PATH:-}" ] && SKILL_DIR="$TENDER_WORKFLOW_PLUGIN_PATH/skills/twc"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./tender-workflow/skills/twc" ] && SKILL_DIR="$(pwd)/tender-workflow/skills/twc"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 tender-workflow / twc skill 安装位置。" >&2
    echo "请设置：export TENDER_WORKFLOW_PLUGIN_PATH=/path/to/tender-workflow" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install tender-workflow@presales-skills` 或手工 export 环境变量。


# twc — Tender Workflow 配置管理

当用户说"配置工作流"、"配置 tender"、"设置配置"时触发。
管理 tender-workflow 统一配置文件（`~/.config/tender-workflow/config.yaml`）。
支持交互式初始配置、查看、设置、验证、旧配置迁移。

## 参数

```
/twc [子命令] [参数]

子命令（默认 setup）：
  setup              交互式首次配置向导（仅 tender-workflow 专属项）
  show [skill]       显示当前生效配置（可选指定 skill: taa/taw/tpl/trv）
  set <key> <value>  设置配置项（支持 dot notation，如 localkb.path）
  models [provider]  列出 AI 生图模型（转发至 ai-image plugin 的 ai_image_config.py models）
  validate           健康检查（路径、API 连通性、工具安装）
  migrate            迁移旧 per-skill 配置（taw/taa）到统一 config
  reset              重置为默认值（确认后删除配置文件）
```

## 配置文件

**唯一路径**：`~/.config/tender-workflow/config.yaml`

旧路径 `~/.config/taw/config.yaml` 和 `~/.config/taa/config.yaml` 已废弃。
使用 `/twc migrate` 可将旧配置合并到统一文件并删除旧文件。

**完整 Schema**（api_keys / ai_image 由 ai-image plugin 持有，详见 `~/.config/presales-skills/config.yaml`）：
```yaml
# 全局共享
localkb:
  path: /path/to/local-knowledgebase  # 知识库根目录

anythingllm:
  enabled: true/false
  base_url: "http://localhost:3001"
  workspace: <slug-or-uuid>           # 全局默认 workspace

mcp_search:
  priority: [tavily_search, exa_search]

drawio:
  cli_path: /Applications/draw.io.app/Contents/MacOS/draw.io

# Skill 专属覆盖
taa:
  vendor: 灵雀云
  kb_source: auto
  anythingllm_workspace: null          # null = 用全局值

taw:
  kb_source: auto
  image_source: auto
  anythingllm_workspace: null

tpl:
  default_template: null
  default_level: standard

trv:
  default_level: all
```

**配置解析优先级**：CLI 参数 > 环境变量 > 统一配置(skill 节) > 统一配置(全局节) > 默认值

## 工具定义

配置读写通过 `skills/twc/tools/tw_config.py` 执行：
```bash
python3 $SKILL_DIR/tools/tw_config.py show [skill]          # 显示配置
python3 $SKILL_DIR/tools/tw_config.py get <skill> <key>     # 获取单个值
python3 $SKILL_DIR/tools/tw_config.py set <key> <value>     # 设置值
python3 $SKILL_DIR/tools/tw_config.py models [provider]     # 列出 AI 生图模型
python3 $SKILL_DIR/tools/tw_config.py validate              # 验证
python3 $SKILL_DIR/tools/tw_config.py migrate               # 迁移旧配置
python3 $SKILL_DIR/tools/tw_config.py normalize             # 规范化 schema
```

## 执行流程

### /twc show [skill]

1. 执行 `python3 $SKILL_DIR/tools/tw_config.py show [skill]`
2. 将输出格式化为表格展示给用户

### /twc set \<key\> \<value\>

1. 执行 `python3 $SKILL_DIR/tools/tw_config.py set <key> <value>`
2. 显示变更确认

### /twc models [provider] / --refresh

转发到 ai-image plugin 的统一模型注册表入口：

```bash
python3 $SKILL_DIR/tools/tw_config.py models [provider | --refresh]
```

`tw_config.py` 内部会调用 `ai-image-config models …`，由 ai-image plugin 提供注册表渲染与联网刷新逻辑。请确保 ai-image plugin 已安装（`/plugin install ai-image@presales-skills`）。

### /twc validate

1. 执行 `python3 $SKILL_DIR/tools/tw_config.py validate`
2. 对每个问题给出修复建议

### /twc migrate

1. 检查旧配置文件是否存在：
   - `~/.config/taw/config.yaml`
   - `~/.config/taa/config.yaml`
2. 执行 `python3 $SKILL_DIR/tools/tw_config.py migrate`
3. 显示迁移结果（哪些 key 被迁移、哪些文件被删除）

### /twc reset

1. 确认用户意图（二次确认）
2. 删除 `~/.config/tender-workflow/config.yaml`
3. 清理 setup 写入的 `~/.claude.json` MCP Server 条目（anythingllm / tavily / exa）：
   ```python
   python3 -c "
   import json
   from pathlib import Path
   p = Path.home() / '.claude.json'
   if not p.exists(): exit()
   try: c = json.loads(p.read_text())
   except (json.JSONDecodeError, ValueError): print('~/.claude.json 格式异常，跳过清理'); exit()
   servers = c.setdefault('mcpServers', {})
   removed = [k for k in ['anythingllm', 'tavily', 'exa'] if k in servers]
   for k in removed: del servers[k]
   if removed:
       p.write_text(json.dumps(c, indent=2, ensure_ascii=False))
       print('已从 ~/.claude.json 移除 MCP Server: ' + ', '.join(removed))
   else:
       print('~/.claude.json 中无需清理的 MCP Server')
   "
   ```
4. 提示运行 `/twc setup` 重新配置
5. 若步骤 3 移除了 MCP Server → 提示**重启 Claude Code** 以卸载

## 配置

完整 setup wizard 见同目录 [`setup.md`](setup.md)。**当用户说「配置工作流 / 配置 tender / 配置 tender-workflow / 设置配置 / setup tender」时**：

1. 用 Read 工具加载 `$SKILL_DIR/setup.md`（路径 `$SKILL_DIR` 由 §路径自定位 段解析）
2. 严格按 setup.md 引导用户完成配置（含 Python 依赖前置 + 6 步专属字段配置）
3. 不要凭记忆执行 — 每次都 Read 当前版本
