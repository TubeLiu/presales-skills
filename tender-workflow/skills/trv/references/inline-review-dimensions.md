# 内联审核模式 4 维度详解（§1.1-1.4）

> **何时读本文件**：`REVIEW_MODE == "inline"`（小文件、无需分块）时。分块模式（chunked / chunked_chapter）跳过本文件，按 `references/chunked-review-mode.md` 执行。
>
> 4 维度按 `--focus` 参数选择性执行：未指定 = 全部 4 维度都跑；指定 `completeness` / `compliance` / `scoring` / `risk` = 仅跑对应维度。

## 目录

- §1.1 完整性检查（Completeness）
- §1.2 合规性审查（Compliance）
- §1.3 评分契合度分析（Scoring Alignment）
- §1.4 风险识别（Risk Check）

---

## 1.1 完整性检查（Completeness）

**执行条件**：--focus 未指定或 --focus=completeness

**步骤**：

1. **加载检查清单**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/completeness.yaml`
   - 根据 --type 参数选择对应的检查清单

2. **执行完整性检查**：
   - 逐项检查待审核文件是否包含必备要素
   - 评估缺失项的严重程度（critical/major/minor）
   - 根据 --level 参数过滤结果：
     - critical: 仅显示 critical 级别的缺失项
     - high: 显示 critical 和 major 级别的缺失项
     - all: 显示所有级别的缺失项

3. **生成检查结果**：
   - 使用 Markdown 表格格式
   - 包含：检查项、状态（✅/❌）、严重程度、说明

**输出格式**：

```markdown
### 1.1 完整性检查

| 检查项 | 状态 | 严重程度 | 说明 |
|--------|------|----------|------|
| <item_name> | ✅/❌ | critical/major/minor | <description> |

**缺失项总数**: <count>
**严重缺失**: <critical_count>
**一般缺失**: <major_count>
**建议补充**: <minor_count>
```

## 1.2 合规性审查（Compliance）

**执行条件**：--focus 未指定或 --focus=compliance

**步骤**：

1. **加载审查要点**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/compliance.yaml`
   - 根据 --type 参数选择对应的审查要点

2. **执行合规性审查**：
   - 检查文档是否符合相关法律法规
   - 识别不合规项和潜在风险
   - 引用相关法规条款
   - 评估风险等级（high/medium/low）
   - 根据 --level 参数过滤结果

3. **生成审查结果**：
   - 使用 Markdown 表格格式
   - 包含：审查项、合规状态、风险等级、法规引用、修改建议

**输出格式**：

```markdown
### 1.2 合规性审查

| 审查项 | 合规状态 | 风险等级 | 法规引用 | 修改建议 |
|--------|----------|----------|----------|----------|
| <item_name> | 合规/不合规/待确认 | high/medium/low | <regulation> | <suggestion> |

**不合规项总数**: <count>
**高风险项**: <high_count>
**中风险项**: <medium_count>
**低风险项**: <low_count>
```

## 1.3 评分契合度分析（Scoring Alignment）

**执行条件**：--focus 未指定或 --focus=scoring

**步骤**：

1. **加载分析模板**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/scoring_alignment.yaml`
   - 根据 --type 参数选择对应的分析模板

2. **提取评分标准**：
   - 如果提供了 --reference 参数，从参考文件中提取评分标准
   - 如果未提供 --reference 参数，从待审核文件中提取评分标准
   - 识别评分项、分值、评分细则

3. **执行契合度分析**：
   - 将待审核文件内容与评分项进行映射
   - 评估每个评分点的覆盖程度（完全覆盖/部分覆盖/未覆盖）
   - 评估内容质量与评分标准的匹配度（高/中/低）
   - 计算总体覆盖度

4. **生成分析结果**：
   - 使用 Markdown 表格格式
   - 包含：评分项、分值、覆盖程度、匹配度、对应内容位置、优化建议

**输出格式**：

```markdown
### 1.3 评分契合度分析

#### 评分项映射矩阵

| 评分项 | 分值 | 覆盖程度 | 匹配度 | 对应内容位置 | 优化建议 |
|--------|------|----------|--------|--------------|----------|
| <scoring_item> | <points> | 完全/部分/未覆盖 | 高/中/低 | <location> | <suggestion> |

#### 覆盖度统计

- **总评分项**: <total_items>
- **完全覆盖**: <full_coverage_count> (<percentage>%)
- **部分覆盖**: <partial_coverage_count> (<percentage>%)
- **未覆盖**: <no_coverage_count> (<percentage>%)
- **总体覆盖度**: <overall_coverage>%

#### 缺口分析

**未覆盖的评分项**：
1. <item_name> (<points>分) - <suggestion>
2. ...

**覆盖不足的评分项**：
1. <item_name> (<points>分) - <suggestion>
2. ...
```

## 1.4 风险识别（Risk Check）

**执行条件**：--focus 未指定或 --focus=risk

**步骤**：

1. **加载风险清单**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/risk_check.yaml`
   - 根据 --type 参数选择对应的风险检查重点

2. **执行风险识别**：
   - 按 4 大风险分类识别风险点：
     - 废标风险（disqualification）
     - 合规风险（compliance）
     - 履约风险（performance）
     - 争议风险（dispute）
   - 评估风险等级（严重/一般/轻微）
   - 评估发生概率（高/中/低）
   - 根据 --level 参数过滤结果

3. **生成风险报告**：
   - 使用 Markdown 表格格式
   - 包含：风险分类、风险描述、风险等级、发生概率、影响、应对措施

**输出格式**：

```markdown
### 1.4 风险识别

#### 风险登记册

| 风险分类 | 风险描述 | 风险等级 | 发生概率 | 影响 | 应对措施 |
|----------|----------|----------|----------|------|----------|
| <category> | <description> | 严重/一般/轻微 | 高/中/低 | <impact> | <mitigation> |

#### 风险统计

- **风险总数**: <total_risks>
- **严重风险**: <critical_risks>
- **一般风险**: <major_risks>
- **轻微风险**: <minor_risks>

#### 应对行动计划

**优先级 1（严重风险）**：
1. <risk_description> - <action>
2. ...

**优先级 2（一般风险）**：
1. <risk_description> - <action>
2. ...

**优先级 3（轻微风险）**：
1. <risk_description> - <action>
2. ...
```
