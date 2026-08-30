#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import dump_json, sha256

SUPPORTED = {"xyz", "mol", "sdf", "pdb"}


def _float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def parse_xyz(lines: list[str]) -> tuple[list[str], bool]:
    count = int(lines[0].strip())
    atoms = []
    for line in lines[2:2 + count]:
        parts = line.split()
        if len(parts) < 4:
            raise ValueError("invalid XYZ atom line")
        atoms.append(f"{parts[0]} {_float(parts[1]):.10f} {_float(parts[2]):.10f} {_float(parts[3]):.10f}")
    if len(atoms) != count:
        raise ValueError("XYZ atom count does not match coordinate records")
    return atoms, False


def counts_line_index(lines: list[str]) -> int:
    for index, line in enumerate(lines[:12]):
        if "V2000" in line or "V3000" in line:
            return index
    return 3 if len(lines) > 3 else -1


def parse_mol_sdf(lines: list[str]) -> tuple[list[str], bool]:
    index = counts_line_index(lines)
    if index < 0 or "V3000" in lines[index]:
        raise ValueError("only MOL/SDF V2000 atom blocks are supported")
    try:
        count = int(lines[index][:3])
    except ValueError as exc:
        raise ValueError("invalid MOL/SDF counts line") from exc
    atoms = []
    start = index + 1
    for line in lines[start:start + count]:
        if len(line) < 34:
            raise ValueError("invalid MOL/SDF atom line")
        symbol = line[31:34].strip() or line.split()[3]
        x = _float(line[0:10])
        y = _float(line[10:20])
        z = _float(line[20:30])
        atoms.append(f"{symbol} {x:.10f} {y:.10f} {z:.10f}")
    if len(atoms) != count:
        raise ValueError("MOL/SDF atom count does not match coordinate records")
    return atoms, True


def parse_pdb(lines: list[str]) -> tuple[list[str], bool]:
    atoms = []
    for line in lines:
        if not line.startswith(("ATOM", "HETATM")):
            continue
        if len(line) < 54:
            raise ValueError("invalid PDB coordinate line")
        symbol = line[76:78].strip()
        if not symbol:
            name = re.sub(r"[^A-Za-z]", "", line[12:16]).strip()
            symbol = (name[:2] if len(name) >= 2 and name[:2].capitalize() in {"Cl", "Br"} else name[:1])
        if not symbol:
            raise ValueError("PDB atom element is missing")
        atoms.append(
            f"{symbol} {_float(line[30:38]):.10f} {_float(line[38:46]):.10f} {_float(line[46:54]):.10f}"
        )
    if not atoms:
        raise ValueError("PDB contains no ATOM/HETATM records")
    return atoms, False


def extract_structure(path: Path) -> dict:
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in SUPPORTED:
        raise ValueError("supported formats: xyz, mol, sdf, pdb")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if suffix == "xyz":
        atoms, connectivity = parse_xyz(lines)
    elif suffix in ("mol", "sdf"):
        atoms, connectivity = parse_mol_sdf(lines)
    else:
        atoms, connectivity = parse_pdb(lines)
    return {
        "status": "PASS",
        "source": str(path),
        "source_sha256": sha256(path),
        "format": suffix,
        "atom_count": len(atoms),
        "atom_order_preserved": True,
        "geometry": "\n".join(atoms),
        "connectivity_in_file": connectivity,
        "connectivity_status": "PRESENT" if connectivity else "REQUIRES_REVIEW",
        "requires_explicit_structure_confirmation": True,
        "gaussian_workflow_route": (
            "compatible finite-molecule workflow prepare -> confirm-structure -> "
            "Gaussian/formchk -> RESP/RESP2"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--confirmed-sha256")
    args = ap.parse_args()
    path = Path(args.input)
    try:
        result = extract_structure(path)
    except (OSError, ValueError) as exc:
        result = {"status": "FAIL", "source": str(path), "error": str(exc)}
        dump_json(result, args.out)
        print("FAIL")
        return 2
    if args.confirmed_sha256:
        result["structure_confirmed"] = args.confirmed_sha256 == result["source_sha256"]
        if not result["structure_confirmed"]:
            result["status"] = "FAIL"
            result["error"] = "confirmation hash does not match source"
    else:
        result["structure_confirmed"] = False
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
