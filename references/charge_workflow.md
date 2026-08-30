# Periodic charge workflow

## Separate definitions

Keep these outputs separate:

- Hirshfeld population analysis;
- Mulliken or Lowdin population analysis;
- periodic RESP;
- CP2K `USE_REPEAT_METHOD` output, labelled `REPEAT_LIKE` unless exact
  original-REPEAT equivalence is established.

Do not choose a model because its charges are closer to zero. Do not apply a
post-hoc uniform charge shift unless the method itself defines that constraint.

## Workflow

```text
validated final structure
  -> common reference SCF/density
  -> Hirshfeld / Mulliken / Lowdin
  -> periodic RESP
  -> REPEAT_LIKE
  -> mapping and charge closure
  -> equivalence and sampling sensitivity
  -> candidate recommendation
```

All ESP-based methods retain sampling settings, radii, restraints, fit quality,
and sensitivity runs. Every method must report total-charge closure and atom
mapping. Chemically equivalent sites are analysed but never silently averaged.

## GROMACS boundary

The output can be marked:

```text
GROMACS_CHARGE_CANDIDATE_ONLY
```

That does not establish a complete force field. LJ, bonded terms, Zn-N model,
cross interactions, and MD validation remain separate. The Skill must not
modify the GROMACS project or write an ITP as part of this charge workflow.
