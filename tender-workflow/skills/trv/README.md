# trv — 招投标审核助手

**中文** | [English](./README_EN.md)

**trv**（Tender Reviewer）对招标文件、分析报告、投标大纲、章节草稿、完整标书进行多维度审核。

**版本**：v1.5.0 | **详细文档**：[SKILL.md](./SKILL.md)

---

## 快速开始

```bash
# 审核招标文件（甲方自查）
/trv 招标文件.docx --type tender_doc

# 审核分析报告
/trv output/招标分析报告.md --type analysis --reference 招标文件.pdf

# 审核投标大纲
/trv output/投标文件大纲.docx --type outline --reference output/招标分析报告.md

# 审核章节草稿
/trv drafts/1.3_技术方案.md --type chapter --reference output/招标分析报告.md

# 审核完整标书（投标前最终检查）
/trv drafts/完整标书.docx --type full_bid --reference 招标文件.pdf

# 审核后自动生成修订版 DOCX
/trv drafts/完整标书.docx --type full_bid --reference 招标文件.docx --level all --revise-docx --revise-scope must

# 快速检查（仅严重问题）
/trv 招标文件.docx --type tender_doc --level critical

# 仅检查某一维度
/trv 大纲.docx --type outline --reference 分析报告.md --focus scoring
```

---

## 参数速查

| 参数 | 类型 | 说明 |
|------|------|------|
| `<file>` | 文件路径 | **必选**。待审核文件（PDF/DOCX/Markdown） |
| `--type` | 字符串 | **必选**。`tender_doc` / `analysis` / `outline` / `chapter` / `full_bid` |
| `--reference` | 文件路径 | 可选但推荐。参考文件，用于对照审核 |
| `--level` | 字符串 | 可选，默认 `all`。`critical` / `high` / `all` |
| `--focus` | 字符串 | 可选。`completeness` / `compliance` / `scoring` / `risk` |
| `--revise-docx` | 开关 | 可选。审核完成后自动生成修订版 DOCX（仅对 `.docx` 输入生效） |
| `--revise-scope` | 字符串 | 可选。`must` / `all`，默认 `must` |

### 审核类型与推荐参考文件

| 审核类型 | 适用阶段 | 推荐 `--reference` |
|---------|---------|-------------------|
| `tender_doc` | 招标文件定稿 | 无需 |
| `analysis` | taa 分析后 | 招标文件.pdf |
| `outline` | 大纲生成后 | 招标分析报告.md |
| `chapter` | taw 撰写后 | 招标分析报告.md |
| `full_bid` | 投标前 | 招标文件.pdf |

### 审核级别

| 级别 | 检查范围 | 预估耗时 |
|------|---------|---------|
| `critical` | 仅严重问题 | 1-2 分钟 |
| `high` | 严重 + 一般问题 | 3-5 分钟 |
| `all` | 完整检查（默认） | 5-10 分钟 |

### 四维度审核

| 维度 | 检查重点 |
|------|---------|
| `completeness` | 章节/要素完整性 |
| `compliance` | 法规/规范符合性 |
| `scoring` | 评分标准契合度 |
| `risk` | 废标/履约/争议风险 |

---

## 输出格式

- **文件名**: `审核报告_<type>_<timestamp>.md`
- **位置**: `./output/trv/`
- **结构**: 审核结论 → 详细结果（四维度）→ 问题清单（按严重程度）→ 修改优先级
- **自动修订输出**: `./output/trv/<原文件名>_修订版_<timestamp>.docx`（启用 `--revise-docx` 且输入受支持时）

自动修订采用 **AI 驱动**模式：Claude 在审核时动态生成修订指令，Python 工具执行通用 DOCX 操作。支持段落替换（保留格式）、表格单元格替换（按表头定位）、全文替换、段落插入/删除。

降级规则：
- 输入不是 `.docx`：跳过修订，不中断审核
- 审核类型不是 `outline` / `chapter` / `full_bid`：跳过修订，不中断审核
- 部分修订指令未匹配：已匹配指令正常生效，未匹配指令在输出中列出
- 修订版编码检查失败：保留修订版文件，并提示人工处理

---

## 工作流集成

```
甲方: tpl → trv(tender_doc) → 发布招标文件
乙方: taa → trv(analysis) → trv(outline) → taw → trv(chapter) → trv(full_bid) → 投标
```

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.5.0 | 2026-04-07 | 重构为 AI 驱动智能修订，删除全部硬编码规则，支持 6 种指令类型 |
| v1.4.1 | 2026-04-07 | 新增 `--revise-docx` / `--revise-scope`，支持审核后自动生成修订版 DOCX |
| v1.3.0 | 2026-04-02 | 适配 taa v2.1-2.4 和 taw v1.8 能力更新 |
| v1.2.0 | 2026-03-13 | tender_doc 对齐 tpl v2.0（技术规格+评标办法） |
| v1.1.0 | 2026-03-10 | outline/full_bid 改为动态关系检查，移除非技术部分审核 |
| v1.0.0 | 2026-03-10 | 初始版本，5 种审核类型，4 个审核维度 |

> 审核类型详解、维度详细说明、场景范例等完整文档请参见 [SKILL.md](./SKILL.md)。
