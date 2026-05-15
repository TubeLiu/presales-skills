# 跨 agent 兼容性

主用 Claude Code；其它 agent 通过 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 装得到核心能力，但 hook / MCP / 跨 plugin 引用等高级特性会降级。

---

## 1. 兼容性矩阵

| Feature | Claude Code | Cursor (skills CLI) | Codex (skills CLI) | OpenCode (skills CLI) |
|---|---|---|---|---|
| `/<plugin>:<sub-skill>` slash 形式 | ✅ canonical | ✅（短形式 `/<sub-skill>`）| ✅（短形式 `/<sub-skill>`）| ✅（短形式 `/<sub-skill>`） |
| 自然语言 auto-trigger（SKILL.md description）| ✅ | ✅ | ✅ | ✅ |
| `${CLAUDE_PLUGIN_ROOT}` 占位符 | ✅ | ❌（无替换）| ❌ | ❌ |
| SessionStart hook（solution-master）| ✅ `hooks.json` | ✅ `hooks-cursor.json` | ❌ | ❌ |
| MCP server（anythingllm-mcp） | ✅ 自动 `plugin.json mcpServers` | ❌ 需手动 `.cursor/mcp.json` | ❌ 需手动配 | ❌ 需手动配 |
| `installed_plugins.json` 自定位 | ✅ | ❌（用 `.cursor/skills/` fallback）| ❌（用 `.agents/skills/` fallback）| ❌ |
| 跨 sub-skill 引用 `$SKILL_DIR/../<other>/` | ✅（同 plugin 内）| ✅（flat layout 兄弟）| ✅（flat layout 兄弟）| ✅ |
| 跨 plugin 引用 | ✅ 用 `installed_plugins.json` | ⚠ 用自然语言 / `Skill(skill="<plugin>:<sub>")` | ⚠ 同上 | ⚠ 同上 |
| `mcp_installer.py` 注册 web 搜索 MCP（tavily / exa / minimax） | ✅ 写 `~/.claude.json` reload 即生效 | ⚠ 配置文件位置不同，需手动套 schema | ⚠ 同上 | ⚠ 同上 |
| `mcp_installer.py list-search-tools` 动态发现已装 MCP | ✅ 直接读 `~/.claude.json` + spawn 各 server `tools/list` | ❌ 不可用（脚本硬编码 `~/.claude.json` 路径，Cursor / Codex 无此文件）；用户需手写 `mcp_search.priority` FQN 列表 | ❌ 同上 | ❌ 同上 |

> **维护者承诺范围**：端到端流程**仅在 Claude Code 上完整验证**。Cursor / Codex / OpenCode 上通过 vercel-labs/skills CLI 安装能跑通基础场景；hook、MCP server 自动注册、跨 plugin 引用等需自行配置或绕开——欢迎社区把验证结果反馈到 issue tracker。

---

## 2. Cursor / Codex / OpenCode 装载

```bash
npx --yes skills add TubeLiu/presales-skills -a cursor   # Cursor
npx --yes skills add TubeLiu/presales-skills -a codex    # Codex
npx --yes skills add TubeLiu/presales-skills -a opencode # OpenCode
```

vercel-labs/skills CLI 会扫描所有 SKILL.md 并 symlink / copy 到目标 agent 的标准目录。

- **默认装到 cwd `.agents/skills/`**（项目级）
- 加 `-g` 装到 `~/.agents/skills/`（全局）
- 只装部分 sub-skill：`-s '*'` 装全部，或 `-s image-gen,draw,make,optimize` 指定
- 完整 CLI 参数：`npx --yes skills --help`

---

## 3. Windows 适配

### 推荐方式（二选一）

- **WSL 2**：零改动，原生 Linux 体验
- **Windows 原生 + [Git for Windows](https://git-scm.com/downloads/win)**：Claude Code 自身依赖 Git Bash（[官方说明](https://docs.claude.com/en/docs/claude-code/setup)）。装完 Git for Windows + Python ≥ 3.10 即可

**不支持**：纯 PowerShell / CMD + 不装 Git for Windows。

### Windows 适配点

每个 SKILL.md 顶部都有 §跨平台兼容性 checklist 段提醒，但维护者修改时要主动确认：

- `python3` 命令在 Windows 原生若不可识别，用 `python` 或 `py -3`
- `ppt-master` 需要 pandoc + GTK runtime（`choco install pandoc` + [GTK runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)）
- `web-access` 的 CDP 自动化在 Windows 原生 cmd / PowerShell best-effort——优先在 Git Bash / WSL2 中运行
- **不要用 MSYS2 Python 代替原生 Windows Python**（`platform.system()` 在 MSYS2 下返回 `MSYS_NT-10.0`，会触发 ppt-master 的非 Windows 异常分支）

### macOS / Linux

零特殊步骤，按 [README 安装](../README.md#安装) 路径走即可。`ppt-master` 需要系统级 pandoc + cairo：

```bash
brew install pandoc cairo                 # macOS
apt install pandoc libcairo2-dev          # Debian / Ubuntu
```
