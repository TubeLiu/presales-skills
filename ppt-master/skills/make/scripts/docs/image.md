# image_gen.py — moved to ai-image plugin

From Milestone D of the presales-skills refactor, `image_gen.py` and all 13
backend modules (`image_backends/`) have been extracted into the independent
**ai-image** plugin, a shared dependency for solution-master / ppt-master /
tender-workflow.

## New location

```
<marketplace>/ai-image/scripts/image_gen.py
<marketplace>/ai-image/scripts/image_backends/
```

## Invocation in plugin mode

ppt-master's SKILL.md invokes the ai-image plugin's underlying script directly (after resolving its SKILL_DIR):

```bash
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" ...
```

v1.0.0 dropped the `image-gen` bin entry for cross-agent compatibility (commit c983037).

Configuration is unified under `~/.config/presales-skills/config.yaml`. Manage via natural language (Claude routes to the ai-image plugin) or by calling `ai_image_config.py` directly:

| Natural language (say to Claude) | Underlying script |
|------|------|
| "configure ai-image" | `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup` |
| "list ai-image models" | `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models` |
| "set ai-image api_keys.\<provider\> to \<key\>" | `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.<provider> <key>` |
| "validate ai-image API key" | `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate` |

## Source-mode invocation

Developers running ppt-master directly from source (no plugin install):

```bash
python3 ../ai-image/scripts/image_gen.py "<prompt>" --list-backends
```

(Relative to ppt-master repo root, assuming the umbrella presales-skills
monorepo layout where ai-image is a sibling directory.)

## Supported backends

Run `python3 <path-to-image_gen.py> --list-backends` for the current list.

Tiered:
- **Core**: gemini, openai, qwen (= dashscope), volcengine (= ark), zhipu
- **Extended**: bfl, ideogram, stability
- **Experimental**: fal, minimax, openrouter, replicate, siliconflow

See `ai-image/README.md` (or run `ai_image_config.py models`) for details.
