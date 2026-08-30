---
name: cp2k-materials-workflow
description: Agent-neutral, version-aware CP2K workflows for periodic and molecular materials calculations. Use when an agent must audit a structure, select exact CP2K syntax for a declared version, build and lint an input, plan convergence, run locally or through a scheduler, parse results, validate properties, or preserve reproducible provenance for energy, geometry optimization, cell optimization, band structure, density of states, projected density of states, electron localization function, electron density, work function, adsorption energy, charge-density difference, population charges, periodic RESP, NEB, or AIMD.
---

# CP2K Materials Workflow

Use this skill as the control protocol for a scientific CP2K calculation. Use
Python for deterministic orchestration, validation, parsing, and provenance;
use CP2K for the electronic-structure calculation. Do not invent CP2K syntax
from memory when the exact manual can be consulted.

This package is agent-neutral. The source of truth is this Markdown file and
the files under `scripts/`, `references/`, and `assets/`; `agents/openai.yaml`
is optional interface metadata for hosts that support it. An agent that can
read Markdown and run Python can use the workflow without a vendor-specific
command, hook, model, or orchestration API.

## Non-negotiable rules

- Detect the exact CP2K executable and version before generating a formal input.
- Resolve the matching official manual branch and record its retrieval hash.
- Keep CP2K 2024.x and 2026.x templates, syntax, restart files, and evidence
  separate. Official syntax is not execution validation.
- Never guess total charge, multiplicity, spin, magnetic ordering, DFT+U,
  slab model, adsorption reference, defect state, or NEB endpoint mapping.
- Mark unresolved scientific choices `SCIENTIFIC_DECISION_REQUIRED`.
- Preserve raw structures, inputs, outputs, restarts, logs, commands, hashes,
  and environment metadata. File existence alone never means `PASS`.
- Do not modify a user structure in place. Every derived structure records its
  parent hash, transformation, tool, and version.
- Use a scheduler for long remote jobs. Never run formal DFT work on an HPC
  login node with direct `mpirun`.
- Keep credentials, private keys, tokens, and site-specific paths outside the
  repository and outside logs and reports.

## Conversation and decision sequence

Collect only what is missing:

1. `RUN_TARGET`: `LOCAL` or `REMOTE_SERVER`.
2. Structure path: CIF, XYZ/EXTXYZ, PDB, POSCAR, or CONTCAR.
3. Requested property or properties.
4. Paper, DOI, PDF, or supplementary information, if reproduction is wanted.

For `REMOTE_SERVER`, collect the hostname, SSH port, username, private-key
path, verified `known_hosts` path or fingerprint, remote work directory, and
site scheduler details. Never request private-key contents. Run a read-only
preflight before submission.

If a reference is supplied, extract observations, label them
`LITERATURE_OBSERVED`, show `COST_EFFECTIVE`, `BALANCED`, and `HIGH_PRECISION`
candidate plans, and wait for explicit user confirmation. Literature values
are evidence, not automatic defaults.

After deterministic audits, ask only unresolved physical-model questions:
charge, spin, magnetic ordering, DFT+U, functional/dispersion, convergence
targets, k-point policy, slab/vacuum model, adsorption reference, or endpoint
mapping. Do not ask the user to write CP2K syntax, copy coordinates, or parse
energies manually.

## Required execution stages

Run stages in this order and stop at the first failed gate:

1. **Route and audit the environment.** Run `task_router.py`,
   `environment_audit.py`, `scheduler_detect.py`, and
   `cp2k_version_detect.py`. For a remote target, run `remote_ssh.py` with
   strict host-key verification. Record executable, version, build/backend,
   CPU/GPU, MPI/OpenMP, memory, Python, and scheduler metadata.
2. **Resolve the manual.** Run `manual_resolver.py`; when network access is
   allowed, run `manual_cache.py`. Read the exact sections for the selected
   workflow and record `manual_manifest.yaml`. If the exact minor branch is
   unavailable, report `EXACT_MANUAL_AVAILABLE=FALSE` and limit the claim.
3. **Audit the structure.** Run `structure_audit.py`; also run
   `structure_audit_full.py` when its optional structure libraries are
   installed. Check cell, periodicity, formula, atom order, occupancy,
   disorder, duplicate/near-duplicate atoms, short contacts, symmetry, and
   coordinate consistency. Preserve the raw file hash.
4. **Create the calculation manifest.** Run `calculation_init.py` and record
   every scientific setting as `USER_SPECIFIED`, `LITERATURE`, or
   `SKILL_DEFAULT`. Run `literature_profile.py` and then
   `parameter_gate.py` only after explicit user confirmation.
5. **Select and render a versioned template.** Use
   `assets/template_registry.json`, the exact manual, and
   `render_versioned_template.py`. Use `input_builder.py` for conditional or
   repeated blocks. Never mix template families or reuse a restart across
   incompatible CP2K versions/builds without evidence.
6. **Pass the three input gates.** Run `input_lint.py` (or the compatibility
   entry point `validate_cp2k_input.py`), an optional compatible external
   validator, and a real executable smoke test. Unresolved slots, unknown
   sections, unverified basis/potential files, or version mismatches block
   submission.
7. **Plan property-specific convergence.** Run `convergence_manager.py` and
   define the axes and acceptance targets for the requested property. Energy
   convergence alone is insufficient for forces, stress, bands, DOS, charge,
   adsorption, or work function.
8. **Submit and monitor.** Use a local command only for `LOCAL` or an explicit
   smoke test; `run_cp2k.py` requires an explicit `--allow-run` flag. For remote work, render a scheduler script and use
   `scheduler_remote.py`; submission requires explicit approval. Retain stdout,
   stderr, job metadata, return state, and restart files.
9. **Validate artifacts.** Use `cp2k_output_parser.py`,
   `compute_adsorption_energy.py`, and `subtract_cube_density.py` as
   applicable. Validate units, finite values, grid dimensions, coordinate
   frames, k-point paths, energy references, and scientific gates before
   plotting or reporting a number.
10. **Archive and report.** Write raw data, derived data, figures, provenance,
    capability status, limitations, and exactly one verdict:
    `PASS`, `PASS WITH LIMITATIONS`, or `FAIL`.

## Version and capability policy

Use `assets/template_registry.json` first, then verify every keyword against
the exact manual:

- CP2K 2024.1 uses the legacy sibling DOS/PDOS layout.
- CP2K 2026.2 uses the version-specific nested DOS/CURVE/PDOS layout recorded
  in its template family.
- A 2024.1 restart is not automatically a 2026.2 restart, and the reverse is
  also false.
- A template or manual entry is not a successful workflow. A capability may
  be called `SUPPORTED` only after a matching executable, exact input, normal
  termination, expected artifact, parser checks, and property gates pass.
- The public package intentionally contains no machine-specific execution
  artifact, so its registry starts unvalidated. Upgrade status only in the
  user's calculation record after new evidence is archived.

Read [cp2k_2024.md](references/cp2k_2024.md) or
[cp2k_2026.md](references/cp2k_2026.md) before selecting property syntax.

## Scientific property gates

Use [properties.md](references/properties.md) for detailed gates. At minimum:

- `ENERGY`: normal termination, converged SCF, finite total energy.
- `GEO_OPT`: SCF convergence, geometry completion marker, force and
  displacement criteria, and expected final atom mapping.
- `CELL_OPT`: all geometry gates plus stress and cell/volume convergence.
- `BAND`: converged integration mesh and independently audited high-symmetry
  path with labels and transformation preserved.
- `DOS`/`PDOS`: suitable state count and k mesh, exact version syntax, finite
  rows, energy reference, spin channels, and artifact presence.
- `ELF`/density: validated cube origin, axes, dimensions, cell, atom block,
  and finite values.
- `ADSORPTION_ENERGY`: same theory for complex, host, and reference; declare
  relaxed versus fixed geometry and the sign convention.
- `CHARGE_DENSITY_DIFFERENCE`: identical cube grids and fragment coordinate
  frame before subtraction.
- `WORK_FUNCTION`: audited slab, vacuum plateau, dipole convention, and
  `Phi = V_vacuum - E_F` only after the potential convention is established.
- Population, periodic RESP, and REPEAT-like charges remain separate methods;
  never relabel a REPEAT-like result as exact REPEAT.

Set `SCIENTIFIC_DECISION_REQUIRED` for unresolved charge/spin, DFT+U,
disorder, slab, adsorption, periodic-charge, and NEB assumptions. Complete
all deterministic audits before asking the user.

## Remote execution and provenance

For remote execution require strict `known_hosts` verification and use the
site scheduler (`sbatch`, `qsub`, or `bsub`) for long jobs. `status` checks are
read-only; `submit` is an external mutation and needs a fresh explicit
approval. See [remote_execution.md](references/remote_execution.md).

Use the calculation layout below and hash all relevant files after they are
complete:

```text
calculation/
├── input_structure/  protocol/  convergence/
├── inputs/           jobs/      outputs/  restart/  logs/
├── cube/             bands/     dos/      figures/
├── reports/          provenance/
└── calculation.yaml
```

Record the structure lineage, exact executable/version, manual branch and
retrieval date, basis/potential sources and hashes, scientific settings,
command, scheduler job ID, host, CPU/GPU, MPI/OMP, raw output hash, restart
hash, postprocessing parameters, validation results, repairs, and limitations.
See [execution_provenance.md](references/execution_provenance.md).

## Bundled resources

- `assets/templates_2024/` and `assets/templates_2026/`: read-only,
  version-bound input skeletons.
- `assets/template_registry.json`: version/workflow map and evidence status.
- `assets/failure_regressions.json`: generic failure guards.
- `assets/*.example.*`: safe placeholders only; replace them after scientific
  decisions and site audit.
- `scripts/`: portable Python 3 orchestration, validation, parsing,
  postprocessing, SSH, scheduler, and provenance helpers.
- `references/`: detailed protocol notes loaded progressively.

Runtime manual caches, calculation outputs, local adapters, credentials, and
site configuration are deliberately outside the public package boundary.
