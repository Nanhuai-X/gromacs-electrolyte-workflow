# Literature protocol mode

Literature mode reproduces a source only when the source or SI provides enough information to resolve the requested stage. Reference-guided mode uses the source as a scientific comparison while keeping the default protocol unless the user explicitly approves a change. Hybrid mode uses source values where present and fills missing fields from the default with an explicit deviation list.

## Required extraction fields

Record publication, DOI, version, temperature, pressure, ensemble, timestep, constraints, thermostat, barostat, cutoffs, PME, neighbor list, dispersion correction, composition and molecule counts, equilibration lengths, production length, output intervals, charge model, force-field family, 1-4 rules, and analysis definitions. Use NOT_REPORTED when absent.

## Decision rules

- A missing timestep or force-field term blocks literal reproduction.
- A reported number without units or context is unresolved.
- A different output frequency is a reporting change only if it does not alter integration.
- A literature density is a reference, not a fitting target.
- Do not import a paper's charge scaling into a different solvent model without a compatibility audit.
