# hooks-cursor.json — Cursor 1.x schema 说明（F-031 / F-032）

本目录有两份 hook 配置：

| 文件 | 目标编辑器 | Schema |
|------|-----------|--------|
| `hooks.json` | Claude Code | PascalCase `SessionStart`、`matcher`、嵌套 `hooks` 数组、`type: command`、`${CLAUDE_PLUGIN_ROOT}` 文本注入 |
| `hooks-cursor.json` | Cursor 1.x | camelCase `sessionStart`、扁平结构、相对路径 `command` |

**两套 schema 不可互通**：

```json
// Claude Code (hooks.json)
{
  "hooks": {
    "SessionStart": [{"matcher": "startup|clear|compact", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd session-start"}]}]
  }
}

// Cursor (hooks-cursor.json)
{
  "version": 1,
  "hooks": {
    "sessionStart": [{"command": "./hooks/session-start"}]
  }
}
```

## 已知差异（与 Claude Code 对照）

| 维度 | Claude Code | Cursor |
|------|-------------|--------|
| `matcher` 字段 | 支持，可选 startup / clear / compact | **不支持** — Cursor 1.x schema 无此字段；hook 对所有 sessionStart 事件响应 |
| `${CLAUDE_PLUGIN_ROOT}` 注入 | 支持 | **不支持** — Cursor 不展开此变量；当前用相对路径 `./hooks/session-start` |
| 跨平台 wrapper | `run-hook.cmd` polyglot | **不提供** — Cursor 直接 exec 无扩展名脚本，Windows 兼容性未做实机测试 |

## Windows + Cursor 已知风险

Windows 下 Cursor 直接执行 `./hooks/session-start`（无 `.sh` 扩展名）的兼容性未验证。
若 Cursor + Windows 用户反馈"hook 不触发"，可能需要：

1. 把 `hooks-cursor.json` 的 `command` 改为带扩展名的 wrapper（如 `./hooks/session-start.bat`）
2. 或在 hooks 目录新增针对 Cursor 的专用包装

## 相对路径 cwd 风险（F-018）

`hooks-cursor.json:6` 用相对路径 `"./hooks/session-start"`。Cursor 文档（cursor.com/docs/agent/hooks）明确说明：

> **hook 运行时 cwd**：项目级 hook 从 project root；用户级 hook 从 `~/.cursor/`。**不是 plugin 安装目录**。
> **环境变量**：仅 `CURSOR_PROJECT_DIR` / `CURSOR_VERSION` / `CURSOR_USER_EMAIL` 等，**无 CURSOR_PLUGIN_ROOT**。

后果：用户在自己项目里启动 Cursor 时，`./hooks/session-start` 解析为 `<user-project>/hooks/session-start`——不是 plugin 目录里的 hook 脚本——**沉默失败**（铁律注入跳过，但会话能继续）。

### 当前缓解 + 建议

1. **本仓库 dev 态**（cwd = `presales-skills/`）能 work：相对路径恰好对应 `solution-master/hooks/session-start`（不是直接命中，但近似）
2. **vercel CLI 装到 Cursor 后**：hook 文件位置在 `~/.cursor/skills/solution-master/hooks/session-start`（或 `<project>/.cursor/skills/...`）。当前相对路径不会命中。
3. **建议变通**：用户若依赖此 hook 的铁律注入，需在 Cursor settings 手工把 sessionStart hook command 改为绝对路径，例：
   ```json
   {"command": "/Users/<you>/.cursor/skills/solution-master/hooks/session-start"}
   ```
   或全局安装路径 `~/.cursor/skills/solution-master/hooks/session-start`。
4. **不阻塞**：hook 失败时 Cursor 不报错，仅缺铁律注入。其它 SKILL description 触发机制仍可工作；Layer 2 防御（agents/{spec,quality}-reviewer.md 内的"不信任报告"段）不依赖 hook，仍生效。

### 为什么不在 plugin 里修

- Cursor 不支持 `${CURSOR_PLUGIN_ROOT}` 文本替换，无法 plugin-portable 写法
- 写绝对路径需要用户自己机器路径，不能在仓库里硬编码
- vercel CLI 装时也不会 rewrite hook command（CLI 仅 copy 文件）

如未来 Cursor 加入 `CURSOR_PLUGIN_ROOT` 变量或 plugin install 自动 rewrite hook 路径，再 revisit。

## 维护原则

- **不要**把 Claude Code 的 `matcher` / `${CLAUDE_PLUGIN_ROOT}` 等约定混入 hooks-cursor.json（Cursor 不识别，会被忽略或报错）
- **不要**把 Cursor 的 `version: 1` / camelCase / 扁平结构混入 hooks.json
- 两份配置内容若需联动改动，务必逐字段确认各自 schema 的支持情况
