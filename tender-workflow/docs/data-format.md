# 招投标工作流数据格式规范

本文档定义四角色工作流中各阶段产出物的数据格式标准，确保角色间的数据可互通、可验证。

---

## 1. 招标分析报告格式 (taa输出)

### 文件信息
- **文件名**: `招标分析报告_YYYYMMDD_HHMMSS.md`
- **格式**: Markdown
- **编码**: UTF-8

### 数据结构

```yaml
report:
  meta:
    tender_name: "项目名称"
    tender_code: "招标编号"
    tenderer: "招标人名称"
    agency: "代理机构（如有）"
    budget: "预算金额/最高限价"
    procurement_method: "公开招标/邀请招标/竞争性磋商等"
    industry_type: "政府IT/建设工程/货物/服务"
    analysis_date: "分析日期"
    version: "报告版本"

  # M1 基础信息分析
  M1_basic_info:
    project_overview: "项目概况描述"
    tender_scope: "招标范围"
    package_info: "分包情况（如有）"
    key_dates:
      publish_date: "公告发布日期"
      doc_sale_start: "招标文件发售开始"
      doc_sale_end: "招标文件发售截止"
      bid_deadline: "投标截止时间"
      bid_opening: "开标时间"
      evaluation_period: "评标周期预估"

  # M2 技术要求分析
  M2_technical_requirements:
    summary: "技术要求概要"
    functional_requirements:
      - category: "功能分类1"
        items: ["功能点1", "功能点2"]
        priority: "核心/重要/一般"
    performance_requirements:
      - metric: "性能指标名称"
        value: "指标值"
        test_method: "测试方法"
    integration_requirements: "集成接口要求"
    security_requirements: "安全要求（等保级别等）"
    compliance_standards: ["符合的标准1", "标准2"]
    key_technical_challenges: "技术难点识别"

  # M3 商务要求分析
  M3_business_requirements:
    qualification_requirements:
      - type: "企业资质"
        requirement: "具体要求"
        level: "硬性/加分"
      - type: "业绩要求"
        requirement: "近X年X个类似项目"
        amount: "合同金额要求"
      - type: "人员要求"
        requirement: "项目经理资格"
      - type: "财务要求"
        requirement: "注册资本/营业收入"
    delivery_requirements:
      duration: "工期/交付期"
      location: "交付地点"
      milestones: ["里程碑1", "里程碑2"]
    warranty_requirements:
      period: "质保期"
      scope: "质保范围"

  # M4 评分标准分析
  M4_scoring_criteria:
    evaluation_method: "综合评分法/最低价法"
    weight_distribution:
      price: "价格权重%"
      business: "商务权重%"
      technical: "技术权重%"
    scoring_items:
      - item: "评分项名称"
        category: "price/business/technical"
        weight: "分值"
        criteria: "评分标准"
        scoring_method: "客观/主观"
        objective: true/false
    key_scoring_points: ["关键得分点1", "关键得分点2"]

  # M5 废标条款分析
  M5_disqualification_clauses:
    major_deviations:
      - clause: "废标条款内容"
        risk_level: "高/中/低"
        prevention: "预防措施建议"
    minor_deviations:
      - clause: "细微偏差内容"
        handling: "处理方式"

  # M6 关键时间节点
  M6_key_dates:
    calendar:
      - date: "YYYY-MM-DD"
        event: "事件描述"
        days_remaining: "距今天数"
    critical_path: ["关键路径节点"]
    risk_alerts: ["时间风险提示"]

  # M7 投标策略建议
  M7_bidding_strategy:
    competitive_analysis:
      expected_competitors: "预期竞争对手"
      price_strategy: "报价策略建议"
    technical_strategy: "技术方案策略"
    business_strategy: "商务响应策略"
    risk_mitigation: "风险应对建议"
    priority_actions: ["优先行动项"]
```

---

## 1.1 产品能力索引格式 (taa内部使用)

当使用 `--product` 参数提供产品能力说明书（Excel格式）时，taa 会生成结构化索引用于技术匹配。

### 数据结构

```yaml
product_index:
  meta:
    source_file: "产品能力说明书.xlsx"
    generated_at: "2026-03-07T10:00:00"
    total_entries: 150

  sheets:
    - name: "技术能力清单"
      headers: ["功能分类", "功能名称", "功能描述", "技术参数"]
      entries:
        - id: "技术能力清单_1"
          category: "平台管理"
          name: "多集群管理"
          description: "支持同时管理多个Kubernetes集群..."
          parameters: "最大支持100个集群"
          keywords: ["多集群", "集群管理", "K8s", "Kubernetes"]
        - id: "技术能力清单_2"
          category: "平台管理"
          name: "命名空间隔离"
          description: "支持多租户命名空间隔离..."
          parameters: "支持网络策略隔离"
          keywords: ["命名空间", "隔离", "多租户"]

    - name: "国产化适配"
      headers: ["适配类型", "厂商/产品", "适配版本", "认证状态"]
      entries:
        - id: "国产化适配_1"
          category: "芯片适配"
          name: "华为鲲鹏"
          description: "ARM架构处理器适配"
          parameters: "鲲鹏920"
          keywords: ["鲲鹏", "ARM", "华为"]
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识符，格式：`{sheet名}_{行号}` |
| `category` | string | 功能分类，自动识别或继承上一行分类 |
| `name` | string | 功能名称/产品名称 |
| `description` | string | 功能描述 |
| `parameters` | string | 技术参数/规格 |
| `keywords` | array | 自动提取的关键词，用于匹配搜索 |

### 关键词提取规则

从 `name`、`description`、`parameters` 字段中提取：
- 中文词汇：长度 > 2 的连续汉字
- 英文词汇：长度 > 2 的连续字母
- 每条目最多 10 个关键词

### 使用场景

1. **M2 技术要求匹配**：根据招标技术要求关键词，检索 PRODUCT_INDEX 中匹配的 entry
2. **匹配依据追溯**：M2 表格中"匹配依据"列填写匹配条目的 `entry.id`
3. **多轮验证**：Phase 1.5 对 `⚠️` 标记条目进行扩展检索

---

## 2. 技术规格与评标办法格式 (tpl v2.0 输出)

### 文件信息
- **文件名**: `技术规格与评标办法_<project>_<timestamp>.docx`
- **格式**: DOCX
- **结构**: 技术规格（9章）+ 评标办法（可选，`--no-scoring` 跳过）

### 文档结构

```
技术规格与评标办法.docx
├── 第一部分 技术规格与要求
│   ├── 1. 项目概述
│   ├── 2. 总体技术要求
│   ├── 3. 功能要求
│   ├── 4. 性能要求
│   ├── 5. 安全要求
│   ├── 6. 兼容性与集成要求
│   ├── 7. 实施与交付要求
│   ├── 8. 培训与技术支持要求
│   └── 9. 其他技术要求
└── 第二部分 评标办法（可选）
    ├── 评分总则（价格/技术/商务权重）
    └── 评分细则表
```

> **注意**: tpl v2.0 仅输出技术规格与评标办法，不再生成完整 M1-M6 招标文件。

---

## 3. 投标大纲格式 (taa输出)

### 文件信息
- **文件名**: `投标文件大纲_YYYYMMDD_HHMMSS.docx`
- **格式**: DOCX

### 标准章节结构

```
投标文件大纲.docx
├── 封面
├── 目录
一、技术部分
  ├── 1.1 技术偏离表
  ├── 1.2 项目理解与需求分析
  ├── 1.3 总体方案设计
  ├── 1.4 [针对招标文件技术要求的专项响应章节]（动态生成）
  ├── 1.5 实施方案与计划
  ├── 1.6 质量保障方案
  ├── 1.7 安全方案
  ├── 1.8 国产化适配方案（如有信创要求）
  ├── 1.9 项目团队与人员配置
  ├── 1.10 售后服务方案
  │   ├── 1.10.1 质保服务方案
  │   ├── 1.10.2 运维服务方案
  │   ├── 1.10.3 服务响应承诺
  │   └── 1.10.4 增值服务方案
  └── 1.11 培训方案
```

---

## 4. 审核报告格式 (trv输出)

### 文件信息
- **文件名**: `审核报告_<type>_<timestamp>.md`
- **格式**: Markdown
- **编码**: UTF-8

启用 `--revise-docx` 时，额外输出：
- **文件名**: `<原文件名>_修订版_<timestamp>.docx`
- **格式**: DOCX
- **生成条件**: 输入为 `.docx`，且审核类型为 `outline` / `chapter` / `full_bid`
- **降级行为**: 输入不是 `.docx` 或审核类型不支持修订时，跳过修订但不报错，审核流程正常完成
- **驱动方式**: AI 驱动 — Claude 在审核时生成修订指令 JSON，Python 工具执行通用 DOCX 操作

### 数据结构

```yaml
review_report:
  meta:
    review_type: "tender_doc/analysis/outline/chapter/full_bid"
    target_file: "被审核文件名"
    reference_file: "参考文件名（如有）"
    review_date: "审核日期"
    reviewer: "审核者"

  summary:
    overall_conclusion: "通过/有条件通过/不通过"
    total_issues: "问题总数"
    critical_issues: "严重问题数"
    high_issues: "高风险问题数"
    risk_level: "高/中/低"
    recommendation: "总体建议"
    # v1.4.0 分块审核模式下新增以下字段
    review_mode: "inline/chunked/chunked_chapter"  # 审核模式
    chunk_count: "chunk 数量（仅分块模式）"
    chunk_success: "成功完成的 chunk 数（仅分块模式）"
    consistency_check: "已执行/跳过（仅分块模式）"

  completeness_check:
    check_items:
      - item: "检查项名称"
        required: true/false
        status: "通过/未通过/不适用"
        severity: "严重/一般/轻微"
        finding: "发现的问题"
        suggestion: "改进建议"
    completion_rate: "完成度%"

  compliance_check:
    regulations_checked:
      - "招标投标法"
      - "政府采购法"
    violations:
      - regulation: "法规名称"
        article: "条款"
        finding: "违规描述"
        severity: "严重/一般"
        recommendation: "修改建议"

  scoring_alignment:
    coverage_analysis:
      overall_coverage: "总体覆盖度%"
      by_category:
        business: "商务分覆盖%"
        technical: "技术分覆盖%"
    gaps:
      - scoring_item: "评分项"
        weight: "分值"
        current_status: "当前状态"
        gap_description: "缺口描述"
        recommendation: "补充建议"

  risk_assessment:
    risks:
      - risk_id: "R001"
        category: "废标风险/合规风险/履约风险/商务风险/争议风险"
        description: "风险描述"
        probability: "高/中/低"
        impact: "严重/重大/中等/轻微"
        risk_level: "严重/高/中/低"
        mitigation: "缓解措施"

  issue_tracker:
    critical:
      - id: "C001"
        description: "问题描述"
        location: "所在位置"
        impact: "影响"
        fix_required: true
        deadline: "修复期限"
    major:
      - id: "M001"
        description: "问题描述"
        recommendation: "建议"
    minor:
      - id: "N001"
        description: "问题描述"
        suggestion: "优化建议"

  # v1.4.0 分块模式新增：跨章节一致性检查
  cross_chunk_consistency:  # 仅分块模式
    data_contradictions:
      - item: "数据项名称"
        chunk_a: "Chunk A 编号"
        value_a: "Chunk A 中的数值"
        chunk_b: "Chunk B 编号"
        value_b: "Chunk B 中的数值"
        severity: "critical/major/minor"
        suggestion: "修改建议"
    description_inconsistencies:
      - item: "描述项"
        locations: ["位置1", "位置2"]
        details: "不一致描述"
    commitment_conflicts:
      - item: "承诺项"
        locations: ["位置1", "位置2"]
        details: "不自洽描述"

  action_plan:
    must_fix:
      - "必须修改项1"
    should_fix:
      - "建议修改项1"
    nice_to_have:
      - "可选优化项1"

  appendices:
    checklist_used: "使用的检查清单"
    regulations_referenced: ["引用的法规"]
```

### 修订指令格式 (trv Phase 3.5 中间产物)

Claude 在审核时生成、`skills/twc/tools/trv_docx_reviser.py` 消费的修订指令 JSON：

```json
{
  "meta": {
    "source_report": "output/trv/审核报告_full_bid_xxx.md",
    "scope": "must|all",
    "instruction_count": 5
  },
  "instructions": [
    {
      "id": "R001",
      "severity": "critical|high|major|minor",
      "type": "paragraph_text_replace|paragraph_full_replace|table_cell_replace|global_text_replace|paragraph_insert_after|paragraph_delete",
      "description": "人可读的修订说明",
      "match": {
        "method": "contains|exact|regex|table_header_row|global",
        "text": "匹配文本（段落类指令）",
        "context_before": "上下文校验（可选）",
        "header_contains": ["表头列名"],
        "row_match": {"column": "列名", "value": "值"},
        "target_column": "目标列名"
      },
      "action": {
        "find": "原文本",
        "replace": "新文本",
        "new_text": "整段替换文本（paragraph_full_replace）",
        "insert_text": "插入文本（paragraph_insert_after）"
      }
    }
  ]
}
```

| 指令类型 | 说明 | 格式保留 |
|---------|------|---------|
| `paragraph_text_replace` | 段落内查找替换 | 保留 run 格式 |
| `paragraph_full_replace` | 整段文本替换 | 降级到首 run 格式 |
| `table_cell_replace` | 按表头+行标识定位单元格替换 | 尽量保留 |
| `global_text_replace` | 全文查找替换（段落+表格） | 保留 run 格式（find 为 replace 子串时降级为首 run 格式） |
| `paragraph_insert_after` | 在匹配段落后插入 | 继承锚点段落格式 |
| `paragraph_delete` | 删除匹配段落 | - |

---

## 5. 章节草稿格式 (taw输出)

### 文件信息
- **文件名**: `<章节号>_<章节名>.docx`
- **格式**: DOCX（python-docx 生成）

### 图片来源（v3.0 变更）

taw v3.0 使用 **KB 图文共生**模式获取图片：图片随 Local-KnowledgeBase 中的 Markdown 段落按需加载，不再依赖独立的 `images.yaml` 评分匹配或 `h3_allocation_rules` 静态配额。DOCX 输出格式不变。

### 标准结构

```markdown
# <章节号> <章节名>

## 章节概述
- 对应评分项：[评分项名称]
- 分值权重：[X分]
- 数据来源：[知识库来源]

## 正文内容
...

## 引用案例
- 案例1：[案例ID] [案例名称]
- 案例2：[案例ID] [案例名称]

## 评分契合说明
- 覆盖的评分点：[列表]
- 竞争优势：[描述]

## 待确认事项
- [ ] 事项1
- [ ] 事项2
```

---

## 6. 数据映射关系

### taa M1-M7 与招标文件 M1-M6 映射

| taa分析模块 | 对应招标文件章节 | 说明 |
|------------|-----------------|------|
| M1 基础信息 | M1 招标公告 | 项目基本信息提取 |
| M2 技术要求 | M5 技术规格 | 技术需求详细分析 |
| M3 商务要求 | M2 投标人须知 | 资格要求分析 |
| M4 评分标准 | M3 评标办法 | 评分细则解析 |
| M5 废标条款 | M2 投标人须知(废标部分) | 废标风险识别 |
| M6 时间节点 | M1 招标公告(时间部分) | 时间规划 |
| M7 策略建议 | - | 分析独有，不映射 |

### 审核类型与参考文件映射

| 审核类型 | 主要审核对象 | 推荐参考文件 | 用途 |
|---------|-------------|-------------|------|
| tender_doc | 招标文件 | - | 法规合规检查 |
| analysis | 招标分析报告 | 招标文件 | 验证理解准确性 |
| outline | 投标大纲 | 招标分析报告 | 对照评分标准检查覆盖 |
| chapter | 章节草稿 | 招标分析报告 + 大纲 | 检查契合度和一致性 |
| full_bid | 完整标书 | 招标文件 | 对照原始要求检查响应 |

---

## 7. 数据验证规则

### 招标分析报告验证
- [ ] M1-M7所有模块存在且非空
- [ ] 评分标准总分值等于100分
- [ ] 关键时间节点在合理范围
- [ ] 预算金额格式正确

### 招标文件验证
- [ ] M1-M6章节完整
- [ ] 评分标准权重总和为100%
- [ ] 价格权重符合法规要求
- [ ] 废标条款清单完整

### 审核报告验证
- [ ] 审核类型有效
- [ ] 问题严重程度分类正确
- [ ] 风险等级与概率/影响矩阵一致
- [ ] 行动项可执行

---

*版本: v1.5 | 最后更新: 2026-04-07*
