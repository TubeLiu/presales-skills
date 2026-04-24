---
name: drawio
description: Always use when user asks to create, generate, draw, or design a diagram, flowchart, architecture diagram, ER diagram, sequence diagram, class diagram, network diagram, mockup, wireframe, or UI sketch, or mentions draw.io, drawio, drawoi, .drawio files, or diagram export to PNG/SVG/PDF.
---

# Draw.io Diagram Skill

Generate draw.io diagrams as native `.drawio` files. Optionally export to PNG, SVG, or PDF. Keep the source `.drawio` file for future editing.

## Environment check (warn-only, don't abort)

!`command -v drawio-cli >/dev/null 2>&1 || command -v draw.io >/dev/null 2>&1 || echo "WARN_NO_DRAWIO_CLI: can still generate .drawio XML source, but PNG/SVG/PDF export unavailable. Install: 'brew install --cask drawio' (macOS) or 'npm install -g @drawio/drawio-desktop-cli'"`

## How to create a diagram

1. **Generate draw.io XML** in mxGraphModel format for the requested diagram
2. **Write the XML** to a `.drawio` file in the current working directory using the Write tool
3. **If the user requested an export format** (png, svg, pdf), locate the draw.io CLI (see below) and export the diagram. **Always keep the source `.drawio` file** alongside the exported file (the source file is the only way to edit the diagram later). If the CLI is not found, tell the user they can install the draw.io desktop app to enable export, or open the `.drawio` file directly
4. **Open the result** — the exported file if exported, or the `.drawio` file otherwise. If the open command fails, print the file path so the user can open it manually

## Choosing the output format

Check the user's request for a format preference. Examples:

- `/drawio create a flowchart` → `flowchart.drawio`
- `/drawio png flowchart for login` → `login-flow.drawio.png`
- `/drawio svg: ER diagram` → `er-diagram.drawio.svg`
- `/drawio pdf architecture overview` → `architecture-overview.drawio.pdf`

If no format is mentioned, just write the `.drawio` file and open it in draw.io. The user can always ask to export later.

### Supported export formats

| Format | Notes |
|--------|-------|
| `png` | Viewable everywhere, compatible with DOCX embedding |
| `svg` | Scalable, web-friendly |
| `pdf` | Printable |
| `jpg` | Lossy compression |

> **WARNING:** Do NOT use the `-e` / `--embed-diagram` flag. It produces truncated PNG files (missing IEND chunk) that PIL/Pillow cannot read, causing python-docx embedding to fail. This is a known draw.io CLI bug. Always keep the source `.drawio` file for future editing instead of relying on embedded XML.

## draw.io CLI

The draw.io desktop app includes a command-line interface for exporting.

### Locating the CLI

**Always try PATH first** — it covers macOS/Linux installs done via a package manager, Windows installs that opted into PATH, and any user who set `drawio` up manually. Only fall back to platform-specific absolute paths if PATH lookup fails.

```bash
command -v drawio >/dev/null 2>&1 && echo "DRAWIO_CMD=drawio"
```

If that fails, detect the environment and pick the right fallback.

#### Environment detection

```bash
case "$(uname -s 2>/dev/null)" in
  Darwin*) ENV=macos ;;
  Linux*) grep -qi microsoft /proc/version 2>/dev/null && ENV=wsl2 || ENV=linux ;;
  MINGW*|MSYS*|CYGWIN*) ENV=win_bash ;;
esac
```

- `macos` → look under `/Applications/`
- `linux` → the `drawio` binary was meant to be on PATH; if it's not, ask the user to install the snap/apt/flatpak package
- `wsl2` → reach into the Windows host via `/mnt/c/...`
- `win_bash` → **this is what Claude Code on Windows uses**. Git Bash (not WSL) sees the Windows filesystem via forward-slash drive paths (`C:/...`)

Keep in mind: **Git Bash on Windows ≠ WSL2**. Git Bash cannot read `/mnt/c/...` paths; WSL2 cannot read `C:/...` paths. Use the exact forms below.

#### macOS fallback

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io
```

#### WSL2 fallback (Linux distro running inside Windows)

```bash
"/mnt/c/Program Files/draw.io/draw.io.exe"
# Per-user install (if the above does not exist):
"/mnt/c/Users/$USER/AppData/Local/Programs/draw.io/draw.io.exe"
```

Double-quote the path — the embedded space in `Program Files` breaks on unquoted forms.

#### Windows Git Bash fallback (Claude Code default on Windows)

Try each path in order until one exists:

```bash
"C:/Program Files/draw.io/draw.io.exe"
"C:/Program Files (x86)/draw.io/draw.io.exe"
"$LOCALAPPDATA/Programs/draw.io/draw.io.exe"
```

**Always use forward slashes in Windows paths** when calling from Git Bash — `"C:\Program Files\..."` with backslashes is interpreted as shell escapes and will fail. Forward-slash form is accepted by the Windows kernel and survives Git Bash as-is.

### Export command

```bash
"$DRAWIO_CMD" -x -f <format> -b 10 -o <output> <input.drawio>
```

Quote `$DRAWIO_CMD` so paths with spaces (`Program Files`) do not split into arguments.

**WSL2 example:**

```bash
"/mnt/c/Program Files/draw.io/draw.io.exe" -x -f png -b 10 -o diagram.drawio.png diagram.drawio
```

**Windows Git Bash example:**

```bash
"C:/Program Files/draw.io/draw.io.exe" -x -f png -b 10 -o diagram.drawio.png diagram.drawio
```

Key flags:
- `-x` / `--export`: export mode
- `-f` / `--format`: output format (png, svg, pdf, jpg)
- ~~`-e` / `--embed-diagram`~~: **DO NOT USE** — causes truncated PNG (missing IEND chunk), breaks PIL/python-docx
- `-o` / `--output`: output file path
- `-b` / `--border`: border width around diagram (default: 0)
- `-t` / `--transparent`: transparent background (PNG only)
- `-s` / `--scale`: scale the diagram size
- `--width` / `--height`: fit into specified dimensions (preserves aspect ratio)
- `-a` / `--all-pages`: export all pages (PDF only)
- `-p` / `--page-index`: select a specific page (1-based)

### Opening the result

| Environment | Command |
|-------------|---------|
| macOS | `open <file>` |
| Linux (native) | `xdg-open <file>` |
| WSL2 | `cmd.exe /c start "" "$(wslpath -w <file>)"` |
| Windows Git Bash | `explorer.exe <file>` |

**WSL2 notes:**
- `wslpath -w <file>` converts a WSL2 path (e.g. `/home/user/diagram.drawio`) to a Windows path (e.g. `C:\Users\...`). This is required because `cmd.exe` cannot resolve `/mnt/c/...` style paths.
- The empty string `""` after `start` is required to prevent `start` from interpreting the filename as a window title.

**Windows Git Bash notes:**
- Use `explorer.exe <file>` rather than `cmd.exe /c start` — Git Bash mangles the `/c` flag via its MSYS path conversion, and `explorer.exe` does not require that workaround.
- Relative paths work; `explorer.exe` resolves them against the current directory. If the open call fails silently (Windows has no standard non-zero exit on "no file association"), print the absolute path so the user can open it by hand.

## File naming

- Use a descriptive filename based on the diagram content (e.g., `login-flow`, `database-schema`)
- Use lowercase with hyphens for multi-word names
- For export, use double extensions: `name.drawio.png`, `name.drawio.svg`, `name.drawio.pdf` — this signals the file was generated by draw.io
- After a successful export, **keep the source `.drawio` file** alongside the exported file for future editing

## XML format

A `.drawio` file is native mxGraphModel XML. Always generate XML directly — Mermaid and CSV formats require server-side conversion and cannot be saved as native files.

### Basic structure

Every diagram must have this structure:

```xml
<mxGraphModel adaptiveColors="auto">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Diagram cells go here with parent="1" -->
  </root>
</mxGraphModel>
```

- Cell `id="0"` is the root layer
- Cell `id="1"` is the default parent layer
- All diagram elements use `parent="1"` unless using multiple layers

## XML reference

For the complete draw.io XML reference including common styles, edge routing, containers, layers, tags, metadata, dark mode colors, and XML well-formedness rules, fetch and follow the instructions at:
https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-reference.md

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| draw.io CLI not found | Desktop app not installed or not on PATH | Keep the `.drawio` file and tell the user to install the draw.io desktop app, or open the file manually |
| Export produces empty/corrupt file | Invalid XML (e.g. double hyphens in comments, unescaped special characters) | Validate XML well-formedness before writing; see the XML well-formedness section below |
| Diagram opens but looks blank | Missing root cells `id="0"` and `id="1"` | Ensure the basic mxGraphModel structure is complete |
| Edges not rendering | Edge mxCell is self-closing (no child mxGeometry element) | Every edge must have `<mxGeometry relative="1" as="geometry" />` as a child element |
| File won't open after export | Incorrect file path or missing file association | Print the absolute file path so the user can open it manually |
| PNG cannot be embedded in DOCX / PIL UnidentifiedImageError | Used `-e` / `--embed-diagram` flag during export | Re-export without `-e` flag; the flag produces truncated PNG files missing the IEND chunk |

## CRITICAL: XML well-formedness

- **NEVER include ANY XML comments (`<!-- -->`) in the output.** XML comments are strictly forbidden — they waste tokens, can cause parse errors, and serve no purpose in diagram XML.
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Always use unique `id` values for each `mxCell`
