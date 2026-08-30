#!/usr/bin/env python3
"""Create a JSON-as-YAML provenance manifest for a calculation."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def sha256(path: Optional[Path]) -> Optional[str]:
    if not path or not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version_probe(executable: Optional[str]) -> Dict[str, Any]:
    if not executable:
        return {"path": None, "version_output": None}
    found = shutil.which(executable) or executable
    try:
        result = subprocess.run(
            [found, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = ((result.stdout or "") + (result.stderr or ""))[-4000:]
        return {"path": found, "returncode": result.returncode, "version_output": text}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"path": found, "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--structure", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--cp2k-executable")
    parser.add_argument("--extra", help="JSON object merged under extra")
    parser.add_argument("--command", action="append", default=[])
    args = parser.parse_args()

    extra = json.loads(args.extra) if args.extra else {}
    record: Dict[str, Any] = {
        "schema_version": "1.0",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
        "structure": {"path": str(args.structure) if args.structure else None, "sha256": sha256(args.structure)},
        "input": {"path": str(args.input) if args.input else None, "sha256": sha256(args.input)},
        "cp2k": version_probe(args.cp2k_executable),
        "command": args.command,
        "extra": extra,
        "secret_policy": "No credentials are collected by this script",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML 1.2 and avoids an undeclared PyYAML dependency.
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
