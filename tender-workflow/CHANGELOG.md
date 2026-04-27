# tender-workflow CHANGELOG

各 skill 的版本演进记录。新增条目从顶部追加。

## trv (Tender Reviewer)

### v1.5.0 (2026-04-07)

- ✅ **重构 Phase 3.5**：从硬编码规则驱动改为 AI 驱动智能修订
- ✅ Claude 在审核时动态生成修订指令 JSON，Python 工具只做通用 DOCX 操作执行
- ✅ 支持 6 种指令类型：段落替换（保留格式）、整段替换、表格单元格替换、全文替换、段落插入、段落删除
- ✅ 表格定位从硬编码行索引改为按表头内容+行标识值匹配
- ✅ Run 级文本替换，最大程度保留原有格式（加粗/斜体/颜色等）
- ✅ 修订结果结构化报告：每条指令独立报告 applied/not_found/error 状态
- ✅ 删除全部项目专属硬编码（16 条段落替换、5 条全局替换、5 个表格行索引）

### v1.4.1 (2026-04-07)

- ✅ 新增 `--revise-docx` 参数：审核完成后自动生成修订版 DOCX
- ✅ 新增 `--revise-scope <must|all>`：控制自动修订范围
- ✅ 新增 `skills/twc/tools/trv_docx_reviser.py`：规则驱动的低风险 DOCX 修订工具（v1.5.0 已重构为 AI 驱动）
- ✅ 新增 Phase 3.5：审核报告生成后自动执行修订与编码检查
- ✅ 输出新增修订版文件命名规则：`<原文件名>_修订版_<timestamp>.docx`
- ✅ 非 DOCX 输入或暂不支持的审核类型自动降级为"跳过修订，不中断审核"

### v1.4.0 (2026-04-03)

- ✅ 大文件分块审核：full_bid/chapter 审核超过 80K token 阈值时自动进入分块模式
- ✅ 动态分块策略：按 L2 章节拆分，超大章节（>3万字）自动下沉到 L3
- ✅ 三阶段审核架构：Phase A（结构提取）→ Phase B（并行 chunk 审核）→ Phase C（一致性检查）→ Phase D（汇总）
- ✅ 跨章节一致性检查：专用 Agent 对比所有 chunk 提取的关键数据点，检测数值/描述/承诺矛盾
- ✅ 检查项 scope 标记：区分 chapter 级（子 Agent 执行）和 global 级（一致性检查执行）
- ✅ 新增提示词模板：fullbid_chapter_agent.yaml + fullbid_consistency_agent.yaml
- ✅ 向后兼容：小文件自动走原有内联模式，--focus/--level 参数不变

### v1.3.0 (2026-04-02)

- ✅ 适配 taa v2.1.0+ 大纲简化：completeness/risk_check 明确技术部分专项范围，增加服务管理章节完整性检查
- ✅ 适配 taa v2.3.0+ 上下文优化：scoring_alignment 支持 phase1_handoff.yaml 作为可选结构化输入
- ✅ 适配 taw v1.8.0+ 并行写作：risk_check 增加并行写作章节一致性风险检查，SKILL.md 增加审核指导
- ✅ full_bid 检查范围明确为技术标书（技术部分）

### v1.2.0 (2026-03-13)

- ✅ tender_doc 类型对齐 tpl v2.0：检查范围从 M1-M6 完整招标文件缩减为 M3+M5（技术规格+评标办法）
- ✅ completeness.yaml：重写 tender_doc 检查清单（9章技术规格 + 6章评标办法）
- ✅ compliance.yaml：更新 tender_doc 审查要点（新增反控标合规性、技术评分与技术规格对应关系检查）
- ✅ risk_check.yaml：更新 tender_doc 风险检查重点（聚焦反控标+评标合规+内部一致性）

### v1.1.0 (2026-03-10)

- ✅ outline/full_bid 检查项改为动态关系检查，不硬编码章节号或章节名
- ✅ 移除非技术部分审核（投标函/商务/资格/报价/签章）
- ✅ 评分契合度移除商务和价格分类
- ✅ 风险识别移除形式性废标、资格性废标、商务风险
- ✅ tender_doc/analysis/chapter 不变

### v1.0.0 (2026-03-10)

- ✅ 实现完整的 Phase 0-4 执行流程
- ✅ 支持 5 种审核类型
- ✅ 支持 4 个审核维度
- ✅ 支持参数组合（--level、--focus）
- ✅ 支持参考文件对照
- ✅ 生成结构化 Markdown 报告
- ✅ 支持 CLI 环境
