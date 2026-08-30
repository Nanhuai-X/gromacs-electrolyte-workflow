#!/usr/bin/env python3
"""Run one explicitly approved local CP2K input and parse its output."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from cp2k_output_parser import parse_output
from cp2k_version_detect import probe


def run_local(
    executable: str,
    input_path: Path,
    output_path: Path,
    expected_version: Optional[str] = None,
    workdir: Optional[Path] = None,
    timeout: Optional[float] = None,
    allow_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Run a single local job; never retries or changes its input."""

    if not allow_run:
        raise ValueError("explicit local execution approval is required; pass --allow-run")
    if not input_path.is_file():
        raise ValueError(f"input not found: {input_path}")
    if output_path.resolve() == input_path.resolve():
        raise ValueError("output must not overwrite the input")
    if output_path.exists() and not force:
        raise ValueError(f"refusing to overwrite existing output: {output_path}; use --force")

    version_probe = probe(executable)
    if version_probe.get("status") != "FOUND":
        return {"status": "VERSION_UNRESOLVED", "version_probe": version_probe}
    if expected_version and version_probe.get("version") != expected_version:
        return {
            "status": "VERSION_MISMATCH",
            "expected_version": expected_version,
            "version_probe": version_probe,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    active_workdir = (workdir or input_path.parent).resolve()
    if not active_workdir.is_dir():
        raise ValueError(f"working directory not found: {active_workdir}")
    command = [executable, "-i", str(input_path.resolve()), "-o", str(output_path.resolve())]
    try:
        completed = subprocess.run(
            command,
            cwd=active_workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "TIMEOUT",
            "command": command,
            "workdir": str(active_workdir),
            "version_probe": version_probe,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }
    if not output_path.is_file():
        return {
            "status": "OUTPUT_MISSING",
            "return_code": completed.returncode,
            "command": command,
            "workdir": str(active_workdir),
            "version_probe": version_probe,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }

    output_text = output_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_output(output_text, completed.returncode)
    return {
        "status": "PASS" if parsed["status"] == "PASS" else "FAIL",
        "return_code": completed.returncode,
        "command": command,
        "workdir": str(active_workdir),
        "version_probe": version_probe,
        "output": str(output_path.resolve()),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "parsed_output": parsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-version")
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--allow-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        result = run_local(
            args.executable,
            args.input,
            args.output,
            args.expected_version,
            args.workdir,
            args.timeout,
            args.allow_run,
            args.force,
        )
    except (OSError, ValueError) as exc:
        result = {"status": "CONFIGURATION_ERROR", "error": str(exc)}
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    print(payload)
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
