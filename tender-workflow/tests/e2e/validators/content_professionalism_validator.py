"""内容专业性验证器 - 评估技术深度和避免空话套话"""
import re
from pathlib import Path
from typing import Dict, List, Any
from .docx_parser import DOCXParser


class ContentProfessionalismValidator:
    """内容专业性验证器"""

    # 空话套话列表
    EMPTY_PHRASES = [
        '先进的', '优秀的', '强大的', '卓越的', '领先的', '一流的',
        '以客户为中心', '以人为本', '精益求精', '追求卓越',
        '高度重视', '充分发挥', '积极推进', '全面提升',
        '深入贯彻', '认真落实', '切实加强', '不断完善',
        '有效提高', '显著增强', '明显改善', '大幅提升',
        '世界级', '国际领先', '行业第一', '无与伦比'
    ]

    # 技术深度指标关键词
    ARCHITECTURE_KEYWORDS = [
        '架构', '设计', '模块', '组件', '层次', '拓扑',
        '微服务', '容器', '集群', '节点', '网关', '负载均衡'
    ]

    IMPLEMENTATION_KEYWORDS = [
        '实现', '部署', '配置', '安装', '集成', '对接',
        'API', '接口', '协议', '算法', '流程', '步骤'
    ]

    PERFORMANCE_KEYWORDS = [
        'QPS', 'TPS', 'RT', '响应时间', '吞吐量', '并发',
        '可用性', 'SLA', '性能', '指标', '监控', '告警',
        'CPU', '内存', '磁盘', '网络', '带宽'
    ]

    def __init__(self, chapter_file: Path):
        self.chapter_file = chapter_file
        doc_data = DOCXParser.parse_document(chapter_file)
        self.chapter_content = doc_data['text']
        self.paragraphs = self._split_paragraphs()

    def _split_paragraphs(self) -> List[str]:
        """分割段落"""
        # 按双换行符分割
        paragraphs = re.split(r'\n\s*\n', self.chapter_content)
        # 过滤空段落
        return [p.strip() for p in paragraphs if p.strip()]

    def validate_all(self) -> List[Dict[str, Any]]:
        """执行所有专业性验证"""
        issues = []
        issues.extend(self.validate_technical_depth())
        issues.extend(self.validate_avoid_empty_phrases())
        issues.extend(self.validate_logical_coherence())
        return issues

    def validate_technical_depth(self) -> List[Dict[str, Any]]:
        """验证技术深度"""
        issues = []

        # 检查是否有架构描述
        has_architecture = any(
            keyword in self.chapter_content
            for keyword in self.ARCHITECTURE_KEYWORDS
        )

        # 检查是否有实现细节
        has_implementation = any(
            keyword in self.chapter_content
            for keyword in self.IMPLEMENTATION_KEYWORDS
        )

        # 检查是否有性能指标
        has_performance = any(
            keyword in self.chapter_content
            for keyword in self.PERFORMANCE_KEYWORDS
        )

        # 计算技术深度得分
        depth_score = sum([has_architecture, has_implementation, has_performance]) / 3

        if depth_score < 0.33:  # 少于1个维度
            issues.append({
                'type': 'technical_depth',
                'severity': 'high',
                'message': '技术深度不足，缺少架构描述、实现细节和性能指标',
                'location': '整个章节',
                'suggestion': '添加技术架构图、实现方案说明或性能指标数据'
            })
        elif depth_score < 0.67:  # 少于2个维度
            issues.append({
                'type': 'technical_depth',
                'severity': 'medium',
                'message': f'技术深度一般（{depth_score*100:.0f}%），建议增加更多技术细节',
                'location': '整个章节',
                'suggestion': '补充缺失的维度：' + (
                    '架构描述' if not has_architecture else
                    '实现细节' if not has_implementation else
                    '性能指标'
                )
            })

        # 检查是否有具体数字
        numbers = re.findall(r'\d+(?:\.\d+)?(?:\s*[%万亿KMGTB])?', self.chapter_content)
        if len(numbers) < 5:
            issues.append({
                'type': 'technical_depth',
                'severity': 'medium',
                'message': f'缺少具体数据支撑（仅 {len(numbers)} 个数字）',
                'location': '整个章节',
                'suggestion': '添加具体的性能指标、容量数据或案例数据'
            })

        return issues

    def validate_avoid_empty_phrases(self) -> List[Dict[str, Any]]:
        """检测空话套话"""
        issues = []

        # 统计空话套话出现次数
        empty_phrase_count = {}
        for phrase in self.EMPTY_PHRASES:
            count = self.chapter_content.count(phrase)
            if count > 0:
                empty_phrase_count[phrase] = count

        # 计算空话套话密度
        total_empty = sum(empty_phrase_count.values())
        paragraph_count = len(self.paragraphs)
        density = total_empty / max(paragraph_count, 1)

        if density > 0.1:  # 平均每10段有1个以上空话套话
            issues.append({
                'type': 'empty_phrases',
                'severity': 'high',
                'message': f'空话套话过多（{total_empty} 处，密度 {density*100:.1f}%）',
                'location': '整个章节',
                'suggestion': f'减少使用空洞词汇，用具体事实替代。高频词：{", ".join(list(empty_phrase_count.keys())[:3])}'
            })
        elif density > 0.05:  # 平均每20段有1个以上
            issues.append({
                'type': 'empty_phrases',
                'severity': 'medium',
                'message': f'存在一定数量的空话套话（{total_empty} 处）',
                'location': '整个章节',
                'suggestion': f'尽量用具体描述替代空洞词汇。出现的词：{", ".join(list(empty_phrase_count.keys())[:5])}'
            })

        # 检查特定段落
        for i, paragraph in enumerate(self.paragraphs):
            paragraph_empty_count = sum(paragraph.count(phrase) for phrase in self.EMPTY_PHRASES)
            if paragraph_empty_count >= 3:  # 单段落超过3个空话套话
                issues.append({
                    'type': 'empty_phrases',
                    'severity': 'medium',
                    'message': f'第 {i+1} 段空话套话过多（{paragraph_empty_count} 处）',
                    'location': f'第 {i+1} 段',
                    'suggestion': '用具体案例、数据或技术细节替代空洞描述'
                })

        return issues

    def validate_logical_coherence(self) -> List[Dict[str, Any]]:
        """检查逻辑连贯性"""
        issues = []

        # 检查段落间的逻辑连接词
        logical_connectors = [
            '因此', '所以', '由于', '因为', '从而', '进而',
            '首先', '其次', '再次', '最后', '然后',
            '同时', '此外', '另外', '而且', '并且',
            '但是', '然而', '不过', '虽然', '尽管'
        ]

        connector_count = sum(
            self.chapter_content.count(connector)
            for connector in logical_connectors
        )

        # 计算连接词密度
        connector_density = connector_count / max(len(self.paragraphs), 1)

        if connector_density < 0.3:  # 平均每3段少于1个连接词
            issues.append({
                'type': 'logical_coherence',
                'severity': 'medium',
                'message': f'段落间逻辑连接较弱（连接词密度 {connector_density:.2f}）',
                'location': '整个章节',
                'suggestion': '增加逻辑连接词，使段落间关系更清晰'
            })

        # 检查是否有列表或结构化内容
        has_list = bool(re.search(r'[1-9]\.|[一二三四五]、|[\u2460-\u2473]|[①-⑩]', self.chapter_content))
        has_table = '|' in self.chapter_content or '表' in self.chapter_content

        if not has_list and not has_table and len(self.paragraphs) > 10:
            issues.append({
                'type': 'logical_coherence',
                'severity': 'low',
                'message': '长篇内容缺少结构化呈现（列表、表格）',
                'location': '整个章节',
                'suggestion': '使用列表或表格组织复杂信息，提高可读性'
            })

        # 检查段落长度分布
        long_paragraphs = [p for p in self.paragraphs if len(p) > 500]
        if len(long_paragraphs) > len(self.paragraphs) * 0.5:
            issues.append({
                'type': 'logical_coherence',
                'severity': 'low',
                'message': f'过长段落较多（{len(long_paragraphs)} / {len(self.paragraphs)}）',
                'location': '整个章节',
                'suggestion': '将长段落拆分为多个短段落，每段聚焦一个主题'
            })

        return issues

    def generate_report(self, output_file: Path, issues: List[Dict[str, Any]]):
        """生成内容专业性验证报告"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 按严重程度分类
        critical = [i for i in issues if i['severity'] == 'critical']
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']

        # 计算专业性得分
        has_architecture = any(kw in self.chapter_content for kw in self.ARCHITECTURE_KEYWORDS)
        has_implementation = any(kw in self.chapter_content for kw in self.IMPLEMENTATION_KEYWORDS)
        has_performance = any(kw in self.chapter_content for kw in self.PERFORMANCE_KEYWORDS)
        depth_score = sum([has_architecture, has_implementation, has_performance]) / 3

        empty_count = sum(self.chapter_content.count(phrase) for phrase in self.EMPTY_PHRASES)
        empty_density = empty_count / max(len(self.paragraphs), 1)

        report = f"""# 内容专业性验证报告

生成时间：{timestamp}
章节文件：{self.chapter_file.name}

## 验证摘要

- 段落总数：{len(self.paragraphs)}
- 总问题数：{len(issues)}
  - 严重问题：{len(critical)}
  - 高风险问题：{len(high)}
  - 中等问题：{len(medium)}
  - 低风险问题：{len(low)}

## 专业性指标

### 技术深度（{depth_score*100:.0f}%）
- 架构描述：{'✅ 有' if has_architecture else '❌ 无'}
- 实现细节：{'✅ 有' if has_implementation else '❌ 无'}
- 性能指标：{'✅ 有' if has_performance else '❌ 无'}

### 空话套话密度（{empty_density*100:.1f}%）
- 空话套话总数：{empty_count}
- 评价：{'✅ 优秀' if empty_density < 0.05 else '🟡 一般' if empty_density < 0.1 else '❌ 较多'}

### 逻辑连贯性
- 段落数：{len(self.paragraphs)}
- 结构化内容：{'✅ 有' if any('列表' in i['message'] or '表格' in i['message'] for i in issues) else '✅ 有'}

## 问题详情

"""

        # 按类型分组
        for issue_type in ['technical_depth', 'empty_phrases', 'logical_coherence']:
            type_issues = [i for i in issues if i['type'] == issue_type]
            if type_issues:
                type_name = {
                    'technical_depth': '技术深度',
                    'empty_phrases': '空话套话',
                    'logical_coherence': '逻辑连贯性'
                }[issue_type]

                report += f"### {type_name}\n\n"
                for issue in type_issues:
                    severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
                    report += f"{severity_icon[issue['severity']]} **{issue['location']}**\n"
                    report += f"- 问题：{issue['message']}\n"
                    report += f"- 建议：{issue['suggestion']}\n\n"

        if not issues:
            report += "✅ 未发现专业性问题\n"

        # 写入文件
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
