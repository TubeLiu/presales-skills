# Phase 2 + Phase 3.1 输出模板详解

> **何时读本文件**：Phase 1 各维度审核完成、要进入 Phase 2 汇总和 Phase 3 报告生成时。
>
> 包含 Phase 2.1（结论）/ 2.2（问题清单）/ 2.3（修改优先级）三个固定模板，以及 Phase 3.1 的完整 Markdown 报告模板和 §3.2 文件保存逻辑。
>
> §3.5 DOCX 智能修订单独见 `references/docx-revision-ai-driven.md`。

## 目录

- §2.1 生成审核结论
- §2.2 生成问题清单
- §2.3 生成修改优先级
- §3.1 完整报告 Markdown 模板
- §3.2 保存报告文件

---

## 2.1 生成审核结论

> **分块模式说明**：当 REVIEW_MODE == "chunked" 或 "chunked_chapter" 时，
> Phase 2 的输入来自 Phase D（1.0.5）的合并结果，包含：
>
> - 各 chunk 的章节级审核发现（已按维度合并）
> - 跨 chunk 一致性检查发现（作为独立维度）
>
> 输入格式与内联模式一致，Phase 2 逻辑无需区分模式。

根据各维度结果判断总体评价：

**步骤**：

1. **统计问题总数**：
   - 完整性检查：缺失项总数
   - 合规性审查：不合规项总数
   - 评分契合度分析：未覆盖/覆盖不足的评分项总数
   - 风险识别：风险总数
   - 跨章节一致性（仅分块模式）：矛盾项总数

2. **统计严重程度分布**：
   - 严重问题（critical/严重风险）
   - 一般问题（major/一般风险）
   - 建议优化（minor/轻微风险）

3. **评估总体风险等级**：
   - 高风险：存在严重问题或严重风险
   - 中风险：存在一般问题但无严重问题
   - 低风险：仅存在建议优化项

4. **判断总体评价**：
   - **通过**：无严重问题，一般问题 ≤ 3 项
   - **有条件通过**：无严重问题，一般问题 > 3 项
   - **不通过**：存在严重问题

**输出格式**：

```markdown
## 审核结论

- **总体评价**: 通过/有条件通过/不通过
- **问题总数**: <total_issues>项
- **严重程度分布**:
  - 严重问题: <critical_count>项
  - 一般问题: <major_count>项
  - 建议优化: <minor_count>项
- **总体风险等级**: 高/中/低
```

## 2.2 生成问题清单

汇总所有维度发现的问题：

**步骤**：

1. **按严重程度分类**：
   - 严重问题（critical）
   - 一般问题（major）
   - 建议优化（minor）

2. **每个问题包含**：
   - 问题描述
   - 来源维度
   - 修改建议

**输出格式**：

```markdown
## 问题清单

### 严重问题

1. **[完整性]** <issue_description>
   - **修改建议**: <suggestion>

2. **[合规性]** <issue_description>
   - **修改建议**: <suggestion>

### 一般问题

1. **[评分契合度]** <issue_description>
   - **修改建议**: <suggestion>

### 建议优化

1. **[风险识别]** <issue_description>
   - **优化建议**: <suggestion>
```

## 2.3 生成修改优先级

根据问题严重程度和影响，生成修改优先级：

**输出格式**：

```markdown
## 修改优先级

### 必须修改（阻塞性问题）

- [ ] <issue_description> - <suggestion>
- [ ] ...

### 建议修改（重要问题）

- [ ] <issue_description> - <suggestion>
- [ ] ...

### 可选优化

- [ ] <issue_description> - <suggestion>
- [ ] ...
```

---

## 3.1 完整报告 Markdown 模板

整合 Phase 1 和 Phase 2 的所有结果，生成结构化 Markdown 报告：

```markdown
# 审核报告 - <审核类型>

## 基本信息

- **审核文件**: <file_name>
- **参考文件**: <reference_name> (如提供)
- **审核时间**: <timestamp>
- **审核类型**: <type_name>
- **审核级别**: <level>
- **专注维度**: <focus> (如提供)

## 审核结论

[Phase 2.1 的输出]

## 详细审核结果

[Phase 1.1-1.4 的输出]

## 问题清单

[Phase 2.2 的输出]

## 修改优先级

[Phase 2.3 的输出]

## 附录

### 审核检查清单

- 完整性检查清单: $SKILL_DIR/prompts/completeness.yaml
- 合规性审查要点: $SKILL_DIR/prompts/compliance.yaml
- 评分契合度分析: $SKILL_DIR/prompts/scoring_alignment.yaml
- 风险识别清单: $SKILL_DIR/prompts/risk_check.yaml

### 法规引用清单

[从 Phase 1.2 中提取的法规引用]

---

**报告生成时间**: <timestamp>
**审核工具**: TRV (Tender Reviewer) v1.5.0
```

## 3.2 保存报告文件

将报告保存到文件系统：

**步骤**：

1. **生成文件名**：

   ```
   审核报告_<type>_<timestamp>.md
   ```

   - `<type>`: 审核类型（tender_doc/analysis/outline/chapter/full_bid）
   - `<timestamp>`: 时间戳（格式：YYYYMMDD_HHMMSS）

2. **保存文件**：
   - 使用 Bash 工具保存文件到 OUTPUT_DIR
   - 命令：

     ```bash
     cat > "${OUTPUT_DIR}/审核报告_<type>_<timestamp>.md" << 'EOF'
     <report_content>
     EOF
     ```

3. **验证文件**：
   - 检查文件是否成功创建
   - 检查文件大小是否合理
   - 如果失败，输出错误并退出
