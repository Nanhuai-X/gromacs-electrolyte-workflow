# WSL/Linux environment gate

This Skill uses the configured control/provenance root from `assets/electrolyte.yaml`, `--project-root`, or `GROMACS_PROJECT_ROOT`. The default formal GROMACS execution target is WSL/Linux, but the user may explicitly select an SSH remote Linux target or a hybrid local-quantum-chemistry/remote-GROMACS backend.

## First action

1. Ask the user to choose wsl_local, ssh_remote, or hybrid_gaussian_local_gromacs_remote.
2. Record the selection in assets/electrolyte.yaml without storing credentials.
3. Run scripts/environment_preflight.py for the local WSL control environment.
4. For ssh_remote or hybrid mode, run scripts/backend_preflight.py in plan-only mode. Only a user-confirmed connection may run a remote preflight.

The local preflight records:

- WSL2 kernel and distribution;
- project real path and filesystem type;
- direct CPU and CUDA GROMACS prefixes;
- the active PATH GROMACS, nvcc, nvidia-smi, Packmol, Python, GCC, CMake, Make, and Git;
- the project virtual environment;
- optional Gaussian, formchk, Multiwfn, and Gaussian/RESP source workflow;
- missing core tools and a configuration plan.

The preflight is not fooled by an empty PATH. It checks validated prefixes and the project virtual environment directly. It must not install a second GROMACS when the WSL CPU or CUDA prefix already exists.

## Core and optional dependencies

Core bulk MD requirements are a usable WSL2 Linux environment, an ext4 project filesystem, a validated GROMACS CPU or CUDA prefix, Python, Packmol, GCC, CMake, and Make. Gaussian, formchk, and Multiwfn are required only when a new RESP calculation is approved. Existing RESP registries can be consumed without re-running quantum jobs.

If a core requirement is genuinely absent, status is ENVIRONMENT_BLOCKED. scripts/environment_setup.py creates a plan and can write a run-local loader only with an explicit confirmation file. It never runs sudo, apt, pip, conda, or system configuration changes. The user-approved installation stage must be completed first.

## Remote backend

The remote host is not assumed to be WSL and is not a replacement for the local control root. The remote preflight must independently check Linux filesystem, GROMACS version/path, CPU/GPU capability, free disk, and the selected environment loader. Private keys are downloaded and placed by the user; the Skill stores only the path and never copies or prints key contents. See references/remote_execution.md.

## Runtime environment

Use the project loaders:

- scripts/env_gromacs_cpu.sh for CPU checks;
- scripts/env_gromacs_cuda.sh for GPU checks;
- .venv/bin/activate for Packmol and Python tools.

A clean shell must load exactly one GROMACS variant for a run. GPU availability is established from nvidia-smi and the GROMACS log/task assignment, not from CPU utilization alone.

## Gate semantics

- PASS: WSL/ext4 and all core tools are available.
- PASS WITH LIMITATIONS: core tools are available but optional quantum or GPU capabilities are absent.
- ENVIRONMENT_BLOCKED: a core tool, project filesystem, or WSL execution requirement is missing.
- USER_DECISION_REQUIRED: execution backend, RESP method, molecule count, or structure identity is not supplied.

No downstream gate can turn ENVIRONMENT_BLOCKED into a scientific pass.
