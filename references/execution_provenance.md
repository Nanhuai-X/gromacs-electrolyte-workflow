# Execution, security, and provenance

## Execution boundary

Select one target explicitly:

- `LOCAL`: an executable found by `shutil.which` or an explicit local path.
- `REMOTE_SERVER`: a scheduler-backed directory on a named server.

For remote work record hostname, scheduler, work directory, command, and job
identifier before submission. Use SSH keys or an existing SSH agent. Never
write a password, private key, token, or scheduler credential to a job file,
manifest, log, or report.

## Calculation record

Every calculation should contain a record equivalent to:

```yaml
schema_version: "1.0"
job_id: "stable-local-id"
parent_calculations: []
structure:
  source: "input_structure/source.cif"
  sha256: "..."
  derived_sha256: "..."
task: "geo_opt"
workflow: "geometry_optimization"
run_target: "LOCAL"
hostname: "..."
scheduler: null
scheduler_job_id: null
cp2k:
  executable: "..."
  version: "2024.1"
  manual_manifest: "manual_manifest.yaml"
  input_sha256: "..."
  output_sha256: "..."
  restart_files: []
scientific_model:
  functional: "PBE"
  dispersion: null
  charge: null
  multiplicity: null
  spin_state: "SCIENTIFIC_DECISION_REQUIRED"
  dft_u: null
  basis: {}
  potential: {}
  kpoints: null
  cutoff: null
  rel_cutoff: null
status: "NOT_STARTED"
validation: []
outputs: []
provenance:
  commands: []
  repairs: []
```

The null scientific values are intentional. Replace them only after the
corresponding decision gate is satisfied.

## Hash and validation policy

Hash the raw and derived structures, rendered input, raw CP2K output, scheduler
logs, restart files, cube/DOS/PDOS files, and final reports after completion.
Require return code, normal termination, SCF evidence, finite numeric values,
and property-specific checks. File existence alone is never a pass.

Repairs are append-only and must record reason, evidence, before/after values,
whether the scientific model changed, and the result. A repair may fix an exact
syntax/path/resource problem or use a bounded validated SCF recipe; it may not
silently change charge, spin, functional, dispersion, basis family, cell,
k-points, endpoints, or property definition.

## Archive layout

```text
calculation/
  calculation.yaml
  input_structure/
  inputs/
  outputs/
  restart/
  logs/
  postprocess/
  figures/
  provenance/
  reports/
```
