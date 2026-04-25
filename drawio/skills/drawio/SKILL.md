---
name: draw-diagram
description: >
  当用户要求"画图 / 画一张图 / 生成流程图 / 架构图 / 拓扑图 / 时序图 / ER 图 / 类图 /
  网络图 / 线框图 / 原型图"或英文 "create / generate / draw / design diagram /
  flowchart / architecture / sequence / class / network / mockup / wireframe /
  UI sketch" 时触发，也包括用户提到 draw.io / drawio / drawoi / .drawio 文件、
  或要求把图导出 PNG / SVG / PDF / JPG 时。
  生成原生 .drawio 文件（mxGraphModel XML），可选导出为 PNG / SVG / PDF / JPG。
  始终保留源 .drawio 文件以便后续编辑。
allowed-tools: Read, Write, Bash, Glob
---

# Draw.io Diagram Skill

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 原生若不可识别（python.org installer 未勾"Add to PATH"、Conda / WinPython 等），改用 `python` 或 `py -3`。
> 2. **路径自定位**：本文档脚本路径用 Python `Path(__file__).resolve().parent` 自定位，不依赖 Bash `realpath`（macOS 默认无、Windows cmd 无）。
> 3. **可执行检测**：检测 draw.io CLI 时优先 `which drawio` / `where drawio`（PowerShell 用 `Get-Command`），不要用 `command -v`（Windows cmd 无）。
> 4. **Bash heredoc / 单行多命令**：`<<'EOF'` heredoc 和 `&&` / `||` 短路在 Windows cmd 不支持；Windows 用户优先在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：写路径用正斜杠 `/`（多数 Windows API 接受），避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

Generate draw.io diagrams as native `.drawio` files. Optionally export to PNG, SVG, or PDF. Keep the source `.drawio` file alongside the exported file — it is the only way to edit the diagram later.

## How to create a diagram

1. **Generate draw.io XML** in mxGraphModel format for the requested diagram
2. **Write the XML** to a `.drawio` file in the current working directory using the Write tool
3. **Post-process edge routing** (optional): If `npx @drawio/postprocess` is available, run it on the `.drawio` file to optimize edge routing (simplify waypoints, fix edge-vertex collisions, straighten approach angles). Skip silently if not available — do not install it or ask the user about it
4. **If the user requested an export format** (png, svg, pdf), locate the draw.io CLI (see below) and export the diagram. **Always keep the source `.drawio` file** — do NOT delete it. Do NOT pass `-e` / `--embed-diagram` to the CLI (see warning below). If the CLI is not found, keep the `.drawio` file and tell the user they can install the draw.io desktop app to enable export, or open the `.drawio` file directly
5. **Open the result** — the exported file if exported, or the `.drawio` file otherwise. If the open command fails, print the file path so the user can open it manually

## Choosing the output format

Check the user's request for a format preference. Examples:

- "create a flowchart" → `flowchart.drawio`
- "png flowchart for login" → `login-flow.drawio.png`
- "svg ER diagram" → `er-diagram.drawio.svg`
- "pdf architecture overview" → `architecture-overview.drawio.pdf`

If no format is mentioned, just write the `.drawio` file and open it in draw.io. The user can always ask to export later.

### Supported export formats

| Format | Notes |
|--------|-------|
| `png` | Viewable everywhere, compatible with DOCX embedding via python-docx / PIL |
| `svg` | Scalable, web-friendly |
| `pdf` | Printable |
| `jpg` | Lossy compression |

> **WARNING — do NOT use the `-e` / `--embed-diagram` flag.** It produces truncated PNG files (missing IEND chunk) that PIL/Pillow cannot read, causing python-docx embedding to fail. This is a known draw.io CLI bug. Keep the source `.drawio` file for future editing instead of relying on embedded XML.

## draw.io CLI

The draw.io desktop app includes a command-line interface for exporting.

### Locating the CLI

First, detect the environment, then locate the CLI accordingly:

#### WSL2 (Windows Subsystem for Linux)

WSL2 is detected when `/proc/version` contains `microsoft` or `WSL`:

```bash
grep -qi microsoft /proc/version 2>/dev/null && echo "WSL2"
```

On WSL2, use the Windows draw.io Desktop executable via `/mnt/c/...`:

```bash
DRAWIO_CMD=`/mnt/c/Program Files/draw.io/draw.io.exe`
```

The backtick quoting is required to handle the space in `Program Files` in bash.

If draw.io is installed in a non-default location, check common alternatives:

```bash
# Default install path
`/mnt/c/Program Files/draw.io/draw.io.exe`

# Per-user install (if the above does not exist)
`/mnt/c/Users/$WIN_USER/AppData/Local/Programs/draw.io/draw.io.exe`
```

#### macOS

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io
```

#### Linux (native)

```bash
drawio   # typically on PATH via snap/apt/flatpak
```

#### Windows (native, non-WSL2)

```
"C:\Program Files\draw.io\draw.io.exe"
```

Use `which drawio` (or `where drawio` on Windows) to check if it's on PATH before falling back to the platform-specific path.

### Export command

```bash
drawio -x -f <format> -b 10 -o <output> <input.drawio>
```

**WSL2 example:**

```bash
`/mnt/c/Program Files/draw.io/draw.io.exe` -x -f png -b 10 -o diagram.drawio.png diagram.drawio
```

Key flags:
- `-x` / `--export`: export mode
- `-f` / `--format`: output format (png, svg, pdf, jpg)
- ~~`-e` / `--embed-diagram`~~: **DO NOT USE** — produces truncated PNG (missing IEND chunk), breaks PIL/python-docx. See "Supported export formats" warning.
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
| Windows | `start <file>` |

**WSL2 notes:**
- `wslpath -w <file>` converts a WSL2 path (e.g. `/home/user/diagram.drawio`) to a Windows path (e.g. `C:\Users\...`). This is required because `cmd.exe` cannot resolve `/mnt/c/...` style paths.
- The empty string `""` after `start` is required to prevent `start` from interpreting the filename as a window title.

**WSL2 example:**

```bash
cmd.exe /c start "" "$(wslpath -w diagram.drawio)"
```

## File naming

- Use a descriptive filename based on the diagram content (e.g., `login-flow`, `database-schema`)
- Use lowercase with hyphens for multi-word names
- For export, use double extensions: `name.drawio.png`, `name.drawio.svg`, `name.drawio.pdf` — this signals the file was generated by draw.io
- After a successful export, **keep** the source `.drawio` file alongside the exported file — it is the only way to re-edit the diagram (we do NOT use `--embed-diagram` due to the PIL/python-docx bug)

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

For the complete draw.io XML reference — common styles, edge routing, containers, layers, tags, metadata, dark mode colors, and XML well-formedness rules — use your Read tool to open `xml-reference.md` in this skill's directory (sibling to this `SKILL.md`). Consult it before generating non-trivial diagrams.

The file is bundled with the plugin, so no network fetch is required — this keeps the skill usable in enterprise environments that block `raw.githubusercontent.com`.

## Optional: Python helper script

This plugin ships an optional Python helper at `scripts/drawio_generator.py` (sibling to this SKILL.md, in the plugin's `scripts/` directory). It wraps common patterns. Most callers can generate XML directly via the Write tool and skip the helper. If you want to invoke it, use the standard installed_plugins.json fallback to find the plugin path:

```bash
DRAWIO_PATH=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/drawio/' in e.get('installPath', ''):
                print(e['installPath']); sys.exit(0)
" 2>/dev/null)
[ -n "$DRAWIO_PATH" ] && python3 "$DRAWIO_PATH/scripts/drawio_generator.py" --help
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| draw.io CLI not found | Desktop app not installed or not on PATH | Keep the `.drawio` file and tell the user to install the draw.io desktop app, or open the file manually |
| Export produces empty/corrupt file | Invalid XML (e.g. double hyphens in comments, unescaped special characters) | Validate XML well-formedness before writing; see the XML well-formedness section below |
| Diagram opens but looks blank | Missing root cells `id="0"` and `id="1"` | Ensure the basic mxGraphModel structure is complete |
| Edges not rendering | Edge mxCell is self-closing (no child mxGeometry element) | Every edge must have `<mxGeometry relative="1" as="geometry" />` as a child element |
| File won't open after export | Incorrect file path or missing file association | Print the absolute file path so the user can open it manually |
| PNG cannot be embedded in DOCX / PIL UnidentifiedImageError | Used `-e` / `--embed-diagram` during export | Re-export without `-e`; the flag produces truncated PNG missing the IEND chunk |

## CRITICAL: XML well-formedness

- **NEVER include ANY XML comments (`<!-- -->`) in the output.** XML comments are strictly forbidden — they waste tokens, can cause parse errors, and serve no purpose in diagram XML.
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Always use unique `id` values for each `mxCell`
