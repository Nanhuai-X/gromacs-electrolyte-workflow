# Property workflows and acceptance gates

## Energy and geometry

- `ENERGY`: require CP2K normal termination, SCF convergence, finite total
  energy, and exact input hash.
- `GEO_OPT`: keep the cell fixed unless `CELL_OPT` is explicit. Require every
  required SCF to converge, the CP2K geometry completion marker, all force and
  displacement criteria, and a final structure with the expected atom mapping.
- `CELL_OPT`: additionally validate cell/stress convergence and preserve the
  cell transformation.

## Band structure

Use a converged SCF integration mesh and a separate high-symmetry path. Generate
the path with the selected structure tool, preserve labels/coordinates and any
standardization matrix, and parse the raw band file before plotting. Report
VBM/CBM/directness only when the calculation definition supports it. A PBE gap
is not an experimental or quasiparticle gap.

## DOS and PDOS

Use a suitable k mesh, state count, broadening, and exact version layout. Keep
raw `.dos`/`.pdos` files, parsed CSV, and figures. Validate finite rows,
energy reference, spin channels, and state coverage. Do not create a PDOS file
or claim support when CP2K emitted none.

## ELF and density

Confirm the exact manual syntax for `ELF_CUBE` and `E_DENSITY_CUBE`. Validate
grid shape, origin, axes, cell, finite values, and atom block before exposing a
cube to VESTA/VMD/Multiwfn.

## Adsorption energy

Use:

```text
E_ads = E_complex - E_host - E_adsorbate
```

State the sign convention; negative is favorable under this convention. Keep
functional, dispersion, basis, potential, cutoff, SCF, charge, spin, cell,
and k-point policy identical. Distinguish relaxed adsorption energy from
fixed-geometry interaction energy and optionally report host deformation. Offer
BSSE when a localized Gaussian basis makes it relevant. Use
`scripts/compute_adsorption_energy.py` only for the arithmetic; it cannot
choose the reference state or prove the three calculations are comparable.

## Charge-density difference

Use frozen fragments in the complex coordinate frame:

```text
delta_rho = rho_complex - rho_host_same_geometry - rho_adsorbate
```

Reject subtraction unless all cubes have identical atom frame, cell, origin,
voxel axes, grid shape, cutoff, REL_CUTOFF, basis, potential, XC, and
periodicity. Use `scripts/subtract_cube_density.py` for the common-grid audit
and subtraction. Save its audit, the difference cube, plane average, and
integrated residual.

## Work function

Require a slab model, orientation, termination, thickness, vacuum, dipole
policy, charge/spin, and k mesh. Compute `Phi = V_vacuum - E_F` only after a
vacuum plateau is demonstrated and the exact potential sign convention is
documented. Do not call a bulk cell plus vacuum a validated surface model.

## Population and periodic charges

Keep Mulliken, Lowdin, Hirshfeld, periodic RESP, and REPEAT-like outputs
separate. Verify total-charge closure, mapping, equivalence statistics, and
fit quality. Do not relabel a method or apply post-hoc charge shifts without a
method-defined constraint.
