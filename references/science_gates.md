# Scientific decision gates

## Always ask or prove

- total charge and periodic charged-cell treatment;
- spin, multiplicity, magnetic ordering, and initial moments;
- DFT+U element, orbital, U/J convention, and source;
- partial occupancy, disorder, and a valid structural interpretation;
- adsorption reference state and adsorbate charge;
- slab orientation, termination, thickness, vacuum, and dipole treatment;
- NEB endpoint atom mapping and cell compatibility.

## Structure gate

Read the raw file without modifying it. Check formula, cell, PBC, site count,
occupancy, duplicates, near-duplicates, short contacts, NaN, symmetry, and
coordinate consistency. Derived primitive/conventional cells must preserve a
parent hash and transformation. Do not symmetrize, repair occupancy, or alter
topology silently.

## Charge gate

For `CHARGE != 0` with periodic XYZ, state the background/countercharge
assumption and any finite-size limitations. A chemical oxidation state is not a
partial atomic charge. Do not infer multiplicity from an element name.

## Slab gate

For work function, surface adsorption, or interface work, require a separately
audited slab. Check vacuum plateau, surface normal, fixed layers, symmetry or
dipole correction, and whether the property converges with slab/vacuum size.

## Automatic versus scientific choices

Automate deterministic checks, file discovery, version detection, finite-data
checks, convergence sweeps, coordinate mapping, and grid comparisons. Escalate
choices that change the physical model. Report the missing decision and the
completed evidence, rather than asking the user to redo automated audits.
