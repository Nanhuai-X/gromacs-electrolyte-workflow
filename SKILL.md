---
name: gromacs-electrolyte-workflow
description: Build, audit, reproduce, and analyze bulk liquid electrolyte GROMACS workflows with environment and backend gates, molecule/ratio intake, literature-or-default protocol resolution, force-field and RESP/RESP2 provenance, static topology validation, Packmol, checkpoint-safe equilibration, NVT production, RDF/CN, solvation, aggregation, MSD, diffusion diagnostics, and stage reports. Use when an agent needs to work with Li or Na salt electrolytes, HCE or LHCE, solvent or diluent mixtures, or related bulk electrolyte MD.
---

# GROMACS Electrolyte Workflow

## Purpose and trigger

Use this skill for a bulk liquid electrolyte workflow from molecular identity and literature protocol extraction through static topology validation, packing, staged equilibration, production, and analysis. It is a gated workflow: an unresolved scientific input is a stop condition, not a guess.

This package follows the Agent Skills layout. The invoking agent may be Codex, Claude Code, or another compatible agent; do not assume vendor-specific invocation syntax, tools, approval prompts, or shell behavior. Use the bundled relative paths and Python entry points, and follow the caller's permission model for side effects.

Set the formal control and provenance root in `assets/electrolyte.yaml` (`system.execution_root`), with `--project-root` or `GROMACS_PROJECT_ROOT` as equivalent runtime inputs. WSL/Linux is the default formal GROMACS backend, but the user may select an SSH remote Linux GROMACS target or a hybrid local-quantum-chemistry/remote-GROMACS route. Do not use a machine-specific path as an implicit fallback.

## Non-negotiable safeguards

- Never invent force-field, charge, Lennard-Jones, bonded, cross, 1-4, concentration, or composition parameters.
- Never silently mix force fields or charge models. Record the mixture and the compatibility rationale.
- Never use `grompp -maxwarn`. A warning requiring maxwarn is a failed gate.
- Never silently edit charges, topology, molecule counts, box size, timestep, thermostat, barostat, or cutoffs.
- Preserve raw source files. Derived files go in a separate directory and carry input hashes.
- Every scientific parameter has a source, status, and provenance record.
- Every stage emits a report with PASS, PASS WITH LIMITATIONS, or FAIL.
- Scientific choices and any deviation from a locked protocol require explicit user confirmation.
- Creating or testing this skill must not start a new formal long MD calculation.

## Execution backend and secret boundary

Choose one backend before any formal calculation and record it in assets/electrolyte.yaml:

- wsl_local: local WSL GROMACS, with optional local Windows Gaussian/RESP.
- ssh_remote: an approved remote Linux host for GROMACS.
- hybrid_gaussian_local_gromacs_remote: local Gaussian/RESP plus remote GROMACS.

Run scripts/backend_preflight.py for remote or hybrid mode. It is plan-only unless a user-created confirmation file is supplied. The Skill never downloads, copies, prints, hashes, or stores private-key contents. The user manually downloads the key, places it under the local OpenSSH directory, verifies permissions and host keys, and provides only the path, username, host, remote root, and loader path. See references/remote_execution.md.

The local WSL directory remains the control root in every mode. Only approved derived inputs and SHA256 manifests may be synchronized to a remote host. Remote GROMACS success does not prove force-field or physical validity.

## Protocol modes and precedence

The invocation accepts `reproduction`, `reference_guided`, `default`, or `hybrid`. The legacy `literature` alias maps to `reproduction`.

Precedence is:

1. an explicitly supplied and hashed literature/SI protocol, when the user approves using it;
2. the installed GROMACS help and official documentation for command semantics;
3. this project's electrolyte-specific defaults;
4. generic external Skill advice.

Literature values override defaults only for fields actually reported with units and context. A source conflict, ambiguous value, or missing required field is recorded and stops literal reproduction. `reference_guided` and `hybrid` may fill missing fields from the default, but every filled field is listed in `DEFAULT_FILLED`. No paper value is silently converted into a force-field or charge parameter.

Use `references/literature_protocol.md` and `scripts/literature_protocol_parser.py` to extract publication, DOI, ensemble, temperature, pressure, timestep, constraints, thermostat, barostat, electrostatics, cutoffs, dispersion, composition, stage lengths, output intervals, QM method/basis/functional/dispersion/solvent model, charge method, and analysis definitions.

## Gate state machine

The only gate states are PASS, PASS WITH LIMITATIONS, and FAIL. The recommended ordered gates are:

`ENVIRONMENT_VALIDATED -> BACKEND_VALIDATED -> INTAKE_VALIDATED -> STRUCTURE_VALIDATED -> COMPOSITION_RESOLVED -> PROTOCOL_RESOLVED -> CHARGE_METHOD_SELECTED -> CHARGE_VALIDATED -> FORCEFIELD_VALIDATED -> TOPOLOGY_VALIDATED -> STATIC_GROMPP_VALIDATED -> PACKMOL_VALIDATED -> EM_VALIDATED -> NVT_ANNEAL_VALIDATED -> NPT_CONVERGED -> NVT_TRANSITION_VALIDATED -> PRODUCTION_COMPLETED -> STRUCTURAL_CONVERGENCE -> MSD_VALIDATED -> DIFFUSION_VALIDATED`

Do not start a downstream stage when its predecessor is FAIL. A static grompp PASS proves only syntax and topology integration; it does not prove physical force-field validity.

## Default bulk protocol

The default is defined in `references/default_protocol.md` and `assets/simulation_protocol.yaml`. The authoritative generated values come from `scripts/mdp_builder.py`, not from memory.

- timestep: 0.002 ps only when the topology has validated hydrogen constraints; otherwise stop and require a slower validated choice.
- constraints: h-bonds; LINCS order 4 and iter 1.
- PME (particle-mesh Ewald), Verlet, periodic xyz. Literal Ewald is used only when a sourced literature protocol explicitly requests `coulombtype=Ewald`.
- Default NVT thermostat: Nose-Hoover, `tau-t=1 ps`, `ref-t=298.15 K`.
- Default NPT barostat: C-rescale isotropic, `tau-p=5 ps`, `ref-p=1 bar`, compressibility `4.5e-5 bar^-1`.
- EM: steepest descent with an explicit convergence gate; the 50000-step value is a ceiling, not a guarantee.
- NVT mild anneal: 600 ps with the declared 298.15 -> 350 -> 298.15 K schedule.
- NPT: at least 5 ns at 298.15 K and 1 bar; extend by 2 ns per convergence decision up to 10 ns total.
- NVT transition: 1 ns from a documented representative final NPT checkpoint/box.
- production: 20 ns NVT. Do not use NPT production for diffusion unless the user explicitly approves a different scientific protocol.
- balanced output: 2 ps per frame (`nstxout-compressed=1000` at 2 fs), energy every 2 ps, log every 10 ps, checkpoint every 15 minutes.
- A representative final NPT box must be selected by the convergence gate before the NVT transition.

The annealing schedule is a mild thermal history, not a substitute for EM or NPT equilibration. It may not be shortened by an automatic convenience rule.

## Workflow

1. **Backend and environment preflight.** Ask the user to choose `wsl_local`, `ssh_remote`, or `hybrid_gaussian_local_gromacs_remote` and record only non-secret connection metadata. Configure the control root through `assets/electrolyte.yaml`, `--project-root`, or `GROMACS_PROJECT_ROOT`; then run `scripts/environment_preflight.py` and read `references/wsl_environment.md`. Confirm the selected Linux/WSL environment, filesystem, GROMACS, Packmol, Python, GCC, CMake, Make, and optional Gaussian/formchk/Multiwfn. For remote/hybrid mode, run `scripts/backend_preflight.py` in plan-only mode. If a core tool or backend field is missing, run `scripts/environment_setup.py` or the backend plan and stop; do not silently install with sudo/apt/pip, connect to an unknown host, or use a Windows `gmx` as a substitute.
2. **User intake.** Collect molecule names/identities, structure files and hashes, formal charge/multiplicity, molar ratios, a base component count or an explicit number-density/box design, charge/force-field source status, and whether a literature protocol is supplied. The template is `assets/electrolyte.yaml`. If molecules, ratio, or count are missing, stop and ask; a ratio alone is not a molecule count.
3. **Structure and identity.** Accept XYZ, MOL V2000, SDF V2000, PDB, or an explicitly identified PubChem structure. Run `scripts/structure_adapter.py` and `scripts/structure_validate.py` to record format, atom count, coordinates, atom order, connectivity status, and source hash. If a compatible finite-molecule/Gaussian workflow skill is available, use it for prepare/confirm/run/formchk; otherwise use the bundled references and snapshot and stop when a required external step is unavailable. PubChem is optional; every structure still needs explicit identity, charge, multiplicity, and user confirmation before Gaussian.
4. **Composition.** Resolve integer molecule counts with `scripts/composition_builder.py`. If `system.base_component_count` is absent, return `COUNT_REQUIRED` and do not build a formal box. For literature reproduction, use reported counts/concentration only when units and conversion are auditable.
5. **Protocol resolution.** Run `scripts/protocol_resolver.py`. Literature temperature, pressure, timestep, thermostat, barostat, electrostatics, annealing, QM method, basis, functional, dispersion, solvent model, RESP settings, and stage lengths override defaults only when explicitly sourced and approved. Generate `resolved_protocol.json` and inspect `field_sources`, `DEFAULT_FILLED`, and `unresolved_required`.
6. **Charge-method decision.** Run `scripts/charge_method_selector.py` and ask the user to choose RESP1 or RESP2 before new Gaussian work. RESP1 is the recommended lower-cost default for a production baseline. RESP2 costs more because it requires a matched gas/implicit-solvent workflow and is more environment-aware, but it is not universally more accurate; the selected literature protocol takes precedence after audit. A no-choice result is `USER_DECISION_REQUIRED`.
7. **Charge/quantum route.** Run `scripts/gaussian_resp_router.py` and read `references/gaussian_resp_integration.md` plus `references/gaussian_molecule_workflow_integration.md`. RESP1 uses its formal validated route; RESP2 uses same-geometry gas plus CPCM/solvent branches and the declared interpolation. `scripts/gaussian_builder.py` accepts `--resolved-protocol` and XYZ/MOL/SDF/PDB input, but refuses to guess a method, basis, route option, dispersion, solvent model, geometry, connectivity, charge, or multiplicity. Keep Gaussian, formchk, Multiwfn, RESP, and RESP2 artifacts separate from GROMACS artifacts.
8. **Force-field audit.** Choose and audit force fields with `scripts/forcefield_selector.py` and `scripts/forcefield_audit.py`. Candidate records must include complete source locations, hashes, functional forms, combination rules, charges, and 1-4 behavior. A static compatibility result is not a physical validation.
9. **Topology.** Build component-prefixed derived topology with `scripts/topology_builder.py` and `scripts/atom_mapping.py`. Raw and normalized baselines remain untouched. Validate bonded terms, nonbonded terms, charge closure, exclusions, pairs, nrexcl, and defaults.
10. **Static grompp.** Before any formal box, run a minimal non-scientific fixture through `gmx grompp -pp` with no `-maxwarn`; audit the processed topology and save stdout, stderr, mdout.mdp, return code, and hashes. After Packmol, run a second actual-box grompp gate.
11. **Packmol and box.** Build and validate Packmol input with `scripts/packmol_builder.py` and `scripts/box_validate.py`. Require an explicit fixed seed, exact molecule/atom counts, non-overlap checks, and a documented box design. Do not infer a box size from an unreferenced density.
12. **MDP and staged execution.** Generate MDP files with `scripts/mdp_builder.py` and store `field_sources`. Run only after user confirmation using `scripts/gromacs_runner.py`. The runner is dry-run by default, requires a confirmation file for production, requires a checkpoint for continuation, and rejects maxwarn. Enforce EM -> 600 ps NVT anneal -> at least 5 ns NPT (extend only by the convergence gate) -> 1 ns NVT transition -> 20 ns NVT production. Preserve `continuation=yes`, `gen_vel=no`, and checkpoint lineage after the first stage.
13. **Analysis and reporting.** Analyze density, temperature, pressure, volume, potential/total energy, block convergence, RDF, first peak, first minimum, CN, solvation shells, SSIP/CIP/AGG proxies, cluster distributions, and PBC/COM-corrected MSD/diffusion diagnostics. Report insufficient data instead of selecting a flattering window. Generate methods and reports only from resolved files with `scripts/methods_generator.py`, `scripts/report_generator.py`, and `scripts/provenance.py`.

## Force-field and charge policy

The skill supports OPLS-like, CL&P, Madrid, RESP, RESP2, scaled-charge, and other models only when the source package explicitly defines all required terms. It does not decide scientific applicability by itself.

A RESP2 charge is not a RESP1 charge with a renamed label. DME or TTE solvent charges cannot be substituted for Li, FSI, TFSI, or an additive. A neutral molecule with printed rounding residue is not fixed by adding counterions. Charge closure is a sourced, auditable transformation and is never silently applied by this skill.

## Analysis policy

RDF and coordination number are reported together with peak and first-minimum diagnostics. If no physically meaningful first minimum exists, the result is `NO_PHYSICAL_FIRST_SHELL`; a fixed-cutoff diagnostic may still be reported separately. Solvation and SSIP/CIP/AGG outputs are structural proxies, not direct experimental species fractions. MSD fits must pass PBC and COM checks and identify a data-supported diffusive window; a line that merely looks straight is insufficient for a production diffusion claim.

## Agent portability and reports

The agent interface is Markdown plus relative file references and Python CLI scripts. `agents/openai.yaml` is optional host-specific UI metadata; other agents may ignore it. Do not require a particular agent name, tool name, approval API, or invocation prefix in order to follow this Skill. Environment-specific roots, binaries, and external workflow sources must be supplied through configuration, command-line arguments, or environment variables.

Each run directory contains resolved_config, stage reports, command log, hashes, and a final verdict. The Skill is portable because references and templates are self-contained and scripts use standard Python where possible. When operating alongside a separate validated GROMACS project, pass its configured root and reuse its validated scripts only when the user explicitly approves that source; keep this Skill's input and output manifests separate.

The bundled Gaussian workflow snapshot and integration reference govern finite-molecule input confirmation and Gaussian preflight when no compatible external skill is available. This Skill governs electrolyte-specific charge/force-field/topology/MD gates. Any external GROMACS or quantum-chemistry skill is advisory and must be explicitly located and audited. Project-specific electrolyte rules and reports take priority, followed by installed GROMACS help and official documentation, then generic references.

## Explicit stop conditions

Stop and request user review when any source is missing, a parameter is unresolved, atom mapping is ambiguous, topology needs maxwarn, a gate fails, a production choice would change the locked protocol, a result would be interpreted beyond its validation, or a run would be a new long MD merely to complete the Skill installation.
