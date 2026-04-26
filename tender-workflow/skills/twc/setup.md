# tender-workflow twc 配置 wizard

> 触发自 tender-workflow twc SKILL.md 的 §配置 段。本文件由 Claude 在用户说「配置工作流 / 配置 tender / 配置 tender-workflow / 设置配置 / setup tender」时 Read 加载。
>
> **关键纪律**：每次都 Read 当前版本 — 不要凭记忆执行。

## 步骤 0.5：依赖前置检查

### A. Python ≥ 3.10（必需）

参照 ai-image setup.md §0.5 §A 段（检测 + 非 sudo 自动 / 需 sudo 打印 + 用户许可）。简版检测命令：

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || py -3 --version 2>/dev/null
```

未通过时按 ai-image setup.md 同款"依赖安装引导"流程。

### B. Node.js ≥ 22（仅启用 AnythingLLM 或 CDP 时必需，按需触发）

如果用户在后续步骤启用 anythingllm 或 mcp_search，本步骤再触发——参照 web-access setup.md §0.5 段。

---

### /twc setup（交互式配置向导）

> **AI 生图配置由 ai-image plugin 管理**：API keys、默认 provider、默认模型请通过 ai-image SKILL（自然语言"配置 ai-image / 我刚装新版需要初始化"）或直接 `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup` 配置——`setup` 含 auto-migrate 兜底。本命令仅引导 tender-workflow 专属项（localkb / anythingllm / drawio / mcp_search / skill 默认值）。

分 6 步交互式引导用户完成 tender-workflow 配置。每步完成后立即写入配置文件。

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

1. 读取已有配置 `python3 $SKILL_DIR/../tools/tw_config.py get global localkb.path`
2. 若已有配置且路径存在：
   - 告知用户"当前知识库目录：<路径>"，询问是否保留
   - 用户确认 → 跳到步骤 5
   - 用户拒绝 → 转到步骤 3
3. 提示用户输入知识库目录的完整路径
4. 验证路径存在
5. 检查 `<路径>/.index/` 是否存在
   - 若不存在 → 提示：索引尚未生成，建议运行 `/taw --build-kb-index` 构建
6. 执行 `python3 $SKILL_DIR/../tools/tw_config.py set localkb.path <路径>`

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
      python3 $SKILL_DIR/../tools/tw_config.py set anythingllm.enabled true
      python3 $SKILL_DIR/../tools/tw_config.py set anythingllm.workspace <workspace>
      python3 $SKILL_DIR/../tools/tw_config.py set anythingllm.base_url <url>
      python3 $SKILL_DIR/../tools/tw_config.py set anythingllm.api_key <key>
      ```
   d. 提示用户：配置完成。MCP server 由 `anythingllm-mcp` plugin 自动注册（plugin.json 的 `mcpServers` 字段），无需手工改 `~/.claude.json`；下次 Claude Code 启动或 `/reload-plugins` 后生效。

#### Step 3：draw.io plugin 安装检测

drawio 现已从 tender-workflow 独立成 `presales-skills` marketplace 内的 shared plugin。用户通常与 tender-workflow 同时通过 umbrella marketplace 安装。

1. 检查 drawio plugin 是否已随 umbrella marketplace 安装（v0.3.0+ 用 installed_plugins.json 自定位）：
   ```bash
   DRAWIO_PATH=$(python3 -c "
   import json, os, sys
   p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
   if os.path.exists(p):
       d = json.load(open(p))
       for entries in d.get('plugins', {}).values():
           for e in (entries if isinstance(entries, list) else [entries]):
               if isinstance(e, dict) and '/drawio/' in e.get('installPath', ''):
                   print(e['installPath']); sys.exit(0)
   " 2>/dev/null)
   [ -n "$DRAWIO_PATH" ] && echo "INSTALLED: drawio plugin at $DRAWIO_PATH" || echo "NOT_INSTALLED"
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
     python3 $SKILL_DIR/../tools/tw_config.py set mcp_search.priority '["tavily_search", "exa_search"]'
     # 或仅配置了一个：
     python3 $SKILL_DIR/../tools/tw_config.py set mcp_search.priority '["tavily_search"]'
     ```
5. 若用户选择全部跳过 → 保持默认值，提示后续可通过 `/twc set mcp_search.priority [...]` 修改

#### Step 5：Skill 默认值（可选）

1. **taa 厂商名**：
   - 当前默认"灵雀云"，询问是否修改
   - 若修改 → `python3 $SKILL_DIR/../tools/tw_config.py set taa.vendor <名称>`

2. **tpl 默认模板**：
   - 显示可选模板：government / finance / soe / enterprise
   - 询问是否设置默认模板（设置后 /tpl 可省略 --template 参数）
   - 若设置 → `python3 $SKILL_DIR/../tools/tw_config.py set tpl.default_template <模板>`

3. **tpl 默认细致程度**：
   - 显示可选级别：detailed / standard / general / brief
   - 当前默认 standard，询问是否修改

#### Step 6：写入配置并验证

1. 执行 `python3 $SKILL_DIR/../tools/tw_config.py validate`
2. 显示配置摘要表格（调用 `python3 $SKILL_DIR/../tools/tw_config.py show`）
3. 若存在旧配置文件：
   ```python
   python3 -c "from pathlib import Path; taw=Path.home()/'.config/taw/config.yaml'; taa=Path.home()/'.config/taa/config.yaml'; print(f'taw: {taw.exists()}, taa: {taa.exists()}')"
   ```
   - 若存在 → 询问是否迁移删除（推荐）
   - 若确认 → 执行 `python3 $SKILL_DIR/../tools/tw_config.py migrate`
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

5. **下一步**：如尚未配置 AI 生图，对 ai-image SKILL 说"配置 ai-image"或直接跑 `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup` 填写 API keys 与默认 provider；已配置过的可跳过。
