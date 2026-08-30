# Literature-aware numerical parameter selection

## Evidence before adoption

When a user supplies a paper, SI, DOI, or local PDF, extract observations such
as functional, dispersion, basis, cutoff, REL_CUTOFF, k-point mesh, smearing,
EPS_SCF, MAX_SCF, force thresholds, cell treatment, and charge/spin choices.
Record the source path/DOI, hash when local, and a short context snippet. An
observed value is labelled `LITERATURE_OBSERVED`; it is not copied silently
into a CP2K input.

If the reference is inaccessible or text extraction fails, report
`LITERATURE_RETRIEVAL_REQUIRED` and continue only with a user-approved
non-literature profile.

## Three candidate profiles

Present all three even when the user has a preference:

| Profile | Purpose | Typical consequence |
|---|---|---|
| `COST_EFFECTIVE` | fast screening and debugging | smaller cells/meshes and shorter probes, but narrower claims |
| `BALANCED` | normal production candidate | moderate cost with property-specific convergence |
| `HIGH_PRECISION` | publication-critical or force-sensitive result | tighter cutoffs/SCF/property tests and higher cost |

The exact numbers come from the reference, an existing validated project
profile, or a user decision. The Skill must not invent universal cutoffs,
k-meshes, force thresholds, or smearing values.

## Confirmation gate

The agent shows a compact comparison containing:

- functional/dispersion;
- basis/potential;
- cutoff and REL_CUTOFF;
- k-point mesh;
- EPS_SCF and MAX_SCF;
- geometry thresholds;
- smearing/ADDED_MOS;
- expected cost class and likely limitation;
- which values came from the user, literature, or project defaults.

The user selects one profile or edits the values. Only then does
`parameter_gate.py` write `execution_allowed: true`. Any unresolved item stays
`SCIENTIFIC_DECISION_REQUIRED` or `USER_CONFIRMATION_REQUIRED`.

## Convergence remains mandatory

Literature replication is not a substitute for convergence in the current
structure, executable, and backend. Run the minimum property-specific probe
after confirmation. A paper's Gamma-only setup may be appropriate for its cell
but does not prove Gamma-only convergence for a different cell.
