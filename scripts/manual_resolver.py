#!/usr/bin/env python3
"""Resolve a declared CP2K version to its official manual branch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--registry", type=Path, default=skill_root / "assets" / "template_registry.json")
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.cwd() / "manual_cache",
        help="runtime cache directory (default: ./manual_cache in the caller's working directory)",
    )
    parser.add_argument("--sections", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    registry = load_json(args.registry)
    versions = registry.get("versions", {})
    requested = args.version
    key = requested if requested in versions else next(
        (candidate for candidate in versions if candidate.startswith(requested)), None
    )
    if not key:
        record = {
            "status": "UNSUPPORTED_VERSION",
            "requested_version": requested,
            "registry": str(args.registry),
        }
        code = 2
    else:
        version_record = versions[key]
        version_cache = args.cache_root / key
        manifest = version_cache / "manual_manifest.yaml"
        html = version_cache / "CP2K_INPUT.html"
        record = {
            "status": "RESOLVED",
            "cp2k_version": key,
            "manual_url": version_record.get("manual_url"),
            "manual_git_revision": version_record.get("manual_git_revision"),
            "manual_branch": version_record.get("manual_url", "").rstrip("/").split("/")[-2]
            if version_record.get("manual_url")
            else None,
            "cache_root": str(version_cache),
            "manual_manifest": str(manifest),
            "manual_cached": manifest.exists() and html.exists(),
            "exact_manual_available": manifest.exists() and html.exists(),
            "sections_requested": [item for item in args.sections.split(",") if item],
            "template_records": registry.get("templates", {}).get(key, {}),
        }
        code = 0 if record["exact_manual_available"] else 3
        if not record["exact_manual_available"]:
            record["status"] = "MANUAL_REQUIRED"
            record["instruction"] = "Retrieve and hash the official branch before formal submission."

    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
