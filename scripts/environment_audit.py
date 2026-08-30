#!/usr/bin/env python3
from __future__ import annotations
import argparse
import platform
import shutil
import subprocess
from pathlib import Path
from common import dump_json

TOOLS = {
    "gmx": ["--version"],
    "packmol": ["-h"],
    "python3": ["--version"],
    "git": ["--version"],
    "cmake": ["--version"],
    "gcc": ["--version"],
    "nvidia-smi": ["--query-gpu=name,driver_version", "--format=csv,noheader"],
    "nvcc": ["--version"],
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = {"platform": platform.platform(), "python": platform.python_version(), "tools": {}}
    for name, probe in TOOLS.items():
        path = shutil.which(name)
        row = {"path": path, "available": bool(path)}
        if path:
            try:
                proc = subprocess.run([path, *probe], text=True, capture_output=True, check=False, timeout=20)
                row.update({"returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]})
            except (OSError, subprocess.TimeoutExpired) as exc:
                row.update({"returncode": None, "error": str(exc)})
        result["tools"][name] = row
    dump_json(result, args.out)
    print("read-only audit written:", args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
