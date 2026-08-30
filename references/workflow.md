# Workflow contract

## Inputs

Accept a structure path, natural-language property request, optional paper or
local PDF, and an explicit run target. Resolve the request into finite workflow
names before rendering an input. Keep the raw structure immutable.

## Stages

1. Audit environment and route the task.
2. Resolve the exact manual and template family.
3. Audit structure and create derived-structure lineage when needed.
4. Resolve scientific choices and confirm numerical parameters.
5. Render, lint, and smoke-test the input.
6. Plan convergence, execute through the correct target, and monitor.
7. Validate raw and derived artifacts.
8. Hash files and write a report with limitations and a verdict.

## Configuration illustration

```yaml
system:
  structure: input_structure/source.cif
  periodicity: periodic_xyz
  charge: null
  spin: SCIENTIFIC_DECISION_REQUIRED
theory:
  method: DFT
  functional: null
  dispersion: null
  basis_set: null
  pseudopotential: null
grid:
  cutoff_ry: null
  rel_cutoff_ry: null
scf:
  eps_scf: null
  max_scf: null
  solver: null
kpoints:
  mode: SCIENTIFIC_DECISION_REQUIRED
task:
  workflow: single_point
sources:
  charge: USER_SPECIFIED_OR_LITERATURE_OR_DECISION_REQUIRED
```

This is a schema illustration, not a universal scientific preset.

## Gates

Use the narrowest gate for the task. Geometry requires force and displacement
criteria. Adsorption requires three consistent energies. Cube subtraction
requires identical grid metadata. Band structure requires a path audit. Work
function requires a slab and vacuum plateau.

## Reports

Every report states environment, structure, theory, numerical settings,
convergence evidence, outputs, limitations, and one of `PASS`,
`PASS WITH LIMITATIONS`, or `FAIL`.
