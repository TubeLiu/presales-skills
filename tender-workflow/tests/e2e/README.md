# 端到端测试使用指南

**中文** | [English](./README_EN.md)

## 概述

本测试框架用于验证 tender-workflow 系统从 taa（招标分析）到 taw（章节撰写）的完整流程质量。

## 测试架构

### 测试流程（10 步骤）

```
Step 0: 环境准备
Step 1: taa 输出文件定位
Step 2: 分析报告质量验证（增强版）
Step 3: 投标大纲质量验证
Step 4: taw 章节生成
Step 5: 章节内容质量验证（增强版）
Step 6: 章节间一致性验证（新增）
Step 7: 大纲匹配度验证（新增）
Step 8: trv 审核集成（可选）
Step 9: 综合质量评分（新增）
Step 10: 生成最终测试报告
```

### 验证器体系

- TAAValidator: 验证 taa 分析报告和大纲质量
- TAWValidator: 验证 taw 章节内容质量
- ConsistencyValidator: 验证一致性（新增）
- ImageQualityValidator: 验证图片质量（新增）
- ContentProfessionalismValidator: 验证内容专业性（新增）
- QualityChecker: 质量检查引擎

## 使用方法

### 前置条件

1. 安装依赖：
```bash
pip install pytest python-docx
```

2. 生成 taa 输出（必须）：
```bash
/taa /home/ubuntu/testfile2.docx --vendor "灵雀云"
```

### 运行测试

```bash
# 完整端到端测试
pytest tests/e2e/test_e2e_workflow.py -v -s

# 参数测试
pytest tests/e2e/test_parameters.py -v -s
```

### 查看测试报告

```bash
cat tests/e2e/reports/e2e_test_report_*.md
```

## 质量指标

- 分析报告质量: ≥85%
- 投标大纲质量: ≥90%
- 章节内容质量: ≥80%
- 一致性质量: ≥90%

详见测试报告中的质量指标仪表盘。
