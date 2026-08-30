# CP2K 2024.1 template set

These files are version-bound input skeletons, not complete scientific jobs.
Render every `{{SLOT}}`, verify the exact CP2K 2024.1 manual, and run
`scripts/input_lint.py --version 2024.1` before an executable smoke test.

The family preserves the 2024.1 distinctions recorded in the registry:

- DOS and PDOS are sibling print sections; do not copy the 2026 nested
  `DOS/CURVE/PDOS` layout into a 2024.1 input.
- The location and meaning of virtual-state controls must be checked against
  the exact manual. A static lint pass is not a syntax or capability proof.
- The GEO_OPT skeleton avoids an unnecessary explicit Gamma KPOINTS block when
  the selected OT recipe does not require one.
- ELF, electron-density, and Hartree cube requests require grid and finite-value
  validation after execution.
- Work function is a slab/vacuum postprocessing workflow, not a bulk property.
