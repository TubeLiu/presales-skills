---
name: solution-config
description: 当用户说"配置"、"设置"或需要管理 Solution Master 配置时使用，也可通过 /solution-config 手动调用
---

# 配置管理

统一管理 Solution Master 的所有配置项。

**配置文件：** `~/.config/solution-master/config.yaml`
**配置工具：** `${CLAUDE_SKILL_DIR}/scripts/sm_config.py`

## 命令

| 命令 | 说明 |
|------|------|
| `/solution-config setup` | 交互式首次配置向导 |
| `/solution-config show` | 查看当前配置 |
| `/solution-config set <key> <value>` | 设置配置项（支持 dot notation） |
| `/solution-config validate` | 健康检查 |
| `/solution-config models [provider]` | 列出所有可用的 AI 图片生成模型（可选过滤: ark/dashscope/gemini） |
| `/solution-config models --refresh` | 联网查询各供应商最新模型，更新本地注册表 |

## setup 流程

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

3. **AI 生图 API Key**（至少一个，可选）
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set api_keys.ark <key>
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set api_keys.dashscope <key>
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set api_keys.gemini <key>
   ```

4. **draw.io Desktop CLI 路径检测**

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

5. **AI 生图供应商与模型选择**
   a. 先展示所有可用模型供用户浏览：
      ```bash
      python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" models
      ```
   b. 选择默认供应商：
      ```bash
      python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set ai_image.default_provider <ark|dashscope|gemini>
      ```
   c. 选择该供应商的默认模型（从模型列表中选择）：
      ```bash
      python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" set ai_image.models.<provider> <model-id>
      ```
   d. 若用户配置了多个供应商的 API Key，可分别为每个供应商选择默认模型

6. **CDP 登录态站点配置**（可选——用于检索需要登录的内部站点，如 Confluence、企业知识库等）

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
   e. 检查 web-access skill 前置依赖：
      ```bash
      node "${CLAUDE_SKILL_DIR}/../web-access/scripts/check-deps.mjs"
      ```
      未通过时引导用户：
      - 安装 Node.js 22+
      - 在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging`，勾选 "Allow remote debugging for this browser instance"
   f. 提示用户确保已在 Chrome 中登录这些站点

7. **验证配置**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" validate
   ```

## 配置 Schema

```yaml
localkb:
  path: /path/to/Local-KnowledgeBase      # 本地知识库路径

anythingllm:
  enabled: true/false                       # 是否启用 AnythingLLM
  base_url: "http://localhost:3001"         # AnythingLLM 地址
  workspace: <slug>                         # 默认 workspace

api_keys:
  ark: <key>                                # 火山方舟 API Key
  dashscope: <key>                          # 阿里云 DashScope API Key
  gemini: <key>                             # Google Gemini API Key

ai_image:
  default_provider: ark                     # 默认供应商：ark/dashscope/gemini
  size: 2048x2048                           # 默认图片尺寸
  max_retries: 2                            # 最大重试次数
  timeout: 60                               # 超时秒数
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image

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

### /solution-config models [provider]

1. 执行 `python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" models [provider]`
2. 将输出的 Markdown 表格直接展示给用户（固定格式，数据来自 sm_config.py 内部通过 `_find_models_yaml()` 定位的 `ai_image_models.yaml` 注册表；该函数在 plugin/npx/npx-global 三种安装模式下都能正确定位）
3. 表格中标记当前配置的默认模型（`● 当前默认`）
4. 底部显示如何更改默认模型的命令提示
5. 若注册表 `last_updated` 距今超过 90 天，底部自动显示过期警告

### /solution-config models --refresh

联网查询各供应商最新的 AI 图片生成模型，与本地注册表对比后更新。

**执行流程**：

0. **解析注册表绝对路径**（在 plugin/npx/全局任何模式下都正确）：
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, '${CLAUDE_SKILL_DIR}/scripts')
   from sm_config import _find_models_yaml
   print(_find_models_yaml())
   "
   ```
   记录输出的绝对路径 `<yaml_path>`。后续所有 Read/Write 操作**必须使用这个绝对路径**，不要使用 `.claude/skills/...` 之类的相对路径——plugin 模式下那些路径不存在。

1. 用 Read 工具读取 `<yaml_path>` 获取当前注册表，记录现有模型列表
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
   a. 用 Write/Edit 工具更新 `<yaml_path>`（第 0 步解析出的绝对路径），保持现有 YAML 格式不变
   b. 更新 `last_updated` 为当日日期
   c. 更新 `version` 递增 patch 版本号
7. 执行 `python3 "${CLAUDE_SKILL_DIR}/scripts/sm_config.py" models` 展示更新后的完整表格

**注意事项**：
- 搜索结果需交叉验证（至少两个来源确认），避免误将不存在的模型写入注册表
- 不自动变更用户已配置的默认模型（`ai_image.models.*`），仅更新注册表
- 若某供应商搜索失败，跳过该供应商并告知用户，不影响其他供应商的更新

## 配置查找优先级

1. 配置文件（`~/.config/solution-master/config.yaml`）
2. 环境变量（`ARK_API_KEY`、`DASHSCOPE_API_KEY`、`GEMINI_API_KEY`、`SM_ANYTHINGLLM_WS`）
3. 内置默认值
