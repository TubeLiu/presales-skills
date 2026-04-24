#!/usr/bin/env python3
"""
taw DOCX 生成工具库

提供中文排版的 DOCX 生成函数，替代在 SKILL.md 中内嵌代码模板。
所有正文写入统一使用 write_markdown()，禁止直接使用 doc.add_heading() / doc.add_paragraph()。

用法（在 Bash 中执行 Python 脚本时 import）：
    import sys; sys.path.insert(0, '.claude/skills/taw/tools')
    from docx_writer import create_document, write_markdown, add_heading_cn, add_picture_cn
"""

import os
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── 样式级字体设置 ──────────────────────────────────

def _apply_font(style, size_pt, bold=False, cn_font='宋体', latin_font='Times New Roman'):
    """设置样式的字体、字号、加粗"""
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.font.name = latin_font
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), latin_font)
    rFonts.set(qn('w:hAnsi'), latin_font)
    rFonts.set(qn('w:eastAsia'), cn_font)
    rFonts.set(qn('w:cs'), cn_font)
    # 删除主题字体引用（优先级高于明确字体名，必须清除）
    for attr in [qn('w:asciiTheme'), qn('w:hAnsiTheme'),
                 qn('w:eastAsiaTheme'), qn('w:cstheme')]:
        rFonts.attrib.pop(attr, None)


def setup_styles(doc):
    """设置文档样式：标题和正文字体规范

    【字体名称固定，禁止修改】
    '宋体' 是 OOXML w:eastAsia 标准映射名，Word 跨平台自动解析：
      Windows → SimSun  |  macOS → Songti SC
    禁止替换为 SimSun（仅 Windows）或 Songti SC（仅 macOS）
    '黑体' 同理：Windows → SimHei，macOS → Heiti SC
    """
    _apply_font(doc.styles['Title'],     22, bold=True,  cn_font='黑体')   # 封面：二号黑体加粗
    _apply_font(doc.styles['Heading 1'], 16, bold=True,  cn_font='宋体')   # 一级：三号宋体加粗
    _apply_font(doc.styles['Heading 2'], 15, bold=True,  cn_font='宋体')   # 二级：小三号宋体加粗
    _apply_font(doc.styles['Heading 3'], 14, bold=True,  cn_font='宋体')   # 三级：四号宋体加粗
    _apply_font(doc.styles['Heading 4'], 13, bold=True,  cn_font='宋体')   # 四级：小四号宋体加粗
    _apply_font(doc.styles['Heading 5'], 12, bold=False, cn_font='宋体')   # 五级：小四号宋体
    _apply_font(doc.styles['Normal'],    12, bold=False, cn_font='宋体')   # 正文：小四宋体


def clean_doc_defaults(doc):
    """清除 python-docx 默认模板的主题字体引用

    python-docx 默认模板的 w:docDefaults 含主题字体引用，优先级最高，必须清除。
    """
    styles_elem = doc.styles.element
    doc_defaults = styles_elem.find(qn('w:docDefaults'))
    if doc_defaults is None:
        return
    rPr_default = doc_defaults.find(qn('w:rPrDefault'))
    if rPr_default is None:
        return
    rPr = rPr_default.find(qn('w:rPr'))
    if rPr is None:
        return
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        return
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), '宋体')
    rFonts.set(qn('w:cs'), '宋体')
    for attr in [qn('w:asciiTheme'), qn('w:hAnsiTheme'),
                 qn('w:eastAsiaTheme'), qn('w:cstheme')]:
        rFonts.attrib.pop(attr, None)


# ── 运行级字体设置 ──────────────────────────────────

def apply_run_font(run, cn_font='宋体', latin_font='Times New Roman'):
    """设置单个 run 的字体（每个 run 也可能继承主题字体，必须逐 run 清除）"""
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), latin_font)
    rFonts.set(qn('w:hAnsi'), latin_font)
    rFonts.set(qn('w:eastAsia'), cn_font)
    rFonts.set(qn('w:cs'), cn_font)
    for attr in [qn('w:asciiTheme'), qn('w:hAnsiTheme'),
                 qn('w:eastAsiaTheme'), qn('w:cstheme')]:
        rFonts.attrib.pop(attr, None)


# ── 包装函数（替代 doc.add_heading / doc.add_paragraph）───

def add_heading_cn(doc, text, level, cn_font='宋体'):
    """添加中文标题，自动设置字体"""
    h = doc.add_heading(text, level)
    for run in h.runs:
        apply_run_font(run, cn_font=cn_font)
    return h


def add_para_cn(doc, text, cn_font='宋体'):
    """添加中文段落（向后兼容，推荐使用 write_markdown 替代）"""
    p = doc.add_paragraph(text)
    for run in p.runs:
        apply_run_font(run, cn_font=cn_font)
    return p


# ── Markdown 渲染函数 ──────────────────────────────────

def _apply_inline(p, text, cn_font='宋体'):
    """解析行内 **bold** *italic* `code`，向段落 p 追加 runs"""
    token_re = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')
    parts = token_re.split(text)
    for part in parts:
        if not part:
            continue
        run = p.add_run(part)
        if part.startswith('**') and part.endswith('**'):
            run.bold = True
            run.text = part[2:-2]
        elif part.startswith('*') and part.endswith('*'):
            run.italic = True
            run.text = part[1:-1]
        elif part.startswith('`') and part.endswith('`'):
            run.font.name = 'Courier New'
            run.text = part[1:-1]
        apply_run_font(run, cn_font=cn_font)


def write_markdown(doc, md_text, cn_font='宋体'):
    """将 Markdown 字符串渲染为 python-docx 内容。

    支持：标题(#)、无序列表(-/*)、有序列表(1.)、引用(>)、
    表格(|col|col|)、行内粗体(**)、斜体(*)、代码(``)、普通段落。
    替代 add_para_cn()，作为所有正文写入的统一入口。
    """
    lines = md_text.split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        # 表格块检测
        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            def is_sep(row):
                return bool(re.match(r'^[\|\s\-:]+$', row))
            rows = [r for r in table_lines if not is_sep(r)]
            if rows:
                parsed = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
                max_cols = max(len(r) for r in parsed)
                tbl = doc.add_table(rows=len(parsed), cols=max_cols)
                tbl.style = 'Table Grid'
                for r_i, row in enumerate(parsed):
                    for c_i in range(max_cols):
                        txt = row[c_i] if c_i < len(row) else ''
                        cell = tbl.cell(r_i, c_i)
                        cell.text = ''
                        p = cell.paragraphs[0]
                        if r_i == 0:
                            run = p.add_run(txt)
                            run.bold = True
                            apply_run_font(run, cn_font=cn_font)
                        else:
                            _apply_inline(p, txt, cn_font=cn_font)
            continue
        # 标题
        m = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m:
            level = len(m.group(1))
            add_heading_cn(doc, m.group(2), level, cn_font=cn_font)
            i += 1
            continue
        # 无序列表
        m = re.match(r'^[-*]\s+(.+)$', stripped)
        if m:
            p = doc.add_paragraph(style='Normal')
            bullet = p.add_run('• ')
            apply_run_font(bullet, cn_font=cn_font)
            _apply_inline(p, m.group(1), cn_font=cn_font)
            i += 1
            continue
        # 有序列表
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            p = doc.add_paragraph(style='Normal')
            num = p.add_run(m.group(1) + '. ')
            apply_run_font(num, cn_font=cn_font)
            _apply_inline(p, m.group(2), cn_font=cn_font)
            i += 1
            continue
        # 引用
        m = re.match(r'^>\s*(.+)$', stripped)
        if m:
            p = doc.add_paragraph(style='Normal')
            p.paragraph_format.left_indent = Cm(0.75)
            _apply_inline(p, m.group(1), cn_font=cn_font)
            i += 1
            continue
        # 普通段落
        p = doc.add_paragraph(style='Normal')
        _apply_inline(p, stripped, cn_font=cn_font)
        i += 1


# ── 图片插入函数 ────────────────────────────────────

def add_picture_cn(doc, img_path, caption=None, width_cm=14.0, cn_font='宋体'):
    """插入图片并附带说明文字。

    img_path 须为绝对路径或相对于工作目录的路径。
    文件不存在时自动降级为占位符文本，不抛出异常。
    """
    if not os.path.exists(img_path):
        p = doc.add_paragraph(style='Normal')
        p.paragraph_format.left_indent = Cm(0.75)
        run = p.add_run('[图片占位符 — ' + (caption or img_path) + '：请手动插入图片]')
        run.italic = True
        apply_run_font(run, cn_font=cn_font)
        return
    doc.add_picture(img_path, width=Cm(width_cm))
    last_para = doc.paragraphs[-1]
    last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        cap_p = doc.add_paragraph(style='Normal')
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_run = cap_p.add_run(caption)
        cap_run.italic = True
        cap_run.font.size = Pt(10.5)  # 五号字
        apply_run_font(cap_run, cn_font=cn_font)


# ── 文档创建快捷函数 ──────────────────────────────────

def create_document():
    """创建预配置的 DOCX 文档（A4、标准字体、页边距）

    返回已设置好样式和页面的 Document 对象，可直接写入内容。
    """
    doc = Document()
    setup_styles(doc)
    clean_doc_defaults(doc)

    # 页面设置：A4，上下 2.5cm，左右 2.4cm
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    return doc
