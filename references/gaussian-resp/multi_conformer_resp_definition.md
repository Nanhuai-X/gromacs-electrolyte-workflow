# Multi-conformer RESP/RESP2 definition (Stage RESP-3)

## Scope

This document fixes the scientific meaning of the Stage RESP-3 implementation.
It is a common-charge fit over several conformers of one molecule.  It is not
an arithmetic average of independently fitted charge vectors.

For conformers (k=1,…,N), with a common atom mapping and positive weights
(w_k), the fitted vector (q) is the single vector that minimizes the
weighted sum of the RESP objectives:

\[
  \underset{q,\,\sum_i q_i=Q}{\operatorname{argmin}}
  \sum_k w_k\left[\chi^2_k(q)+P_{\mathrm{RESP}}(q)\right].
\]

The same atom equivalence groups, total-charge constraint, two-stage
restraint policy, ESP definition, and atom order are used for every conformer.
Weights are recorded in `conformers.list`; Stage RESP-3 validates equal weights
only.  Boltzmann weighting is intentionally not validated.

The gas and aqueous branches each produce their own common charge vector using
the same conformer mapping.  RESP2 is then the strict, derived operation

\[
q_{RESP2}(\delta)=(1-\delta)q_{gas}+\delta q_{aqueous},
\quad 0\leq\delta\leq1.
\]

The mixer does not renormalize, rescale ionic charges, reorder atoms, or alter
coordinates.  Endpoint identity (δ=0 and δ=1), intermediate linearity, and
formal-charge closure are required.

## Equivalence and mapping gates

- Every FCHK must have the same atom count, atomic numbers, formal charge and
  multiplicity.
- XYZ atom order is the mapping authority for the stdout-only common-charge
  table produced by the local Multiwfn build.
- Missing, duplicated, or ambiguous mapping is a hard failure.
- A conformer set must contain genuine graph-preserving conformers; adding
  coordinate noise is not sufficient.
- Independent per-conformer RESP outputs are retained only as diagnostics.

## Source definition

The RESP restraint and charge-constraint definition follows Bayly *et al.*,
DOI [10.1021/j100142a004](https://doi.org/10.1021/j100142a004).  RESP2 mixing
follows the published linear gas/solvent construction in DOI
[10.1038/s42004-020-0291-4](https://doi.org/10.1038/s42004-020-0291-4), with the
local Multiwfn implementation and exact settings recorded in the registry.

This formal definition is independent of force-field selection and does not
authorize parameterization of DME, TTE, FSI, TFSI, Li+, or an electrolyte.
