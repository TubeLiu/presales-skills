# ppt-master

PPT Master 是 [presales-skills](https://github.com/TubeLiu/presales-skills) marketplace 中的一个 plugin，将 PDF / DOCX / URL / Markdown 等多源文档转换为**原生可编辑的 PPTX**——真正的 PowerPoint 形状、文本框、图表，不是图片。

[English](./README.md) | [中文](./README_CN.md)

<p align="center">
  <img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/hero-liziqi-colors.gif" alt="演示：端到端生成 12 页 PPT" width="860" />
</p>

<p align="center">
  <sub>↑ 一份 12 页的原生可编辑 PPT，端到端由 <a href="https://mp.weixin.qq.com/s/6ZmBl0uE3sOtD8TJcHfNAw">一个微信公众号链接</a> 生成。每一个形状、文本框、图表都可以在 PowerPoint 里直接点击编辑。</sub>
</p>

---

## 工作方式

PPT Master 是一个在 AI IDE（Claude Code / Cursor / VS Code + Copilot / Codebuddy 等）里运行的 Claude Code skill。你在对话框里描述需求——"用这份 PDF 做一份 PPT"——skill 会带 AI 走一套多阶段管线：源文档抽取 → 策略师（strategist）→ 配图 → 执行者（executor）→ 后处理 → PPTX 导出。

> 📐 **结构化配图走模板**：当某页需要 Bento grid 信息图、政策风 slide、教育图解 slide、图形摘要等结构化样式时，会自动从 ai-image 的 79 个内置模板里挑匹配项填槽位生图，比自由 prompt 输出稳定得多。

```
源文档 → 创建项目 → 选择模板 → 策略师 → [配图生成器]
  → 执行者 → 后处理 → 导出 PPTX
```

首次配置约 15 分钟；之后每做一份 PPT 约 10–20 分钟的 AI 对话。

---

## 安装（Claude Code plugin）

ppt-master 作为 `presales-skills` umbrella marketplace 的成员 plugin 分发：

```
/plugin marketplace add TubeLiu/presales-skills
/plugin install ppt-master@presales-skills
/plugin install ai-image@presales-skills        # 必需：AI 配图能力
/reload-plugins
```

安装后，内置 SKILL 会自动响应 "做 PPT" / "生成 PPT" / "做演示稿" / "make a PPT" / "generate slides" 等触发语。Claude 通过 `${CLAUDE_SKILL_DIR}/scripts/...` 调用内部脚本——**plugin 模式下你不需要手动 cd 进项目或执行下文的脚本**。

完整 marketplace 安装步骤见 umbrella [README](https://github.com/TubeLiu/presales-skills#readme)。

### 配置 AI 图片生成

直接用自然语言告诉 Claude——Claude 会自动调用 ai-image plugin 的 setup/set/validate 流程：

- "配置 ai-image" — 交互式首次配置向导
- "设置 ai-image api_keys.gemini 为 \<key\>" — Google Gemini
- "设置 ai-image api_keys.ark 为 \<key\>" — 火山方舟
- "验证 ai-image API key" — 健康检查
- "列出 ai-image 模型" — 13 后端的完整注册表

支持 13 个后端：volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter。

---

## 快速开始（安装后）

```
你：请用 <你的文件路径>.pdf 这份文件生成一份 PPT
AI：好的，先确认设计规范：
   [模板] B) 自由设计
   [格式] PPT 16:9
   [页数] 8-10 页
   ...
```

输出：两个带时间戳的文件保存到 `exports/` —— 原生形状版 `.pptx`（可直接编辑）和 `_svg.pptx` 快照版（视觉参考备份）。需要 Office 2016+。

如果 AI 中途丢失上下文，让它先读 `skills/make/SKILL.md`。

---

## 效果展示

<table>
  <tr>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_magazine_garden.png" alt="杂志风" width="400"/><br/><sub><b>杂志风</b> — 暖色调，大图排版，生活方式感</sub></td>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_academic_medical.png" alt="学术风" width="400"/><br/><sub><b>学术风</b> — 严谨结构，数据图表，论文答辩场景</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_dark_art_mv.png" alt="暗色艺术风" width="400"/><br/><sub><b>暗色艺术风</b> — 电影感深色背景，美术馆陈列感</sub></td>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_nature_wildlife.png" alt="自然风" width="400"/><br/><sub><b>自然纪录风</b> — 沉浸式摄影，简洁信息层级</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_tech_claude_plans.png" alt="科技 / SaaS 风" width="400"/><br/><sub><b>科技 / SaaS 风</b> — 白底卡片，定价表格，产品说明书</sub></td>
    <td align="center"><img src="https://github.com/TubeLiu/presales-skills/releases/download/ppt-master-assets-v1/preview_launch_xiaomi.png" alt="发布会风" width="400"/><br/><sub><b>发布会风</b> — 高对比度，参数突出，发布会感</sub></td>
  </tr>
</table>

---

## SVG 技术约束

PPT Master 用 SVG 作为中间格式，再转换为原生 DrawingML 供 PowerPoint 使用。部分 SVG 特性被禁用，因为它们无法回环到原生 PPTX 形状。完整规范见 [`CLAUDE.md`](./CLAUDE.md) 与 `skills/make/SKILL.md`。

**速查表**：

| 禁用 | 原因 | 替代方案 |
|------|------|---------|
| `mask`、`<style>`、`class`、外部 CSS、`<foreignObject>`、`textPath`、`@font-face`、`<animate*>`、`<script>`、`<iframe>` | 无 PPTX 等价物 | 用元素级独立样式 |
| `rgba()` | 无法直接映射 | `fill-opacity` / `stroke-opacity` |
| `<g opacity>` | 组级透明度无法保留 | 在每个子元素上设置 opacity |
| `<symbol>` + `<use>` | 无法正确展开 | 内联几何形状 |

**有条件允许**：`marker-start` / `marker-end`（`<defs>` 中的三角形/菱形/圆形 marker）和 `<image>` 上的 `clipPath`（单一形状子元素）—— 均可回环到原生 DrawingML。

**画布格式**：

| 格式 | viewBox |
|------|---------|
| PPT 16:9 | `0 0 1280 720` |
| PPT 4:3 | `0 0 1024 768` |
| 小红书 | `0 0 1242 1660` |
| 朋友圈 | `0 0 1080 1080` |
| Story | `0 0 1080 1920` |

---

## 文档导航

以下文档保留上游 PPT Master 项目内容，未做 presales-skills marketplace 本地化：

| 文档 | 涵盖内容 |
|------|---------|
| [`docs/zh/why-ppt-master.md`](./docs/zh/why-ppt-master.md) | 与 Gamma、Copilot 等工具的对比 |
| [`docs/zh/windows-installation.md`](./docs/zh/windows-installation.md) | Windows 用户手把手安装教程 |
| [`docs/zh/technical-design.md`](./docs/zh/technical-design.md) | 架构、设计哲学、为什么选 SVG |
| [`docs/zh/faq.md`](./docs/zh/faq.md) | 模型选择、费用、排版问题排查、自定义模板 |
| [`skills/make/SKILL.md`](./skills/make/SKILL.md) | 核心流程与规则 |

---

## 源码模式（高级）

如果你想绕开 Claude Code 直接手工跑管线脚本，详见 `CLAUDE.md` 中的完整命令参考（项目初始化、源文档转换、后处理管线）。绝大多数用户不需要此模式。

---

## 致谢

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Robin Williams](https://en.wikipedia.org/wiki/Robin_Williams_(author))（CRAP 设计原则）· 麦肯锡、BCG、贝恩

## 第三方组件

本 plugin vendor 自 [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)（MIT License © 2025-2026 Hugo He）。详细借用文件清单、相对 upstream 的改写说明以及原项目 LICENSE 全文见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
