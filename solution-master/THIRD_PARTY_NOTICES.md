# 第三方组件来源声明

Solution Master 在构建过程中从以下第三方开源项目 vendor（借用 + 改写）了部分文件。所有借用内容均遵守原项目的 MIT 许可证，并在本文件中集中标注出处。

## superpowers-zh

- **项目主页**：https://github.com/jnMetaCode/superpowers-zh
- **许可证**：MIT License © 2026 jnMetaCode
- **上游（英文原版）**：https://github.com/obra/superpowers © Jesse Vincent
- **Vendor 源 commit**：`4a55cbf9f348ba694cf5cbf4d56df7340ff2b74f` (2026-03-27)

### 借用文件清单

| Solution Master 路径 | superpowers-zh 源路径 | 改写程度 | 说明 |
|---|---|---|---|
| `hooks/session-start` | `hooks/session-start` | 小 | 变量重命名 `PLUGIN_ROOT`→`SM_ROOT`；注入文本改为 Solution Master 上下文；读取的 SKILL 从 `using-superpowers` 改为 `using-solution-master`；新增项目门禁逻辑；保留 `escape_for_json`、Cursor/Claude Code 双格式输出、bash 5.3+ heredoc 规避等所有技术细节 |
| `hooks/run-hook.cmd` | `hooks/run-hook.cmd` | 无 | 跨平台包装器原样保留 |
| `hooks/hooks.json` | `hooks/hooks.json` | 无 | SessionStart schema 原样保留 |
| `hooks/hooks-cursor.json` | `hooks/hooks-cursor.json` | 小 | schema 保留，命令改为 Solution Master 的 session-start |
| `skills/using-solution-master/SKILL.md` | `skills/using-superpowers/SKILL.md` | 中 | 保留 "1% 适用就必须调用" 段落、红线检查表、子智能体跳过标签等核心反合理化机制；替换技能列表为 Solution Master 的技能；追加 7 条 Solution Master 铁律 |
| `skills/subagent-driven-writing/SKILL.md` | `skills/subagent-driven-development/SKILL.md` | 中 | 措辞从代码开发调整为文档撰写；角色名 `implementer`→`writer`、`code-reviewer`→`quality-reviewer`；保留两阶段审查流程、红线清单、状态汇报标签 |
| `skills/subagent-driven-writing/writer-prompt.md` | `skills/subagent-driven-development/implementer-prompt.md` | 小 | 改名 + 措辞从代码改为章节，保留所有反作弊机制（前置自审、DONE_WITH_CONCERNS、文件超规模上报） |
| `skills/subagent-driven-writing/spec-reviewer-prompt.md` | `skills/subagent-driven-development/spec-reviewer-prompt.md` | 小 | "不要信任报告" 段落原文保留 |
| `skills/subagent-driven-writing/quality-reviewer-prompt.md` | 新文件（派生自 SKILL.md 中 code-reviewer 角色） | 中 | Solution Master 根据 spec-reviewer-prompt.md 模板派生的质量审查版本 |

### superpowers-zh 原项目 LICENSE

```
MIT License

Copyright (c) 2026 jnMetaCode

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

### 改名映射

为了体现 Solution Master 是文档撰写场景（而非代码开发），以下技能 / 角色进行了改名：

| superpowers-zh | solution-master |
|---|---|
| `using-superpowers` | `using-solution-master` |
| `subagent-driven-development` | `subagent-driven-writing` |
| `implementer`（角色） | `writer`（角色） |
| `implementer-prompt.md` | `writer-prompt.md` |
| `code-reviewer`（角色） | `quality-reviewer`（角色） |
| `code-quality-reviewer-prompt.md` | `quality-reviewer-prompt.md` |
