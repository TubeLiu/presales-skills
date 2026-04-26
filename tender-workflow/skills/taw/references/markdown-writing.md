# Markdown → DOCX 写入约束

主 SKILL.md §Phase 2/3 列了 `write_markdown()` 是唯一入口；本文件给详细规则 + 反例。

## 1. 唯一入口规则

✅ **必须**通过 `write_markdown()` 写入所有正文；
❌ **禁止**直接 `doc.add_paragraph()` / `add_para_cn()` 写带 Markdown 标记的内容。

理由：`add_paragraph()` 会把 `**粗体**` 字面写出，DOCX 显示原始 `**`；`write_markdown()` 解析后渲染为正确的粗体 run。

## 2. 错误 / 正确示例

```python
# ❌ 错误：Markdown 标记会被字面写入 DOCX
doc.add_paragraph('本项目采用 **微服务架构**，具备 `容器编排` 能力。')
add_para_cn(doc, '本项目采用 **微服务架构**，具备 `容器编排` 能力。')
# DOCX 显示：本项目采用 **微服务架构**，具备 `容器编排` 能力。

# ✅ 正确
write_markdown(doc, '本项目采用 **微服务架构**，具备 `容器编排` 能力。')
# DOCX 显示：本项目采用 微服务架构（粗体），具备 容器编排（代码） 能力。
```

## 3. 强制检查清单（生成代码前必查）

1. 正文写入唯一入口：所有正文必须经 `write_markdown()` 函数
2. 格式标记检查：内容含 `**` / `__` / `*` / `_` / `` ` `` / `- ` / `1. ` / `|` / `>` 任何一个 → 必须走 `write_markdown()`
3. 表格强制：技术参数对比 / 功能列表 / 里程碑计划等用 Markdown 表格通过 `write_markdown()`，**禁止**文本或制表符模拟
4. 代码自检：检查所有 `doc.add_paragraph()` 和 `add_para_cn()` 调用，仅允许：
   - 纯文本标题（无 Markdown 标记）
   - 空行
   - 已明确不需要格式化的内容
5. 输出验证：生成 DOCX 后想象检查——若看到 `**` / `__` / `` ` `` 字面残留，说明解析失败，必须修正

## 4. write_markdown() 支持的语法

| Markdown | 渲染 |
|---|---|
| `# / ## / ### / #### / #####` | Heading 1-5（多级列表自动加编号） |
| `![cap](path)` | 嵌入图片 + caption（小五宋体居中）；文件不存在自动占位符 |
| `**粗体**` | 粗体 run |
| `*斜体*` | 斜体 run |
| `` `代码` `` | 代码字体 run |
| `- ` / `* ` | 无序列表 |
| `1. ` `2. ` | 有序列表 |
| `> ` | 引用段（左缩进） |
| `\| col \| col \|` | Markdown 表格 → docx Table Grid |

注意：
- `#` 只渲染为 H1，不渲染为 Title（`level=0` 被 clamp 到 1）
- 标题文本若残留编号（如 `### 1.2.1 标题`）会被 `strip_numbering_prefix` 自动剥除
- 多级列表自动加编号 → 标题文本**不要**写编号

## 5. 调用骨架

```bash
SKILL_DIR="$SKILL_DIR" python3 <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ['SKILL_DIR'], 'tools'))
from docx_writer import create_document, write_markdown, add_heading_cn, add_picture_cn, add_toc_field, validate_heading_hierarchy

doc = create_document()                       # 自动 setup_styles + multilevel_list + 页面
add_toc_field(doc, levels=4)                  # 文档开头 TOC
write_markdown(doc, md_text)                  # 一把渲染整个章节 Markdown（含 ![]() 图）
ok, errs = validate_heading_hierarchy(doc, OUTLINE_SUBSECTIONS_LIST)  # 终检
doc.save('./drafts/<output>.docx')
PY
```
