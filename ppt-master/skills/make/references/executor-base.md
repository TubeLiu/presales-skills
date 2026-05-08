# Executor Common Guidelines

> Style-specific content is in the corresponding `executor-{style}.md`. Technical constraints are in shared-standards.md.

---

## 1. Template Adherence Rules

If template files exist in the project's `templates/` directory, the template structure must be followed:

| Page Type | Corresponding Template | Adherence Rules |
|-----------|----------------------|-----------------|
| Cover | `01_cover.svg` | Inherit background, decorative elements, layout structure; replace placeholder content |
| Chapter | `02_chapter.svg` | Inherit numbering style, title position, decorative elements |
| Content with semantic route | `03_content_*.svg` declared in `spec_lock.md ## semantic_routes` | Use the declared variant as the primary visual grammar; adapt content within the declared payload budget |
| Content without semantic route | `03_content.svg` | Inherit header/footer styles; content area may be freely laid out |
| Ending | `04_ending.svg` | Inherit background, thank-you message position, contact info layout |
| TOC | `02_toc.svg` | **Optional**: Inherit TOC title, list styles |

### Page-Template Mapping Declaration (Required Output)

Before generating each page, you must explicitly output which template (or "free design") is used:

```
📝 **Template mapping**: `templates/01_cover.svg` (or "None (free design)")
🧭 **Semantic route**: `page_intent | template_variant | visual_grammar | payload_budget` (or "None")
🧩 **Visual system**: `density | components | icons` (or "None")
🎛️ **Deck diversity**: `visual_archetype | current deck archetype mix`
🧱 **Design semantics**: `component roles | slot roles | text alignment policy`
🎯 **Adherence rules / layout strategy**: [specific description]
```

- **Content pages with `semantic_routes`**: Use the declared `template_variant` as the first-choice page template and preserve its visual grammar unless the content would violate SVG constraints. Keep visible text inside the declared `payload_budget`; move overflow to speaker notes.
- **Content pages with `visual_system`**: Use the declared density profile, component primitives, and icon inventory as the execution contract. Read `templates/component_library.md` before composing the first such page.
- **Content pages with `design_diversity`**: Preserve the page's declared visual archetype. If recent pages already use the same archetype heavily, prefer the declared route's alternate grammar or reduce card-grid structure before repeating it.
- **Content pages with `density_contract`**: Satisfy the declared visible claims / objects / labels / evidence / relationships minimums. Use compact human slide forms (tables, mapped rows, annotations, KPI chips, layer labels, callout strips) instead of hiding concrete source detail in speaker notes.
- **Design semantics are mandatory on generated primitives**: before writing SVG, name the intended component tree in page terms (for example `hero-message`, `process-step`, `mapping-row`, `decision-callout`). In SVG, mark generated shapes/text with `data-role`, `data-slot`, `data-group`, `data-intent`, or `data-text-align` when the default center rule does not apply. This is not decoration; downstream checkers use it to verify component→slot→text relationships instead of guessing from colors.
- **Content pages without `semantic_routes`**: Templates only define header and footer; the content area is freely laid out by the Executor
- **No template**: Generate entirely per the Design Specification & Content Outline

---

## 2. Design Parameter Confirmation (Mandatory Step)

> Before generating the first SVG page, you **must review the key design parameters from the Design Specification & Content Outline** to ensure all subsequent generation strictly follows the spec.

Must output confirmation including: canvas dimensions, body font size, color scheme (primary/secondary/accent HEX values), font plan.

**Why is this step mandatory?** Prevents the "spec says one thing, execution does another" disconnect.

### 2.1 Per-page spec_lock re-read (Mandatory)

> Long decks + streaming generation = attention drift and context compression. By mid-deck, the Executor has often drifted off the color palette or icon inventory declared in `design_spec.md`. `spec_lock.md` is the short form of those decisions and is the Executor's **canonical execution reference** during generation.

**Hard rule**: Before generating **each** SVG page, `read_file <project_path>/spec_lock.md`. Use the values from this file — not values you remember from earlier in the conversation. If the context was auto-compacted, `read_file <project_path>/design_spec.md` too (for the current page's §IX brief).

**If `spec_lock.md` is missing**: Before generating each page, emit the literal line `warning: spec_lock.md missing — generating without execution lock` and proceed using `design_spec.md` narrative values. Do not silently skip. A missing lock is expected only for legacy projects predating this feature; for new projects the Strategist MUST produce it (see [strategist.md](strategist.md) §6, step 4).

**Forbidden — values outside the lock**:

- Color values (fill / stroke / stop-color) MUST come from `colors` in `spec_lock.md`
- Icons MUST come from the `icons.inventory` list; icon library MUST equal `icons.library`
- Font family MUST come from the `typography` block: use the role-specific override (`title_family` / `body_family` / `emphasis_family` / `code_family`) if declared for that role, otherwise fall back to `font_family`.
- Font sizes follow a **ramp anchored on `typography.body`**, not a closed menu. The slots listed in `spec_lock.md typography` (`title` / `subtitle` / `annotation` / any project-specific additions like `cover_title` / `hero_number`) are common anchors — use them directly when they fit. Executor MAY use an intermediate size (e.g., 40px hero number, 13px chart annotation, 72px cover headline) when the role calls for it, **provided** the size's ratio to `body` falls within the corresponding role's band in the design-spec ramp table (see `design_spec_reference.md §IV — Font Size Hierarchy`, also mirrored in `design_spec.md §IV` per project). Sizes outside every ramp band are still forbidden — surface the need and extend the lock instead of inventing one-off values.
- Images MUST reference files listed under `images`; no invented filenames

If a page genuinely needs a value not in `spec_lock.md`, stop and surface it — do not silently invent one. Either request the user to extend the lock, or revise the page to stay within it.

**Design semantics contract — component → slot → text**:

Every non-background visual group must be expressible as a component with one
or more slots. This is the semantic layer that prevents fragile color/size
rules from becoming the design system.

- Component shapes: use `data-role` for the role (`content-card`, `process-step`, `metric-card`, `table`, `mapping-row`, `callout-content`, `label`, `header`, etc.) and `data-group` for siblings that belong together.
- Slot shapes: use `data-slot` or a slot role such as `label-slot`, `header-cell`, `table-cell`, `body-slot`.
- Text: use `data-slot` when attached to a slot, `data-intent` for route-specific meaning, and `data-text-align="left"` only for true paragraph/card content with padding.
- Default rule: text inside colored blocks, chips, step circles, table headers, buttons, and small labels is horizontally and vertically centered. Left alignment is an explicit exception, not the default.
- Large content cards may contain left-aligned text only when the owning shape is marked as content (`data-role="content-card"` or `data-role="callout-content"`) and the text has visible padding from the card edge.

**Per-page layout rhythm — `page_rhythm` section**:

Before drawing each page, look up its entry in `page_rhythm` (key format `P<NN>` matching the page index in §IX of `design_spec.md`) and apply the corresponding layout discipline:

| Tag | Layout discipline |
|-----|-------------------|
| `anchor` | Structural page (cover / chapter / TOC / ending). Follow the matching template verbatim. |
| `dense` | Information-heavy. Card grids, multi-column layouts, KPI dashboards, tables, and charts are all permitted. This is the baseline behavior. |
| `breathing` | Low-density impact page. Avoid **multi-card grid layouts** — do not organize content as multiple parallel rounded containers (3-card row, 4-card KPI grid, 2×2 matrix rendered as cards). Use naked text blocks, dividers, whitespace, or full-bleed imagery as the content structure. Single rounded visual elements (hero image corners, callouts, tags, one emphasis block) are fine — the rule is about grid structure, not about the `rx` attribute. Proportions follow information weight (not a preset ratio). Typical forms: hero quote, single large number with one-line interpretation, full-bleed image with floating caption, section transition. |

**Why this matters**: Without rhythm variation, long decks default to "every page is a card grid" — the AI-generated look. The `page_rhythm` tag is the only lever that survives context compression (since Executor re-reads `spec_lock.md` per page); narrative guidance buried in `design_spec.md` does not.

**Missing `page_rhythm` section** → fall back to `dense` for every page (pre-rhythm behavior). Emit the literal line `warning: spec_lock.md missing page_rhythm — defaulting all pages to dense` once, then proceed.

**Tag not found for current page** → fall back to `dense` silently. Do not invent a tag.

**Deck-level design diversity — `design_diversity` section**:

If `spec_lock.md` includes `design_diversity`, read the current page's intended
visual archetype before drawing. The archetype is a design grammar promise, not
a cosmetic label. Examples:

| Archetype | Use when content is... |
|-----------|------------------------|
| `architecture_stack` | platform layers, control/data plane, topology, dependencies |
| `process_flow` | phases, gates, responsibility flow, delivery rhythm |
| `matrix_table` | object mapping, risk/owner/rollback decisions, compact comparison |
| `code_annotation` | YAML / CLI / API samples that need annotated code panels |
| `kpi_dashboard` | measurable targets, thresholds, acceptance metrics |
| `comparison_bridge` | current vs. target, before/after, migration bridge |
| `argument_thesis` | "why this approach" pages, decision rationale, evidence chain |

For decks with mixed source semantics, do not let one archetype dominate most
pages. In practice: if a deck has 6+ content pages, avoid using card-grid
structure on more than about half of them unless the deck is intentionally a
table appendix. After generation, run `ppt_master_eval.py --target <project_path>
--design`; fix upstream route/archetype choices when it reports
`repeated_visual_archetype` or `card_grid_overuse`.
Use the report's `generationGuidance` fields as the regeneration brief. Those
actions describe how to change route, component, slot, density, and hierarchy;
they are not permission to patch a single SVG's coordinates until it passes.

**Information density — `density_contract` section**:

If `spec_lock.md` includes `density_contract`, read the current page's contract
before drawing. The contract is a lower bound for visible information, not a
decoration target:

- `visible_claims`: explicit statements the audience can read on the slide.
- `visible_objects`: source-specific business / technical objects, not generic
  nouns.
- `visible_labels`: row labels, chips, annotations, step names, layer labels,
  KPI labels, or table headers.
- `evidence_items`: numbers, thresholds, named standards, status values, or
  validation gates.
- `relationships`: mappings, dependencies, migration steps, validation links,
  ownership, or before/after transitions.

Do not satisfy density by shrinking text below the typography ramp. Increase
structure instead: matrix rows, compact badges, annotation columns, dense
architecture labels, grouped callout strips, or table-like layouts. Speaker
notes are for overflow and narration; if most source detail is only in notes,
the page fails the density contract.

**Per-page semantic route — `semantic_routes` section**:

If `spec_lock.md` includes `semantic_routes`, look up the current page's
`P<NN>` entry before choosing a content-page template. The compact value is:

`page_intent | template_variant | visual_grammar | payload_budget`

Apply it as follows:

| Field | Executor obligation |
|-------|---------------------|
| `page_intent` | Use it to preserve the source-to-design decision made by Strategist. Do not silently recategorize the page during SVG generation. |
| `template_variant` | Map the page to `templates/<template_variant>` when that file exists. If it is missing, emit a warning and fall back to `templates/03_content.svg` while preserving the visual grammar manually. |
| `visual_grammar` | Preserve the relationship structure (for example, before-bridge-after, four-layer stack, four-step process). Do not replace it with a generic card grid. |
| `payload_budget` | Treat it as the visible-text budget. Summarize to fit the slot; put extra explanation in notes rather than shrinking font size or overflowing containers. |

If the project has `templates/semantic_routes.json` but `spec_lock.md` lacks a
`semantic_routes` section, emit the literal line
`warning: spec_lock.md missing semantic_routes — using generic content template routing`
once before the first content page, then proceed with the pre-route behavior.

**Per-page visual system — `visual_system` section**:

If `spec_lock.md` includes `visual_system`, look up the current page's
`P<NN>` entry before drawing SVG. The compact per-page value is:

`density | components | icons`

Apply it as follows:

| Field | Executor obligation |
|-------|---------------------|
| `density` | Load the matching density profile from `templates/visual_system.json`; apply its minimum gaps, label budget, nesting limit, and notes-overflow expectation. |
| `components` | Compose from the named primitives in `templates/component_library.md` before inventing new shapes. Adapting sizes is allowed; replacing the route with generic card grids is not. |
| `icons` | Use only icons listed here and in `icons.inventory`; render with `<use data-icon="chunk/name">` placeholders so `finalize_svg.py` embeds them. |

If the project has `templates/visual_system.json` but `spec_lock.md` lacks a
`visual_system` section, emit the literal line
`warning: spec_lock.md missing visual_system — using template routes without density/icon contract`
once before the first content page, then proceed with semantic routing only.

For any route using `connector_line` or `directional_arrow`, also apply
`templates/visual_system.json.connectorPolicy`: horizontal arrows must travel
through whitespace lanes and stay at least `minTextLaneGapPx` away from nearby
text in the same y band. This applies to every connector on the page, not just
the most visually obvious one.
Also keep connectors at least `minContainerBorderGapPx` away from card/container
borders. If an arrow head would touch or enter a card, shorten the arrow,
increase the gutter, or move the connector to a separate whitespace lane.

If `templates/visual_system.json.deliveryMode.customerCanvas` exists, treat it
as a release rule: internal metadata such as `page_intent`, density names, route
variant names, and sample labels like `样张 P07` must not appear as visible slide
text. Put that information in speaker notes, eval reports, filenames, or
comments only.

If `templates/visual_system.json.shapeTextPolicy` exists, apply it to every
badge, button, pill, circle number, metric chip, and colored header strip before
SVG export. Text inside a colored block is centered by default, including pale
tints such as light blue, light green, light yellow, and light red. Single-line
label text must use geometric centering:
`text-anchor="middle"`, `dominant-baseline="middle"`, `x = shape center x`, and
`y = shape center y`. Do not approximate vertical centering by adding font-size
offsets to the baseline. Left-aligned text is allowed for paragraph/card content
areas with explicit padding, but it is an exception: model it as a separate
padded content area rather than placing start-anchored text directly inside the
colored primitive. If a colored callout intentionally contains left-aligned
content, mark the owning shape or text with `data-text-align="left"` or
`data-role="callout-content"` so the checker can distinguish the design choice
from an accidental miss.
When a colored header bar, table header, or status strip contains multiple
labels, split it into explicit cells or virtual column slots and center each
label horizontally and vertically in its own slot; do not leave the labels as
start-anchored text floating on one large colored rectangle.

If `templates/visual_system.json.routeQualityRules` has an entry for the current
`page_intent`, apply every bullet before drawing SVG. These rules are more
specific than generic layout instincts. Examples:

- `mapping_table`: rows need business-decision cues such as automation, risk,
  owner, rollback, or priority; do not stop at object-name mapping.
- `migration_bridge`: the bridge is the visual and narrative center; avoid three
  equal cards unless the content truly has equal weight. The bridge must show
  transformation mechanics such as gates, control points, validation signals, or
  rollback logic; a large percentage ramp alone is not enough.
- `risk_matrix`: axis labels must be explicit and high-contrast before quadrant
  details.

**Density and collision discipline**:

- Preserve at least the profile's `relatedGapPx` between text and its owning visual, and at least `groupGapPx` between unrelated visual groups.
- Respect `maxNestedLevels`; do not create unreadable architecture pages by stacking labels inside labels inside containers.
- Respect `maxVisibleMicroLabels`; when content exceeds the budget, merge labels, shorten them, or move details to notes.
- Do not create information density by repeating identical micro-label stacks in
  multiple peer cards. If three or more cards would contain the same vertical
  pill pattern, switch to bands, a matrix, a causal map, or a scoped decision
  block.
- Every text item and child shape must remain inside its direct semantic parent
  component (`content-card`, `bridge`, `process-step`, `metric-card`,
  `risk-quadrant`, etc.). A child that fits the outer panel but escapes its own
  card is still a layout failure.
- Do not put CJK text in narrow vertical strips or rotate Chinese labels. Use horizontal side labels, badges, or section headers instead.
- Do not shrink text below the typography ramp to make dense pages fit. Reducing visible content is the preferred solution.
- Do not render eval/internal metadata such as `mapping_table`, `dense_technical`, or `样张 P05` on a customer-facing slide canvas.
- After rendering dense technical pages, inspect for text overlap, clipping, icon/text collisions, arrows covering labels, connector arrows sharing a text lane, connector arrows intruding into card/container borders, semantic parent overflow, and shape-label text not centered in its primitive before proceeding to export.

**Component placement grid discipline**:

- Before placing any semantic component (content-card, process-step, metric-card, bridge, mapping-row, etc.), calculate its bounding box: `{x, y, width, height}`.
- Maintain a running **placement ledger** of all component bounding boxes placed on the current page. Before placing each new component, verify it does not intersect any existing entry in the ledger:
  - Horizontal clearance: components sharing vertical overlap must have ≥12px horizontal gap between their right edge and the next component's left edge.
  - Vertical clearance: components sharing horizontal overlap must have ≥12px vertical gap between the upper component's bottom edge and the lower component's top edge.
  - If the new component would violate clearance, adjust its position before writing SVG. Do NOT overlap and expect post-processing to fix it.
- Text must be inset ≥8px from each edge of its containing component rect. If text would exceed the available width after inset, shorten the text and put the remainder in speaker notes — do NOT shrink font below the typography ramp or let text touch/exceed the rect boundary.
- For table-like layouts: ensure each row rect has a unique y-range that does not overlap with adjacent rows. Row height must accommodate all text at the declared font size plus ≥6px top and bottom padding.
- For card grids: calculate total height of all cards + inter-card gaps (≥12px each) before placing the first card. If total exceeds the available content area height (viewBox height minus header/footer), reduce card count or card height — do NOT compress gaps below 12px.
- **Component rect must fit its content**: A colored block's height is the content height + padding, not an arbitrary value. After placing all text inside a card, set the card rect's bottom to `last_text_baseline + font_size + padding` (typically 8–12px). Excess empty space below text in a card is a layout defect — the card looks broken in PPTX because it visually "leaks" past its content. Never place a card rect and then fill it top-down hoping the height is "close enough."
- **Footer zone is reserved (y ≥ 682 on 720px canvas)**: The area below the footer rule (y=682 on PPT 16:9) is exclusively for the brand mark and page number — both annotated `data-slot="footer"`. No content component (card, strip, banner, table, chart frame) may extend into or past this zone. When calculating available content height, subtract the footer zone: effective content bottom = 670 (12px clearance above the footer rule). If content would encroach on the footer zone, reduce component count, card height, or font size — do NOT push into the footer.
- **viewBox is a hard boundary, not a clip region**: SVG viewBox clips overflow in browsers, but PPTX has no equivalent — any shape extending past the viewBox becomes a visible element protruding beyond the slide boundary. ALL shapes (including decorative background circles/ellipses, tinted overlays, and subtle gradient elements) must fit entirely within `0 0 <width> <height>`. Do not place circles at `cx=1350` with `r=280` hoping the viewBox will hide the overflow — it will not survive PPTX conversion. Decorative edge effects must be achieved with shapes that terminate at or before the canvas boundary.

**Human-quality sample discipline — `quality_samples` section**:

If `spec_lock.md` includes `quality_samples`, treat those pages as the first
review set after the deck is generated. This is a review priority, not a
generation subset: every page in `design_spec.md §IX` still must be generated.

- Inspect the sample pages against the template's `human_quality_rubric.json`
  when that file exists.
- Cover narrative specificity, composition hierarchy, density control,
  brand-native execution, technical legibility, and client readiness.
- If a sample page fails because of a local collision or overflow, regenerate
  that page and rerun `svg_quality_checker.py`.
- If a sample page fails because the route, density profile, component choice,
  or payload budget is wrong, go back to `design_spec.md` / `spec_lock.md` and
  fix the upstream contract. Do not keep hand-polishing the same SVG.
- During skill improvement or repeated quality iterations, rotate sample page
  numbers and page intents instead of repeatedly inspecting the same page.
- If `ppt_master_eval.py --design` reports `low_visual_focus`, redesign the
  page grammar before touching coordinates: introduce a dominant component,
  merge equal peer cards into a table / layer / bridge / swimlane, or use
  asymmetric scale so the audience can see what matters first.
- If it reports `repetitive_micro_label_stacks`, do not add spacing to the
  same cards. Change the component type: convert repeated vertical pill lists
  into matrix rows, bands, grouped chips, causal maps, or scoped decision
  blocks.
- If it reports `low_semantic_grouping`, add explicit component and slot roles
  (`data-role`, `data-slot`, `data-group`, `data-intent`) and redraw around
  those groups; this is a semantic-generation failure, not a local alignment
  failure.

**Rationale**: Tool-result re-reads bypass model memory (which compression can corrupt). Every page gets a fresh ground truth pinned to the most recent turn in context.

---

## 3. Execution Guidelines

- **Proximity principle**: Place related elements close together to form visual groups; increase spacing between unrelated groups to reinforce logical structure
- **Absolute spec adherence**: Strictly follow the color, layout, canvas format, and typography parameters in the spec
- **Follow template structure**: If templates exist, inherit the template's visual framework
- **Main-agent ownership**: SVG generation must be performed by the current main agent, not delegated to sub-agents, because each page depends on shared upstream context and cross-page visual continuity
- **Generation rhythm**: First lock the global design context, then generate pages sequentially one by one in the same continuous context; grouped page batches (for example, 5 pages at a time) are not allowed
- **Phased batch generation** (recommended):
  1. **Visual Construction Phase**: Generate all SVG pages continuously in sequential page order, ensuring high consistency in design style and layout coordinates (Visual Consistency)
  2. **Quality Check Gate** (mandatory between phases): run `python3 scripts/svg_quality_checker.py <project_path>` against `svg_output/`. Any `error` (banned SVG features, viewBox mismatch, spec_lock color / font / size drift, non-PPT-safe font stack, etc.) MUST be fixed on the offending page before entering the Logic Construction Phase. Icon drift warnings are contract violations for branded templates; fix off-inventory icons or extend `spec_lock.md` before export. Re-generate the offending page and re-run the check. `warning` entries should be reviewed and fixed when straightforward; otherwise acknowledge and release. Do NOT defer this check to after `finalize_svg.py` — finalize rewrites SVG and some violations get masked.
  3. **Logic Construction Phase**: After SVGs pass the quality gate, batch-generate speaker notes to ensure narrative coherence (Narrative Continuity)
- **Technical specifications**: See [shared-standards.md](shared-standards.md) for SVG technical constraints and PPT compatibility rules
- **Visual depth**: Use filter shadows, glow effects, gradient fills, dashed strokes, and gradient overlays from shared-standards.md to create layered depth — flat pages without elevation or emphasis look unfinished

### SVG File Naming Convention

File naming format: `<number>_<page_name>.svg`

- **Chinese content** → Chinese naming: `01_封面.svg`, `02_目录.svg`, `03_核心优势.svg`
- **English content** → English naming: `01_cover.svg`, `02_agenda.svg`, `03_key_benefits.svg`
- **Number rules**: Two-digit numbers, starting from 01
- **Page name**: Concise and descriptive, matching the page title in the Design Specification & Content Outline

---

## 4. Icon Usage

Four approaches: **A: Emoji** (`<text>🚀</text>`) | **B: AI-generated** (SVG basic shapes) | **C: Built-in library** (`templates/icons/` 6700+ icons, recommended) | **D: Custom** (user-specified)

**Built-in icons — Placeholder method (recommended)**:

```xml
<!-- chunk (default — straight-line geometry, sharp corners, structured) -->
<use data-icon="chunk/home" x="100" y="200" width="48" height="48" fill="#005587"/>

<!-- tabler-filled (bezier-curve forms, smooth & rounded contours) -->
<use data-icon="tabler-filled/home" x="100" y="200" width="48" height="48" fill="#005587"/>

<!-- tabler-outline (light, line-art style — screen-only decks) -->
<use data-icon="tabler-outline/home" x="100" y="200" width="48" height="48" fill="#005587"/>
```

> No need to manually run `embed_icons.py`; `finalize_svg.py` post-processing tool will auto-embed icons.

**Three icon libraries**:

| Library | Style | Count | Prefix | When to use |
|---------|-------|-------|--------|-------------|
| `chunk` | fill · straight-line geometry (sharp corners, rectilinear) | 640 | `chunk/` | ✅ **Default** — most scenarios |
| `tabler-filled` | fill · bezier-curve forms (smooth, rounded contours) | 1000+ | `tabler-filled/` | When design calls for smooth, rounded, organic icon forms |
| `tabler-outline` | stroke/line | 5000+ | `tabler-outline/` | Screen-only decks needing a light, elegant aesthetic |

> ⚠️ **One presentation = one library.** Never mix icons from different libraries. If the chosen library lacks an exact icon, find the closest available alternative **within that same library** — do not cross into another library to fill the gap.

**Searching for icons** — use terminal, zero token cost:
```bash
ls skills/make/templates/icons/chunk/ | grep home
ls skills/make/templates/icons/tabler-filled/ | grep home
ls skills/make/templates/icons/tabler-outline/ | grep chart
```

**Abstract concept → icon name** (names for `chunk`; tabler libraries use their own equivalents — verify with `ls | grep`):

| Concept | chunk | tabler-filled / tabler-outline |
|---------|-------|-------------------------------|
| Growth / Increase | `arrow-trend-up` | same |
| Decline / Decrease | `arrow-trend-down` | same |
| Success / Complete | `circle-checkmark` | `circle-check` |
| Warning / Risk | `triangle-exclamation` | `alert-triangle` |
| Innovation / Idea | `lightbulb` | `bulb` |
| Strategy / Goal | `target` | same |
| Efficiency / Speed | `bolt` | same |
| Collaboration / Team | `users` | same |
| Settings / Config | `cog` | `settings` |
| Security / Trust | `shield` | same |
| Money / Finance | `dollar` | `currency-dollar` |
| Time / Deadline | `clock` | same |
| Location / Region | `map-pin` | same |
| Communication | `comment` | `message` |
| Analysis / Data | `chart-bar` | same |
| Process / Flow | `arrows-rotate-clockwise` | `refresh` |
| Global / World | `globe` | `world` |
| Excellence / Award | `star` | same |
| Expand / Scale | `maximize` | same |
| Problem / Issue | `bug` | same |

> For self-evident names (home, user, file, search, arrow, etc.) — just `grep chunk/` directly without consulting the table.

> ⚠️ **Icon validation rule**: If the Design Specification includes an icon inventory list, Executor may **only** use icons from that approved list. Before using any icon, verify it exists via `ls | grep` search. **Mixing icons from different libraries in the same presentation is FORBIDDEN** — use only the library specified in the Design Spec.

---

## 5. Visualization Reference

When the Design Spec includes a **VII. Visualization Reference List**, read the referenced SVG templates from `templates/charts/` before drawing pages that use those visualization types. The path remains `templates/charts/` for backward compatibility.

🚧 **GATE — Mandatory read before first use**: When Executor encounters a visualization type listed in Section VII of the Design Spec for the first time, Executor **MUST** `read_file templates/charts/<chart_name>.svg` **before** generating that page. Extract the layout coordinates, card structure, spacing rhythm, and visual logic from the template as **creative reference and inspiration** — not as a strict copy. Then design the page independently using the project's own color scheme, typography, and content.

> **Workflow**: read template SVG → understand structure & spacing → design original SVG informed by the reference → do NOT replicate the template verbatim.
> **Reuse**: Once a visualization type has been read and understood, there is no need to re-read for subsequent pages of the same type.
> **Change**: Read the new template when the visualization type changes or the structure needs re-reference.

**Adaptation rules**:
- **Must preserve**: Visualization type (bar/line/pie/timeline/process/framework etc.) as specified in the Design Spec
- **Must adapt**: Data values, labels, colors (match the project's color scheme), and dimensions to fit the page layout
- **May adjust freely**: Visual composition, axis ranges, grid lines, legend position, spacing, decorative elements — creative freedom is encouraged as long as the chart remains accurate and readable
- **Must NOT**: Change visualization type without Design Spec justification, or omit data points / structural elements specified in the outline

> Visualization templates: `templates/charts/` (57 types). Index: `templates/charts/charts_index.json`

---

## 6. Image Handling

Handle images based on their status in the Design Specification's "Image Resource List":

| Status | Source | Handling |
|--------|--------|----------|
| **Existing** | User-provided | Reference images directly from `../images/` directory |
| **AI-generated** | Generated by Image_Generator | Images already in `../images/`, reference directly |
| **Placeholder** | Not yet prepared | Use dashed border placeholder |

**Reference**: `<image href="../images/xxx.png" ... preserveAspectRatio="xMidYMid slice"/>`

**Placeholder**: Dashed border `<rect stroke-dasharray="8,4" .../>` + description text

---

## 7. Font Usage

Font family per role is governed by `spec_lock.md typography` — that file is the source of truth. Read `font_family` as the default, plus any `*_family` override (`title_family` / `body_family` / `emphasis_family` / `code_family` / etc.); roles without an explicit override fall back to `font_family`.

If `spec_lock.md` is absent for any reason, consult the seed combinations and PPT-safe discipline in [`strategist.md`](strategist.md) §g "Typography Plan Confirmation" rather than inventing a stack.

**Hard rule — never violate**: every `font-family` stack emitted into SVG MUST end with a cross-platform pre-installed family (Microsoft YaHei / SimHei / SimSun / Arial / Calibri / Segoe UI / Times New Roman / Georgia / Consolas / Courier New / Impact / Arial Black). PPTX stores a single `typeface` per run with no runtime fallback — a missing font silently degrades to Calibri on the viewer's machine.

---

## 8. Speaker Notes Generation Framework

### Task 1. Generate Complete Speaker Notes Document

After **all SVG pages are generated and finalized**, enter the "Logic Construction Phase" and generate the complete speaker notes document in `notes/total.md`.

**Why not generate page-by-page?** Batch-writing notes allows planning transitions like a script, ensuring coherent presentation logic.

**Format**: Each page starts with `# <number>_<page_title>`, separated by `---` between pages. Each page includes: script text (2-5 sentences), `Key points: ① ② ③`, `Duration: X minutes`. Except for the first page, each page's text starts with a `[Transition]` phrase.

**Basic stage direction markers** (common to all styles):

| Marker | Purpose |
|--------|---------|
| `[Pause]` | Whitespace after key content, letting the audience absorb |
| `[Transition]` | Standalone paragraph at the start of each page's text, bridging from the previous page |

> Each style may extend with additional markers (`[Interactive]`/`[Data]`/`[Scan Room]`/`[Benchmark]` etc.), see `executor-{style}.md`.

**Language consistency rule**: All structural labels and stage direction markers in speaker notes **MUST match the presentation's content language**. When the presentation content is non-English, localize every label — do NOT mix English labels with non-English content.

| English | 中文 | 日本語 | 한국어 |
|---------|------|--------|--------|
| `[Transition]` | `[过渡]` | `[つなぎ]` | `[전환]` |
| `[Pause]` | `[停顿]` | `[間]` | `[멈춤]` |
| `[Interactive]` | `[互动]` | `[問いかけ]` | `[상호작용]` |
| `[Data]` | `[数据]` | `[データ]` | `[데이터]` |
| `[Scan Room]` | `[观察]` | `[観察]` | `[관찰]` |
| `[Benchmark]` | `[对标]` | `[ベンチマーク]` | `[벤치마크]` |
| `Key points:` | `要点：` | `要点：` | `핵심 포인트:` |
| `Duration:` | `时长：` | `所要時間：` | `소요 시간:` |
| `Flex:` | `弹性：` | `調整：` | `조정:` |

> For languages not listed above, translate each label to the corresponding natural term in that language.

**Requirements**:

- Notes should be conversational and flow naturally
- Highlight each page's core information and presentation key points
- Users can manually edit and override in the `notes/` directory

### Task 2. Split Into Per-Page Note Files

Automatically split `notes/total.md` into individual speaker note files in the `notes/` directory.

**File naming convention**:

- **Recommended**: Match SVG names (e.g., `01_cover.svg` → `notes/01_cover.md`)
- **Compatible**: Also supports `slide01.md` format (backward compatibility)

---

## 9. Next Steps After Completion

> **Auto-continuation**: After Visual Construction Phase (all SVG pages) and Logic Construction Phase (all notes) are complete, the Executor proceeds directly to the post-processing pipeline.

**Post-processing & Export** (see [shared-standards.md](shared-standards.md)):

```bash
# 1. Split speaker notes
python3 scripts/total_md_split.py <project_path>

# 2. SVG post-processing (auto-embed icons, images, etc.)
python3 scripts/finalize_svg.py <project_path>

# 3. Export PPTX
python3 scripts/svg_to_pptx.py <project_path> -s final
# Output: exports/<project_name>_<timestamp>.pptx + exports/<project_name>_<timestamp>_svg.pptx
```
