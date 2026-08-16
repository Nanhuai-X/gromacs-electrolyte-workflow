# GROMACS MDP policy

Generate MDP from a resolved protocol object. Keep integration settings separate from output settings. Record dt, constraints, LINCS, PME, cutoff scheme, thermostat, barostat, pressure, temperature, dispersion correction, continuation, velocity generation, and output intervals with a source for each field.

Never add maxwarn. A production continuation requires a valid checkpoint and gen_vel=no. GPU flags are execution choices and must be reported, not inferred from CPU utilization.
