"""taa 输出验证器"""
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from docx import Document
from .docx_parser import DOCXParser


class TAAValidator:
    """taa 输出验证器"""

    # 臆测关键词
    SPECULATION_KEYWORDS = [
        '预计', '估计', '大约', '可能', '或许', '应该', '推测',
        '猜测', '假设', '大概', '似乎', '看起来', '据推断'
    ]

    # 合理使用上下文（排除误报）
    REASONABLE_CONTEXTS = [
        '招标文件中', '文件中提到', '根据文件', '文件要求',
        '明确要求', '明确规定', '文件规定'
    ]

    def __init__(self, analysis_file: Path, outline_file: Path = None):
        self.analysis_file = analysis_file
        self.outline_file = outline_file
        self.analysis_content = self._load_analysis()
        self.modules = self._parse_modules()

    def _load_analysis(self) -> str:
        """加载 Markdown 分析报告"""
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            return f.read()

    def _parse_modules(self) -> Dict[str, str]:
        """解析 M1-M7 模块"""
        modules = {}
        # 匹配 ## M1 到 ## M7
        pattern = r'## (M\d+)[^\n]*\n(.*?)(?=\n## M\d+|\Z)'
        matches = re.findall(pattern, self.analysis_content, re.DOTALL)
        for module_name, content in matches:
            modules[module_name] = content.strip()
        return modules

    def validate_all(self, tender_file: Path = None) -> List[Dict[str, Any]]:
        """执行所有验证"""
        issues = []
        issues.extend(self._check_module_completeness())
        issues.extend(self._check_citations())
        issues.extend(self._check_no_speculation())
        issues.extend(self._check_required_clauses())
        issues.extend(self._check_disqualification_marks())
        issues.extend(self._check_m2_matrix_completeness())
        issues.extend(self._check_m4_scoring_total())
        if tender_file:
            issues.extend(self.validate_information_accuracy(tender_file))
        return issues

    def _check_module_completeness(self) -> List[Dict[str, Any]]:
        """检查模块完整性"""
        issues = []
        required_modules = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']

        for module in required_modules:
            if module not in self.modules:
                issues.append({
                    'type': 'completeness',
                    'severity': 'critical',
                    'module': module,
                    'description': f'缺少 {module} 模块',
                    'location': '分析报告',
                    'suggestion': f'补充 {module} 模块内容',
                })
            elif len(self.modules[module]) < 100:
                issues.append({
                    'type': 'completeness',
                    'severity': 'high',
                    'module': module,
                    'description': f'{module} 模块内容过少（<100 字符）',
                    'location': '分析报告',
                    'suggestion': f'扩充 {module} 模块内容',
                })

        return issues

    def _check_citations(self) -> List[Dict[str, Any]]:
        """检查出处标注"""
        issues = []

        # 统计关键信息点（数字、日期、金额）
        key_info_pattern = r'(\d+[\d.,]*\s*(?:元|万元|亿元|天|个月|年|%|台|套|人|项))'
        key_infos = re.findall(key_info_pattern, self.analysis_content)

        # 统计出处标注
        citation_pattern = r'（出处：[^）]+）'
        citations = re.findall(citation_pattern, self.analysis_content)

        if len(key_infos) > 0:
            citation_rate = len(citations) / len(key_infos)
            if citation_rate < 0.3:
                issues.append({
                    'type': 'citation',
                    'severity': 'high',
                    'module': 'all',
                    'description': f'出处标注率过低（{citation_rate:.1%}，应 ≥30%）',
                    'location': '分析报告',
                    'suggestion': '为关键信息点（数字、日期、金额）添加出处标注',
                })

        return issues

    def _check_no_speculation(self) -> List[Dict[str, Any]]:
        """检查臆测"""
        issues = []

        for module_name, content in self.modules.items():
            for keyword in self.SPECULATION_KEYWORDS:
                # 查找关键词
                matches = re.finditer(keyword, content)
                for match in matches:
                    # 提取上下文
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]

                    # 检查是否为合理使用
                    is_reasonable = any(ctx in context for ctx in self.REASONABLE_CONTEXTS)

                    if not is_reasonable:
                        issues.append({
                            'type': 'speculation',
                            'severity': 'high',
                            'module': module_name,
                            'description': f'检测到臆测关键词：{keyword}',
                            'location': f'{module_name}：{context}',
                            'suggestion': '基于招标文件原文描述，避免主观推测',
                        })

        return issues

    def _check_required_clauses(self) -> List[Dict[str, Any]]:
        """检查必须条款标注"""
        issues = []

        if 'M2' in self.modules:
            m2_content = self.modules['M2']
            required_marks = re.findall(r'【必须】', m2_content)

            if len(required_marks) == 0:
                issues.append({
                    'type': 'required_clause',
                    'severity': 'high',
                    'module': 'M2',
                    'description': 'M2 技术要求矩阵缺少【必须】标注',
                    'location': 'M2 技术要求矩阵',
                    'suggestion': '为必须满足的技术要求添加【必须】标注',
                })

        return issues

    def _check_disqualification_marks(self) -> List[Dict[str, Any]]:
        """检查废标项标记（支持文本标记和表格两种格式）"""
        issues = []

        if 'M5' in self.modules:
            m5_content = self.modules['M5']
            # 格式1：文本标记 [废标]
            text_marks = re.findall(r'\[废标\]', m5_content)
            # 格式2：表格格式（含"资格性废标"、"符合性废标"等列内容）
            table_marks = re.findall(r'(?:资格性废标|符合性废标|时间性废标|格式性废标|实质性废标|废标类型)', m5_content)

            if len(text_marks) == 0 and len(table_marks) == 0:
                issues.append({
                    'type': 'disqualification',
                    'severity': 'critical',
                    'module': 'M5',
                    'description': 'M5 废标条款缺少废标标记（[废标] 文本或废标类型表格）',
                    'location': 'M5 废标条款',
                    'suggestion': '为废标条款添加 [废标] 标记，或使用包含"废标类型"列的表格格式',
                })

        return issues

    def _check_m2_matrix_completeness(self) -> List[Dict[str, Any]]:
        """验证 M2 技术要求矩阵完整性"""
        issues = []

        if 'M2' not in self.modules:
            return issues

        m2_content = self.modules['M2']

        # 检查表格格式（应包含：ID、分类、技术要求、优先级、支持度、原文出处）
        required_columns = ['ID', '技术要求', '优先级', '支持度', '出处']
        missing_columns = []

        for col in required_columns:
            if col not in m2_content:
                missing_columns.append(col)

        if missing_columns:
            issues.append({
                'type': 'm2_matrix',
                'severity': 'high',
                'module': 'M2',
                'description': f'M2 技术要求矩阵缺少必要列：{", ".join(missing_columns)}',
                'location': 'M2 技术要求矩阵',
                'suggestion': f'补充缺失的列：{", ".join(missing_columns)}',
            })

        # 检查是否有表格结构
        if '|' not in m2_content and '表' not in m2_content:
            issues.append({
                'type': 'm2_matrix',
                'severity': 'high',
                'module': 'M2',
                'description': 'M2 技术要求矩阵缺少表格结构',
                'location': 'M2 技术要求矩阵',
                'suggestion': '使用表格形式组织技术要求',
            })

        return issues

    def _check_m4_scoring_total(self) -> List[Dict[str, Any]]:
        """验证 M4 评分标准总分"""
        issues = []

        if 'M4' not in self.modules:
            return issues

        m4_content = self.modules['M4']

        # 提取所有评分项的分值
        scoring_pattern = r'(\d+(?:\.\d+)?)\s*分'
        scores = re.findall(scoring_pattern, m4_content)

        if scores:
            total_score = sum(float(s) for s in scores)

            # 检查总分是否接近 100 分（允许 ±2 分误差）
            if abs(total_score - 100) > 2:
                issues.append({
                    'type': 'm4_scoring',
                    'severity': 'high',
                    'module': 'M4',
                    'description': f'M4 评分标准总分异常（{total_score} 分，应为 100 分）',
                    'location': 'M4 评分标准',
                    'suggestion': '检查评分项分值，确保总分为 100 分',
                })

        return issues

    def validate_information_accuracy(self, tender_file: Path) -> List[Dict[str, Any]]:
        """验证信息准确性（与招标文件原文对比）"""
        issues = []

        # 从分析报告中提取关键数字
        budget_pattern = r'预算[：:]\s*([\d.,]+)\s*(?:元|万元|亿元)'
        duration_pattern = r'工期[：:]\s*(\d+)\s*(?:天|个月|年)'
        date_pattern = r'(\d{4}年\d{1,2}月\d{1,2}日)'

        analysis_budget = re.search(budget_pattern, self.analysis_content)
        analysis_duration = re.search(duration_pattern, self.analysis_content)
        analysis_dates = re.findall(date_pattern, self.analysis_content)

        # 从招标文件中提取对应信息（需要 DOCX 解析）
        try:
            doc_data = DOCXParser.parse_document(tender_file)
            tender_content = doc_data['text']

            # 对比预算
            if analysis_budget:
                tender_budget = re.search(budget_pattern, tender_content)
                if tender_budget and analysis_budget.group(1) != tender_budget.group(1):
                    issues.append({
                        'type': 'information_accuracy',
                        'severity': 'critical',
                        'module': 'M1',
                        'description': f'预算金额不一致：分析报告 {analysis_budget.group(1)}，招标文件 {tender_budget.group(1)}',
                        'location': 'M1 项目概况',
                        'suggestion': '核对招标文件原文，修正预算金额',
                    })

            # 对比工期
            if analysis_duration:
                tender_duration = re.search(duration_pattern, tender_content)
                if tender_duration and analysis_duration.group(1) != tender_duration.group(1):
                    issues.append({
                        'type': 'information_accuracy',
                        'severity': 'high',
                        'module': 'M1',
                        'description': f'工期不一致：分析报告 {analysis_duration.group(1)}，招标文件 {tender_duration.group(1)}',
                        'location': 'M1 项目概况',
                        'suggestion': '核对招标文件原文，修正工期',
                    })

        except Exception as e:
            issues.append({
                'type': 'information_accuracy',
                'severity': 'medium',
                'module': 'all',
                'description': f'无法读取招标文件进行准确性验证：{str(e)}',
                'location': '分析报告',
                'suggestion': '手动核对关键信息（预算、工期、日期）',
            })

        return issues

    def parse_outline(self, outline_file: Path = None) -> Dict[str, Any]:
        """解析 DOCX 大纲"""
        if outline_file:
            self.outline_file = outline_file

        if not self.outline_file or not self.outline_file.exists():
            return {}

        doc_data = DOCXParser.parse_document(self.outline_file)
        structure = DOCXParser.parse_outline_structure(Document(self.outline_file))

        return {
            'file': str(self.outline_file),
            'structure': structure,
            'chapter_count': len([s for s in structure if s['level'] <= 2]),
            'text': doc_data['text'],
            'tables': doc_data['tables'],
        }

    def validate_outline(self, outline_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """验证大纲质量"""
        issues = []

        if not outline_data:
            issues.append({
                'type': 'completeness',
                'severity': 'critical',
                'module': 'outline',
                'description': '投标大纲文件不存在或无法解析',
                'location': '投标大纲',
                'suggestion': '检查大纲文件路径',
            })
            return issues

        # 检查章节数量
        chapter_count = outline_data.get('chapter_count', 0)
        if chapter_count < 20:
            issues.append({
                'type': 'completeness',
                'severity': 'high',
                'module': 'outline',
                'description': f'章节数量过少（{chapter_count} 个，应 ≥20 个）',
                'location': '投标大纲',
                'suggestion': '补充章节内容',
            })

        # 检查标准章节
        text = outline_data.get('text', '')
        standard_chapters = ['投标函', '商务', '技术', '报价', '服务']
        for chapter in standard_chapters:
            if chapter not in text:
                issues.append({
                    'type': 'completeness',
                    'severity': 'critical',
                    'module': 'outline',
                    'description': f'缺少标准章节：{chapter}',
                    'location': '投标大纲',
                    'suggestion': f'添加 {chapter} 章节',
                })

        # 检查需求覆盖度（Part C）
        if 'Part C' in text:
            # 提取 M2 必须条款
            if 'M2' in self.modules:
                required_clauses = re.findall(r'【必须】([^\n]+)', self.modules['M2'])
                if required_clauses:
                    # 检查 Part C 表格覆盖度
                    part_c_tables = [t for t in outline_data.get('tables', [])
                                     if any('需求' in str(row) for row in t.get('data', []))]
                    if part_c_tables:
                        covered = sum(1 for clause in required_clauses
                                      if any(clause[:10] in str(table.get('data', []))
                                             for table in part_c_tables))
                        coverage = covered / len(required_clauses) if required_clauses else 0
                        if coverage < 0.8:
                            issues.append({
                                'type': 'completeness',
                                'severity': 'critical',
                                'module': 'outline',
                                'description': f'需求覆盖度不足（{coverage:.1%}，应 ≥80%）',
                                'location': 'Part C 需求-章节对应表',
                                'suggestion': '补充 Part C 表格，覆盖所有【必须】条款',
                            })

        return issues

    def generate_report(self, issues: List[Dict[str, Any]], output_file: Path):
        """生成 Markdown 验证报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 按严重程度分类
        critical = [i for i in issues if i['severity'] == 'critical']
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']

        report = f"""# taa 分析报告验证报告

生成时间：{timestamp}
分析文件：{self.analysis_file}
大纲文件：{self.outline_file or '未提供'}

## 验证摘要

- 总问题数：{len(issues)} 个
- 严重问题：{len(critical)} 个
- 高风险问题：{len(high)} 个
- 中等问题：{len(medium)} 个
- 低风险问题：{len(low)} 个

## 模块完整性

"""
        for module in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
            status = '✅' if module in self.modules and len(self.modules[module]) >= 100 else '❌'
            length = len(self.modules.get(module, ''))
            report += f"- {module}：{status} ({length} 字符)\n"

        if critical:
            report += "\n## 严重问题\n\n"
            for i, issue in enumerate(critical, 1):
                report += f"### {i}. [{issue['module']}] {issue['description']}\n\n"
                report += f"- 位置：{issue['location']}\n"
                report += f"- 建议：{issue['suggestion']}\n\n"

        if high:
            report += "\n## 高风险问题\n\n"
            for i, issue in enumerate(high, 1):
                report += f"### {i}. [{issue['module']}] {issue['description']}\n\n"
                report += f"- 位置：{issue['location']}\n"
                report += f"- 建议：{issue['suggestion']}\n\n"

        if medium:
            report += "\n## 中等问题\n\n"
            for i, issue in enumerate(medium, 1):
                report += f"{i}. [{issue['module']}] {issue['description']}\n"

        if low:
            report += "\n## 低风险问题\n\n"
            for i, issue in enumerate(low, 1):
                report += f"{i}. [{issue['module']}] {issue['description']}\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
