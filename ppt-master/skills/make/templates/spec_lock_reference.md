# Execution Lock

> **⚠️ This file is a REFERENCE skeleton for Strategist — do NOT copy it verbatim into a project.** When producing `<project_path>/spec_lock.md`, emit only the structural `##` sections with their filled-in `-` data lines. Do NOT carry over any `>` blockquote guidance, callout boxes, HARD-rule notes, or `> ```code fence` override examples from this file — those are author-time guidance for Strategist, not runtime data. The output is a machine-readable contract; every line must be parseable data.
>
> Machine-readable execution contract. Executor MUST `read_file` this before every SVG page. Values NOT listed here must NOT appear in SVGs. For design narrative (rationale, audience, style), see `design_spec.md`.
>
> After SVG generation begins, this file is the canonical source for color / font / icon / image values. Modifications should go through `scripts/update_spec.py` so both this file and the generated SVGs stay in sync.

## template_lock
- template: alauda
- source_dir: templates
- routes_required: true
- variant_files_present: 31

> **Mandatory section.** Declares the layout-template commitment for this deck so downstream Executor cannot silently degrade a branded template into the generic `03_content.svg` fallback. `scripts/spec_lock_validator.py` reads this section before Step 5 / Step 6 / Step 7 enter and blocks the pipeline if the contract is violated.
>
> **Field semantics**:
> - `template` — Directory name copied by Step 3 (e.g. `alauda`, `mckinsey`, `academic_defense`). **Empty string `""`** is the only legal value for free design (no template package copied).
> - `source_dir` — Path inside the project where the template package was copied (default `templates`). Validator looks here for `semantic_routes.json` and `*.svg` variants.
> - `routes_required` — `true` when the template package ships `semantic_routes.json`; the validator will require `## semantic_routes` to be filled and reference real variant files. `false` only for legacy minimal templates without a route catalog, or for free design.
> - `variant_files_present` — Strategist writes the count of `*.svg` files under `source_dir` at lock time. Sanity field; the validator does not parse it but it surfaces "the template was actually copied" at a glance during human review.
>
> **Free design escape hatch (must be explicit)**:
>
> ```
> ## template_lock
> - template: ""
> - source_dir: templates
> - routes_required: false
> - variant_files_present: 0
> ```
>
> Any other combination (e.g. `template: alauda` + `routes_required: false`) is treated as a contradiction and rejected. This wires the CLAUDE.md §6 anti-hardcoding rule "例外要显式建模" into spec_lock.

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

> Strategist: fill the viewBox and format for the chosen canvas. Common values: `0 0 1280 720` (PPT 16:9), `0 0 1024 768` (PPT 4:3), `0 0 1242 1660` (Xiaohongshu), `0 0 1080 1080` (WeChat Moments), `0 0 1080 1920` (Story).

## colors
- bg: #FFFFFF
- primary: #......
- accent: #......
- secondary_accent: #......
- text: #......
- text_secondary: #......
- border: #......

> Strategist: fill only the colors actually used in this deck. Extra rows may be added; unused rows should be deleted rather than left as `#......`.

## typography
- font_family: "Microsoft YaHei", Arial, sans-serif
- title_family: Georgia, SimSun, serif
- body_family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif
- emphasis_family: Georgia, SimSun, serif
- code_family: Consolas, "Courier New", monospace
- body: 22
- title: 32
- subtitle: 24
- annotation: 14

> **All five family lines are listed explicitly** so Strategist considers every role when filling this block — easy to forget `code_family` or `emphasis_family` otherwise. In a real project's `spec_lock.md`:
> - Keep any `*_family` whose role genuinely differs from `font_family`.
> - **Omit** any `*_family` whose value would equal `font_family` — Executor falls back to `font_family` for missing roles, so writing it twice is noise. (Exception: keep `code_family` even if equal, since it's the conceptually distinct monospace role.)
>
> `font_family` is the default fallback for roles without an explicit override. Every declared family is a CSS font-stack string.
>
> **Source of these strings**: they are the *Per-role font stacks* list from `design_spec.md §IV Font Plan` — copy across verbatim. The breakdown table in `design_spec.md` (Chinese / English / Fallback columns) is the human-readable accompaniment; the ordered CSS stack strings live here (and in `design_spec.md`) and must match character-for-character. Stack **order** carries browser-rendering intent (Latin-led vs. CJK-led) that the breakdown table alone cannot encode — see the explainer in `design_spec.md §IV`.
>
> Sizes (`body` / `title` / etc.) are in px, matching SVG native units. `body` is the **required baseline anchor** — every other size in the deck is derived as a ratio of it (see ramp table in `design_spec_reference.md §IV`).
>
> **Size slots are anchors, not a closed menu.** The common slots (`title` / `subtitle` / `annotation`) cover frequent cases. Add role-specific slots (e.g. `cover_title: 72`, `hero_number: 48`, `chart_annotation: 13`) when a deck genuinely needs them — this is expected for cover-heavy decks, consulting-style hero numbers, and information-dense pages. Executor may use intermediate sizes as long as the size's ratio to `body` sits within the corresponding role's band in the ramp table.
>
> **⚠️ PPT-safe stack discipline (HARD rule).** PPTX stores one `typeface` per text run; there is no runtime fallback. Every stack here MUST end with a cross-platform pre-installed font: `"Microsoft YaHei", sans-serif` / `SimSun, serif` / `Arial, sans-serif` / `"Times New Roman", serif` / `Consolas, "Courier New", monospace`. Non-pre-installed fonts (Inter / Google Fonts / brand typefaces) may lead the stack only when the Design Spec explicitly notes the font-install or font-embedding requirement.
>
> **Stack length discipline.** 3-4 fonts per stack is the sweet spot. Converter only writes the **first** Latin and **first** CJK font into PPTX — everything after is silently dropped. macOS-only families (`Songti SC`, `Menlo`, `Monaco`, `Helvetica`) are auto-mapped to their Windows equivalents via `FONT_FALLBACK_WIN` (see `scripts/svg_to_pptx/drawingml_utils.py`), so stacking both the macOS family and its Windows equivalent is redundant. Lead with Windows-preinstalled fonts (`Microsoft YaHei` / `SimSun` / `Arial` / `Georgia` / `Consolas`); keep at most **one** macOS-exclusive family (typically `"PingFang SC"`) as a browser-preview nicety.

## icons
- library: chunk
- inventory: target, bolt, shield, users, chart-bar, lightbulb

> `library` MUST be one of `chunk` / `tabler-filled` / `tabler-outline` (exactly one — mixing is forbidden). `inventory` lists the approved icon names (without library prefix); Executor may only use icons from this list.

## images
- cover_bg: images/cover_bg.jpg

> One entry per image file actually used. Remove the section entirely if the deck uses no images.

## page_rhythm
- P01: anchor
- P02: dense
- P03: breathing
- P04: dense
- P05: dense
- P06: breathing
- P07: anchor

> One entry per page. Key format: `P<NN>` (zero-padded two-digit page index matching `§IX Content Outline` in `design_spec.md`). Value is one of the three rhythm tags below. This field exists to break the "every page looks the same" pattern — Executor reads it per page and applies the tag's layout discipline.
>
> **Vocabulary** (exactly these three values):
> - `anchor` — Structural pages (cover / chapter opener / TOC / ending). Follow the corresponding template as-is.
> - `dense` — Information-heavy pages (data, KPIs, comparisons, multi-point lists). Card grids, multi-column layouts, tables, and charts are all permitted.
> - `breathing` — Low-density pages (single concept, hero quote, big image + caption, section transition). Avoid **multi-card grid layouts** (multiple parallel rounded containers as the primary content structure); organize with naked text, dividers, whitespace, or full-bleed imagery instead. Single rounded visual elements (hero image corners, callouts, tags, one emphasis block) are fine. Proportions follow information weight — not a preset ratio menu.
>
> **Rhythm follows narrative** (for Strategist when filling this section): `breathing` pages appear where the narrative genuinely pauses — section transitions, a single argument worth standalone emphasis, a deliberate stop after a dense sequence. A high-density data briefing or consulting analysis may legitimately be nearly all `dense` — **do not invent filler pages** to pad the rhythm. Validation: every `breathing` page must answer "what independent thing is this page saying?".
>
> **Missing or empty section** → Executor falls back to `dense` for every page (current pre-rhythm behavior). Remove the whole section only for legacy decks; new decks authored by Strategist MUST fill it.

## design_diversity
- source: design_quality_checker.py deckDiversity
- target_archetypes: at least 3 visual archetypes for decks with 6+ non-structural pages when source content contains mixed semantics
- dominant_archetype_limit: <=55% unless the whole deck is intentionally a single artifact type such as a pure table appendix
- card_grid_limit: <=45% for client-facing technical decks; route content into architecture stacks, process flows, matrices, code annotations, argument pages, KPI dashboards, or comparison bridges when appropriate
- P02: kpi_dashboard
- P03: architecture_stack
- P04: comparison_bridge
- P05: matrix_table
- P06: process_flow

> Per-page value is the intended visual archetype, not a rigid template name.
> Strategist fills it from the page's source semantics. Executor preserves it
> using component roles and visual grammar. The design checker verifies the
> generated deck has real archetype variety instead of repeated card grids.

## density_contract
- source: design_archetype_planner.py
- policy: visible page content must expose source objects, relationships, and evidence; speaker notes are overflow, not the default hiding place
- target: avoid AI-sparse slides by giving each page visible information minimums before SVG generation
- P02: visible_claims>=3; visible_objects>=8; visible_labels>=12; evidence_items>=2; relationships>=3; notes_only_ratio<=0.38; fill=0.50-0.72 | expose=source-specific terms
- P03: visible_claims>=3; visible_objects>=10; visible_labels>=14; evidence_items>=1; relationships>=3; notes_only_ratio<=0.40; fill=0.52-0.74 | expose=source-specific terms

> One entry per content page when source material contains concrete details.
> This is the contract that prevents the model from hiding detailed source
> material in notes and drawing only three abstract cards. Values are minimums,
> not exact quotas. Executor should satisfy the contract through appropriate
> visual forms: tables, annotations, swimlanes, architecture layers, KPI chips,
> mapping rows, or dense callouts. If a page is intentionally sparse, it must be
> justified by page rhythm / archetype and should carry a lower contract.

## semantic_routes
- P02: platform_panorama | 03_content_panorama.svg | domain_row_platform_core_infra_row | title<=18; key_message<=36; notes_overflow=yes
- P03: architecture_stack | 03_content_architecture.svg | four_layer_stack_with_downward_dependency | layer_title<=12; layer_desc<=38; notes_overflow=yes
- P04: migration_bridge | 03_content_migration.svg | before_bridge_after | panel_title<=12; panel_desc<=3 lines; notes_overflow=yes

> One entry per non-structural content page (cover/toc/chapter/ending excluded).
> **Mandatory whenever `template_lock.routes_required=true`** — i.e. the project
> has copied a template package that ships `templates/semantic_routes.json` (e.g.
> the Alauda layout). `scripts/spec_lock_validator.py` cross-checks every entry
> against the catalog and against `*.svg` files in `source_dir`; missing entries
> or unknown variants block Step 5 / Step 6 / Step 7. Key format:
> `P<NN>` matching `§IX Content Outline`. Value format is intentionally a
> compact pipe-delimited string:
>
> `page_intent | template_variant | visual_grammar | payload_budget`
>
> This section is what lets Executor choose a concrete content-page variant
> before drawing SVG. The route must match the **Semantic Route** block in
> `design_spec.md §IX`. If no route fits, use:
>
> `custom_content | 03_content.svg | alauda_frame_custom_content | notes_overflow=yes`
>
> Payload budgets are short guardrails, not prose containers. If source
> material exceeds the budget, keep the visual slot concise and move the
> detail to speaker notes.

## visual_system
- source: templates/visual_system.json
- component_library: templates/component_library.md
- icon_library: chunk
- icon_inventory: cube, server, database, cloud-arrow-up, robot, shield-check, route, git-branch, card-stack, checkmark, target, arrows-repeat
- default_density: dense_technical
- density_dense_technical: related_gap=12; group_gap=24; outer_margin=56; min_text_box_height=22; max_nested_levels=3; max_visible_micro_labels=34
- density_balanced_technical: related_gap=16; group_gap=32; outer_margin=60; min_text_box_height=26; max_nested_levels=2; max_visible_micro_labels=22
- connector_policy: min_text_lane_gap=72; route_through_whitespace=yes; avoid_title_row=yes; applies_to_all_connectors=yes
- customer_canvas: no_visible_internal_metadata=yes; metadata_destination=notes_or_eval_report
- route_quality_rules: apply matching templates/visual_system.json.routeQualityRules per page_intent
- P02: dense_technical | layer_header_bar,nested_capability_block,tag_badge,layered_band | cube,server,database,cloud-arrow-up,robot,shield-check
- P03: dense_technical | layered_band,side_accent_card,tag_badge,connector_line | layers,server,cube,database,shield,robot
- P04: balanced_technical | before_after_block,directional_arrow,step_circle_label,connector_line | route,arrows-repeat,cloud-arrow-up,circle-checkmark,shield-check

> One entry per template package with a visual execution contract
> (`templates/visual_system.json`). **Mandatory whenever the package ships
> `visual_system.json`** — i.e. paired with `template_lock.routes_required=true`.
> Global lines declare the component library,
> icon library/inventory, density profile constants, and connector policy.
> Per-page lines mirror the page's **Semantic Route** block in
> `design_spec.md §IX` using the compact format:
>
> `P<NN>: density | component_names | icon_names`
>
> Executor uses this section to choose component primitives and enforce
> density/spacing before writing SVG. If no visual system file exists, omit the
> section entirely.

## design_semantics
- default_text_policy: colored labels, chips, buttons, table headers, step circles, and small status blocks are centered horizontally and vertically
- left_aligned_exception: only paragraph/card content areas with explicit padding; mark owning shape/text with data-role="content-card" or data-role="callout-content" plus data-text-align="left"
- required_svg_attrs: data-role, data-slot, data-group, data-intent, data-text-align where needed
- P02: components=layer-header,capability-card,platform-conclusion | slots=header-label,card-title,label-slot,body-callout | text_policy=labels_centered; conclusion_left_padded
- P03: components=layer-stack,decision-card,dependency-connector | slots=layer-title,layer-body,connector-lane | text_policy=layer_titles_left_padded; connector_labels_centered
- P04: components=migration-bridge,source-card,target-card,step-strip | slots=bridge-title,row-label,row-detail,step-number | text_policy=headers_centered; row_body_left_padded

> Per-page format:
>
> `P<NN>: components=<roles> | slots=<slot roles> | text_policy=<default and exceptions>`
>
> Executor must translate these roles into SVG `data-*` attributes. The design
> quality checker uses this semantic layer to evaluate component→slot→text
> coverage without relying on brittle color or width heuristics.

## quality_samples
- source: templates/human_quality_rubric.json
- rotation_policy: 3 non-structural pages; different page_intent values; include one dense technical page when available; avoid repeating the previous iteration's first sample
- P03: architecture_stack | dense_technical | layered technical diagram quality sample
- P05: mapping_table | dense_technical | compact editable mapping quality sample
- P07: migration_bridge | balanced_technical | transition narrative quality sample

> One section per template package with a human-quality rubric. These entries
> select the first pages to inspect after generation. They do **not** reduce the
> deck scope; Executor still generates every page in `design_spec.md §IX`.
> Rotate these page numbers and route intents between quality iterations to
> avoid repeatedly polishing the same SVG.
>
> Per-page format:
>
> `P<NN>: page_intent | density | review_reason`

## forbidden
- Mixing icon libraries
- rgba()
- `<style>`, `class`, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>`, `<symbol>`+`<use>`
- `<g opacity>` (set opacity on each child element individually)
