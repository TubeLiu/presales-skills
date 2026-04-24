"""taw 输出验证器"""
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from docx import Document
from .docx_parser import DOCXParser


class TAWValidator:
    """taw 输出验证器"""

    # 核心章节（需要 4500+ 字）— taa v2.1.0 后编号改为 1.X 体系
    CORE_CHAPTERS = ['1.3', '1.4', '1.5', '1.10', '1.11']

    # 最低字数要求
    MIN_WORDS_CORE = 4500
    MIN_WORDS_OTHER = 2400

    # 图片数量要求
    MIN_IMAGES = 2
    MAX_IMAGES = 3

    def __init__(self, analysis_file: Path):
        self.analysis_file = analysis_file
        self.analysis_content = self._load_analysis()
        self.m2_requirements = self._extract_m2_requirements()
        self.m4_scoring = self._extract_m4_scoring()
        self.m5_disqualifications = self._extract_m5_disqualifications()
        self.m7_keywords = self._extract_m7_keywords()
        self.m7_redlines = self._extract_m7_redlines()

    def _load_analysis(self) -> str:
        """加载分析报告"""
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_m2_requirements(self) -> List[str]:
        """提取 M2 技术要求"""
        m2_match = re.search(r'## M2[^\n]*\n(.*?)(?=\n## M\d+|\Z)', self.analysis_content, re.DOTALL)
        if not m2_match:
            return []
        m2_content = m2_match.group(1)
        # 提取【必须】条款
        requirements = re.findall(r'【必须】([^\n]+)', m2_content)
        return requirements

    def _extract_m4_scoring(self) -> Dict[str, List[str]]:
        """提取 M4 评分标准中的核心关键词（支持表格格式）"""
        m4_match = re.search(r'## M4[^\n]*\n(.*?)(?=\n## M\d+|\Z)', self.analysis_content, re.DOTALL)
        if not m4_match:
            return {}
        m4_content = m4_match.group(1)

        scoring = {}
        lines = m4_content.split('\n')
        current_category = None
        for line in lines:
            stripped = line.strip()
            if line.startswith('###'):
                current_category = line.strip('#').strip()
                scoring[current_category] = []
            elif current_category:
                # 跳过表格分隔行（|---|...）
                if re.match(r'^\|[-|\s]+\|$', stripped):
                    continue
                # 从表格行中提取评分项名称（第二列，跳过 ID 列 S1/S2）
                if stripped.startswith('|') and stripped.endswith('|'):
                    cells = [c.strip() for c in stripped.split('|')[1:-1]]
                    if len(cells) < 2:
                        continue
                    # 跳过表头行
                    if re.match(r'^(ID|评分|分值|原文|推测|如何|灵雀|规则|方法|来源|优先)', cells[0]):
                        continue
                    # 第一列是 ID（S1/S2...），取第二列作为评分项名称
                    if re.match(r'^[A-Z]\d+$', cells[0]) and len(cells) > 1:
                        item_name = cells[1]
                        # 提取核心关键词（前 4 个中文字符）
                        cjk_chars = re.findall(r'[\u4e00-\u9fa5]+', item_name)
                        if cjk_chars:
                            # 用最长的中文词段作为关键词
                            keyword = max(cjk_chars, key=len)
                            if len(keyword) >= 2:
                                scoring[current_category].append(keyword)

        return scoring

    def _extract_m5_disqualifications(self) -> List[str]:
        """提取 M5 废标条款"""
        m5_match = re.search(r'## M5[^\n]*\n(.*?)(?=\n## M\d+|\Z)', self.analysis_content, re.DOTALL)
        if not m5_match:
            return []
        m5_content = m5_match.group(1)
        # 提取 [废标] 标记的条款
        disqualifications = re.findall(r'\[废标\]([^\n]+)', m5_content)
        return disqualifications

    def _extract_m7_keywords(self) -> List[str]:
        """提取 M7 关键词清单（支持数字列表和标题格式）"""
        m7_match = re.search(r'## M7[^\n]*\n(.*?)(?=\n## M\d+|\Z)', self.analysis_content, re.DOTALL)
        if not m7_match:
            return []
        m7_content = m7_match.group(1)

        # 提取关键词（在 M7.2 或含 "关键词" 的章节）
        keywords = []
        keyword_section = re.search(r'关键词[^\n]*\n(.*?)(?=\n###|\Z)', m7_content, re.DOTALL)
        if keyword_section:
            content = keyword_section.group(1)
            # 支持数字列表格式：`1. Kubernetes / K8s（出处）`
            for line in content.split('\n'):
                stripped = line.strip()
                # 跳过小节标题（**粗体**开头）
                if stripped.startswith('**') or stripped.startswith('#'):
                    continue
                # 匹配数字列表项
                num_match = re.match(r'^\d+\.\s+(.+)', stripped)
                if num_match:
                    item_text = num_match.group(1)
                    # 去掉括号内的出处
                    item_text = re.sub(r'（[^）]+）', '', item_text).strip()
                    # 取第一个 / 分隔前的词作为主关键词
                    keyword = item_text.split('/')[0].strip()
                    if keyword and len(keyword) >= 2:
                        keywords.append(keyword)
                # 也支持 - * 列表格式
                elif stripped.startswith(('-', '*', '+')) and not stripped.startswith('**'):
                    item = re.sub(r'^[-*+]\s*', '', stripped)
                    item = re.sub(r'（[^）]+）', '', item).strip()
                    if item and len(item) >= 2:
                        keywords.append(item)

        return keywords

    def _extract_m7_redlines(self) -> List[str]:
        """提取 M7.5 红线清单"""
        m7_match = re.search(r'## M7[^\n]*\n(.*?)(?=\n## M\d+|\Z)', self.analysis_content, re.DOTALL)
        if not m7_match:
            return []
        m7_content = m7_match.group(1)

        # 提取红线（假设在 M7.5 或类似章节）
        redlines = []
        redline_section = re.search(r'红线[^\n]*\n(.*?)(?=\n###|\Z)', m7_content, re.DOTALL)
        if redline_section:
            # 提取列表项
            redlines = re.findall(r'[-*]\s*([^\n]+)', redline_section.group(1))

        return redlines

    def parse_chapter(self, chapter_file: Path) -> Dict[str, Any]:
        """解析 DOCX 章节内容"""
        doc = Document(chapter_file)
        doc_data = DOCXParser.parse_document(chapter_file)

        # 提取章节号（从文件名）
        chapter_match = re.search(r'(\d+\.\d+)', chapter_file.name)
        chapter = chapter_match.group(1) if chapter_match else 'unknown'

        # 提取标题（第一个段落或 Heading 1）
        title = ''
        for para in doc.paragraphs:
            if para.text.strip():
                title = para.text.strip()
                break

        # 统计引用数量
        citation_patterns = [
            r'\[来源：[^\]]+\]',
            r'\[互联网来源[^\]]*\]',
            r'\[出处：[^\]]+\]',
            r'（来源：[^）]+）',
        ]
        citation_count = sum(len(re.findall(pattern, doc_data['text']))
                             for pattern in citation_patterns)

        return {
            'chapter': chapter,
            'title': title,
            'word_count': doc_data['word_count'],
            'image_count': len(doc_data['images']),
            'citation_count': citation_count,
            'text': doc_data['text'],
            'paragraphs': doc_data['paragraphs'],
            'images': doc_data['images'],
        }

    def validate_chapter(self, chapter: str, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """验证章节质量"""
        issues = []

        # 1. 字数检查
        is_core = chapter in self.CORE_CHAPTERS
        min_words = self.MIN_WORDS_CORE if is_core else self.MIN_WORDS_OTHER
        word_count = content['word_count']

        if word_count < min_words:
            issues.append({
                'type': 'word_count',
                'severity': 'high',
                'chapter': chapter,
                'description': f'字数不足（{word_count} 字，应 ≥{min_words} 字）',
                'location': f'章节 {chapter}',
                'suggestion': f'扩充内容至 {min_words}+ 字',
            })

        # 2. 图文比例检查
        image_count = content['image_count']
        if image_count < self.MIN_IMAGES:
            issues.append({
                'type': 'image_count',
                'severity': 'medium',
                'chapter': chapter,
                'description': f'图片数量不足（{image_count} 张，应 {self.MIN_IMAGES}-{self.MAX_IMAGES} 张）',
                'location': f'章节 {chapter}',
                'suggestion': f'添加 {self.MIN_IMAGES - image_count} 张图片',
            })

        # 3. 事实引用检查
        citation_count = content['citation_count']
        # 统计数字/指标
        numbers = re.findall(r'\d+[\d.,]*\s*(?:元|万元|%|台|套|GB|TB|ms|秒)', content['text'])
        if len(numbers) > 5 and citation_count < len(numbers) * 0.3:
            issues.append({
                'type': 'citation',
                'severity': 'high',
                'chapter': chapter,
                'description': f'事实引用不足（{citation_count} 个引用，{len(numbers)} 个数字/指标）',
                'location': f'章节 {chapter}',
                'suggestion': '为具体数字/指标添加来源标注',
            })

        # 4. 评分覆盖检查
        if self.m4_scoring:
            # 简化版：检查是否包含评分项关键词
            covered_items = []
            for category, items in self.m4_scoring.items():
                for item in items:
                    # 提取关键词（前 10 个字符）
                    keyword = item[:10]
                    if keyword in content['text']:
                        covered_items.append(item)

            total_items = sum(len(items) for items in self.m4_scoring.values())
            if total_items > 0:
                coverage = len(covered_items) / total_items
                if coverage < 0.5:
                    issues.append({
                        'type': 'scoring_coverage',
                        'severity': 'critical',
                        'chapter': chapter,
                        'description': f'评分覆盖度不足（{coverage:.1%}，应 ≥50%）',
                        'location': f'章节 {chapter}',
                        'suggestion': '补充评分项响应内容',
                    })

        # 5. 关键词覆盖检查
        if self.m7_keywords:
            covered_keywords = [kw for kw in self.m7_keywords if kw in content['text']]
            coverage = len(covered_keywords) / len(self.m7_keywords)
            if coverage < 0.8:
                issues.append({
                    'type': 'keyword_coverage',
                    'severity': 'high',
                    'chapter': chapter,
                    'description': f'关键词覆盖率不足（{coverage:.1%}，应 ≥80%）',
                    'location': f'章节 {chapter}',
                    'suggestion': f'补充关键词：{", ".join(set(self.m7_keywords) - set(covered_keywords))}',
                })

        # 6. 红线检查
        if self.m7_redlines:
            violated_redlines = [rl for rl in self.m7_redlines if rl in content['text']]
            if violated_redlines:
                issues.append({
                    'type': 'redline_violation',
                    'severity': 'critical',
                    'chapter': chapter,
                    'description': f'违反红线条款（{len(violated_redlines)} 项）',
                    'location': f'章节 {chapter}',
                    'suggestion': f'移除违规内容：{", ".join(violated_redlines)}',
                })

        # 7. 待确认标注检查
        unconfirmed = re.findall(r'\[待确认\]', content['text'])
        if len(unconfirmed) > 5:
            issues.append({
                'type': 'unconfirmed',
                'severity': 'medium',
                'chapter': chapter,
                'description': f'待确认标注过多（{len(unconfirmed)} 处）',
                'location': f'章节 {chapter}',
                'suggestion': '补充能力支撑或移除无支撑内容',
            })

        return issues

    def generate_report(self, issues: List[Dict[str, Any]], taw_outputs: Dict[str, Path], output_file: Path):
        """生成验证报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 按章节分组
        chapters = {}
        for issue in issues:
            chapter = issue.get('chapter', 'unknown')
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(issue)

        # 统计质量指标
        total_words = 0
        total_images = 0
        total_citations = 0
        chapter_count = len(taw_outputs)

        for chapter_file in taw_outputs.values():
            if chapter_file.exists():
                content = self.parse_chapter(chapter_file)
                total_words += content['word_count']
                total_images += content['image_count']
                total_citations += content['citation_count']

        avg_words = total_words / chapter_count if chapter_count > 0 else 0
        avg_images = total_images / chapter_count if chapter_count > 0 else 0
        avg_citations = total_citations / chapter_count if chapter_count > 0 else 0

        # 按严重程度分类
        critical = [i for i in issues if i['severity'] == 'critical']
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']

        report = f"""# taw 章节内容验证报告

生成时间：{timestamp}
分析文件：{self.analysis_file}
章节数量：{chapter_count} 个

## 验证摘要

- 总问题数：{len(issues)} 个
- 严重问题：{len(critical)} 个
- 高风险问题：{len(high)} 个
- 中等问题：{len(medium)} 个
- 低风险问题：{len(low)} 个

## 质量指标

- 平均字数：{avg_words:.0f} 字
- 平均图片数：{avg_images:.1f} 张
- 平均引用数：{avg_citations:.1f} 个

## 章节详情

"""
        for chapter, chapter_file in taw_outputs.items():
            if chapter_file.exists():
                content = self.parse_chapter(chapter_file)
                chapter_issues = chapters.get(content['chapter'], [])
                status = '✅' if len([i for i in chapter_issues if i['severity'] in ['critical', 'high']]) == 0 else '❌'

                report += f"### {content['chapter']} {content['title']} {status}\n\n"
                report += f"- 字数：{content['word_count']} 字\n"
                report += f"- 图片：{content['image_count']} 张\n"
                report += f"- 引用：{content['citation_count']} 个\n"
                report += f"- 问题：{len(chapter_issues)} 个\n\n"

        if critical:
            report += "\n## 严重问题\n\n"
            for i, issue in enumerate(critical, 1):
                report += f"### {i}. [{issue['chapter']}] {issue['description']}\n\n"
                report += f"- 位置：{issue['location']}\n"
                report += f"- 建议：{issue['suggestion']}\n\n"

        if high:
            report += "\n## 高风险问题\n\n"
            for i, issue in enumerate(high, 1):
                report += f"### {i}. [{issue['chapter']}] {issue['description']}\n\n"
                report += f"- 位置：{issue['location']}\n"
                report += f"- 建议：{issue['suggestion']}\n\n"

        if medium:
            report += "\n## 中等问题\n\n"
            for i, issue in enumerate(medium, 1):
                report += f"{i}. [{issue['chapter']}] {issue['description']}\n"

        if low:
            report += "\n## 低风险问题\n\n"
            for i, issue in enumerate(low, 1):
                report += f"{i}. [{issue['chapter']}] {issue['description']}\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

    def validate_vendor_consistency(self, chapter_file: Path, expected_vendor: str) -> List[Dict[str, Any]]:
        """验证厂商名一致性（--vendor 参数测试）"""
        issues = []

        content = self.parse_chapter(chapter_file)
        text = content['text']

        # 提取文本中的厂商名
        vendor_pattern = r'(灵雀云|博云|华为|阿里云|腾讯云|红帽|VMware)'
        vendors_found = re.findall(vendor_pattern, text)

        if vendors_found:
            # 统计出现次数
            vendor_counts = {}
            for vendor in vendors_found:
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

            # 检查是否与预期一致
            main_vendor = max(vendor_counts, key=vendor_counts.get)
            if main_vendor != expected_vendor:
                issues.append({
                    'type': 'vendor_consistency',
                    'severity': 'high',
                    'chapter': content['chapter'],
                    'description': f'厂商名不一致：预期 {expected_vendor}，实际主要使用 {main_vendor}（{vendor_counts[main_vendor]} 次）',
                    'location': f'章节 {content["chapter"]}',
                    'suggestion': f'将所有 {main_vendor} 替换为 {expected_vendor}',
                })

            # 检查是否混用多个厂商名
            if len(vendor_counts) > 1:
                issues.append({
                    'type': 'vendor_consistency',
                    'severity': 'medium',
                    'chapter': content['chapter'],
                    'description': f'混用多个厂商名：{vendor_counts}',
                    'location': f'章节 {content["chapter"]}',
                    'suggestion': f'统一使用 {expected_vendor}',
                })

        return issues

    def validate_with_image_quality(self, chapter_file: Path) -> List[Dict[str, Any]]:
        """集成图片质量检查"""
        from .image_quality_validator import ImageQualityValidator

        validator = ImageQualityValidator(chapter_file)
        return validator.validate_all()

    def validate_with_professionalism(self, chapter_file: Path) -> List[Dict[str, Any]]:
        """集成内容专业性检查"""
        from .content_professionalism_validator import ContentProfessionalismValidator

        validator = ContentProfessionalismValidator(chapter_file)
        return validator.validate_all()
