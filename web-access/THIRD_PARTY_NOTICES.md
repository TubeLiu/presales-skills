# 第三方组件来源声明

本 plugin（`web-access`）的 skill 内容整包 vendored 自上游开源项目 `eze-is/web-access`，所有借用内容均遵守原项目的 MIT 许可证。

## eze-is/web-access

- **项目主页**：https://github.com/eze-is/web-access
- **许可证**：MIT License © 一泽 Eze
- **Vendor 源版本**：v2.5.0
- **Vendor 范围**：`skills/web-access/` 下的所有内容（`SKILL.md` / `README.md` / `scripts/*.mjs` / `references/`）

### 本地改写清单

| 本 plugin 路径 | 上游源路径 | 改写程度 | 说明 |
|---|---|---|---|
| `skills/web-access/SKILL.md` | `SKILL.md` | 无 | 原样保留 v2.5.0 内容 |
| `skills/web-access/scripts/*.mjs` | `scripts/*.mjs` | 无 | 原样保留 |
| `skills/web-access/references/cdp-api.md` | `references/cdp-api.md` | 极小 | 仅把行 6 的 `~/.claude/skills/web-access/...` 硬编码路径改为 `${CLAUDE_SKILL_DIR}/...`（plugin 安装模式下硬编码路径不成立） |
| `skills/web-access/README.md` | `README.md` | 极小 | 方式四手动安装段落改为 `/plugin install web-access@presales-skills`；删除 `${CLAUDE_SKILL_DIR}` 冗余注释 |
| `bin/web-access-check`、`bin/web-access-match-site` | — | 新增 | 跨 plugin 调用入口（solution-master 通过这两个命令使用本 plugin） |

### eze-is/web-access 原项目 LICENSE

```
MIT License

Copyright (c) 2026 一泽 Eze

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
