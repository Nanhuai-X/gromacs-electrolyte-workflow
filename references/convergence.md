# Convergence planning

## Principle

Use a property-specific metric. Energy convergence alone is insufficient for
forces, stress, adsorption energy, band gaps, DOS, charge density, or work
function.

## Candidate axes

Plan only axes that affect the requested property:

- CUTOFF and REL_CUTOFF;
- basis level;
- SCF EPS_SCF and solver;
- k-point mesh and band-path sampling;
- added states/smearing for DOS or metals;
- supercell and vacuum size;
- slab thickness and fixed-layer policy.

## Suggested acceptance targets

These are Skill recommendations, not CP2K hard standards:

- standard energy: roughly 1 meV/atom;
- adsorption energy: typically 0.01–0.02 eV or a user-approved target;
- work function: typically 0.02–0.05 eV after a vacuum plateau;
- geometry: user- or literature-defined force/RMS/displacement criteria;
- charge density: property-specific integral and local charge stability.

Always record the target and whether it is `USER_SPECIFIED`, `LITERATURE`, or
`SKILL_DEFAULT`. Do not replace an unsuccessful convergence study with a
single reassuring number.

## SCF repair order

Diagnose first: oscillation, charge sloshing, metallic occupation, incorrect
spin, insufficient states, grid, diagonalization, memory, or geometry. Apply a
finite validated recipe and record reason/before/after/result. Never lower
EPS_SCF or use `IGNORE_CONVERGENCE_FAILURE` only to obtain a file.
