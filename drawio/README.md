# drawio plugin — Draw.io 图表生成

**中文** | [English](./README_EN.md)

通过自然语言生成 `.drawio` XML 文件，可选导出 PNG / SVG / PDF / JPG（依赖 draw.io desktop CLI）。

## Slash 入口

| 触发方式 | 形式 |
|---|---|
| Claude Code canonical | `/drawio:draw "GitOps 蓝绿发布架构图"` |
| Codex / Cursor / OpenCode 短形式 alias | `/draw "..."` |
| 自然语言 auto-trigger | "画一张架构图：用户 → 网关 → 微服务" / "draw a flowchart of X" / "生成 ER 图" 等 |

## 6 种 diagram preset

| Preset | 适用场景 |
|---|---|
| **ERD** | 数据库实体关系（实体、属性、外键）|
| **UML class** | 类图（类、接口、继承、组合）|
| **Sequence** | 时序图（actor、生命线、消息）|
| **Architecture** | 系统架构（layer / tier / 组件分组，layered 风格）|
| **ML / DL** | 神经网络模型（含 tensor shape `(B, C, H, W)` 标注，适合 NeurIPS/ICML/ICLR 论文风格）|
| **Flowchart** | 流程图（start / decision / process / end）|

每种 preset 自带形状库 / 颜色 / 布局约定。Animated connectors（`flowAnimation=1`）支持数据流 / pipeline 可视化（在 SVG 与 draw.io desktop 中可见）。

## Style presets（v1.3+）

支持从 `.drawio` 文件 / 截图 反推出视觉风格保存为 named preset，未来调用时统一应用：

```
> 学习这个 .drawio 文件的风格，保存为 'corporate-blue'
> 用 corporate-blue 风格画一张服务网格架构图
> 列出我有哪些 style preset
> 把 corporate-blue 设为默认
```

内置 3 个 preset：`default` / `corporate` / `handdrawn`（位于 `skills/draw/styles/built-in/`）。用户自定义 preset 存于 `~/.drawio-skill/styles/`（持久化于 vendor sync）。

## 自定义 output dir（v1.4+）

```
> 把图导出到 ./artifacts/
> 输出到 docs/images/
```

skill 自动 `mkdir -p` 目标目录后导出。适合 CI/CD artifact pipeline。

## 安装 draw.io CLI

```bash
# macOS（Homebrew）
brew install --cask drawio

# 跨平台（npm）
npm install -g @drawio/drawio-desktop-cli

# Linux（含 xvfb headless support）
# 见 https://github.com/jgraph/drawio-desktop/releases
```

CLI 不可用时，本 skill 自动降级为 **browser fallback**：生成 diagrams.net URL（base64-encoded XML），用户在浏览器打开即可编辑。

## 与其它 plugin 协作

- **drawio**：架构图 / 流程图 / 时序图 / ER 图（结构化、几何图形）
- **ai-image** `/ai-image:gen`：概念图 / 插画 / 截图 / 配图（自由风格、AI 生成）
- **solution-master** 内部按章节语义自动选型（架构图走 drawio，封面 / 概念图走 ai-image）

## 限制

- 导出 PNG/SVG/PDF/JPG **不内嵌 XML metadata** — 用户必须保留 source `.drawio` 文件以便后续编辑（双击 PNG 不能直接在 draw.io 打开）
- Self-check（vision-based）需 vision-enabled 模型（Claude Sonnet/Opus 等）；不支持时 gracefully skip
- ML 模型图的 tensor shape 标注遵循 PyTorch 风格 `(B, C, H, W)` 约定

## 第三方组件

本 plugin 的 SKILL.md / references / styles / assets vendor 自 [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) v1.4.0（MIT License）。详细借用清单、改写说明与原项目 LICENSE 见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
