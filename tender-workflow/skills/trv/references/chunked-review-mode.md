# 分块审核模式详解（Phase A / B / C / D）

> **何时读本文件**：当 §1.0.1 上下文模式决策判定 `REVIEW_MODE == "chunked"` 或 `"chunked_chapter"` 时（即标书/章节体量 > token 阈值需要分块时）。
>
> 内联模式（REVIEW_MODE == "inline"）跳过本文件，按 SKILL.md §1.1-1.4 流程执行 + 读 `references/inline-review-dimensions.md`。

## 目录

- §1.0.2 Phase A：结构提取与动态分块规划
- §1.0.3 Phase B：按 Chunk 分发子 Agent 审核
- §1.0.4 Phase C：跨 Chunk 一致性检查
- §1.0.5 Phase D：分块结果汇总

---

## 1.0.2 Phase A：结构提取与动态分块规划

**执行条件**：REVIEW_MODE == "chunked" 或 "chunked_chapter"

**步骤**：

1. **读取标书目录结构**：
   - 使用 Read 工具读取待审核文件的前 300 行（目录区域）
   - 提取所有 L2 章节（如 1.1, 1.2, 1.3 ...）和 L3 章节的列表
   - 记录每个章节的起始行号

2. **估算各章节体量**：
   - 对每个 L2 章节，计算到下一个 L2 章节之间的行数
   - 估算字数：`行数 × 平均每行字数（约 40 字）`
   - 标记超大章节：估算字数 > 30000 字的章节

3. **动态分块决策**：

   ```
   CHUNK_PLAN = []

   对每个 L2 章节：
     IF 估算字数 > 30000 AND 有 L3 子节：
       → 按 L3 子节拆分，每个 L3 作为独立 chunk
       → 输出提示："章节 {id} 估算 {N} 万字，下沉到 L3 拆分"
     ELSE：
       → 整个 L2 作为一个 chunk

     将每个 chunk 添加到 CHUNK_PLAN：
       chunk = {
         id: 章节编号,
         name: 章节名称,
         line_start: 起始行,
         line_end: 结束行
       }
   ```

4. **读取招标文件关键区域**（仅 full_bid 模式，需要 --reference）：
   - 使用 Grep 工具在参考文件中搜索以下关键词，记录所在行号范围：
     - 废标/否决条款：搜索 "废标|否决|无效投标|不予受理"
     - 评分标准：搜索 "评分|分值|评标办法|评审标准"
     - 技术要求：搜索 "技术要求|功能需求|性能指标|技术规格"
   - 对每个关键区域，使用 Read 工具读取对应段落（上下文扩展 50 行）
   - 产出 TENDER_SECTIONS：

     ```
     TENDER_COMMON = 废标条款文本 + 评分标准概览文本
     TENDER_TECH_SECTIONS = { 关键词 → 段落文本 }
     ```

5. **为每个 chunk 关联招标参考**：
   - 通用参考（所有 chunk 共享）：TENDER_COMMON
   - 定向参考：根据 chunk 章节名称，从 TENDER_TECH_SECTIONS 中匹配最相关的技术要求段落

6. **chapter 分块特殊处理**（REVIEW_MODE == "chunked_chapter"）：
   - 读取章节内容，提取 H3 子节列表
   - **如果有 H3 子节**：按 H3 子节拆分 chunk
   - **如果没有 H3 子节**（纯平铺内容）：按每 800 行强制切分为均匀 chunk
   - 招标参考沿用 --reference 文件的相关段落

7. **输出分块计划摘要**：

   ```
   ========================================
   分块审核计划
   ========================================
   总 chunk 数: <count>
   分块详情:
     Chunk 1: <id> <name> (约 <N> 字)
     Chunk 2: <id> <name> (约 <N> 字)
     ...
   下沉拆分章节: <list>（如有）
   ========================================
   ```

## 1.0.3 Phase B：按 Chunk 分发子 Agent 审核

**执行条件**：REVIEW_MODE == "chunked" 或 "chunked_chapter"

**步骤**：

1. **读取子 Agent 提示词模板**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/fullbid_chapter_agent.yaml`

2. **按批次分发子 Agent**：
   - 每批最多 4 个 Agent 并行
   - 对 CHUNK_PLAN 中的每个 chunk：
     - 构建子 Agent 提示词，填充变量：
       - `{{CHUNK_ID}}` = chunk.id
       - `{{CHUNK_NAME}}` = chunk.name
       - `{{BID_FILE_PATH}}` = 待审核文件路径
       - `{{BID_LINE_START}}` = chunk.line_start
       - `{{BID_LINE_END}}` = chunk.line_end
       - `{{LEVEL}}` = --level 参数值
       - `{{FOCUS}}` = --focus 参数值（如有）
       - `{{TENDER_COMMON}}` = TENDER_COMMON 文本
       - `{{TENDER_TARGETED}}` = 该 chunk 对应的定向参考文本
       - `{{CHUNK_MODE}}` = "full_bid_chunk"（REVIEW_MODE=chunked）或 "chapter_h3_chunk"（REVIEW_MODE=chunked_chapter）
         - **重要**：chapter_h3_chunk 模式下，子 Agent 的检查范围收窄至 H3 子节自身主题，不评判章节整体需求/评分覆盖度
     - 使用 Agent 工具发起调用：

       ```
       Agent(
         description="TRV 审核 chunk {chunk.id}",
         prompt=填充后的子 Agent 提示词
       )
       ```

   - 同一批次的 Agent 调用放在**同一条消息**中并行发送
   - 等待当前批次全部完成后，再发送下一批次

3. **收集子 Agent 结果**：
   - 收集每个子 Agent 返回的结构化 Markdown
   - 记录成功/失败状态

4. **降级守卫**：

   ```
   IF 某批次中 > 50% 的 Agent 失败：
     → 输出警告：" 分块审核部分失败，已完成 {N}/{total} 个 chunk"
     → 暂停后续批次
     → 使用已完成的结果继续进入 Phase C 和 Phase D
     → 在最终报告中标注未完成的 chunk
   ```

## 1.0.4 Phase C：跨 Chunk 一致性检查

**执行条件**：REVIEW_MODE == "chunked" 或 "chunked_chapter"，且 Phase B 至少有 2 个 chunk 成功完成

**步骤**：

1. **汇总关键数据点**：
   - 从 Phase B 所有成功完成的 chunk 结果中，提取"关键数据点提取"表格
   - 合并为统一的数据点汇总表

2. **读取一致性检查模板**：
   - 使用 Read 工具读取 `$SKILL_DIR/prompts/fullbid_consistency_agent.yaml`

3. **分发一致性检查 Agent**：
   - 构建提示词，填充变量：
     - `{{DATA_POINTS}}` = 数据点汇总表（Markdown 格式）
     - `{{BID_TOC}}` = 标书目录结构（Phase A 产出）
     - `{{CHUNK_LIST}}` = 已审核的 chunk 列表
     - `{{LEVEL}}` = --level 参数值
     - `{{CHUNK_MODE}}` = "full_bid_chunk" 或 "chapter_h3_chunk"
     - `{{TENDER_SCORING}}` = 评分标准摘要（仅 chapter_h3_chunk 模式，用于章节级评分覆盖度汇总评估）
     - `{{TENDER_REQUIREMENTS}}` = 章节对应的技术要求（仅 chapter_h3_chunk 模式，用于章节级需求覆盖度汇总评估）
     - **重要**：chapter_h3_chunk 模式下，Phase C 除标准一致性检查外，还承担章节级整体评估（需求覆盖度、评分覆盖度、H3 衔接质量），因为 Phase B 的 H3 子 Agent 只检查各自范围
   - 使用 Agent 工具发起调用：

     ```
     Agent(
       description="TRV 跨章节一致性检查",
       prompt=填充后的一致性检查提示词
     )
     ```

4. **收集一致性检查结果**

## 1.0.5 Phase D：分块结果汇总

**执行条件**：REVIEW_MODE == "chunked" 或 "chunked_chapter"

**步骤**：

1. **合并章节级审核结果**：
   - 按维度分类，合并所有 chunk 的审核发现
   - 按章节顺序排列

2. **合并一致性检查结果**：
   - 将 Phase C 的一致性检查发现作为独立维度"跨章节一致性"添加

3. **去重处理**：
   - 同一问题在相邻 chunk 中可能重复发现（尤其是 L3 拆分的情况）
   - 合并重复问题，保留最严重的评级

4. **进入 Phase 2**：
   - 将合并后的结果作为 Phase 1 的输出，传递给 Phase 2 进行统计和报告生成
   - Phase 2 逻辑不变，因为输入格式一致（各维度的检查结果表格）

5. **在报告中标注分块审核信息**：
   - 在报告的"基本信息"部分添加：

     ```
     - **审核模式**: 分块审核
     - **Chunk 数量**: <count>
     - **成功完成**: <success_count>/<total_count>
     - **一致性检查**: 已执行/跳过
     ```
