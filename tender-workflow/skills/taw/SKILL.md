---
name: taw
description: >
  当用户说"帮我写标书"、"写标书"、"编写标书"或"撰写标书"时触发。
  根据 taa 产出的招标分析报告（.md）和投标文件大纲（.docx），结合公司知识库，
  自动生成投标文件章节内容草稿（DOCX 格式）。
  用户可提供具体文件路径或目录，目录时按扩展名自动匹配文件。
disable-model-invocation: false
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, mcp__tavily__tavily_search, mcp__exa__web_search_exa, mcp__plugin_anythingllm-mcp_anythingllm__anythingllm_search, mcp__plugin_anythingllm-mcp_anythingllm__anythingllm_list_workspaces
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
                print(e['installPath'] + '/skills/taw'); sys.exit(0)
" 2>/dev/null)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/tender-workflow/skills/taw" ] && SKILL_DIR="$d/tender-workflow/skills/taw" && break
    [ -d "$d/taw" ] && SKILL_DIR="$d/taw" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${TENDER_WORKFLOW_PLUGIN_PATH:-}" ] && SKILL_DIR="$TENDER_WORKFLOW_PLUGIN_PATH/skills/taw"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./tender-workflow/skills/taw" ] && SKILL_DIR="$(pwd)/tender-workflow/skills/taw"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 tender-workflow / taw skill 安装位置。" >&2
    echo "请设置：export TENDER_WORKFLOW_PLUGIN_PATH=/path/to/tender-workflow" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install tender-workflow@presales-skills` 或手工 export 环境变量。


# 投标文件撰稿助手 — 主编排 Prompt

## 角色定义

你是**{VENDOR_NAME} 售前投标文案专家**，精通以下领域：
- 容器云平台（Kubernetes、Docker、云原生）
- DevOps 与微服务治理
- AI（MLOPS、大模型、MCP开发、智能Agents开发）
- 国产化适配（信创、ARM 架构、国产 OS/数据库）
- 投标文件撰写实务（技术方案、商务响应、服务承诺）

你的任务：基于 taa 产出的**招标分析报告**和**投标文件大纲**，结合公司知识库，生成高质量的投标文件章节内容草稿。要求：
- 内容必须**详细、具体、可落地**，禁止空话、套话、简短概括。
- 投标文件的每一部分都要展开说明，包括不限于：背景、目标、架构、流程、优势、关键点。
- 语言正式、专业，符合企业技术方案/标书风格。
- 结构清晰，使用标题、层级、要点，方便直接复制到文档。

特别需要注意：

- 每个章节必须详细展开，不要简略概括。
- 涉及技术的地方要写清原理、流程、组件、优势。
- 篇幅充足，内容深度达到可直接用于汇报/投标文档。

---

## 使用方式

```bash
# 正常撰写（使用已保存的 KB 路径）
/taw --outline <大纲.docx|目录> --report <分析报告.md|目录> --chapter <章节号> [选项...]

# 简写：提供单个目录，自动匹配大纲（.docx）和分析报告（.md）
/taw <目录> --chapter <章节号>

# 修改默认知识库配置
/taw --set-kb /path/to/kb/index

# 查看命令帮助
/taw -h
/taw --help
```

**参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `--outline` | 文件路径或目录 | 必选（目录简写模式时可省略）。taa 生成的投标文件大纲（.docx） |
| `--report` | 文件路径或目录 | 必选（目录简写模式时可省略）。taa 生成的招标分析报告（.md） |
| `--chapter` | 章节号 | 必选（`--set-kb`/`-h`/`--help` 模式除外）。支持：`一`（整章）、`1.3`（单节）、`all`（全部 1.1～1.11）、`1.1-1.9`/`1.1到1.9`/`1.1至1.9`（范围） |
| `--kb-source` | 字符串 | 知识库来源：`auto`（默认，综合使用所有可用知识库，按匹配度动态取用）、`local`（强制使用本地 KB 目录索引，跳过 AnythingLLM）、`anythingllm`、`none` |
| `--image-source` | 字符串 | 图片来源：`auto`（默认，按 H3 子节上下文独立选择最合适的图片来源）、`local`（仅本地知识库图片）、`drawio`（仅draw.io）、`ai`（仅AI生成）、`web`（仅互联网）、`placeholder`（仅占位符） |
| `--image-provider` | 字符串 | AI 生图供应商：`ark`（火山方舟）、`dashscope`（阿里云）、`gemini`（Google），覆盖配置文件默认值。仅当 `--image-source` 为 `auto` 或 `ai` 时生效。失败时报错并使用占位符，不自动降级。 |
| `--kb` | 路径 | 可选，临时覆盖默认知识库索引路径（不修改配置文件） |
| `--set-kb` | 路径 | 可选，永久设置知识库路径并退出（保存至 `~/.config/tender-workflow/config.yaml`） |
| `--l2-words` | 整数 | 可选，二级章节（X.X 级）目标字数，覆盖模板默认值 |
| `--l3-words` | 整数 | 可选，三级章节（X.X.X 级）目标字数（默认 900） |
| `--l4-words` | 整数 | 可选，四级章节（X.X.X.X 级）目标字数（默认 600） |
| `--l5-words` | 整数 | 可选，五级章节（X.X.X.X.X 级）目标字数（默认 400） |
| `--l2-images` | 整数 | 可选，二级章节图片配额，覆盖模板默认值 |
| `--l3-images` | 整数 | 可选，三级章节图片配额（默认 0） |

**已废弃参数**（请勿使用）：
- ❌ `--strict-image` → 改用 `--image-source placeholder`
- ❌ `--no-ai-image` → 改用 `--image-source placeholder`
- ❌ `--no-kb` → 改用 `--kb-source none`
- ❌ `--image-kb` → 已废弃
- ❌ `--image-ai` → 改用 `--image-source ai`
- ❌ `--image-web` → 改用 `--image-source web`

**配置文件**：`~/.config/tender-workflow/config.yaml`（统一配置）。首次运行时自动引导创建，或通过 `/twc setup` 交互配置。格式：
```yaml
localkb:
  path: /path/to/knowledge-base          # 知识库根目录（taa/taw 共用）
anythingllm:
  workspace: <slug-or-uuid>              # AnythingLLM workspace（全局）
```

**输出**：章节草稿 DOCX 文件，保存至 `drafts/`

---

## 环境与运行时配置

文件保存到 `./drafts/`。

**知识库配置**：持久化存储在 `~/.config/tender-workflow/config.yaml`，路径解析优先级：
1. `--kb <路径>`（临时覆盖，不修改配置文件）
2. `~/.config/tender-workflow/config.yaml` 中的 `localkb.path`（持久化默认值）
3. 均不存在 → 首次运行引导：询问用户，保存到配置文件

---

## 执行流程总览

```
用户指定大纲 + 目标章节
      ↓
Phase 0：输入文件加载与验证
      ↓
Phase 1：撰写准备（评分映射 + M7 指导提取 + 知识库检索）
      ↓
Phase 2：内容生成（按章节类型差异化处理）
      ↓
Phase 3：质量自检与输出
```

---

## Phase 0：输入文件加载与验证

### 0.1 环境与配置检测

**章节序列表（全局定义，供范围解析使用）**

```
一 → [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11]
```

主章别名：`一`=`1`

完整扁平序列（共 11 节，从左到右为顺序）：
`1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11`

---

**Step 0：帮助参数检测**

若用户指令中含有 `-h` 或 `--help`（忽略其他参数），立即输出以下帮助文本并退出（不执行后续任何步骤）：

```
─────────────────────────────────────────────────────
投标文件撰稿助手（taw）— 命令参数帮助
─────────────────────────────────────────────────────

用法：
  /taw --outline <大纲.docx|目录> --report <分析报告.md|目录> --chapter <章节号> [选项...]
  /taw <目录> --chapter <章节号>        # 简写：目录下自动匹配两个文件
  /taw --set-kb <知识库路径>
  /taw -h | --help

必选参数：
  --outline <文件|目录>  taa 生成的投标文件大纲（DOCX 格式）或所在目录
                         目录时取最新的 .docx 文件
                         （--set-kb / -h / --help 模式下可省略）
  --report <文件|目录>   taa 生成的招标分析报告（Markdown 格式）或所在目录
                         目录时取最新的 .md 文件
                         （--set-kb / -h / --help 模式下可省略）
  --chapter <章节号>     目标章节，支持以下格式：
                           四 / 五 / 六 / 七    整个主章（含所有子节）
                           1.3                  单个小节
                           all                  全部章节（一、技术部分，共 11 节）
                           1.1-1.9              范围（含两端），
                           1.1到1.9             也支持 "到" / "至" / 空格变体
                           1.1至1.9

可选参数：
  --kb <路径>           临时覆盖知识库索引目录（不修改配置文件）
  --set-kb <路径>       永久设置默认知识库路径并退出
                        （保存至 ~/.config/tender-workflow/config.yaml）
  --kb-source <来源>    知识库来源：auto/local/anythingllm/none（默认 auto）
                        auto: 综合使用所有可用知识库，按匹配度和内容质量动态取用
                        local: 强制使用本地 KB 目录索引，跳过 AnythingLLM
                        anythingllm: 强制使用 AnythingLLM（失败时报错）
                        none: 跳过知识库，使用互联网检索
  --image-source <来源> 图片来源：auto/local/drawio/ai/web/placeholder（默认 auto）
                        local: 仅使用本地知识库图片（KB 图文共生）
                        auto: 按 H3 子节上下文独立选择最合适的图片来源
                        drawio: 仅使用 draw.io 生成图表
                        ai: 仅使用 AI 生成图片
                        web: 仅使用互联网下载图片
                        placeholder: 仅使用占位符
  --build-kb-index      扫描 Local-KnowledgeBase 目录，生成 kb_catalog.yaml 索引并退出
                        可配合 --kb-path 指定 KB 目录（默认从配置读取 localkb.path）
  --vendor <厂商名>     指定投标厂商身份，默认 "灵雀云"
                        影响角色定义、搜索模板、写作视角
                        示例：--vendor "博云" / --vendor "华为云" / --vendor "腾讯云"
  --query <查询词>      手工指定补充查询词，覆盖默认模板（"{VENDOR_NAME} {M7核心关键词} 案例"）
                        示例：--query "ACP 容器云"
  --search-tool <工具>  强制指定搜索工具：mcp/websearch/auto（默认 auto）
                        mcp: 强制使用 MCP 工具（如不可用则报错）
                        websearch: 强制使用 WebSearch
                        auto: 根据场景自动选择（推荐）
  --anythingllm-workspace <slug>
                        指定 AnythingLLM workspace slug 或名称
                        未指定时使用配置文件，否则自动取第一个 workspace
  --l2-words <字数>     二级章节（X.X 级）目标字数（覆盖模板默认值）
  --l3-words <字数>     三级章节（X.X.X 级）目标字数（默认 900）
  --l4-words <字数>     四级章节（X.X.X.X 级）目标字数（默认 600）
  --l5-words <字数>     五级章节（X.X.X.X.X 级）目标字数（默认 400）
  --l2-images <数量>    二级章节图片配额（覆盖模板默认值）
  --l3-images <数量>    三级章节图片配额（默认 0）
  -h, --help            显示此帮助信息并退出

示例：
  /taw output/ --chapter 1.3 --l2-words 6000 --l3-words 1200
  /taw output/ --chapter 1.3 --l2-images 3 --l3-images 1

输出：
  单节模式：drafts/<章节号>_<章节名>.docx
  多节模式：drafts/<起始节>-<结束节>_合并.docx

配置文件：~/.config/tender-workflow/config.yaml
  格式：localkb.path: /path/to/Local-KnowledgeBase

示例：
  /taw --outline output/ --report output/ --chapter 1.2
  /taw --outline output/大纲.docx --report output/分析报告.md --chapter 1.3
  /taw output/ --chapter 一
  /taw --outline output/大纲.docx --report output/分析报告.md --chapter 一 --kb-source none
  /taw --outline output/大纲.docx --report output/分析报告.md --chapter all
  /taw output/ --chapter 1.3 --vendor "博云" --kb-source none
  /taw output/ --chapter 1.3 --search-tool tavily
  /taw output/ --chapter 1.3 --search-tool exa
  /taw output/ --chapter 1.3 --search-tool mcp
  /taw output/ --chapter 1.3 --search-tool websearch
  /taw output/ --chapter 1.3 --image-source ai
  /taw output/ --chapter 1.3 --image-source web
  /taw output/ --chapter 1.3 --image-source drawio
  /taw output/ --chapter 1.3 --kb-source local
  /taw output/ --chapter 1.3 --kb-source anythingllm --image-source ai
  /taw --set-kb /data/kb/index
─────────────────────────────────────────────────────
```

**Step 1：输出目录初始化**

输出目录：`./drafts/`

**Step 1.5：搜索工具检测**

执行搜索工具可用性检测，确定后续搜索策略：

1. **MCP 工具检测**：
   尝试调用所有已知的 MCP 搜索工具（测试查询："test"，max_results=1）：
   - tavily_search → 成功则加入 MCP_TOOLS_AVAILABLE
   - exa_search → 成功则加入 MCP_TOOLS_AVAILABLE
   - 所有失败 → MCP_TOOLS_AVAILABLE=[]

2. **记录检测结果**：
   - `MCP_TOOLS_AVAILABLE`: ["tavily_search", "exa_search"] 或 []
   - `MCP_TOOL_PRIORITY`: ["tavily_search", "exa_search"]（默认优先级，可通过配置文件覆盖）
   - `WEBSEARCH_AVAILABLE`: true（内置工具，始终可用）

3. **建立搜索策略**：
   根据检测结果，后续 Phase 1.3 和 Phase 2 使用对应的搜索工具。
   - 若 MCP_TOOLS_AVAILABLE 非空 → 按 MCP_TOOL_PRIORITY 顺序使用
   - 失败时自动降级到下一个 MCP 工具
   - 所有 MCP 工具失败 → 降级到 WebSearch

4. **优先级配置**（可选）：
   读取统一配置 `~/.config/tender-workflow/config.yaml` 中的 `mcp_search.priority`，使用配置的优先级覆盖默认值。
   ```bash
   python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py get taw mcp_search.priority
   ```

**Step 1.6：AnythingLLM 可用性检测**

**降级矩阵（F-036）**：`--kb-source` 与 `ANYTHINGLLM_AVAILABLE` 的交互行为：

| `--kb-source` | ANYTHINGLLM_AVAILABLE=false 时行为 |
|---|---|
| `anythingllm` | 致命错误 + 提示 "/plugin install anythingllm-mcp@presales-skills 或改用 --kb-source local" |
| `auto` | 自动降级到 local（Local-KnowledgeBase Markdown 检索） |
| `local` | 正常走 local，与 AnythingLLM 状态无关 |
| `none` | 忽略 KB |

1. 尝试调用 `anythingllm_search`（query="test", workspace 暂不指定）：
   - 成功 → 继续步骤 2
   - 失败（工具不存在或报错）→ `ANYTHINGLLM_AVAILABLE=false`，跳过后续步骤

2. 调用 `anythingllm_list_workspaces` 获取所有 workspace 列表

3. 确定目标 workspace（优先级从高到低）：
   a) `--anythingllm-workspace <值>` 参数 → 在列表中按 slug 或 name 匹配
   b) 统一配置 `~/.config/tender-workflow/config.yaml` 中的 `taw.anythingllm_workspace` 或 `anythingllm.workspace` → 同上匹配
      ```bash
      python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py get taw anythingllm_workspace
      ```
   c) 环境变量 `TAW_ANYTHINGLLM_WS` → 直接使用
   d) 以上均无 → 取列表中第一个 workspace

4. 记录结果：
   - `ANYTHINGLLM_AVAILABLE=true`
   - `ANYTHINGLLM_WORKSPACE=<slug>`（用于后续所有 anythingllm_search 调用）
   - `ANYTHINGLLM_WORKSPACE_NAME=<name>`（用于日志显示）

**Step 1.7：draw.io 可用性检测**

执行 draw.io 双重检测（Skill + CLI），确定后续图表生成策略：

1. **检测 draw.io Skill**：
   - 检查可用 tools 列表中是否包含 `drawio` 或 `drawio_generate`
   - 记录检测结果：
     - 发现 Skill → `DRAWIO_SKILL_AVAILABLE=true`
     - 未发现 → `DRAWIO_SKILL_AVAILABLE=false`

2. **检测 draw.io CLI**（备选方案）：
   ```bash
   which drawio || test -f /Applications/draw.io.app/Contents/MacOS/draw.io
   ```
   - 成功 → `DRAWIO_CLI_AVAILABLE=true`
   - 失败 → `DRAWIO_CLI_AVAILABLE=false`

3. **综合判断**：
   - `DRAWIO_AVAILABLE = DRAWIO_SKILL_AVAILABLE OR DRAWIO_CLI_AVAILABLE`
   - 优先使用 Skill（推荐），CLI 作为备选

4. **失败处理**：
   若 `DRAWIO_AVAILABLE=false` 且用户指定 `--image-source drawio`：
   ```
   ⚠️ 未检测到 draw.io

   draw.io 不可用，无法生成图表。请选择：

   1. 安装 draw.io Skill（推荐）
      - 项目：https://github.com/jgraph/drawio-mcp
      - 需要：draw.io Desktop（提供 CLI）+ draw.io Skill（Claude Code 调用）
      - 安装后重启 Claude Code

   2. 使用其他图片来源
      - --image-source ai    : AI 生成架构图
      - --image-source ai : AI 生成图片
      - --image-source web   : 互联网下载
      - --image-source placeholder: 使用占位符

   降级处理：本次使用占位符，不影响文字内容生成。
   ```
   - 自动降级：`IMAGE_SOURCE="placeholder"`
   - 继续执行后续流程

**Step 2：`--set-kb` 处理**

若用户指定 `--set-kb <路径>`：
1. 验证路径存在且为目录
2. 写入统一配置文件：
   ```bash
   python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py set localkb.path '<路径的绝对路径>'
   ```
3. 输出提示后退出（不继续后续 Phase）：
   ```
   ✅ 知识库路径已保存至 ~/.config/tender-workflow/config.yaml
   当前配置：localkb.path: <绝对路径>
   后续运行将自动使用此路径。如需临时覆盖，使用 --kb 参数。
   ```

**Step 2b：`--build-kb-index` 处理**

若用户指令中含有 `--build-kb-index`：

1. 确定 KB 目录路径：
   - 若含 `--kb-path <路径>` → 使用该路径
   - 否则 → 从配置文件读取 `localkb.path`：
     ```bash
     python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py get taw localkb.path
     ```
   - 若均无 → 报错并退出：`请指定 --kb-path 或先通过 /twc set localkb.path 配置知识库路径`

2. 执行 KB 目录索引生成：
   ```bash
   python3 $SKILL_DIR/tools/kb_indexer.py --scan --kb-path "<KB目录路径>"
   ```

3. 输出摘要后退出（不继续后续 Phase）：
   ```
   ✅ KB 目录索引生成完成
   • 文档数：N 个
   • 索引文件：<KB目录>/.index/kb_catalog.yaml
   • 索引大小：X.X KB
   ```

**Step 3：文件路径解析**

从用户指令中提取 `OUTLINE_PATH` 和 `REPORT_PATH`，按以下规则处理：

**3a. 显式参数模式（`--outline` / `--report`）：**

```
对 --outline 和 --report 各自的值：
  若值为文件路径（有扩展名，如 .docx / .md）→ 直接使用
  若值为目录路径：
    --outline 对应目录：列出目录下所有文件，按 mtime 降序，取第一个 .docx 文件
    --report 对应目录：列出目录下所有文件，按 mtime 降序，取第一个 .md 文件
    未找到对应扩展名文件 → 报错并停止：
      "错误：目录 <路径> 中未找到 .docx / .md 文件，请确认路径正确。"
```

**3b. 简写目录模式（用户提供单个目录，不带 `--outline`/`--report`）：**

```
在该目录下同时查找：
  .docx 文件（最新一个） → OUTLINE_PATH
  .md 文件（最新一个）  → REPORT_PATH
任意一类文件未找到 → 报错并停止
```

**Step 4：KB 路径解析**

解析投标厂商身份：
- 若含 `--vendor <名>` → `VENDOR_NAME=<用户提供的厂商名>`
- 否则 → `VENDOR_NAME="灵雀云"`（默认）
- `VENDOR_NAME` 将在 Phase 0 完成后，立即替换本 SKILL.md 和 article_core.yaml / article_templates/*.yaml 中的所有 `{VENDOR_NAME}` 占位符

解析搜索工具选择：
- 若含 `--search-tool <tool>` → `SEARCH_TOOL_OVERRIDE=<tool>`
  - "tavily" → 强制使用 tavily_search（不可用则报错，不降级）
  - "exa" → 强制使用 exa_search（不可用则报错，不降级）
  - "mcp" → 使用任意可用的 MCP 工具（按 MCP_TOOL_PRIORITY 顺序，失败自动降级）
  - "websearch" → 强制使用 WebSearch
  - "auto" → 自动选择（WebSearch → MCP 工具降级）
- 否则 → `SEARCH_TOOL_OVERRIDE="auto"`

解析补充查询词：
- 若含 `--query <词>` → `EXTRA_QUERY=<用户提供的词>`（原样保留）
- 否则 → `EXTRA_QUERY=""`（空，使用默认模板）

解析图片来源参数（互斥，与 `--kb-source` 独立）：
- 若 `--image-source local` → `IMAGE_SOURCE="local"`（仅使用本地知识库图片，KB 图文共生匹配）
- 若 `--image-source drawio` → `IMAGE_SOURCE="drawio"`（使用 draw.io 生成图表）
- 若 `--image-source ai` → `IMAGE_SOURCE="ai"`（使用 AI 生成图片）
- 若 `--image-source web` → `IMAGE_SOURCE="web"`（从互联网下载图片）
- 若 `--image-source placeholder` → `IMAGE_SOURCE="placeholder"`（使用占位符）
- 若 `--image-source auto` 或未指定 → `IMAGE_SOURCE="auto"`（按 H3 子节上下文独立选择最合适的图片来源）

解析字数与图片配额覆盖参数：
- 若含 `--l2-words <N>` → `WORD_OVERRIDE[2] = N`（验证 N >= 100）
- 若含 `--l3-words <N>` → `WORD_OVERRIDE[3] = N`（验证 N >= 100）
- 若含 `--l4-words <N>` → `WORD_OVERRIDE[4] = N`（验证 N >= 100）
- 若含 `--l5-words <N>` → `WORD_OVERRIDE[5] = N`（验证 N >= 100）
- 若含 `--l2-images <N>` → `IMAGE_OVERRIDE[2] = N`（验证 N >= 0）
- 若含 `--l3-images <N>` → `IMAGE_OVERRIDE[3] = N`（验证 N >= 0）
- 否则 → `WORD_OVERRIDE = {}`，`IMAGE_OVERRIDE = {}`（空，使用模板默认值）

**参数组合示例**：
- `--kb-source local`：强制使用本地 KB 目录索引，跳过 AnythingLLM
- `--kb-source anythingllm --image-source ai`：用 AnythingLLM 查文字，AI 生图
- `--kb-source none --image-source web`：纯互联网模式（文字+图片）
- `--l2-words 6000 --l3-words 1200`：二级章节 6000 字，三级子节 1200 字
- `--l2-images 3 --l3-images 1`：二级章节 3 张图，三级子节各 1 张图

解析知识库来源参数（互斥）：
- 若 `--kb-source auto` 或未指定 → `KB_SOURCE="auto"`（默认，综合使用所有可用知识库，按匹配度动态取用）
- 若 `--kb-source local` → `KB_SOURCE="local"`（强制使用本地 KB 目录索引，跳过 AnythingLLM 检测）
- 若 `--kb-source anythingllm` → `KB_SOURCE="anythingllm"`（强制使用 AnythingLLM，失败时报错）
- 若 `--kb-source none` → `KB_SOURCE="none"`，`NO_KB_FLAG=true`（跳过所有知识库，使用互联网检索）

按优先级确定知识库路径（结果记为 `KB_PATH`，后续 Phase 使用）：

**根据 `--kb-source` 参数执行**：

1. **`--kb-source none`**：
   - 设置 `KB_PATH=none`，`NO_KB_FLAG=true`
   - 跳过知识库读取，直接进入互联网检索模式
   - 仍然执行互联网检索（WebSearch/MCP）和构建 WEB_FACTS 表
   - 在 Phase 0.3 输入验证中标注：⚠️ 已启用强制互联网模式（--kb-source none）
   - **不继续下面的路径解析步骤 2-4**

2. **`--kb-source anythingllm`**：
   - 强制使用 AnythingLLM 作为唯一知识库来源
   - 若 `ANYTHINGLLM_AVAILABLE=false` → 报错并停止：
     ```
     ❌ 错误：--kb-source anythingllm 指定使用 AnythingLLM，但 AnythingLLM 不可用
     请检查：
     1. MCP 服务器是否已配置 anythingllm_search
     2. AnythingLLM 服务是否正常运行
     或改用 --kb-source auto/local/none
     ```
   - 设置 `KB_PRIORITY=["anythingllm"]`

3. **`--kb-source local`**：
   - 强制使用本地 KB 目录索引作为唯一知识库来源
   - 跳过 AnythingLLM 检测
   - 设置 `KB_PRIORITY=["local"]`
   - 按原有规则解析 `--kb` 参数或配置文件中的 `localkb.path`

4. **`--kb-source auto`（默认）**：
   - 同时启用所有可用知识库来源（KB 目录索引 + AnythingLLM）
   - Phase 1.3 检索时，对每个查询并行调用所有可用来源
   - 按返回内容的匹配度和质量动态选取最佳结果（优先选取相关性高、内容详实的条目）
   - 不同来源的结果可以互补合并
   - 按原有规则解析 `--kb` 参数或配置文件中的 `kb_path`

**路径解析（`--kb-source auto` 时）**：

1. 若指定 `--kb <路径>` → 使用该路径（临时覆盖，不修改配置）
2. 否则读取统一配置：
   ```bash
   python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py get taw localkb.path
   ```
   - 若返回有效路径 → 使用该路径
   - 若返回空 → 跳过知识库（降级模式）
3. 若配置不存在 → **交互询问知识库来源**：
   ```
   未检测到知识库配置，请选择内容来源：
   1. 互联网检索（WebSearch，适合知识库未建立或需要最新资料的场景）
   2. 本地知识库（需提供索引目录路径）
   请输入选项编号（1 或 2）：
   ```
   等待用户回复：
   - 用户选 **1** → 设置 `NO_KB_FLAG=true`，进入互联网检索模式，跳过路径配置，输出：
     ```
     ⚠️ 已选择互联网检索模式，将跳过知识库。如需后续配置知识库，使用 /taw --set-kb <路径>
     ```
   - 用户选 **2** → 继续原有引导流程：
     ```
     请提供 Local-KnowledgeBase 知识库目录路径（运行 /taw --build-kb-index 生成索引）：
     ```

     用户提供路径 → 验证路径存在后保存到 `~/.config/tender-workflow/config.yaml`，输出：
     ```
     ✅ 知识库路径已保存至 ~/.config/tender-workflow/config.yaml
     后续运行将自动使用此路径。如需修改，使用 /taw --set-kb <新路径>
     ```
     用户回复"无"或"跳过" → 保存 `kb_path: none`，走降级逻辑，输出：
     ```
     ⚠️ 已跳过知识库配置，将以降级模式运行（无案例/方案引用）。
     如需后续配置，使用 /taw --set-kb <路径>
     ```

**Step 5：`--chapter` 解析 → 确定 CHAPTERS_TO_WRITE 列表**

将用户输入的 `--chapter` 值解析为待撰写章节列表 `CHAPTERS_TO_WRITE`：

```
1. 若值包含 "-"、"到"、"至"（去除空格后） → 范围模式：
   a. 提取起止节点（如 "1.1" 和 "1.9"）
   b. 在完整扁平序列中定位两个节点的索引（start_idx / end_idx）
   c. 切片得到 [start_idx, end_idx] 区间（含两端）
   d. CHAPTERS_TO_WRITE = 切片结果
   e. 边界异常：节点不在序列中 / start_idx > end_idx → 输出错误提示并停止

2. 若值为 "all" → CHAPTERS_TO_WRITE = 大纲中的所有小节（根据实际章节数）

3. 若值为主章名（一/1）→ CHAPTERS_TO_WRITE = 该章的子节列表

4. 若值为具体小节号（如 "1.3"）→ CHAPTERS_TO_WRITE = ["1.3"]

示例：
  输入 "1.1到1.9"
  → CHAPTERS_TO_WRITE = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]（共9节）
```

### 0.2 文件加载

#### 0.2.1 读取投标文件大纲（.docx）

使用 Phase 0.1 Step 3 解析出的 `OUTLINE_PATH`，以 `python-docx` 提取文本内容：

```bash
python3 -c "import docx" 2>/dev/null || python3 -m pip install python-docx -q --break-system-packages 2>/dev/null || pip install python-docx -q 2>/dev/null
python3 -c "
from docx import Document
import sys

doc = Document(sys.argv[1])
for para in doc.paragraphs:
    level = ''
    if para.style.name.startswith('Heading'):
        try:
            level = '#' * int(para.style.name.split()[-1]) + ' '
        except ValueError:
            pass
    if para.text.strip():
        print(f'{level}{para.text}')
" "$OUTLINE_PATH"
```

将提取的文本保存为临时变量，用于后续章节定位。重点提取：
- **章节编号与标题**：识别一/二/三级标题，构建大纲目录树
- **目标章节内容**：定位用户指定章节号对应的大纲段落

#### 0.2.2 读取招标分析报告（.md）

分析报告为 Markdown 格式，直接使用 Read 工具读取 Phase 0.1 Step 3 解析出的 `REPORT_PATH`。

**模块定位规则**（分析报告使用 Markdown 标题组织，按以下模式定位各模块）：

| 模块 | 标题匹配模式 | 用途 |
|------|------------|------|
| M1 | `## M1` 或 `## 一、基础信息` | 项目背景 |
| M2 | `## M2` 或 `## 二、技术要求` | 技术要求矩阵 |
| M3 | `## M3` 或 `## 三、商务要求` | 商务条款 |
| M4 | `## M4` 或 `## 四、评分标准` | 评分细则 |
| M5 | `## M5` 或 `## 五、废标条款` | 红线条款 |
| M7 | `## M7` 或 `## 七、投标策略` | 撰写指导 |

每个模块从其标题行开始，到下一个同级 `##` 标题行结束。使用 Grep 工具搜索模块标题快速定位行号，再用 Read 工具读取对应区间。

#### 0.2.3 检测知识库

若 `NO_KB_FLAG=true` → 跳过本节，标记所有 KB 为空。

否则，检测新知识库目录结构：

**KB 目录索引**：
```
KB_CATALOG = null
KB_ROOT = 从 config 获取 localkb.path（python3 $SKILL_DIR/../twc/skills/twc/tools/tw_config.py get taw localkb.path）
if KB_ROOT/.index/kb_catalog.yaml exists:
  KB_CATALOG = Read(KB_ROOT/.index/kb_catalog.yaml)
  log: "[KB] 已加载目录索引: {len(KB_CATALOG.entries)} 个文档"
else:
  log: "⚠️ KB 目录索引未建立，建议运行 /taw --build-kb-index"
```

> 图片来源：v3.0 Local-KnowledgeBase 格式下图片路径为 `{KB_ROOT}/{dir}/images/{hash}.jpg`

### 0.3 输入验证

```
已加载文件：
1. 大纲：[OUTLINE_PATH 实际文件名] - 章节数：[N]
2. 报告：[REPORT_PATH 实际文件名] - 模块：M1-M7 [+ 行业扩展 E1-E3]
3. 知识库状态：
   - 来源配置：`--kb-source` = [auto/local/anythingllm/none]
   - AnythingLLM：✅ 可用（workspace: [ANYTHINGLLM_WORKSPACE_NAME]）/ ⚠️ 不可用
   - KB 目录索引：✅ 已加载 [N 个文档] / ⚠️ 未建立（运行 /taw --build-kb-index）
4. 搜索工具：
   - 若 MCP_TOOLS_AVAILABLE 非空 → `✅ MCP工具可用 (tavily_search, exa_search)` 或 `✅ MCP工具可用 (tavily_search)` 或 `✅ MCP工具可用 (exa_search)`
   - 若 MCP_TOOLS_AVAILABLE 为空 → `⚠️ 仅 WebSearch 可用`
   - 显示优先级：`工具优先级: WebSearch → tavily_search → exa_search`（根据实际可用工具显示）
5. 图片来源：`--image-source` = [auto/local/drawio/ai/web/placeholder]
   - ai: ✅ AI 生图模式（调用 ai-image plugin 的 image-gen 命令）
   - web: ✅ 互联网图片模式（WebSearch + curl 下载）
   - placeholder: ✅ 占位符模式（生成图片占位符文本）
   - auto: ✅ 自动模式（按 H3 子节上下文独立选择）

目标章节：[章节号] [章节名]
```

若 `OUTLINE_PATH` 或 `REPORT_PATH` 是经目录匹配得出（非用户直接指定文件），在验证信息后追加一行确认提示：
```
（目录自动匹配：[参数来源目录] → [实际文件名]，如需指定其他文件请使用完整路径）
```

若分析报告不存在或无法解析，提示用户先运行 `/taa` 生成分析报告。

### 0.4 启动确认

输出以下信息后，直接进入 Phase 1（无需用户回复）：

```
─────────────────────────────────────
撰写启动：
• 大纲文件：[OUTLINE_PATH 实际文件名]
• 分析报告：[REPORT_PATH 实际文件名]
• 目标章节：[原始输入] → 展开为 [N] 个章节：[1.1, 1.2, ...]
• 知识库：[状态]
• 输出目录：[路径]
─────────────────────────────────────
```

单节模式（CHAPTERS_TO_WRITE 仅含 1 个章节）时，"目标章节"行直接显示章节号和名称，无需展开说明。

---

## Phase 1：撰写准备

### 1.1 章节模板加载与评分映射提取

**Step 1：读取核心模板和匹配器**

1. 读取核心模板：
   ```
   Read $SKILL_DIR/prompts/article_core.yaml
   ```

2. 读取章节类型匹配器：
   ```
   Read $SKILL_DIR/prompts/chapter_type_matcher.yaml
   ```

**Step 2：从大纲中提取目标章节信息**

1. 定位目标章节在大纲中的位置（基于章节编号）
2. 提取章节标题（如"1.3 总体方案设计"）
3. **提取章节子节标题**（提取所有层级子节，最深至第5级）：
   - 扫描大纲中当前章节下的所有子标题（三级/四级/五级）
   - 记录到 OUTLINE_SUBSECTIONS[章节号] = [{numbering, title, depth}, ...]
   - depth 值：3=三级标题, 4=四级标题, 5=五级标题
   - **此列表将直接用于 Phase 2 内容组织的标题结构**

   **示例**：
   - 大纲结构：
     ```
     1.11 培训方案
       1.11.1 培训计划与课程体系
         1.11.1.1 基础培训课程
         1.11.1.2 进阶培训课程
       1.11.2 培训讲师资质
       1.11.3 培训效果评估
     ```
   - 提取结果：
     ```
     OUTLINE_SUBSECTIONS['1.11'] = [
         {'numbering': '1.11.1', 'title': '培训计划与课程体系', 'depth': 3},
         {'numbering': '1.11.1.1', 'title': '基础培训课程', 'depth': 4},
         {'numbering': '1.11.1.2', 'title': '进阶培训课程', 'depth': 4},
         {'numbering': '1.11.2', 'title': '培训讲师资质', 'depth': 3},
         {'numbering': '1.11.3', 'title': '培训效果评估', 'depth': 3},
     ]
     ```

**Step 3：章节类型语义匹配**

1. 使用 chapter_type_matcher.yaml 中的匹配策略
2. 输入：章节标题（如"1.3 总体方案设计"）
3. 执行匹配：
   - 提取章节标题中的关键词（去除编号）
   - 与各类型的 keywords 进行语义匹配
   - 计算匹配度（关键词交集数 / 总关键词数）
   - 选择匹配度最高的类型
   - 若匹配度 < 0.6，使用 LLM 语义理解
4. 输出：章节类型（business/technical/service/commitment）+ 置信度

**示例**：
- "1.3 总体方案设计" → technical（置信度 0.90）
- "1.5 实施方案与计划" → technical（置信度 0.92）
- "1.10 售后服务方案" → service（置信度 0.92）
- "1.11 培训方案" → service（置信度 0.95）
- "1.4.2 容器编排与集群管理方案" → technical（置信度 0.85）

**Step 4：加载章节模板并提取图片配额**

1. 读取对应的章节模板：
   ```
   Read $SKILL_DIR/prompts/article_templates/{chapter_type}.yaml
   ```

   示例：
   - 章节类型 technical → 读取 article_templates/technical.yaml
   - 章节类型 business → 读取 article_templates/business.yaml

2. 从模板中匹配对应的 section_type（基于语义关键词）：
   - 提取章节标题中的关键词
   - 与模板中各 section_type 的 semantic_keywords 进行匹配
   - 选择匹配度最高的 section_type

3. 提取章节写作指南：
   - 从匹配的 section_type 中提取 word_count（字数要求）
   - **若 WORD_OVERRIDE[2] 已设置 → word_count = WORD_OVERRIDE[2]**（命令行覆盖模板值）
   - 提取 content_elements（内容要素）
   - 提取 kb_priority（知识库优先级）
   - 提取 image_types（图片类型）
   - 提取 scoring_alignment（评分对齐要求，如有）

4. **读取章节图片配额配置（新增）**：
   ```
   Read $SKILL_DIR/prompts/chapter_image_quota.yaml
   ```

   根据 section_type 查询配额：
   - 查找 chapter_image_quota[section_type]
   - 若找到 → 获取 quota（目标配额）、required（最少要求）、image_types（图片类型）
   - 若未找到 → 使用 defaults[chapter_type]（technical/service/business/commitment）
   - **若 IMAGE_OVERRIDE[2] 已设置 → quota = IMAGE_OVERRIDE[2]**（命令行覆盖配额值）

   **配额数据结构示例**：
   ```yaml
   training_service:
     quota: 1          # 目标：1张图片
     required: 1       # 最少：1张图片（必须满足）
     image_types: [培训体系图, 培训路径图]
   ```

**示例**：
- 章节标题："1.3 总体方案设计"
- 章节类型匹配：technical（置信度 0.90）
- 加载模板：article_templates/technical.yaml
- 匹配 section_type：overall_solution（匹配关键词：总体方案、架构设计）
- 提取写作指南：4500字，技术架构设计、技术选型、关键技术路线...
- 查询图片配额：quota=2, required=1, image_types=[系统架构图, 技术架构图]

**Step 2：评分映射提取**

从分析报告 M4（评分细则与得分策略）中提取与目标章节相关的评分项：

| 评分项 ID | 评分项名称 | 分值 | 评分规则 | {VENDOR_NAME} 优势 | 拿高分策略 |
|-----------|-----------|------|---------|-----------|-----------|
| S编号 | | | | | |

（此表为模板，实际内容由 Phase 1.1 从分析报告 M4 中提取）

标注高分值项（≥10分）为**重点展开**项。

### 1.2 M7 撰写指导提取

从 M7（标书撰写指导）中提取与目标章节直接相关的指导信息：

- **撰写优先级**：目标章节涉及的 P1/P2/P3 优先事项
- **关键词清单**：目标章节需覆盖的技术/商务/合规关键词
- **写作策略**：M7.3 中与目标评分项对应的具体写法建议
- **差异化亮点**：M7.4 中指定在目标章节展现的亮点
- **红线**：M7.5 中的 ⛔ 红线和 ⚠️ 慎重项

### 1.3 知识库检索（⚠️ 强制步骤 - 不可跳过）

**重要**：本阶段必须执行，Phase 1.4 输出中必须包含知识库来源统计。

#### 核心原则

- 所有匹配基于**内容主题/关键词语义**，与章节号无关
- `--kb-source local` → 强制使用本地 KB 目录索引，跳过 AnythingLLM
- `--kb-source none` → 跳过所有 KB（文字和图片均走 WebSearch）
- reusable 有内容+有图 → 直接用，不走其他图片逻辑

#### 全局知识池（多节模式优化）

**触发条件**：CHAPTERS_TO_WRITE 含多个章节（≥ 2 个）且 `NO_KB_FLAG=false`

**说明**：若 `NO_KB_FLAG=true`，跳过全局知识池（因为知识库不可用，全局搜索基于知识库）

**目的**：减少重复搜索，提高知识复用效率

**GLOBAL_KNOWLEDGE_POOL 结构**：

```yaml
vendor_info:
  products: []           # 产品列表（名称、版本、核心能力）
  capabilities: []       # 核心能力（技术特性、性能指标）
  cases: []              # 典型案例（客户类型、项目规模、实施时间）
  certifications: []     # 资质认证（ISO、信创、安全等级）
industry_trends: []      # 行业趋势（最新技术、发展方向）
technical_standards: []  # 技术标准（Kubernetes、CNCF、国标）
```

**填充策略**（Phase 1.3 开始时执行）：

1. **全局搜索**（≤ 2 次 WebSearch，不计入后续每节的搜索次数限制）：
   - 查询词 1：`"{VENDOR_NAME} 产品线 核心能力 2026"`
   - 查询词 2：`"{项目行业} 技术趋势 最佳实践 2026"`
2. **结构化提取**：从搜索结果中提取产品信息、行业趋势、技术标准
3. **记录到 GLOBAL_KNOWLEDGE_POOL**
4. **后续每节写作时**：
   - 优先从 GLOBAL_KNOWLEDGE_POOL 提取相关知识
   - 不足时再执行 ≤ 2 次定向搜索
   - 新知识补充到池中

**单节模式**：跳过全局知识池，直接执行定向搜索

#### 当前章节语义上下文

```
章节语义上下文 = 章节标题 + 章节内容纲要 + M7关键词（取前10个最相关）
```

#### 文字内容检索（知识库 + 互联网并行策略，⚠️ 强制执行）

**根据 `--kb-source` 参数执行检索**：

| `--kb-source` | KB 目录索引 | AnythingLLM | 互联网检索 |
|---------------|------------|-------------|------------|
| `auto`（默认）| ✅ 并行查询 | ✅ 并行查询 | ✅ 并行执行 |
| `local` | ✅ 强制使用 | ❌ 跳过 | ✅ 并行执行 |
| `anythingllm` | ❌ 跳过 | ✅ 强制使用 | ✅ 并行执行 |
| `none` | ❌ 跳过 | ❌ 跳过 | ✅ 仅互联网 |

**【优先层：Local-KnowledgeBase Markdown 检索（图文一体化）】**

触发条件：`{KB_ROOT}/.index/kb_catalog.yaml` 存在 且 `NO_KB_FLAG=false`

**核心原则**：从 Markdown 文档中同时获取文字素材和图片引用，图文关系通过位置共存自然表达。

1. 读取 KB 目录索引：`{KB_ROOT}/.index/kb_catalog.yaml`
   - 若不存在 → 跳过此层，降级到 AnythingLLM 层（若可用）
   - 若存在 → 获取 entries 列表（每条含 dir、title、category、headings、summary）

2. AI 从索引条目中选出与当前章节语义相关的 KB 文档（1-5 个，有匹配则尽量多选）：
   - 匹配依据：章节标题 + M2 技术要求关键词 ↔ 索引的 title/headings/summary
   - 多版本消歧：目录名含版本号时优先选最新版
   - 分类过滤：技术章节优先匹配 category=technical 的文档
   - **宁多勿漏**：只要索引条目与章节主题存在实质关联，即应纳入候选，在后续段落级筛选中再精确取舍

3. **多文档互补分工**（选出 2 个及以上文档时）：
   - 按 H3 子节分配：每个 H3 优先从与其主题最贴合的那 1-2 个文档取材
   - 互补原则：不同文档提供不同维度的内容（如文档 A 提供架构设计，文档 B 提供部署实施，文档 C 提供运维保障）
   - 禁止重复拼接：不得从多个文档取语义重叠的段落拼凑，若多个文档覆盖相同主题则取内容最详实的一个
   - 取材记录：在 KB_MATERIALS 中标注每条素材的来源文档，便于后续溯源

4. 对匹配到的 KB 文档，获取其段落结构：
   ```
   KB_ROOT = 从 config 获取 localkb.path
   main_md_file = matched_entry.get("file", "full.md")  # 兼容旧索引
   full_md_path = KB_ROOT / matched_entry.dir / main_md_file
   使用 Grep 工具搜索 full_md_path 中的标题行（^# ）获取段落结构
   ```

5. AI 从标题列表中选出与当前 H3 主题最相关的段落，用 Read 工具按行范围读取

6. AI 在读取的段落中同时获得：
   - **文字素材**：可复用/改写的段落内容 → 记录到 KB_MATERIALS（标注来源文档 dir）
   - **图片引用**：`![](images/HASH.jpg)` 形式的嵌入图片 → AI 判断图片与 H3 内容的相关性
     - 相关 → 记录到 MATCHED_IMAGES：`{h3_numbering, image_path: KB_ROOT/dir/images/HASH.jpg, context: 图片前后文字}`
     - 不相关 → 跳过

7. 若有效结果数 >= 2（包含文字或图片匹配）→ **跳过下方 AnythingLLM 层**
8. 若有效结果数 < 2 → 降级到 AnythingLLM 层（若可用）

**注意**：此层与互联网检索并行执行（不互斥）

**检索结果统计**（必须在 Phase 1.4 输出中显示）：
- KB 目录索引匹配文档数
- AnythingLLM 检索结果数
- 互联网检索结果数（WebSearch/MCP）
- 总可用知识条目数

**执行流程**：

**核心策略**：知识库与互联网**并行检索**，融合两者优势：
- **知识库**：公司案例、历史方案、固定条款（优先引用）
- **互联网**：最新技术、行业趋势、产品参数（补充深度）

**⚠️ 知识库检索强制执行检查点**：

在 Phase 1.3 执行时，必须完成以下步骤，禁止跳过：

1. **KB 目录索引检索**（`--kb-source=auto` 时）：
   - 必须读取 `kb_catalog.yaml`（若存在）
   - 从匹配的 KB 文档中读取相关段落
   - 禁止假设知识库为空而不读取索引文件

2. **AnythingLLM 检测与调用**（`--kb-source=auto` 或 `anythingllm` 时）：
   - 必须先检测 anythingllm_search 工具是否可用
   - 若可用，必须实际调用 anythingllm_search 进行检索
   - 记录检索结果数量和来源分布

3. **检索结果输出要求**：
   - Phase 1.4 输出必须包含知识库来源统计
   - 显示 KB 目录索引匹配数或 "⚠️ 未使用" 状态
   - 显示 AnythingLLM 结果数或 "⚠️ 未使用" 状态
   - 若两者都显示 "⚠️ 未使用"，说明知识库检索被跳过，必须重新执行

4. **知识库为空处理**：
   - 若读取后发现 entries 为空或索引文件不存在，明确标注 "知识库索引为空"
   - 此时触发互联网检索作为兜底
   - 禁止不读取文件就假设知识库为空

**【优先层：AnythingLLM 语义检索】**

触发条件：`ANYTHINGLLM_AVAILABLE=true` 且 `NO_KB_FLAG=false`

1. 构建查询词：`章节标题 + M7关键词（取前5个最相关）`
2. 调用：
   ```
   anythingllm_search(
     query="<章节标题> <M7关键词>",
     workspace=ANYTHINGLLM_WORKSPACE
   )
   ```
3. 过滤：取 `score >= 0.7` 的结果（最多5条）
4. 按来源分类标注：
   - `metadata.chunkSource` 含 `fixed` → 标注 `[来源：固定条款，不可修改]`
   - `metadata.chunkSource` 含 `reusable` → 标注 `[来源：可复用方案，微调使用]`
   - `metadata.chunkSource` 含 `history` → 标注 `[来源：历史案例，改写提炼，注意脱敏]`
   - 其他 → 标注 `[来源：知识库，参考使用]`
5. 若有效结果数 >= 2 → 直接进入互联网检索层
6. 若有效结果数 < 2 → 仅依赖互联网检索兜底

**【第四层：互联网检索 — 并行执行，场景化工具选择】**

触发：**与知识库检索同时执行**（不等前三层失败）

**厂商优先站点加载**：

Read `$SKILL_DIR/prompts/vendor_sites.yaml`，解析厂商站点列表：
- 用 `VENDOR_NAME` 匹配 `vendors[].vendor_name` 或 `vendors[].aliases`（不区分大小写）
- 匹配到 → 记为 `VENDOR_SITES`（该厂商的 sites 列表）
- 未匹配 → `VENDOR_SITES=[]`（不影响搜索，仅跳过定向检索）
- 加载 `authority_sites`（通用权威站点）

**搜索执行策略**：对每个搜索场景，先用 `VENDOR_SITES + authority_sites` 做定向检索（allowed_domains），再做不限域名的补充检索。定向检索结果优先纳入 WEB_FACTS。

**工具选择策略**（根据搜索内容类型）：

1. **判断搜索场景**（基于章节主题和 M7 关键词）：

   场景 A：产品能力查询
   - 触发词：产品名称、版本、功能特性、技术参数
   - 工具选择：知识库 history > WebSearch > MCP 工具

   场景 B：技术方案/架构
   - 触发词：架构设计、技术方案、最佳实践、设计模式
   - 工具选择：WebSearch > MCP 工具（如可用）

   场景 C：案例数据
   - 触发词：案例、客户、项目、实施、部署
   - 工具选择：知识库 history > WebSearch > MCP 工具

   场景 D：行业趋势/标准
   - 触发词：趋势、标准、发展方向、技术演进
   - 工具选择：WebSearch > MCP 工具（如可用）

2. **执行搜索**：

   **统一执行顺序（所有场景）**：

   根据 SEARCH_TOOL_OVERRIDE 确定工具列表：

   - 若 SEARCH_TOOL_OVERRIDE="tavily" → 工具列表: ["tavily_search"]
   - 若 SEARCH_TOOL_OVERRIDE="exa" → 工具列表: ["exa_search"]
   - 若 SEARCH_TOOL_OVERRIDE="mcp" → 工具列表: MCP_TOOLS_AVAILABLE（按 MCP_TOOL_PRIORITY 顺序）
   - 若 SEARCH_TOOL_OVERRIDE="websearch" → 工具列表: ["WebSearch"]
   - 若 SEARCH_TOOL_OVERRIDE="auto"（默认）→ 工具列表: ["WebSearch"] + MCP_TOOLS_AVAILABLE

   **按顺序尝试工具列表中的每个工具**：

   1. **WebSearch**：

      **定向检索**（VENDOR_SITES 非空时优先执行）：
        ```
        WebSearch(
          query="{VENDOR_NAME} {章节主题} {场景关键词}",
          allowed_domains=VENDOR_SITES  # 从 vendor_sites.yaml 加载的厂商站点
        )
        ```
        - 定向检索结果优先纳入 WEB_FACTS（confidence 默认为"高"）
        - 此次搜索计入搜索次数配额

      **补充检索**（不限域名，覆盖定向检索未涵盖的内容）：

      - 产品查询（场景 A）：
        ```
        WebSearch(
          query="{VENDOR_NAME} {产品名} {功能特性}"
        )
        ```

      - 技术方案/架构（场景 B）：
        ```
        WebSearch(
          query="{项目行业} {章节主题} 技术方案 最佳实践"
        )
        ```

      - 案例数据（场景 C）：
        ```
        WebSearch(
          query="{VENDOR_NAME} {章节主题} 案例 项目"
        )
        ```

      - 行业趋势/标准（场景 D）：
        ```
        WebSearch(
          query="{项目行业} {章节主题} 趋势 标准",
          allowed_domains=authority_sites.standards + authority_sites.technical  # 从 vendor_sites.yaml 加载
        )
        ```

   2. **tavily_search**（若在工具列表中）：
      ```
      tavily_search(
        query="{项目行业} {章节主题} 技术方案",
        search_depth="advanced",
        max_results=5
      )
      ```
      - 超时设置：30秒
      - 失败处理：继续尝试下一个工具

   3. **exa_search**（若在工具列表中）：
      ```
      exa_search(
        query="{项目行业} {章节主题} 技术方案",
        num_results=5,
        use_autoprompt=True
      )
      ```
      - 超时设置：30秒
      - 失败处理：继续尝试下一个工具

   **降级链**：
   - 当前工具超时（>30秒）→ 尝试下一个工具
   - 当前工具返回错误 → 尝试下一个工具
   - 所有工具失败 → 标注 [待补充]

   **强制指定工具时的特殊处理**：
   - 若 SEARCH_TOOL_OVERRIDE="tavily" 或 "exa" → 失败则报错，不降级
   - 若 SEARCH_TOOL_OVERRIDE="mcp" → 尝试所有 MCP 工具，全部失败则报错
   - 若 SEARCH_TOOL_OVERRIDE="websearch" → 只用 WebSearch，失败则标注 [待补充]

3. **查询词构建**：
   - 主查询：`"{项目行业} {章节主题关键词} 解决方案 最佳实践"`
   - 补充查询（若 EXTRA_QUERY 非空）：EXTRA_QUERY
   - 补充查询（否则）：`"{VENDOR_NAME} {M7核心关键词} 案例"`

4. **搜索次数限制**：
   - NO_KB_FLAG=true 时：≤ 4 次/章节
   - 否则：≤ 3 次/章节（定向检索 1 次 + 补充检索 1 次 + MCP 工具 1 次）
   - 定向检索、补充检索、MCP 工具共享此配额

5. **结果处理与格式适配**：
   > Read `$SKILL_DIR/prompts/fact_extraction_rules.yaml` 中 `search_result_formats`～`unified_extraction_flow` 部分，按格式适配规则处理各搜索工具返回结果。

6. **降级处理**：
   - MCP 工具超时（>30秒）→ 降级到 WebSearch
   - MCP 工具返回错误 → 降级到 WebSearch
   - WebSearch 失败 → 使用知识库兜底
   - 所有工具失败 → 标注 `[待补充]`

7. **优先来源**（WebSearch 模式）：
   官方文档、InfoQ/CNCF/云厂商官网；过滤广告及泛泛问答

8. **标注规则**：
   - Tavily Search 来源的具体数字/指标标注 `[Tavily来源，请核实]`
   - Exa Search 来源的具体数字/指标标注 `[Exa来源，请核实]`
   - WebSearch 来源的具体数字/指标标注 `[互联网来源，请核实]`
   - 知识库来源标注 `[知识库来源]`
   - 通用技术描述无需逐句标注
   - 不得照搬原文，结合 M2/M4/M7 针对本项目写作

**内容融合策略**（Phase 2 章节写作时应用）：

> **多结果选择与去重**：每个 H3 子节引用 WEB_FACTS 不超过 5 条，同类型语义重叠的事实仅保留最详实的一条（confidence 高优先），优先凑齐不同 type 的事实组合实现多维度论证。KB 与互联网内容重叠时优先使用 KB，互联网作为补充（最新数据/行业对比/第三方佐证）。完整规则见 `fact_extraction_rules.yaml` 的 `selection_rules`。

1. **开篇：需求理解**（300-450 字）
   - 来源：M2 技术要求原文
   - 作用：明确招标方需求

2. **行业背景**（450-600 字）
   - 来源：互联网资料（最新趋势、技术演进）
   - 作用：展示行业洞察力

3. **方案设计**（900-1,500 字）
   - 来源：知识库 reusable 方案（公司经验）+ 互联网技术方案
   - 作用：核心技术路线

4. **技术实现**（900-1,500 字）
   - 来源：互联网技术细节 + 知识库历史实施经验
   - 作用：具体实施步骤

5. **案例佐证**（450-600 字）
   - 来源：知识库案例（公司业绩）
   - 作用：证明实施能力

6. **预期效果**（300-450 字）
   - 来源：M4 评分标准
   - 作用：对标评分点

**搜索完成后，立即执行事实提取** — Read `$SKILL_DIR/prompts/fact_extraction_rules.yaml` 中 `web_facts_schema`～`multi_chapter_mode` 部分，按规则从搜索结果中提炼结构化事实（`WEB_FACTS` 表），供 Phase 2 写作引用。

#### 图片获取（简化版）

**核心原则**：
- 通过 `--image-source` 参数控制图片来源：`drawio`/`ai`/`web`/`placeholder`/`auto`
- `--image-source auto`（默认）：按 H3 子节上下文独立选择最合适的图片来源（见下方决策规则）
- 显式指定模式（ai/web/placeholder）失败时不降级，直接使用占位符

**auto 模式决策规则**（按三级章节粒度，根据每个 H3 子节的内容上下文独立判断）：
- 子节涉及架构设计、流程描述、部署方案 → 优先 `drawio`（生成架构图/流程图）
- 子节涉及公司产品截图、已有方案、历史案例 → 优先从 KB 图文共生获取
- 子节需要示意图、概念图、通用技术图 → 优先 `ai`（AI 生成）
- 子节需要行业数据、第三方产品截图 → 优先 `web`（互联网下载）
- 无法判断或均不适合 → `placeholder`（占位符）
- **注意**：同一个 H2 章节下的不同 H3 子节可以选择不同的图片来源

**执行流程**：

根据 `IMAGE_SOURCE` 参数执行对应方案：

**方案 A：AI 生图（IMAGE_SOURCE="ai"）**

1. **判断图表类型**：
   - 根据当前章节主题判断图表类型（architecture/flowchart/organization）

2. **调用 AI 生图工具**：
   ```bash
   image-gen \
     --type <图表类型> \
     --topic "<章节主题>" \
     --components "<关键组件，逗号分隔>" \
     --output /tmp/taw_ai_img_<章节号>.png
   ```

   参数说明：
   - `--type`：从 diagram_type_rules 获取（architecture/flowchart/organization）
   - `--topic`：章节主题（从大纲中提取）
   - `--components`：关键组件列表（从招标分析报告 M2 技术要求中提取）

3. **验证生成结果**：
   ```bash
   if [ -f /tmp/taw_ai_img_<章节号>.png ] && [ $(stat -c%s /tmp/taw_ai_img_<章节号>.png) -gt 10240 ]; then
     echo "✅ AI 生图成功"
   else
     echo "❌ AI 生图失败"
   fi
   ```

4. **记录到 MATCHED_IMAGES**：
   ```
   MATCHED_IMAGES[<章节号>] = {
     path: "/tmp/taw_ai_img_<章节号>.png",
     caption: "图 <章节号>-1：<章节主题> [AI生成图片，建议人工审核]",
     source: "AI生成（火山方舟/阿里云）"
   }
   ```

5. **失败处理**：
   - 若生成失败或文件过小（< 10KB）→ 使用占位符（不降级）

**方案 C：互联网图片（IMAGE_SOURCE="web"）**

1. **搜索图片页面**：
   - 工具优先级：**WebSearch 优先** > MCP 工具（tavily/exa）兜底
   - 不限定固定网站，搜索范围为全网
   - 查询词构造：根据 H3 内容和所需图片类型动态生成，中文优先、英文补充
     - 架构/流程类示例：`"容器云平台 微服务架构 架构图"`、`"CI/CD pipeline 流程图"`、`"Kubernetes 集群部署 拓扑图"`
     - 产品截图类示例：`"云原生 平台 控制台 界面"`、`"Kubernetes dashboard 截图"`、`"Prometheus 监控大屏"`
     - 若中文结果不足，追加英文查询：`"{section_topic} {diagram_type} screenshot/diagram"`
   - 选取最相关的 2-3 个结果页面 URL
   - 若 WebSearch 无有效结果，使用 MCP 工具兜底：
     - tavily_search：`query="{章节主题} {diagram_type}"`, `search_depth="advanced"`, `include_images=true`
     - exa web_search_exa：`query="{章节主题} {diagram_type} diagram"`, `num_results=5`
     - MCP 工具返回的图片 URL 可直接使用，跳过步骤 2

2. **提取图片 URL**：
   - 使用 WebFetch 获取页面完整内容，从 Markdown/HTML 中提取图片 URL
   - 若 WebFetch 不可用或失败 → 使用 Bash curl + grep 提取：
     ```bash
     curl -s -L "{页面URL}" --max-time 10 -A "Mozilla/5.0" | grep -oE '(src|href)="[^"]*\.(png|jpg|jpeg|svg)"' | head -5
     ```
   - 过滤掉明显的 icon/logo/avatar 小图（路径含 `icon`、`logo`、`avatar`、`favicon` 的跳过）

3. **下载图片**：
   ```bash
   curl -L -o /tmp/taw_img_{section}_{n}.png "{图片直链}" --max-time 15 -A "Mozilla/5.0"
   ```
   - 下载成功（文件 > 5KB）→ 加入 `MATCHED_IMAGES`
   - caption 追加：`[来源: {domain}，建议替换为自有图片]`

4. **失败处理**：
   - 若所有 URL 下载失败 → 使用占位符（不降级）
   - 每章节互联网图片上限：2 张

**方案 D：占位符（IMAGE_SOURCE="placeholder"，默认）**

生成图片占位符文本：
```
> [图片占位符 — {diagram_type}：{description}，请在此处插入对应图片]
```

示例：
```
> [图片占位符 — 架构图：总体技术架构图（分层架构示意），请在此处插入对应图片]
> [图片占位符 — 流程图：CI/CD流水线端到端流程图，请在此处插入对应图片]
```

**重要约束**：
- ❌ 任何模式下都不得用文字描述代替图片
- ❌ 不得用纯文本段落模拟图表内容
- ❌ 不得使用外部 URL 直接引用图片（必须下载到本地）
- ✅ 失败时使用占位符，不隐式降级到其他方案

### 1.4 准备确认（⚠️ 必须包含知识库来源统计）

```
撰写准备完成：
• 相关评分项：[N] 个（重点项 [M] 个，合计 [X] 分）
• M7 关键词：[N] 个
• 章节类型：[章节类型] → [section_type]
• **图片分配**：H3 粒度分配 [N] 张（或静态配额 [quota] 张），类型：[image_types]
• 知识库来源统计：
  - 配置来源：`--kb-source` = [auto/local/anythingllm/none]
  - KB 目录索引：[N] 个文档匹配 / ⚠️ 未使用
  - AnythingLLM：[N] 条 / ⚠️ 未使用
  - 互联网检索：[N] 条
  - 总计可用：[N] 条
• 图片来源：`--image-source` = [auto/local/drawio/ai/web/placeholder]
  - auto: 自动模式（按 H3 子节上下文独立选择）
  - drawio: draw.io 图表生成模式
  - ai: AI 生图模式
  - web: 互联网图片模式
  - placeholder: 占位符模式
• 红线约束：[N] 条
```

**⚠️ 强制要求**：
- 若 KB 目录索引和 AnythingLLM 都显示 "⚠️ 未使用"，**禁止进入 Phase 2**，必须重新执行 Phase 1.3
- 未使用原因必须明确标注（如："未配置"、"调用失败"、"文件不存在"、"entries为空"、"无匹配"）
- 图片配额信息必须显示（目标配额、最少要求、图片类型）

---

## Phase 2：内容生成

根据目标章节类型，加载对应的写作策略（详见「章节类型与写作策略」），逐节生成内容。

**⚠️ Markdown 渲染强制要求**：
- ❌ **禁止直接使用 `doc.add_paragraph()` 添加正文内容**
- ❌ **禁止将 Markdown 原始标记（如 `**粗体**`）直接写入 DOCX**
- ✅ **必须使用 `write_markdown()` 函数处理所有正文**
- ✅ **所有正文必须先经过 Markdown 格式渲染再写入 DOCX**
- ✅ **确保粗体、斜体、代码、列表、表格等格式正确渲染**

**错误示例**：
```python
# ❌ 错误：直接使用 add_paragraph，Markdown 标记不会渲染
doc.add_paragraph('本项目采用 **微服务架构**，具备`容器编排`能力。')
# DOCX 中显示为：本项目采用 **微服务架构**，具备`容器编排`能力。

# ❌ 错误：直接使用 add_para_cn，Markdown 标记不会渲染
add_para_cn(doc, '本项目采用 **微服务架构**，具备`容器编排`能力。')
```

**正确示例**：
```python
# ✅ 正确：使用 write_markdown，Markdown 会被正确解析
write_markdown(doc, '本项目采用 **微服务架构**，具备`容器编排`能力。')
# DOCX 中显示为：本项目采用 **微服务架构**（粗体），具备`容器编排`（代码样式）能力。
```

**⚠️ 强制执行检查点（代码生成时必须遵守）**：

1. **正文写入唯一入口**：所有正文内容必须通过 `write_markdown()` 函数写入，禁止直接使用 `doc.add_paragraph()` 或 `add_para_cn()`

2. **格式标记检查**：如果生成的内容包含以下任何标记，必须经过 `write_markdown()` 解析：
   - `**文本**` 或 `__文本__`（粗体）
   - `*文本*` 或 `_文本_`（斜体）
   - `` `文本` ``（代码）
   - `- ` 或 `* `（无序列表）
   - `1. ` `2. `（有序列表）
   - `|`（表格）
   - `>`（引用）

3. **表格强制要求**：技术参数对比、功能列表、里程碑计划等表格数据，必须使用 Markdown 表格格式通过 `write_markdown()` 写入，禁止用文本或制表符模拟表格

4. **代码执行前自检**：在生成 Python 代码前，检查所有 `doc.add_paragraph()` 和 `add_para_cn()` 调用，确保它们只用于：
   - 纯文本标题（不含任何 Markdown 标记）
   - 空行
   - 已明确不需要格式化的内容

5. **输出验证**：生成 DOCX 后，想象检查生成的内容：如果看到 `**`、`__`、`` ` `` 等原始标记出现在文档中，说明 Markdown 解析失败，必须修正

### 执行步骤

1. 使用 Read 工具读取 skill base_dir 下的 `prompts/article_core.yaml` 和对应的 `prompts/article_templates/*.yaml`，获取对应章节类型的写作规则

2. **并行写作路由判断**

   在开始内容生成前，对**每个章节**评估是否启用并行写作模式：

   ```
   H3_SUBSECTIONS = [s for s in OUTLINE_SUBSECTIONS.get(章节号, []) if s['depth'] == 3]
   H3_COUNT = len(H3_SUBSECTIONS)
   TARGET_WORDS = WORD_OVERRIDE[2] if WORD_OVERRIDE.get(2) else section_type_word_count
   USE_PARALLEL_WRITING = (H3_COUNT >= 3) and (TARGET_WORDS >= 4500)
   ```

   **路由输出**：
   ```
   [写作模式] 章节 {章节号} {章节标题}
   - H3 子节数：{H3_COUNT}
   - 目标字数：{TARGET_WORDS}
   - 模式：{'✅ 并行写作模式（Phase 2A→2B→2C）' if USE_PARALLEL_WRITING else '→ 顺序写作模式（Step 2a-2d）'}
   ```

   - `USE_PARALLEL_WRITING = true` → 跳转到 **Phase 2A（写作蓝图生成）**
   - `USE_PARALLEL_WRITING = false` → 继续执行下方 Step 3（顺序写作流程）

---

### Phase 2A：写作蓝图生成（仅 USE_PARALLEL_WRITING=true）

> Read `$SKILL_DIR/prompts/writing_brief_template.yaml`，按 `phase_2a_execution` 步骤和 `brief_structure` 格式生成 Writing Brief（论述主线 + H3 分工表 + 术语表）。完成后进入 Phase 2B。

---

### Phase 2B：并发子智能体撰写（仅 USE_PARALLEL_WRITING=true）

> Read `$SKILL_DIR/prompts/parallel_writer_agent.yaml`，按 `agent_prompt_template` 为每个 H3 打包上下文并并发分发，按 `phase_2b_execution.result_checking` 检查结果。>50% 失败则降级到顺序写作。完成后进入 Phase 2C。

---

### Phase 2C：整合审校（仅 USE_PARALLEL_WRITING=true）

> Read `$SKILL_DIR/prompts/writing_brief_template.yaml` 中 `phase_2c_integration` 步骤：拼接 → 引言 → 过渡 → 一致性审校 → M4 终检 → 结尾。合并完成后继续 Step 2b（图片）→ Step 2d → Phase 2.5 → Phase 3。

---

3. **按 CHAPTERS_TO_WRITE 顺序逐节撰写**（顺序写作模式 — USE_PARALLEL_WRITING=false 时执行，或并行模式降级后执行）

   **内容生成与写入规范（强制执行）**：

   **步骤 A：内容生成**
   - 使用 LLM 生成该子节的完整内容（Markdown 格式）
   - 内容应包含：标题、正文、列表、表格、强调等 Markdown 元素

   **步骤 B：内容写入（关键修复点）**

   ✅ **必须使用 write_markdown() 函数写入所有内容**

   ```python
   # ✅ 正确做法：使用 write_markdown 写入整个子节内容
   subsection_content = '''生成的 Markdown 内容，包含 **粗体**、- 列表、| 表格等'''
   write_markdown(doc, subsection_content)

   # ❌ 错误做法：逐段使用 add_para_cn
   # add_para_cn(doc, '**文本**')  # 这会显示原始 **
   ```

   **写入规则**：
   1. 每个子节的内容作为一个整体字符串，通过 `write_markdown()` 一次性写入
   2. 不要逐行/逐段调用 `add_para_cn()`
   3. 确保生成的内容使用正确的 Markdown 语法
   4. 表格使用 Markdown 表格格式（`|` 分隔）

   **步骤 C：图片插入（在文字内容写入后执行）**
   - 根据 SECTION_IMAGES[节号] 的记录
   - 对每个图片调用 `add_picture_cn()` 插入

2a. **每节写作前**：
    - 检查 `WEB_FACTS` 表，筛选适用于本节的事实条目（按"适用章节"列匹配）
    - 若多节模式：针对本节主题执行 ≤ 2 次定向 WebSearch，立即提取事实并补充 `WEB_FACTS`；以 "{VENDOR_NAME} {章节主题}" 为默认核心查询词；若 `EXTRA_QUERY` 非空，追加到查询词中
    - 将以上具体事实（产品名/版本/数字/引用）**强制融入本节正文**，不得以通用描述替代
    - 来自互联网的具体数字/指标标注 `[互联网来源，请核实]`

2b. **每节写作前（图片获取 - 强制执行）**：

    **核心流程**：H3 粒度分配 → 优先级匹配 → 执行获取 → 统一记录

    **Step 2b-1：图片规划（AI 驱动）**

    读取 `$SKILL_DIR/prompts/image_guidelines.yaml` 的护栏配置。

    **图片来源判断（按优先级）**：

    对每个 H3 子节，依次检查：

    **【情况 A -- KB 图文共生（MATCHED_IMAGES 非空）】**

    Phase 1.3 的 Local-KnowledgeBase 检索已识别出与该 H3 相关的 KB 图片：

    1. AI 确认图片仍与当前写作上下文相关
    2. 生成动态 caption：结合 H3 标题 + 图片在 KB 中的上下文
       - 格式：`图 {章节号}-{序号}：{结合 H3 上下文的描述}`
    3. 解析图片绝对路径：`KB_ROOT / dir_name / image_ref`
    4. 验证文件存在且大小 > 5KB
    5. 去重检查（USED_IMAGES 集合）→ 记录到 SECTION_IMAGES

    **【情况 B -- AnythingLLM 文字 + KB 图片分离模式】**

    触发：`--kb-source anythingllm` 且需要从 KB 获取图片（文字来自 AnythingLLM，图片需单独从 KB 获取）

    1. AI 用 H3 主题查 `kb_catalog.yaml` → 选相关 KB 文档
    2. Grep 主文档标题 → 定位与 H3 主题相关的段落
    3. Read 段落 → 从中提取 `![](images/...)` 引用
    4. AI 判断图片与 H3 内容的相关性 → 记录到 SECTION_IMAGES
    5. 无匹配 → 转情况 C

    **【情况 C -- 无 KB 匹配（AI 自主判断）】**

    AI 根据 H3 内容自主判断（参考 image_guidelines.yaml 的 no_kb_hints）：
    a. 该 H3 是否需要图片？（内容可视化价值、评分影响、章节图片密度）
    b. 需要 → 按 IMAGE_SOURCE 参数选择来源（见下方 IMAGE_SOURCE 策略）
    c. 不需要 → 跳过

    **【护栏（硬限制，AI 不可覆盖）】**
    - 章节最多 8 张图（chapter_max）
    - 单个 H3 最多 1 张图（h3_max）
    - 同章节不重复使用同一图片
    - 跨章节不重复使用同一图片（GLOBAL_USED_IMAGES）
    - 占位符 caption 要具体描述需要什么图：`图 X.X-N：{具体描述}，请在此处插入对应图片`

    **强制输出（图片规划）**：
    ```
    [图片规划] 章节 1.4 微服务管理平台解决方案（AI 评估）
    - H3 子节数：6
    - 评估结果：
      1.4.1 微服务核心能力方案 → 跳过 | AI："功能列表用表格更清晰"
      1.4.2 微服务治理与运营方案 → 1 张 [KB] images/abc.jpg
        来源：KB 段落"微服务治理架构"中嵌入的图片
        caption: "图 1.4-1：微服务治理与流量调度架构"
      1.4.3 微服务监控与运维方案 → 1 张 [drawio] 待生成
        来源：无 KB 匹配，AI 判断需要监控架构图
        caption: "图 1.4-2：可观测性平台监控架构"
      1.4.4 应用部署与中间件方案 → 1 张 [KB] images/def.jpg
        来源：KB 段落"CI/CD 部署流程"中嵌入的图片
        caption: "图 1.4-3：应用部署与中间件容器化流程"
      1.4.5 集成兼容与定制开发方案 → 跳过 | AI："文字描述型内容"
      1.4.6 微服务迁移咨询服务方案 → 跳过 | AI："服务承诺类，无需图片"
    - 总计：3 张（上限 8 张）
    ```

    **Step 2b-2：按 IMAGE_PLAN 逐条执行图片获取**

    对 IMAGE_PLAN 中每个需要图片的 H3，独立执行图片获取：

    ```
    USED_IMAGES = set()  # 去重集合

    for h3 in H3_SUBS:
      if h3 has MATCHED_IMAGES:    # 情况 A 或 B
        image = MATCHED_IMAGES[h3]
        verify file exists and size > 5KB
        USED_IMAGES.add(image.path)
        → SECTION_IMAGES.append(...)
      elif AI decides h3 needs image:  # 情况 C
        执行图片获取（按 IMAGE_SOURCE 策略，见下方详细流程）
        若获取成功 → USED_IMAGES.add(image_id)
        结果记录到 SECTION_IMAGES
      else:
        跳过（AI 判断不需要图片）
    ```

    **各 IMAGE_SOURCE 详细流程**：

    对 IMAGE_PLAN 中每个 allocate > 0 的 H3：

    **IMAGE_SOURCE="auto"（默认）**：
    ```
    1. 尝试 AnythingLLM 图片搜索（若 ANYTHINGLLM_AVAILABLE=true）
       - 调用 anythingllm_search(query="{h3_title} {preferred_types[0]}", workspace=...)
       - 若找到 → 记录到 SECTION_IMAGES，跳过下方步骤

    2. 尝试知识库图片（KB 图文共生）
       - AI 用 H3 主题查 kb_catalog.yaml → 选相关 KB 文档
       - Grep 主文档标题 → 读取相关段落 → 提取 ![](images/...) 引用
       - 若匹配成功 → 记录到 SECTION_IMAGES，跳过下方步骤

    3. 尝试 draw.io 生成（若 DRAWIO_AVAILABLE=true）
       - 调用 drawio Skill 或 `drawio-gen ...`
       - 验证：文件存在且 > 5KB
       - 若成功 → 记录到 SECTION_IMAGES，跳过下方步骤

    4. 尝试 AI 生图
       - 调用 ai-image plugin 的 image-gen 命令
       - 验证：文件存在且 > 10KB
       - 若成功 → 记录到 SECTION_IMAGES，跳过下方步骤

    5. 使用占位符（兜底）
    ```

    **IMAGE_SOURCE="drawio"（仅 draw.io 生成）**：
    ```
    1. 检查 DRAWIO_AVAILABLE 是否为 true
       - 若 false → 输出提示并降级到占位符（见 Step 1.7）

    2. 生成图表（优先 MCP，备选 CLI）：
       - 若 DRAWIO_SKILL_AVAILABLE=true：调用 drawio Skill（共享 drawio plugin 提供）
       - 若 DRAWIO_CLI_AVAILABLE=true：调用 `drawio-gen ...`
       - 参数：--type <图片类型> --topic "<章节主题>" --details "<JSON 格式的组件/流程/结构>"
       - 输出：/tmp/drawio_output/<topic>_<timestamp>.png（带嵌入 XML）

    3. 验证结果（文件存在且 > 5KB）
       - 成功 → 记录到 SECTION_IMAGES[节号]
       - 失败 → 使用占位符（不降级）
    ```
    适用场景：需要生成专业的架构图、流程图、组织图等可编辑图表

    **IMAGE_SOURCE="ai"（仅 AI 生图）**：
    ```
    1. 调用 ai-image plugin 的 image-gen 命令
       - 参数：--type, --topic, --components
       - 输出：/tmp/taw_ai_img_<节号>_<i>.png

    2. 验证结果（文件存在且 > 10KB）
       - 成功 → 记录到 SECTION_IMAGES[节号]
       - 失败 → 使用占位符（不降级）
    ```

    **IMAGE_SOURCE="web"（仅互联网下载）**：
    ```
    1. WebSearch 搜索图片页面
       - 查询词："{章节主题} {图片类型} diagram"

    2. 提取图片 URL
       - WebFetch 白名单页面 或 curl + grep 提取

    3. 下载图片
       - curl 下载到 /tmp/
       - 验证文件大小 > 5KB
       - 成功 → 记录到 SECTION_IMAGES[节号]
       - 失败 → 使用占位符（不降级）
    ```

    **IMAGE_SOURCE="placeholder"（仅占位符）**：
    ```
    直接为所有配额位置生成占位符
    记录到 SECTION_IMAGES[节号]
    ```

    **Step 4：统一记录格式**
    ```
    SECTION_IMAGES[节号] = [
      {
        index: 1,
        path: "/tmp/taw_ai_img_1.3_1.png",  # 真实图片路径或 null
        caption: "图 1.3-1：容器云平台总体架构",
        source: "AI生成",  # AI生成/知识库/互联网/占位符
        type: "architecture",
        status: "success"  # success/placeholder/failed
      },
      ...
    ]
    ```

    **Step 5：DOCX 写入**
    - 遍历 SECTION_IMAGES[节号]
    - 存在 path → 调用 add_picture_cn() 插入图片
    - path 为 null → 写入占位符文本："> [图片占位符 — {type}：{caption}，请在此处插入对应图片]"

    **重要约束**：
    - ❌ 任何模式下都不得用文字描述代替图片
    - ❌ 不得用纯文本段落模拟图表内容
    - ❌ 不得使用外部 URL 直接引用图片（必须下载到本地）
    - ✅ 显式指定模式失败时使用占位符，不隐式降级到其他方案
    - ✅ 所有章节统一走此配额流程，无特殊处理

    - **记录格式**：
      ```
      SECTION_IMAGES[节号] = [
        {
          index: 1,
          path: "/tmp/taw_ai_img_5.3_1.png",  # 真实图片路径或 null
          caption: "图 1.3-1：容器云平台总体架构",
          source: "AI生成",  # AI生成/知识库/互联网/占位符/AnythingLLM
          type: "architecture",
          status: "success"  # success/placeholder/failed
        },
        ...
      ]
      ```

    - **DOCX 写入**：
      - 遍历 SECTION_IMAGES[节号]
      - 存在 path → 调用 add_picture_cn() 插入图片
      - path 为 null → 写入占位符文本："> [图片占位符 — {type}：{caption}，请在此处插入对应图片]"

    - **进度提示中的图片信息**：
      ```
      [进度 3/8] ✅ 1.3 总体方案设计 — 2,200字，插图 2/2 张（实插 1 张 / 占位符 1 张）
      ```

2c. **长内容章节分段生成机制**（仅 USE_PARALLEL_WRITING=false 时执行；目标字数 ≥ WORD_OVERRIDE[2] 或 4,500 字且大纲无子节时触发）：
    - **检测条件**：章节目标字数 ≥ (WORD_OVERRIDE[2] 或 4,500) 字（如 1.3、1.4 等核心技术章节）**且** OUTLINE_SUBSECTIONS[章节号] 为空
    - **优先使用大纲子节**：若 OUTLINE_SUBSECTIONS 存在子节标题，直接以子节作为分段依据，不触发此机制
    - **拆分策略**（大纲无子节时）：基于 M2 技术要求和 M4 评分项，拆分为 3-5 个子主题
      - 示例（1.3 技术方案，默认字数）：
        1. 需求理解与行业背景（WORD_OVERRIDE[3] 或 900 字）
        2. 总体架构设计（1,200 字）
        3. 核心技术实现（1,500 字）
        4. 案例佐证（600 字）
        5. 预期效果（300 字）
    - **子主题生成模板**（每个子主题 WORD_OVERRIDE[3] 或 900-1,500 字）：
      - **需求理解**（300 字）：引用 M2 原文要求
      - **方案设计**（450 字）：技术路线和架构
      - **实现路径**（300 字）：具体实施步骤
      - **预期效果**（150 字）：量化指标
    - **质量检查**（每个子主题生成后）：
      - 检查字数是否达标（≥ WORD_OVERRIDE[3] 或 900 字）
      - 检查是否包含 WEB_FACTS 中的具体事实（≥ 2 条）
      - 检查是否覆盖对应评分点（M4）
      - 不达标 → 补充生成（追加 WORD_OVERRIDE[3]*0.3 ~ WORD_OVERRIDE[3]*0.7 或 300-600 字）
    - **失败处理**：
      - 若某个子主题生成失败（超时/错误）→ 标注 `[待补充：{子主题名}]`
      - 继续生成下一个子主题，不中断整体流程
      - 在最终输出中列出失败的子主题
    - **合并输出**：所有子主题合并为完整章节，保持逻辑连贯

2d. **大纲子节标题对齐（新增）**

    **核心原则**：生成内容的标题结构必须严格遵循大纲的子节结构。

    **执行流程**：
    1. **提取大纲子节标题**：
       - 从 Phase 1.1 Step 2 提取的 OUTLINE_SUBSECTIONS 中获取当前章节的子节标题列表
       - 例如：1.11 章节应获取到 ["培训计划与课程体系", "培训讲师资质", "培训效果评估"]

    2. **内容组织策略**：
       - **若大纲子节标题存在**（OUTLINE_SUBSECTIONS 非空）：
         * 必须使用这些标题作为内容标题，层级由 depth 字段决定（3→Heading 3, 4→Heading 4, 5→Heading 5）
         * 各层级子节字数：depth=3 → WORD_OVERRIDE[3] 或 900 字，depth=4 → WORD_OVERRIDE[4] 或 600 字，depth=5 → WORD_OVERRIDE[5] 或 400 字
         * 禁止使用自定义的"一、二、三"或"1. 2. 3."编号

       - **若大纲无子节标题**：
         * 使用 article_templates/*.yaml 中 section_type 的 content_elements
         * 每个 content_element 作为一个三级标题
         * 标题格式：去除括号内的说明文字，保留核心主题

    3. **标题层级规范**（支持最深至五级）：
       ```
       二级标题（Heading 2）：1.11 培训方案
         三级标题（Heading 3）：1.11.1 培训计划与课程体系
           四级标题（Heading 4）：1.11.1.1 基础培训课程
             五级标题（Heading 5）：1.11.1.1.1 线上课程安排
               正文段落...
         三级标题（Heading 3）：1.11.2 培训讲师资质
           正文段落...
       ```

    4. **DOCX 写入**（使用 depth 动态设置 heading level）：
       ```python
       # 二级标题
       add_heading_cn(doc, '1.11 培训方案', level=2)

       # 子标题 - 必须使用大纲子节标题，按 depth 设置层级
       subsections = OUTLINE_SUBSECTIONS.get('1.11', [])
       for sub in subsections:
           add_heading_cn(doc, f"{sub['numbering']} {sub['title']}", level=sub['depth'])
           # 生成该子节内容（字数根据 depth 确定：
           #   depth=3 → WORD_OVERRIDE[3] 或 900 字
           #   depth=4 → WORD_OVERRIDE[4] 或 600 字
           #   depth=5 → WORD_OVERRIDE[5] 或 400 字）
       ```

    **强制检查点**：
    - [ ] 生成内容前检查 OUTLINE_SUBSECTIONS 是否已提取
    - [ ] 确保子标题与大纲子节标题一一对应（编号和标题文字均一致）
    - [ ] 标题层级（level）必须与 depth 值一致
    - [ ] 禁止使用非大纲定义的标题结构

    **向后兼容性**：
    - 对于没有三级子节的大纲章节（如简单的偏离表），保持现有行为
    - content_elements 作为备选方案，仅在大纲无子节时使用
    - 不影响其他功能模块

3. 每节内容组织围绕 M4 评分标准，确保每个评分点有实质性响应
4. 融入 M7 差异化亮点和关键词

**多章节循环模式**（CHAPTERS_TO_WRITE 含多个章节时）：

- **全局知识复用**：
  - Phase 1.3 已填充 GLOBAL_KNOWLEDGE_POOL（产品信息、行业趋势、技术标准）
  - 每节写作前优先从池中提取相关知识
  - 不足时再执行 ≤ 2 次定向搜索，新知识补充到池中
  - 减少重复搜索，提高生成效率
- 所有章节**合并为单个 DOCX 文件**，章节间用分节符（`doc.add_section()`）分隔
- 文件命名：`<起始节>-<结束节>_合并.docx`（始终使用小数点格式，如 `1.1-1.9_合并.docx`，即使用户指定 `--chapter 一`）
- 每节完成后输出进度提示（含图片配额信息）：

```
[进度 2/11] ✅ 1.2 项目理解与需求分析 — 1,820字，插图 1/1 张（实插 0 / 占位符 1）[满足]
[进度 3/11] 正在撰写 1.3 总体方案设计...（配额 2 张）
```

**图片插入步骤（每节文字写完后执行）**：

对 `MATCHED_IMAGES` 中属于当前章节的图片：
- 调用 `add_picture_cn(doc, image['file'], image['caption'], image['width_cm'])`

对 `PLACEHOLDER_IMAGES` 中属于当前章节的图片：
- 调用 `write_markdown(doc, '> [图片占位符 — ' + caption + '：请在此处插入对应图片]')`

进度提示中新增图片数（有图片时）：
```
[进度 3/8] ✅ 1.3 总体方案设计 — 2,200字，插图 1 张（已写入合并文件）
```

**单章节模式**：行为同原有逻辑，输出 `<节号>_<节名>.docx`，无进度提示。

### 内容组织原则

- **评分导向**：高分值项（≥10分）重点展开 ≥ 1,500字，低分值项（<5分）简明响应
- **M7 驱动**：M7 撰写优先级决定内容深度，P1 最详尽，P3 简明
- **数据支撑**：尽可能用量化数据（性能指标、案例规模、认证数量）支撑论述
- **差异化突出**：M7.4 差异化亮点在对应章节显著位置展现
- **红线规避**：M5 废标条款和 M7.5 红线在内容中不得违反

**篇幅要求（标书写作规范）**：
- 每个三级子节（X.X.X 级）正文不少于 WORD_OVERRIDE[3] 或 900 字
- 每个四级子节（X.X.X.X 级）正文不少于 WORD_OVERRIDE[4] 或 600 字
- 每个五级子节（X.X.X.X.X 级）正文不少于 WORD_OVERRIDE[5] 或 400 字
- 二级节（X.X 级）完整内容不少于 WORD_OVERRIDE[2] 或模板 word_count
- 重点章节（1.3 总体方案设计、1.4 专项响应）不少于 WORD_OVERRIDE[2] 或 4,500 字/节
- 内容组织要求：
  • 每个论点下至少 3-5 个具体支撑子要点
  • 优先使用数字、技术参数、案例规模量化描述
  • 避免单句论断，每个功能/方案至少展开"需求响应→方案设计→实现路径→预期效果"四段
  • 表格优先：技术要求响应、功能对比、里程碑计划等用表格呈现

---

## Phase 2.5：执行阶段自检（新增）

在 Phase 2 每节内容生成完成后、写入 DOCX 前，强制执行以下自检：

### 2.5.1 内容格式自检

```python
# 在生成内容后、写入 DOCX 前执行
if '**' in content or '__' in content or '`' in content:
    print("⚠️ 内容包含 Markdown 标记，确认使用 write_markdown() 写入")

# 检查是否使用了 write_markdown
# 如果代码中使用的是 add_para_cn() → 必须修改为 write_markdown()
```

**检查点**：
- [ ] 生成的内容字符串包含 Markdown 标记（`**`、`*`、`` ` ``、`- `、`1. `、`|`）
- [ ] 确认使用 `write_markdown()` 而非 `add_para_cn()` 写入
- [ ] 检查未通过 → 修改代码 → 重新生成

### 2.5.2 图片获取自检

```python
# 检查 SECTION_IMAGES 是否已记录
if chapter not in SECTION_IMAGES:
    print("[错误] SECTION_IMAGES 未记录，返回 Phase 2 Step 2b 重新执行")

# 检查图片是否已记录到 SECTION_IMAGES
actual_images = [img for img in SECTION_IMAGES.get(chapter, []) if img['status'] in ['success', 'placeholder']]
h3_with_images = len(actual_images)
print(f"[图片自检] 章节 {chapter}：{h3_with_images} 张图片已分配")
```

**检查点**：
- [ ] SECTION_IMAGES[节号] 存在且有记录
- [ ] SECTION_IMAGES 中有对应的图片记录
- [ ] 图片分布在不同 H3 子节中（无重复使用同一图片）
- [ ] 每张图片有正确的 source 和 status 标注

### 2.5.3 大纲对齐自检

```python
# 验证子标题与大纲子节一一对应（支持多级标题）
if OUTLINE_SUBSECTIONS.get(chapter):
    subs = OUTLINE_SUBSECTIONS[chapter]
    expected_count = len(subs)
    depth_counts = {}
    for s in subs:
        depth_counts[s['depth']] = depth_counts.get(s['depth'], 0) + 1
    print(f"✅ 大纲子节对齐检查：期望 {expected_count} 个子标题")
    for d, c in sorted(depth_counts.items()):
        print(f"   - {d}级标题：{c} 个")
```

**检查点**：
- [ ] OUTLINE_SUBSECTIONS 已提取
- [ ] 生成内容使用大纲子节作为子标题（层级由 depth 决定）
- [ ] 每个子标题的 heading level 与 depth 值一致

### 2.5.4 知识库使用自检

```python
# 验证知识库检索结果
kb_total = anythingllm_count + fixed_count + reusable_count + history_count
if kb_total == 0 and NO_KB_FLAG == false:
    print("⚠️ 知识库未命中任何内容，检查 Phase 1.3 执行")
```

**检查点**：
- [ ] 至少一种知识库来源有命中（AnythingLLM/本地YAML）
- [ ] 或明确标注 `--kb-source none` 进入互联网模式
- [ ] 或使用 `--kb-source local` 强制本地 KB 目录索引模式

### 2.5.5 并行写作一致性自检（仅 USE_PARALLEL_WRITING=true 时执行）

**检查点**：
- [ ] **术语一致性**：扫描全文，确认无禁用变体残留（对照 Writing Brief 术语表）
- [ ] **无重复论述**：检查是否有多个 H3 子节包含高度相似的段落（>80% 重叠），如有则标记
- [ ] **过渡质量**：相邻 H3 之间有自然衔接，无突兀跳转
- [ ] **论述主线连贯**：全文论证逻辑与 Writing Brief 论述主线一致，未出现偏离
- [ ] **评分覆盖完整**：所有 M4 评分项在合并后的内容中有实质性响应

```
[并行写作自检] 章节 {章节号}
- 术语一致性：✅/⚠️（{违规数} 处已替换）
- 重复论述：✅/⚠️（{重复数} 处已精简）
- 过渡质量：✅/⚠️（{补充数} 处已衔接）
- 评分覆盖：{已覆盖}/{总数} 项
```

---

## Phase 3：质量自检与输出

### 3.1 质量自检

完成章节撰写后，执行以下自检项（基础检查，深度审核由 trv 负责）：

| 自检项 | 检查内容 | 通过标准 |
|--------|---------|---------|
| 评分覆盖度 | M4 相关评分点是否全部有实质性响应 | 覆盖率 100% |
| 关键词覆盖率 | M7 关键词清单中的词汇是否在对应章节出现 | 覆盖率 ≥ 80% |
| 废标红线 | M5 废标条款和 M7.5 红线是否未触犯 | 零违反 |
| 过度承诺 | 是否存在绝对化措辞 | 零过度承诺 |
| 待确认标注 | 无知识库支撑的内容是否标注 `[待确认]` | 全部标注 |

### 3.2 自检结果输出

```
─────────────────────────────────────
质量自检结果：
• 评分覆盖度：[X/Y] 项（[%]）
• 关键词覆盖率：[X/Y] 个（[%]）
• **图片分配达成**：[实际]/[目标] 张（实插 [Y] 张 / 占位符 [Z] 张）
  - 分配模式：H3 粒度（[N] 个 H3 分配 [M] 张）或静态配额（[quota] 张）
  - 实际生成：[Y] 张实图 + [Z] 张占位符
  - 状态：[满足 / 图片数量不足]
• 废标红线：✅ 未触犯 / ⚠️ [说明]
• 过度承诺：✅ 未发现 / ⚠️ [N] 处需修改
• 待确认事项：[N] 项
─────────────────────────────────────
```

**图片分配检查逻辑**：
- H3 粒度模式：检查每个 allocate=1 的 H3 是否有对应图片（实图或占位符）
- 静态配额模式：检查 实图数 + 占位符数 >= required
- 不足时提示具体缺少哪些 H3 子节的图片

**⚠️ 执行验证检查点（Phase 2 完成后必须确认）**：

1. **Markdown 渲染验证**：
   - [ ] 检查生成的 DOCX 中是否存在 `**`、`__`、`` ` `` 等原始 Markdown 标记
   - [ ] 若存在 → 说明使用了 `add_para_cn()` 而非 `write_markdown()`，必须修正
   - [ ] 检查表格是否正确渲染为 Word 表格（非文本模拟）

2. **知识库使用验证**：
   - [ ] 确认 Phase 1.4 输出中显示了知识库来源统计
   - [ ] 确认 KB 目录索引或 AnythingLLM 至少有一项显示结果数（非 "⚠️ 未使用"）
   - [ ] 确认内容中包含知识库来源标注（`[来源：知识库，参考使用]` 等）

3. **图片生成验证**：
   - [ ] 确认 SECTION_IMAGES[节号] 中有记录
   - [ ] 确认图片数量 >= required（最少要求）
   - [ ] 确认每张图片有正确的 source 标注（AI生成/知识库/互联网/占位符）
   - [ ] 确认 DOCX 中图片位置正确（标题后或内容中）
   - [ ] 确认图片有标题说明（"图 X.X-X：..."）
   - [ ] 对于 technical_core/implementation/training_service 等 required>=1 的章节，确认至少 1 张实图或占位符

4. **字数验证**：
   - [ ] 统计实际生成字数，确认达到目标字数要求（WORD_OVERRIDE[2] 或模板 word_count）
   - [ ] 技术章节（≥ WORD_OVERRIDE[2] 或 4,500字）：确认触发分段生成机制
   - [ ] 各层级子节字数：三级 ≥ WORD_OVERRIDE[3] 或 900 字，四级 ≥ WORD_OVERRIDE[4] 或 600 字，五级 ≥ WORD_OVERRIDE[5] 或 400 字
   - [ ] 若字数不足 → 补充生成

5. **来源标注验证**：
   - [ ] 确认互联网数据标注了 `[互联网来源，请核实]` 或 `[Tavily来源，请核实]` 等
   - [ ] 确认无知识库支撑的内容标注了 `[待确认]`

**若以上任何检查项未通过，必须返回对应 Phase 重新执行，禁止直接输出文件。**

### 3.3 文件输出

将章节草稿以 DOCX 格式输出，文件命名遵循 `docs/data-format.md` 第5节：

- **文件名**：`<章节号>_<章节名>.docx`（如 `五_技术部分.docx`、`5.3_总体方案设计.docx`）
- **格式**：使用 python-docx 生成，字体规范与 taa 一致

**DOCX 生成**：

使用 Read 工具读取 `$SKILL_DIR/tools/docx_writer.py`，获取所有 DOCX 生成函数。

> **关键规则**：
> - **禁止**直接使用 `doc.add_heading()` / `doc.add_paragraph()`
> - **必须**通过 `add_heading_cn()` / `write_markdown()` 创建所有标题和段落
> - 所有字符串参数必须用**单引号** `'...'`，禁止双引号（中文引号会触发 SyntaxError）

**核心函数**（定义在 `docx_writer.py` 中）：
- `create_document()` — 创建预配置的 A4 文档（字体/页边距已设置）
- `write_markdown(doc, md_text)` — 将 Markdown 渲染为 DOCX（支持标题/列表/表格/粗体/斜体/代码）
- `add_heading_cn(doc, text, level)` — 添加中文标题
- `add_picture_cn(doc, img_path, caption)` — 插入图片（不存在时自动降级为占位符）

**用法示例**（用 bash heredoc 包装，确保 $SKILL_DIR 被 bash 展开后传给 Python 环境）：
```bash
SKILL_DIR="$SKILL_DIR" python3 <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ['SKILL_DIR'], 'tools'))
from docx_writer import create_document, write_markdown, add_heading_cn, add_picture_cn

doc = create_document()
add_heading_cn(doc, '1.3 总体方案设计', level=2)
write_markdown(doc, '正文内容（支持 **粗体**、*斜体*、`代码`、- 列表、| 表格 |）')
add_picture_cn(doc, '/path/to/image.png', '图 1：系统架构图')
doc.save('./drafts/1.3_总体方案设计.docx')
PY
```

**文件交付**：

```bash
mkdir -p ./drafts
# 生成 DOCX 文件
# → ./drafts/<章节号>_<章节名>.docx
```

### 3.4 任务完成确认

**单章节模式**：
```
✅ 章节撰写完成！
1. [章节号]_[章节名].docx — [X] 字
   • 覆盖评分项：[N] 个
   • 引用案例/资料：[N] 条
   • 插图统计：实插 N 张 / 占位符 M 张
   • 待确认事项：[N] 项

建议后续操作：
• /trv <草稿文件> --type chapter --reference <分析报告> — 章节深度审核
• /taw --outline <大纲> --report <分析报告> --chapter <下一章节> — 继续撰写下一章节
```

**多章节模式**：
```
✅ 批量撰写完成！
• 输出文件：<起始节>-<结束节>_合并.docx
• 共 [N] 个章节，合计 [X] 字
• 插图统计：实插 N 张 / 占位符 M 张
• 章节明细：
  1. [章节号] [章节名] — [X] 字，待确认 [N] 项
  2. [章节号] [章节名] — [X] 字，待确认 [N] 项
  ...

建议后续：/trv drafts/<起始节>-<结束节>_合并.docx --type chapter --reference <分析报告>
```

---

## 章节类型与写作策略

### 一、技术部分（taw 核心，重点生成）

| 子章节 | 重点内容 | 知识库检索 | 关键输入 |
|--------|---------|-----------|---------|
| 1.1 技术偏离表 | 逐条对应 M2 技术要求，标注正偏离/无偏离 | 不检索 | M2 全部技术要求 |
| 1.2 项目理解与需求分析 | 体现对招标需求的深度理解，分析现状与痛点 | 不检索 | M1 项目概况 + M2 技术要求 |
| 1.3 总体方案设计 | 架构设计、技术路线，突出{VENDOR_NAME}核心产品能力 | solutions | M2 技术要求 + M4 技术评分项 + M7 亮点 |
| 1.4 专项响应章节 | 与大纲动态章节一一对应，针对性技术方案 | solutions + cases | M2【必须】条款 + M4 高分评分项 |
| 1.5 实施方案与计划 | 里程碑与 M3 工期要求一致，资源投入计划 | cases | M3 交付要求 |
| 1.6 质量保障方案 | 质量管理体系、测试策略 | 不检索 | M3 验收标准 |
| 1.7 安全方案 | 安全架构、等保合规 | solutions | M2 安全要求 + 行业扩展模块 |
| 1.8 国产化适配方案 | 信创适配（如有信创要求） | solutions | M2 国产化要求 + 行业扩展 E2 |
| 1.9 项目团队与人员配置 | 团队架构、核心岗位职责 | 不检索 | M3 人员要求 |
| 1.10 售后服务方案 | 质保/运维/响应/增值服务 | solutions | M3 质保运维要求 + M4 服务评分项 + M7 差异化亮点 |
| 1.11 培训方案 | 培训计划、内容、方式、考核 | 不检索 | M3 培训要求 + M4 培训评分项 |

**写作规则**：
- 专业深入、方案导向
- M7 差异化亮点在对应章节显著位置融入
- M2【必须】条款须有明确的技术响应方案
- 架构设计需体现{VENDOR_NAME} 核心产品能力（产品名/特性从 WebSearch 或知识库获取）
- 性能指标、技术参数引用 M2 原文要求，响应方案给出具体数值
- 每个评分子项有对应内容段落
- 1.10 售后服务方案：务实可信、承诺可执行，SLA 和响应时间标注 `[待商务确认]`，与 M3 质保/运维要求逐条呼应
- 1.11 培训方案：培训计划须覆盖内容/方式/考核，与 M3 培训要求对应

---

## [DEPRECATED] 知识库检索策略（旧版 cases.yaml/solutions.yaml）

> ⚠️ 已废弃：v3.0 起使用 Local-KnowledgeBase Markdown 图文一体化检索（见 Phase 1.3）。
> 以下内容仅供历史参考，不再被主流程引用。

---

## 过度承诺防范规则

### 禁用措辞

以下绝对化措辞**禁止使用**：
- 保证、确保100%、绝对、承诺必定、保障万无一失

### 替代措辞

| 禁用 | 替代 |
|------|------|
| 保证达到 | 预期可达到 / 目标为 |
| 确保100% | 力争实现 / 设计目标为 |
| 绝对安全 | 多层防护，最大程度保障安全 |
| 承诺必定完成 | 制定详细计划确保按期推进 |

### 标注规则

- 无知识库支撑的技术能力描述：标注 `[待确认]`
- 资源承诺（人员数量、设备配置）：标注 `[待商务确认]`
- 量化性能指标（无实测数据支撑）：标注 `[待技术确认]`

---

## 全局约束

1. **评分导向**：所有内容组织围绕 M4 评分标准，确保每个评分点有实质性响应
2. **M7 驱动**：M7 撰写指导是最核心的写作指南，关键词、策略、亮点必须融入
3. **禁止臆测**：所有数字（金额/日期/参数）必须来自招标文件或知识库，缺失标注 `[待确认]`
4. **出处可溯**：技术参数引用须对应 M2 原文
5. **项目特定性**：内容必须针对本项目，禁止通用模板语句
6. **中文排版规范**：使用中文标点，数字用阿拉伯数字，章节编号遵循大纲体系
7. **与 taa 解耦**：taw 通过读取 taa 的 Markdown/DOCX 产出物工作，不直接调用 taa 代码
8. **基础自检**：taw 执行基础质量检查（覆盖度/关键词/红线），深度审核由 trv 负责
9. **互联网检索兜底**：知识库为空或当前章节无匹配时，主动通过 WebSearch/MCP 工具检索相关技术资料，结合项目上下文写作
10. **来源标注规范**：来自互联网的具体数据（数字/指标）标注 `[互联网来源，请核实]` 或 `[MCP来源，请核实]`，通用技术描述无需逐句标注，不得照搬原文
