# Execution backend and SSH guide

The control and provenance root is the user-configured `system.execution_root` in `assets/electrolyte.yaml`, or the value passed through `--project-root`/`GROMACS_PROJECT_ROOT`. Choose one execution backend before any formal run:

- wsl_local: Gaussian/RESP may run in the local Windows workflow when approved; GROMACS runs in the audited WSL prefixes.
- ssh_remote: approved remote Linux host runs GROMACS.
- hybrid_gaussian_local_gromacs_remote: Gaussian/RESP runs locally through the Windows Gaussian workflow; derived, hashed charge/topology inputs are transferred to the remote Linux host for GROMACS.

## Manual private-key setup

The user must download the provider's private key manually. Do not ask the Skill to retrieve it and do not place it in the project.

Recommended locations:

- Windows OpenSSH: C:\Users\<user>\.ssh\lhce_server_ed25519 or the provider .pem.
- WSL OpenSSH: /home/<user>/.ssh/lhce_server_ed25519.

If the key is downloaded on Windows and used by WSL, copy it manually to the WSL user's ~/.ssh directory, then set owner and mode manually:

    mkdir -p ~/.ssh
    cp /mnt/c/Users/<user>/.ssh/lhce_server_ed25519 ~/.ssh/
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/lhce_server_ed25519

Do not store a private key under the configured control root, `runs/`, `reports/`, or any source archive. Do not paste the key into chat, YAML, logs, reports, or provenance. `assets/electrolyte.yaml` stores only the path, never key contents.

Required remote fields are:

- host or provider DNS name;
- SSH username;
- port, normally 22;
- private-key path;
- verified known_hosts entry;
- remote project root and work directory;
- CPU/GPU environment loader path.

The first host-key decision is manual. Keep StrictHostKeyChecking=yes; never use StrictHostKeyChecking=no as a convenience.

## Preflight and connection

Run:

    python3 scripts/backend_preflight.py --config assets/electrolyte.yaml --out reports/backend_preflight.json

The script is plan-only by default. It checks field completeness, local SSH client availability, key-file existence and permission warnings, and emits a redacted SSH command plan. It never reads or prints private-key contents and never copies the key.

Only after the user has verified the host key and explicitly approved connectivity may a controlled preflight be run:

    python3 scripts/backend_preflight.py --config assets/electrolyte.yaml --out reports/backend_preflight_connected.json --connect --confirm-file config/remote_connect.confirm

The remote preflight must report Linux filesystem, GROMACS version/path, CPU/GPU capability, Python/Packmol if needed, free disk, and the selected environment loader before any transfer or GROMACS command.

## Transfer and hash contract

Transfer only derived, approved inputs and manifests. Never transfer the private key. Prefer rsync or scp through OpenSSH with IdentitiesOnly=yes, and do not use --delete for the first synchronization.

Before transfer, create a manifest in the local control root:

    sha256sum outputs/<approved-derived-files>/* > provenance/remote_input.sha256

After transfer, verify on the remote host:

    sha256sum -c provenance/remote_input.sha256

Pull back logs, checkpoints, trajectories, and analysis outputs into a new local run directory, then verify the reverse manifest. A successful SSH copy is not a scientific or topology validation.

## Hybrid local-Gaussian / remote-GROMACS route

1. Run the local Windows Gaussian workflow preflight for Gaussian, formchk, Multiwfn, Python, and required packages.
2. Accept MOL V2000, SDF V2000, XYZ, PDB, or an explicitly identified PubChem structure; confirm identity, geometry, atom order, charge, and multiplicity.
3. Run the approved RESP1 or RESP2 route locally. Keep Gaussian, CHK/FCHK, Multiwfn, RESP logs, and raw structures in the Gaussian source project.
4. Export only the approved derived charge registry, namespaced topology, MDP, Packmol inputs, and SHA256 manifest to the remote GROMACS work directory.
5. Run remote static grompp and all MD stages with no -maxwarn; save remote logs and checkpoint hashes.
6. Pull results back for local analysis/reporting. Do not treat remote execution success as force-field or physical validation.

The backend selector does not choose a server, infer a username, infer a private key, or silently switch local/remote execution. Missing or ambiguous fields stop the workflow.
