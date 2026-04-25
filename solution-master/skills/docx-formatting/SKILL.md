---
name: docx-formatting
description: 当需要将方案内容输出为标准格式 DOCX 文件时使用——支持 Markdown 转 DOCX，遵循统一字体规范
allowed-tools: Read, Write, Edit, Bash, Glob
---

# DOCX 格式输出

将方案内容从 Markdown 格式渲染为符合规范的 DOCX 文件。

**工具：** `${CLAUDE_SKILL_DIR}/scripts/docx_writer.py`

## 字体规范

| 层级 | 字号 | 字重 | 中文字体 | 拉丁字体 |
|------|------|------|---------|---------|
| 封面标题 | 22pt | Bold | 黑体 | Times New Roman |
| H1 一级标题 | 16pt | Bold | 宋体 | Times New Roman |
| H2 二级标题 | 15pt | Bold | 宋体 | Times New Roman |
| H3 三级标题 | 14pt | Bold | 宋体 | Times New Roman |
| H4 四级标题 | 13pt | Bold | 宋体 | Times New Roman |
| H5 五级标题 | 12pt | Regular | 宋体 | Times New Roman |
| 正文 | 12pt（小四号） | Regular | 宋体 | Times New Roman |

**字体名称使用 OOXML 标准映射名（跨平台兼容）：**
- '宋体'：Windows -> SimSun, macOS -> Songti SC
- '黑体'：Windows -> SimHei, macOS -> Heiti SC
- **禁止**替换为平台特定名称

## 标题自动编号

DOCX 输出时，Heading 1-5 自动关联多级列表编号，无需在 Markdown 源文本中手动编号：

| Markdown 标题 | DOCX 显示效果 |
|-------------|-------------|
| `# 章节标题` | **1** 章节标题 |
| `## 子章节标题` | **1.1** 子章节标题 |
| `### 三级标题` | **1.1.1** 三级标题 |
| `#### 四级标题` | **1.1.1.1** 四级标题 |
| `##### 五级标题` | **1.1.1.1.1** 五级标题 |

编号由 `${CLAUDE_SKILL_DIR}/scripts/docx_writer.py` 的 `setup_heading_numbering()` 函数自动生成。

## 页面设置

- 纸张：A4（21.0cm x 29.7cm）
- 上下边距：2.5cm
- 左右边距：2.4cm
- 行距：1.5 倍

## 使用方式

### 方式一：命令行

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/docx_writer.py" input.md --output output.docx --title "方案名称" --author "作者"
```

### 方式二：Python API

```python
from docx_writer import create_document, write_markdown, save_document

doc = create_document(title='方案名称', subtitle='副标题', author='作者')
write_markdown(doc, markdown_text)
save_document(doc, 'output/方案名称.docx')
```

## 支持的 Markdown 元素

| 元素 | Markdown 语法 | DOCX 渲染 |
|------|-------------|-----------|
| 标题 | `# ## ### #### #####` | Heading 1-5 样式 |
| 粗体 | `**文字**` | Bold |
| 斜体 | `*文字*` | Italic |
| 代码 | `` `代码` `` | Consolas 字体 |
| 无序列表 | `- 项目` | List Bullet 样式 |
| 有序列表 | `1. 项目` | List Number 样式 |
| 表格 | `\|列\|列\|` | Table Grid 样式 |
| 图片 | `![描述](路径)` | 居中图片 + 描述 |
| 引用 | `> 文字` | 左缩进 0.75cm + 斜体 |

## 图片处理

- 图片存在：居中插入，默认宽度 14cm
- 图片不存在：降级为占位符文本（斜体居中）
- 占位符格式：`[图片占位符 — {描述}：请手动插入图片]`

### draw.io 导出图片

`.drawio.png` 文件是标准 PNG 格式，**必须**像普通 PNG 一样自动嵌入 DOCX，**禁止**跳过或要求用户手动插入。

## 输出产物

### 单章节
```
drafts/{章节编号}_{章节名称}.docx
```

### 完整方案
```
output/{方案名称}.docx
```

## 禁止事项

- 使用 emoji 或特殊 Unicode 符号
- 修改字体规范中的字号和字体名称
- 使用平台特定字体名称（SimSun、Songti SC 等）
- 跳过 `clean_doc_defaults()` 步骤
