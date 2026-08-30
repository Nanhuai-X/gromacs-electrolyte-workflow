#!/usr/bin/env python3
"""Detect available schedulers without submitting a job."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


SCHEDULERS = {
    "slurm": ["sbatch", "squeue", "sacct"],
    "pbs": ["qsub", "qstat"],
    "lsf": ["bsub", "bjobs"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    available = {
        scheduler: {
            "commands": {name: shutil.which(name) for name in commands},
            "complete": all(shutil.which(name) for name in commands),
        }
        for scheduler, commands in SCHEDULERS.items()
    }
    selected = next((name for name in ("slurm", "pbs", "lsf") if available[name]["complete"]), None)
    record = {"schema_version": "1.0", "selected": selected, "available": available}
    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
