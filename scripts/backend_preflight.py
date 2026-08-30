#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from common import dump_json, load_data

BACKENDS = (
    "wsl_local",
    "ssh_remote",
    "hybrid_gaussian_local_gromacs_remote",
)


def normalize_local_path(value: str | None) -> Path | None:
    if not value or value in ("TODO", "null"):
        return None
    raw = os.path.expanduser(value)
    if len(raw) >= 3 and raw[1] == ":" and raw[2] in ("\\", "/"):
        drive = raw[0].lower()
        tail = raw[3:].replace("\\", "/")
        return Path(f"/mnt/{drive}/{tail}")
    return Path(raw)


def remote_config(execution: dict) -> dict:
    value = execution.get("remote")
    return value if isinstance(value, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--backend", choices=BACKENDS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--connect", action="store_true", help="only with an explicit confirmation file")
    ap.add_argument("--confirm-file")
    args = ap.parse_args()

    cfg = load_data(args.config) or {} if args.config else {}
    execution = cfg.get("execution") if isinstance(cfg.get("execution"), dict) else {}
    system = cfg.get("system") if isinstance(cfg.get("system"), dict) else {}
    formal_root = (
        execution.get("execution_root")
        or system.get("execution_root")
        or os.environ.get("GROMACS_PROJECT_ROOT")
    )
    if formal_root in ("", "TODO", "null"):
        formal_root = None
    backend = args.backend or execution.get("backend")
    result = {
        "status": "USER_DECISION_REQUIRED" if backend in (None, "", "TODO") else "PASS",
        "backend": backend,
        "formal_control_root": formal_root,
        "gromacs_target": execution.get("gromacs_target"),
        "gaussian_target": execution.get("gaussian_target"),
        "private_key_contents_read": False,
        "private_key_copied": False,
        "network_action": "none",
        "missing": [],
        "warnings": [],
        "command_plan": [],
    }
    if backend in (None, "", "TODO"):
        result["question"] = (
            "Choose wsl_local, ssh_remote, or hybrid_gaussian_local_gromacs_remote "
            "before execution."
        )
    elif backend not in BACKENDS:
        result["status"] = "FAIL"
        result["missing"].append("unsupported_backend")
    elif backend == "wsl_local":
        result["status"] = "PASS"
        result["gromacs_target"] = execution.get("gromacs_target") or "wsl_local"
        result["gaussian_target"] = execution.get("gaussian_target") or "optional_local"
        result["command_plan"].append(
            "source the existing WSL CPU or CUDA environment loader; do not use Windows gmx"
        )
    else:
        remote = remote_config(execution)
        host = remote.get("host")
        username = remote.get("username")
        port = remote.get("port", 22)
        key_value = remote.get("private_key_path")
        remote_root = remote.get("remote_project_root")
        known_hosts = remote.get("known_hosts_file")
        for key, value in (
            ("remote.host", host),
            ("remote.username", username),
            ("remote.private_key_path", key_value),
            ("remote.remote_project_root", remote_root),
        ):
            if value in (None, "", "TODO"):
                result["missing"].append(key)
        if remote_root not in (None, "", "TODO") and not str(remote_root).startswith("/"):
            result["missing"].append("remote.remote_project_root_absolute_path")
        key_path = normalize_local_path(key_value)
        if key_path is not None:
            result["private_key_path_for_ssh"] = str(key_path)
            if not key_path.is_file():
                result["missing"].append("private_key_file")
            else:
                mode = stat.S_IMODE(key_path.stat().st_mode)
                if mode & 0o077:
                    result["warnings"].append(
                        "private key is accessible by group/other; fix permissions manually to 600"
                    )
        ssh = shutil.which("ssh")
        if not ssh:
            result["missing"].append("ssh_client")
        if known_hosts in (None, "", "TODO"):
            result["warnings"].append(
                "verify the server host key and retain StrictHostKeyChecking=yes; no automatic trust"
            )
        if ssh and host not in (None, "", "TODO") and username not in (None, "", "TODO") and key_path is not None:
            target = f"{username}@{host}"
            options = [
                ssh,
                "-p",
                str(port),
                "-i",
                str(key_path),
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                target,
            ]
            result["command_plan"].append(" ".join(shlex.quote(part) for part in options) + " 'uname -a; command -v gmx || true'")
        result["remote_policy"] = (
            "run remote environment_preflight before any GROMACS command; "
            "transfer only hashed derived inputs; never copy private keys into the project"
        )
        if args.connect:
            if not args.confirm_file or not Path(args.confirm_file).is_file():
                result["status"] = "CONFIRMATION_REQUIRED"
            elif result["missing"]:
                result["status"] = "FAIL"
            else:
                cmd = options + ["uname -a; command -v gmx || true"]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                result["network_action"] = "ssh_preflight"
                result["returncode"] = proc.returncode
                result["stdout"] = proc.stdout[-4000:]
                result["stderr"] = proc.stderr[-4000:]
                result["status"] = "PASS" if proc.returncode == 0 else "REMOTE_PREFLIGHT_FAILED"
        elif result["missing"]:
            result["status"] = "REMOTE_CONFIG_INCOMPLETE"
        else:
            result["status"] = "PLAN_ONLY"

    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] in ("PASS", "PLAN_ONLY", "USER_DECISION_REQUIRED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
