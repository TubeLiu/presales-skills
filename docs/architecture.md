# 架构原理

本文件描述 presales-skills monorepo 的设计选择与运行时约定。读者：维护者、贡献者、想理解为什么这么组织的用户。

跨 plugin 工程纪律（版本号 bump / 路径解析 / 运行时陷阱）见仓库根 [CLAUDE.md](../CLAUDE.md)。

---

## 1. 仅用 `skills/`（不用 `commands/` / `agents/`）

9 个有用户入口的 plugin（ai-image / web-access / drawio / solution-master / ppt-master / tender-workflow / customer-research / skill-optimizer / market）和 5 个 tender-workflow sub-skill 全部用 `skills/<X>/SKILL.md` 注册；`anythingllm-mcp` 是 MCP server 型 plugin，无 slash 入口。**不用** Claude Code 的 `commands/` 或 `agents/` 机制，原因：

- `skills/` 是唯一被 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 识别 + 拷贝的格式 → 同一 SKILL.md 既给 Claude Code 用又给 Cursor / Codex / OpenCode 用
- `description:` 字段提供自然语言 auto-trigger，省去用户记忆 slash 名
- `commands/` 仅 Claude Code 识别，加了它 = Cursor / Codex 用户体验降级

参考：[anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) 中的 frontend-design / mcp-server-dev / claude-code-setup 都是同款"仅 skills/"设计。

---

## 2. Skill 命名约定

每个 sub-skill 目录名 ≠ plugin 名（消除 `<plugin>:<plugin>` 双名）。Claude Code 注册形式：

- canonical = `<plugin>:<dir-name>`（如 `/ai-image:gen`）
- alias = SKILL.md `name:` 字段（如 `/image-gen` 自动补全到 `/ai-image:gen`）

vercel CLI 装到 Codex / Cursor 时按 SKILL.md `name:` 命名 dir，slash 直接是 `/<name>` 短形式（无 plugin 前缀）。

---

## 3. 跨 plugin 调用约定

跨 plugin 调用通过查询 `~/.claude/plugins/installed_plugins.json` 拿到对方 plugin 的 `installPath`，再拼脚本绝对路径。**不假设兄弟相对路径**——Claude Code 的 cache 布局是 `<plugin>/<version>/skills/<sub-skill>/`，跨 plugin 不是兄弟。

每个 SKILL.md §路径自定位 段提供五段式 fallback：

1. `~/.claude/plugins/installed_plugins.json`（Claude Code 权威来源，精确指向当前激活版本）
2. `~/.cursor/skills` / `~/.agents/skills` / `.cursor/skills` / `.agents/skills`（vercel CLI 标准目录）
3. 用户预设环境变量 `<PLUGIN>_PLUGIN_PATH`（如 `DRAWIO_PLUGIN_PATH`）
4. cwd 相对 `./` 和 `../`（dev 态）
5. 全失败 → 输出诊断 + 退出 1（让 Claude 转述给用户，要求 export 环境变量或安装缺失 plugin）

---

## 4. 跨 sub-skill 引用（同 plugin 内）

同 plugin 内的 sub-skill 之间用 `$SKILL_DIR/../<sibling>/...` 兄弟相对路径。Claude Code marketplace cache 与 Cursor / Codex flat layout 下都成立（同 plugin 的 sub-skill 总是兄弟）。`tests/test_skill_format.py` 第 10 项断言 `test_cross_skill_refs_within_plugin` 强制此规则。

---

## 5. SessionStart hook（仅 solution-master）

10 个 plugin 中**仅 solution-master** 注册 SessionStart hook（Claude Code 用 `hooks.json`，Cursor 用 `hooks-cursor.json`）：

- **项目门禁**：仅当 cwd 含 `drafts/` / `docs/specs/` / `skills/go/SKILL.md` / `.claude/skills/go/SKILL.md` 任一时触发
- 触发后 cat 主 SKILL.md 全文注入到 additionalContext（铁律 + 文件导航 + 子智能体调度全量）
- 其它 plugin 不重复注册——多个同步 hook 会让会话启动时间线性叠加；其它 plugin 的提示性内容用 SKILL description 承载即可

其它 agent（Codex / OpenCode）暂无 hook 机制；铁律靠主 SKILL.md description 自然语言匹配触发（best-effort）。

---

## 6. 子智能体调度（solution-master / tender-workflow taw）

solution-master 与 tender-workflow `taw` 的子智能体（writer / spec-reviewer / quality-reviewer）通过 **Task tool** 委派——把 `agents/<role>.md` 完整内容作为 Task prompt body 传入：

```python
Task(
  subagent_type="general-purpose",
  description="撰写章节 N: <章节名>",
  prompt="""<agents/writer.md 完整内容>

  ## 你的任务
  ...
  """
)
```

不支持 Task tool 的 agent：在主上下文顺序执行，章节之间显式输出 `---RESET CONTEXT FOR <章节名>---` 边界（近似隔离，非真隔离）。

---

## 7. web 搜索 MCP server 的统一注册

`web-access/skills/browse/scripts/mcp_installer.py` 提供 6 子命令 CLI（`check` / `auto-install` / `probe` / `register` / `test` / `unregister`），把 tavily / exa / minimax-token-plan 三类用户级 MCP server 统一注册到 `~/.claude.json`。

tender-workflow / solution-master 的 setup wizard 通过 `installed_plugins.json` 探针定位本脚本调用，避免在两个 wizard 内重复 inline python。

设计要点：

- `auto-install` 走用户级路径（uv 用 astral.sh install.sh / install.ps1；node 优先 fnm / brew / winget）**不要 sudo**
- `test` 子命令独立 spawn server 跑 MCP JSON-RPC 握手 + tools/call 实测，**不依赖 reload-plugins**
- `list-search-tools` 子命令实时枚举当前会话所有可用搜索 MCP（让 sm / tw setup 动态选默认）

---

## 8. 配置文件物理布局

monorepo 故意不合并配置——每个工作流 plugin 配置独立，共享层放共享配置。详见 [docs/configuration.md](configuration.md)。

| 文件 | 用途 |
|---|---|
| `~/.config/presales-skills/config.yaml` | 共享：API keys / ai_image / ppt_master.default_layout |
| `~/.config/solution-master/config.yaml` | sm 专属：localkb / anythingllm / cdp_sites / drawio / mcp_search |
| `~/.config/tender-workflow/config.yaml` | tw 专属：tender 流程参数 |
| `~/.claude.json` | Claude Code 自身：mcpServers 注册（tavily / exa / minimax / anythingllm 等） |
