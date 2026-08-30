#!/usr/bin/env python3
"""Discover a CP2K executable and parse its reported version."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


CANDIDATES = ["cp2k", "cp2k.psmp", "cp2k.popt", "cp2k.ssmp", "cp2k.sopt"]
VERSION_RE = re.compile(r"CP2K\s+version\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)", re.I)


def probe(executable: str) -> Dict[str, Any]:
    attempts = []
    for flag in ("--version", "-v"):
        try:
            result = subprocess.run(
                [executable, flag],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            text = (result.stdout or "") + (result.stderr or "")
            attempts.append({"flag": flag, "returncode": result.returncode, "output": text[-4000:]})
            match = VERSION_RE.search(text)
            if match:
                return {
                    "status": "FOUND",
                    "executable": executable,
                    "version": match.group(1),
                    "probe": attempts,
                }
        except (OSError, subprocess.TimeoutExpired) as exc:
            attempts.append({"flag": flag, "error": type(exc).__name__})
    return {"status": "VERSION_UNRESOLVED", "executable": executable, "probe": attempts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    executable = args.executable
    if executable:
        executable = str(Path(executable).expanduser())
    else:
        executable = next((shutil.which(name) for name in CANDIDATES if shutil.which(name)), None)
    record = {"status": "EXECUTABLE_NOT_FOUND"} if not executable else probe(executable)
    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if record["status"] == "FOUND" else 2


if __name__ == "__main__":
    raise SystemExit(main())
