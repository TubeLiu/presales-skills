"""质量检查规则引擎"""
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class QualityChecker:
    """质量检查规则引擎"""

    def __init__(self, test_context: Dict[str, Any]):
        self.test_context = test_context

    def generate_final_report(self, output_file: Path):
        """生成最终测试报告（增强版）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 汇总所有问题
        all_issues = []
        taa_issues = self.test_context.get('taa_issues', [])
        outline_issues = self.test_context.get('outline_issues', [])
        taw_issues = self.test_context.get('taw_issues', [])
        consistency_issues = self.test_context.get('consistency_issues', [])
        image_quality_issues = self.test_context.get('image_quality_issues', [])
        professionalism_issues = self.test_context.get('professionalism_issues', [])

        all_issues.extend(taa_issues)
        all_issues.extend(outline_issues)
        all_issues.extend(taw_issues)
        all_issues.extend(consistency_issues)
        all_issues.extend(image_quality_issues)
        all_issues.extend(professionalism_issues)

        # 计算质量指标
        metrics = self._calculate_metrics()

        # 计算一级指标
        primary_metrics = self._calculate_primary_metrics()

        # 问题分类统计
        issue_stats = self._categorize_issues(all_issues)

        # 生成改进建议
        suggestions = self._generate_suggestions(all_issues)

        # 生成报告
        report = f"""# 端到端测试报告

生成时间：{timestamp}
测试文件：{self.test_context.get('tender_file', 'N/A')}

## 执行摘要

- 执行时间：{self.test_context.get('execution_time', 'N/A')}
- taa 输出：{len(self.test_context.get('taa_outputs', {}))} 个文件
- taw 输出：{len(self.test_context.get('taw_outputs', {}))} 个章节
- 总问题数：{len(all_issues)} 个
  - 严重问题：{issue_stats['critical']} 个
  - 高风险问题：{issue_stats['high']} 个
  - 中等问题：{issue_stats['medium']} 个
  - 低风险问题：{issue_stats['low']} 个

## 质量指标仪表盘

### 一级指标（总体质量）

| 指标 | 得分 | 目标 | 状态 |
|------|------|------|------|
| 分析报告质量 | {primary_metrics['analysis_quality']*100:.1f}% | ≥85% | {'✅' if primary_metrics['analysis_quality'] >= 0.85 else '❌'} |
| 投标大纲质量 | {primary_metrics['outline_quality']*100:.1f}% | ≥90% | {'✅' if primary_metrics['outline_quality'] >= 0.90 else '❌'} |
| 章节内容质量 | {primary_metrics['content_quality']*100:.1f}% | ≥80% | {'✅' if primary_metrics['content_quality'] >= 0.80 else '❌'} |
| 一致性质量 | {primary_metrics['consistency_quality']*100:.1f}% | ≥90% | {'✅' if primary_metrics['consistency_quality'] >= 0.90 else '❌'} |
| **总体质量** | **{primary_metrics['overall_quality']*100:.1f}%** | **≥75%** | **{'✅' if primary_metrics['overall_quality'] >= 0.75 else '❌'}** |

### 二级指标（详细）

#### taa 分析报告

- 模块完整度：{metrics['taa_module_completeness']:.1%} (目标 100%)
- 出处标注率：{metrics['taa_citation_rate']:.1%} (目标 ≥30%)
- 臆测检出数：{metrics['taa_speculation_count']} 个 (目标 0)
- 信息准确性：{'✅ 通过' if metrics.get('taa_information_accuracy', False) else '❌ 未通过'}

#### taa 投标大纲

- 章节数量：{metrics['outline_chapter_count']} 个 (目标 ≥20)
- 需求覆盖度：{metrics['outline_requirement_coverage']:.1%} (目标 ≥80%)
- 编号规范性：{metrics['outline_numbering_compliance']}

#### taw 章节内容

- 平均字数：{metrics['taw_avg_word_count']:.0f} 字 (核心章节 ≥4500)
- 平均图片数：{metrics['taw_avg_image_count']:.1f} 张 (目标 2-3)
- 平均引用数：{metrics['taw_avg_citation_count']:.1f} 个
- 评分覆盖度：{metrics['taw_scoring_coverage']:.1%} (目标 ≥50%)
- 关键词覆盖率：{metrics['taw_keyword_coverage']:.1%} (目标 ≥80%)

#### 一致性

- 大纲-分析一致性：{'✅ 通过' if len([i for i in consistency_issues if 'outline_analysis' in i.get('type', '')]) == 0 else '❌ 未通过'}
- 章节-大纲一致性：{'✅ 通过' if len([i for i in consistency_issues if 'chapter_outline' in i.get('type', '')]) == 0 else '❌ 未通过'}
- 章节间一致性：{'✅ 通过' if len([i for i in consistency_issues if 'cross_chapter' in i.get('type', '')]) == 0 else '❌ 未通过'}

## 质量雷达图数据

```
分析报告质量: {primary_metrics['analysis_quality']*100:.1f}
投标大纲质量: {primary_metrics['outline_quality']*100:.1f}
章节内容质量: {primary_metrics['content_quality']*100:.1f}
一致性质量: {primary_metrics['consistency_quality']*100:.1f}
```

## 问题清单

"""

        # 按严重程度输出问题
        for severity in ['critical', 'high', 'medium', 'low']:
            severity_issues = [i for i in all_issues if i['severity'] == severity]
            if severity_issues:
                severity_name = {
                    'critical': '严重问题',
                    'high': '高风险问题',
                    'medium': '中等问题',
                    'low': '低风险问题',
                }[severity]

                report += f"\n### {severity_name} ({len(severity_issues)})\n\n"

                for i, issue in enumerate(severity_issues, 1):
                    if severity in ['critical', 'high']:
                        report += f"#### {i}. [{issue.get('module', issue.get('chapter', 'N/A'))}] {issue.get('description', issue.get('message', 'N/A'))}\n\n"
                        report += f"- 位置：{issue['location']}\n"
                        report += f"- 建议：{issue['suggestion']}\n\n"
                    else:
                        report += f"{i}. [{issue.get('module', issue.get('chapter', 'N/A'))}] {issue.get('description', issue.get('message', 'N/A'))}\n"

        # trv 审核结果
        if self.test_context.get('trv_reports'):
            report += "\n## trv 审核结果\n\n"
            for trv_report in self.test_context['trv_reports']:
                report += f"- {trv_report['type']}：{trv_report['status']}\n"

        # 改进建议
        if suggestions:
            report += "\n## 改进建议\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                report += f"{i}. {suggestion}\n"

        # 关键改进点
        critical_improvements = self._identify_critical_improvements(all_issues)
        if critical_improvements:
            report += "\n## 关键改进点\n\n"
            for i, improvement in enumerate(critical_improvements, 1):
                report += f"{i}. {improvement}\n"

        # 写入文件
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

    def _calculate_metrics(self) -> Dict[str, Any]:
        """计算质量指标"""
        metrics = {
            # taa 分析报告
            'taa_module_completeness': 0.0,
            'taa_citation_rate': 0.0,
            'taa_speculation_count': 0,

            # taa 投标大纲
            'outline_chapter_count': 0,
            'outline_requirement_coverage': 0.0,
            'outline_numbering_compliance': '未检查',

            # taw 章节内容
            'taw_avg_word_count': 0.0,
            'taw_avg_image_count': 0.0,
            'taw_avg_citation_count': 0.0,
            'taw_scoring_coverage': 0.0,
            'taw_keyword_coverage': 0.0,
        }

        # 从测试上下文提取指标
        if 'taa_metrics' in self.test_context:
            metrics.update(self.test_context['taa_metrics'])

        if 'outline_metrics' in self.test_context:
            metrics.update(self.test_context['outline_metrics'])

        if 'taw_metrics' in self.test_context:
            metrics.update(self.test_context['taw_metrics'])

        return metrics

    def _categorize_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """问题分类统计"""
        return {
            'critical': len([i for i in issues if i['severity'] == 'critical']),
            'high': len([i for i in issues if i['severity'] == 'high']),
            'medium': len([i for i in issues if i['severity'] == 'medium']),
            'low': len([i for i in issues if i['severity'] == 'low']),
        }

    def _generate_suggestions(self, issues: List[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 按问题类型分组
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)

        # 针对每种问题类型生成建议
        if 'completeness' in issue_types:
            suggestions.append('补充缺失的模块和章节内容，确保结构完整')

        if 'citation' in issue_types:
            suggestions.append('为关键信息点（数字、日期、金额）添加出处标注，提高可信度')

        if 'speculation' in issue_types:
            suggestions.append('基于招标文件原文描述，避免主观推测和臆测')

        if 'word_count' in issue_types:
            suggestions.append('扩充章节内容，核心章节达到 4500+ 字，其他章节达到 2400+ 字')

        if 'image_count' in issue_types:
            suggestions.append('为每个章节添加 2-3 张图片，提升图文比例')

        if 'scoring_coverage' in issue_types:
            suggestions.append('补充评分项响应内容，确保覆盖所有评分点')

        if 'keyword_coverage' in issue_types:
            suggestions.append('补充关键词，确保覆盖率达到 80% 以上')

        if 'redline_violation' in issue_types:
            suggestions.append('移除违反红线条款的内容，避免废标风险')

        return suggestions

    def _calculate_primary_metrics(self) -> Dict[str, float]:
        """计算一级指标"""
        # 从测试上下文获取质量得分（如果已计算）
        if 'quality_scores' in self.test_context:
            return self.test_context['quality_scores']

        # 否则简化计算
        taa_issues = self.test_context.get('taa_issues', [])
        outline_issues = self.test_context.get('outline_issues', [])
        taw_issues = self.test_context.get('taw_issues', [])
        consistency_issues = self.test_context.get('consistency_issues', [])

        # 1. 分析报告质量
        taa_critical = len([i for i in taa_issues if i['severity'] == 'critical'])
        analysis_quality = 1.0 if taa_critical == 0 else 0.5

        # 2. 投标大纲质量
        outline_critical = len([i for i in outline_issues if i['severity'] == 'critical'])
        outline_quality = 1.0 if outline_critical == 0 else 0.5

        # 3. 章节内容质量
        taw_critical = len([i for i in taw_issues if i['severity'] == 'critical'])
        content_quality = 1.0 if taw_critical == 0 else 0.5

        # 4. 一致性质量
        consistency_high = len([i for i in consistency_issues if i['severity'] in ['critical', 'high']])
        consistency_quality = 1.0 if consistency_high == 0 else 0.7

        # 总体质量
        overall_quality = (
            analysis_quality * 0.3 +
            outline_quality * 0.2 +
            content_quality * 0.4 +
            consistency_quality * 0.1
        )

        return {
            'analysis_quality': analysis_quality,
            'outline_quality': outline_quality,
            'content_quality': content_quality,
            'consistency_quality': consistency_quality,
            'overall_quality': overall_quality,
        }

    def _identify_critical_improvements(self, issues: List[Dict[str, Any]]) -> List[str]:
        """识别关键改进点"""
        improvements = []

        # 统计严重和高风险问题
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        high_issues = [i for i in issues if i['severity'] == 'high']

        # 按类型分组
        critical_by_type = {}
        for issue in critical_issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in critical_by_type:
                critical_by_type[issue_type] = []
            critical_by_type[issue_type].append(issue)

        # 生成关键改进点
        if 'completeness' in critical_by_type:
            improvements.append(f"【严重】补充缺失的模块和章节（{len(critical_by_type['completeness'])} 处）")

        if 'disqualification' in critical_by_type:
            improvements.append(f"【严重】标记废标条款（{len(critical_by_type['disqualification'])} 处）")

        if 'scoring_coverage' in critical_by_type:
            improvements.append(f"【严重】提高评分覆盖度（{len(critical_by_type['scoring_coverage'])} 处）")

        if 'redline_violation' in critical_by_type:
            improvements.append(f"【严重】移除违反红线的内容（{len(critical_by_type['redline_violation'])} 处）")

        # 高风险问题
        if len(high_issues) > 5:
            improvements.append(f"【高风险】解决 {len(high_issues)} 个高风险问题，优先处理字数、引用、关键词覆盖")

        return improvements
