# taw 章节模板加载 + 评分映射

主 SKILL.md §Phase 1.1 列了高层步骤；本文件给细节。

## 1. 读取核心模板

```
Read $SKILL_DIR/prompts/article_core.yaml
Read $SKILL_DIR/prompts/chapter_type_matcher.yaml
```

## 2. 章节类型语义匹配

输入：章节标题（如"1.3 总体方案设计"）

执行：
1. 提取章节标题中的关键词（去除编号）
2. 与 `chapter_type_matcher.yaml` 各类型的 keywords 进行语义匹配
3. 计算匹配度（关键词交集数 / 总关键词数）
4. 选匹配度最高的类型；若 < 0.6 → LLM 语义理解兜底
5. 输出：`business / technical / service / commitment` + 置信度

示例：
- "1.3 总体方案设计" → technical（0.90）
- "1.5 实施方案与计划" → technical（0.92）
- "1.10 售后服务方案" → service（0.92）
- "1.11 培训方案" → service（0.95）
- "1.4.2 容器编排与集群管理方案" → technical（0.85）

## 3. 加载章节模板 + 提取写作指南

```
Read $SKILL_DIR/prompts/article_templates/{chapter_type}.yaml
```

匹配 section_type（按章节标题关键词与 `semantic_keywords` 匹配），提取：
- `word_count`（字数；若 `WORD_OVERRIDE[2]` 非空则覆盖）
- `content_elements`（内容要素）
- `kb_priority`（KB 优先级）
- `image_types`（图片类型）
- `scoring_alignment`（评分对齐，如有）

## 4. 图片配额

```
Read $SKILL_DIR/prompts/chapter_image_quota.yaml
```

按 section_type 查 `chapter_image_quota[section_type]`：
- 找到 → 取 `quota`/`required`/`image_types`
- 未找到 → 用 `defaults[chapter_type]`
- 若 `IMAGE_OVERRIDE[2]` 非空 → 覆盖 `quota`

示例：
```yaml
training_service:
  quota: 1
  required: 1
  image_types: [培训体系图, 培训路径图]
```

## 5. 评分映射（M4）

从 M4 提取与目标章节相关的评分项，构建表：

| 评分项 ID | 名称 | 分值 | 评分规则 | {VENDOR_NAME} 优势 | 拿高分策略 |
|---|---|---|---|---|---|

标注 ≥10 分项为**重点展开**项。

## 6. 章节类型表（一、技术部分；taw 核心）

| 子章节 | 重点内容 | KB 检索 | 关键输入 |
|---|---|---|---|
| 1.1 技术偏离表 | 逐条对应 M2 技术要求，标注正偏离/无偏离 | 不检索 | M2 全部技术要求 |
| 1.2 项目理解与需求分析 | 体现对需求的深度理解，分析现状与痛点 | 不检索 | M1 + M2 |
| 1.3 总体方案设计 | 架构设计、技术路线，突出 {VENDOR_NAME} 核心产品能力 | solutions | M2 + M4 技术评分项 + M7 亮点 |
| 1.4 专项响应章节 | 与大纲动态章节一一对应 | solutions + cases | M2 必须条款 + M4 高分评分项 |
| 1.5 实施方案与计划 | 里程碑与 M3 工期一致 | cases | M3 交付要求 |
| 1.6 质量保障方案 | 质量管理体系、测试策略 | 不检索 | M3 验收标准 |
| 1.7 安全方案 | 安全架构、等保合规 | solutions | M2 安全要求 + 行业扩展 |
| 1.8 国产化适配方案 | 信创适配（如有信创要求） | solutions | M2 国产化要求 + E2 |
| 1.9 项目团队与人员配置 | 团队架构、核心岗位职责 | 不检索 | M3 人员要求 |
| 1.10 售后服务方案 | 质保/运维/响应/增值服务 | solutions | M3 质保运维 + M4 服务评分项 + M7 差异化亮点 |
| 1.11 培训方案 | 培训计划、内容、方式、考核 | 不检索 | M3 培训要求 + M4 培训评分项 |

写作规则：
- 专业深入、方案导向
- M7 差异化亮点在对应章节显著位置融入
- M2 必须条款须有明确技术响应
- 架构设计需体现 {VENDOR_NAME} 核心产品能力
- 性能指标 / 技术参数引用 M2 原文要求，响应方案给具体数值
- 1.10 售后：SLA 与响应时间标注 `[待商务确认]`，与 M3 逐条呼应
- 1.11 培训：覆盖内容/方式/考核，与 M3 培训要求对应
