---
name: solution-config
description: 当用户说"配置"、"设置"或需要管理 Solution Master 配置时使用，也可通过 /solution-config 手动调用
allowed-tools: Read, Edit, Bash, AskUserQuestion
---

# 配置管理

统一管理 Solution Master 的所有配置项。

**配置文件：** `~/.config/solution-master/config.yaml`
**配置工具：** `${CLAUDE_SKILL_DIR}/scripts/sm_config.py`

## 命令

| 命令 | 说明 |
|------|------|
| `/solution-config setup` | 交互式首次配置向导（仅 solution-master 专属项） |
| `/solution-config show` | 查看当前配置 |
| `/solution-config set <key> <value>` | 设置配置项（支持 dot notation） |
| `/solution-config validate` | 健康检查 |
| `/solution-config models [provider]` | 列出 AI 生图模型（转发至 `/ai-image:models`） |
| `/solution-config migrate` | 把 sm config 中残留的 api_keys / ai_image 整理到 ai-image plugin（转发至 `/ai-image:migrate`） |

## setup 流程

> **AI 生图配置由 ai-image plugin 管理**：API keys、默认 provider、默认模型请通过 `/ai-image:setup` 配置。本命令仅引导 solution-master 专属项（localkb / anythingllm / drawio / cdp_sites）。

交互式引导用户完成以下配置：

1. **知识库路径**（可选）
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set localkb.path /path/to/Local-KnowledgeBase
   ```

2. **AnythingLLM**（可选）
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set anythingllm.enabled true
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set anythingllm.base_url http://localhost:3001
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set anythingllm.workspace <workspace-slug>
   ```

3. **draw.io Desktop CLI 路径检测**

   draw.io skill 已作为 solution-master 插件的一部分捆绑分发（skills/drawio/），**始终可用**，无需单独安装。唯一需要配置的是 **draw.io Desktop 应用程序**的 CLI 路径，用于把 .drawio 文件自动导出为 PNG 嵌入 DOCX。

   a. 检测 draw.io Desktop CLI 路径：
      ```python
      python3 -c "
      import shutil, sys
      from pathlib import Path
      candidates = [shutil.which('draw.io')]
      if sys.platform == 'darwin':
          candidates.append('/Applications/draw.io.app/Contents/MacOS/draw.io')
      elif sys.platform == 'win32':
          import os
          candidates.append(str(Path.home() / 'AppData/Local/Programs/draw.io/draw.io.exe'))
          candidates.append(os.environ.get('PROGRAMFILES', 'C:/Program Files') + '/draw.io/draw.io.exe')
      path = next((c for c in candidates if c and Path(c).exists()), None)
      print(f'CLI: {path}' if path else 'CLI: NOT_FOUND')
      "
      ```
   b. 若检测到 → 设置 `drawio.cli_path`
   c. 若未检测到 → 提示用户："draw.io Desktop 应用程序未安装，PNG 导出功能不可用（drawio skill 仍可生成 .drawio 文件供手动打开）。可从 https://www.drawio.com/ 下载 Desktop 版本后重新运行 /solution-config setup。"跳过此步

4. **CDP 登录态站点配置**（可选——用于检索需要登录的内部站点，如 Confluence、企业知识库等）

   a. 询问用户是否需要从需要登录的内部站点检索知识
   b. 若用户选择跳过 → 继续下一步
   c. 若用户需要：
      ```bash
      python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set cdp_sites.enabled true
      ```
   d. 循环添加站点：
      - 询问站点名称（如"公司 Confluence"、"内部知识库"）
      - 引导用户获取搜索 URL 模板：
        > "请在浏览器中打开该站点，搜索一个关键词（如"测试"），然后复制搜索结果页的 URL 给我。我会将关键词替换为 `{query}` 占位符。"
      - 将用户提供的 URL 中的搜索关键词替换为 `{query}`，构造 search_url
      - 从 search_url 中自动提取 domain（如 `https://confluence.alauda.cn/...` → `confluence.alauda.cn`）
      - 询问是否有单独的登录页 URL（大多数站点不需要，直接回车跳过）
      - 通过 sm_config.py 写入站点配置（注意：`cdp_sites.sites` 是列表，需要整体 set）
      - 询问是否继续添加下一个站点
   e. 检查 web-access plugin 前置依赖（调用 web-access plugin 暴露的 `web-access-check` 命令，自动探测 Node 版本、Chrome 远程调试端口、启动 CDP Proxy）：
      ```bash
      web-access-check
      ```
      未通过时引导用户：
      - 安装 Node.js 22+
      - 在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging`，勾选 "Allow remote debugging for this browser instance"
      - 如果提示 `command not found`，说明 web-access plugin 未安装，请执行 `/plugin install web-access@presales-skills`
   f. 提示用户确保已在 Chrome 中登录这些站点

5. **验证配置**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" validate
   ```

> **下一步**：完成本命令后，如尚未配置 AI 生图，运行 `/ai-image:setup` 填写 API keys 与默认 provider。

## 配置 Schema

api_keys 与 ai_image 块由 ai-image plugin 持有（`~/.config/presales-skills/config.yaml`），不在此处。

```yaml
localkb:
  path: /path/to/Local-KnowledgeBase      # 本地知识库路径

anythingllm:
  enabled: true/false                       # 是否启用 AnythingLLM
  base_url: "http://localhost:3001"         # AnythingLLM 地址
  workspace: <slug>                         # 默认 workspace

mcp_search:
  priority: [tavily_search, exa_search]     # MCP 搜索工具优先级

cdp_sites:
  enabled: true/false                       # 是否启用 CDP 登录态站点检索
  sites:                                    # 站点列表
    - name: "站点显示名"                     # 出现在检索结果来源标注中
      domain: example.com                   # 站点域名（匹配 site-patterns）
      search_url: "https://example.com/search?q={query}"  # 搜索 URL 模板
      login_url: "https://example.com/login"  # 可选：登录页 URL
      max_results: 5                        # 可选：最多提取结果数（默认 5）

drawio:
  cli_path: null                            # draw.io CLI 路径
```

## 执行流程

### /solution-config models [provider] / --refresh

转发到 ai-image plugin 的统一模型注册表入口：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" models [provider | --refresh]
```

`sm_config.py` 内部会调用 `ai-image-config models …`，由 ai-image plugin 提供注册表渲染与联网刷新逻辑。请确保 ai-image plugin 已安装（`/plugin install ai-image@presales-skills`）。

## 配置查找优先级

1. 配置文件（`~/.config/solution-master/config.yaml`）
2. 环境变量（`SM_ANYTHINGLLM_WS`）
3. 内置默认值
