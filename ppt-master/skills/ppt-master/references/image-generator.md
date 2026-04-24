# AI Image Generator Reference — moved to ai-image plugin

From Milestone D of the presales-skills refactor, the AI image generation
tooling (formerly `scripts/image_gen.py` + `scripts/image_backends/`) has been
extracted into the independent **ai-image** plugin — a shared dependency for
solution-master / ppt-master / tender-workflow.

See:
- `ai-image/skills/ai-image/SKILL.md` — main skill with usage guidance
- `ai-image/prompts/ai_image_models.yaml` — unified 13-provider model registry
- `ai-image/scripts/image_gen.py` — CLI entry (same interface as before)
- `ai-image/scripts/image_backends/` — 13 backend modules

## Invocation from ppt-master (plugin mode)

```bash
image-gen "<prompt>" \
  --aspect_ratio 16:9 --image_size 1K -o <project_path>/images
```

## Configuration

All API keys now unified at `~/.config/presales-skills/config.yaml`, managed
via `/ai-image-config-*` slash commands. See ai-image plugin README for the
full setup guide.
