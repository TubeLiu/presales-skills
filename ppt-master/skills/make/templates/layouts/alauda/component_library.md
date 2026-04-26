# Alauda Component Library — Atomic SVG Primitives

> This file defines the reusable atomic components of the Alauda design system.
> The Executor should compose pages by combining these primitives rather than
> inventing ad-hoc shapes. All code snippets use the Alauda color palette and
> are ready to copy-paste into any `viewBox="0 0 1280 720"` SVG canvas.

---

## 1. Card Family

### 1.1 Basic Card (Accent-Bar Top)

The standard Alauda card. A white/light-gray rounded rectangle with a colored
accent bar on top. Used for feature blocks, capability items, and general
information containers.

```xml
<!-- Basic Card — adjust x/y/width/height as needed -->
<rect x="60" y="140" width="360" height="200" fill="#F8FAFC" rx="8" stroke="#E2E8F0" stroke-width="1"/>
<rect x="60" y="140" width="360" height="6" fill="#3BAEE3" rx="3"/>
<!-- Card title -->
<text x="84" y="180" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="16" font-weight="bold" fill="#334155">Card Title</text>
<!-- Card body -->
<text x="84" y="210" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#475569">Card description text.</text>
```

**Accent bar color rotation** (use in sequence for multi-card layouts):
1. `#3BAEE3` — Alauda Blue
2. `#14B8A6` — Teal
3. `#25B273` — Green
4. `#125B7D` — Deep Teal
5. `#FFC832` — Amber
6. `#FE574C` — Red (warning/contrast only)

### 1.2 Side-Accent Card (Left Bar)

Used for bullet-point items, detail rows, and list entries.

```xml
<rect x="60" y="200" width="500" height="100" fill="#F8FAFC" rx="6" stroke="#E2E8F0" stroke-width="1"/>
<rect x="60" y="200" width="4" height="100" fill="#3BAEE3" rx="2"/>
<text x="84" y="236" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="16" font-weight="bold" fill="#334155">Item Title</text>
<text x="84" y="264" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#475569">Item description.</text>
```

### 1.3 KPI Metric Card

Large number + label + optional description. Used for data highlights.

```xml
<rect x="60" y="140" width="270" height="200" fill="#F8FAFC" rx="8" stroke="#E2E8F0" stroke-width="1"/>
<rect x="60" y="140" width="4" height="200" fill="#3BAEE3" rx="2"/>
<text x="88" y="210" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="48" font-weight="bold" fill="#3BAEE3">72%</text>
<text x="88" y="245" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="16" font-weight="bold" fill="#334155">Metric Label</text>
<text x="88" y="275" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="13" fill="#94A3B8">Supporting context.</text>
```

### 1.4 Dark KPI Metric Card

For dark background pages. Semi-transparent white card with colored top accent.

```xml
<rect x="60" y="140" width="270" height="220" fill="#FFFFFF" fill-opacity="0.08" rx="8"/>
<rect x="60" y="140" width="270" height="4" fill="#3BAEE3" rx="2"/>
<text x="88" y="170" font-family="Aptos, sans-serif" font-size="12" fill="#3BAEE3" letter-spacing="1">01</text>
<text x="88" y="240" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="52" font-weight="bold" fill="#FFFFFF">3.2K</text>
<text x="88" y="275" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="16" font-weight="bold" fill="#FFFFFF">Metric Label</text>
<text x="88" y="305" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="13" fill="#FFFFFF" fill-opacity="0.5">Context.</text>
```

### 1.5 Numbered Card

Card with a large semi-transparent number prefix. Used for ordered lists and
differentiation layouts.

```xml
<rect x="60" y="120" width="360" height="240" fill="#F8FAFC" rx="8" stroke="#E2E8F0" stroke-width="1"/>
<rect x="60" y="120" width="360" height="6" fill="#3BAEE3" rx="3"/>
<text x="88" y="175" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="40" font-weight="bold" fill="#3BAEE3" fill-opacity="0.2">01</text>
<text x="148" y="175" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="20" font-weight="bold" fill="#334155">Card Title</text>
<text x="88" y="210" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#475569">Description text.</text>
```

### 1.6 Tag / Badge

Small colored pill for category labels.

```xml
<!-- Blue tag -->
<rect x="80" y="155" width="100" height="28" fill="#D8EFF9" rx="4"/>
<text x="130" y="174" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="12" font-weight="bold" fill="#125B7D">Tag Label</text>

<!-- Teal tag -->
<rect x="80" y="155" width="100" height="28" fill="#CCFBF1" rx="4"/>
<text x="130" y="174" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="12" font-weight="bold" fill="#0F766E">Tag Label</text>
```

---

## 2. Structure Components

### 2.1 Before / After Block

Colored panel with a header bar. Red for "before", green for "after", blue for
neutral/bridge.

```xml
<!-- BEFORE block (red) -->
<rect x="60" y="130" width="400" height="400" fill="#FEF2F2" rx="8" stroke="#FECACA" stroke-width="1"/>
<rect x="60" y="130" width="400" height="44" fill="#FE574C" rx="8"/>
<rect x="60" y="152" width="400" height="22" fill="#FE574C"/>
<text x="90" y="160" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="14" font-weight="bold" fill="#FFFFFF" letter-spacing="2">BEFORE</text>

<!-- AFTER block (green) -->
<rect x="500" y="130" width="400" height="400" fill="#F0FDF4" rx="8" stroke="#BBF7D0" stroke-width="1"/>
<rect x="500" y="130" width="400" height="44" fill="#25B273" rx="8"/>
<rect x="500" y="152" width="400" height="22" fill="#25B273"/>
<text x="530" y="160" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="14" font-weight="bold" fill="#FFFFFF" letter-spacing="2">AFTER</text>

<!-- BRIDGE block (blue) -->
<rect x="280" y="130" width="400" height="400" fill="#EFF6FF" rx="8" stroke="#BFDBFE" stroke-width="1"/>
<rect x="280" y="130" width="400" height="44" fill="#3BAEE3" rx="8"/>
<rect x="280" y="152" width="400" height="22" fill="#3BAEE3"/>
<text x="310" y="160" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="14" font-weight="bold" fill="#FFFFFF">Migration Path</text>
```

### 2.2 Layered Band

Horizontal full-width band for architecture layers. Darker = more important.

```xml
<!-- Primary layer (strongest) -->
<rect x="160" y="130" width="960" height="100" fill="#D8EFF9" rx="6" stroke="#3BAEE3" stroke-width="1"/>
<text x="640" y="172" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="16" font-weight="bold" fill="#125B7D">Layer Title</text>
<text x="640" y="196" text-anchor="middle" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="13" fill="#475569">Layer description</text>

<!-- Secondary layer -->
<rect x="160" y="250" width="960" height="100" fill="#EFF6FF" rx="6" stroke="#3BAEE3" stroke-width="1" stroke-opacity="0.6"/>

<!-- Tertiary layer -->
<rect x="160" y="370" width="960" height="100" fill="#F1F5F9" rx="6" stroke="#E2E8F0" stroke-width="1"/>

<!-- Base layer (lightest) -->
<rect x="160" y="490" width="960" height="100" fill="#F8FAFC" rx="6" stroke="#E2E8F0" stroke-width="1"/>
```

### 2.3 Layer Header Bar

Colored header bar on top of a content panel. Used for panorama and canvas views.

```xml
<rect x="60" y="130" width="400" height="300" fill="#EFF6FF" rx="8" stroke="#3BAEE3" stroke-width="1" stroke-opacity="0.5"/>
<rect x="60" y="130" width="400" height="36" fill="#3BAEE3" rx="8"/>
<rect x="60" y="150" width="400" height="16" fill="#3BAEE3"/>
<text x="260" y="155" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="14" font-weight="bold" fill="#FFFFFF">Section Title</text>
```

### 2.4 Nested Capability Block

Small white block inside a layered band. Used to show individual capabilities
within a platform layer.

```xml
<rect x="80" y="265" width="175" height="110" fill="#FFFFFF" rx="6" stroke="#E2E8F0" stroke-width="1"/>
<text x="168" y="300" text-anchor="middle" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="13" font-weight="bold" fill="#334155">Capability</text>
<text x="168" y="322" text-anchor="middle" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="11" fill="#94A3B8">Sub-description</text>
```

---

## 3. Process & Flow

### 3.1 Step Circle + Label

Numbered circle on a connecting line. Color rotates per step.

```xml
<!-- Step node -->
<circle cx="200" cy="300" r="28" fill="#3BAEE3"/>
<text x="200" y="307" text-anchor="middle" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="20" font-weight="bold" fill="#FFFFFF">1</text>
<!-- Step title (below) -->
<text x="200" y="355" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="18" font-weight="bold" fill="#334155">Step Title</text>
```

**Step color sequence**: `#3BAEE3` → `#14B8A6` → `#25B273` → `#125B7D` → `#FFC832`

### 3.2 Connector Line

Horizontal backbone connecting process steps.

```xml
<line x1="100" y1="300" x2="1180" y2="300" stroke="#E2E8F0" stroke-width="3"/>
```

### 3.3 Directional Arrow

Solid arrow for flow direction between blocks. Use `<polygon>` (not `marker-end`).

```xml
<!-- Right-pointing arrow -->
<polygon points="635,390 655,378 655,384 680,384 680,396 655,396 655,402" fill="#3BAEE3"/>

<!-- Down-pointing arrow -->
<polygon points="630,234 650,234 640,248" fill="#3BAEE3" fill-opacity="0.4"/>
```

### 3.4 Timeline Node

Circle with inner dot, positioned on the timeline backbone.

```xml
<circle cx="300" cy="300" r="16" fill="#3BAEE3"/>
<circle cx="300" cy="300" r="6" fill="#FFFFFF"/>
<!-- Year/date label above -->
<text x="300" y="265" text-anchor="middle" font-family="&quot;Aptos Display&quot;, sans-serif" font-size="18" font-weight="bold" fill="#3BAEE3">2024</text>
```

---

## 4. Information Containers

### 4.1 Lead Statement Banner

Highlighted single-line summary at the top of a page. Blue-tinted background
with left accent bar.

```xml
<rect x="60" y="100" width="1160" height="60" fill="#D8EFF9" rx="6"/>
<rect x="60" y="100" width="6" height="60" fill="#3BAEE3" rx="3"/>
<text x="88" y="138" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="18" font-weight="bold" fill="#125B7D">Key insight or judgment statement.</text>
```

### 4.2 Thesis Block (Evidence Header)

Larger banner for stating a core thesis, with source attribution.

```xml
<rect x="60" y="100" width="1160" height="120" fill="#D8EFF9" rx="8"/>
<rect x="60" y="100" width="8" height="120" fill="#3BAEE3" rx="4"/>
<text x="96" y="148" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="24" font-weight="bold" fill="#125B7D">Core thesis statement</text>
<text x="96" y="185" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#475569">— Source attribution</text>
```

### 4.3 Quote Block

Dark rounded container with large quotation marks.

```xml
<rect x="60" y="80" width="1160" height="520" fill="#125B7D" rx="12"/>
<!-- Open quote -->
<text x="140" y="210" font-family="Georgia, serif" font-size="120" fill="#3BAEE3" fill-opacity="0.3">&#x201C;</text>
<!-- Quote text -->
<text x="180" y="280" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="26" fill="#FFFFFF" font-weight="500">Quote content here.</text>
<!-- Divider -->
<line x1="180" y1="430" x2="340" y2="430" stroke="#3BAEE3" stroke-width="2"/>
<!-- Attribution -->
<text x="180" y="470" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="18" font-weight="bold" fill="#FFFFFF">Speaker Name</text>
<text x="180" y="500" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#FFFFFF" fill-opacity="0.6">Title · Organization</text>
```

### 4.4 Code Terminal Block

Dark code display with browser-like chrome.

```xml
<!-- Terminal container -->
<rect x="60" y="100" width="700" height="500" fill="#1E293B" rx="8"/>
<!-- Title bar -->
<rect x="60" y="100" width="700" height="36" fill="#334155" rx="8"/>
<rect x="60" y="124" width="700" height="12" fill="#334155"/>
<!-- Traffic light dots -->
<circle cx="84" cy="118" r="5" fill="#FE574C"/>
<circle cx="100" cy="118" r="5" fill="#FFC832"/>
<circle cx="116" cy="118" r="5" fill="#25B273"/>
<!-- Filename label -->
<text x="400" y="123" text-anchor="middle" font-family="Aptos, sans-serif" font-size="12" fill="#94A3B8">filename.yaml</text>
<!-- Code text -->
<text x="88" y="170" font-family="'JetBrains Mono', 'Fira Code', monospace" font-size="14" fill="#E2E8F0">code content</text>
```

### 4.5 Browser Screenshot Frame

Wrapper for product screenshots / UI demos.

```xml
<rect x="60" y="130" width="1160" height="480" fill="#F1F5F9" rx="8" stroke="#E2E8F0" stroke-width="1"/>
<!-- Browser chrome -->
<rect x="60" y="130" width="1160" height="32" fill="#E2E8F0" rx="8"/>
<rect x="60" y="150" width="1160" height="12" fill="#E2E8F0"/>
<circle cx="84" cy="146" r="5" fill="#FE574C"/>
<circle cx="100" cy="146" r="5" fill="#FFC832"/>
<circle cx="116" cy="146" r="5" fill="#25B273"/>
```

---

## 5. Table Components

### 5.1 Table Header Row

```xml
<rect x="60" y="130" width="1160" height="48" fill="#125B7D" rx="6"/>
<rect x="60" y="158" width="1160" height="20" fill="#125B7D"/>
<text x="200" y="161" text-anchor="middle" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="14" font-weight="bold" fill="#FFFFFF">Column Header</text>
<!-- Column separator -->
<line x1="340" y1="140" x2="340" y2="172" stroke="#FFFFFF" stroke-width="1" stroke-opacity="0.3"/>
```

### 5.2 Table Data Row (Alternating)

```xml
<!-- Even row (gray) -->
<rect x="60" y="178" width="1160" height="80" fill="#F8FAFC"/>
<line x1="60" y1="258" x2="1220" y2="258" stroke="#E2E8F0" stroke-width="1"/>
<text x="200" y="224" text-anchor="middle" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="14" fill="#334155">Cell Value</text>

<!-- Odd row (white) -->
<rect x="60" y="258" width="1160" height="80" fill="#FFFFFF"/>
<line x1="60" y1="338" x2="1220" y2="338" stroke="#E2E8F0" stroke-width="1"/>
```

---

## 6. Page Frame Components

### 6.1 Page Header (All Content Pages — Master Frame)

The canonical Alauda content-page header, extracted from the original PPTX master EMF. Use this on every light content page. (No top accent bar; the left edge block is the page-identity marker.)

```xml
<!-- White background -->
<rect width="1280" height="720" fill="#FFFFFF"/>

<!-- Background geometric decorations (right-bottom corner, subtle) -->
<circle cx="1350" cy="600" r="280" fill="#3BAEE3" fill-opacity="0.04"/>
<circle cx="1400" cy="250" r="220" fill="#3BAEE3" fill-opacity="0.03"/>
<ellipse cx="1150" cy="780" rx="350" ry="130" fill="#3BAEE3" fill-opacity="0.02"/>

<!-- Left edge accent bar (PPTX: pos 0,29 size 22x45) -->
<rect x="0" y="29" width="22" height="45" fill="#3BAEE3"/>

<!-- Page title (right next to the accent block) -->
<text x="46" y="55" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="37" font-weight="bold" fill="#334155">Page Title</text>
```

**Dark page variant** — same frame, inverted colors:

```xml
<!-- Dark background (gradient or solid) -->
<rect width="1280" height="720" fill="url(#darkBgGrad)"/>

<!-- Background decorations (white, lower opacity for dark bg) -->
<circle cx="1350" cy="600" r="280" fill="#FFFFFF" fill-opacity="0.03"/>
<circle cx="1400" cy="250" r="220" fill="#FFFFFF" fill-opacity="0.02"/>
<ellipse cx="1150" cy="780" rx="350" ry="130" fill="#FFFFFF" fill-opacity="0.015"/>

<!-- Left edge accent bar (always Alauda Blue, even on dark) -->
<rect x="0" y="29" width="22" height="45" fill="#3BAEE3"/>

<!-- Page title (white on dark) -->
<text x="46" y="55" font-family="&quot;Aptos Display&quot;, &quot;PingFang SC&quot;, sans-serif" font-size="37" font-weight="bold" fill="#FFFFFF">Page Title</text>
```

> **Why this frame and not a top 4px bar?** The original Alauda PowerPoint master uses the left edge block (extracted coordinates: `pos 0,29 size 22x45`) as the canonical identity marker, not a top accent bar. The top-bar variant that once appeared in `03_content.svg`, `03_content_cards.svg`, `03_content_process.svg`, etc. was a simplified departure — all content variants have been migrated back to the master frame.

### 6.2 Key Message Line (Subtitle)

Optional one-line takeaway below the page title. Placed at y=95 so it sits just below the title.

```xml
<!-- Light page -->
<text x="32" y="95" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="21" fill="#334155">One-sentence key message or takeaway.</text>

<!-- Dark page -->
<text x="32" y="95" font-family="Aptos, &quot;PingFang SC&quot;, sans-serif" font-size="21" fill="#FFFFFF" fill-opacity="0.7">One-sentence key message or takeaway.</text>
```

### 6.3 Page Footer (Light Background)

```xml
<line x1="0" y1="682" x2="1280" y2="682" stroke="#E2E8F0" stroke-width="1"/>
<text x="60" y="706" font-family="Aptos, sans-serif" font-size="12" fill="#94A3B8" letter-spacing="1">Alauda</text>
<text x="1220" y="706" text-anchor="end" font-family="Aptos, sans-serif" font-size="12" fill="#94A3B8">Page Number</text>
```

### 6.4 Page Footer (Dark Background)

```xml
<line x1="60" y1="682" x2="1220" y2="682" stroke="#FFFFFF" stroke-width="1" stroke-opacity="0.1"/>
<text x="60" y="706" font-family="Aptos, sans-serif" font-size="12" fill="#FFFFFF" fill-opacity="0.4" letter-spacing="1">Alauda</text>
<text x="1220" y="706" text-anchor="end" font-family="Aptos, sans-serif" font-size="12" fill="#FFFFFF" fill-opacity="0.4">Page Number</text>
```

### 6.5 Dark Page Background

Full dark gradient + texture overlay.

```xml
<defs>
    <linearGradient id="darkBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#125B7D"/>
        <stop offset="100%" style="stop-color:#0D3F56"/>
    </linearGradient>
</defs>
<rect width="1280" height="720" fill="url(#darkBgGrad)"/>
<image x="0" y="0" width="1280" height="720" href="dark_grid_texture.png" preserveAspectRatio="xMidYMid slice"/>
<rect x="0" y="0" width="1280" height="720" fill="#125B7D" fill-opacity="0.7"/>
<rect x="0" y="0" width="1280" height="4" fill="#3BAEE3"/>
```

---

## 7. Decorative Elements

### 7.1 Geometric Accent (Light Pages)

Low-opacity shapes for visual interest on right/corner areas.

```xml
<rect x="880" y="100" width="320" height="320" fill="none" stroke="#3BAEE3" stroke-width="1" stroke-opacity="0.12"/>
<rect x="920" y="140" width="240" height="240" fill="none" stroke="#3BAEE3" stroke-width="1" stroke-opacity="0.08"/>
<circle cx="1040" cy="520" r="80" fill="none" stroke="#3BAEE3" stroke-width="1" stroke-opacity="0.10"/>
```

### 7.2 Divider Combo

Two-line divider with accent.

```xml
<line x1="60" y1="380" x2="400" y2="380" stroke="#E2E8F0" stroke-width="2"/>
<line x1="60" y1="386" x2="160" y2="386" stroke="#3BAEE3" stroke-width="2"/>
```

### 7.3 Vertical Sidebar Label

Rotated text for sidebar annotations.

```xml
<rect x="60" y="130" width="40" height="400" fill="#125B7D" fill-opacity="0.1" rx="4"/>
<text x="80" y="330" text-anchor="middle" font-family="Aptos, sans-serif" font-size="12" fill="#125B7D" transform="rotate(-90,80,330)">SIDEBAR LABEL</text>
```

---

## Usage Notes

1. **Color rotation**: When placing multiple cards/steps in a row, rotate through
   the accent colors in order: Blue → Teal → Green → Deep Teal → Amber.
2. **Spacing**: Maintain 24px gap between cards, 40px page margins (60px left/right).
3. **Font consistency**: Always use `"Aptos Display"` for titles/headings, `Inter` for body.
   Include `"PingFang SC"` in the fallback stack for Chinese text.
4. **Dark vs light**: Use dark components only on dark background pages. Do not mix.
5. **SVG constraints**: No `clipPath`, `mask`, `<style>`, `class`, `rgba()`,
   `<g opacity>`, `foreignObject`. See `design_spec.md` Section IX for full list.
