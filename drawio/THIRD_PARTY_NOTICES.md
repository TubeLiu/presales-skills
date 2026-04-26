# 第三方组件来源声明

drawio plugin 在构建过程中从以下第三方开源项目 vendor（借用 + 改写）了部分文件。所有借用内容均遵守原项目的 MIT 许可证，并在本文件中集中标注出处。

## Agents365-ai/drawio-skill

- **项目主页**：https://github.com/Agents365-ai/drawio-skill
- **许可证**：MIT License（upstream 在 `SKILL.md` frontmatter `license: MIT` 与 `README.md` 顶部声明，但未提供独立 LICENSE 文件，本文件按 SPDX MIT 标准模板补全）
- **Vendor 源版本**：v1.4.0（snapshot 2026-04-26）

### 借用文件清单

| drawio plugin 路径 | upstream 源路径 | 改写程度 | 说明 |
|---|---|---|---|
| `skills/draw/SKILL.md` | `SKILL.md` | 中 | frontmatter 仅保留 `name: draw` / `description:` (block scalar 重写) / `allowed-tools`；删除 `metadata.{openclaw,hermes,...}` / `license` / `homepage` / `compatibility` / `platforms`；插入跨平台 checklist + `<SUBAGENT-STOP>` 段 + 5 段式路径自定位 bootstrap；删除 `## Workflow` 第 0 步 auto `git pull` 机制；移除全部 `-e` 参数（共 8 处导出命令 + 1 处 Key flags 定义行）；`<this-skill-dir>` 占位符替换为 `$DRAW_DIR`；`command -v` 替换为 `which`（Windows cmd 兼容） |
| `skills/draw/references/style-extraction.md` | `references/style-extraction.md` | 小 | 删除 line 98 的 `-e` 参数 |
| `skills/draw/styles/built-in/{default,corporate,handdrawn}.json` | `styles/built-in/*.json` | 无 | 原样保留（3 个内置 style preset）|
| `skills/draw/styles/schema.json` | `styles/schema.json` | 无 | 原样保留 |
| `skills/draw/assets/{demo-erd,demo-uml-class,demo-sequence,demo-layered,demo-ml,workflow}.drawio` | `assets/*.drawio` | 无 | 原样保留 6 个最小代表样本（每种 preset 一个），不保 PNG（节省 git history 体积）|

### 未借用 / 不拷贝的文件

- upstream `assets/*.png`（每个 ~100KB，对 Claude 解析 .drawio XML 格式无价值）
- upstream `agents/openai.yaml`（与本仓集成无关）
- upstream `docs/index.html` / `docs/zh.html`（与本仓集成无关）
- upstream auto `git pull` 升级机制（装到 vendored copy 后会覆盖本仓改动，已删除）

### 与上游行为差异（用户可见）

1. **导出文件不再内嵌 XML metadata**：移除 `-e` 参数后，导出的 PNG/SVG/PDF/JPG 不能直接在 draw.io 双击打开重新编辑，必须保留 source `.drawio` 文件作为编辑入口。本 plugin SKILL.md `## Workflow` 已强调此约束。
2. **不再自动从 upstream 拉取更新**：本 plugin 是 vendored snapshot，不会通过 `git pull` 自动同步 upstream 改动，需要 maintainer 手动定期 review + sync。

### Agents365-ai/drawio-skill 原项目 LICENSE

```
MIT License

Copyright (c) 2026 Agents365-ai (https://github.com/Agents365-ai)

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
