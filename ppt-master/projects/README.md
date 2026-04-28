# 用户项目工作区

**中文** | [English](./README_EN.md)

此目录用于存放进行中的项目。

## 新建项目

```bash
python3 skills/make/scripts/project_manager.py init my_project --format ppt169
```

## 目录结构

典型项目通常包含以下内容：

```
project_name_format_YYYYMMDD/
├── README.md
├── design_spec.md
├── sources/
│   ├── 原始文件 / URL 归档 / 转换后的 Markdown
│   └── *_files/                  # Markdown 配套资源目录（如图片）
├── images/                       # 项目使用的图片资源
├── notes/
│   ├── 01_xxx.md
│   ├── 02_xxx.md
│   └── total.md
├── svg_output/
│   ├── 01_xxx.svg
│   └── ...
├── svg_final/
│   ├── 01_xxx.svg
│   └── ...
├── templates/                    # 项目级模板（如有）
├── *.pptx
└── image_analysis.csv            # 可选，图片扫描分析结果
```

项目可处于不同阶段，未必同时具备所有产物。例如：

- 仅完成 `sources/` 归档与设计规范 & 内容大纲（design_spec）
- `svg_output/` 已生成，但后处理尚未执行
- `svg_final/`、`notes/`、`*.pptx` 全部完成

## 备注

- 此目录下内容被 `.gitignore` 排除
- 完成的项目可移到 `examples/` 目录分享
- 工作区外的文件默认复制进来；工作区内的文件直接移到项目的 `sources/` 下
