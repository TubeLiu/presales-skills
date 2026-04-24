"""图片质量验证器 - 验证图片来源、质量和适用性"""
import re
from pathlib import Path
from typing import Dict, List, Any
from .docx_parser import DOCXParser


class ImageQualityValidator:
    """图片质量验证器"""

    # 允许的图片来源
    ALLOWED_SOURCES = [
        'Local-KnowledgeBase/',   # Local-KnowledgeBase 图文共生
        'drafts/',          # 生成的图片
        '/tmp/',            # 临时生成（AI/drawio）
    ]

    # 互联网图片标记
    INTERNET_INDICATORS = [
        'http://', 'https://', 'www.', '.com', '.cn', '.net'
    ]

    # 最小分辨率要求（像素）
    MIN_RESOLUTION = 800

    # 最大文件大小（字节）
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

    # 允许的图片格式
    ALLOWED_FORMATS = ['.png', '.jpg', '.jpeg', '.svg']

    def __init__(self, chapter_file: Path):
        self.chapter_file = chapter_file
        doc_data = DOCXParser.parse_document(chapter_file)
        self.chapter_content = doc_data['text']
        self.images = self._extract_images()

    def _extract_images(self) -> List[Dict[str, Any]]:
        """提取章节中的图片信息"""
        images = []

        # 从 DOCX 中提取图片引用
        # 注意：这里需要扩展 DOCXParser 来支持图片提取
        # 当前简化实现：从文本中提取图片说明
        image_patterns = [
            r'图\s*(\d+[-\.]\d+)[：:](.*?)(?=\n|$)',  # 图 5-1：架构图
            r'!\[([^\]]+)\]\(([^\)]+)\)',  # Markdown 格式
        ]

        for pattern in image_patterns:
            matches = re.finditer(pattern, self.chapter_content)
            for match in matches:
                if len(match.groups()) == 2:
                    images.append({
                        'number': match.group(1),
                        'caption': match.group(2).strip() if len(match.groups()) > 1 else '',
                        'source': self._infer_source(match.group(0))
                    })

        return images

    def _infer_source(self, image_text: str) -> str:
        """推断图片来源"""
        for indicator in self.INTERNET_INDICATORS:
            if indicator in image_text:
                return 'internet'

        for source in self.ALLOWED_SOURCES:
            if source in image_text:
                return 'local'

        return 'unknown'

    def validate_all(self) -> List[Dict[str, Any]]:
        """执行所有图片质量验证"""
        issues = []
        issues.extend(self.validate_image_quality())
        issues.extend(self.validate_image_relevance())
        issues.extend(self.validate_image_count())
        return issues

    def validate_image_quality(self) -> List[Dict[str, Any]]:
        """验证图片质量"""
        issues = []

        for img in self.images:
            # 检查来源合规性
            if img['source'] == 'internet':
                # 检查是否有版权标注
                caption = img.get('caption', '')
                if not any(keyword in caption for keyword in ['来源', '出处', '引用自', '©']):
                    issues.append({
                        'type': 'image_quality',
                        'severity': 'high',
                        'message': f'图片 {img.get("number", "未知")} 来自互联网但未标注版权来源',
                        'location': f'图片 {img.get("number", "未知")}',
                        'suggestion': '在图片说明中添加来源标注，或使用知识库图片'
                    })

            elif img['source'] == 'unknown':
                issues.append({
                    'type': 'image_quality',
                    'severity': 'medium',
                    'message': f'图片 {img.get("number", "未知")} 来源不明',
                    'location': f'图片 {img.get("number", "未知")}',
                    'suggestion': '明确图片来源（Local-KnowledgeBase 或 AI 生成）'
                })

            # 检查图片说明
            if not img.get('caption') or len(img.get('caption', '')) < 3:
                issues.append({
                    'type': 'image_quality',
                    'severity': 'medium',
                    'message': f'图片 {img.get("number", "未知")} 缺少说明或说明过短',
                    'location': f'图片 {img.get("number", "未知")}',
                    'suggestion': '添加清晰的图片说明，描述图片内容和作用'
                })

        return issues

    def validate_image_relevance(self) -> List[Dict[str, Any]]:
        """验证图片与内容相关性"""
        issues = []

        for img in self.images:
            caption = img.get('caption', '')
            if not caption:
                continue

            # 提取图片周围的文本（简化实现：查找图片说明前后的文本）
            pattern = rf'图\s*{re.escape(img.get("number", ""))}'
            match = re.search(pattern, self.chapter_content)

            if match:
                # 提取前后各200字
                start = max(0, match.start() - 200)
                end = min(len(self.chapter_content), match.end() + 200)
                context = self.chapter_content[start:end]

                # 提取图片说明中的关键词
                caption_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', caption)

                # 检查关键词是否在上下文中出现
                missing_keywords = []
                for keyword in caption_keywords[:3]:  # 检查前3个关键词
                    if keyword not in context:
                        missing_keywords.append(keyword)

                if len(missing_keywords) >= 2:  # 超过一半关键词不匹配
                    issues.append({
                        'type': 'image_relevance',
                        'severity': 'medium',
                        'message': f'图片 {img.get("number", "未知")} 与周围内容相关性较低',
                        'location': f'图片 {img.get("number", "未知")}',
                        'suggestion': f'确保图片内容与文本描述一致，或调整图片位置'
                    })

        return issues

    def validate_image_count(self) -> List[Dict[str, Any]]:
        """验证图片数量"""
        issues = []

        image_count = len(self.images)
        word_count = len(self.chapter_content)

        # 核心章节（≥4500字）应有 2-3 张图片
        if word_count >= 4500:
            if image_count < 2:
                issues.append({
                    'type': 'image_count',
                    'severity': 'high',
                    'message': f'核心章节（{word_count}字）图片数量不足（{image_count}张），建议 2-3 张',
                    'location': '整个章节',
                    'suggestion': '添加架构图、流程图或示意图，增强可读性'
                })
            elif image_count > 5:
                issues.append({
                    'type': 'image_count',
                    'severity': 'low',
                    'message': f'图片数量过多（{image_count}张），可能影响阅读体验',
                    'location': '整个章节',
                    'suggestion': '精简图片，保留最关键的 2-3 张'
                })

        # 短章节（<2000字）图片不宜过多
        elif word_count < 2000 and image_count > 2:
            issues.append({
                'type': 'image_count',
                'severity': 'low',
                'message': f'短章节（{word_count}字）图片数量过多（{image_count}张）',
                'location': '整个章节',
                'suggestion': '短章节建议 0-1 张图片'
            })

        return issues

    def generate_report(self, output_file: Path, issues: List[Dict[str, Any]]):
        """生成图片质量验证报告"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 按严重程度分类
        critical = [i for i in issues if i['severity'] == 'critical']
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']

        # 统计图片来源
        source_stats = {}
        for img in self.images:
            source = img['source']
            source_stats[source] = source_stats.get(source, 0) + 1

        report = f"""# 图片质量验证报告

生成时间：{timestamp}
章节文件：{self.chapter_file.name}

## 验证摘要

- 图片总数：{len(self.images)}
- 总问题数：{len(issues)}
  - 严重问题：{len(critical)}
  - 高风险问题：{len(high)}
  - 中等问题：{len(medium)}
  - 低风险问题：{len(low)}

## 图片来源统计

"""

        for source, count in source_stats.items():
            source_name = {
                'local': '知识库/本地',
                'internet': '互联网',
                'unknown': '未知'
            }.get(source, source)
            report += f"- {source_name}：{count} 张\n"

        report += "\n## 质量指标\n\n"

        # 计算质量指标
        word_count = len(self.chapter_content)
        image_count = len(self.images)
        expected_count = 2 if word_count >= 4500 else 1

        report += f"- 字数：{word_count}\n"
        report += f"- 图片数量：{image_count} / {expected_count}（建议）\n"
        report += f"- 图片质量合格率：{max(0, len(self.images) - len([i for i in issues if i['type'] == 'image_quality'])) / max(len(self.images), 1) * 100:.1f}%\n"
        report += f"- 图片相关性：{'✅ 通过' if not any(i['type'] == 'image_relevance' for i in issues) else '❌ 未通过'}\n"

        report += "\n## 问题详情\n\n"

        # 按类型分组
        for issue_type in ['image_quality', 'image_relevance', 'image_count']:
            type_issues = [i for i in issues if i['type'] == issue_type]
            if type_issues:
                type_name = {
                    'image_quality': '图片质量',
                    'image_relevance': '图片相关性',
                    'image_count': '图片数量'
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
