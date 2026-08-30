# Portable automation tool contracts

| Tool | Contract |
|---|---|
| `task_router.py` | Map natural language to finite workflows and scientific gates; never choose numerical values. |
| `calculation_init.py` | Write a hash-linked calculation manifest without changing the source structure. |
| `manual_cache.py` | Fetch and hash only an allowlisted exact official CP2K manual page. |
| `manual_resolver.py` | Resolve a declared version and report whether its local manual cache exists. |
| `remote_ssh.py` | Build strict known-hosts SSH commands and perform read-only preflight. |
| `scheduler_remote.py` | Build bounded Slurm/PBS/LSF status or submit commands; submit requires approval. |
| `literature_profile.py` | Extract observations and create cost/balanced/precision candidates; never auto-adopt. |
| `parameter_gate.py` | Convert a confirmed candidate into an execution-allowed record. |
| `convergence_manager.py` | List property-specific metrics and candidate axes without inventing thresholds. |
| `input_lint.py` | Perform static section, token, and version-trap checks. |
| `validate_cp2k_input.py` | Compatibility entry point for `input_lint.py`. |
| `render_versioned_template.py` | Render only a registry-approved template with explicit slots. |
| `cp2k_output_parser.py` | Parse version, termination, SCF, energy, geometry, warnings, and errors. |
| `run_cp2k.py` | Run one explicitly approved local input after exact-version probing; no retries or input mutation. |
| `compute_adsorption_energy.py` | Compute three-energy bookkeeping and check supplied invariant metadata. |
| `subtract_cube_density.py` | Audit cube metadata and subtract only common-grid data. |
| `charge_workflow.py` | Keep population, periodic RESP, and REPEAT-like methods separate. |
| `input_builder.py` | Build and parse nested CP2K sections, repeated blocks, and conditionals. |
| `structure_audit.py` | Run a read-only structure audit with an XYZ fallback. |
| `structure_audit_full.py` | Use optional pymatgen/spglib for occupancy, contacts, and symmetry; missing dependencies remain `NOT_VALIDATED`. |
| `provenance.py` | Write a JSON-as-YAML-compatible provenance record with file hashes. |
| `self_check.py` | Check release files, registry paths, templates, and public-boundary markers. |

These tools do not replace the exact CP2K manual, a basis/potential registry,
an executable smoke test, or scientific judgment.
