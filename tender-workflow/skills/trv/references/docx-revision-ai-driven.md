# DOCX 智能修订（AI 驱动）— Phase 3.5 详解

> **何时读本文件**：用户传 `--revise-docx` 且原文件是 .docx 且 --type 为 outline / chapter / full_bid 时。
>
> 不传 `--revise-docx` 或类型为 tender_doc / analysis 时跳过本文件。

## 执行条件

启用 `--revise-docx`。

## 步骤

### 1. 检查适用范围

- 若待审核文件不是 `.docx`：输出"自动修订已跳过：仅支持 DOCX 输入"，直接进入 Phase 4
- 若审核类型不是 `outline` / `chapter` / `full_bid`：输出"自动修订已跳过：当前审核类型暂不支持"，直接进入 Phase 4

### 2. 生成修订指令 JSON

基于刚完成的审核报告和原文 DOCX 内容（已在上下文中），为每个可自动修订的问题生成一条结构化指令。

**范围过滤**（根据 `--revise-scope`）：

- `must`：仅为 `critical` 和 `high` 严重程度的问题生成指令
- `all`：为所有严重程度的问题生成指令（含 `major` 和 `minor`）

**指令 JSON 格式**：

```json
{
  "meta": {
    "source_report": "<审核报告路径>",
    "scope": "must",
    "instruction_count": 5
  },
  "instructions": [
    {
      "id": "R001",
      "severity": "critical",
      "type": "<指令类型>",
      "description": "问题描述与修订说明",
      "match": { "method": "<匹配方式>", "text": "..." },
      "action": { "find": "原文本", "replace": "新文本" }
    }
  ]
}
```

**支持的指令类型**：

- `paragraph_text_replace` — 段落内查找替换（**优先使用**，保留 run 格式）
- `paragraph_full_replace` — 整段替换（格式降级到首 run）
- `table_cell_replace` — 按表头+行内容定位单元格替换
- `global_text_replace` — 全文查找替换（段落 + 表格）
- `paragraph_insert_after` — 在匹配段落后插入新段落
- `paragraph_delete` — 删除匹配段落

**匹配方式**：

- `contains` — 段落/单元格包含指定文本（推荐，容错性最好）。可选 `context_before` 字段：要求同一段落内还包含该文本，用于消歧（注意：检查的是同一段落，不是前一段落）
- `exact` — 段落文本精确匹配（归一化后比较）
- `regex` — 正则表达式匹配（`pattern` 字段指定正则）
- `table_header_row` — 按表头列名 + 行标识值定位（**表格必用**）
- `global` — 全文范围，无需匹配

**表格单元格匹配格式**（`table_cell_replace` 专用）：

```json
"match": {
  "method": "table_header_row",
  "header_contains": ["序号", "投标规格", "偏离"],
  "row_match": { "column": "序号", "value": "15" },
  "target_column": "投标规格"
}
```

**生成规则**：

- 优先 `paragraph_text_replace`，仅当无法精确定位 find 文本时才用 `paragraph_full_replace`
- 数值修正（如 99.9% → 99.99%）使用精确 find/replace
- 术语统一（如"贵行"→"招标方"）使用 `global_text_replace`
- 表格更新**必须**用 `table_header_row` 匹配，**禁止**硬编码行索引
- 补充缺失内容时，仅在有明确锚点段落时使用 `paragraph_insert_after`
- 需要人工输入的问题（如 `[待商务确认]` 占位符）、结构重组等复杂修订，**不生成指令**，在终端输出中标注为"需人工处理"
- 每条指令的 `description` 字段应人可读，说明修订原因

**写入临时文件**：

```bash
cat > "${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json" << 'INSTRUCTIONS_EOF'
{ ... }
INSTRUCTIONS_EOF
```

### 3. 执行修订工具

```bash
python3 $SKILL_DIR/../twc/tools/trv_docx_reviser.py \
  --input <file> \
  --instructions "${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json" \
  --output-dir "${OUTPUT_DIR}"
```

### 4. 修订后编码检查

- 若修订成功，继续执行：

  ```bash
  python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <revised_docx> --max-retries 3
  ```

- 若发现残留乱码，将结果写入终端输出，并保留修订版文件供人工处理

### 5. 失败降级

- 若修订工具返回 `status=skipped`，输出跳过原因，但不影响审核报告交付
- 若修订工具或编码检查失败，输出警告"审核报告已生成，修订版 DOCX 生成失败"，不回滚审核结果

### 6. 结果报告

- 解析工具输出的 JSON，在终端输出中报告：
  - 指令总数、成功数、未匹配数、错误数
  - 需人工处理的问题列表
  - 修订版文件路径
- 在审核报告"基本信息"或"附录"中追加：
  - **自动修订**: 已执行/已跳过/失败
  - **修订范围**: must/all
  - **修订版文件**: <path>（如成功）
  - **修订统计**: applied N / not_found N / errors N

### 7. 清理临时文件

- 删除 `${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json`
