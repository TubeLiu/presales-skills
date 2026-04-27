---
name: trv
description: >
  当用户说"审核标书"、"审一下标书"、"检查投标文件"、"审查招标文件"、"审核方案"、"review"、"quality check" 时触发。
  对招标文件、分析报告、投标大纲、章节草稿、完整标书进行多维度审核（完整性 / 合规性 / 评分对齐 / 风险检查），支持 AI 驱动智能修订。
  审核类型通过 --type 指定（tender_doc / analysis / outline / chapter / full_bid）。
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob, Grep
---

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析（替代 `$SKILL_DIR`）。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

## 路径自定位

**首次调用本 skill 的脚本/工具前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/tools/...`、`$SKILL_DIR/prompts/...`、`$SKILL_DIR/templates/...`）：

```bash
SKILL_DIR=$(python3 - <<'PYEOF' 2>/dev/null
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/tender-workflow/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/trv'); sys.exit(0)
PYEOF
)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/tender-workflow/skills/trv" ] && SKILL_DIR="$d/tender-workflow/skills/trv" && break
    [ -d "$d/trv" ] && SKILL_DIR="$d/trv" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${TENDER_WORKFLOW_PLUGIN_PATH:-}" ] && SKILL_DIR="$TENDER_WORKFLOW_PLUGIN_PATH/skills/trv"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./tender-workflow/skills/trv" ] && SKILL_DIR="$(pwd)/tender-workflow/skills/trv"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 tender-workflow / trv skill 安装位置。" >&2
    echo "请设置：export TENDER_WORKFLOW_PLUGIN_PATH=/path/to/tender-workflow" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install tender-workflow@presales-skills` 或手工 export 环境变量。


# 审核者 (TRV) - Tender Reviewer

对招标文件、分析报告、投标大纲、章节草稿、技术标书进行多维度审核。

## 角色定位

**服务对象**: 甲方 + 乙方（服务招投标全流程）
**核心任务**: 对各阶段产出物进行质量把控，识别问题与风险，提供改进建议

## 使用方式

```bash
/trv <file> --type <review_type> [--reference <file>] [--level <level>] [--focus <focus>] [--revise-docx] [--revise-scope <must|all>]
```

**参数说明**:
- `file`: 待审核的文件路径
- `--type`: 审核类型（必填）
  - `tender_doc`: 技术规格与评标办法审核（tpl v2.0 输出，含 M3 评标办法 + M5 技术规格）
  - `analysis`: 招标分析报告审核
  - `outline`: 投标大纲审核（技术部分）
  - `chapter`: 章节草稿审核
  - `full_bid`: 技术标书审核
- `--reference`: 参考文件（用于对照审核，可选但推荐）
  - 审核大纲时：引用招标分析报告
  - 审核章节时：引用招标分析报告
  - 审核完整标书时：引用招标文件
- `--level`: 审核严格程度（可选，默认`all`）
  - `critical`: 仅检查严重问题（快速检查）
  - `high`: 检查严重和高风险问题
  - `all`: 完整检查（包括建议优化项）
- `--focus`: 专注维度（可选）
  - `completeness`: 仅检查完整性
  - `compliance`: 仅检查合规性
  - `scoring`: 仅分析评分契合度
  - `risk`: 仅识别风险
- `--revise-docx`: 审核完成后自动生成修订版 DOCX（仅对 `.docx` 输入有效，优先支持 `outline` / `chapter` / `full_bid`）
- `--revise-scope`: 自动修订范围（可选，默认 `must`）
  - `must`: 仅处理必须修改项/严重和重要问题
  - `all`: 同时纳入建议优化项

**输出**: `output/trv/审核报告_<type>_<timestamp>.md`，启用 `--revise-docx` 时额外输出 `output/trv/<原文件名>_修订版_<timestamp>.docx`

---

## Phase 0：参数解析与初始化

### 0.0 参数解析

检查命令行参数并解析：

**步骤**：

1. **检查帮助参数**：
   - 如果参数包含 `-h` 或 `--help`，输出帮助信息并退出
   - 帮助信息包括：使用方式、参数说明、审核类型详解、使用示例

2. **解析位置参数**：
   - 第一个位置参数：待审核文件路径
   - 如果未提供，输出错误提示并退出

3. **解析 --type 参数**（必选）：
   - 检查是否提供 --type 参数
   - 验证 --type 值是否有效（tender_doc/analysis/outline/chapter/full_bid）
   - 如果未提供或无效，输出错误提示并退出

4. **解析 --reference 参数**（可选）：
   - 如果提供，检查文件是否存在
   - 如果文件不存在，输出警告但继续执行

5. **解析 --level 参数**（可选，默认 all）：
   - 验证值是否有效（critical/high/all）
   - 如果无效，输出警告并使用默认值 all

6. **解析 --focus 参数**（可选）：
   - 验证值是否有效（completeness/compliance/scoring/risk）
   - 如果无效，输出警告并忽略

7. **解析 --revise-docx 参数**（可选）：
   - 若提供该参数，记录 `REVISE_DOCX=true`
   - 若未提供，默认 `REVISE_DOCX=false`

8. **解析 --revise-scope 参数**（可选，默认 must）：
   - 验证值是否有效（must/all）
   - 如果无效，输出警告并使用默认值 `must`

9. **参数组合检查**：
   - 如果 --focus=scoring 但未提供 --reference，输出建议提示
   - 如果审核类型为 outline/chapter/full_bid 但未提供 --reference，输出建议提示
   - 如果启用 `--revise-docx` 但待审核文件不是 `.docx`，输出提示“自动修订已跳过：仅支持 DOCX 输入”并继续审核
   - 如果启用 `--revise-docx` 但审核类型不是 `outline`/`chapter`/`full_bid`，输出提示“当前类型暂不支持自动修订”，并继续审核

10. **输出参数解析摘要**：
   ```
   ========================================
   TRV 审核参数解析
   ========================================
   待审核文件: <file_path>
   审核类型: <type>
   参考文件: <reference_path> (如提供)
   审核级别: <level>
   专注维度: <focus> (如提供)
   自动修订: 开启/关闭
   修订范围: <revise_scope> (如启用)
   ========================================
   ```

### 0.05 配置加载（可选）

读取统一配置文件获取默认审核级别（可被 `--level` 参数覆盖）：
```bash
python3 $SKILL_DIR/../twc/tools/tw_config.py get trv default_level
```

- 若未指定 `--level` 且配置中 `trv.default_level` 有值 → 使用配置值
- 配置文件：`~/.config/tender-workflow/config.yaml`，通过 `/twc setup` 管理

### 0.1 输出目录初始化

确定输出路径：

**步骤**：

1. **设置输出路径**：
   ```bash
   OUTPUT_DIR="./output/trv"
   ```

2. **创建输出目录**：
   ```bash
   mkdir -p "${OUTPUT_DIR}"
   ```

3. **输出环境信息**：
   ```
   输出目录: ./output/trv
   ```

### 0.2 文件读取

读取待审核文件和参考文件：

**步骤**：

1. **读取待审核文件**：
   - 使用 Read 工具读取文件内容
   - 支持 PDF、DOCX、Markdown 格式
   - 如果读取失败，输出错误并退出

2. **读取参考文件**（如提供）：
   - 使用 Read 工具读取参考文件内容
   - 支持 PDF、DOCX、Markdown 格式
   - 如果读取失败，输出警告但继续执行

3. **输出文件信息摘要**：
   ```
   ========================================
   文件信息
   ========================================
   待审核文件: <file_name>
   文件类型: <file_type>
   文件大小: <file_size>
   参考文件: <reference_name> (如提供)
   ========================================
   ```

### 0.25 文档质量预检（DOCX 编码完整性检查与自动修复）

对 DOCX 格式的待审核文件，在进入正式审核前执行编码完整性扫描。若发现乱码，自动修复（最多重试 3 次）后再进入审核流程。

**执行条件**：待审核文件为 .docx 格式

**步骤**：

1. 执行 `python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <file_path> --max-retries 3`

2. 根据退出码和输出判断结果：

   - **`FIX_OK`（退出码 0）**：无乱码或已全部清除。
     在审核报告"基本信息"中记录清除数量，使用修复后的文件继续审核。

   - **`FIX_FAILED`（退出码 2）**：3 次重试后仍有残留。
     将残留信息记录为 **critical 级别问题**，并**通知用户人工修复**：
     ```
     ⚠️ 文档编码损坏：3 次自动修复后仍残留 N 处乱码，需要人工介入。
     残留位置：<工具输出的 UNFIXED 列表>
     建议操作：
     1. 重新生成文档（推荐）
     2. 在 Word 中打开文件，手动修正上述段落
     修复完成后请重新提交审核。
     ```
     使用修复后的文件继续后续审核（尽量提供完整审核意见），但最终结论标注为"不通过"。

### 0.3 启动确认

输出审核启动信息并直接进入 Phase 1：

**输出**：
```
========================================
开始审核
========================================
审核类型: <type_name>
审核维度: <dimensions>
预计耗时: <estimated_time>
========================================
```

**预计耗时参考**：
- critical 级别：1-2 分钟
- high 级别：3-5 分钟
- all 级别：5-10 分钟

---

## Phase 1：多维度审核执行

### 1.0 确定审核维度

根据 --focus 参数确定执行的审核维度：

**步骤**：

1. **如果提供了 --focus 参数**：
   - 仅执行指定的维度
   - 输出：`审核维度: <focus_name>`

2. **如果未提供 --focus 参数**：
   - 执行所有 4 个维度
   - 输出：`审核维度: 完整性检查、合规性审查、评分契合度分析、风险识别`

3. **维度执行顺序**：
   - 1.1 完整性检查（Completeness）
   - 1.2 合规性审查（Compliance）
   - 1.3 评分契合度分析（Scoring Alignment）
   - 1.4 风险识别（Risk Check）

### 1.0.1 上下文模式决策

根据待审核文件体量，自动选择审核模式：

**步骤**：

1. **估算内容 token 量**：
   - 对 DOCX/PDF 文件：使用 Bash 工具提取实际文本字符数（python3 -c "from docx import Document; print(sum(len(p.text) for p in Document('file.docx').paragraphs))"），然后 `估算 token = 字符数 × 1.5`
   - 对 Markdown/纯文本文件：使用 Bash 工具获取文件大小（字节数），`估算 token = 字节数 / 2`
   - 如果提供了 --reference，同样估算参考文件 token 量
   - `总估算 token = 待审核文件 token + 参考文件 token + 15000`（审核指令开销）
   - 注意：DOCX 文件字节数包含图片等二进制数据，不能直接用文件大小估算

2. **模式决策**：
   ```
   IF 总估算 token < 80000:
     → REVIEW_MODE = "inline"（当前内联模式，直接进入 1.1-1.4）
   
   ELIF type == "full_bid":
     → REVIEW_MODE = "chunked"（分块审核模式，进入 1.0.2）
   
   ELIF type == "chapter" AND 总估算 token >= 80000:
     → REVIEW_MODE = "chunked_chapter"（大章节分块模式，进入 1.0.2）
   
   ELSE:
     → REVIEW_MODE = "inline"
   ```

3. **输出模式信息**：
   ```
   审核模式: <mode>（内联/分块审核/大章节分块）
   估算 token: <estimated_tokens>
   ```

4. **如果 REVIEW_MODE == "inline"**：跳过 1.0.2-1.0.5，直接进入 1.1

### 1.0.2 Phase A：结构提取与动态分块规划

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

### 1.0.3 Phase B：按 Chunk 分发子 Agent 审核

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

### 1.0.4 Phase C：跨 Chunk 一致性检查

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

### 1.0.5 Phase D：分块结果汇总

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

---

**以下为内联模式（REVIEW_MODE == "inline"）的审核流程，当进入分块模式时跳过 1.1-1.4：**

### 1.1 完整性检查（Completeness）

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

### 1.2 合规性审查（Compliance）

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

### 1.3 评分契合度分析（Scoring Alignment）

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

### 1.4 风险识别（Risk Check）

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

---

## Phase 2：审核结果汇总

> **分块模式说明**：当 REVIEW_MODE == "chunked" 或 "chunked_chapter" 时，
> Phase 2 的输入来自 Phase D（1.0.5）的合并结果，包含：
> - 各 chunk 的章节级审核发现（已按维度合并）
> - 跨 chunk 一致性检查发现（作为独立维度）
> 输入格式与内联模式一致，Phase 2 逻辑无需区分模式。

### 2.1 生成审核结论

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

### 2.2 生成问题清单

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

### 2.3 生成修改优先级

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

## Phase 3：Markdown 报告生成

### 3.1 生成完整报告

整合 Phase 1 和 Phase 2 的所有结果，生成结构化 Markdown 报告：

**报告结构**：

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

### 3.2 保存报告文件

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

### 3.5 DOCX 智能修订（AI 驱动）

**执行条件**：启用 `--revise-docx`

**步骤**：

1. **检查适用范围**：
   - 若待审核文件不是 `.docx`：输出”自动修订已跳过：仅支持 DOCX 输入”，直接进入 Phase 4
   - 若审核类型不是 `outline` / `chapter` / `full_bid`：输出”自动修订已跳过：当前审核类型暂不支持”，直接进入 Phase 4

2. **生成修订指令 JSON**：

   基于刚完成的审核报告和原文 DOCX 内容（已在上下文中），为每个可自动修订的问题生成一条结构化指令。

   **范围过滤**（根据 `--revise-scope`）：
   - `must`：仅为 `critical` 和 `high` 严重程度的问题生成指令
   - `all`：为所有严重程度的问题生成指令（含 `major` 和 `minor`）

   **指令 JSON 格式**：
   ```json
   {
     “meta”: {
       “source_report”: “<审核报告路径>”,
       “scope”: “must”,
       “instruction_count”: 5
     },
     “instructions”: [
       {
         “id”: “R001”,
         “severity”: “critical”,
         “type”: “<指令类型>”,
         “description”: “问题描述与修订说明”,
         “match”: { “method”: “<匹配方式>”, “text”: “...” },
         “action”: { “find”: “原文本”, “replace”: “新文本” }
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
   “match”: {
     “method”: “table_header_row”,
     “header_contains”: [“序号”, “投标规格”, “偏离”],
     “row_match”: { “column”: “序号”, “value”: “15” },
     “target_column”: “投标规格”
   }
   ```

   **生成规则**：
   - 优先 `paragraph_text_replace`，仅当无法精确定位 find 文本时才用 `paragraph_full_replace`
   - 数值修正（如 99.9% → 99.99%）使用精确 find/replace
   - 术语统一（如”贵行”→”招标方”）使用 `global_text_replace`
   - 表格更新**必须**用 `table_header_row` 匹配，**禁止**硬编码行索引
   - 补充缺失内容时，仅在有明确锚点段落时使用 `paragraph_insert_after`
   - 需要人工输入的问题（如 `[待商务确认]` 占位符）、结构重组等复杂修订，**不生成指令**，在终端输出中标注为”需人工处理”
   - 每条指令的 `description` 字段应人可读，说明修订原因

   **写入临时文件**：
   ```bash
   cat > “${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json” << 'INSTRUCTIONS_EOF'
   { ... }
   INSTRUCTIONS_EOF
   ```

3. **执行修订工具**：
   ```bash
   python3 $SKILL_DIR/../twc/tools/trv_docx_reviser.py \
     --input <file> \
     --instructions “${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json” \
     --output-dir “${OUTPUT_DIR}”
   ```

4. **修订后编码检查**：
   - 若修订成功，继续执行：
     ```bash
     python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <revised_docx> --max-retries 3
     ```
   - 若发现残留乱码，将结果写入终端输出，并保留修订版文件供人工处理

5. **失败降级**：
   - 若修订工具返回 `status=skipped`，输出跳过原因，但不影响审核报告交付
   - 若修订工具或编码检查失败，输出警告”审核报告已生成，修订版 DOCX 生成失败”，不回滚审核结果

6. **结果报告**：
   - 解析工具输出的 JSON，在终端输出中报告：
     - 指令总数、成功数、未匹配数、错误数
     - 需人工处理的问题列表
     - 修订版文件路径
   - 在审核报告”基本信息”或”附录”中追加：
     - **自动修订**: 已执行/已跳过/失败
     - **修订范围**: must/all
     - **修订版文件**: <path>（如成功）
     - **修订统计**: applied N / not_found N / errors N

7. **清理临时文件**：
   - 删除 `${OUTPUT_DIR}/.revision_instructions_${TIMESTAMP}.json`

---

## Phase 4：任务完成与清理

### 4.1 输出确认

输出文件信息：

```
========================================
审核完成
========================================
报告文件: <file_name>
文件路径: <file_path>
文件大小: <file_size>
========================================
```

### 4.2 审核结果摘要

输出审核结果摘要：

```
审核结果摘要:
- 总体评价: <overall_assessment>
- 问题总数: <total_issues>项
- 风险等级: <risk_level>
- 执行维度: <dimensions>
```

### 4.3 后续建议

根据审核类型和结果提供针对性建议：

**tender_doc（招标文件审核）**：
- 如果通过：建议发布前再次人工复核关键条款
- 如果有条件通过：建议修改一般问题后再次审核
- 如果不通过：必须修改严重问题后重新审核

**analysis（招标分析报告审核）**：
- 如果通过：可以基于此分析报告生成投标大纲
- 如果有条件通过：建议修改后再生成大纲
- 如果不通过：必须重新分析招标文件

**outline（投标大纲审核）**：
- 如果通过：可以开始撰写章节内容
- 如果有条件通过：建议优化大纲结构后再撰写
- 如果不通过：必须重新调整大纲

**chapter（章节草稿审核）**：
- 如果通过：可以继续撰写其他章节
- 如果有条件通过：建议修改后再继续
- 如果不通过：必须重新撰写该章节

> **并行写作章节审核提示**（taw v1.8.0+）：
> 长章节（≥3个H3子节且≥4500字）可能采用并行写作模式，额外关注：
> - H3 子节间术语是否统一
> - 相邻 H3 之间过渡是否自然（无突兀跳转或重复论述）
> - 同一技术描述在不同 H3 中是否一致（架构层级数、组件名称等）
> - 评分项覆盖是否完整

**full_bid（技术标书审核）**：
- 如果通过：可以准备投标
- 如果有条件通过：建议修改后再次审核
- 如果不通过：必须修改严重问题后重新审核

### 4.4 文件交付

根据运行环境交付文件：

**CLI 环境**：
```
报告已保存至: <file_path>
修订版已保存至: <revised_docx_path>（如成功生成）
```

---

## 执行示例

### 示例 1：审核 tpl 生成的技术规格与评标办法

```bash
/trv 技术规格与评标办法_政务云项目_20260313020016.docx --type tender_doc
```

**执行流程**：
1. Phase 0：解析参数，读取技术规格与评标办法文件
2. Phase 1：执行所有 4 个维度（1.1-1.4），检查技术规格完整性、反控标合规性、评标办法合规性、内部一致性风险
3. Phase 2：汇总结果
4. Phase 3：生成报告
5. Phase 4：输出确认

### 示例 2：全面审核大纲结构与评分契合度

```bash
/trv 大纲.docx --type outline --reference 招标分析报告.md --level all
```

**执行流程**：
1. Phase 0：解析参数，读取大纲和分析报告
2. Phase 1：执行所有 4 个维度（1.1-1.4），显示所有问题
3. Phase 2：汇总结果
4. Phase 3：生成报告
5. Phase 4：输出确认

### 示例 3：深度审核章节内容质量

```bash
/trv 总体方案设计.md --type chapter --reference 招标分析报告.md --level all --focus scoring
```

**执行流程**：
1. Phase 0：解析参数，读取章节和分析报告
2. Phase 1：仅执行评分契合度分析（1.3），显示所有问题
3. Phase 2：汇总结果
4. Phase 3：生成报告
5. Phase 4：输出确认

### 示例 4：投标前技术标书最终检查

```bash
/trv 技术标书.docx --type full_bid --reference 招标文件.pdf --level all --focus risk
```

**执行流程**：
1. Phase 0：解析参数，读取技术标书和招标文件
2. Phase 1：仅执行风险识别（1.4），显示所有风险
3. Phase 2：汇总结果
4. Phase 3：生成报告
5. Phase 4：输出确认

### 示例 5：审核完成后自动生成修订版 DOCX

```bash
/trv 技术标书.docx --type full_bid --reference 招标文件.docx --level all --revise-docx --revise-scope must
```

**执行流程**：
1. Phase 0：解析参数并确认已启用自动修订
2. Phase 1-3：正常完成审核并生成 Markdown 报告
3. Phase 3.5：基于审核报告生成修订指令 JSON → 调用 `skills/twc/tools/trv_docx_reviser.py` 执行修订 → 编码检查
4. Phase 4：同时输出审核报告、修订版文件路径、修订统计

---

## 错误处理

### 参数错误

- 缺少必选参数：输出错误提示并退出
- 无效参数值：输出警告并使用默认值或忽略
- 文件不存在：输出错误并退出

### 文件读取错误

- 文件格式不支持：输出错误并退出
- 文件损坏：输出错误并退出
- 文件过大：输出警告但继续执行

### 审核执行错误

- Prompt 配置加载失败：输出错误并跳过该维度
- 审核过程中断：保存已完成的部分结果

### 文件保存错误

- 目录不存在：自动创建目录
- 磁盘空间不足：输出错误并退出
- 权限不足：输出错误并退出

### 智能修订错误

- 输入不是 DOCX：跳过修订，不影响审核报告生成
- 审核类型暂不支持：跳过修订，不影响审核报告生成
- 修订指令 JSON 生成失败：保留审核报告，输出修订失败提示
- 修订工具执行失败：保留审核报告，输出修订失败提示
- 部分指令未匹配（not_found）：已匹配指令正常生效，未匹配指令在输出中列出供人工参考
- 修订版编码检查失败：保留修订版文件，并提示人工处理残留乱码

---

## 注意事项

1. **审核准确性**：
   - 审核结果依赖 LLM 的理解能力
   - 建议人工复核关键问题
   - 报告中会添加"建议人工复核"提示

2. **性能考虑**：
   - 全面审核（--level=all）可能耗时较长
   - 建议先使用 --level=critical 快速检查
   - 大文件审核可能需要更长时间

3. **参考文件重要性**：
   - 评分契合度分析强烈建议提供参考文件
   - 参考文件有助于提高审核准确性
   - 参考文件应与待审核文件相关

4. **审核级别选择**：
   - critical：快速预检，仅关注阻塞性问题
   - high：常规检查，关注严重和高风险问题
   - all：最终审核，全面检查所有问题

5. **专注维度使用**：
   - 用于针对性检查特定方面
   - 不建议在最终审核时使用
   - 适合迭代优化过程中的快速检查

---

## 版本历史

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
- ✅ 非 DOCX 输入或暂不支持的审核类型自动降级为”跳过修订，不中断审核”

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

