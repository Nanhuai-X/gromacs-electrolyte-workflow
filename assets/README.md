# Bundled assets

This directory contains portable, reviewable resources for the CP2K workflow.

- `templates_2024/` and `templates_2026/` are version-bound CP2K input
  skeletons. They are not complete scientific jobs and must be checked against
  the exact manual and executable.
- `template_registry.json` maps workflow names to the matching template and
  records evidence status.
- `failure_regressions.json` contains generic failure guards.
- `*.example.*` files contain placeholders only. They are safe examples, not
  cluster configuration or universal numerical presets.
- `library/` contains small read-only helpers for template access and input
  validation.

The public package intentionally does not include downloaded manuals, runtime
outputs, credentials, or project-specific adapters. Put such material in a
separate local overlay and keep it outside this directory.
