# Overflow Fallback (Step 6.5)

> SKILL.md `### Step 6.5` 的详细规范文档。文字超出布局容量时，**必须**走 speaker notes，**严禁**缩字号或写画布外。

## Table of Contents

- [5 条禁令与后果](#5-条禁令与后果)
- [Speaker notes 写入路径](#speaker-notes-写入路径)
- [5 个版式下的溢出表现差异](#5-个版式下的溢出表现差异)
- [svg_quality_checker 第 5 维 proxy 行为说明](#svg_quality_checker-第-5-维-proxy-行为说明)

---

## 5 条禁令与后果

### ❌ 禁令 1：缩小字号

- **后果**：违反 `spec_lock.md` 的 `font_family/sizes` 锁定值；下游所有页面字号一致性被破坏；导出 PPTX 后用户看到字号不齐
- **正确做法**：把溢出段移入 `notes/total.md` 对应 H1 段（详见下方 §Speaker notes 写入路径）

### ❌ 禁令 2：缩小行高 / 压缩 padding

- **后果**：行高 / padding 也是 spec_lock 锁定值；压缩后视觉拥挤、PPT 客户端缩放时易出现文字重叠
- **正确做法**：同禁令 1，走 speaker notes

### ❌ 禁令 3：写到画布外（viewBox 外）

- **后果**：viewBox 外的内容在 SVG 渲染时**仍然被裁切**，导出 PPTX 后看不到；preview 工具可能误显示，造成"开发预览正常、生产环境截断"的诡异 bug
- **正确做法**：走 speaker notes；如果是必须可见的关键信息，回 Step 4 拆页

### ❌ 禁令 4：拆成两页但不更新 page_count

- **后果**：`design_spec.md` 的 `page_count` 与实际 SVG 数量对不上；`total_md_split.py` 按 page_count 分配 notes 时映射错位；后处理三步统计出错
- **正确做法**：拆页前必须回 Step 4.5 更新 `design_spec.md` page_count + 重新经过用户复核 Gate

### ❌ 禁令 5：把 H1 / H2 / 关键 bullet 移入 notes

- **后果**：speaker notes 是给主讲人看的"补充说明"，不是"被裁的正文"；把核心信息（标题 / 关键 bullet）移入 notes 等于让用户看不到
- **正确做法**：核心信息必须留在画布内；只能把"次要展开 / 旁注 / 数字来源 / 引用细节"移入 notes

---

## Speaker notes 写入路径

### 写入位置

**`<project_path>/notes/total.md`**，按 H1 标题分段映射到对应 page。

### 与 total_md_split.py 的对齐

`scripts/total_md_split.py` 中 `parse_total_md` 函数支持 H1 / H2 / H3 标题切分，**但溢出 fallback 推荐使用 H1**——理由：

- H1 与 `design_spec.md` 中 page 的 H1 对齐，映射唯一无歧义
- H2 / H3 在多页场景下可能跨 page 重复，映射会回退到最近 H1
- `scripts/svg_to_pptx/pptx_builder.py` 中 `create_pptx_with_native_svg(notes=...)` 参数按 SVG 文件名 stem 读取 `notes/total.md` 切分结果，H1 是它的天然边界

### 写入示例

`design_spec.md` 中：
```markdown
## Page 3: 市场机会与规模
- 全球 SaaS TAM $1.2T（来源：Gartner 2024）
- 增长率 CAGR 18%
- 重点细分：HR Tech / FinOps / DevTools
```

如果某条来源说明（"来源：Gartner 2024 Q3 Market Share Report, p.42"）写满会让画布超容，把它移入 `notes/total.md`：

```markdown
# 市场机会与规模

来源细节：Gartner 2024 Q3 Market Share Report, p.42。
HR Tech 数据采纳 IDC 交叉验证，CAGR 18% 已扣除汇率波动 ±2%。
DevTools 细分剔除了 IDE-only 厂商。
```

H1 = `市场机会与规模` 与对应 SVG 文件名 stem（如 `slide_03_市场机会与规模.svg`）匹配 → 自动映射到该 page 的 speaker notes。

> ⚠️ **映射前提**：`total_md_split.py` 按 SVG 文件名 stem（exact / normalized substring / leading-number 模糊匹配）映射 H1，**不是按 design_spec.md 的 Page 序号**。如果 SVG 命名是 `slide_03.svg` / `p3.svg` / `cover.svg` 等不含 H1 文本的纯编号，请把 `notes/total.md` 的 H1 改用 SVG 文件名 stem（最稳）。如果 H1 与 SVG stem 都不匹配，notes 会被静默 drop（仅 stderr 提示 unmatched_headings）。

---

## 5 个版式下的溢出表现差异

不同 viewBox 容量决定了"多少字会溢出"，**不设硬阈值**。

| 版式 | viewBox | 典型容纳 | 溢出表现 |
|---|---|---|---|
| PPT 16:9 | `0 0 1280 720` | 中文 ~250 字 / 英文 ~400 词（22pt 正文）| 横向溢出最常见，宽度先碰边 |
| PPT 4:3 | `0 0 1024 768` | 中文 ~280 字 / 英文 ~450 词 | 接近 16:9，但稍能多塞一行 |
| 小红书 (RED) | `0 0 1242 1660` | 中文 ~600 字 / 英文 ~900 词 | 纵向长，溢出常出现在底部 |
| 朋友圈 (Moments) | `0 0 1080 1080` | 中文 ~400 字 / 英文 ~600 词 | 正方形对密集文字最不友好 |
| Story | `0 0 1080 1920` | 中文 ~650 字 / 英文 ~1000 词 | 极长纵向，但需要 hero 视觉占大量空间，文字预算其实接近 RED |

> 容纳数字是 **典型估算**（22pt 中文正文 / 22pt 英文正文 / 默认行高 1.5），实际取决于 spec_lock.md 锁定的字号 + 是否有侧栏 / 装饰元素。**不要把表中的数字当硬阈值**——以 svg_quality_checker 第 5 维 warning 为准 + AI 自查兜底。

---

## svg_quality_checker 第 5 维 proxy 行为说明

### 第 5 维实际检查的是什么

`svg_quality_checker.py` 第 5 维「文本换行」检测的是**「页面用了哪些换行机制」**，不是「文字实际是否溢出」。具体：

- 扫描 SVG 中所有 `<text>` 元素
- 报告它们用了 `<tspan>` 多行 / `textLength` 压缩 / 或纯单行 `<text>`
- 在 `<tspan>` 数量 / 单元素字符数异常时给 warning

### 为什么这是 proxy 而非直接检测

直接检测"是否溢出"需要：
- 解析 spec_lock.md 字号
- 解析 viewBox 容量
- 模拟字体度量（不同 OS 的 fallback 字体宽度不同）
- 计算每个 `<text>` 实际渲染宽高 vs 父容器边界

这套 pipeline 在 svg_quality_checker 当前实现里没做（避免引入字体度量库依赖）。换行机制是**经验上与溢出强相关**的信号——多行 `<tspan>` 多 = 多半在塞文字。

### False negative 的常见场景

第 5 维 **不会** 报警但实际溢出的场景：
1. 单 `<text>` 元素塞了超长字符串，没用 `<tspan>` 拆行 → 第 5 维认为"用了单行"，不报警；但实际超出画布宽度
2. `<tspan>` 数量正常但每个 `<tspan>` 都很长 → 总量超容
3. 文字在 viewBox 边界外但被 svg renderer 裁切静默 → 静态扫不到

### AI 自查兜底协议

第 5 维 false negative 时，AI 必须在 Step 6.5 阶段对每个 page 自查：

1. 数一下该 page 中文字数 / 英文词数（`<text>` 内 textContent 总和）
2. 对照本节 §5 个版式表的"典型容纳"判断是否危险
3. 危险 → 按 5 条禁令处置（默认走 notes）
4. 如果不确定，**保守地按"危险"处理**（走 notes 永远比"被截断"安全）

### 与 Step 7.0 入口 lint 的关系

第 5 维属于 7 维全检（Step 6 Quality Check Gate），**不**在 Step 7.0 入口 `--lint` 的 3 维子集内。原因：第 5 维需要 spec_lock.md 上下文，前置 lint 阶段还没生成 spec_lock。Step 6.5 自查已经覆盖该维度的判断责任。
