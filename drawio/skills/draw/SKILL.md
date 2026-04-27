---
name: draw
description: >
  画图 / 生成流程图 / 架构图 / 拓扑图 / 时序图 / ER 图 / 类图 / UML / 网络图 /
  ML 模型图 / 线框图 时触发；亦支持 6 种 preset（ERD / UML class / sequence /
  architecture / ML/DL / flowchart）+ animated connectors + style presets +
  自定义 output dir。生成 .drawio XML，可选导出 PNG/SVG/PDF/JPG。3+ 组件复杂
  关系时 proactively 触发。draw / generate / design diagram / flowchart /
  architecture / sequence / class / network / mockup / wireframe / UI sketch
  时触发。
allowed-tools: Read, Write, Bash, Glob
---

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能给协调者读。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

## 路径自定位

**首次调用本 skill 的脚本前，先跑一次以下 bootstrap 解析 DRAW_DIR**（后续命令用 `$DRAW_DIR/styles/...` 等）：

```bash
DRAW_DIR=""
for d in "$HOME/.cursor/skills/draw" "$HOME/.agents/skills/draw" \
         "./.cursor/skills/draw" "./.agents/skills/draw" \
         "$HOME/.claude/plugins/cache/presales-skills/drawio/"*"/skills/draw"; do
    [ -d "$d" ] && DRAW_DIR="$d" && break
done
[ -z "$DRAW_DIR" ] && DRAW_DIR="${CLAUDE_PLUGIN_ROOT:-./drawio}/skills/draw"
```

## Overview

Generate `.drawio` XML files and export to PNG/SVG/PDF/JPG locally using the native draw.io desktop app CLI.

**Supported formats:** PNG, SVG, PDF, JPG — no browser automation needed.

## When to Use

**Explicit triggers:** user says "diagram", "visualize", "flowchart", "draw", "architecture diagram", "process flow", "ER diagram", "UML", "sequence diagram", "class diagram", "neural network", "model architecture"

**Proactive triggers:**
- Explaining a system with 3+ interacting components
- Describing a multi-step process or decision tree
- Comparing architectures or approaches side by side

**Skip when:** a simple list or table suffices, or user is in a quick Q&A flow

## Prerequisites

The draw.io desktop app must be installed and the CLI accessible:

```bash
# macOS (Homebrew — recommended)
brew install --cask drawio
draw.io --version

# macOS (full path if not in PATH)
/Applications/draw.io.app/Contents/MacOS/draw.io --version

# Windows
"C:\Program Files\draw.io\draw.io.exe" --version

# Linux
draw.io --version
```

Install draw.io desktop if missing:
- macOS: `brew install --cask drawio` or download from https://github.com/jgraph/drawio-desktop/releases
- Windows: download installer from https://github.com/jgraph/drawio-desktop/releases
- Linux: download `.deb`/`.rpm` from https://github.com/jgraph/drawio-desktop/releases

## Workflow

Before starting the workflow, assess whether the user's request is specific enough. If key details are missing, ask 1-3 focused questions:
- **Diagram type** — which preset? (ERD, UML, Sequence, Architecture, ML/DL, Flowchart, or general)
- **Output format** — PNG (default), SVG, PDF, or JPG?
- **Output location** — default is the user's working dir; honor any explicit path the user gives (e.g. "put it in `./artifacts/`"). Don't ask if they didn't mention one.
- **Scope/fidelity** — how many components? Any specific technologies or labels?

Skip clarification if the request already specifies these details or is clearly simple (e.g., "draw a flowchart of X").

**Style preset fast-path（避免被 preset 系统 railroad）**：

```
Did the user mention any preset name OR is there a default user preset in ~/.drawio-skill/styles/?
├─ NO  → SKIP Step 0.5 entirely. Go straight to Step 1 with built-in colors. Do NOT read references/preset-management.md.
└─ YES → Run Step 0.5 below.
```

> 简单画图（rectangle + arrow / 单图类型 / 用户没提风格）的默认路径**不经过 preset 系统**——直接用 SKILL.md 的 built-in color palette 即可。

**Step 0.5 — Resolve active preset.** Determine which (if any) user-defined style preset applies to this generation.

- Scan the user's message for a phrase that clearly names a style preset: "use my `<name>` style", "with my `<name>` style", "in `<name>` mode", "in the style of `<name>`". A bare `with <name>` does **not** count — "draw a diagram with redis" names a component, not a style. If a clear match is found → active preset = `<name>`.
- Else, check `~/.drawio-skill/styles/` for any file with `"default": true`. If found → active preset = that one.
- Else → no preset active; fall through to the built-in color/shape/edge conventions for the rest of the workflow.

Load the preset JSON from `~/.drawio-skill/styles/<name>.json`, falling back to `$DRAW_DIR/styles/built-in/<name>.json`. If the named preset exists in neither location, tell the user the name is unknown, list the available presets (user dir + built-in), and stop — do **not** silently fall back to defaults.

When a preset loads successfully, mention it in the first line of the reply: *"Using preset `<name>` (confidence: `<level>`)."* See the **Applying a preset** subsection below for how the preset changes color/shape/edge/font decisions.

1. **Check deps** — verify `draw.io --version` succeeds; note platform for correct CLI path
2. **Plan** — identify shapes, relationships, layout (LR or TB), group by tier/layer
3. **Generate** — write `.drawio` XML file to disk. Default output dir is the user's working dir; if the user specified an output path or directory (e.g. `./artifacts/`, `docs/images/`), use that instead — `mkdir -p` the target dir first. Apply the same dir choice to PNG/SVG/PDF exports in steps 4 and 7.
4. **Export draft** — run CLI to produce PNG for preview
5. **Self-check** — use the agent's built-in vision capability to read the exported PNG, catch obvious issues, auto-fix before showing user (requires a vision-enabled model such as Claude Sonnet/Opus)
6. **Review loop** — show image to user, collect feedback, apply targeted XML edits, re-export, repeat until approved
7. **Final export** — export approved version to all requested formats, report file paths

### Step 5: Self-Check

After exporting the draft PNG, use the agent's vision capability (e.g., Claude's image input) to read the image and check for these issues before showing the user. If the agent does not support vision, skip self-check and show the PNG directly:

| Check | What to look for | Auto-fix action |
|-------|-----------------|-----------------|
| Overlapping shapes | Two or more shapes stacked on top of each other | Shift shapes apart by ≥200px |
| Clipped labels | Text cut off at shape boundaries | Increase shape width/height to fit label |
| Missing connections | Arrows that don't visually connect to shapes | Verify `source`/`target` ids match existing cells |
| Off-canvas shapes | Shapes at negative coordinates or far from the main group | Move to positive coordinates near the cluster |
| Edge-shape overlap | An edge/arrow visually crosses through an unrelated shape | Add waypoints (`<Array as="points">`) to route around the shape, or increase spacing between shapes |
| Stacked edges | Multiple edges overlap each other on the same path | Distribute entry/exit points across the shape perimeter (use different exitX/entryX values) |

- Max **2 self-check rounds** — if issues remain after 2 fixes, show the user anyway
- Re-export after each fix and re-read the new PNG

### Step 6: Review Loop

After self-check, show the exported image and ask the user for feedback.

**Targeted edit rules** — for each type of feedback, apply the minimal XML change:

| User request | XML edit action |
|-------------|----------------|
| Change color of X | Find `mxCell` by `value` matching X, update `fillColor`/`strokeColor` in `style` |
| Add a new node | Append a new `mxCell` vertex with next available `id`, position near related nodes |
| Remove a node | Delete the `mxCell` vertex and any edges with matching `source`/`target` |
| Move shape X | Update `x`/`y` in the `mxGeometry` of the matching `mxCell` |
| Resize shape X | Update `width`/`height` in the `mxGeometry` of the matching `mxCell` |
| Add arrow from A to B | Append a new `mxCell` edge with `source`/`target` matching A and B ids |
| Change label text | Update the `value` attribute of the matching `mxCell` |
| Change layout direction | **Full regeneration** — rebuild XML with new orientation |

**Rules:**
- For single-element changes: edit existing XML in place — preserves layout tuning from prior iterations
- For layout-wide changes (e.g., swap LR↔TB, "start over"): regenerate full XML
- Overwrite the same `{name}.png` each iteration — do not create `v1`, `v2`, `v3` files
- After applying edits, re-export and show the updated image
- Loop continues until user says approved / done / LGTM
- **Safety valve:** after 5 iteration rounds, suggest the user open the `.drawio` file in draw.io desktop for fine-grained adjustments

### Step 7: Final Export

Once the user approves:
- Export to all requested formats (PNG, SVG, PDF, JPG) — default to PNG if not specified
- Report file paths for both the `.drawio` source file and exported image(s)
- **Auto-launch:** offer to open the `.drawio` file in draw.io desktop for fine-tuning — `open diagram.drawio` (macOS), `xdg-open` (Linux), `start` (Windows)
- Confirm files are saved and ready to use

## Style Presets

A **style preset** is a named JSON file that captures a user's visual preferences — palette, shape vocabulary, fonts, edge style. When a preset is active, it fully replaces the built-in conventions for color/shape/edge/font.

**Lookup order**: `~/.drawio-skill/styles/<name>.json` (user) → `$DRAW_DIR/styles/built-in/<name>.json` (shipped: `default`, `corporate`, `handdrawn`). User presets shadow built-ins of the same name. Only user presets can carry `"default": true`. All names lowercase.

**Detail references**（按需读取，保持一级深，不要从 preset-management 跳到其他文件）：

- **`references/preset-management.md`** — Learn flow / Manage operations / Validation / Apply 规则 / 与 Diagram Type Preset 冲突解决
- **`references/style-extraction.md`** — 仅 Learn flow 用：从 `.drawio` XML 或图片样本提取 palette / shapes / fonts 的具体算法，sample diagram skeleton 模板
- **`references/diagram-type-presets.md`** — 6 种 diagram type（ERD / UML / Sequence / Architecture / ML-DL / Flowchart）的结构化 shape/edge/layout 表

读取触发：

- **Learn**: "learn my style from `<path>` as `<name>`" / "save this as `<name>` style" → 读 preset-management.md + style-extraction.md
- **Manage**: "list my styles" / "show my `<name>` style" / "make `<name>` the default" / "remove default" / "delete `<name>`" / "rename `<a>` to `<b>`" → 读 preset-management.md
- **Apply** a preset 到当前 diagram → 读 preset-management.md §5

## Draw.io XML Structure

### File skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- user shapes start at id="2" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**Rules:**
- `id="0"` and `id="1"` are required root cells — never omit them
- User shapes start at `id="2"` and increment sequentially
- All shapes have `parent="1"` (unless inside a container — then use container's id)
- All text uses `html=1` in style for proper rendering
- **Never use `--` inside XML comments** — it's illegal per XML spec and causes parse errors
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- **Multi-line text in labels:** use `&#xa;` for line breaks inside `value` attributes (not literal `\n`). Example: `value="Line 1&#xa;Line 2"`

### Shape types (vertex)

| Style keyword | Use for |
|--------------|---------|
| `rounded=0` | plain rectangle (default) |
| `rounded=1` | rounded rectangle — services, modules |
| `ellipse;` | circles/ovals — start/end, databases |
| `rhombus;` | diamond — decision points |
| `shape=mxgraph.aws4.resourceIcon;` | AWS icons |
| `shape=cylinder3;` | cylinder — databases |
| `swimlane;` | group/container with title bar |

### Required properties

```xml
<!-- Rectangle / rounded box -->
<mxCell id="2" value="Label" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry" />
</mxCell>

<!-- Cylinder (database) -->
<mxCell id="3" value="DB" style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;" vertex="1" parent="1">
  <mxGeometry x="350" y="100" width="120" height="80" as="geometry" />
</mxCell>

<!-- Diamond (decision) -->
<mxCell id="4" value="Check?" style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
  <mxGeometry x="100" y="220" width="160" height="80" as="geometry" />
</mxCell>
```

### Containers and groups

For architecture diagrams with nested elements, use draw.io's parent-child containment — do **not** just place shapes on top of larger shapes.

| Type | Style | When to use |
|------|-------|-------------|
| **Group** (invisible) | `group;pointerEvents=0;` | No visual border needed, container has no connections |
| **Swimlane** (titled) | `swimlane;startSize=30;` | Container needs a visible title bar, or container itself has connections |
| **Custom container** | Add `container=1;pointerEvents=0;` to any shape | Any shape acting as a container without its own connections |

**Key rules:**
- Add `pointerEvents=0;` to container styles that should not capture connections between children
- Children set `parent="containerId"` and use coordinates **relative to the container**

```xml
<!-- Swimlane container -->
<mxCell id="svc1" value="User Service" style="swimlane;startSize=30;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="300" height="200" as="geometry"/>
</mxCell>
<!-- Child inside container — coordinates relative to parent -->
<mxCell id="api1" value="REST API" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="svc1">
  <mxGeometry x="20" y="40" width="120" height="60" as="geometry"/>
</mxCell>
<mxCell id="db1" value="Database" style="shape=cylinder3;whiteSpace=wrap;html=1;" vertex="1" parent="svc1">
  <mxGeometry x="160" y="40" width="120" height="60" as="geometry"/>
</mxCell>
```

### Connector (edge)

**CRITICAL:** Every edge `mxCell` must contain a `<mxGeometry relative="1" as="geometry" />` child element. Self-closing edge cells (`<mxCell ... edge="1" ... />`) are **invalid** and will not render. Always use the expanded form.

```xml
<!-- Directed arrow — always include rounded, orthogonalLoop, jettySize for clean routing -->
<mxCell id="10" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="2" target="3">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Arrow with label + explicit entry/exit points to control direction -->
<mxCell id="11" value="HTTP/REST" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" source="2" target="4">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Arrow with waypoints — use when edge must route around other shapes -->
<mxCell id="12" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="3" target="5">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="500" y="50" />
    </Array>
  </mxGeometry>
</mxCell>
```

**Edge style rules:**
- **Animated connectors:** add `flowAnimation=1;` to any edge style to show a moving dot animation along the arrow. Works in SVG export and draw.io desktop — ideal for data-flow and pipeline diagrams. Example: `style="edgeStyle=orthogonalEdgeStyle;flowAnimation=1;rounded=1;..."`
- **Always** include `rounded=1;orthogonalLoop=1;jettySize=auto` — these enable smart routing that avoids overlaps
- Pin `exitX/exitY/entryX/entryY` on every edge when a node has 2+ connections — distributes lines across the shape perimeter
- Add `<Array as="points">` waypoints when an edge must detour around an intermediate shape
- **Leave room for arrowheads:** the final straight segment between the last bend and the target shape must be ≥20px long. If too short, the arrowhead overlaps the bend and looks broken. Fix by increasing node spacing or adding explicit waypoints

### Distributing connections on a shape

When multiple edges connect to the same shape, assign different entry/exit points to prevent stacking:

| Position | exitX/entryX | exitY/entryY | Use when |
|----------|-------------|-------------|----------|
| Top center | 0.5 | 0 | connecting to node above |
| Top-left | 0.25 | 0 | 2nd connection from top |
| Top-right | 0.75 | 0 | 3rd connection from top |
| Right center | 1 | 0.5 | connecting to node on right |
| Bottom center | 0.5 | 1 | connecting to node below |
| Left center | 0 | 0.5 | connecting to node on left |

**Rule:** if a shape has N connections on one side, space them evenly (e.g., 3 connections on bottom → exitX = 0.25, 0.5, 0.75)

### Applying a preset

When Workflow Step 0.5 resolved a preset, the preset's palette / shape keywords / edge defaults / font fully replace the built-in tables below. Detailed application rules — color slot fallback ladder, decision/container shape mapping, shape keyword composition, edge dashedFor token matching, font append rules, sketch/strokeWidth extras, conflict resolution with Diagram Type Presets — see **`references/preset-management.md` §5 Applying a preset**.

### Color palette (fillColor / strokeColor)

*Used only when no preset is active (see "Applying a preset" above).*

| Color name | fillColor | strokeColor | Use for |
|-----------|-----------|-------------|---------|
| Blue | `#dae8fc` | `#6c8ebf` | services, clients |
| Green | `#d5e8d4` | `#82b366` | success, databases |
| Yellow | `#fff2cc` | `#d6b656` | queues, decisions |
| Orange | `#ffe6cc` | `#d79b00` | gateways, APIs |
| Red/Pink | `#f8cecc` | `#b85450` | errors, alerts |
| Grey | `#f5f5f5` | `#666666` | external/neutral |
| Purple | `#e1d5e7` | `#9673a6` | security, auth |

### Layout tips

**Spacing — scale with complexity:**

| Diagram complexity | Nodes | Horizontal gap | Vertical gap |
|-------------------|-------|----------------|--------------|
| Simple | ≤5 | 200px | 150px |
| Medium | 6–10 | 280px | 200px |
| Complex | >10 | 350px | 250px |

**Routing corridors:** between shape rows/columns, leave an extra ~80px empty corridor where edges can route without crossing shapes. Never place a shape in a gap that edges need to traverse.

**Grid alignment:** snap all `x`, `y`, `width`, `height` values to **multiples of 10** — this ensures shapes align cleanly on draw.io's default grid and makes manual editing easier.

**General rules:**
- Plan a grid before assigning x/y coordinates — sketch node positions on paper/mentally first
- Group related nodes in the same horizontal or vertical band
- Use `swimlane` cells for logical grouping with visible borders
- Place heavily-connected "hub" nodes centrally so edges radiate outward instead of crossing
- To force straight vertical connections, pin entry/exit points explicitly on edges:
  `exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0`
- Always center-align a child node under its parent (same center x) to avoid diagonal routing
- **Event bus pattern**: place Kafka/bus nodes in the **center of the service row**, not below — services on either side can reach it with short horizontal arrows (`exitX=1` left side, `exitX=0` right side), eliminating all line crossings
- Horizontal connections (`exitX=1` or `exitX=0`) never cross vertical nodes in the same row; use them for peer-to-peer and publish connections

**Avoiding edge-shape overlap:**
- Before finalizing coordinates, trace each edge path mentally — if it must cross an unrelated shape, either move the shape or add waypoints
- For tree/hierarchical layouts: assign nodes to layers (rows), connect only between adjacent layers to minimize crossings
- For star/hub layouts: place the hub center, satellites around it — edges stay short and radial
- When an edge must span multiple rows/columns, route it along the outer corridor, not through the middle of the diagram

## Export

### Commands

```bash
# macOS — Homebrew (draw.io in PATH)
draw.io -x -f png -s 2 -o diagram.png input.drawio

# macOS — full path (if not in PATH)
/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -o diagram.png input.drawio

# Windows
"C:\Program Files\draw.io\draw.io.exe" -x -f png -s 2 -o diagram.png input.drawio

# Linux (headless — requires xvfb-run)
xvfb-run -a draw.io -x -f png -s 2 -o diagram.png input.drawio

# SVG export
draw.io -x -f svg -o diagram.svg input.drawio

# PDF export
draw.io -x -f pdf -o diagram.pdf input.drawio

# Custom output directory (e.g. CI artifacts dir) — create if missing, then export there
mkdir -p ./artifacts && draw.io -x -f png -s 2 -o ./artifacts/diagram.png input.drawio
```

**Key flags:**
- `-x` — export mode (required)
- `-f` — format: `png`, `svg`, `pdf`, `jpg`
- `-s` — scale: `1`, `2`, `3` (2 recommended for PNG)
- `-o` — output file path; accepts any directory (e.g. `./artifacts/diagram.png`) — `mkdir -p` the target dir first. Use `.png` double extension when embedding.
- `-b` — border width around diagram (default: 0, recommend 10)
- `-t` — transparent background (PNG only)
- `--page-index 0` — export specific page (default: all)

### Browser fallback (no CLI needed)

When the draw.io desktop CLI is unavailable, generate a browser-editable URL by deflate-compressing and base64-encoding the XML:

```bash
# Encode .drawio XML into a diagrams.net URL
python3 -c "
import zlib, base64, urllib.parse, sys
xml = open(sys.argv[1]).read()
# Raw deflate (no zlib header) — diagrams.net uses mxGraph's raw inflate
c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
compressed = c.compress(xml.encode('utf-8')) + c.flush()
# Standard base64 (atob rejects url-safe -/_); strip any newlines
encoded = base64.b64encode(compressed).decode('utf-8').replace('\n', '')
print('https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&edit=_blank#R' + urllib.parse.quote(encoded, safe=''))
" input.drawio
```

This produces a client-side URL that opens the diagram in the browser for viewing and editing. No data is uploaded to any server — the entire diagram XML is encoded in the URL fragment (after `#`), which is never sent to the server. Useful when the user cannot install the desktop app.

### Fallback chain

When tools are unavailable, degrade gracefully:

| Scenario | Behavior |
|----------|----------|
| draw.io CLI missing, Python available | Use browser fallback (diagrams.net URL) |
| draw.io CLI missing, Python missing | Generate `.drawio` XML only; instruct user to open in draw.io desktop or diagrams.net manually |
| Vision unavailable for self-check | Skip self-check (step 5); proceed directly to showing user the exported PNG |
| Export fails (Chromium/display issues) | On Linux, retry with `xvfb-run -a`; if still failing, deliver `.drawio` XML and suggest manual export |

### Checking if draw.io is in PATH

```bash
# Try short command first
if which draw.io >/dev/null 2>&1; then
  DRAWIO="draw.io"
elif [ -f "/Applications/draw.io.app/Contents/MacOS/draw.io" ]; then
  DRAWIO="/Applications/draw.io.app/Contents/MacOS/draw.io"
else
  echo "draw.io not found — install from https://github.com/jgraph/drawio-desktop/releases"
fi
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `id="0"` and `id="1"` root cells | Always include both at the top of `<root>` |
| Shapes not connected | `source` and `target` on edge must match existing shape `id` values |
| Export command not found on macOS | Try full path `/Applications/draw.io.app/Contents/MacOS/draw.io` |
| Linux: blank/error output headlessly | Prefix command with `xvfb-run -a` |
| PDF export fails | Ensure Chromium is available (draw.io bundles it on desktop) |
| Background color wrong in CLI export | Known CLI bug; add `--transparent` flag or set background via style |
| Overlapping shapes | Scale spacing with complexity (200–350px); leave routing corridors |
| Edges crossing through shapes | Add waypoints, distribute entry/exit points, or increase spacing |
| Special characters in `value` | Use XML entities: `&amp;` `&lt;` `&gt;` `&quot;` |
| Iteration loop never ends | After 5 rounds, suggest user open .drawio in draw.io desktop for fine-tuning |
| Self-closing edge `mxCell` | Always use expanded form with `<mxGeometry>` child — self-closing edges won't render |
| `--` inside XML comments | Illegal per XML spec — use single hyphens or rephrase |
| Arrowhead overlaps bend | Final edge segment before target must be ≥20px — increase spacing or add waypoints |
| Literal `\n` in label text | Use `&#xa;` for line breaks in `value` attributes |

## Diagram Type Presets

When the user requests a **specific diagram type**, apply that type's structural shape/style/layout conventions. Detailed tables (shapes, edges, layout rules) for the 6 supported types live in **`references/diagram-type-presets.md`** — read it only when the request matches one of these:

| Type | Triggers |
|---|---|
| **ERD** | "ER diagram", "数据库表关系", "schema diagram", PK/FK 提及 |
| **UML Class** | "UML class", "类图", "继承/实现/composition" |
| **Sequence** | "sequence diagram", "时序图", "lifeline", "actor 交互" |
| **Architecture** | "架构图", "system architecture", 多 tier / 多 service / queue+db |
| **ML / DL** | "neural network", "model architecture", "Conv/RNN/Transformer/Attention" |
| **Flowchart** | "flowchart", "流程图", start/end + decision + process |

For generic diagrams that don't match any specific type, use the §"Color palette" + §"Shape types" tables above directly — no need to read the reference.
