<div align="right">
  <details>
    <summary>🌐 Language</summary>
    <div>
      <div align="center">
        <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=en">English (upstream)</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=zh-CN">简体中文</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=zh-TW">繁體中文</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=ja">日本語</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=ko">한국어</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=fr">Français</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=de">Deutsch</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=es">Español</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=pt">Português</a>
        | <a href="https://openaitx.github.io/view.html?user=eze-is&project=web-access&lang=ru">Русский</a>
      </div>
    </div>
  </details>
</div>

[中文](./README.md) | **English**

<img width="879" height="376" alt="image" src="https://github.com/user-attachments/assets/a87fd816-a0b5-4264-b01c-9466eae90723" />

<p align="center">
  <b>A Skill that gives AI Agents full web-access capability.</b><br/>
  <a href="https://web-access.eze.is">🌐 Website</a> · <a href="https://mp.weixin.qq.com/s/rps5YVB6TchT9npAaIWKCw">📖 Design deep-dive</a> · <a href="#installation">⚡ Quick install</a>
</p>

The native web-access of an AI Agent (WebSearch, WebFetch) lacks scheduling strategy and browser-automation capability. This Agent Skill fills the gap: **web strategy + CDP browser operations + per-site experience accumulation**. Compatible with all Agents that support SKILL.md (Claude Code, Cursor, Gemini CLI, Codex CLI, etc.).

> Recommended reading: [Web Access: One Skill, full Agent web + browser capability](https://mp.weixin.qq.com/s/rps5YVB6TchT9npAaIWKCw) — covers the development details of Web-Access Skill and Agent Skill design philosophy, helping you build similarly general, high-ceiling Skills.

---

## v2.5.0 capabilities

| Capability | Description |
|---|---|
| Auto web-tool selection | WebSearch / WebFetch / curl / Jina / CDP, picked autonomously by scenario, freely combinable |
| CDP Proxy browser ops | Direct connection to the user's daily Chrome, naturally carries login state, supports dynamic pages, interactive ops, video frame capture |
| Three click methods | `/click` (JS click), `/clickAt` (CDP real mouse event), `/setFiles` (file upload) |
| Local Chrome bookmark / history search | `find-url.mjs` finds targets unsearchable on the public web (internal systems) or pages the user has visited; supports keyword / time-window / visit-frequency ranking |
| Parallel divide-and-conquer | For multiple targets, dispatch sub-Agents to run in parallel sharing one Proxy with tab-level isolation |
| Per-site experience | Stores ops experience by domain (URL patterns, platform features, known pitfalls), reusable across sessions |
| Media extraction | Direct image / video URL from DOM, or analyze video frames captured at any timestamp |

**v2.5.0 update:**

- **Local Chrome resource lookup** — added `scripts/find-url.mjs`, locates URLs from local Chrome bookmarks / history by keyword / time window / visit frequency. Typical scenarios: user mentions an internal system ("our XX platform" — unsearchable on public web), look up a page they visited but don't remember the URL, view recent high-frequency sites (scenario suggested by @MVPGFC in #60).

<details><summary>v2.4.3 update</summary>

- **Fix CLAUDE_SKILL_DIR path issue** — bash code blocks switched to `${CLAUDE_SKILL_DIR}` string-substitution syntax, fixing Windows Git Bash path-conversion errors and unset-variable issues (#47 #46)
- **Per-site experience list merged into pre-flight check** — after the startup check passes, the existing per-site experience list is auto-output, removing the unreliable `!` inline injection
</details>

<details><summary>v2.4.1 update</summary>

- **Cross-platform support** — scripts migrated from bash to Node.js, runs on Windows / Linux / macOS
- **DOM boundary penetration** — added technical fact: eval recursive traversal can pierce Shadow DOM, iframe, and other selector-uncrossable boundaries
</details>

<details><summary>v2.4 update</summary>

- **In-site URL reliability** — added fact: site-generated links carry full implicit context, manually constructed URLs may miss implicit required params
- **Platform error messages untrustworthy** — added technical fact: platform-returned "content not found" can be an access-method issue rather than the content itself
- **Xiaohongshu (RED) per-site experience hardened** — xsec_token mechanism, creator platform state validation, draft-save flow
</details>

<details><summary>v2.3 update</summary>

- **Browsing philosophy refactor** — clearer "think like a human" framework, emphasizing goal-driven over step-driven
- **Active Jina recommendation** — explicitly encourages using Jina to save tokens in suitable scenarios
- **Sub-Agent prompt guidance** — clearer load instructions, with notes on avoiding verbs that imply execution methods
</details>

> **Install**: see the root [README_EN.md#install](../../../README_EN.md#install) (installs as a shared plugin under the `presales-skills` umbrella marketplace).
>
> Standalone upstream distribution: [eze-is/web-access](https://github.com/eze-is/web-access) (independent install path when not using presales-skills).

## Pre-configuration (CDP mode)

CDP mode requires **Node.js 22+** and Chrome with remote debugging enabled:

1. Open `chrome://inspect/#remote-debugging` in Chrome's address bar
2. Tick **Allow remote debugging for this browser instance** (browser restart may be needed)

Environment check (the Agent's runtime auto-runs the pre-flight check; no manual run needed):

```bash
node "${CLAUDE_SKILL_DIR}/scripts/check-deps.mjs"
# $CLAUDE_SKILL_DIR is the env var auto-set when the skill loads
```

## MCP installer (presales-skills integration)

`scripts/mcp_installer.py` registers search-class MCP servers (tavily / exa / minimax-token-plan) into `~/.claude.json`. Called by the setup wizards of [tender-workflow](https://github.com/Alauda-io/presales-skills) and [solution-master](https://github.com/Alauda-io/presales-skills); also runnable standalone via CLI.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" check uv
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" auto-install uv
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" probe minimax
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" register minimax --key=sk-cp-xxxx
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" test minimax        # stdio live-test web_search + understand_image
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" unregister minimax
python3 "${CLAUDE_SKILL_DIR}/scripts/mcp_installer.py" list-search-tools --include-builtin
#   ↑ Enumerates all MCP servers registered in ~/.claude.json, spawns each to run MCP tools/list,
#     heuristically filters for web-search-class tools, outputs JSON Lines (server / tool / fqn / description).
#     Used by tender-workflow / solution-master setup wizards to "dynamically discover available search MCPs and let the user pick a default".
#     --include-builtin appends WebSearch (Claude Code built-in) as a fallback candidate.
#     --all skips heuristics and outputs all tools (for manual user selection).
```

`auto-install` uses user-level paths (uv via astral.sh install.sh / install.ps1; node prefers fnm / brew / winget), no sudo required; only emits `NEEDS_USER_ACTION` in fallback cases for the wizard to forward the command. The `test` sub-command spawns the server to perform the MCP JSON-RPC handshake (initialize → notifications/initialized → tools/call) — **does not depend on reload-plugins**, validates immediately after config write. minimax keys must have an `sk-cp-` prefix (regular chat keys are not MCP-compatible, see [MiniMax-AI/MiniMax-M2 issue #96](https://github.com/MiniMax-AI/MiniMax-M2/issues/96)).

> **Path style**: the examples above use `${CLAUDE_SKILL_DIR}`, which is set when web-access's own skill loads. When called by the tender-workflow / solution-master setup wizard, the wizard resolves the absolute path via the `installed_plugins.json` bootstrap probe, so the command becomes `python3 "$WA_INSTALLER" check uv` (where `WA_INSTALLER=<web-access install path>/skills/browse/scripts/mcp_installer.py`). The two styles are equivalent — pick by calling context.

## CDP Proxy API

The Proxy connects directly to Chrome via WebSocket (compatible with the `chrome://inspect` flow, no command-line args needed to launch), providing an HTTP API:

```bash
# Start (the Agent auto-manages the Proxy lifecycle; no manual launch needed)
node "${CLAUDE_SKILL_DIR}/scripts/cdp-proxy.mjs" &

# Page operations
curl -s "http://localhost:3456/new?url=https://example.com"     # New tab
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.title'  # Run JS
curl -s -X POST "http://localhost:3456/click?target=ID" -d 'button.submit'  # JS click
curl -s -X POST "http://localhost:3456/clickAt?target=ID" -d '.upload-btn'  # Real mouse click
curl -s -X POST "http://localhost:3456/setFiles?target=ID" \
  -d '{"selector":"input[type=file]","files":["/path/to/file.png"]}'        # File upload
curl -s "http://localhost:3456/screenshot?target=ID&file=/tmp/shot.png"     # Screenshot
curl -s "http://localhost:3456/scroll?target=ID&direction=bottom"           # Scroll
curl -s "http://localhost:3456/close?target=ID"                             # Close tab
curl -s "http://localhost:3456/health"                                      # Status (with managedTabs count)
```

The Proxy auto-tracks tabs created via `/new` and auto-closes idle tabs after 15 minutes, preventing orphan tabs when the Agent exits abnormally. Adjust the timeout via `CDP_TAB_IDLE_TIMEOUT` (in milliseconds).

## ⚠️ Heads-up before using

Browser-automating social platforms (like Xiaohongshu) carries a real risk of platform rate-limiting or account banning. **Strongly recommend using a secondary account.**

## Usage

After installing, just ask the Agent to perform a web task — the skill auto-takes over:

- "Search the latest XX news for me"
- "Read this page: [URL]"
- "Find XX's account on Xiaohongshu"
- "Post an image-text post on the creator platform for me"
- "Research these 5 products' official sites simultaneously and give me a comparison summary"

## Design philosophy

> Skill = philosophy + technical facts, not operation manual. Surface the tradeoffs, let the AI choose; don't reason for it.

The core is the 4-step "think like a human" decision framework:

1. **Receive the request** — clarify goal, define success criteria
2. **Pick a starting point** — choose the path most likely to reach the goal directly
3. **In-process verification** — check each step's result against success criteria; if direction is wrong, adjust immediately
4. **Completion judgment** — stop once success criteria are met; don't over-operate for "completeness"

Execution details (specific decision points for each web task) — see [SKILL.md §Browsing philosophy](./SKILL.md).

## License

MIT · Author: [Eze](https://github.com/eze-is) · [Website](https://web-access.eze.is)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=eze-is/web-access&type=Date)](https://star-history.com/#eze-is/web-access&Date)

## Clawhub Download History

[![Download History](https://skill-history.com/chart/eze-is/web-access.svg)](https://skill-history.com/eze-is/web-access)

<img width="1280" height="306" alt="image" src="https://github.com/user-attachments/assets/2afa25c2-3730-413e-b40f-94e52567249d" />
