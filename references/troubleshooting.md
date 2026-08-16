# Troubleshooting and stop rules

- grompp error or a warning requiring maxwarn: stop and fix the source or topology.
- Missing parameter or unclear cross term: stop and classify as incomplete.
- Packmol count mismatch or overlap: stop before EM.
- LINCS, NaN, PME, or DD fatal error: stop, preserve logs, and diagnose.
- Checkpoint missing or incompatible: do not regenerate velocities silently.
- No RDF minimum or no diffusive regime: report the limitation; do not fabricate a number.
- A GPU executable can use CPU for some tasks; check the GROMACS log and task assignment rather than a desktop utilization graph.
