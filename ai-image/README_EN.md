# ai-image — Unified AI Image Generation

[中文](./README.md) | **English**

A **shared plugin** in the `presales-skills` marketplace, providing unified AI image generation for solution-master / ppt-master / tender-workflow. 13 backends share one model registry and configuration; bundled with 79 structured prompt templates covering 17 high-density visual scenarios.

> 🙏 **Upstream attribution**: the 79 structured prompt templates under `templates/` are sourced from [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) gpt-image-2 (MIT License), covering high-density scenarios — PPT slides / infographics / UI mockups / academic figures / technical diagrams / posters. This repo adapts the directory layout, naming, and integration to the ai-image plugin; the core prompt content follows upstream design. License at [`skills/gen/templates/LICENSE-gpt-image-2`](./skills/gen/templates/LICENSE-gpt-image-2).

---

## Core capabilities

- **Unified call across 13 backends**: volcengine/ark · qwen/dashscope · gemini · openai · minimax · stability · bfl · ideogram · zhipu · siliconflow · fal · replicate · openrouter
- **Shared model registry**: `prompts/ai_image_models.yaml` defines every provider × model with ID / price / resolution / features; adding a model requires editing one place only
- **79 structured templates (17 categories)**: auto-match high-density visual scenarios; each template confirms slot values before generating, far more stable than freeform prompts
- **OpenAI backend exclusive**: transparent-background PNG (logo / icon cutout), webp/jpeg custom-compression output, image editing (inpainting, with optional mask for partial repaint)
- **Unified configuration**: all API keys and defaults centralized in `~/.config/presales-skills/config.yaml`, shared by the three main plugins, no duplication

## Slash entry points

| Trigger | Form |
|---|---|
| Claude Code canonical | `/ai-image:gen "modern minimalist container cloud architecture"` |
| Codex / Cursor / OpenCode short alias | `/image-gen "..."` |
| Natural language auto-trigger | "generate image: xxx" / "make an illustration" / "draw an architecture diagram" / "做一张配图" |
| Structured-scenario auto-trigger | "make a Bento grid infographic" / "PPT visual" / "ER diagram" / "academic graphical abstract" → auto-routes through `templates/` |
| Image editing | "replace the background with blue sky and clouds" / "partial repaint / remove element" → auto-routes through OpenAI inpainting (`--mode edit`) |
| Management sub-commands | "configure ai-image" / "first-time setup" / "validate api key" / "list image models" / "add custom model" |

## 17 built-in template categories

| Category | Use case | Used by main plugin |
|---|---|---|
| `slides-and-visual-docs/` | Dense explainer slides / educational slides / policy-style slides / visual reports | ppt-master |
| `infographics/` | Bento grid / KPI dashboard / comparison infographics / step-by-step | solution-master / ppt-master |
| `ui-mockups/` | Chat UI / short-video covers / live commerce UI / social UI | tender-workflow / solution-master |
| `academic-figures/` | Graphical abstracts / neural network architecture / paper figures / method flowcharts | solution-master |
| `technical-diagrams/` | ER / flowchart / sequence / state machine / system architecture / network topology (PNG, raster; for editable use drawio) | solution-master |
| `maps/` | Food map / travel route / illustrated city map / store distribution | Generic |
| `poster-and-campaigns/` | Posters, campaign banners | Generic |
| `product-visuals/` | Product photography, studio shots | Generic |
| `branding-and-packaging/` | Brand packaging | Generic |
| `portraits-and-characters/` | Portraits, character art | Generic |
| `avatars-and-profile/` | Avatars, profile pictures | Generic |
| `editing-workflows/` | Image-editing workflows | Generic |
| `grids-and-collages/` | Grids / collages | Generic |
| `scenes-and-illustrations/` | Scene illustrations | Generic |
| `storyboards-and-sequences/` | Comic panels / sequential storyboards | Generic |
| `typography-and-text-layout/` | Typography / text layout | Generic |
| `assets-and-props/` | Props, assets | Generic |

Each template `.md` file contains the visual layer structure + `{argument name="..." default="..."}` slots + missing-field question priority.

## Configuration

> **Install**: see the root [README_EN.md#install](../README_EN.md#install).

After install, configure via natural language:

```
> Configure ai-image                          # Interactive first-time setup wizard
> Set ai-image api_keys.ark to sk-xxx
> Validate ai-image API key                   # Health check
> List ai-image models                        # Full registry across 13 backends
> Migrate old ai-image config                 # Merge legacy ~/.config/{solution-master,tender-workflow}/config.yaml
```

Or pure CLI (power user) — first resolve `$AI_IMAGE_DIR` per SKILL.md §path-self-locate:

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models [provider]
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" add-model <provider> <yaml-snippet>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" migrate
```

**Config file**: `~/.config/presales-skills/config.yaml` — fields: `api_keys.<provider>` / `ai_image.default_provider` / `ai_image.default_size` / `ai_image.default_aspect_ratio`. `models-user.yaml` lives in the same directory; user-defined models go there (via the `add-model` command).

## Cross-plugin invocation

When solution-master / ppt-master / tender-workflow call ai-image from their own SKILL.md, they **bootstrap the ai-image plugin path via installed_plugins.json** (substituting the plugin name with `ai-image`), then:

```bash
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/
```

See the "cross-plugin call" template section in each main plugin's SKILL.md.

## Usage examples

```
> Generate an image: a modern minimalist container cloud architecture diagram
> Use ark to generate a K8s network topology diagram
> /ai-image:gen "futuristic cloud platform dashboard, hi-tech aesthetic"
> Generate a transparent-background fox logo                    # OpenAI backend exclusive
> Replace the background of this image with blue sky and clouds (provide source path)  # OpenAI inpainting
> Make a Bento grid infographic comparing 5 cloud vendors       # Auto-routes through infographics/
> Make an ER diagram: User / Order / Product / Inventory        # Auto-routes through technical-diagrams/
```

## Out of scope

- **Video generation** — this plugin handles images only; video is a separate concern
- **ASCII art** — handled by plain-text tools, not image generation

## Project structure

```
ai-image/
├── .claude-plugin/plugin.json       # Plugin metadata
├── skills/gen/
│   ├── SKILL.md                     # Main entry / path self-locate / workflow
│   ├── setup.md                     # Configuration wizard
│   ├── requirements.txt             # Python dependencies
│   ├── prompts/
│   │   └── ai_image_models.yaml     # 13 backends × model registry (unified)
│   ├── templates/                   # 79 templates, 17 categories (vendored from garden-skills MIT)
│   │   ├── slides-and-visual-docs/
│   │   ├── infographics/
│   │   ├── ui-mockups/
│   │   ├── academic-figures/
│   │   ├── technical-diagrams/
│   │   └── ... (17 categories total)
│   └── scripts/
│       ├── _ensure_deps.py          # Auto pip install
│       ├── ai_image_config.py       # Config CRUD CLI
│       ├── image_gen.py             # Main entry (called by SKILL.md / main plugins)
│       └── image_backends/          # Per-backend implementations
└── tests/                           # ai-image's own unit tests
    ├── test_config_size_validation.py
    ├── test_ensure_deps_lock.py
    └── test_sanitize_error.py
```

## Relationship with other plugins

| Main plugin | What it uses ai-image for |
|---|---|
| **solution-master** | Chapter visuals (architecture → drawio; concept / screenshot → ai-image); structured scenarios auto-route through templates/ |
| **ppt-master** | Per-slide visuals; Bento grid / policy-style slides etc. auto-route through templates/ |
| **tender-workflow taw** | Bid chapter visuals; per-H3 sub-section context picks ai-image / drawio / placeholder |

All three main plugins list ai-image as a **required dependency**; without it, image-gen capability gracefully degrades to placeholder.

## Third-party components

The prompt templates under `templates/` are sourced from [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) gpt-image-2 (MIT License). See [`skills/gen/templates/LICENSE-gpt-image-2`](./skills/gen/templates/LICENSE-gpt-image-2) for the borrowed-files list and the original LICENSE.
