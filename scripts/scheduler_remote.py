#!/usr/bin/env python3
"""Build bounded remote scheduler commands; submission requires explicit approval."""

from __future__ import annotations

import argparse
import json
import shlex
from typing import Any, Dict


def build_scheduler_command(
    scheduler: str, action: str, job_script: str = "", job_id: str = "", allow_submit: bool = False
) -> Dict[str, Any]:
    scheduler = scheduler.lower()
    if scheduler not in {"slurm", "pbs", "lsf"}:
        raise ValueError("scheduler must be slurm, pbs, or lsf")
    if action == "submit":
        if not allow_submit:
            return {"status": "SUBMISSION_CONFIRMATION_REQUIRED", "command": None}
        if not job_script:
            raise ValueError("job_script is required for submission")
        executable = {"slurm": "sbatch", "pbs": "qsub", "lsf": "bsub"}[scheduler]
        command = f"{executable} {shlex.quote(job_script)}"
    elif action == "status":
        if not job_id:
            raise ValueError("job_id is required for status")
        if scheduler == "slurm":
            command = f"squeue -j {shlex.quote(job_id)} -h -o '%T %M %R'; sacct -j {shlex.quote(job_id)} --format=JobID,State,ExitCode -n"
        elif scheduler == "pbs":
            command = f"qstat {shlex.quote(job_id)}"
        else:
            command = f"bjobs -l {shlex.quote(job_id)}"
    else:
        raise ValueError("action must be submit or status")
    return {
        "status": "COMMAND_READY",
        "scheduler": scheduler,
        "action": action,
        "command": command,
        "external_mutation": action == "submit",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheduler", required=True)
    parser.add_argument("--action", choices=["submit", "status"], required=True)
    parser.add_argument("--job-script", default="")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--allow-submit", action="store_true")
    args = parser.parse_args()
    try:
        result = build_scheduler_command(args.scheduler, args.action, args.job_script, args.job_id, args.allow_submit)
    except ValueError as exc:
        result = {"status": "SCHEDULER_CONFIGURATION_ERROR", "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"COMMAND_READY", "SUBMISSION_CONFIRMATION_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
