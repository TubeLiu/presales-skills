# ppt-master

[中文](./README.md) | **English**

PPT Master is a plugin in the [presales-skills](https://github.com/TubeLiu/presales-skills) marketplace that converts multi-source documents (PDF / DOCX / URL / Markdown) into **natively editable PPTX** — real PowerPoint shapes, text boxes, and charts, not images.

> 🙏 **Upstream attribution**: This plugin is vendored from [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) (MIT License © 2025-2026 Hugo He) and adapted to the presales-skills marketplace conventions — the core pipeline, SKILL.md body, 22 built-in layouts, and script tools all follow upstream design and implementation. Thanks to Hugo He for the open-source work. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for the full borrowed-files list, change notes relative to upstream, and the original LICENSE.

---

## How it works

PPT Master is a Claude Code skill that runs inside an AI IDE (Claude Code / Cursor / VS Code + Copilot / Codebuddy, etc.). You describe what you want in chat — "make a PPT from this PDF" — and the skill walks the AI through a multi-stage pipeline: source extraction → strategist → image generation → executor → post-processing → PPTX export.

> 📐 **Structured visuals route through templates**: when a slide calls for a Bento grid infographic, policy-style slide, educational explainer, graphical abstract, etc., the system automatically picks a matching one from the 79 built-in ai-image templates and fills its slots — far more reliable than freeform prompts.

```
Source Document → Create Project → Choose Template → Strategist → [Step 4.5 User Review Gate]
  → [Image Generator] → Executor → Post-process → Export PPTX
```

First-time setup ~15 minutes; each subsequent PPT takes ~10–20 minutes of AI conversation.

---

> **Install**: see the root [README_EN.md#install](../README_EN.md#install). Once installed, the built-in SKILL auto-responds to "make a PPT" / "generate slides" / "做 PPT" / etc., and Claude calls internal scripts via `${CLAUDE_SKILL_DIR}/scripts/...` — **in plugin mode, you don't need to manually cd into the project or run the scripts shown below**.

### Configure AI image generation

Just talk to Claude in natural language — Claude will route to ai-image's setup / set / validate flows:

- "Configure ai-image" — interactive first-time setup wizard
- "Set ai-image api_keys.gemini to \<key\>" — Google Gemini
- "Set ai-image api_keys.ark to \<key\>" — Volcengine Ark
- "Validate ai-image API key" — health check
- "List ai-image models" — full registry across 13 backends

Supports 13 backends: volcengine/ark, qwen/dashscope, gemini, openai, minimax, stability, bfl, ideogram, zhipu, siliconflow, fal, replicate, openrouter.

---

## Quick start (post-install)

```
You:  Make a PPT from <your-file-path>.pdf
AI:   OK, let's confirm the design spec first:
      [template] B) Free design
      [format]   PPT 16:9
      [pages]    8-10
      ...
```

Output: two timestamped files in `exports/` — a native-shape `.pptx` (directly editable) and a `_svg.pptx` snapshot (visual reference backup). Requires Office 2016+.

If the AI loses context mid-flow, ask it to re-read `skills/make/SKILL.md`.

---

## SVG technical constraints

PPT Master uses SVG as the intermediate format, then converts to native DrawingML for PowerPoint. Some SVG features are disabled because they don't round-trip to native PPTX shapes. See [`CLAUDE.md`](./CLAUDE.md) and `skills/make/SKILL.md` for the complete spec.

**Quick reference**:

| Disabled | Reason | Alternative |
|---|---|---|
| `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>` | No PPTX equivalent | Element-level independent styles |
| `rgba()` | No direct mapping | `fill-opacity` / `stroke-opacity` |
| `<g opacity>` | Group-level opacity not preserved | Set opacity on each child |
| `<symbol>` + `<use>` | Cannot be expanded correctly | Inline the geometry |

**Conditionally allowed**: `marker-start` / `marker-end` (triangle / diamond / circle markers in `<defs>`) and `clipPath` on `<image>` (single-shape child) — both round-trip to native DrawingML.

**Canvas formats**:

| Format | viewBox |
|---|---|
| PPT 16:9 | `0 0 1280 720` |
| PPT 4:3 | `0 0 1024 768` |
| Xiaohongshu (RED) | `0 0 1242 1660` |
| WeChat Moments | `0 0 1080 1080` |
| Story | `0 0 1080 1920` |

---

## Documentation map

The following docs preserve upstream PPT Master content and are not localized to presales-skills:

| Document | Covers |
|---|---|
| [`docs/zh/why-ppt-master.md`](./docs/zh/why-ppt-master.md) | Comparison with Gamma, Copilot, etc. |
| [`docs/zh/windows-installation.md`](./docs/zh/windows-installation.md) | Step-by-step Windows install guide |
| [`docs/zh/technical-design.md`](./docs/zh/technical-design.md) | Architecture, design philosophy, why SVG |
| [`docs/zh/faq.md`](./docs/zh/faq.md) | Model choice, costs, layout troubleshooting, custom templates |
| [`skills/make/SKILL.md`](./skills/make/SKILL.md) | Core pipeline and rules |

---

## Source mode (advanced)

If you want to bypass Claude Code and run the pipeline scripts manually, see the full command reference in `CLAUDE.md` (project init, source-document conversion, post-processing pipeline). Most users don't need this mode.

---

## Acknowledgments

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Robin Williams](https://en.wikipedia.org/wiki/Robin_Williams_(author)) (CRAP design principles) · McKinsey, BCG, Bain
