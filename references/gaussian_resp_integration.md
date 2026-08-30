# Gaussian plus Multiwfn RESP integration

This Skill reuses the existing gaussian-resp-charge-workflow as a source implementation. The source directory is discovered by scripts/gaussian_resp_router.py; it is not assumed to exist at one absolute path on a migrated machine.

## Source discovery

The router checks, in order:

1. A caller-supplied `--source-root`.
2. `GAUSSIAN_RESP_WORKFLOW_ROOT` from the environment.

No machine-specific source path is assumed. If neither input is available, the router returns `DEPENDENCY_BLOCKED` and does not execute Gaussian, formchk, Multiwfn, or GROMACS.

A route is FOUND only when the source has its SKILL.md, the formal RESP references, and the required scripts. The router records source hashes and the exact root. It never downloads, modifies, or executes the source workflow during discovery.

## RESP1 route

Use this route when one formal RESP charge vector is required.

1. Validate the molecule identity, atom order, formal charge, multiplicity, and a sourced RESP1 profile.
2. Audit the Gaussian, formchk, and Multiwfn executables and their versions.
3. Choose USE_EXISTING_OPTIMIZED_GEOMETRY or OPTIMIZE_THEN_RESP. The geometry decision is explicit; a missing geometry source is a gate failure.
4. Prepare Gaussian input, manifest, atom_mapping.csv, and equivalence_groups.csv with prepare_resp_job.py.
5. Run Gaussian optimization if requested, then a RESP gas-phase single point using the same frozen atom mapping. Require normal termination, SCF convergence, checkpoint, and geometry identity.
6. Convert CHK to FCHK with formchk and check atom count, atomic numbers, charge, multiplicity, and hashes.
7. Run the validated native Multiwfn two-stage RESP path. For the local Multiwfn 3.8_dev route the audited menu is 7 -> 18 -> 1. The exact stdin and version registry are retained in multiwfn_native_resp_registry.yaml.
8. Parse and validate native output: finite charges, atom mapping, equivalence constraints, fitted point count, residual metrics, and total-charge closure.
9. Export only a derived charges.csv/charges.json or ITP. Raw Gaussian, FCHK, Multiwfn, source topology, and bonded/LJ terms remain unchanged.

The diagnostic cube-plus-Python fitter is not silently labeled formal RESP. It needs a separate numerical equivalence audit.

## RESP2 route

Use this route when a gas and implicit-water pair must be interpolated.

1. Freeze one validated geometry and one atom mapping. The gas and CPCM-water branches must have identical atom count, order, elements, coordinates, charge, multiplicity, RESP settings, and equivalence groups.
2. Prepare and run the gas branch with the RESP1 route.
3. Prepare and run the CPCM-water branch without aqueous reoptimization. Require SCRF=CPCM water or the explicitly sourced solvent protocol.
4. Convert both CHK files to FCHK and validate both branches independently.
5. Run the same validated native Multiwfn two-stage RESP workflow on each branch. Do not fit three charges and average them.
6. Mix only after both charge vectors pass validation:
   q_RESP2 = (1 - delta) q_gas + delta q_aqueous
   where delta is supplied by the approved profile, such as 0.5 or 0.6. The mixer does not renormalize, shift, scale ions, or modify atom order.
7. Check interpolation identity at delta 0 and 1, requested delta values, formal-charge closure, equivalence groups, per-atom deltas, and input/output hashes.
8. Register gas, aqueous, and RESP2 vectors separately. A RESP2 result is not a RESP1 result renamed.

## Multi-conformer extension

For approved multi-conformer RESP, use a common-charge simultaneous fit with equal weights through the audited native Multiwfn route. Do not independently fit each conformer and average. For multi-conformer RESP2, fit one common gas vector and one common aqueous vector, then apply the same strict mixer. Multi-conformer production readiness remains molecule-specific and requires a conformer, mapping, QM, and charge audit.

## Execution boundary

The router is a discovery and plan tool. It lists exact source scripts and profiles but does not start Gaussian, formchk, Multiwfn, or GROMACS. Execution requires a separate user-approved stage and must preserve raw/derived separation, checkpoint recovery, and stage reports.
