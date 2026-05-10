# Design Review Gate (Step 4.5)

> SKILL.md `### Step 4.5` 的详细规范文档。Strategist 完成九项确认后必须输出 `design_review.md` 并暂停等待用户确认才能进入 Step 5。本步骤还顺带捕获 Step 4.5 ⑤ 配音决策——避免到 Step 7 export 时才 ad-hoc 询问用户。

## Table of Contents

- [何时触发](#何时触发)
- [design_review.md 5 项产物详解](#design_reviewmd-5-项产物详解)
- [用户回复判定](#用户回复判定)
- [Gate 状态文件写入](#gate-状态文件写入)
- [边界 case](#边界-case)
- [与 spec_lock.md / design_spec.md 的引用关系](#与-spec_lockmd--design_specmd-的引用关系)

---

## 何时触发

- **进入条件**：Step 4 Strategist Phase 完成；九项确认通过且 `<project_path>/.gates/nine_confirmations.json` 中 `passed: true`；`design_spec.md` + `spec_lock.md` 已生成
- **退出条件（GATE 通过）**：用户回复明确确认词（"确认" / "OK" / "continue" / "👍" 等，参见 SKILL.md §Step 4 末尾 "User reply contract — explicit gate" 表格），且 Strategist 已写入 `.gates/design_review.json` 与 `.gates/audio_choice.json` 两份 gate 文件
- **不触发**：Strategist 还在做九项确认中 / 用户尚未回复 / 用户已开始改方案

---

## design_review.md 5 项产物详解

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

### ④ 质量样张轮换页

**字段**：从 `spec_lock.md ## quality_samples` 摘出 3 张非结构页，列出页码、page intent、density 和本轮检查理由。若模板包提供 `templates/human_quality_rubric.json`，样张选择必须遵循其中的 `qualitySampleRotation`。

**目的**：避免陷入反复修改同一张 SVG。用户确认方案后，Executor 仍生成完整 deck，但质量复盘优先看这 3 张轮换样张，覆盖不同页型与信息密度。

**示例**：
```markdown
## 质量样张轮换页

- **P03 架构分层**: `architecture_stack | dense_technical` — 检查层级关系、标签可读性、侧栏证据密度
- **P05 对象映射**: `mapping_table | dense_technical` — 检查表格紧凑度、术语短标签、状态提示
- **P07 迁移路径**: `migration_bridge | balanced_technical` — 检查 before/bridge/after 视觉逻辑
```

**反模式**：
- ❌ 每轮都选同一页作为样张
- ❌ 只选最容易做漂亮的低密度页
- ❌ 把样张机制理解成"只生成这几页"
- ❌ 在技能优化时一直改同一张 SVG，而不是回到 route / visual system / checker 改能力

### ⑤ 配音 / 音频策略

⛔ **MUST — 不可省略本节，即使用户原始命令未提及配音**。默认值（`audio_mode: edge_default`）由 ⑤ 项明确呈现给用户后决定，不是由 AI 自行假设；「沉默 ≠ 不要音频」，沉默是「AI 漏问 ⑤ 项」的失效模式。`scripts/audio_decision_validator.py` 在 design_review.md 输出后立即跑校验，⑤ 项缺失或 `.gates/audio_choice.json` 缺失会直接 exit 1 阻断 Step 4.5 通过。

**字段**：`audio_mode` 必填，取值 `none | edge_default | cloud_quality | recorded_existing`；`cloud_quality` 时额外要求 `provider`（`elevenlabs` / `minimax` / `qwen` / `cosyvoice`）和 `voice_preference`（自然语言描述，如「沉稳男声 / 商务女声 / 轻快 narrator」）。

**目的**：把"生成 PPT 之后是否要配音 / 用什么 provider"这个决策从 Step 7 之后的散场询问提前到 Step 4.5——这样 Step 7.3 可以直接读 `.gates/audio_choice.json` 决定是否串入 `notes_to_audio.py`，弱模型也无法因为"没人主动问 audio"就漏掉。

**真实失效观察（v1.6.0 plan context）**：用户在初次命令中明说"生成有配音的版本"，但流程中 AI 仍未停下来让用户选音频选项 → 直接进 Step 7 export 时才意识到。根因：⑤ 项是 design_review.md 的一个 section，在长上下文 + 多 section 同时输出时容易漏写。`audio_decision_validator.py` 把"漏写 ⑤ 项"从"AI 自觉"变成"机器拦截"。

**示例**：

```markdown
## 配音 / 音频策略

- **audio_mode**: `edge_default`（推荐：免 API key、本地 edge-tts 引擎，适合内部 demo / 临时录课）
- 备选项：
  - `none` — 不需要配音，纯 PPTX
  - `cloud_quality` — 高保真，需要 provider key（elevenlabs/minimax/qwen/cosyvoice）+ 音色偏好
  - `recorded_existing` — 已有人工录音文件放在 `<project_path>/audio/`，直接 embed
- 我会按 `edge_default` 准备，如果你想换说一声。
```

**反模式**：
- ❌ 在 design_review.md 把 5 个 provider 全列一遍要用户选——`edge_default` 是合理默认，单句兜底即可
- ❌ 跳过本节直接默认 `none`——会让用户在 Step 7 突然被问"要不要配音"，破坏 Step 4.5 单点确认契约
- ❌ 写 `audio_mode: maybe` / 留空——必须落到 4 个枚举之一，否则 `audio_choice.json` 无法持久化

**默认建议规则**：
- 内部 demo / 给同事预演 → `edge_default`
- 客户高管演示 / 朋友圈分发 / 视频号成片 → `cloud_quality`
- 已有播客 / 课程录音 → `recorded_existing`
- 现场口讲、不需要预录 → `none`

---

## 用户回复判定

> **复用 SKILL.md §Step 4 末尾 "User reply contract — explicit gate" 表格，不重复列**。

简化要点：
- ✅ 明确确认词（确认 / OK / 通过 / continue / 👍 / 同意 / 没问题）→ 写 `.gates/design_review.json` 与 `.gates/audio_choice.json`，进 Step 5
- ❌ 模糊正面词（嗯 / 差不多 / 看起来还行 / 应该可以）→ **不算确认**，必须 re-ping，**不写**任何 gate 文件
- ❌ 修改意见（改一下 X / 多一页 / 换模板 / 重做大纲 / 改 audio_mode）→ 回 Step 4 调整 9 项确认 → 重新输出 `design_review.md`，覆盖原 gate 文件为 `passed: false`
- ❌ 用户长时间未回复 → **AI 永不主动推进**，下次 AI 输出时优先追问；gate 文件保持缺失状态

---

## Gate 状态文件写入

Strategist 在用户明确确认后**必须**写两份 JSON，schema 同 `.gates/nine_confirmations.json`（参见 SKILL.md Step 4 user reply contract 表第一行）：

**`<project_path>/.gates/design_review.json`**：
```json
{
  "passed": true,
  "verdict": "explicit_confirmation",
  "user_reply_snippet": "确认，按方案走",
  "items_locked": [
    "template:alauda",
    "pages:12",
    "image_triggers:[P1, P3]",
    "quality_samples:[P03, P05, P07]"
  ],
  "timestamp": "2026-05-10T12:34:56Z"
}
```

**`<project_path>/.gates/audio_choice.json`**：
```json
{
  "passed": true,
  "verdict": "explicit_confirmation",
  "audio_mode": "edge_default",
  "provider": null,
  "voice_preference": null,
  "user_reply_snippet": "确认 + 用 edge 默认配音",
  "timestamp": "2026-05-10T12:34:56Z"
}
```

`audio_mode == "cloud_quality"` 时填 `provider` 与 `voice_preference`；`none` 时这两字段为 `null`，但 `passed: true` 仍要写——它表示"用户决定 = 不要音频"，而不是"用户没说"。

下游 Step 5 / Step 6 / Step 7 的 GATE block 都会跑 `gate_check.py --require <gates>`，缺文件或 `passed: false` 直接阻断。

---

## 边界 case

### 1. 用户改主意（已确认后又想改）

如果用户已经回复确认、AI 已进入 Step 5 / Step 6，但用户随后又想改方案：
- 立即停止当前阶段（如 Image_Generator 中途、Executor 写到一半）
- 回到 Step 4 重做九项确认（不是改 design_review.md，是从源头重做）；同时把 `.gates/nine_confirmations.json` 与 `.gates/design_review.json` 都覆盖为 `passed: false`，让下游 GATE 重新阻塞
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
design_spec.md       ←── Strategist 九项确认的"完整方案"（每页详细 bullet）
       ↓
  spec_lock.md      ←── Strategist 锁定的"执行决策"（颜色 / 字体 / 图标 / page_rhythm / quality_samples）
       ↓
design_review.md     ←── 给用户复核的"摘要视图"（4 项：模板 / 大纲 / 图片预算 / 质量样张）
       ↓
   user confirm
       ↓
  Step 5 / Step 6    ←── 凭 spec_lock.md 执行（design_review.md 自此是历史档案）
```

**关键约定**：
- `design_review.md` 是 `design_spec.md` + `spec_lock.md` 的**摘要**，**不是**第三份独立 spec
- 用户确认后，`design_review.md` 是历史档案；Step 5 / Step 6 的脚本只依赖 `spec_lock.md` / `design_spec.md`（用户可手动 Read 回看 design_review.md，但工作流不再引用它）
- 用户改主意触发的"重做"必须从 `design_spec.md` + `spec_lock.md` 重做，不能只改 `design_review.md`
