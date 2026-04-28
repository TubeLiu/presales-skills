# web-access — Web access + CDP browser automation

[中文](./README.md) | **English**

A **shared plugin** in the `presales-skills` marketplace, equipping AI Agents with full web-access capability — unified scheduling across WebSearch / WebFetch / curl / Jina / CDP browser automation, plus authenticated-site scraping and per-site experience accumulation. Used by solution-master / tender-workflow (when cdp_sites is enabled or MCP search is registered).

> 🙏 **Upstream attribution**: this plugin is fully vendored from [eze-is/web-access](https://github.com/eze-is/web-access) v2.5.0 (MIT License © Eze) — the core SKILL.md, CDP Proxy scripts, references, and design philosophy all follow upstream design and implementation. This repo adapts the layout to the presales-skills marketplace conventions (path substitution + plugin integration + an additional `mcp_installer.py` tool). Thanks to Eze for the open-source work. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for the full borrowed-files list and the original LICENSE.

---

## Core capabilities

- **Auto web-tool selection**: WebSearch / WebFetch / curl / Jina / CDP, picked autonomously by scenario, freely combinable
- **CDP Proxy browser ops**: direct connection to the user's daily Chrome, naturally carries login state, supports dynamic pages, interactive ops, video frame capture
- **Three click methods**: `/click` (JS click), `/clickAt` (CDP real mouse event), `/setFiles` (file upload)
- **Local Chrome bookmark / history search**: `find-url.mjs` finds targets unsearchable on the public web (internal systems) or pages the user has visited
- **Parallel divide-and-conquer**: for multiple targets, dispatch sub-Agents to run in parallel sharing one Proxy with tab-level isolation
- **Per-site experience**: stores ops experience by domain (URL patterns, platform features, known pitfalls), reusable across sessions
- **Media extraction**: direct image / video URL from DOM, or analyze video frames captured at any timestamp
- **MCP search installer** (presales-skills integration): bundled `mcp_installer.py`, called by `/twc setup` / `/solution-master setup` to one-click register tavily / exa / minimax-token-plan web search MCP servers into `~/.claude.json`

## Slash entry points

| Trigger | Form |
|---|---|
| Claude Code canonical | `/web-access:browse "..."` |
| Codex / Cursor / OpenCode short alias | `/browse "..."` |
| Natural language auto-trigger | "search X for me" / "fetch this page" / "find someone's account on Xiaohongshu" / "post an image-text on the creator platform" / "research these 5 product sites in parallel" |

## Detailed usage docs

For the complete capability list, CDP Proxy API, MCP installer usage, and design philosophy, see the sub-skill README:

→ [`skills/browse/README.md`](./skills/browse/README.md) | [`skills/browse/README_EN.md`](./skills/browse/README_EN.md)

## Install

> **Install**: see the root [README_EN.md#install](../README_EN.md#install) (installs as a shared plugin under the `presales-skills` umbrella marketplace).

CDP mode additionally requires **Node.js 22+** and Chrome remote debugging. See [`skills/browse/README_EN.md` §Pre-configuration (CDP mode)](./skills/browse/README_EN.md#pre-configuration-cdp-mode).

> Standalone upstream distribution: [eze-is/web-access](https://github.com/eze-is/web-access) (independent install path when not using presales-skills).

## Relationship with other plugins

| Main plugin | What it uses web-access for |
|---|---|
| **solution-master** | CDP authenticated-site retrieval (required when `cdp_sites.enabled=true`); `mcp_installer.py` registers MCP search tools |
| **tender-workflow** | `/twc setup` calls `mcp_installer.py` to register tavily / exa / minimax; taw uses MCP search while writing chapters |

Without web-access installed, main plugins gracefully degrade to the built-in `WebSearch`.

## ⚠️ Heads-up before using

Browser-automating social platforms (like Xiaohongshu) carries a real risk of platform rate-limiting or account banning. **Strongly recommend using a secondary account.**

## Third-party components

Fully vendored from [eze-is/web-access](https://github.com/eze-is/web-access) v2.5.0 (MIT License). See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for details.
