# Formal RESP definition and local implementation audit

This document freezes the scientific definition used for Stage RESP-1 before
any implementation is called formal. It is not inferred from the legacy
Python fitter. The primary literature source is Bayly et al., *J. Phys.
Chem.* 1993, DOI [10.1021/j100142a004](https://doi.org/10.1021/j100142a004).
The implementation-specific source is the locally installed Multiwfn 3.8_dev
manual (official download page:
<https://www.umsyar.com/multiwfn/download.html>; official manual:
<https://www.umsyar.com/multiwfn/misc/Multiwfn_3.8_dev.pdf>), together with
captured stdout from the exact executable tested in this project.

## Mathematical definition

For ESP values `V_k^QM` at fitting points `r_k`, RESP minimizes a weighted ESP
residual plus a hyperbolic restraint:

`sum_k w_k [V_k(q) - V_k^QM]^2 + sum_i a_i (sqrt(q_i^2 + b_i^2) - b_i)`

where `V_k(q) = sum_i q_i / |r_k-R_i|` in consistent atomic units. The Bayly
protocol requires a molecular total-charge constraint for the RESP result.
Chemical
equivalence constraints are linear equalities (for example the three methyl
hydrogens in methanol). The penalty is not a post-fit charge closure edit.
The derivative used for auditing is `a_i q_i / sqrt(q_i^2+b_i^2)`.

## Bayly two-stage protocol

The standard RESP protocol has two coupled fits. Stage 1 fits all atoms with
the weak hyperbolic restraint and the molecule charge constraint. Stage 2
uses the stage-1 result as the starting/fixed reference, applies the stronger
restraint to the atoms selected by the protocol, freezes the remaining atoms,
and enforces chemical equivalence groups. Hydrogen handling is therefore not
the same as “fit every atom independently”; the exact stage-2 fitted set and
equivalence rules must be recorded for the implementation used.

## Local Multiwfn 3.8_dev audit

The exact executable banner is `Version 3.8(dev), update date: 2025-Oct-2`.
The verified menu path is main menu `7` (population analysis) then `18`
(RESP). Standard option `1` runs the native two-stage workflow; option `2`
is retained only as a one-stage diagnostic. The validated standard stdin
sequence, including the initial settings prompt, is:

```text
<blank>
7
18
1
y
0
0
q
```

Runtime observations for this build are:

* Stage 1 reports weak restraint `a=0.0005`, `b=0.1`, convergence `1e-6`,
  and no equivalence constraint in the stage-1 screen. This build also prints
  “No charge constraint is imposed in this stage”; that is recorded as a
  version-specific implementation observation, not silently rewritten as the
  Bayly ideal. The final result is independently checked against the FCHK
  formal charge.
* Stage 2 reports strong restraint `a=0.001`, `b=0.1`; it fits sp3/methyl
  carbons and hydrogens attached to them while other atoms retain stage-1
  values. Methanol reports the equivalence group H 2/3/4. Water correctly
  reports Stage 2 skipped because there is no atom requiring the second fit.
* The default fitting method observed is MK, with automatic vdW radii and
  nuclear-plus-electronic ESP. Water used 2933 points (H 1.2 Å, O 1.4 Å);
  methanol used 4866 points (H 1.2 Å, C 1.5 Å, O 1.4 Å).
* The native output is `resp_sp.chg` with element, coordinates, and charge.
  Native stdout prints the final charge table, RMSE/RRMSE and stage markers;
  this build does not print a Stage-1 charge table in the standard path. A
  separate option-2 run is therefore recorded as a diagnostic reference,
  never substituted for the standard two-stage production path.

These values are implementation observations from the local binary and are
not silently promoted to a universal Bayly default. The complete registry is
`references/multiwfn_native_resp_registry.yaml`.

## Scope boundary

The legacy cube-plus-Python constrained fitter is audited separately and is
classified `NOT_FORMAL_RESP`: it uses a Multiwfn cube, a project-selected
distance shell and an iteratively reweighted least-squares penalty, but it does
not reproduce the local native MK surface, native stage-2 freezing, or native
point generation. Native Multiwfn is consequently the only validated formal
engine in this stage. RESP2, multi-conformer RESP, solvent mixing, and any
electrolyte-specific parameter decision remain outside this validation.
