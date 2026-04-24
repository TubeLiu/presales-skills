#!/usr/bin/env python3
"""验证器模块单元测试"""
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'tests' / 'e2e'))

from validators.docx_parser import DOCXParser
from validators.taa_validator import TAAValidator
from validators.taw_validator import TAWValidator
from validators.quality_checker import QualityChecker


def test_docx_parser():
    """测试 DOCX 解析器"""
    print("测试 DOCX 解析器...")

    # 测试字数统计
    text = "这是一个测试文本，包含中文和 English words。"
    word_count = DOCXParser.count_words(text)
    print(f"  字数统计: {word_count} 字")
    assert word_count > 0, "字数统计失败"

    print("  ✅ DOCX 解析器测试通过")


def test_taa_validator():
    """测试 taa 验证器"""
    print("\n测试 taa 验证器...")

    # 创建测试分析报告
    test_analysis = """# 招标分析报告

## M1 项目概况
项目名称：测试项目
预算金额：100万元（出处：第1章 P.1）

## M2 技术要求矩阵
【必须】支持 Kubernetes 1.20+

## M3 评分标准
技术方案：30分

## M4 评分标准详解
### 技术方案
- 架构设计：10分

## M5 废标条款
[废标] 未按时提交投标文件

## M6 投标策略
重点关注技术方案

## M7 投标策略详解
### 关键词清单
- Kubernetes
- 容器
"""

    # 写入临时文件
    temp_file = PROJECT_ROOT / 'tests' / 'e2e' / 'reports' / 'test_analysis.md'
    temp_file.write_text(test_analysis, encoding='utf-8')

    # 创建验证器
    validator = TAAValidator(temp_file)

    # 验证模块解析
    assert 'M1' in validator.modules, "M1 模块未解析"
    assert 'M2' in validator.modules, "M2 模块未解析"
    print(f"  解析模块数: {len(validator.modules)}")

    # 执行验证
    issues = validator.validate_all()
    print(f"  发现问题: {len(issues)} 个")

    # 清理临时文件
    temp_file.unlink()

    print("  ✅ taa 验证器测试通过")


def test_taw_validator():
    """测试 taw 验证器"""
    print("\n测试 taw 验证器...")

    # 创建测试分析报告
    test_analysis = """# 招标分析报告

## M2 技术要求矩阵
【必须】支持 Kubernetes 1.20+

## M4 评分标准详解
### 技术方案
- 架构设计：10分

## M5 废标条款
[废标] 未按时提交投标文件

## M7 投标策略详解
### 关键词清单
- Kubernetes
- 容器

### 红线清单
- 不得使用盗版软件
"""

    # 写入临时文件
    temp_file = PROJECT_ROOT / 'tests' / 'e2e' / 'reports' / 'test_analysis.md'
    temp_file.write_text(test_analysis, encoding='utf-8')

    # 创建验证器
    validator = TAWValidator(temp_file)

    # 验证数据提取
    print(f"  M2 要求数: {len(validator.m2_requirements)}")
    print(f"  M4 评分项: {len(validator.m4_scoring)}")
    print(f"  M7 关键词: {len(validator.m7_keywords)}")
    print(f"  M7 红线: {len(validator.m7_redlines)}")

    # 清理临时文件
    temp_file.unlink()

    print("  ✅ taw 验证器测试通过")


def test_quality_checker():
    """测试质量检查器"""
    print("\n测试质量检查器...")

    # 创建测试上下文
    test_context = {
        'tender_file': Path('/home/ubuntu/testfile2.docx'),
        'timestamp': '20260308_120000',
        'execution_time': '120.5 秒',
        'taa_outputs': {},
        'taw_outputs': {},
        'taa_issues': [
            {
                'type': 'completeness',
                'severity': 'critical',
                'module': 'M1',
                'description': '测试问题',
                'location': '测试位置',
                'suggestion': '测试建议',
            }
        ],
        'outline_issues': [],
        'taw_issues': [],
        'taa_metrics': {
            'taa_module_completeness': 1.0,
            'taa_citation_rate': 0.85,
            'taa_speculation_count': 0,
        },
        'outline_metrics': {
            'outline_chapter_count': 25,
            'outline_requirement_coverage': 0.95,
            'outline_numbering_compliance': '通过',
        },
        'taw_metrics': {
            'taw_avg_word_count': 4500,
            'taw_avg_image_count': 2.5,
            'taw_avg_citation_count': 10,
            'taw_scoring_coverage': 0.9,
            'taw_keyword_coverage': 0.85,
        },
        'trv_reports': [],
        'errors': [],
    }

    # 创建质量检查器
    checker = QualityChecker(test_context)

    # 生成报告
    report_file = PROJECT_ROOT / 'tests' / 'e2e' / 'reports' / 'test_final_report.md'
    checker.generate_final_report(report_file)

    # 验证报告生成
    assert report_file.exists(), "报告文件未生成"
    report_content = report_file.read_text(encoding='utf-8')
    assert '端到端测试报告' in report_content, "报告标题缺失"
    assert '质量指标' in report_content, "质量指标缺失"

    print(f"  报告文件: {report_file}")
    print(f"  报告大小: {len(report_content)} 字符")

    # 清理临时文件
    report_file.unlink()

    print("  ✅ 质量检查器测试通过")


if __name__ == '__main__':
    print("=" * 60)
    print("验证器模块单元测试")
    print("=" * 60)

    try:
        test_docx_parser()
        test_taa_validator()
        test_taw_validator()
        test_quality_checker()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
