# Remote SSH onboarding and scheduler boundary

## First interaction

For a remote calculation, collect:

1. hostname;
2. SSH port;
3. username;
4. local private-key path;
5. a verified `known_hosts` file or a host-key fingerprint that the user has
   confirmed;
6. remote working directory;
7. scheduler and account/partition if the site requires them.

Never ask the user to paste a private key. Never copy the key into the project.
The key path and its file hash may be recorded as metadata only if the local
security policy permits it; key contents must never enter logs or provenance.

## Preflight

Run `scripts/remote_ssh.py` with strict host-key verification:

```text
BatchMode=yes
StrictHostKeyChecking=yes
UserKnownHostsFile=<verified-known-hosts>
```

The helper must fail with `SSH_HOST_KEY_REQUIRED`/configuration error when the
known-hosts file is absent. It must not use `StrictHostKeyChecking=accept-new`.
The first connection therefore requires an explicit user-side fingerprint
verification step.

The preflight may inspect hostname, home/project paths, scheduler commands,
CP2K candidates, and data directories. It must not submit a job.

## Submission boundary

Use `scripts/scheduler_remote.py` to construct a scheduler command. Submission
is an external mutation and requires all of:

- an approved `calculation.yaml`;
- a user-confirmed parameter plan;
- input lint and executable smoke evidence;
- an explicit submission approval at the execution boundary.

Status queries are read-only and may continue without re-approval. Use
`sbatch`, `qsub`, or `bsub` for formal work; never run formal CP2K on a login
node. Record scheduler job ID, command, stdout, stderr, exit state, host, and
timestamps.

## Server-side file layout

```text
remote_workdir/
  inputs/<version>/<job>.inp
  jobs/<scheduler>.sh
  calculations/<job>/
  outputs/<job>/
  restart/<job>/
  provenance/<job>.yaml
```

Keep CP2K 2024.x and 2026.x directories separate. Do not reuse a WFN restart
until the exact executable/version and compatibility are verified.
