# anythingllm-mcp

AnythingLLM MCP server — 提供知识库语义搜索能力，被 `presales-skills` 下的其他 plugin（`solution-master`、`tender-workflow` 等）共用。

## 暴露的 MCP 工具

- `anythingllm_search` — 在指定 workspace 中做语义搜索；返回 AI 回答 + 相关文档片段
- `anythingllm_list_workspaces` — 列出所有可用 workspace（含 name、slug）

Claude Code 会把它们暴露为 `mcp__anythingllm__anythingllm_search` 和 `mcp__anythingllm__anythingllm_list_workspaces`。

> **安装**：见仓库根 [README.md#安装](../README.md#安装)。装好后 Claude Code 会根据 `plugin.json` 的 `mcpServers` 字段自动注册 `anythingllm` MCP server，无需手工改写 `~/.claude.json`。

## 配置（环境变量）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ANYTHINGLLM_BASE_URL` | `http://localhost:3001` | AnythingLLM API 地址 |
| `ANYTHINGLLM_API_KEY` | （空） | API Key，**必填**；从 AnythingLLM Desktop → 设置 → API Keys 创建 |
| `ANYTHINGLLM_WORKSPACE` | （空） | 默认 workspace slug；若不设置则自动取第一个 |

在 Claude Code 的 MCP 启动命令里通过 env 注入，或由主 plugin（如 `tender-workflow`）的 `twc` / `solution-config` 配置流程写入用户级配置后读取。

## 前置条件

1. 本机运行 AnythingLLM Desktop：`curl http://localhost:3001/api/ping` 返回 `{"online":true}`
2. 已创建至少一个 workspace 并投喂文档

## 依赖关系

`anythingllm-mcp` 被以下 plugin 调用：

- `solution-master` — `knowledge-retrieval` skill 作为可选后端
- `tender-workflow` — `taa` / `taw` / `trv` 等 skill 的产品知识库检索

这些 plugin 会在缺少 `mcp__anythingllm__*` 工具时降级为本地 YAML 索引或联网检索，不会 hard-fail；但要启用语义搜索路径，必须一并安装本 plugin。

## 零依赖

`index.js` 仅使用 Node 内置模块（`readline`/`http`/`https`/`url`），无 `package.json.dependencies`。用户无需 `npm install`。
