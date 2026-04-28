# PPT Master 工具集

**中文** | [English](./README_EN.md)

本目录包含面向用户的脚本：转换、项目搭建、SVG 处理、导出、图片生成。

## 目录结构

- 顶层 `scripts/`：可执行入口脚本
- `scripts/source_to_md/`：源文档 → Markdown 转换器（`pdf_to_md.py`、`doc_to_md.py`、`ppt_to_md.py`、`web_to_md.py`、`web_to_md.cjs`）
- `scripts/template_import/`：`pptx_template_import.py` 使用的内部 PPTX 参考准备 helper
- `scripts/svg_finalize/`：`finalize_svg.py` 使用的内部后处理 helper
- `scripts/docs/`：按主题组织的脚本文档
- `scripts/assets/`：脚本依赖的静态资产

## 快速开始

典型端到端工作流：

```bash
python3 scripts/source_to_md/pdf_to_md.py <file.pdf>
# 或
python3 scripts/source_to_md/ppt_to_md.py <deck.pptx>
python3 scripts/project_manager.py init <project_name> --format ppt169
python3 scripts/project_manager.py import-sources <project_path> <source_files...>
python3 scripts/total_md_split.py <project_path>
python3 scripts/finalize_svg.py <project_path>
python3 scripts/svg_to_pptx.py <project_path> -s final
```

仓库更新：

```bash
python3 scripts/update_repo.py
```

## 脚本索引

| 类别 | 主要脚本 | 文档 |
|------|----------|------|
| 转换 | `source_to_md/pdf_to_md.py`、`source_to_md/doc_to_md.py`、`source_to_md/ppt_to_md.py`、`source_to_md/web_to_md.py`、`source_to_md/web_to_md.cjs` | [docs/conversion.md](./docs/conversion.md) |
| 项目管理 | `project_manager.py`、`batch_validate.py`、`generate_examples_index.py`、`error_helper.py`、`pptx_template_import.py` | [docs/project.md](./docs/project.md) |
| SVG 流水线 | `finalize_svg.py`、`svg_to_pptx.py`、`total_md_split.py`、`svg_quality_checker.py` | [docs/svg-pipeline.md](./docs/svg-pipeline.md) |
| 规范维护 | `update_spec.py` | [docs/update_spec.md](./docs/update_spec.md) |
| 图片工具 | `analyze_images.py`、`gemini_watermark_remover.py`、`rotate_images.py`（AI 生图委托给独立的 ai-image plugin，通过 `Skill(skill="ai-image:gen")` 或 `image_gen.py`）| [docs/image.md](./docs/image.md) |
| 仓库维护 | `update_repo.py` | README 安装 / 更新段 |
| 故障排查 | 校验、预览、导出、依赖问题 | [docs/troubleshooting.md](./docs/troubleshooting.md) |

## 高频命令

转换：

```bash
python3 scripts/source_to_md/pdf_to_md.py <file.pdf>
python3 scripts/source_to_md/ppt_to_md.py <deck.pptx>
python3 scripts/source_to_md/doc_to_md.py <file.docx>
python3 scripts/source_to_md/web_to_md.py <url>
```

项目搭建：

```bash
python3 scripts/project_manager.py init <project_name> --format ppt169
python3 scripts/project_manager.py import-sources <project_path> <source_files...>
python3 scripts/project_manager.py validate <project_path>
```

模板源导入：

```bash
python3 scripts/pptx_template_import.py <template.pptx>
python3 scripts/pptx_template_import.py <template.pptx> --manifest-only
```

后处理与导出：

```bash
python3 scripts/total_md_split.py <project_path>
python3 scripts/finalize_svg.py <project_path>
python3 scripts/svg_to_pptx.py <project_path> -s final
```

图片生成（委托给 ai-image plugin —— v1.0.0 c983037 删了 `image-gen` PATH bin 入口，改为下列两种调用方式之一）：

**Claude Code**（推荐）：
```
Skill(skill="ai-image:gen")
```

**跨 agent / 直接脚本**：先按 ai-image SKILL.md §路径自定位 解析 `$AI_IMAGE_SKILL_DIR`：
```bash
python3 "$AI_IMAGE_SKILL_DIR/scripts/image_gen.py" "A modern futuristic workspace"
python3 "$AI_IMAGE_SKILL_DIR/scripts/image_gen.py" --list-backends
python3 scripts/analyze_images.py <project_path>/images
```

仓库更新：

```bash
python3 scripts/update_repo.py
python3 scripts/update_repo.py --skip-pip
```

依赖验证（**AI 不要手写 `python3 -c "import X; import Y"`** 来猜包名 —— 真实依赖以 `requirements.txt` 为准）：

```bash
# 唯一 canonical 入口：直接跑 _ensure_deps.py，按 requirements.txt 检查并按需 pip install
python3 scripts/_ensure_deps.py
```

> 历史教训：`cssutils` / `cairosvg` 都**不是 requirements.txt 列出的依赖**（前者根本未用，
> 后者是 `svglib` 的更优替代品但仅在 SVG 含复杂渐变/滤镜时才需要）。手写 import 验证会
> 因 AI 训练数据陈旧而虚报"依赖缺失"。

## 建议

- 每个 workflow 在 `scripts/` 顶层只保留一个面向用户的入口
- provider 特定或 helper 内部实现移到子目录
- 优先使用统一入口 `project_manager.py`、`finalize_svg.py`，AI 生图优先用 ai-image plugin 的 `Skill(skill="ai-image:gen")` / `image_gen.py`
- 导出时优先 `svg_final/` 而非 `svg_output/`

## 相关文档

- [转换工具](./docs/conversion.md)
- [项目工具](./docs/project.md)
- [SVG 流水线工具](./docs/svg-pipeline.md)
- [图片工具](./docs/image.md)
- [故障排查](./docs/troubleshooting.md)
- [AGENTS 指南](../../../AGENTS.md)

_最后更新：2026-04-09_
