# RESP1 versus RESP2 user decision

Before any new Gaussian work, ask the user to choose RESP1 or RESP2. The Skill must not silently choose from a missing value.

## RESP1

Recommended default for cost-controlled electrolyte component work when the approved protocol supports it.

- One formal RESP charge workflow.
- One Gaussian ESP branch per approved geometry set.
- Lower Gaussian and Multiwfn cost.
- Does not include an implicit-solvent interpolation.

## RESP2

Higher-cost option when the user wants gas/solvent electrostatic sensitivity and the source protocol supports it.

- Gas ESP branch and implicit-solvent ESP branch.
- Same geometry, atom mapping, charge, multiplicity, equivalence groups, and RESP settings across branches.
- Strict interpolation q = (1-delta) q_gas + delta q_aqueous.
- More QM/ESP jobs and stronger provenance burden.
- Not automatically more accurate for every electrolyte and not interchangeable with ionic charge scaling.

If a literature protocol explicitly specifies RESP, RESP2, QM method, basis, functional, dispersion, solvent model, restraint, or delta, those fields override the default only after the source and compatibility audit pass. If it does not specify them, the user must choose the approved project profile; the Skill does not invent a method or basis.

Both routes require atom mapping, equivalence groups, charge closure, raw/derived separation, and a stage report before topology construction.
