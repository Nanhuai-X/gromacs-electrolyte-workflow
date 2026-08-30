# Formal RESP2 definition and protocol audit

Primary source: Schauperl et al., *Communications Chemistry* 3, 44 (2020),
DOI [10.1038/s42004-020-0291-4](https://doi.org/10.1038/s42004-020-0291-4).
The original implementation used Psi4 for QM/ESP calculations and Respyte for
MSK point selection and RESP fitting. This project uses Gaussian plus the
validated local Multiwfn native RESP engine, so the result is named
`GAUSSIAN_MULTIWNF_RESP2_IMPLEMENTATION`, not “original RESP2 code”.

## Definition

Two independently fitted, same-geometry charge sets are generated:

`q_RESP2,i = (1 - delta) * q_gas,i + delta * q_aqueous,i`

`delta=0` is the gas RESP result, `delta=1` is the aqueous RESP result, and
intermediate values are explicit user/profile choices. This is a neutral or
charged-molecule polarization interpolation, not ionic charge scaling and not
an AMBER/Li/FSI scaling factor. No post-fit renormalization, uniform shifting,
or “charge closure” edit is permitted.

## Audited source protocol

The paper reports PW6B95/aug-cc-pV(D+d)Z for ESP calculations, implicit water
with dielectric constant 78.39 using CPCM, Bondi radii, and MSK shells from
1.6 Ri to 2.0 Ri with 0.2 Ri spacing and 2.4 points/Å² per layer. It reports
two-stage RESP with weak hyperbolic restraint `a=0.005 e/a0²` in stage 1 and
`a=0.01 e/a0²` in stage 2, with chemical symmetry and only apolar atoms
refitted in stage 2. The paper’s production workflow can fit multiple
conformers simultaneously with equal weights; this Stage RESP-2 validates only
single-conformer execution and keeps multi-conformer RESP2
`NOT_YET_VALIDATED`.

The paper’s geometry/QM software and the present adapter are different:

| Item | Original RESP2 | This project |
|---|---|---|
| QM driver | Psi4 | Gaussian 16 through the read-only adapter |
| ESP/fitting | Respyte/Psi4 | Native Multiwfn 3.8_dev RESP |
| solvent | CPCM water, ε=78.39 | Gaussian `SCRF=(CPCM,Solvent=Water)` audit |
| geometry | one frozen geometry per branch, or common conformer set | exact same validated XYZ for both branches |

Therefore the correct claim is protocol reproduction with a Gaussian/native
implementation, not bitwise software identity with Psi4/Respyte.

## Guards

Gas and aqueous branches must have identical atom count, order, elements,
coordinates, formal charge, multiplicity, RESP version, two-stage settings,
equivalence rules, and output mapping. Only the QM electrostatic environment
may differ. RESP2 output remains raw charges and is not a force-field or ionic
scaling decision.
