# web-access 配置 wizard

> 触发自 web-access SKILL.md 的 §配置 段，**或被 solution-master 的 CDP 配置流程委托**。
>
> Claude 在用户说「配置 web-access / 帮我配置 web-access / 启用 CDP / 初始化 web-access」或 solution-master 启用 CDP 时 Read 加载。
>
> **关键纪律**：每次都 Read 当前版本 — 不要凭记忆执行。

## 步骤 0.5：依赖前置检查（Node.js ≥ 22）

```bash
node --version 2>/dev/null
```

- ✅ ≥22 → 继续步骤 1
- ❌ 未装 / 版本 <22：进入下方"依赖安装引导"

### 依赖安装引导

1. **检测平台 + 包管理器**：
   ```bash
   uname -s
   command -v brew >/dev/null && echo HAS_BREW
   command -v winget >/dev/null && echo HAS_WINGET
   command -v nvm >/dev/null && echo HAS_NVM   # 注：nvm 是 shell 函数，可能 command -v 检测不到，需要 source ~/.nvm/nvm.sh 后再试
   ```

2. **走非 sudo 路径（Claude 直接执行）**：
   - macOS（已装 brew）→ 准备命令 `brew install node@22`
   - Windows（已装 winget）→ 准备命令 `winget install -e --id OpenJS.NodeJS.LTS`
   - 已装 nvm（任何 OS）→ 准备命令 `nvm install 22 && nvm use 22`

3. **走 sudo 路径（Claude 不能跑，仅打印让用户复制到自己 terminal）**：
   - Debian/Ubuntu → 打印 NodeSource 安装：
     ```
     curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
     sudo apt-get install -y nodejs
     ```
   - RHEL/Fedora → 打印类似 NodeSource RPM 流程

4. **非 sudo 路径执行前必须先告诉用户**：

   > "我想为你执行 `<完整命令>`，需要你确认。这会装 Node.js 22 到 `<预期路径>`，无需 sudo。要继续吗？(y/n)"

   收到 y 才用 Bash 工具执行；收到 n 或没明确同意 → 停下来告知"装好后回话告诉我'装好了'，我重新检测"。

5. **装完重新跑步骤 0.5 检测命令**，确认 ≥22 才继续步骤 1。

## 步骤 1：检测 Chrome remote-debugging

```bash
node "$SKILL_DIR/scripts/check-deps.mjs"
```

输出 ok = 已启用 + 端口可达 → 继续步骤 2。

输出 fail（Chrome remote-debugging 未启用 / 端口未开）：

### 1.a 引导用户启用 Chrome remote-debugging

告诉用户：

> "请在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging`
> 勾选 'Allow remote debugging for this browser instance'。
> 可能需要重启浏览器（关闭所有 Chrome 窗口后重新打开，注意是**所有**窗口，不是只关一个 tab）。
> 完成后告诉我'好了'，我重新检测。"

### 1.b 收到用户回复后重新检测

```bash
node "$SKILL_DIR/scripts/check-deps.mjs"
```

循环直到 ok。如果反复失败（≥3 次），提示用户检查：

- Chrome 是否在 9222 端口启动（默认）：`lsof -i :9222`（macOS/Linux）或 `netstat -ano | findstr :9222`（Windows）
- 是否有多个 Chrome 实例（kill 全部 Chrome 进程后重启）
- 公司 IT 策略是否禁用了 remote debugging（企业 managed Chrome 常见）—— 如有，告知用户这部分功能在公司 Chrome 内不可用，建议改用个人 Chrome 或 Chromium

## 步骤 2：启动并验证 CDP Proxy

`check-deps.mjs` 通过后会自动启动 `cdp-proxy.mjs`（端口 :3456）。验证 proxy 可达：

```bash
curl -s http://localhost:3456/targets | python3 -c "import json,sys;print(len(json.load(sys.stdin)))"
```

返回 ≥1 = OK（用户当前打开的所有 tab 数量）→ 继续步骤 3。

返回错误 / 0 = proxy 未启动 / 端口冲突 / Chrome 没开任何 tab。

### 2.a 端口冲突诊断

```bash
lsof -ti :3456    # macOS/Linux：看占用 3456 的进程 pid
# Windows：netstat -ano | findstr :3456
```

**不要默认 kill**——先把占用进程信息展示给用户，让他决定：

> "端口 3456 被进程 `<pid>` 占用了。这通常是上次 cdp-proxy 没正常退出。要我 kill 它吗？(y/n)"

收到 y 才执行：

```bash
kill -9 <pid>
node "$SKILL_DIR/scripts/check-deps.mjs"   # 重启
```

收到 n → 让用户自己处理后回话继续。

## 步骤 3：风险告知（必须原文显示给用户）

```
温馨提示：部分站点对浏览器自动化操作检测严格，存在账号封禁风险。
web-access 已内置防护措施但无法完全避免，继续操作即视为接受。
```

收到用户确认（任何 ack 即可，比如"知道了 / OK / 继续"）后视为配置通过，进入步骤 4。

## 步骤 4：MCP 搜索工具（tavily / exa / minimax）

> web-access 内置 `scripts/mcp_installer.py`，把 web 搜索类 MCP server 一键注册到 `~/.claude.json`。这是 web-access 配置的一部分，**不要跳过本步直接到步骤 5**——先问用户要不要配，再按用户决定执行。

### 4.1 显示当前 mcpServers 状态

```bash
python3 -c "
import json, os
p = os.path.expanduser('~/.claude.json')
try:
    d = json.load(open(p, encoding='utf-8'))
    s = d.get('mcpServers', {})
except Exception:
    s = {}
for k in ('tavily', 'exa', 'minimax'):
    print(f'{k}: ' + ('已配' if k in s else '未配'))
"
```

把三行 `<provider>: 已配/未配` 直接展示给用户。

### 4.2 询问要不要配 MCP 搜索

AskUserQuestion 一次性问全：

> 要配 web 搜索 MCP 吗？这些工具被 solution-master / tender-workflow 等 plugin 用来做联网检索，是 web-access 的标配能力。
>
> 选项（多选；可以全跳过）：
> - **tavily** — 通用 web 搜索（[tavily.com](https://tavily.com)，需 API key）
> - **exa** — 语义搜索 + 深度抓取（[exa.ai](https://exa.ai)，需 API key）
> - **minimax** — `web_search` + `understand_image`（图理解）；需订阅 [MiniMax Token Plan 套餐](https://platform.minimaxi.com/subscribe/token-plan) 拿 `sk-cp-` 前缀的 key
> - **跳过** — 不配 MCP，直接进步骤 5

> **AI 注 (SKIP 短路)**：用户选"跳过"或全部不选 → echo `SKIP_MCP` 后**整个步骤 4 结束**，跳到步骤 5。下面 4.3-4.5 不要执行。

### 4.3 对每个被选中的 provider 走完整流程

对每个 provider（tavily/exa/minimax）依次：

**a. 检测 runtime**（tavily/exa→`node`；minimax→`uv`）：

```bash
python3 "$SKILL_DIR/scripts/mcp_installer.py" check <runtime>
```

- `OK <path>` → 进 b
- `MISSING` → 跑 auto-install：

```bash
python3 "$SKILL_DIR/scripts/mcp_installer.py" auto-install <runtime>
```

- 用户级安装路径成功（`OK`）→ 重检测 `check` → 进 b
- `NEEDS_USER_ACTION: <command>` → 把命令转述给用户（"装好告诉我'装好了'"），等回话后回 a 重新 check

**b. 探活**：

```bash
python3 "$SKILL_DIR/scripts/mcp_installer.py" probe <provider>
```

- `PASS` → 进 c
- `FAIL: <err>` → 转述末行错误，让用户决定重试 / 跳过该 provider（跳过 → 直接进下个 provider）

**c. AskUserQuestion 收 key**：

> 请贴一下 `<provider>` 的 API key：
> （minimax 的 key 必须以 `sk-cp-` 开头，是 Token Plan 套餐 key，不是普通 chat key）

minimax 收到的 key 不是 `sk-cp-` 开头 → 立即重新问；连续 3 次错 → 提示用户去 [Token Plan 订阅页](https://platform.minimaxi.com/subscribe/token-plan)拿正确 key 后回话。

**d. 写入 `~/.claude.json`**：

```bash
python3 "$SKILL_DIR/scripts/mcp_installer.py" register <provider> --key=<KEY>
```

- 输出 `OK` → 显示 "✅ <provider> 已写入 ~/.claude.json"
- `INVALID_KEY_PREFIX` → 回 c 重新问 key
- 其它错误（写文件失败 / JSON 损坏） → 转述给用户，跳过该 provider

**e. AskUserQuestion 是否实测**：

> 现在测一下 `<provider>` 通不通？（实际跑 MCP 握手 + tools/call，约 30-60 秒）
> - **测一下**
> - **跳过**（之后想测可以说"测一下 <provider>"）

选"测一下" → 跑：

```bash
python3 "$SKILL_DIR/scripts/mcp_installer.py" test <provider>
```

minimax 会跑 `web_search` + `understand_image` 两次 tool/call，全 PASS 才 ✅。

任一 FAIL → 转述错误，三选一：换 key（回 c）/ unregister 跳过 / 留着自己排查（用 `python3 "$SKILL_DIR/scripts/mcp_installer.py" unregister <provider>` 删除）。

### 4.4 完成提示

把成功配的 provider 列一遍：

> ✅ 已配：tavily / exa / minimax 中的 [实际成功的几个]
> ⚠ MCP server 注册需要 `/reload-plugins` 或重启 Claude Code 才生效。
>
> 💡 **下一步（如果你装了 solution-master / tender-workflow）**：
>    跑 `配置 solution-master` 或 `配置 tender` 时，wizard 的 §4 会自动跑
>    `mcp_installer.py list-search-tools` 实时枚举刚配的 MCP，让你选默认
>    搜索工具。新装的 MCP 不需要升级 plugin，下一次 setup 自动出现。

### 4.5 → 进入步骤 5

## 步骤 5：完成提示

> "web-access 配置完成。现在你可以让我搜信息 / 抓登录态网页 / 操作浏览器界面，
> 我会通过 cdp-proxy（:3456）在你 Chrome 后台 tab 里执行（不打扰你正在用的 tab）。"
>
> （如果步骤 4 配了 MCP 搜索工具，提醒一句 `/reload-plugins` 或重启）

## 关键纪律

- 风险告知段（步骤 3）必须**原文显示**给用户，不要简化或意译
- 每次重新检测 = 重新跑 `check-deps.mjs`，不靠记忆
- 端口冲突时**不要默认 kill**，先让用户看占用进程让他决定
- Node.js 安装引导：非 sudo 必须先 print + 等用户 y 才执行；需 sudo 永远只打印让用户复制
- **步骤 4（MCP 搜索工具）不可跳过**——必须主动询问用户，不能因为"看起来 CDP 已配完"就直接到步骤 5；MCP server 注册是 web-access 配置的标配项，跳过会造成 solution-master / tender-workflow 联网检索失能
