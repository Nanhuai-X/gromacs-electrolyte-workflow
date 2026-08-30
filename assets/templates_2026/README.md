# CP2K 2026.2 template set

These files are version-bound input skeletons, not complete scientific jobs.
Render every `{{SLOT}}`, verify the exact CP2K 2026.2 manual, and run
`scripts/input_lint.py --version 2026.2` before an executable smoke test.

The electronic-property family records the nested 2026.2 DOS/CURVE/PDOS
layout. Do not copy it into a 2024.1 input. A template being present or
documented does not make a workflow supported: the exact executable, basis and
potential files, output artifacts, parser checks, and scientific gates still
have to pass.
