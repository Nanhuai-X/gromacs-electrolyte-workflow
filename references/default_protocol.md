# Default bulk electrolyte protocol

This is the default protocol for a bulk liquid electrolyte when no complete literature protocol has been approved. It is a reproducible starting point, not an assertion that every force field or composition is valid.

## Stage schedule

| Stage | Duration | Ensemble and controls | Gate |
|---|---:|---|---|
| EM | until converged | steepest descent then validated fallback | EM_VALIDATED |
| NVT anneal | 600 ps | 298.15 -> 350 -> 298.15 K | NVT_ANNEAL_VALIDATED |
| NPT | 5 ns minimum | 298.15 K, 1 bar, C-rescale isotropic | NPT_CONVERGED |
| NPT extension | +2 ns per extension, maximum 10 ns total | unchanged physical settings | NPT_CONVERGED |
| NVT transition | 1 ns | representative final NPT box, 298.15 K | NVT_TRANSITION_VALIDATED |
| production | 20 ns | NVT, 298.15 K | PRODUCTION_COMPLETED |

NPT is extended only when block density, volume, pressure, or structural diagnostics fail their declared criteria. The extension decision is recorded; it is never an automatic request to run 30 ns or longer.

## Exact anneal schedule

annealing=single, annealing-npoints=6, annealing-time=0 100 200 350 500 600, and annealing-temp=298.15 298.15 350 350 298.15 298.15 K.

At dt 0.002 ps, 600 ps is 300000 steps. Output intervals of 1000 steps correspond to 2 ps and give 301 anneal frames including the initial frame.

## MDP invariants

- dt 0.002 ps requires validated h-bond constraints.
- constraints=h-bonds, lincs-order=4, lincs-iter=1.
- pbc=xyz, cutoff-scheme=Verlet, coulombtype=PME.
- NVT uses a validated thermostat; the default template uses Nose-Hoover for transition and production with a single temperature group.
- NPT uses C-rescale isotropic, tau-p 5 ps, compressibility 4.5e-5 bar-1.
- continuation=yes and gen_vel=no for stages resumed from a prior checkpoint. Production does not regenerate velocities.
- Every production run uses mdrun checkpoint interval 15.

## Output accounting

At 2 fs, 20 ns is 10000000 steps. nstxout-compressed=1000 yields 10000 intervals plus the initial frame, so expected frame count is 10001 if all frames are present. nstenergy=1000 and nstlog=5000 are balanced defaults. The exact resolved values are taken from mdp_builder output.
