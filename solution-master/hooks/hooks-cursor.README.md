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

## 维护原则

- **不要**把 Claude Code 的 `matcher` / `${CLAUDE_PLUGIN_ROOT}` 等约定混入 hooks-cursor.json（Cursor 不识别，会被忽略或报错）
- **不要**把 Cursor 的 `version: 1` / camelCase / 扁平结构混入 hooks.json
- 两份配置内容若需联动改动，务必逐字段确认各自 schema 的支持情况
