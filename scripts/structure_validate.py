#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, load_data, sha256

SUPPORTED_FORMATS = {"xyz", "mol", "sdf", "pdb"}


def atom_count(path: Path) -> int:
    suffix = path.suffix.lower().lstrip(".")
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if suffix == "xyz":
        return int(text[0].strip())
    if suffix == "pdb":
        return sum(1 for line in text if line.startswith(("ATOM", "HETATM")))
    if suffix in ("mol", "sdf"):
        for line in text[:12]:
            if "V3000" in line:
                raise ValueError("V3000 is not accepted by this lightweight gate; use V2000 or an audited converter")
            if "V2000" in line:
                return int(line[:3])
        raise ValueError("MOL/SDF V2000 counts line not found")
    raise ValueError("supported formats: xyz, mol, pdb, sdf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--metadata", required=True, help="JSON/YAML with expected atom_count, formula, charge and source")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = Path(args.structure)
    meta = load_data(args.metadata) or {}
    fmt = p.suffix.lower().lstrip(".")
    result = {
        "source": str(p),
        "source_sha256": sha256(p),
        "format": fmt,
        "checks": {},
        "status": "PASS",
    }
    try:
        actual = atom_count(p)
        result["checks"]["atom_count"] = {
            "expected": meta.get("atom_count"),
            "actual": actual,
            "pass": meta.get("atom_count") in (None, actual),
        }
    except (OSError, ValueError) as exc:
        result["status"] = "FAIL"
        result["error"] = str(exc)
        dump_json(result, args.out)
        return 2
    result["checks"]["format"] = {
        "supported": fmt in SUPPORTED_FORMATS,
        "manual_review": fmt in ("xyz", "pdb"),
    }
    result["checks"]["source_recorded"] = bool(
        meta.get("source") or meta.get("source_doi") or meta.get("source_hash")
    )
    for key in ("formula", "formal_charge", "multiplicity", "connectivity"):
        if key in meta:
            result["checks"][key] = {
                "expected": meta[key],
                "status": "REQUIRES_STRUCTURAL_REVIEW",
            }
    if (
        fmt not in SUPPORTED_FORMATS
        or not result["checks"]["atom_count"]["pass"]
        or not result["checks"]["source_recorded"]
    ):
        result["status"] = "FAIL"
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
