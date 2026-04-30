# Design Review Gate (Step 4.5)

> SKILL.md `### Step 4.5` 的详细规范文档。Strategist 完成八项确认后必须输出 `design_review.md` 并暂停等待用户确认才能进入 Step 5。

## Table of Contents

- [何时触发](#何时触发)
- [design_review.md 3 项产物详解](#design_reviewmd-3-项产物详解)
- [用户回复判定](#用户回复判定)
- [边界 case](#边界-case)
- [与 spec_lock.md / design_spec.md 的引用关系](#与-spec_lockmd--design_specmd-的引用关系)

---

## 何时触发

- **进入条件**：Step 4 Strategist Phase 完成；八项确认通过；`design_spec.md` + `spec_lock.md` 已生成
- **退出条件（GATE 通过）**：用户回复明确确认词（"确认" / "OK" / "continue" / "👍" 等，参见 SKILL.md §Step 4 末尾 "User reply contract — explicit gate" 表格）
- **不触发**：Strategist 还在做八项确认中 / 用户尚未回复 / 用户已开始改方案

---

## design_review.md 3 项产物详解

### ① 选定模板 + 简短理由

**字段**：模板 ID + 一句话理由（cross-link `templates/layouts/layouts_index.json` 中本模板 entry 的 `summary` 字段）

**示例**：
```markdown
## 选定模板

- **Template**: `mckinsey`
- **Summary（取自 layouts_index.json）**: McKinsey-style template for strategic consulting decks, executive briefings...
- **本项目匹配理由**：源文档主题为 SaaS 商业化战略评估，目标受众是客户高管 → 命中 mckinsey 的「外部客户 / 高管」定位；不选 exhibit 是因为本方案是 narrative-driven 而非 data-dump
```

**反模式**：
- ❌ 仅写"用 mckinsey"不给理由
- ❌ 把 summary 全文复述一遍（应该只引用关键短语）
- ❌ 自创理由文字而不引用 layouts_index.json 既有 summary

### ② 页数 + 一级大纲

**字段**：页数总量 + 每页 H1（不含 bullet 细节）

**示例**：
```markdown
## 页数与一级大纲（共 12 页）

1. 封面：标题 + 副标题 + 团队署名
2. 执行摘要 (Executive Summary)
3. 市场机会与规模
4. 竞品对比矩阵
...
12. Q&A / 致谢
```

**反模式**：
- ❌ 写每页 5 个 bullet 细节（应该在 design_spec.md，不在 review）
- ❌ 不写页数总量（让用户回头数）
- ❌ 把封面 / 致谢 / Q&A 拼一起算一页

### ③ Image_Generator 触发列表

**字段**：哪些页需要 AI 生图 + 每张图的角色（hero / decoration / diagram）+ 大致 prompt 方向（不必完整 V2 四段式，那是 Step 5 的事）

**示例**：
```markdown
## Image_Generator 触发列表

- **P1 封面**: hero image, 简洁深色科技调性，推荐 anthropic / google_style provider
- **P3 市场机会**: decoration, 抽象增长曲线视觉，可低成本 provider
- **P12 致谢**: 不需要，复用 P1 hero 缩略

总触发数 2 张图。预算评估：~$0.5（按 anthropic 1K 1024px）
```

**反模式**：
- ❌ 把 V2 四段式 prompt 全写在这里（Step 5 才需要）
- ❌ 漏写"不触发的页面"（用户会以为每页都要图）
- ❌ 不给预算评估（用户无法判断要不要砍图）

---

## 用户回复判定

> **复用 SKILL.md §Step 4 末尾 "User reply contract — explicit gate" 表格，不重复列**。

简化要点：
- ✅ 明确确认词（确认 / OK / 通过 / continue / 👍 / 同意 / 没问题）→ 进 Step 5
- ❌ 模糊正面词（嗯 / 差不多 / 看起来还行 / 应该可以）→ **不算确认**，必须 re-ping
- ❌ 修改意见（改一下 X / 多一页 / 换模板 / 重做大纲）→ 回 Step 4 调整 8 项确认 → 重新输出 `design_review.md`
- ❌ 用户长时间未回复 → **AI 永不主动推进**，下次 AI 输出时优先追问

---

## 边界 case

### 1. 用户改主意（已确认后又想改）

如果用户已经回复确认、AI 已进入 Step 5 / Step 6，但用户随后又想改方案：
- 立即停止当前阶段（如 Image_Generator 中途、Executor 写到一半）
- 回到 Step 4 重做八项确认（不是改 design_review.md，是从源头重做）
- 把已生成的 SVG / 图片归档到 `<project_path>/archive/` 而不是删除（保留沉没成本可视化）
- 重新输出 design_review.md → 再次 Gate

### 2. 模糊正面词不算确认

| 用户回复 | 判定 | 处理 |
|---|---|---|
| "确认" / "OK" / "通过" | ✅ 确认 | 进 Step 5 |
| "👍" / "🙆" / "好的" | ✅ 确认 | 进 Step 5 |
| "嗯" / "知道了" | ❌ 模糊 | re-ping："请明确回复确认 / 修改 / 取消" |
| "差不多吧" / "还行" | ❌ 模糊 | re-ping |
| "可以吗？" / "你怎么看？" | ❌ 反问 | 回答 + 再要求确认 |
| 长时间无回复 | ❌ 等待 | AI 永不主动推进，下次轮到 AI 输出时优先追问 |

### 3. AI 永不主动推进的工程理由

AI 没有真实计时能力，不能"5 分钟后超时自动推进"。任何"超时旁路"都是借口。下次轮到 AI 输出时（无论是用户其他指令还是会话恢复），优先重新追问 design_review.md 是否已确认，而不是假装收到确认就推进。

---

## 与 spec_lock.md / design_spec.md 的引用关系

```
design_spec.md       ←── Strategist 八项确认的"完整方案"（每页详细 bullet）
       ↓
   spec_lock.md      ←── Strategist 锁定的"执行决策"（颜色 / 字体 / 图标 / page_rhythm）
       ↓
design_review.md     ←── 给用户复核的"摘要视图"（3 项：模板 / 大纲 / 图片预算）
       ↓
   user confirm
       ↓
  Step 5 / Step 6    ←── 凭 spec_lock.md 执行（design_review.md 自此是历史档案）
```

**关键约定**：
- `design_review.md` 是 `design_spec.md` + `spec_lock.md` 的**摘要**，**不是**第三份独立 spec
- 用户确认后，`design_review.md` 是历史档案；Step 5 / Step 6 的脚本只依赖 `spec_lock.md` / `design_spec.md`（用户可手动 Read 回看 design_review.md，但工作流不再引用它）
- 用户改主意触发的"重做"必须从 `design_spec.md` + `spec_lock.md` 重做，不能只改 `design_review.md`
