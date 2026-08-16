# Force-field compatibility audit

Compare native and target representations before merging components.

Audit mass, charge, sigma/epsilon or C6/C12, bonded functions, improper definitions, pair and exclusion rules, nrexcl, fudgeLJ, fudgeQQ, combination rule, nonbond_params, pairtypes, and atom-type namespace. Check same-species and selected cross-species pair potentials at multiple distances. A conversion is PASS only when the mathematical potential and 1-4 behavior are preserved or the deliberate difference is explicitly approved.

Do not use include order to resolve a collision. Do not call a source compatible merely because grompp accepts it.
