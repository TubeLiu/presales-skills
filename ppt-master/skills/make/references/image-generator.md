# AI Image Generator Reference — moved to ai-image plugin

From Milestone D of the presales-skills refactor, the AI image generation
tooling (formerly `scripts/image_gen.py` + `scripts/image_backends/`) has been
extracted into the independent **ai-image** plugin — a shared dependency for
solution-master / ppt-master / tender-workflow.

See (paths under ai-image plugin):
- `skills/gen/SKILL.md` — main skill with usage guidance + §路径自定位 bootstrap
- `skills/gen/prompts/ai_image_models.yaml` — unified 13-provider model registry
- `skills/gen/scripts/image_gen.py` — CLI entry (same interface as before)
- `skills/gen/scripts/image_backends/` — 13 backend modules

## Invocation from ppt-master

v1.0.0 已删 `image-gen` PATH bin（c983037，cross-agent 兼容）。两种入口：

**Claude Code 推荐**——Skill tool 直接触发，不需要解析路径：
```
Skill(skill="ai-image:gen")
```

**跨 agent fallback**（Cursor / Codex / OpenCode 等）——先按 ai-image SKILL.md §路径自定位 解析 `$AI_IMAGE_SKILL_DIR`，再调底层脚本：
```bash
python3 "$AI_IMAGE_SKILL_DIR/scripts/image_gen.py" "<prompt>" \
  --aspect_ratio 16:9 --image_size 1K -o <project_path>/images
```

## Configuration

All API keys unified at `~/.config/presales-skills/config.yaml`, managed by the ai-image plugin. Users say "configure ai-image" in Claude conversation; AI routes to the plugin's setup wizard. See ai-image plugin SKILL.md for full setup guide.
