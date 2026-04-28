# drawio plugin — Draw.io Diagram Generation

[中文](./README.md) | **English**

Generate `.drawio` XML files via natural language, with optional PNG / SVG / PDF / JPG export (requires draw.io desktop CLI).

## Slash entry points

| Trigger | Form |
|---|---|
| Claude Code canonical | `/drawio:draw "GitOps blue-green architecture"` |
| Codex / Cursor / OpenCode short alias | `/draw "..."` |
| Natural language auto-trigger | "draw an architecture diagram: user → gateway → microservices" / "draw a flowchart of X" / "generate an ER diagram", etc. |

## 6 diagram presets

| Preset | Use case |
|---|---|
| **ERD** | Database entity-relationship (entities, attributes, foreign keys) |
| **UML class** | Class diagram (classes, interfaces, inheritance, composition) |
| **Sequence** | Sequence diagram (actor, lifeline, messages) |
| **Architecture** | System architecture (layer / tier / component grouping, layered style) |
| **ML / DL** | Neural network model (with tensor shape `(B, C, H, W)` annotations, suited for NeurIPS / ICML / ICLR paper style) |
| **Flowchart** | Flow chart (start / decision / process / end) |

Each preset comes with its own shape library, color palette, and layout conventions. Animated connectors (`flowAnimation=1`) support dataflow / pipeline visualization (visible in SVG and draw.io desktop).

## Style presets (v1.3+)

Reverse-engineer a visual style from `.drawio` files / screenshots, save as a named preset, then reuse:

```
> Learn the style of this .drawio file and save as 'corporate-blue'
> Draw a service mesh architecture in corporate-blue style
> List my available style presets
> Set corporate-blue as default
```

3 built-in presets: `default` / `corporate` / `handdrawn` (in `skills/draw/styles/built-in/`). User-defined presets live in `~/.drawio-skill/styles/` (persisted across vendor sync).

## Custom output dir (v1.4+)

```
> Export the diagram to ./artifacts/
> Output to docs/images/
```

The skill auto-`mkdir -p` the target directory before exporting. Suited for CI/CD artifact pipelines.

## Installing draw.io CLI

```bash
# macOS (Homebrew)
brew install --cask drawio

# Cross-platform (npm)
npm install -g @drawio/drawio-desktop-cli

# Linux (with xvfb headless support)
# see https://github.com/jgraph/drawio-desktop/releases
```

When the CLI is unavailable, the skill gracefully falls back to **browser fallback**: emits a diagrams.net URL (base64-encoded XML) the user can open in a browser to edit.

## Working with other plugins

- **drawio**: architecture / flowchart / sequence / ER diagrams (structured, geometric)
- **ai-image** `/ai-image:gen`: concept art / illustrations / screenshots / cover art (freeform, AI-generated)
- **solution-master** automatically picks the right one per section semantics (architecture → drawio, cover / concept art → ai-image)

## Limitations

- Exported PNG/SVG/PDF/JPG **does not embed XML metadata** — users must keep the source `.drawio` file for future editing (double-clicking the PNG does not open it directly in draw.io)
- Self-check (vision-based) requires a vision-enabled model (Claude Sonnet / Opus, etc.); gracefully skips when unavailable
- ML model diagrams use PyTorch-style tensor shape `(B, C, H, W)` conventions

## Third-party components

The SKILL.md / references / styles / assets in this plugin are vendored from [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) v1.4.0 (MIT License). See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for the full borrowed-files list, change notes, and the upstream LICENSE.
