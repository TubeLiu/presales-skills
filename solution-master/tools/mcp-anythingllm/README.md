# AnythingLLM MCP Server

为 Tender Workflow 项目提供 AnythingLLM 知识库语义搜索能力的 MCP 工具。

## 功能

- `anythingllm_search` - 语义搜索知识库，返回相关文档片段和 AI 生成回答
- `anythingllm_list_workspaces` - 列出所有可用的 workspace

## 安装

### 方式一：使用安装脚本（推荐）

```bash
cd tools/mcp-anythingllm
node install.js
```

安装脚本会：
1. 全局安装 npm 包
2. 自动配置 `~/.claude.json`
3. 创建 `~/.config/tender-workflow/config.yaml`
4. 交互式引导配置 API Key 和 workspace

### 方式二：手动安装

**1. 确保 AnythingLLM 运行中**

```bash
# 检查 AnythingLLM Desktop 是否运行
curl http://localhost:3001/api/ping
# 预期输出：{"online":true}
```

**2. 获取 API Key**

打开 AnythingLLM Desktop → 设置 → API Keys → 创建新 Key

**3. 全局安装 npm 包**

```bash
cd tools/mcp-anythingllm
npm install -g .
```

**4. 配置 Claude Code MCP**

编辑 `~/.claude.json`：

```json
{
  "mcpServers": {
    "anythingllm": {
      "command": "mcp-anythingllm",
      "args": [],
      "env": {
        "ANYTHINGLLM_BASE_URL": "http://localhost:3001",
        "ANYTHINGLLM_API_KEY": "your-api-key-here",
        "ANYTHINGLLM_WORKSPACE": "product-kb"
      }
    }
  }
}
```

**说明**：全局安装后，`command` 使用包名 `mcp-anythingllm`，系统会自动在 PATH 中查找可执行文件。

**5. 重启 Claude Code**

重启后 MCP 工具即可使用。

## 使用

### 基本用法

```bash
# 搜索知识库
/anythingllm_search query="容器云架构"

# 列出 workspaces
/anythingllm_list_workspaces
```

### 在 taa/taw 中使用

```bash
# 指定 workspace slug（推荐）
/taa 招标文件.pdf --anythingllm-workspace "product-kb"

# 指定 workspace 名称（也支持）
/taa 招标文件.pdf --anythingllm-workspace "产品能力库"

# 强制使用 AnythingLLM 作为产品能力来源
/taa 招标文件.pdf --kb-source anythingllm

# taw 同样支持
/taw output/ --chapter 1.3 --anythingllm-workspace "product-kb"
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANYTHINGLLM_BASE_URL` | `http://localhost:3001` | AnythingLLM API 地址 |
| `ANYTHINGLLM_API_KEY` | - | API Key（必需） |
| `ANYTHINGLLM_WORKSPACE` | - | 默认 workspace slug（可选） |

## Workspace Slug 说明

`--anythingllm-workspace` 参数支持两种形式：

1. **Workspace Slug**（推荐）： workspace 的唯一标识符，如 `product-kb`
2. **Workspace Name**：工作区的显示名称，如 "产品能力库"

**如何查看 workspace slug**：

```bash
# 使用 MCP 工具列出所有 workspace
/anythingllm_list_workspaces
```

返回结果示例：
```json
{
  "id": 1,
  "name": "产品能力库",
  "slug": "product-kb"
}
```

- `name`：显示名称（中文）
- `slug`：唯一标识符（英文，推荐在命令行中使用）

**优先级**：
1. 先按 slug 精确匹配
2. 若未找到，再按 name 匹配

## 配置文件

### Claude Code 配置

`~/.claude.json` - MCP Server 配置

### 统一配置

`~/.config/tender-workflow/config.yaml` - 统一配置文件

```yaml
anythingllm:
  workspace: product-kb   # workspace slug 或名称
```

## 与 taw/taa 集成

taw 和 taa skill 会自动检测并使用 AnythingLLM 进行知识库检索，优先级：

1. AnythingLLM 语义搜索（score >= 0.65）
2. 本地 YAML 索引（fixed → reusable → history）
3. 互联网检索（WebSearch / Tavily / Exa）

**Workspace 优先级**：
1. `--anythingllm-workspace` 参数值
2. `~/.config/tender-workflow/config.yaml` 中的 `anythingllm.workspace`
3. 环境变量 `TAA_ANYTHINGLLM_WS` 或 `TAW_ANYTHINGLLM_WS`
4. 列表中第一个 workspace
