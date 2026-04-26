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

ppt-master's SKILL.md now calls:

```bash
image-gen "<prompt>" ...
```

Configuration is unified under `~/.config/presales-skills/config.yaml`.
Manage via `/ai-image:*` slash commands:

- `/ai-image:setup` — first-time setup wizard
- `/ai-image:models` — show model registry (13 providers)
- `/ai-image:set api_keys.<provider> <key>` — set API key
- `/ai-image:validate` — health check

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

See `ai-image/README.md` and `/ai-image:models` for details.
