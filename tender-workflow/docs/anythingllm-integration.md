# AnythingLLM 知识库集成指南

本文档说明如何将 AnythingLLM 向量知识库对接到 taa 和 taw skill，实现语义检索增强。

**最新更新**（2026-03-16）：
- ✅ taa 完整集成 AnythingLLM（Step 1.6 完整检测逻辑）
- ✅ 支持 `--anythingllm-workspace` 参数和配置文件
- ✅ M2 查询规则增强（缓存机制 + 失败降级）

---

## 前提条件

1. 已安装 [AnythingLLM Desktop](https://anythingllm.com/)
2. AnythingLLM 已配置 MCP Server（见下方）
3. Claude Code 已连接到 AnythingLLM MCP Server

---

## 第一步：配置 AnythingLLM MCP Server

AnythingLLM Desktop 内置 MCP Server，需在 Claude Code 的 MCP 配置文件中注册。

编辑 `~/.claude/claude_desktop_config.json`（若不存在则创建）：

```json
{
  "mcpServers": {
    "anythingllm": {
      "command": "node",
      "args": ["/path/to/anythingllm-mcp-server/index.js"],
      "env": {
        "ANYTHINGLLM_BASE_URL": "http://localhost:3001",
        "ANYTHINGLLM_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**获取 API Key**：打开 AnythingLLM Desktop → 设置 → API Keys → 创建新 Key

**验证连接**：重启 Claude Code 后，在对话中调用 `anythingllm_list_workspaces`，若返回 workspace 列表则连接成功。

---

## 第二步：准备知识库文档

将公司文档上传到 AnythingLLM workspace：

### 方式一：通过 AnythingLLM Desktop 界面上传

1. 打开 AnythingLLM Desktop
2. 选择目标 workspace（建议创建专用 workspace，如"投标知识库"）
3. 点击"上传文档"，选择 `Local-KnowledgeBase/` 下的文档目录中的文件
4. 等待向量化完成

### 方式二：通过 MCP 工具上传（在 Claude Code 中执行）

```
anythingllm_upload_document(
  workspace="your-workspace-slug",
  filePath="/path/to/Local-KnowledgeBase/技术方案-平台架构说明/full.md"
)
```

### 建议的文档组织

| 文档类型 | 来源目录 | 说明 |
|---------|---------|------|
| 技术方案 | `Local-KnowledgeBase/技术方案-*/` | 技术文档（Markdown + 图片） |
| 交付方案 | `Local-KnowledgeBase/交付方案-*/` | 交付相关文档 |
| 其他文档 | `Local-KnowledgeBase/*/` | 其他知识库文档 |
| 产品文档 | 产品能力说明书 | 用于 taa 产品能力评估 |

---

## 第三步：配置 taw（撰稿者）

### 方式一：命令行参数（临时指定）

```bash
# 推荐：使用 workspace slug（唯一标识符）
/taw output/ --chapter 1.3 --anythingllm-workspace "bid-kb"

# 也支持：使用 workspace 名称
/taw output/ --chapter 1.3 --anythingllm-workspace "投标知识库"
```

**如何查看 workspace slug**：

```bash
/anythingllm_list_workspaces
```

返回结果示例：
```json
[
  {"id": 1, "name": "投标知识库", "slug": "bid-kb"},
  {"id": 2, "name": "产品能力库", "slug": "product-kb"}
]
```

- `slug`：唯一标识符（推荐在命令行中使用）
- `name`：显示名称（也支持，但可能有重名风险）

### 方式二：配置文件（永久设置）

编辑 `~/.config/tender-workflow/config.yaml`：

```yaml
localkb:
  path: /path/to/Local-KnowledgeBase             # 知识库根目录（降级用）

anythingllm:
  enabled: true
  workspace: <workspace-slug-or-name>  # AnythingLLM workspace
```

workspace slug 可在 AnythingLLM Desktop 的 workspace 设置中查看，或通过 `anythingllm_list_workspaces` 获取。

---

## 第四步：配置 taa（分析者）

taa 支持三种方式指定 workspace（优先级从高到低）：

### 方式一：命令行参数（最高优先）

```bash
# 推荐：使用 workspace slug（唯一标识符）
/taa <招标文件> --anythingllm-workspace "product-kb"

# 也支持：使用 workspace 名称
/taa <招标文件> --anythingllm-workspace "产品能力库"
```

**如何查看 workspace slug**：

```bash
/anythingllm_list_workspaces
```

返回结果示例：
```json
[
  {"id": 1, "name": "产品能力库", "slug": "product-kb"},
  {"id": 2, "name": "投标案例库", "slug": "bid-cases"}
]
```

- `slug`：唯一标识符（推荐在命令行中使用）
- `name`：显示名称（也支持，但可能有重名风险）

### 方式二：配置文件（永久设置）

编辑 `~/.config/tender-workflow/config.yaml`：

```yaml
anythingllm:
  workspace: <workspace-slug-or-name>
```

或使用 twc 命令：
```bash
/twc set anythingllm.workspace "product-kb"
```

### 方式三：环境变量

```bash
export TAA_ANYTHINGLLM_WS="your-workspace-slug"
```

**自动检测**：若以上均未配置，taa 在 Phase 0 会自动检测 AnythingLLM 可用性并使用第一个 workspace。

**workspace slug 获取**：可在 AnythingLLM Desktop 的 workspace 设置中查看，或通过 `anythingllm_list_workspaces` 工具获取。

### 方式四：强制使用 AnythingLLM（`--kb-source` 参数）

```bash
# 强制使用 AnythingLLM 作为产品能力来源（不可用则报错）
/taa <招标文件> --kb-source anythingllm

# 强制使用本地索引，跳过 AnythingLLM
/taa <招标文件> --kb-source local
```

**`--kb-source` 参数说明**：

| 参数值 | 说明 |
|--------|------|
| `auto`（默认） | 先尝试 AnythingLLM，不可用则降级到本地 YAML 索引 |
| `anythingllm` | 强制使用 AnythingLLM（不可用则报错退出） |
| `local` | 强制使用本地 YAML 索引，跳过 AnythingLLM |

---

## 工作流说明

### taw 知识库检索优先级

```
AnythingLLM 语义检索（score >= 0.7，最多5条）
    ↓ 结果 < 2 条时降级
本地 YAML 三层索引（fixed → reusable → history）
    ↓ 均无结果时
互联网检索（WebSearch / Tavily / Exa）
```

### taa 产品能力评估优先级

```
--product 指定文件（最高优先，精确评估）
    ↓ 未指定时
AnythingLLM 语义检索（score >= 0.65，M2 阶段按需查询）
    ↓ 不可用时
本地 YAML 索引（V2 三层 / V1 单文件）
    ↓ 均无时
AI 模糊评估
```

**`--kb-source` 参数影响**：

| 参数值 | AnythingLLM | 本地索引 | AI 模糊评估 | 说明 |
|--------|-------------|----------|-------------|------|
| `auto`（默认） | ✅ 优先使用 | ✅ 降级 | ✅ 最终降级 | 自动检测，优先 AnythingLLM |
| `anythingllm` | ✅ 强制（失败报错） | ❌ 跳过 | ❌ 不使用 | 强制使用，不可用时报错退出 |
| `local` | ❌ 跳过 | ✅ 强制使用 | ✅ 无索引时 | 仅使用本地索引 |

**注意**：若同时使用 `--product` 和 `--kb-source anythingllm`，后者优先（强制使用 AnythingLLM）。

**AnythingLLM 查询规则**：
- 对招标文件中每个技术要求条目，执行 `anythingllm_search(query="<关键词>", workspace=<workspace>)`
- 取 `score >= 0.65` 的结果用于支持度评估
- 查询缓存机制：相同关键词不重复查询
- 查询失败降级：标注"AI 模糊评估（查询失败）"，不中断整体流程
- 每条技术要求最多调用 1 次，避免过多 API 调用

---

## 常见问题

**Q：AnythingLLM 检测失败怎么办？**

检查：
1. AnythingLLM Desktop 是否正在运行
2. MCP Server 配置是否正确（API Key、端口）
3. 重启 Claude Code 后重试

taw 和 taa 在 AnythingLLM 不可用时会自动降级到本地 YAML 索引，不影响正常使用。

**Q：如何查看当前使用的 workspace？**

运行任意 taw/taa 命令，在启动确认输出中会显示"AnythingLLM 可用（workspace: xxx）"。

**Q：搜索结果质量不好怎么优化？**

1. 确保文档已完整上传并向量化
2. 调整 AnythingLLM workspace 的相似度阈值（默认 0.25，可适当提高到 0.5）
3. 在 taw 中使用 `--no-kb` 跳过知识库，完全基于互联网检索
