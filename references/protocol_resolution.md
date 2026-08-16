# Protocol resolution and precedence

The workflow has one resolved protocol object. It is created before MDP generation.

## Precedence

1. An explicitly approved literature protocol field.
2. A user-approved override recorded in the input manifest.
3. The default protocol field from default_protocol.md.
4. No hidden fallback.

The resolver records field_sources, DEFAULT_FILLED, literature_source, and unresolved_required. Reproduction mode stops when required literature fields are missing. Reference_guided and hybrid modes fill missing fields from the default but report each filled field.

## Fields that may be literature overrides

Temperature, pressure, timestep, constraints, LINCS settings, thermostat and tau-t, barostat and coupling type, tau-p, compressibility, Coulomb method (PME or literal Ewald), cutoff scheme, pbc, dispersion correction, anneal schedule, EM settings, NPT/NVT/production lengths, output intervals, checkpoint interval, QM method, basis, functional, dispersion, solvent model, ESP method, RESP restraint/equivalence settings, and RESP2 interpolation factor.

A paper must provide units and stage context. A number copied without units or a clear definition is unresolved.

## MD consequence

The generated MDP files use the resolved values. If a literature paper specifies Berendsen, Ewald, a different thermostat, a different temperature schedule, or another timestep, the generated file reflects that only when the field is explicitly present and the compatibility report accepts it. The Skill does not silently convert a literature protocol into the default.

## Scientific boundary

Changing a thermostat, barostat, QM method, basis, functional, solvent model, charge method, or timestep is a protocol change and is reported as a deviation. A literature density is a validation reference, not a fitting target.
