# Alauda (灵雀云) - Design Specification

> Suitable for enterprise solution proposals, product introductions, technical architecture presentations, customer case studies, and cloud-native technology sharing.

---

## I. Template Overview

| Property         | Description                                                        |
| ---------------- | ------------------------------------------------------------------ |
| **Template Name** | alauda (灵雀云)                                                    |
| **Use Cases**    | Enterprise solution proposals, product introductions, technical selection, customer case studies |
| **Design Tone**  | Modern tech consulting, structured expression, clean and restrained |
| **Theme Mode**   | Light theme (white background + Alauda Blue accent)                |

---

## II. Canvas Specification

| Property          | Value                          |
| ----------------- | ------------------------------ |
| **Format**        | Standard 16:9                  |
| **Dimensions**    | 1280 × 720 px                 |
| **viewBox**       | `0 0 1280 720`                 |
| **Page Margins**  | Left/Right 60px, Top 56px, Bottom 40px |
| **Safe Area**     | x: 60–1220, y: 56–680         |
| **Grid Baseline** | 40px                           |

---

## III. Color Scheme

### Primary Colors

| Role                   | Value       | Notes                                      |
| ---------------------- | ----------- | ------------------------------------------ |
| **Alauda Blue**        | `#3BAEE3`   | Primary brand color, accent, icons, buttons |
| **Deep Teal**          | `#125B7D`   | Dark backgrounds, chapter page, gradient endpoint |
| **Background White**   | `#FFFFFF`   | Main page background                       |
| **Light Blue Tint**    | `#D8EFF9`   | Card backgrounds, secondary fill           |
| **Light Gray BG**      | `#F1F5F9`   | Separator areas, subtle backgrounds        |

### Text Colors

| Role               | Value       | Usage                          |
| ------------------ | ----------- | ------------------------------ |
| **Title Dark**     | `#334155`   | Main titles, headings (dk1)    |
| **Body Text**      | `#475569`   | Body content, descriptions     |
| **Auxiliary Gray**  | `#94A3B8`   | Annotations, sources, footer   |
| **White Text**     | `#FFFFFF`   | Text on dark/blue backgrounds  |

### Accent Colors

| Usage               | Value       | Description                          |
| -------------------- | ----------- | ------------------------------------ |
| **Teal**             | `#14B8A6`   | Positive indicators, success states  |
| **Green**            | `#25B273`   | Growth, positive metrics             |
| **Red**              | `#FE574C`   | Warning, negative, Before states     |
| **Amber**            | `#FFC832`   | Highlight, attention                 |
| **Link Blue**        | `#1B89BC`   | Links, interactive elements          |

---

## IV. Typography System

### Font Stack

**Primary stack**: `"Aptos Display", "PingFang SC", "Microsoft YaHei", sans-serif`
**Body stack**: `Aptos, "PingFang SC", "Microsoft YaHei", sans-serif`

### Font Size Hierarchy

| Level  | Usage                | Size    | Weight   |
| ------ | -------------------- | ------- | -------- |
| H1     | Cover main title     | 48px    | Bold     |
| H2     | Page title           | 32px    | Bold     |
| H3     | Section title        | 20–22px | SemiBold |
| H4     | Card title           | 16–18px | SemiBold |
| P      | Body content         | 14–15px | Regular  |
| Data   | KPI / data highlight | 40px    | Bold     |
| Sub    | Labels / annotations | 12px    | Regular  |

---

## V. Page Structure

### General Layout (Master Frame — from original PPTX master EMF)

| Area                 | Position              | Description                                      |
| -------------------- | --------------------- | ------------------------------------------------ |
| **Left accent block**| x=0, y=29, 22×45px    | Alauda Blue (`#3BAEE3`) vertical bar anchoring the page identity |
| **Title**            | x=46, y=55, fs=37px   | Page title, bold, `#334155` (light) / `#FFFFFF` (dark) |
| **Subtitle / Key Msg**| x=32, y=95, fs=21px  | Optional takeaway, `#334155` (light) / `#FFFFFF` fill-opacity 0.7 (dark) |
| **Content area**     | y=130+, ~520px tall   | Main content zone — freely laid out by the Executor |
| **Footer divider**   | y=682                 | Light gray line `#E2E8F0` (light) / `#FFFFFF` opacity 0.1 (dark) |
| **Footer**           | y=706                 | `Alauda` label (left, x=60) + page number (right, x=1220) |

### Decorative Design (Master Frame)

- **Left edge accent block**: Alauda Blue (`#3BAEE3`) `<rect x="0" y="29" width="22" height="45"/>` — the canonical frame marker, anchors the page identity next to the title
- **Background geometric decorations** (right-bottom corner, low opacity):
  - Light pages: `#3BAEE3` at 0.04 / 0.03 / 0.02 (3 shapes)
  - Dark pages: `#FFFFFF` at 0.03 / 0.02 / 0.015 (3 shapes)
  - Shapes (partially offscreen for subtle corner accent):
    - `<circle cx="1350" cy="600" r="280"/>`
    - `<circle cx="1400" cy="250" r="220"/>`
    - `<ellipse cx="1150" cy="780" rx="350" ry="130"/>`
- **No top 4px bar**: the master does NOT use a top accent bar — the left block is the canonical identity marker
- **Footer divider**: Horizontal line at y=682
- **Card style**: White cards with `#E2E8F0` border (1px), rounded corners (rx=8)
- **Logo**: Alauda bird logo on cover and ending pages

---

## VI. Page Types

### 1. Cover Page (01_cover.svg)

- Solid Dark Navy (`#0F2B46`) background — default cover style
- Left-aligned title stack: `{{TITLE}}` (H1, white), `{{SUBTITLE}}` (white, fill-opacity 0.85), `{{AUTHOR}}` + `{{DATE}}`
- Footer: `Alauda` label at `(60, 706)` white fill-opacity 0.5

> A `01_cover_light.svg` variant also exists with full Alauda Blue (`#3BAEE3`) background + white decorative circles, for projects that prefer the lighter brand-blue cover.

### 2. Table of Contents (02_toc.svg)

- White background with standard right-bottom decorations (same as content pages)
- Left side: `city_skyline.jpg` photo at `(137, 137, 335×446)` with translucent Alauda Blue overlay panel containing "目录 / CONTENT" text
- Right side: 4-section grid layout with large numbered items (`01`–`04`)
- Each item: big blue numeral + `{{TOC_ITEM_N_TITLE}}` + `{{TOC_ITEM_N_DESC}}`

### 3. Chapter Page (02_chapter.svg)

- White background with standard right-bottom decorations
- Left side: `building_glass.png` full-bleed photo at `(55, 47, 417×625)`
- Right side: Large red (`#FE574C`) `{{CHAPTER_NUM}}` at 128px + "PART" label + `{{CHAPTER_TITLE}}` at 60pt bold
- Chapter number uses red accent as a visual interrupt against the blue/white palette

### 4. Content Page (03_content.svg and all 03_content_*.svg variants)

- White background (light variants) or dark gradient (dark variants)
- Left edge accent block (`rect x=0 y=29 w=22 h=45 fill=#3BAEE3`)
- Background geometric decorations at right-bottom corner (3 low-opacity shapes)
- Page title at `x=46, y=55, font-size=37px` bold (right next to the accent block)
- Optional subtitle/key-message at `x=32, y=95, font-size=21px`
- Flexible content area (AI determines layout based on content)
- Footer: "Alauda" (left), page number (right)

**Authoritative frame reference**: `03_content_title.svg` / `03_content_title_subtitle.svg` — these are extracted directly from the original PPTX master EMF and define the canonical header/footer for all content pages. All `03_content_*.svg` variants share this frame.

### 5. Ending Page (04_ending.svg)

- Solid Dark Navy (`#0F2B46`) background — mirrors the default dark cover
- Centered "THANK YOU!" headline (white, 44px bold) at `(640, 280)`
- `{{THANK_YOU}}` Chinese tagline (white fill-opacity 0.85, 28px)
- `{{CONTACT_INFO}}` (white fill-opacity 0.75, 16px)
- Footer: `Alauda` label at `(60, 706)` white fill-opacity 0.5

> A `04_ending_light.svg` variant also exists with full Alauda Blue (`#3BAEE3`) background + centered Alauda logo, paired with the light cover variant.

---

## VII. Content Page Variants (Layout Primitives)

In addition to the generic `03_content.svg`, this template includes 8 pre-built content page variants from the Alauda design system. The Executor can reference these when the content matches a specific layout pattern.

| Variant File | Layout Pattern | Origin | Key Placeholders |
| --- | --- | --- | --- |
| `03_content_cards.svg` | Three-card differentiation | Slide 18 | `{{CARD_N_TITLE}}`, `{{CARD_N_DESC}}` |
| `03_content_compare.svg` | Before / After comparison | Slide 12 | `{{BEFORE_TITLE}}`, `{{AFTER_TITLE}}` |
| `03_content_kpi.svg` | KPI metric cards (4 cards, light) | Slide 21 | `{{KPI_N_VALUE}}`, `{{KPI_N_LABEL}}` |
| `03_content_dark_metrics.svg` | Dark four-metric page | Slide 6 | `{{METRIC_N_VALUE}}`, `{{METRIC_N_LABEL}}` |
| `03_content_process.svg` | Four-step process flow | Slide 11 | `{{STEP_N_TITLE}}`, `{{STEP_N_DESC}}` |
| `03_content_twocol.svg` | Two-column (image + text) | Slide 7 | `{{LEFT_CONTENT}}`, `{{RIGHT_TITLE}}` |
| `03_content_lead_detail.svg` | Lead statement + detail items | Slide 8 | `{{LEAD_STATEMENT}}`, `{{ITEM_N_TITLE}}` |
| `03_content_screenshot.svg` | Full-width screenshot | Slide 9 | `{{SCREENSHOT_CONTENT}}`, `{{SCREENSHOT_CAPTION}}` |
| `03_content_dual_value.svg` | Dual product value | Slide 10 | `{{PRODUCT_A_TITLE}}`, `{{PRODUCT_B_TITLE}}` |
| `03_content_architecture.svg` | Layered architecture diagram | Slide 13 | `{{LAYER_N_TITLE}}`, `{{LAYER_N_DESC}}` |
| `03_content_panorama.svg` | Platform panorama | Slide 14 | `{{DOMAIN_N}}`, `{{PLATFORM_TITLE}}`, `{{CAP_N}}` |
| `03_content_migration.svg` | System migration (Old → Bridge → New) | Slide 15 | `{{OLD_SYSTEM_TITLE}}`, `{{BRIDGE_TITLE}}`, `{{NEW_SYSTEM_TITLE}}` |
| `03_content_canvas.svg` | Capability canvas (3-column) | Slide 16 | `{{COL_N_HEADER}}`, `{{CAP_N_TITLE}}` |
| `03_content_company.svg` | Company introduction | Slide 17 | `{{COMPANY_NAME}}`, `{{STAT_N_VALUE}}` |
| `03_content_matrix.svg` | 2×2 matrix | Slide 19 | `{{QUAD_N_TITLE}}`, `{{QUAD_N_DESC}}` |
| `03_content_code.svg` | Code + notes | Slide 20 | `{{CODE_CONTENT}}`, `{{NOTE_N_TITLE}}` |
| `03_content_logos.svg` | Logo wall | Slide 22 | `{{GROUP_N_LABEL}}`, `{{LOGO_N_N}}` |
| `03_content_evidence.svg` | Evidence page (thesis + proof) | Slide 23 | `{{THESIS_STATEMENT}}`, `{{EVIDENCE_N_TITLE}}` |
| `03_content_case.svg` | Case study | Slide 24 | `{{CASE_CUSTOMER}}`, `{{CHALLENGE_TITLE}}`, `{{RESULT_TITLE}}` |
| `03_content_quote.svg` | Quote / testimonial | Slide 25 | `{{QUOTE_TEXT}}`, `{{SPEAKER_NAME}}` |
| `03_content_table.svg` | Standard table (4-col × 5-row) | Slide 26 | `{{COL_HEADER_N}}`, `{{ROW_N_COL_N}}` |
| `03_content_timeline.svg` | Timeline (5 nodes) | Slide 27 | `{{TIME_N}}`, `{{EVENT_N_TITLE}}` |
| `03_content_parallel.svg` | Dual parallel value | Slide 28 | `{{LEFT_PANEL_TITLE}}`, `{{RIGHT_PANEL_TITLE}}` |

### Component Library

For atomic-level SVG primitives (individual card shapes, layer bands, step circles, arrows, code blocks, table rows, etc.), see **`component_library.md`**. The component library provides copy-pasteable SVG snippets that the Executor can freely compose into any layout — not limited to the pre-built variant templates above.

### Usage Guidelines

- **Variant templates are references, not rigid constraints.** The Executor may adapt, combine, or simplify them based on actual content.
- **For layouts not covered by any variant**, compose directly from `component_library.md` primitives.
- All variants share the same header/footer frame (top blue bar, "Alauda" footer, page number).
- Each variant uses the standard Alauda color palette and font stack.
- The generic `03_content.svg` remains the default for any content that does not match a specific variant.

### Layout Modes Summary

| Mode              | Description                            |
| ----------------- | -------------------------------------- |
| **Single Column** | Full-width content, text or diagrams   |
| **Two Column**    | Left text + right image/diagram        |
| **Card Grid**     | 2–4 cards in a row, equal sizing       |
| **KPI Row**       | 3–4 metric cards, large number + label |
| **Before/After**  | Two-panel comparison                   |
| **Architecture**  | Layered structure diagram              |

---

## VIII. Spacing Specification

| Element              | Value     |
| -------------------- | --------- |
| Page margins         | 60px      |
| Title area height    | 50px      |
| Content top offset   | 140px     |
| Card gap             | 24px      |
| Card inner padding   | 20–24px   |
| Text line height     | 1.6       |
| Grid baseline        | 40px      |

---

## IX. SVG Technical Constraints

### Mandatory Rules

1. viewBox: `0 0 1280 720`
2. Use `<rect>` elements for backgrounds
3. Use `<tspan>` for text wrapping (no `<foreignObject>`)
4. Use `fill-opacity` / `stroke-opacity` for transparency; `rgba()` is prohibited
5. Prohibited: `clipPath`, `mask`, `<style>`, `class`, `foreignObject`
6. Prohibited: `textPath`, `animate*`, `script`, `marker`/`marker-end`
7. Use `<polygon>` triangles instead of `<marker>` for arrows
8. Define gradients using `<linearGradient>` within `<defs>`

### PPT Compatibility Rules

- No `<g opacity="...">` (group opacity); set opacity on each child element individually
- Use overlay layers instead of image opacity
- Use inline styles only; external CSS and `@font-face` are prohibited

---

## X. Placeholder Specification

| Placeholder          | Description          | Applicable Template |
| -------------------- | -------------------- | ------------------- |
| `{{TITLE}}`          | Main title           | Cover               |
| `{{SUBTITLE}}`       | Subtitle             | Cover               |
| `{{DATE}}`           | Date                 | Cover               |
| `{{AUTHOR}}`         | Author / Organization| Cover               |
| `{{CHAPTER_NUM}}`    | Chapter number       | Chapter page        |
| `{{CHAPTER_TITLE}}`  | Chapter title        | Chapter page        |
| `{{PAGE_TITLE}}`     | Page title           | Content page        |
| `{{CONTENT_AREA}}`   | Content area         | Content page        |
| `{{PAGE_NUM}}`       | Page number          | Content, Ending     |
| `{{SOURCE}}`         | Data source          | Content footer      |
| `{{TOC_ITEM_1_TITLE}}` ~ `{{TOC_ITEM_4_TITLE}}` | TOC item titles | TOC |
| `{{TOC_ITEM_1_DESC}}` ~ `{{TOC_ITEM_4_DESC}}`   | TOC item descriptions | TOC |
| `{{THANK_YOU}}`      | Thank-you message    | Ending page         |
| `{{CONTACT_INFO}}`   | Contact information  | Ending page         |

---

## XI. Asset Inventory

| File                   | Purpose                         |
| ---------------------- | ------------------------------- |
| `alauda_logo.png`      | Brand logo (blue bird + text)   |
| `dark_grid_texture.png`| Chapter page dark background    |
| `blue_gradient_bg.jpg` | Blue gradient (optional accent) |
