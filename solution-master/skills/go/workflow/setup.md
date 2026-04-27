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

## 步骤 4：MCP 搜索工具配置（可选）

知识检索可走 MCP 搜索工具补充 web 素材。当前支持三类，全部走 web-access plugin 的 `mcp_installer.py` 统一注册到 `~/.claude.json`。**`<provider>` 列即下文命令中传给 mcp_installer.py 的短名**（不要传完整品牌名）：

| `<provider>` | 完整品牌名 | Runtime | 包 | 提供 tool |
|---|---|---|---|---|
| `tavily` | Tavily Search | node | `tavily-mcp@latest` | `tavily_search` |
| `exa` | Exa Search | node | `exa-mcp-server@latest` | `exa_search` |
| `minimax` | MiniMax Token Plan | uv | `minimax-coding-plan-mcp` | `web_search` + `understand_image`（图理解）；需订阅 [Token Plan](https://platform.minimaxi.com/subscribe/token-plan) 拿 `sk-cp-` 前缀 key |

### 4.0 路径自定位 web-access plugin

```bash
WA_PATH=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/web-access/' in e.get('installPath', ''):
                print(e['installPath']); sys.exit(0)
" 2>/dev/null)
[ -n "$WA_PATH" ] && WA_INSTALLER="$WA_PATH/skills/browse/scripts/mcp_installer.py" \
  || echo "SKIP_MCP: web-access plugin 未安装"
```

**两种处理路径**：
- 用户决定**先装 web-access 再继续**（`/plugin install web-access@presales-skills` + `/reload-plugins` 后回话）→ 重新跑 4.0
- 用户决定**跳过 MCP 工具配置**（knowledge-retrieval 用内置 WebSearch 兜底也能跑）→ 直接进步骤 5，不要因此中断整个 wizard

> ⚠️ **AI 注 1（路径解析）**：本 markdown 内的 ```bash``` 块在每次执行时是独立 subprocess（环境变量不跨 Bash 调用持久）。`$WA_INSTALLER` 是 4.0 解析得到的**绝对路径字符串**，AI 在每次调用 4.1–4.4 各 bash 块时需把 `$WA_INSTALLER` **inline 替换为该绝对路径**，否则会 command not found。
>
> ⚠️ **AI 注 2（SKIP 短路）**：若 4.0 输出含 `SKIP_MCP:` 前缀（即 web-access 未装且用户选择不装），**直接跳过 4.1–4.4 整段进步骤 5**；不要继续执行下面任何 bash 块（否则会用空 `$WA_INSTALLER` 跑出 command not found）。

### 4.1 检测当前已注册状态

```bash
python3 -c "
import json
from pathlib import Path
p = Path.home() / '.claude.json'
c = json.loads(p.read_text()) if p.exists() else {}
s = c.get('mcpServers', {})
for k in ('tavily', 'exa', 'minimax'):
    print(f'{k}: ' + ('✅' if k in s else '⚠️ 未配置'))
"
```

### 4.2 询问要配哪些（多选）

通过 AskUserQuestion 让用户多选：`Tavily` / `Exa` / `MiniMax Token Plan` / `全部跳过`。
全部跳过 → 进步骤 5。

### 4.3 对每个选中 provider 循环

按以下流程对每个 `<provider>` 走完再进下一个：

**a. 检测 runtime**

```bash
RUNTIME=$( [ "$provider" = "minimax" ] && echo uv || echo node )
python3 "$WA_INSTALLER" check "$RUNTIME"
```

- `OK <path>` → 进 b
- `MISSING` → 调 `python3 "$WA_INSTALLER" auto-install "$RUNTIME"`（用户级路径，不要 sudo）
  - 输出 `OK ...` → 提示 reopen shell 让 PATH 生效（fnm/uv 都装到 `~/.local/bin` 等位置），让用户回话告诉我 "装好了" → 重检测回 a
  - 输出 `NEEDS_USER_ACTION: <command>` → 转述命令给用户，等用户回话 → 重检测回 a

**b. 探活包可用性**

```bash
python3 "$WA_INSTALLER" probe "$provider"
```

- `PASS` → 进 c
- `FAIL` → 转述末行错误，让用户决定重试（回 a）/ 跳过该 provider

**c. 收集 API key**

通过 AskUserQuestion 收 key（一次问一个 provider）：
- **Tavily**：从 https://tavily.com 获取（无前缀强约束）
- **Exa**：从 https://exa.ai 获取（无前缀强约束）
- **MiniMax**：从 https://platform.minimaxi.com 订阅 Token Plan 后拿 key，**必须 `sk-cp-` 前缀**（普通 chat key 不能给 MCP 用）

**d. 写入 ~/.claude.json**

```bash
python3 "$WA_INSTALLER" register "$provider" --key="$KEY"
```

- 输出 `OK <provider> written to ~/.claude.json` → 进 e
- 输出 `INVALID_KEY_PREFIX: ...` → 回 c 重收 key

**e. 询问是否实测（推荐）**

通过 AskUserQuestion：`现在测一下 <provider> 通不通？`（Yes / Skip）

- Yes → `python3 "$WA_INSTALLER" test "$provider"`
  - 该子命令独立 spawn server 跑 MCP JSON-RPC 握手 + tools/call 实测，**不依赖 reload-plugins**
  - tavily/exa 跑 1 次 search；minimax 跑 `web_search` + `understand_image` 两次 tool/call，**全 PASS** 才算通过
  - 全 PASS → 显示 `✅ <provider> 实测通过`
  - 任一 FAIL → 转述输出末行 + 给用户三选一：①换 key（回 c）②unregister 跳过（`python3 "$WA_INSTALLER" unregister "$provider"`）③留着自己排查
- Skip → 直接进下一个 provider

### 4.4 动态发现 + 用户选默认 search MCP

> **动机**：Claude Code 里有什么 MCP 搜索工具就用什么，不预设 provider 名单。这一步跑 `mcp_installer.py list-search-tools` 实时枚举当前 `~/.claude.json` 已注册的 MCP server，spawn 每个跑 MCP `tools/list`，启发式过滤出 web 搜索类 tool，让用户从**真实可用**的清单里选默认。新装的 MCP（不需要升级 plugin）下一次 setup 自动出现。

**a. 枚举可用搜索工具**

```bash
python3 "$WA_INSTALLER" list-search-tools --include-builtin --timeout 60
```

输出 JSON Lines。常见情况：
- 正常：每个找到的搜索 tool 一行（含 `server` / `tool` / `fqn` / `description`）+ 末尾 WebSearch 兜底行
- 单 server 失败：`{"server":"<x>","error":"<reason>"}` 行（不阻塞其它）
- 完全没 MCP：只输出 `_empty` + WebSearch 兜底

**b. 把 fqn 列表展示给用户**（编号 1..N，每行：`<n>. <server>  (<fqn>)  <description>`）

```
1. tavily       (mcp__tavily__tavily_search)        Search the web for current information…
2. exa          (mcp__exa__web_search_exa)          Search the web for any topic and get…
3. minimax      (mcp__minimax__web_search)          MiniMax web search
4. WebSearch    (内置兜底)                          Claude Code 内置 web 搜索
```

特殊场景：
- 只有 1 项 → 不问，直接选它
- 0 项 → 提示 "没检测到任何 MCP 搜索工具，建议跑 `配置 web-access` 注册 tavily/exa/minimax，或继续用 WebSearch 兜底"，把 priority 设成 `["WebSearch"]` 进 4.5

**c. AskUserQuestion 让用户选默认**（单选 + "全用 + 按编号顺序降级"选项）

> "选 solution-master 跑 web 检索时的默认搜索工具：
>   - 单选某个：只用它，失败时回 WebSearch
>   - 全用：按上面编号顺序试，前一个失败试下一个，最后回 WebSearch"

**d. 写入 priority（永远存 FQN）**

```bash
# 例 1：用户选了 minimax
python3 "$SM_CONFIG" set mcp_search.priority '["mcp__minimax__web_search"]'

# 例 2：用户选了"全用"，按编号顺序排
python3 "$SM_CONFIG" set mcp_search.priority \
  '["mcp__tavily__tavily_search", "mcp__exa__web_search_exa", "mcp__minimax__web_search", "WebSearch"]'

# 例 3：0 项兜底
python3 "$SM_CONFIG" set mcp_search.priority '["WebSearch"]'
```

> **AI 注**：`set` 命令收到老别名（如 `tavily_search`）会自动转 FQN 落盘——但**新写的 priority 必须用 FQN**，不要再造别名。落盘后 `python3 "$SM_CONFIG" get mcp_search.priority` 查 confirm。

**e. 显示当前 priority + 提示**

```
✅ 已写入 mcp_search.priority = ["mcp__minimax__web_search"]
   工作流（knowledge-retrieval）跑 web 检索时按列表顺序试，全失败回 WebSearch。
   未来新装其它 MCP 想加进来，重跑 /solution-master setup 这一步即可。
```

### 4.5 关键纪律

- **配置自动化的边界**：用户级安装路径（uv via astral.sh / node via fnm）→ 直接装；落到 sudo 才 print + 等 y
- **register 后必问 test** — 不要静默写完就走，否则用户后续真检索时才发现 key 失效
- **test 失败必须给三选一** — 不能默默跳过；unregister 提供干净回滚路径
- **minimax sk-cp- 校验** — 普通 chat key 不能给 MCP 用（MiniMax-AI/MiniMax-M2 issue #96）
- **4.4 不可跳过**：必须主动跑 list-search-tools 让用户选默认，不能凭"看起来 Step 4 注册完了"就 set priority；否则 priority 是空 → 工作流只能用 WebSearch，浪费用户配的 MCP

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

1. Read `<web-access plugin path>/skills/browse/SKILL.md` → 学习 §路径自定位 + §配置
2. Read `<web-access plugin path>/skills/browse/setup.md` → 走完整 wizard
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
node "$WA_PATH/skills/browse/scripts/check-deps.mjs"

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
