---
name: twc
description: >
  当用户说"配置工作流"、"配置 tender"、"设置配置"时触发，也可通过 /twc 手动调用。
  管理 tender-workflow 统一配置文件（~/.config/tender-workflow/config.yaml）。
  支持交互式初始配置（setup）、查看（show）、修改（set）、验证（validate）、旧配置迁移（migrate）、
  列出 AI 生图模型（models）、重置（reset）等子命令。
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob
---

# twc — Tender Workflow 配置管理

当用户说"配置工作流"、"配置 tender"、"设置配置"时触发，也可通过 /twc 手动调用。
管理 tender-workflow 统一配置文件（`~/.config/tender-workflow/config.yaml`）。
支持交互式初始配置、查看、设置、验证、旧配置迁移。

## 参数

```
/twc [子命令] [参数]

子命令（默认 setup）：
  setup              交互式首次配置向导（完整流程）
  show [skill]       显示当前生效配置（可选指定 skill: taa/taw/tpl/trv）
  set <key> <value>  设置配置项（支持 dot notation，如 localkb.path）
  models [provider]  列出所有可用的 AI 图片生成模型（可选过滤: ark/dashscope/gemini）
  models --refresh   联网查询各供应商最新模型，更新本地注册表
  validate           健康检查（路径、API 连通性、工具安装）
  migrate            迁移旧 per-skill 配置并删除旧文件
  reset              重置为默认值（确认后删除配置文件）
```

## 配置文件

**唯一路径**：`~/.config/tender-workflow/config.yaml`

旧路径 `~/.config/taw/config.yaml` 和 `~/.config/taa/config.yaml` 已废弃。
使用 `/twc migrate` 可将旧配置合并到统一文件并删除旧文件。

**完整 Schema**：
```yaml
# 全局共享
localkb:
  path: /path/to/local-knowledgebase  # 知识库根目录

anythingllm:
  enabled: true/false
  base_url: "http://localhost:3001"
  workspace: <slug-or-uuid>           # 全局默认 workspace

api_keys:
  ark: <火山方舟 API Key>
  dashscope: <阿里云 API Key>
  gemini: <Google Gemini API Key>

ai_image:
  default_provider: ark                    # 默认 AI 生图供应商（ark/dashscope/gemini）
  size: 2048x2048
  max_retries: 2
  timeout: 60
  models:
    ark: doubao-seedream-5-0-260128       # 可通过 /twc models 查看全部可选模型
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image

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

配置读写通过 `tools/tw_config.py` 执行：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py show [skill]          # 显示配置
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py get <skill> <key>     # 获取单个值
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set <key> <value>     # 设置值
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py models [provider]     # 列出 AI 生图模型
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py validate              # 验证
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py migrate               # 迁移旧配置
python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py normalize             # 规范化 schema
```

## 执行流程

### /twc show [skill]

1. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py show [skill]`
2. 将输出格式化为表格展示给用户

### /twc set \<key\> \<value\>

1. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set <key> <value>`
2. 显示变更确认

### /twc models [provider]

1. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py models [provider]`
2. 将输出的 Markdown 表格直接展示给用户（固定格式，数据来自 ai-image plugin 的 ai_image_models.yaml（由 tw_config.py 自动定位））
3. 表格中标记当前配置的默认模型（`←`）
4. 底部显示如何更改默认模型的命令提示
5. 若注册表 `last_updated` 距今超过 90 天，底部自动显示过期警告

### /twc models --refresh

> ⚠ **`--refresh` 子命令尚未实现（F-047）** — 当前仅展示注册表内容（`/twc models` 不带 --refresh 即可）。后续版本将加入"联网搜索 → AI 对比 → 用户确认 → 更新 yaml" 逻辑。下文为已规划的执行流程参考，目前 tw_config.py 不响应该 flag。

联网查询各供应商最新的 AI 图片生成模型，与本地注册表对比后更新。

**执行流程**：

1. 读取当前注册表 ai-image plugin 的 ai_image_models.yaml（由 tw_config.py 自动定位），记录现有模型列表
2. 对每个供应商**并行**联网搜索最新可用的图片生成模型：
   - **火山方舟**：搜索"火山方舟 Seedream 图片生成模型 最新"或查阅火山方舟官方文档
   - **阿里云 DashScope**：搜索"阿里云 通义万相 DashScope 图片生成模型 最新"或查阅阿里云官方文档
   - **Google Gemini**：搜索"Google Gemini image generation models latest"或查阅 Google AI 官方文档
3. 对比搜索结果与当前注册表，识别差异：
   - **新增模型**：搜索结果中有但注册表中没有的模型
   - **已下线模型**：注册表中标记为 available 但已确认下线的模型（改为 deprecated）
   - **信息变更**：价格、分辨率、名称等字段有更新
4. 向用户展示变更摘要（表格格式）：
   ```
   ## 模型注册表更新摘要
   
   | 变更类型 | 供应商 | 模型 ID | 说明 |
   |---------|--------|---------|------|
   | 新增 | Google Gemini | gemini-xxx | ... |
   | 下线 | 阿里云 | xxx | 官方已停止服务 |
   | 更新 | 火山方舟 | xxx | 价格调整: ¥0.20→¥0.15 |
   ```
5. 询问用户确认是否应用变更
6. 用户确认后：
   a. 更新 ai-image plugin 的 ai_image_models.yaml（由 tw_config.py 自动定位）（保持现有格式不变）
   b. 更新 `last_updated` 为当日日期
   c. 更新 `version` 递增 patch 版本号
7. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py models` 展示更新后的完整表格

**注意事项**：
- 搜索结果需交叉验证（至少两个来源确认），避免误将不存在的模型写入注册表
- 不自动变更用户已配置的默认模型（`ai_image.models.*`），仅更新注册表
- 若某供应商搜索失败，跳过该供应商并告知用户，不影响其他供应商的更新

### /twc validate

1. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py validate`
2. 对每个问题给出修复建议

### /twc migrate

1. 检查旧配置文件是否存在：
   - `~/.config/taw/config.yaml`
   - `~/.config/taa/config.yaml`
2. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py migrate`
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

### /twc setup（交互式配置向导）

分 7 步交互式引导用户完成完整配置。每步完成后立即写入配置文件。

#### 前置检测：Node.js 环境

Step 2（AnythingLLM）和 Step 4（MCP 搜索工具）依赖 Node.js（`node`/`npx`）。
在进入 Step 1 之前，先检测 Node.js 是否可用：

```python
python3 -c "import shutil; n=shutil.which('node'); print(f'node: {n}') if n else print('node: NOT_FOUND')"
```

- 若已安装 → 显示路径，继续
- 若未安装 → 检测平台和包管理器，自动安装：
  ```python
  python3 -c "
  import sys, shutil
  p = sys.platform
  if p == 'darwin':
      pm = 'brew install node' if shutil.which('brew') else None
  elif p == 'win32':
      pm = 'winget install OpenJS.NodeJS.LTS' if shutil.which('winget') else None
  else:  # linux
      if shutil.which('apt'): pm = 'sudo apt install -y nodejs npm'
      elif shutil.which('dnf'): pm = 'sudo dnf install -y nodejs npm'
      elif shutil.which('yum'): pm = 'sudo yum install -y nodejs npm'
      else: pm = None
  print(f'INSTALL_CMD: {pm}' if pm else 'NO_PACKAGE_MANAGER')
  "
  ```
  - 若检测到包管理器 → 执行对应安装命令
  - 若无可用包管理器 → 提示用户：`"请从 https://nodejs.org/ 下载安装 Node.js"`
  - 安装失败或用户跳过 → 跳过依赖 Node.js 的步骤（Step 2 AnythingLLM、Step 4 MCP 搜索工具）
- 安装完成后验证：`node --version && npm --version`

#### Step 1：知识库目录

知识库目录包含公司技术文档（Markdown 格式）。
目录名称和位置不固定，可在项目内或外部（如 OneDrive 同步目录）。

1. 读取已有配置 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py get global localkb.path`
2. 若已有配置且路径存在：
   - 告知用户"当前知识库目录：<路径>"，询问是否保留
   - 用户确认 → 跳到步骤 5
   - 用户拒绝 → 转到步骤 3
3. 提示用户输入知识库目录的完整路径
4. 验证路径存在
5. 检查 `<路径>/.index/` 是否存在
   - 若不存在 → 提示：索引尚未生成，建议运行 `/taw --build-kb-index` 构建
6. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set localkb.path <路径>`

#### Step 2：AnythingLLM 配置

1. 询问用户是否需要配置 AnythingLLM 语义检索（推荐）
2. 若用户选择"否" → 设置 `anythingllm.enabled: false`，跳到 Step 3
3. 若选择"是"：
   a. 检查 `anythingllm-mcp` plugin 是否已装：
      ```bash
      ls ~/.claude/plugins/cache/presales-skills/anythingllm-mcp/ 2>/dev/null || \
        echo "MISSING: anythingllm-mcp plugin 未安装，请先执行 /plugin install anythingllm-mcp@presales-skills 然后 /reload-plugins"
      ```
      若未装，提示用户安装后再继续 Step 2。
   b. 通过 AskUserQuestion 一次性收集全部信息：
      - **AnythingLLM Base URL**（默认 `http://localhost:3001`）
      - **API Key**（必填）
      - **Workspace slug 或 UUID**（必填，用户可从 AnythingLLM 界面获取）
   c. 写入统一配置（MCP server 会在启动时从这里读取凭据）：
      ```bash
      python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set anythingllm.enabled true
      python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set anythingllm.workspace <workspace>
      python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set anythingllm.base_url <url>
      python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set anythingllm.api_key <key>
      ```
   d. 提示用户：配置完成。MCP server 由 `anythingllm-mcp` plugin 自动注册（plugin.json 的 `mcpServers` 字段），无需手工改 `~/.claude.json`；下次 Claude Code 启动或 `/reload-plugins` 后生效。

#### Step 3：draw.io plugin 安装检测

drawio 现已从 tender-workflow 独立成 `presales-skills` marketplace 内的 shared plugin。用户通常与 tender-workflow 同时通过 umbrella marketplace 安装。

1. 检查 drawio plugin 是否已随 umbrella marketplace 安装：
   ```bash
   # drawio plugin 安装后会往 PATH 注入 drawio-gen 包装脚本。
   # 用 command -v 检测比尝试路径更可靠——对 local / remote marketplace 两种布局都有效
   command -v drawio-gen >/dev/null 2>&1 && echo "INSTALLED: drawio plugin" || echo "NOT_INSTALLED"
   ```
2. 若已安装：
   - 显示"drawio plugin 已随 presales-skills marketplace 安装"
   - 检测 draw.io Desktop CLI 路径：
     ```python
     python3 -c "
     import shutil, sys
     from pathlib import Path
     import os
     candidates = [shutil.which('draw.io'), shutil.which('drawio-cli')]
     if sys.platform == 'darwin':
         candidates.append('/Applications/draw.io.app/Contents/MacOS/draw.io')
     elif sys.platform == 'win32':
         candidates.append(str(Path.home() / 'AppData/Local/Programs/draw.io/draw.io.exe'))
         candidates.append(os.environ.get('PROGRAMFILES', 'C:/Program Files') + '/draw.io/draw.io.exe')
     path = next((c for c in candidates if c and Path(c).exists()), None)
     print(f'CLI: {path}' if path else 'CLI: NOT_FOUND')
     "
     ```
   - 若检测到 → 设置 `drawio.cli_path`
   - 若未检测到 → 提示：draw.io Desktop / drawio-cli 未安装，导出功能不可用（drawio plugin 仍可生成 .drawio 文件）。安装命令：
     - macOS: `brew install --cask drawio`
     - npm:   `npm install -g @drawio/drawio-desktop-cli`
3. 若未安装：
   - 提示用户：drawio plugin 未安装，请在 Claude Code 里执行：
     ```
     /plugin install drawio@presales-skills
     ```
   - 若 marketplace `presales-skills` 尚未注册，先 `/plugin marketplace add Alauda-io/presales-skills`（远程订阅）或本地路径 `/plugin marketplace add /path/to/presales-skills`
   - 安装后 `/reload-plugins` 生效，随后 setup 可返回此步继续检测

#### Step 4：MCP 搜索工具配置（可选）

taw 撰写章节时可通过 MCP 搜索工具（tavily_search、exa_search）从互联网补充内容。

1. 检测当前可用的 MCP 搜索工具：
   ```python
   python3 -c "
   import json
   from pathlib import Path
   p = Path.home() / '.claude.json'
   c = json.loads(p.read_text()) if p.exists() else {}
   servers = c.get('mcpServers', {})
   print('tavily:', any('tavily' in k.lower() for k in servers))
   print('exa:', any('exa' in k.lower() for k in servers))
   "
   ```
2. 展示检测结果：
   - 若 tavily 已配置 → 显示 `✅ tavily_search 已配置`
   - 若 exa 已配置 → 显示 `✅ exa_search 已配置`
   - 若均未配置 → 显示 `⚠️ 未检测到 MCP 搜索工具。taw 将仅使用内置 WebSearch，搜索质量可能受限。`
3. 若有未配置的工具，询问用户是否需要配置（可多选 Tavily / Exa / 跳过）：
   - 若用户选择配置某个工具 → 通过 AskUserQuestion 收集对应的 API Key：
     - **Tavily Search**：需要 TAVILY_API_KEY（从 https://tavily.com 获取）
     - **Exa Search**：需要 EXA_API_KEY（从 https://exa.ai 获取）
   - 收集完 API Key 后，**自动写入** `~/.claude.json` 的 `mcpServers`：
     ```python
     python3 -c "
     import json
     from pathlib import Path
     p = Path.home() / '.claude.json'
     c = json.loads(p.read_text()) if p.exists() else {}
     c.setdefault('mcpServers', {})
     # 根据用户选择写入对应配置（以下为示例，实际根据用户选择的工具执行）
     c['mcpServers']['tavily'] = {
       'command': 'npx',
       'args': ['-y', 'tavily-mcp@latest'],
       'env': {'TAVILY_API_KEY': '<用户输入的key>'}
     }
     c['mcpServers']['exa'] = {
       'command': 'npx',
       'args': ['-y', 'exa-mcp-server@latest'],
       'env': {'EXA_API_KEY': '<用户输入的key>'}
     }
     p.write_text(json.dumps(c, indent=2, ensure_ascii=False))
     print('MCP 搜索工具配置已写入 ~/.claude.json')
     "
     ```
   - 写入成功后显示确认信息，提示需在 setup 全部完成后**重启 Claude Code** 以加载
4. 设置搜索工具优先级：
   - 若两个都配置了 → 询问优先顺序（默认 `[tavily_search, exa_search]`）
   - 若只配置了一个 → 自动设置该工具为唯一优先
   - 写入示例：
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set mcp_search.priority '["tavily_search", "exa_search"]'
     # 或仅配置了一个：
     python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set mcp_search.priority '["tavily_search"]'
     ```
5. 若用户选择全部跳过 → 保持默认值，提示后续可通过 `/twc set mcp_search.priority [...]` 修改

#### Step 5：AI 生图 API Key（可选）

1. 询问用户是否配置 AI 生图功能（可选，用于生成架构图等）
2. 若选择"否" → 跳到 Step 6（Skill 默认值）
3. 若选择"是"：
   a. **火山方舟 API Key**（推荐）：
      - 检查环境变量 `ARK_API_KEY` 是否已设置
      - 若已设置 → 显示"已通过环境变量配置"，询问是否同时写入配置文件
      - 若未设置 → 引导用户输入 API Key
      - 写入：`python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set api_keys.ark <key>`
   b. **阿里云 DashScope API Key**（备选）：
      - 同上逻辑，检查 `DASHSCOPE_API_KEY`
      - 写入：`python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set api_keys.dashscope <key>`
   c. **Google Gemini API Key**（可选）：
      - 检查环境变量 `GEMINI_API_KEY` 是否已设置
      - 若已设置 → 显示"已通过环境变量配置"，询问是否同时写入配置文件
      - 若未设置 → 引导用户输入 API Key（需安装 `pip install google-genai`）
      - 写入：`python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set api_keys.gemini <key>`
   d. 选择默认 AI 生图供应商：
      - 仅配置了一个 API Key → 自动设为默认
      - 配置了多个 API Key → 通过 AskUserQuestion 让用户选择一个作为默认
      - 写入：`python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set ai_image.default_provider <供应商>`

#### Step 6：Skill 默认值（可选）

1. **taa 厂商名**：
   - 当前默认"灵雀云"，询问是否修改
   - 若修改 → `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set taa.vendor <名称>`

2. **tpl 默认模板**：
   - 显示可选模板：government / finance / soe / enterprise
   - 询问是否设置默认模板（设置后 /tpl 可省略 --template 参数）
   - 若设置 → `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py set tpl.default_template <模板>`

3. **tpl 默认细致程度**：
   - 显示可选级别：detailed / standard / general / brief
   - 当前默认 standard，询问是否修改

#### Step 7：写入配置并验证

1. 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py validate`
2. 显示配置摘要表格（调用 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py show`）
3. 若存在旧配置文件：
   ```python
   python3 -c "from pathlib import Path; taw=Path.home()/'.config/taw/config.yaml'; taa=Path.home()/'.config/taa/config.yaml'; print(f'taw: {taw.exists()}, taa: {taa.exists()}')"
   ```
   - 若存在 → 询问是否迁移删除（推荐）
   - 若确认 → 执行 `python3 ${CLAUDE_PLUGIN_ROOT}/tools/tw_config.py migrate`
4. 若 setup 过程中新增了 MCP Server（AnythingLLM / Tavily / Exa），在完成提示中**统一提醒**重启：
   ```
   配置完成！配置文件保存在：~/.config/tender-workflow/config.yaml
   
   ⚠️ 本次安装了新的 MCP Server，请重启 Claude Code 以加载。
   
   后续可通过以下命令管理配置：
     /twc show          查看当前配置
     /twc set <k> <v>   修改配置项
     /twc validate      健康检查
   ```
   若未新增 MCP Server，则不显示重启提醒。
