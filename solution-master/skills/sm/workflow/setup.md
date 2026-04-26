# solution-master 配置 wizard

> 触发自 solution-master 主 SKILL.md 的 §配置 段。本文件由 Claude 在用户说「配置 solution-master / 帮我配置 solution-master / 初始化 solution-master / setup solution-master」时 Read 加载。
>
> **关键纪律**：每次都 Read 当前版本 — 不要凭记忆执行。

## 配置文件分工

solution-master 的配置分两个文件：

| 文件 | 字段 | 由谁管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml`（共享） | `api_keys` / `ai_image` / `ai_keys` | **ai-image** 的 `ai_image_config.py`（要配 API keys 时告诉用户："API keys 由 ai-image 管理，跟我说'帮我配置 ai-image'我来引导。") |
| `~/.config/solution-master/config.yaml`（专属） | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search` | **本 wizard** 引导 `sm_config.py` 写入 |

## 步骤 0.5：依赖前置检查

### A. Python ≥ 3.10（必需）

参照 ai-image setup.md §0.5 §A 段（检测 + 非 sudo 自动 / 需 sudo 打印 + 用户许可）。简版检测命令：

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || py -3 --version 2>/dev/null
```

⚠ Windows 特例：命令"成功"但无输出（exit 49）= WindowsApps 下的 Microsoft Store stub，按"未装"处理。识别：
```bash
python --version 2>&1 | grep -qi "Microsoft Store" && echo STUB
where python 2>&1 | grep -qi "WindowsApps" && echo STUB
```

未通过时按 ai-image setup.md 同款"依赖安装引导"流程（Windows 推荐 `winget install -e --id Python.Python.3.12`）。

### B. Node.js ≥ 22（仅启用 CDP 时必需，按需触发）

如果用户在步骤 5 选择启用 CDP，本步骤再触发——参照 web-access setup.md §0.5 段。

## 步骤 1：解析 SKILL_DIR + show 当前配置

```bash
SM_CONFIG="$SKILL_DIR/scripts/sm_config.py"
python3 "$SM_CONFIG" show
```

告知用户当前哪些字段已有值、哪些是默认/缺失。

## 步骤 2：本地知识库路径（必填）

询问用户：

> "你的本地知识库目录在哪？（用绝对路径。如果还没有，可以先建一个空目录，后续往里加 .md 文件）"

```bash
python3 "$SM_CONFIG" set localkb.path <path>
```

验证路径存在性：

```bash
[ -d "<path>" ] && echo OK || echo "目录不存在，已记录路径但请用户后续创建"
```

## 步骤 3：AnythingLLM 语义搜索（可选）

询问用户：

> "要启用 AnythingLLM 语义搜索吗？（需要本地或远程跑了 AnythingLLM 服务；不启用也能正常工作 — 会降级为本地 YAML 索引 + Web 多源检索）"

### 启用分支

询问：

> "AnythingLLM 服务的 base_url 是什么？（默认 `http://localhost:3001`，远程服务给完整 URL）"

```bash
python3 "$SM_CONFIG" set anythingllm.base_url <url>
```

询问：

> "workspace slug 是什么？如果不确定，去你的 AnythingLLM Web UI 看一下（地址栏会显示 workspace slug，或在 Settings > Workspaces 列表里找）。"

```bash
python3 "$SM_CONFIG" set anythingllm.workspace <slug>
python3 "$SM_CONFIG" set anythingllm.enabled true
```

### 跳过分支

```bash
python3 "$SM_CONFIG" set anythingllm.enabled false
```

## 步骤 4：MCP 搜索工具优先级（可选）+ 试调验证 + 引导配 key

### 4.1 询问优先级

询问用户：

> "Web 检索用哪个优先级？默认 `[tavily_search, exa_search]`（先试 tavily，失败回退 exa）。也可只配一个：
> - `[tavily_search]`（仅 tavily）
> - `[exa_search]`（仅 exa）
> - `[]`（不用 MCP 搜索，仅靠 Claude Code 内置 WebSearch）"

```bash
python3 "$SM_CONFIG" set mcp_search.priority "[<用户选择>]"
```

### 4.2 对每个选中的工具试调（核心新增）

**只设 priority 不配 key 没意义 — 必须实测每个工具能不能跑。** 对 priority 数组里每个工具按以下流程：

#### 4.2.a tavily_search 试调（如选中）

Claude 用 mcp 工具试调一次最小搜索：

```
Tool call: mcp__tavily__tavily_search
Args: { "query": "kubernetes", "max_results": 1 }
```

或对应注册名（按用户实际装的 MCP server，如 `mcp__tavily-search__tavily_search` / `mcp__tavily_mcp__search`）。

**结果分支**：

- ✅ 返回搜索结果 → 告知用户"tavily 已配通，可用"，进入 4.2.b
- ❌ 错误 = "tool not found / tavily MCP server not registered"：

  > "你选了 tavily 但 Claude Code 未注册 tavily MCP server。要用 tavily，需要先装一个 tavily MCP plugin（推荐：https://github.com/anthropics/mcp-tavily 或社区版本），并按其文档配 `TAVILY_API_KEY` 环境变量。
  >
  > 现在你有 3 个选择：
  > 1. 我等你去装 + 配 key + `/reload-plugins`，然后回来对我说"好了"我重新试调
  > 2. 改 priority 把 tavily 移掉（保留 exa 或纯 WebSearch）
  > 3. 先跳过这步，后续真用到时再配（但 knowledge-retrieval workflow 在你启用了 tavily 时会一直试调失败）"

  按用户选择处理（1 → 等用户回复后重新 4.2.a；2 → 回到 4.1 改 priority；3 → 进入 4.2.b）

- ❌ 错误 = "missing API key / unauthorized / 401"：

  > "tavily MCP server 已注册但 API key 未配 / 已过期。请检查环境变量 `TAVILY_API_KEY` 或对应 MCP plugin 的配置文件（具体路径取决于你装的 tavily MCP plugin），配好后重新 `/reload-plugins` 再回来重试。"

  等用户回复后重新 4.2.a。

- ❌ 其它错误（rate limit / 网络）：转述错误给用户，让用户自行决定重试或跳过

#### 4.2.b exa_search 试调（如选中）

重复 4.2.a 流程，但 MCP 工具名换成 `mcp__exa__exa_search` / `mcp__exa-search__exa_search` / 类似。

错误信息同样三类：
- 工具未注册 → 引导装 mcp-exa（如 https://github.com/exa-labs/mcp-exa）+ 配 `EXA_API_KEY`
- API key 缺失 → 引导配 `EXA_API_KEY`
- 其它 → 转述

### 4.3 全部试调通过后

> "Web 检索已配通。priority = `<最终列表>`。
> 后续 knowledge-retrieval workflow 会按此优先级试调；如果某次失败，自动 fallback 到下一个工具，最后兜底用 Claude Code 内置 WebSearch。"

### 4.4 关键纪律

- **不要只 set 不试调** — 这是 v0.3.0 之前的痛点（用户后续真检索时才发现 key 没配）
- 试调失败时**不要默默跳过**，必须转述错误 + 给用户三个明确选择
- API key 配置不在 sm_config.py 范围内（这些是用户级 MCP server 的 env / config）— wizard 只引导，不代为执行

## 步骤 5：CDP 登录态站点检索（可选）

### 5.0 先决条件：web-access 必须配通

询问用户：

> "要启用 CDP 登录态站点（如内部 Confluence / 知识库）检索吗？这需要先配通 web-access plugin（Chrome 浏览器 + remote debugging）。"

#### 跳过

```bash
python3 "$SM_CONFIG" set cdp_sites.enabled false
```

跳到步骤 6。

#### 启用

##### 5.0.a 检测 web-access plugin 是否安装

用主 SKILL.md §跨 skill 调用 段的 installed_plugins.json fallback 找 web-access plugin path。

未装 → 告知用户：

> "web-access plugin 未安装。请在 Claude Code 跑 `/plugin install web-access@presales-skills`，等装完回话告诉我'装好了'，我继续。"

##### 5.0.b 委托 web-access SKILL 完成它自己的配置

告知用户：

> "现在我去配通 web-access（检测 Node.js / 启动 Chrome remote-debug / cdp-proxy 启动）"

按下面步骤走：

1. Read `<web-access plugin path>/skills/web-access/SKILL.md` → 学习 §路径自定位 + §配置
2. Read `<web-access plugin path>/skills/web-access/setup.md` → 走完整 wizard
3. web-access setup.md 通过后回到本步骤 5.1

### 5.1 站点配置循环

```bash
python3 "$SM_CONFIG" set cdp_sites.enabled true
```

每轮配一个站点（按 5.1.a → 5.1.b → 5.1.c → 5.1.d → 5.1.e → 5.1.f）：

#### 5.1.a 逐个询问站点 5 个字段（不要一次抛 5 个问题）

按以下顺序**一次只问一个**，每问完一个等用户回复后再问下一个：

##### 5.1.a.1 name（站点显示名）

> "这个 CDP 站点叫什么名字？给个能识别的中文名就行，比如 `内部 Confluence` / `公司知识库` / `灵雀云 Wiki`。"

##### 5.1.a.2 domain（站点域名）

> "这个站点的域名是什么？只要主域名，不要带 `https://` 前缀，比如 `confluence.alauda.cn`。"

##### 5.1.a.3 search_url（搜索 URL 模板，最关键）

> "请去你的浏览器打开这个站点，对它**搜任何一个词**（比如 'kubernetes'），然后把**地址栏的完整 URL** 复制给我。我会帮你把你刚才搜的那个词换成 `{query}` 占位符做模板。"

收到原始 URL 后，Claude 用字符串替换把用户搜过的词替换为 `{query}`，给用户确认：

> "替换后的模板是：`<modified_url>`
> 确认对吗？"

##### 5.1.a.4 login_url（登录页 URL，可空）

> "这个站点的登录页 URL 是什么？用于实测时检测登录态丢失。如果不需要登录或不知道，回 'skip' 跳过。"

##### 5.1.a.5 max_results（单次最多结果数）

> "这个站点单次搜索最多返回几条结果给我用？推荐 5。直接回数字或 'default' 用推荐值。"

#### 5.1.b 写入 yaml

`sm_config.py set` 不支持数组索引 — 用 Edit 工具直接在 `~/.config/solution-master/config.yaml` 的 `cdp_sites.sites` 数组追加该站点条目（4-5 行 yaml 片段）：

```yaml
cdp_sites:
  enabled: true
  sites:
    # ... 已有站点 ...
    - name: <name>
      domain: <domain>
      search_url: <search_url>
      login_url: <login_url 或省略此行>
      max_results: <max_results>
```

#### 5.1.c 立即实测（核心新增）

询问用户：

> "用什么关键词测一下这个站点的搜索？例如 `kubernetes` / `容器云` / 任何你之前在该站点搜过的词。"

收到关键词后：

```bash
# 1. 解析 web-access plugin path（用 installed_plugins.json fallback）
WA_PATH=$(...)

# 2. 启动/复用 cdp-proxy（idempotent）
node "$WA_PATH/skills/web-access/scripts/check-deps.mjs"

# 3. URL-encode 替换 {query}
SEARCH_URL=$(python3 -c "
import urllib.parse, sys
print(sys.argv[1].replace('{query}', urllib.parse.quote(sys.argv[2])))
" "<search_url 模板>" "<用户给的关键词>")

# 4. 通过 cdp-proxy 在 Chrome 后台 tab 打开
NEW_TARGET=$(curl -s "http://localhost:3456/new?url=$SEARCH_URL" | python3 -c "import json,sys;print(json.load(sys.stdin)['targetId'])")

# 5. 等加载（页面 load 事件后）
sleep 3

# 6. 提取 body 前 1500 字（含前几条搜索结果摘要）
RESULT=$(curl -s -X POST "http://localhost:3456/eval?target=$NEW_TARGET" \
  -d 'document.body.innerText.substring(0, 1500)')

# 7. 关闭测试 tab
curl -s "http://localhost:3456/close?target=$NEW_TARGET" >/dev/null

echo "$RESULT"
```

#### 5.1.d 把 eval 返回内容展示给用户

> "返回内容（前 1500 字）：
> ```
> <eval 返回>
> ```
>
> 这看起来是不是 `<你的关键词>` 的搜索结果？是 / 不是 / 部分对"

#### 5.1.e 实测结果分支

- ✅ 用户确认结果对 → 5.1.f
- ❌ 不对 / 部分对 → 引导排查：
  - **URL 模板错**（{query} 没替换正确）→ 让用户重新提供正确的 search_url 模板，回到 5.1.a.3
  - **登录态丢失**（返回内容含 "login" / "登录" / "sign in" / "请先登录" 等关键字）→ 提示用户去 Chrome 登录该站点 + 刷新一下，回话告诉我"登录好了"，重新 5.1.c
  - **站点 search 实际 API 不在此 URL** → 让用户重新提供 search_url 模板（可能站点用了 GET vs POST / 客户端渲染等），回到 5.1.a.3
- 修复后回到 5.1.c 重测

#### 5.1.f 问下一个站点

> "已配通 `<name>` 站点。还要配置下一个 CDP 站点吗？"

- 用户回"要" / 给新站点 → 回到 5.1.a 配下一个
- 用户回"不要" / "够了" → 退出循环到 5.2

### 5.2 sm_config.py validate 检查 cdp_sites 整体格式

```bash
python3 "$SM_CONFIG" validate
```

## 步骤 6：draw.io 桌面版（可选 — 配图导出能力检测）

> **注**：drawio plugin 自身会在调用时**自动定位** draw.io CLI（PATH / macOS Applications / Windows Program Files / WSL2 /mnt/c），
> 不依赖 config.yaml 写路径。本步骤**只检测桌面版是否可用**，并在缺失时引导安装；不写任何 config 字段。
>
> （v2.x 旧字段 `drawio.cli_path` 已废弃。如果你的 config.yaml 还有这一行，sm_config.py validate 会给 deprecation warn 提示删除。）

### 6.1 自动检测安装位置

按下面顺序检测（任一命中即视为可用）：

```bash
which drawio 2>/dev/null || where drawio 2>/dev/null    # PATH
[ -x /Applications/draw.io.app/Contents/MacOS/draw.io ] && echo "macOS"
[ -x "C:/Program Files/draw.io/draw.io.exe" ] && echo "Windows native"
[ -x "/mnt/c/Program Files/draw.io/draw.io.exe" ] && echo "WSL2"
```

检测到 → 告知用户："draw.io 桌面版已可用（位于 `<detected_path>`），drawio plugin 调用时会自动定位，无需手工配置路径。"，跳到步骤 7。

### 6.2 默认位置都没找到时的三步分支

未检测到时**不要直接劝装** — 很多用户把 draw.io 装在自定义目录（公司 IT 限制 Applications/、个人偏好 ~/Apps/、挂载在 D:/E: 盘等）。按下面三步走：

#### 6.2.a 询问是否已装在其他路径

> "默认安装位置都没找到 draw.io。是不是装在了其他目录？比如自定义的 `~/Apps/`、`D:\Tools\`、公司 IT 部署的特定路径等。
>
> 如果是，请把 draw.io 可执行文件的**完整绝对路径**告诉我；如果没装就回 '没装'。"

收到用户提供的路径后验证：

```bash
[ -x "<user_provided_path>" ] && echo OK || echo "路径不可执行"
"<user_provided_path>" --version 2>&1 | head -1   # 试跑确认是 draw.io
```

- 验证通过 → 告知用户："已确认 draw.io 在 `<path>` 可用。drawio plugin 当前不读 config 字段定位 CLI——如果它的自动检测列表没覆盖你这个路径，使用时它会报错；那时再把这个路径告诉我，我让 drawio plugin 通过环境变量 `DRAWIO_CLI` 或 PATH 临时使用。"，跳到步骤 7
- 验证失败（路径不存在 / 不可执行 / 跑出来不是 draw.io）→ 告知用户错误原因 + 让用户重新提供路径，或回到 6.2.b

#### 6.2.b 用户回"没装" → 询问要不要装

> "draw.io 桌面版未装，drawio skill 仍可生成 .drawio 源文件，但不能自动导出 PNG/SVG/PDF。要我帮你装吗？"

同意装 → 按 §0.5 §A/B 同款"依赖安装引导"模式（先 print + 等用户 y + Bash 执行 / 降级打印）：

- macOS：`brew install --cask drawio`
- Windows：`winget install -e --id JGraph.Draw`
- Linux：手动下载（无非 sudo 自动路径，仅打印指引到 https://github.com/jgraph/drawio-desktop/releases）

装完后回到 6.1 重新检测。

#### 6.2.c 用户拒绝装 → 跳过

> "已跳过 draw.io 桌面版。后续 drawio skill 仍可生成 .drawio 源文件，但不能自动导出 PNG/SVG/PDF——需要时你可以用 draw.io Web 版（https://app.diagrams.net）手动打开 .drawio 文件后导出。"

不需要写 config 字段（drawio plugin 不依赖 config 定位）。直接跳到步骤 7。

## 步骤 7：API keys 透传

> "solution-master 撰写章节配图时会用到 AI 生图 API keys。这部分由 ai-image plugin 管理（共享给所有 plugin）。
>
> 如果你还没配，对我说'帮我配置 ai-image'我来引导你完成。"

## 步骤 8：完成提示

```bash
python3 "$SM_CONFIG" validate
```

告知用户每项检查结果。

> "solution-master 配置完成！
>
> 配置文件：`~/.config/solution-master/config.yaml`（专属字段）+ `~/.config/presales-skills/config.yaml`（共享 API keys，由 ai-image 管理）
>
> 现在你可以说'帮我写一份 K8s 多集群方案'之类自然语言来启动方案撰写流程。"

## 关键纪律

- **一步一问 + 立即写入 + 立即验证**（不批量收集再统一写）
- 用户可跳过任何"可选"字段
- CDP 站点用 Edit 工具直接改 yaml（sm_config.py set 不支持数组索引）
- 实测失败必须给出诊断 + 让用户决策，不默默跳过
- MCP 搜索工具配置必须 set + 试调（不只 set），key 缺失时引导用户去 MCP plugin 自己配
