# taw 图片获取详细规则（Phase 2A image_plan 预备）

主 SKILL.md §Phase 2A 列了"主 session 必须把 image_plan 路径预备齐"的硬性要求；本文件给图片获取的详细执行流程。

## 0. 核心原则

- 通过 `--image-source` 控制：`auto` / `local` / `drawio` / `ai` / `web` / `placeholder`
- `auto`（默认）按 H3 子节上下文独立选最适合
- 显式指定模式失败时**不降级**，直接占位符（`auto` 模式才走降级链）
- image_plan 数组每项：`{path: 绝对路径, caption: "图 X-Y 标题", placement_hint: "开头/中段/末尾"}`，空数组 `[]` = 无图

## 1. auto 模式决策（按 H3 粒度独立判断）

- 子节涉及架构/流程/部署 → 优先 `drawio`
- 子节涉及公司产品截图、已有方案、历史案例 → 优先 KB 图文共生
- 子节需要示意图/概念图/通用技术图 → 优先 `ai`
- 子节需要行业数据/第三方产品截图 → 优先 `web`
- 无法判断或均不适合 → `placeholder`

同一 H2 章节下不同 H3 可选择不同来源。

## 2. 图片规划（AI 驱动）

```
Read $SKILL_DIR/prompts/image_guidelines.yaml  # 护栏配置
```

对每个 H3 依次检查（按优先级）：

### 情况 A — KB 图文共生（MATCHED_IMAGES 非空）

Phase 1.3 Local-KB 检索已识别相关图片：

1. AI 确认图片仍与当前写作上下文相关
2. 生成动态 caption：`图 {章节号}-{序号}：{结合 H3 上下文}`
3. 解析绝对路径：`KB_ROOT / dir_name / image_ref`
4. 验证文件存在且 > 5KB
5. 去重（USED_IMAGES 集合）→ 记录 image_plan

### 情况 B — AnythingLLM 文字 + KB 图片分离

触发：`--kb-source anythingllm` 且需从 KB 取图。

1. AI 用 H3 主题查 `kb_catalog.yaml` → 选相关 KB 文档
2. Grep 主文档标题 → Read 段落 → 提取 `![](images/...)` 引用
3. AI 判断相关性 → 记录 image_plan
4. 无匹配 → 转情况 C

### 情况 C — 无 KB 匹配（AI 自主判断）

AI 按 `image_guidelines.yaml::no_kb_hints` 判断：

a. 该 H3 是否需要图片（可视化价值 / 评分影响 / 章节图片密度）
b. 需要 → 按 `IMAGE_SOURCE` 选择来源（见下方各模式）
c. 不需要 → 跳过

### 护栏（硬限制不可覆盖）

- 章节最多 8 张图
- 单个 H3 最多 1 张图
- 同章节不重复同一图片
- 跨章节不重复（GLOBAL_USED_IMAGES）
- 占位符 caption 必须具体描述需要什么图

### 强制输出（图片规划摘要）

```
[图片规划] 章节 1.4 微服务管理平台解决方案
- H3 子节数：6
- 评估结果：
  1.4.1 微服务核心能力方案 → 跳过 | "功能列表用表格更清晰"
  1.4.2 微服务治理与运营方案 → 1 张 [KB] images/abc.jpg
    caption: "图 1.4-1：微服务治理与流量调度架构"
  1.4.3 微服务监控与运维方案 → 1 张 [drawio] 待生成
    caption: "图 1.4-2：可观测性平台监控架构"
  1.4.4 应用部署与中间件方案 → 1 张 [KB] images/def.jpg
    caption: "图 1.4-3：应用部署与中间件容器化流程"
  1.4.5 集成兼容与定制开发方案 → 跳过 | "文字描述型内容"
  1.4.6 微服务迁移咨询服务方案 → 跳过 | "服务承诺类，无需图片"
- 总计：3 张（上限 8 张）
```

## 3. 各 IMAGE_SOURCE 详细流程

### IMAGE_SOURCE="auto"（默认）

```
1. 尝试 AnythingLLM 图片搜索（若 ANYTHINGLLM_AVAILABLE）
   anythingllm_search(query="{h3_title} {preferred_types[0]}", workspace=...)
   找到 → 记录，跳过下方
2. 尝试 KB 图文共生（kb_catalog → grep → read 段落 → 提 ![](images/...)）
   匹配 → 记录，跳过下方
3. 尝试 drawio（若 DRAWIO_AVAILABLE）
   Skill(skill="drawio:draw")  # 文件 > 5KB
   成功 → 记录，跳过下方
4. 尝试 AI 生图
   Skill(skill="ai-image:gen")  # 文件 > 10KB
   成功 → 记录，跳过下方
5. 占位符兜底
```

### IMAGE_SOURCE="drawio"

1. 若 `DRAWIO_AVAILABLE=false` → 提示 + 降级占位符（见 preflight.md §3）
2. `Skill(skill="drawio:draw")`，参数：图片类型 / 章节主题 / 组件流程结构 JSON；输出 `/tmp/drawio_output/<topic>_<ts>.png`（含嵌入 XML 便于回编辑）
3. 验证文件 > 5KB；成功 → 记录；失败 → 占位符（不降级）

适用：架构图 / 流程图 / 组织图等可编辑图表。

### IMAGE_SOURCE="ai"

1. `Skill(skill="ai-image:gen")` 参数：`--type / --topic / --components`；输出 `/tmp/taw_ai_img_<节号>_<i>.png`
2. 验证 > 10KB；成功 → 记录；失败 → 占位符（不降级）

跨 agent fallback（v1.0.0 已删 `image-gen` bin）：解析 ai-image plugin SKILL_DIR 后：
```bash
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" --type <类型> --topic "<主题>" --components "<组件>" --output /tmp/taw_ai_img_<节号>.png
```

### IMAGE_SOURCE="web"

1. WebSearch 找图页：`"{章节主题} {图片类型} diagram"`，中文优先英文补；过滤 icon/logo/avatar/favicon
2. 提 URL：WebFetch 拿页面提 `<img>`；失败用 curl + grep：
   ```bash
   curl -s -L "{页面URL}" --max-time 10 -A "Mozilla/5.0" | grep -oE '(src|href)="[^"]*\.(png|jpg|jpeg|svg)"' | head -5
   ```
3. 下载：
   ```bash
   curl -L -o /tmp/taw_img_{section}_{n}.png "{图片直链}" --max-time 15 -A "Mozilla/5.0"
   ```
   验证 > 5KB；成功加 `image_plan`，caption 追加 `[来源: {domain}，建议替换为自有图片]`
4. 失败 → 占位符（不降级）；每章互联网图上限 2 张

MCP 兜底（WebSearch 无果）：
- `tavily_search(query=..., search_depth="advanced", include_images=true)`
- `exa web_search_exa(query=... diagram, num_results=5)`
- 返回的图片 URL 直用，跳过步骤 2

### IMAGE_SOURCE="placeholder"

直接为所有配额位置生成占位符；记录到 image_plan（path 仍要写，docx_writer 检测文件不存在时自动转占位符段）。

## 4. 重要约束

- ❌ 任何模式都不得用文字描述代替图片
- ❌ 不得用纯文本段落模拟图表内容
- ❌ 不得使用外部 URL 直接引用图片（必须下载到本地）
- ✅ 显式指定模式失败 → 占位符（不隐式降级）
- ✅ 所有章节统一走此配额流程，无特殊处理

## 5. 主 session 与 subagent 的边界

主 session 必须在 Phase 2A **完成所有图片获取**（含 Skill 调用、Web 下载、KB 提取），把绝对路径写入 Writing Brief 的 `image_plan` 字段。

Subagent（writer.md）只负责把 `image_plan` 中每项嵌入 Markdown：`![{caption}]({path})` 至 `placement_hint` 指示的位置；**不调任何受限工具**。

Phase 2A 漏图 → 回 Phase 2A 由主 session 补，不让 subagent 自己 try（auto-deny 浪费一轮）。
