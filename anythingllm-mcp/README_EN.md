# anythingllm-mcp

[中文](./README.md) | **English**

AnythingLLM MCP server — provides knowledge base semantic search, shared by other plugins under `presales-skills` (`solution-master`, `tender-workflow`, etc.).

## Exposed MCP tools

- `anythingllm_search` — semantic search in a specified workspace; returns AI answer + relevant document chunks
- `anythingllm_list_workspaces` — list all available workspaces (with name and slug)

Claude Code exposes these as `mcp__anythingllm__anythingllm_search` and `mcp__anythingllm__anythingllm_list_workspaces`.

> **Install**: see the root [README.md#install](../README_EN.md#install). Once installed, Claude Code auto-registers the `anythingllm` MCP server via the `mcpServers` field in `plugin.json` — no manual edits to `~/.claude.json` needed.

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `ANYTHINGLLM_BASE_URL` | `http://localhost:3001` | AnythingLLM API endpoint |
| `ANYTHINGLLM_API_KEY` | (empty) | API key, **required**; create one in AnythingLLM Desktop → Settings → API Keys |
| `ANYTHINGLLM_WORKSPACE` | (empty) | Default workspace slug; if unset, the first workspace is used |

Inject via env in Claude Code's MCP launch command, or write to user-level config through the main plugin's setup flow (e.g., `tender-workflow`'s `twc` / `solution-master`'s `solution-config`).

## Prerequisites

1. AnythingLLM Desktop running locally: `curl http://localhost:3001/api/ping` returns `{"online":true}`
2. At least one workspace created and seeded with documents

## Dependencies

`anythingllm-mcp` is called by:

- `solution-master` — used as an optional backend in the `knowledge-retrieval` skill
- `tender-workflow` — product knowledge base retrieval in `taa` / `taw` / `trv` skills

When `mcp__anythingllm__*` tools are missing, these plugins gracefully degrade to local YAML index or web search rather than hard-failing; but to enable the semantic-search path, this plugin must be installed alongside.

## Zero dependencies

`index.js` only uses Node built-in modules (`readline` / `http` / `https` / `url`), no `package.json.dependencies`. No `npm install` required.
