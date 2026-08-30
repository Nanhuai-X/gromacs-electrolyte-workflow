#!/usr/bin/env python3
"""Create an explicit, hash-linked calculation.yaml manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import socket
from pathlib import Path
from typing import Any, Dict

from task_router import route_task


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_choices(value: str) -> Dict[str, Any]:
    """Read a JSON object from a literal string or a file path."""

    candidate = Path(value)
    if candidate.is_file():
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("choices JSON must contain an object")
    return payload


def build_manifest(structure: Path, task: str, run_target: str, choices: Dict[str, Any]) -> Dict[str, Any]:
    route = route_task(task)
    decision_status = "SCIENTIFIC_DECISION_REQUIRED" if route["scientific_gates"] else "READY_FOR_PARAMETER_PLAN"
    return {
        "schema_version": "1.0",
        "job_id": None,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "run_target": run_target,
        "task": task,
        "route": route,
        "structure": {
            "source": str(structure.resolve()),
            "sha256": file_sha256(structure),
            "raw_structure_immutable": True,
        },
        "scientific_model": choices,
        "parameter_status": "USER_CONFIRMATION_REQUIRED",
        "decision_status": decision_status,
        "cp2k": {
            "version": None,
            "executable": None,
            "manual_manifest": None,
            "input_sha256": None,
            "output_sha256": None,
        },
        "scheduler": {"name": None, "job_id": None},
        "provenance": {"commands": [], "restart_files": [], "repairs": []},
        "outputs": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-target", choices=["LOCAL", "REMOTE_SERVER"], required=True)
    parser.add_argument("--choices-json", default="{}")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.structure.is_file():
        raise SystemExit(f"structure not found: {args.structure}")
    output = args.output_dir / "calculation.yaml"
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {output}; use --force explicitly")
    try:
        choices = read_choices(args.choices_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"choices must be a JSON object or a readable JSON file: {exc}") from exc
    manifest = build_manifest(args.structure, args.task, args.run_target, choices)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
