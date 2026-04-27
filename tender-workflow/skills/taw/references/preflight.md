# taw Phase 0 Preflight 详细规则

主 SKILL.md §Phase 0 已列出顶层步骤；本文件给出每步骤的细化逻辑。当主 session 需要执行某项检测/解析的细节时按需 Read 本文件对应小节。

## 1. 搜索工具检测（MCP_TOOLS_AVAILABLE）

> **设计原则**：Claude Code 里有什么 MCP 搜索工具就用什么——**不预设 provider 名单**。priority 列表由用户在 /twc setup §4.4 用 `list-search-tools` 实时枚举后选定（写到 `mcp_search.priority`，存的是 FQN：`mcp__<server>__<tool>` 或内置 `WebSearch`）。

**步骤**：

1. 读用户配置的 priority 列表：
   ```bash
   python3 $SKILL_DIR/../twc/tools/tw_config.py get taw mcp_search.priority
   ```
   - 返回非空列表（如 `["mcp__tavily__tavily_search", "mcp__minimax__web_search"]`） → 进 step 2
   - 返回空列表 `[]` → 兜底 `["WebSearch"]`，进 step 3
   - 老 config 写的别名（`tavily_search` 等）由 `tw_config.py` 自动透明转 FQN，preflight 这里只看 FQN，不需要别名映射

2. 对 priority 里**每个 FQN** 尝试调用（测试查询 `"test"`，`max_results=1`）：
   - `mcp__<server>__<tool>` 形式 → 直接用对应 MCP 工具调（首次调时 Claude Code 会弹 permission prompt，允许后持久 ok）；成功 → 加入 `MCP_TOOLS_AVAILABLE`
   - `WebSearch` → 内置工具，永远视为可用，加入 `MCP_TOOLS_AVAILABLE`
   - 调用失败（错误 / 超时 / no tool）→ 跳过该 FQN，**不阻塞**列表里其它项

3. 记录变量供后续 phase 用：
   - `MCP_TOOL_PRIORITY`: 用户配置的 priority 列表（保留全部，包括探活失败的——便于 fallback 二次尝试时判断顺序）
   - `MCP_TOOLS_AVAILABLE`: priority 中**探活通过**的子集（按 priority 顺序保留）
   - 若 `MCP_TOOLS_AVAILABLE = []`（全部探活失败 + 无 WebSearch）→ 强制兜底 `["WebSearch"]` 并 emit 一行 warn `所有配置的 MCP 搜索工具都不可用，已兜底 WebSearch`

**策略**：检索时按 `MCP_TOOLS_AVAILABLE` 顺序使用，前一个失败试下一个，最后回 `WebSearch`。

## 2. AnythingLLM 检测

降级矩阵：

| `--kb-source` | ANYTHINGLLM_AVAILABLE=false 时行为 |
|---|---|
| `anythingllm` | 致命错误 + 提示 "/plugin install anythingllm-mcp@presales-skills 或改用 --kb-source local" |
| `auto` | 降级到 local |
| `local` | 与 AnythingLLM 状态无关 |
| `none` | 忽略 KB |

步骤：

1. 调用 `anythingllm_search(query="test")`，成功则继续；失败则 `ANYTHINGLLM_AVAILABLE=false`，跳过后续
2. `anythingllm_list_workspaces()` 取所有 workspace
3. 确定目标 workspace（优先级递减）：
   - `--anythingllm-workspace <值>`
   - 配置 `taw.anythingllm_workspace` 或 `anythingllm.workspace`
   - 环境变量 `TAW_ANYTHINGLLM_WS`
   - 列表中第一个
4. 记录 `ANYTHINGLLM_AVAILABLE=true`、`ANYTHINGLLM_WORKSPACE=<slug>`、`ANYTHINGLLM_WORKSPACE_NAME=<name>`

## 3. draw.io 检测

1. 检查工具列表是否含 `drawio` 或 `drawio_generate` → `DRAWIO_SKILL_AVAILABLE`
2. CLI 备选：`which drawio || test -f /Applications/draw.io.app/Contents/MacOS/draw.io` → `DRAWIO_CLI_AVAILABLE`
3. `DRAWIO_AVAILABLE = SKILL OR CLI`，优先 Skill
4. 失败处理：若 `DRAWIO_AVAILABLE=false` 且 `--image-source drawio`：
   - 提示安装 + 列出替代方案（`ai` / `web` / `placeholder`）
   - 自动降级 `IMAGE_SOURCE="placeholder"`，继续后续流程

## 4. `--set-kb` 与 `--build-kb-index`

### `--set-kb <路径>`

1. 验证路径存在且为目录
2. 写入配置：`python3 $SKILL_DIR/../twc/tools/tw_config.py set localkb.path <绝对路径>`
3. 提示后退出，**不执行后续 Phase**

### `--build-kb-index`

1. 确定 KB 路径：`--kb-path` > 配置 `localkb.path` > 报错退出
2. 执行索引：`python3 $SKILL_DIR/tools/kb_indexer.py --scan --kb-path <路径>`
3. 输出摘要后退出

## 5. 文件路径解析（OUTLINE_PATH / REPORT_PATH）

### 显式参数模式（`--outline` / `--report`）

- 值为文件路径（含扩展名）→ 直接使用
- 值为目录 → 列文件按 mtime 降序，取第一个对应扩展名（`.docx` 给 outline，`.md` 给 report）
- 未找到 → 报错并停止

### 简写目录模式（无 `--outline`/`--report`，仅一个目录参数）

在该目录下分别匹配最新的 `.docx`（OUTLINE）和 `.md`（REPORT），任一缺失则报错。

## 6. 关键参数解析

### --vendor

- 含 `--vendor <名>` → `VENDOR_NAME=<名>`
- 否则 → `VENDOR_NAME="灵雀云"`
- Phase 0 完成后立即把所有 `{VENDOR_NAME}` 占位符替换

### --search-tool

- `tavily` → 强制 tavily_search，失败报错不降级
- `exa` → 强制 exa_search，失败报错不降级
- `mcp` → 用任意可用 MCP（按 priority 降级）
- `websearch` → 强制 WebSearch
- `auto`（默认）→ WebSearch → MCP 工具降级

### --query

- 含 `--query <词>` → `EXTRA_QUERY=<词>`
- 否则 → 空字符串（用默认模板）

### --image-source

`local` / `drawio` / `ai` / `web` / `placeholder` / `auto`（默认）。
互斥；与 `--kb-source` 独立。

### --l{2,3,4,5}-words / --l{2,3}-images

- 设置 `WORD_OVERRIDE[N] = <字数>`（验证 N >= 100）
- 设置 `IMAGE_OVERRIDE[N] = <数量>`（验证 N >= 0）
- 否则 `WORD_OVERRIDE = {}`、`IMAGE_OVERRIDE = {}`（用模板默认）

### --kb-source 与 KB 路径解析

| `--kb-source` | KB 目录索引 | AnythingLLM | 互联网检索 |
|---|---|---|---|
| `auto` | ✅ 并行 | ✅ 并行 | ✅ 并行 |
| `local` | ✅ 强制 | ❌ 跳过 | ✅ 并行 |
| `anythingllm` | ❌ 跳过 | ✅ 强制 | ✅ 并行 |
| `none` | ❌ 跳过 | ❌ 跳过 | ✅ 仅互联网 |

`KB_PATH` 解析（`--kb-source auto/local`）：

1. `--kb <路径>` → 临时覆盖
2. 否则读 `python3 $SKILL_DIR/../twc/tools/tw_config.py get taw localkb.path`
3. 配置不存在 → 交互询问：
   ```
   未检测到知识库配置，请选择内容来源：
   1. 互联网检索（适合 KB 未建立或需要最新资料的场景）
   2. 本地知识库（需提供索引目录路径）
   ```
   - 选 1 → `NO_KB_FLAG=true`，跳过路径配置
   - 选 2 → 提示输入路径，验证后存入配置；回复"无"/"跳过" → 保存 `kb_path: none`，降级运行

## 7. `--chapter` → CHAPTERS_TO_WRITE

```
1. 含 "-" / "到" / "至"（去空格）→ 范围模式
   提取起止节点 → 在完整扁平序列中定位 idx → 切片 [start, end]（含两端）
   边界异常（不在序列 / start > end）→ 报错并停止

2. "all" → 大纲所有小节

3. 主章名（一/1）→ 该章子节列表

4. 具体小节号（如 "1.3"）→ ["1.3"]
```

示例：`"1.1到1.9"` → `[1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]`（共 9 节）

## 8. 输出目录与配置文件路径

- 输出目录：`./drafts/`（自动 `mkdir -p`）
- 配置文件：`~/.config/tender-workflow/config.yaml`，taw / taa 共用
- 解析优先级：`--kb` > 配置 `localkb.path` > 首次运行引导
