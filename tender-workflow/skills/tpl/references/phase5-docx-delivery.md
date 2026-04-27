# Phase 5：DOCX 输出与交付详解

> **何时读本文件**：Phase 3-4 内容生成完成、要把结果写为 DOCX 文件并交付时。
>
> 包括 5.1-5.5 全流程 + **§5.1.5 失败 fallback 矩阵**（D-008 — `docx_encoding_check.py --fix` 重试 N 次仍失败时该怎么做）。

## 5.1 DOCX 生成（内容与渲染分离）

采用**内容与渲染分离**架构，避免在 Python 脚本中内嵌大量中文字符串导致 UTF-8 截断乱码：

**步骤一：生成 JSON 数据文件**

将 Phase 3-4 的全部文档内容组织为 JSON 结构，通过 Write 工具写入临时文件（如 `/tmp/tpl_content.json`）。JSON 格式见 `skills/twc/tools/tpl_docx_writer.py` 文件头部注释。

**步骤二：调用渲染工具**

```bash
python3 $SKILL_DIR/../twc/tools/tpl_docx_writer.py <content.json> <output.docx>
```

渲染工具会自动清理 JSON 中因 Write 传输产生的 U+FFFD 字符碎片，确保 DOCX 内容干净。

**步骤三：编码完整性校验**

```bash
python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <output.docx> --max-retries 3
```

| 退出码 | 含义 | 动作 |
|---|---|---|
| `ENCODING_OK` | 一次通过，无需修复 | 继续 §5.2 反控标最终检查 |
| `FIX_OK` | 内部修复成功（最多 3 次重试） | 继续 §5.2 |
| `FIX_FAILED` | 3 次重试后仍残留损坏 | 走下方 §5.1.5 fallback 决策矩阵 |

## 5.1.5 输出失败 fallback 矩阵

`docx_encoding_check.py --fix` 返回 `FIX_FAILED` 后，按以下决策矩阵选择降级路径：

| 残留损坏数量 | 损坏分布 | 推荐 fallback | 必做动作 |
|---|---|---|---|
| ≤ 5 处 | 集中在 1-2 个段落 | **A. 保留 DOCX + 通知人工** | 输出工具 UNFIXED 列表给用户，提示 Word 内手改 |
| 6-20 处 | 散布多段 | **B. 保留 JSON + 输出 Markdown 备选** | 不删 `/tmp/tpl_content.json`，额外 `tpl_docx_writer.py --format markdown` 生成 .md 副本 |
| > 20 处 或 全文 ratio > 5% | 大面积损坏 | **C. 中止 + 强制重生成** | 删 `<output.docx>`、保留 JSON、提示用户调小 level 后重跑 |
| 任意 + 用户已等待 > 5 min | 任意 | **D. 优先 B（JSON+Markdown）保人** | 不让用户空手而归 |

**A — 保留 DOCX + 通知人工**：

```
⚠️ 文档存在 N 处无法自动清除的编码损坏，已生成 DOCX 但建议人工检查：
<工具输出的 UNFIXED 列表，含段落定位>

后续动作：
1. 用 Word 打开文件，按 UNFIXED 列表定位修正
2. 或重新生成（删除 <output.docx> 后重跑 /tpl）
```

**B — 保留 JSON + 输出 Markdown 备选**：

```bash
# 不删 /tmp/tpl_content.json
python3 $SKILL_DIR/../twc/tools/tpl_docx_writer.py /tmp/tpl_content.json <output_md_path> --format markdown
```

输出给用户：

```
⚠️ DOCX 生成出现较多编码损坏（N 处），已额外生成 Markdown 备选：
- DOCX：<output.docx>（含 N 处待修问题）
- Markdown：<output.md>（结构完整可手工二次加工）
- 原始 JSON：/tmp/tpl_content.json（保留，可用于重生成）

建议：先用 Markdown 版核对内容，再决定是修 DOCX 还是从 JSON 重生成。
```

**C — 中止 + 强制重生成**：

```bash
rm <output.docx>
# 保留 /tmp/tpl_content.json
```

输出给用户：

```
❌ DOCX 损坏比例过高（N 处 / X% 全文），已中止交付。
原因：可能是 Phase 3 生成的内容含特殊字符 / 长度超阈值。
建议：用 --level 降一档（如 detailed → standard）后重跑：
  /tpl <原参数> --level <更低级别>
原始 JSON 保留在 /tmp/tpl_content.json 供调试。
```

**D — 默认走 B**：当 5 分钟阈值触发时，无论损坏数量直接走 B，确保用户至少拿到可读的 Markdown。

**fallback 决策日志要求**：

每次进入 §5.1.5 必须输出一行决策日志：

```
[5.1.5 fallback] 触发原因：FIX_FAILED, 残留=N, 分布=<集中/散布/全文>, 选择=A/B/C/D
```

## 5.2 反控标最终检查

生成 DOCX 前执行最终品牌名扫描，确保零残留。

## 5.3 文件交付

告知用户文件路径。

**文件命名**：

- 含评标办法：`技术规格与评标办法_<项目名>_<时间戳>.docx`
- 仅技术规格：`技术规格_<项目名>_<时间戳>.docx`

**文档结构**：

- 封面（标题、项目名、行业类型、生成日期）
- 目录占位（提示按 Ctrl+A → F9 更新）
- 第一部分：技术规格与要求（Phase 3 输出）
- 第二部分：评标办法（Phase 4 输出，若有）

## 5.4 输出确认

```
技术规格[与评标办法]生成完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
文件名称：[文件名]
文件路径：[完整路径]
行业类型：[行业]
细致程度：[级别]
技术要求条目：X 条（含 Y 条控标点）
[评标办法维度：Z 个]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

反控标自检：✅ 通过

后续建议：
1. 打开 Word 文件，按 Ctrl+A → F9 更新目录
2. 审核技术要求的合理性和自然度
3. 建议通过 /trv --type tender_doc 进行深度审核
```

## 5.5 自动清理

若存在临时处理目录，自动删除。

**例外**：若 §5.1.5 走了 B 或 C 路径（保留 JSON），**不要清理** `/tmp/tpl_content.json`，直到用户明确确认完成。
