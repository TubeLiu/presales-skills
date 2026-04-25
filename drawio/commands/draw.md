---
description: Draw.io 图表生成主入口（等价自然语言"画图"/"生成流程图"或 /draw-diagram skill）。接受图表类型 + 描述，生成 .drawio 文件并可选导出 PNG/SVG/PDF。
---

用户运行了 `/drawio:draw $ARGUMENTS` —— 请按 drawio plugin 的 `draw-diagram` skill 流程生成图表。

**用户输入**：`$ARGUMENTS`

## 工作流（详见 `skills/drawio/SKILL.md`）

1. **澄清需求**：图表类型（flowchart / architecture / ER / sequence / class / network / mockup / wireframe）？关键节点和关系？
2. **生成 `.drawio` XML**：手写 mxGraph XML 或调 plugin 内的脚手架脚本。保留 `.drawio` 源文件——这是后续编辑唯一入口。
3. **生成方式**：直接调 `drawio-gen` bin（plugin bin/ 自动上 PATH）：
   ```bash
   drawio-gen --type architecture --topic "<主题>" --details '<JSON 详情>' --output <dir>
   ```
   类型支持：`architecture | flowchart | org_chart | sequence | other`。
4. **导出 PNG/SVG/PDF**（如需）：参考 SKILL.md 的导出小节（drawio CLI 或在线渲染）。
5. **返回**：源 `.drawio` 路径 + 导出文件路径（如有）。

## 注意

- 永远保留 `.drawio` 源文件（导出文件无法反向编辑）。
- 跨 plugin 调用走 `drawio-gen` bin，不走 plugin 内部 Python。
