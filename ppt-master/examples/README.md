# PPT Master Example Projects

This directory contains a minimal demo project that serves as the regression
fixture for `ppt-master/skills/make/scripts/` post-processing pipelines.

## Available

- `demo_project_intro_ppt169_20251211/` — the canonical "this is what a
  finalized project looks like" sample. Contains `svg_output/`,
  `svg_final/`, `images/`, `design_spec.md`, etc.

## Browsing more demos

The full upstream catalog (22 projects, 309 SVG pages, including consulting
style, magazine editorial, creative cultural narrative) is at:

- Online preview: https://hugohe3.github.io/ppt-master/
- Source repo: https://github.com/hugohe3/ppt-master/tree/main/examples

To pull in additional demo projects on demand:

```bash
# Clone upstream temporarily
git clone --depth 1 https://github.com/hugohe3/ppt-master.git /tmp/ppt-master-demos

# Copy the project you want
cp -r /tmp/ppt-master-demos/examples/<project_name> ./examples/
```

The upstream `examples.json` index in this directory lists all 22 projects
with metadata (page count, paradigm, density) so you can pick which to bring
in.

## Why we keep just one demo locally

Each upstream demo carries 5–15 MB of `svg_output/` + `svg_final/` + rendered
PPTX exports. Bundling all 22 (~219 MB) would inflate the monorepo. The
`demo_project_intro_ppt169_20251211` fixture is enough to verify the
post-processing pipeline end-to-end; richer demos can be cherry-picked when
needed.
