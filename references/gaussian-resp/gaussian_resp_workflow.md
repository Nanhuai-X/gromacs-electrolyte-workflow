# Gaussian/formchk execution policy

Reuse the reference Skill's `gaussian_runner.run_gaussian` and
`formchk_runner.run_formchk`. They use list arguments and `shell=False`, build a
child environment containing `GAUSS_EXEDIR`/`GAUSS_SCRDIR`, preserve stdout and
stderr, enforce timeouts, and record return codes and output sizes.

Required checks are stronger than file existence:

- Gaussian log has normal termination and no error termination;
- optimization has an explicit convergence marker when requested;
- CHK is non-empty;
- formchk returns zero and FCHK is non-empty;
- FCHK atom count, atomic numbers, charge and multiplicity agree with the
  source manifest;
- all artifacts are hashed.

HOMO/LUMO or a pre-existing FCHK may be reused for execution provenance, but
their theory level is not silently accepted as a RESP protocol.
