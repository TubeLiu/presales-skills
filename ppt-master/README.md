# ppt-master

PPT Master 是 [presales-skills](https://github.com/Alauda-io/presales-skills) marketplace 中的一个 plugin，将 PDF / DOCX / URL / Markdown 等多源文档转换为**原生可编辑的 PPTX**——真正的 PowerPoint shape、文本框、图表，不是图片。

[English](./README.md) | [中文](./README_CN.md)

<p align="center">
  <img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/hero-liziqi-colors.gif" alt="Demo: 12-page PPT generated end-to-end" width="860" />
</p>

<p align="center">
  <sub>↑ A 12-page natively editable deck, generated end-to-end from <a href="https://mp.weixin.qq.com/s/6ZmBl0uE3sOtD8TJcHfNAw">a single WeChat article URL</a>. Every shape, text box, and chart is clickable and editable in PowerPoint.</sub>
</p>

---

## How it works

PPT Master is a Claude Code skill that runs inside AI IDEs (Claude Code / Cursor / VS Code + Copilot / Codebuddy). You describe what you want — "make a deck from this PDF" — and the skill walks the AI through a multi-stage pipeline: source extraction → strategist → image generation → executor → post-processing → PPTX export.

```
Source Document → Create Project → Template Option → Strategist → [Image_Generator]
   → Executor → Post-processing → Export PPTX
```

First-time setup ≈ 15 minutes. Each deck ≈ 10–20 minutes of AI back-and-forth.

---

## Install (Claude Code plugin)

ppt-master is distributed as a member plugin of the `presales-skills` umbrella marketplace:

```
/plugin marketplace add Alauda-io/presales-skills
/plugin install ppt-master@presales-skills
/plugin install ai-image@presales-skills        # required: AI image generation
/reload-plugins
```

After install, the embedded SKILL automatically responds to triggers like "make a PPT" / "generate slides" / "做 PPT" / "生成演示文稿". Claude invokes the internal scripts via `${CLAUDE_SKILL_DIR}/scripts/...` — you do **not** need to `cd` into this project or run the scripts manually.

For full marketplace install steps see the umbrella [README](https://github.com/Alauda-io/presales-skills#readme).

### Configure AI image generation

Trigger ai-image plugin via natural language (Claude routes to the plugin's setup/set/validate flows):

```text
say to Claude: "configure ai-image"                              # interactive first-time setup
say to Claude: "set ai-image api_keys.gemini to <key>"           # Google Gemini
say to Claude: "set ai-image api_keys.ark to <key>"              # Volcengine ARK
say to Claude: "validate ai-image API keys"                      # health check
```

Or invoke the underlying script directly (after resolving the ai-image plugin's SKILL_DIR):

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.gemini <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate
```

13 backends supported (volcengine/ark, qwen/dashscope, gemini, openai, minimax, stability, bfl, ideogram, zhipu, siliconflow, fal, replicate, openrouter). Say "list ai-image models" (or run `ai_image_config.py models`) for the full registry.

---

## Quick start (after install)

```
You: Please create a PPT from <path-to-your-file>.pdf
AI:  Sure. Let's confirm the design spec:
     [Template] B) Free design
     [Format]   PPT 16:9
     [Pages]    8-10 pages
     ...
```

Output: two timestamped files saved to `exports/` — a native-shapes `.pptx` (directly editable) and an `_svg.pptx` snapshot for visual reference. Requires Office 2016+.

If the AI loses context mid-flow, ask it to read `skills/make/SKILL.md`.

---

## Gallery

<table>
  <tr>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_magazine_garden.png" alt="Magazine style" width="400"/><br/><sub><b>Magazine</b> — warm earthy tones, photo-rich layout</sub></td>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_academic_medical.png" alt="Academic style" width="400"/><br/><sub><b>Academic</b> — structured research format, data-driven</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_dark_art_mv.png" alt="Dark art style" width="400"/><br/><sub><b>Dark Art</b> — cinematic dark background, gallery aesthetic</sub></td>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_nature_wildlife.png" alt="Nature style" width="400"/><br/><sub><b>Nature Documentary</b> — immersive photography, minimal UI</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_tech_claude_plans.png" alt="Tech / SaaS style" width="400"/><br/><sub><b>Tech / SaaS</b> — clean white cards, pricing table layout</sub></td>
    <td align="center"><img src="https://github.com/Alauda-io/presales-skills/releases/download/ppt-master-assets-v1/preview_launch_xiaomi.png" alt="Product launch style" width="400"/><br/><sub><b>Product Launch</b> — high contrast, bold specs highlight</sub></td>
  </tr>
</table>

---

## SVG technical constraints

PPT Master generates SVG as the intermediate format, then converts to native DrawingML for PowerPoint. Some SVG features are banned because they can't round-trip to native PPTX shapes. Full reference in [`CLAUDE.md`](./CLAUDE.md) and `skills/make/SKILL.md`.

**Quick reference**:

| Banned | Why | Alternative |
|--------|-----|-------------|
| `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>` | No PPTX equivalent | Use individual element styling |
| `rgba()` | Not directly mappable | `fill-opacity` / `stroke-opacity` |
| `<g opacity>` | Group opacity collapses | Set opacity per child element |
| `<symbol>` + `<use>` | Won't expand correctly | Inline the geometry |

**Conditionally allowed**: `marker-start` / `marker-end` (triangle/diamond/circle markers in `<defs>`) and `clipPath` on `<image>` (single shape child) — both round-trip to native DrawingML.

**Canvas formats**:

| Format | viewBox |
|--------|---------|
| PPT 16:9 | `0 0 1280 720` |
| PPT 4:3 | `0 0 1024 768` |
| 小红书 (RED) | `0 0 1242 1660` |
| WeChat Moments | `0 0 1080 1080` |
| Story | `0 0 1080 1920` |

---

## Documentation

The following docs are inherited from the upstream PPT Master project and have not yet been localized for the presales-skills marketplace:

| Doc | What it covers |
|-----|----------------|
| [`docs/why-ppt-master.md`](./docs/why-ppt-master.md) | How it compares to Gamma, Copilot, and other AI tools |
| [`docs/windows-installation.md`](./docs/windows-installation.md) | Step-by-step setup for Windows |
| [`docs/technical-design.md`](./docs/technical-design.md) | Architecture, design philosophy, why SVG |
| [`docs/faq.md`](./docs/faq.md) | Model selection, cost, layout troubleshooting, custom templates |
| [`skills/make/SKILL.md`](./skills/make/SKILL.md) | Core workflow and rules |

---

## Source mode (advanced)

If you want to run the pipeline scripts manually without going through Claude Code, see `CLAUDE.md` for the full command reference (project init, source conversion, post-processing pipeline). Most users won't need this.

---

## Acknowledgments

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Robin Williams](https://en.wikipedia.org/wiki/Robin_Williams_(author)) (CRAP principles) · McKinsey, BCG, Bain

## Third-party components

This plugin is vendored from [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) (MIT License © 2025-2026 Hugo He). For the full list of borrowed files, modifications relative to upstream, and the original LICENSE text, see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
