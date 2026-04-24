"""一致性验证器 - 验证大纲、分析报告、章节之间的一致性"""
import re
from pathlib import Path
from typing import Dict, List, Any
from .docx_parser import DOCXParser


class ConsistencyValidator:
    """一致性验证器"""

    def __init__(self, analysis_file: Path, outline_file: Path, chapter_files: List[Path] = None):
        self.analysis_file = analysis_file
        self.outline_file = outline_file
        self.chapter_files = chapter_files or []

        self.analysis_content = self._load_analysis()
        self.outline_content = self._load_outline()
        self.modules = self._parse_modules()
        self.chapters = self._load_chapters()

    def _load_analysis(self) -> str:
        """加载分析报告"""
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_outline(self) -> Dict[str, Any]:
        """加载大纲"""
        doc_data = DOCXParser.parse_document(self.outline_file)
        return {
            'text': doc_data['text'],
            'tables': doc_data['tables']
        }

    def _parse_modules(self) -> Dict[str, str]:
        """解析 M1-M7 模块"""
        modules = {}
        pattern = r'## (M\d+)[^\n]*\n(.*?)(?=\n## M\d+|\Z)'
        matches = re.findall(pattern, self.analysis_content, re.DOTALL)
        for module_name, content in matches:
            modules[module_name] = content.strip()
        return modules

    def _load_chapters(self) -> Dict[str, str]:
        """加载章节内容"""
        chapters = {}
        for chapter_file in self.chapter_files:
            doc_data = DOCXParser.parse_document(chapter_file)
            chapter_num = self._extract_chapter_number(chapter_file.name)
            if chapter_num:
                chapters[chapter_num] = doc_data['text']
        return chapters

    def _extract_chapter_number(self, filename: str) -> str:
        """从文件名提取章节号"""
        match = re.search(r'(\d+\.\d+)', filename)
        return match.group(1) if match else None

    def validate_all(self) -> List[Dict[str, Any]]:
        """执行所有一致性验证"""
        issues = []
        issues.extend(self.validate_outline_analysis_consistency())
        issues.extend(self.validate_cross_chapter_consistency())
        for chapter_num in self.chapters.keys():
            issues.extend(self.validate_chapter_outline_consistency(chapter_num))
        return issues

    def validate_outline_analysis_consistency(self) -> List[Dict[str, Any]]:
        """验证大纲与分析报告一致性"""
        issues = []

        # 检查 M2 必须条款 → Part C 需求映射表
        if 'M2' in self.modules:
            m2_content = self.modules['M2']
            must_requirements = re.findall(r'【必须】(.*?)(?=\n|$)', m2_content)

            # 检查 Part C 是否存在
            part_c_found = 'Part C' in self.outline_content['text'] or '需求映射表' in self.outline_content['text']

            if must_requirements and not part_c_found:
                issues.append({
                    'type': 'outline_analysis_consistency',
                    'severity': 'high',
                    'message': f'M2 中有 {len(must_requirements)} 个必须条款，但大纲中未找到 Part C 需求映射表',
                    'location': '大纲 Part C',
                    'suggestion': '在大纲中添加 Part C 需求映射表，映射 M2 中的必须条款'
                })

        # 检查 M4 评分项 → Part B 章节设计
        if 'M4' in self.modules:
            m4_content = self.modules['M4']
            scoring_items = re.findall(r'(\d+)\s*分[：:](.*?)(?=\n|$)', m4_content)

            # 检查 Part B 是否存在
            part_b_found = 'Part B' in self.outline_content['text'] or '章节设计' in self.outline_content['text']

            if scoring_items and not part_b_found:
                issues.append({
                    'type': 'outline_analysis_consistency',
                    'severity': 'high',
                    'message': f'M4 中有 {len(scoring_items)} 个评分项，但大纲中未找到 Part B 章节设计',
                    'location': '大纲 Part B',
                    'suggestion': '在大纲中添加 Part B 章节设计，对应 M4 中的评分项'
                })

        # 检查 M7 关键词 → 章节标题/内容
        if 'M7' in self.modules:
            m7_content = self.modules['M7']
            keywords = re.findall(r'[「『]([^」』]+)[」』]', m7_content)

            outline_text = self.outline_content['text']
            missing_keywords = []
            for keyword in keywords[:5]:  # 检查前5个关键词
                if keyword not in outline_text:
                    missing_keywords.append(keyword)

            if missing_keywords:
                issues.append({
                    'type': 'outline_analysis_consistency',
                    'severity': 'medium',
                    'message': f'M7 中的关键词 {missing_keywords} 未在大纲中体现',
                    'location': '大纲章节标题',
                    'suggestion': f'在大纲章节标题或内容中体现这些关键词：{", ".join(missing_keywords)}'
                })

        return issues

    def validate_chapter_outline_consistency(self, chapter_num: str) -> List[Dict[str, Any]]:
        """验证章节与大纲一致性"""
        issues = []

        if chapter_num not in self.chapters:
            return issues

        chapter_content = self.chapters[chapter_num]
        outline_text = self.outline_content['text']

        # 检查章节号是否在大纲中
        if chapter_num not in outline_text:
            issues.append({
                'type': 'chapter_outline_consistency',
                'severity': 'high',
                'message': f'章节 {chapter_num} 在大纲中未找到',
                'location': f'章节 {chapter_num}',
                'suggestion': f'确认章节 {chapter_num} 是否应该存在，或检查大纲是否缺失该章节'
            })

        # 提取大纲中该章节的标题
        pattern = rf'{re.escape(chapter_num)}\s+([^\n]+)'
        match = re.search(pattern, outline_text)
        if match:
            outline_title = match.group(1).strip()

            # 检查章节内容中是否包含标题关键词
            title_keywords = re.findall(r'[\u4e00-\u9fa5]+', outline_title)
            missing_keywords = []
            for keyword in title_keywords:
                if len(keyword) >= 2 and keyword not in chapter_content[:500]:  # 检查前500字
                    missing_keywords.append(keyword)

            if missing_keywords:
                issues.append({
                    'type': 'chapter_outline_consistency',
                    'severity': 'medium',
                    'message': f'章节 {chapter_num} 内容与大纲标题 "{outline_title}" 不匹配，缺少关键词：{", ".join(missing_keywords)}',
                    'location': f'章节 {chapter_num}',
                    'suggestion': f'在章节开头部分体现标题关键词：{", ".join(missing_keywords)}'
                })

        return issues

    def validate_cross_chapter_consistency(self) -> List[Dict[str, Any]]:
        """验证章节间一致性"""
        issues = []

        if len(self.chapters) < 2:
            return issues

        # 1. 术语一致性检查
        vendor_names = {}
        product_names = {}

        for chapter_num, content in self.chapters.items():
            # 提取厂商名（常见模式）
            vendors = re.findall(r'(灵雀云|博云|华为|阿里云|腾讯云|红帽|VMware)', content)
            if vendors:
                vendor_names[chapter_num] = vendors[0]

            # 提取产品名（常见模式）
            products = re.findall(r'(ACP|KubeSphere|Rancher|OpenShift|ACK|TKE)', content)
            if products:
                product_names[chapter_num] = products[0]

        # 检查厂商名一致性
        if len(set(vendor_names.values())) > 1:
            issues.append({
                'type': 'cross_chapter_consistency',
                'severity': 'high',
                'message': f'不同章节使用了不同的厂商名：{vendor_names}',
                'location': '多个章节',
                'suggestion': '统一使用同一个厂商名'
            })

        # 检查产品名一致性
        if len(set(product_names.values())) > 1:
            issues.append({
                'type': 'cross_chapter_consistency',
                'severity': 'medium',
                'message': f'不同章节使用了不同的产品名：{product_names}',
                'location': '多个章节',
                'suggestion': '统一使用同一个产品名'
            })

        # 2. 数据一致性检查（案例编号）
        case_numbers = {}
        for chapter_num, content in self.chapters.items():
            cases = re.findall(r'案例\s*[：:]\s*([^\n]+)', content)
            if cases:
                case_numbers[chapter_num] = cases

        # 检查是否有重复的案例但描述不同
        all_cases = []
        for cases in case_numbers.values():
            all_cases.extend(cases)

        if len(all_cases) != len(set(all_cases)):
            issues.append({
                'type': 'cross_chapter_consistency',
                'severity': 'medium',
                'message': '不同章节引用了相同的案例，但描述可能不一致',
                'location': '多个章节',
                'suggestion': '确保相同案例在不同章节中的描述一致'
            })

        # 3. 风格一致性检查（语气）
        formal_patterns = ['我们', '我司', '本公司', '贵方']
        style_scores = {}

        for chapter_num, content in self.chapters.items():
            formal_count = sum(content.count(p) for p in formal_patterns)
            style_scores[chapter_num] = formal_count / max(len(content), 1) * 1000  # 每千字出现次数

        # 检查风格差异
        if style_scores:
            max_score = max(style_scores.values())
            min_score = min(style_scores.values())
            if max_score > min_score * 2:  # 差异超过2倍
                issues.append({
                    'type': 'cross_chapter_consistency',
                    'severity': 'low',
                    'message': f'不同章节的语气风格差异较大：{style_scores}',
                    'location': '多个章节',
                    'suggestion': '统一使用正式或非正式的语气风格'
                })

        return issues

    def generate_report(self, output_file: Path, issues: List[Dict[str, Any]]):
        """生成一致性验证报告"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 按严重程度分类
        critical = [i for i in issues if i['severity'] == 'critical']
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']

        report = f"""# 一致性验证报告

生成时间：{timestamp}
分析报告：{self.analysis_file.name}
投标大纲：{self.outline_file.name}
章节数量：{len(self.chapters)}

## 验证摘要

- 总问题数：{len(issues)}
  - 严重问题：{len(critical)}
  - 高风险问题：{len(high)}
  - 中等问题：{len(medium)}
  - 低风险问题：{len(low)}

## 一致性指标

### 大纲-分析报告一致性
- M2 → Part C 映射：{'✅ 通过' if not any(i['type'] == 'outline_analysis_consistency' and 'Part C' in i['message'] for i in issues) else '❌ 未通过'}
- M4 → Part B 映射：{'✅ 通过' if not any(i['type'] == 'outline_analysis_consistency' and 'Part B' in i['message'] for i in issues) else '❌ 未通过'}
- M7 → 章节标题：{'✅ 通过' if not any(i['type'] == 'outline_analysis_consistency' and 'M7' in i['message'] for i in issues) else '❌ 未通过'}

### 章节-大纲一致性
- 章节号匹配：{'✅ 通过' if not any(i['type'] == 'chapter_outline_consistency' and '未找到' in i['message'] for i in issues) else '❌ 未通过'}
- 标题匹配：{'✅ 通过' if not any(i['type'] == 'chapter_outline_consistency' and '不匹配' in i['message'] for i in issues) else '❌ 未通过'}

### 章节间一致性
- 术语一致性：{'✅ 通过' if not any(i['type'] == 'cross_chapter_consistency' and '厂商名' in i['message'] for i in issues) else '❌ 未通过'}
- 数据一致性：{'✅ 通过' if not any(i['type'] == 'cross_chapter_consistency' and '案例' in i['message'] for i in issues) else '❌ 未通过'}
- 风格一致性：{'✅ 通过' if not any(i['type'] == 'cross_chapter_consistency' and '风格' in i['message'] for i in issues) else '❌ 未通过'}

## 问题详情

"""

        # 按类型分组
        for issue_type in ['outline_analysis_consistency', 'chapter_outline_consistency', 'cross_chapter_consistency']:
            type_issues = [i for i in issues if i['type'] == issue_type]
            if type_issues:
                type_name = {
                    'outline_analysis_consistency': '大纲-分析报告一致性',
                    'chapter_outline_consistency': '章节-大纲一致性',
                    'cross_chapter_consistency': '章节间一致性'
                }[issue_type]

                report += f"### {type_name}\n\n"
                for issue in type_issues:
                    severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
                    report += f"{severity_icon[issue['severity']]} **{issue['location']}**\n"
                    report += f"- 问题：{issue['message']}\n"
                    report += f"- 建议：{issue['suggestion']}\n\n"

        # 写入文件
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
