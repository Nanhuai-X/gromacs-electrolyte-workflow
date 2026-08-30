#!/usr/bin/env python3
"""Read-only local environment audit for the CP2K materials Skill."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


EXECUTABLES = [
    "cp2k",
    "cp2k.psmp",
    "cp2k.popt",
    "cp2k.ssmp",
    "cp2k.sopt",
    "mpirun",
    "mpiexec",
    "sbatch",
    "squeue",
    "sacct",
    "qsub",
    "qstat",
    "bsub",
    "bjobs",
    "nvidia-smi",
]


def run_capture(command: list[str], timeout: float = 10.0) -> Optional[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or "") + (result.stderr or "")
    return text.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    executables: Dict[str, Any] = {}
    for name in EXECUTABLES:
        found = shutil.which(name)
        executables[name] = {"path": found, "available": found is not None}

    memory: Dict[str, Any] = {"status": "NOT_CHECKED"}
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        memory = {
            "status": "AVAILABLE",
            "total_bytes": vm.total,
            "available_bytes": vm.available,
        }
    except ImportError:
        memory = {"status": "psutil_not_installed"}

    gpu = {"status": "NOT_AVAILABLE", "devices": []}
    if executables["nvidia-smi"]["available"]:
        output = run_capture(
            [
                executables["nvidia-smi"]["path"],
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ]
        )
        if output:
            gpu = {
                "status": "AVAILABLE",
                "devices": [line.strip() for line in output.splitlines() if line.strip()],
            }

    record: Dict[str, Any] = {
        "schema_version": "1.0",
        "audit_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "memory": memory,
        "gpu": gpu,
        "executables": executables,
        "read_only": True,
    }
    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
