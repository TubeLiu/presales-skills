---
description: PPT 生成主入口（等价自然语言"做 PPT"/"生成演示稿"或 /ppt-make skill）。接受源文档（PDF/DOCX/URL/MD）路径或主题，启动 PPT 生成流程。
---

用户运行了 `/ppt-master:make $ARGUMENTS` —— 请按 ppt-master plugin 的 `ppt-make` skill 完整工作流为用户生成 PPT。

**用户输入**：`$ARGUMENTS`

## 工作流概要（详细见 `skills/ppt-master/SKILL.md`）

`Source Document → Create Project → Template Option → Strategist Eight Confirmations → [Image_Generator] → Executor → Post-processing → Export PPTX`

1. **解析输入**：`$ARGUMENTS` 是文件路径 / URL / 主题描述？
2. **创建项目**：`python3 skills/ppt-master/scripts/project_manager.py init <name> --format ppt169`
3. **导入源文档**（如有）：`project_manager.py import-sources ...`
4. **执行 ppt-make skill 全流程**：Strategist 八项确认 → Image_Generator → Executor → Post-processing
5. **导出 PPTX**：`svg_to_pptx.py <project_path> -s final`

## 关键约束

- 后处理三步（`total_md_split.py` / `finalize_svg.py` / `svg_to_pptx.py`）**必须串行单独执行**，不能合并代码块。
- SVG 禁用项见 SKILL.md / shared-standards.md（mask、style、class、foreignObject 等）。
- 配图调用 ai-image plugin 的 `image-gen` bin（不是直接走 plugin 内部脚本）。
