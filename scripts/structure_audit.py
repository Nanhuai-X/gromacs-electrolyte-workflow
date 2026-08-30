#!/usr/bin/env python3
"""Read-only structure audit with an ASE path and a minimal XYZ fallback."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


def xyz_fallback(path: Path) -> Dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: List[str] = []
    if not lines:
        return {"status": "FAIL", "errors": ["empty structure"]}
    try:
        count = int(lines[0].strip())
    except ValueError:
        return {"status": "ASE_REQUIRED", "errors": ["non-XYZ input and ASE is unavailable"]}
    atoms = []
    for line_number, line in enumerate(lines[2 : 2 + count], start=3):
        fields = line.split()
        if len(fields) < 4:
            errors.append(f"line {line_number}: expected element x y z")
            continue
        try:
            coords = [float(value) for value in fields[1:4]]
        except ValueError:
            errors.append(f"line {line_number}: non-numeric coordinate")
            continue
        if not all(math.isfinite(value) for value in coords):
            errors.append(f"line {line_number}: non-finite coordinate")
        atoms.append({"element": fields[0], "position_angstrom": coords})
    if len(atoms) != count:
        errors.append(f"expected {count} atoms but parsed {len(atoms)}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "parser": "minimal_xyz",
        "atom_count": len(atoms),
        "elements": dict(Counter(atom["element"] for atom in atoms)),
        "periodic": False,
        "cell": None,
        "atoms": atoms,
        "errors": errors,
        "warnings": ["XYZ fallback cannot audit cell, occupancy, disorder, or symmetry"],
    }


def ase_audit(path: Path, short_contact: float) -> Dict[str, Any]:
    try:
        from ase.io import read  # type: ignore
    except ImportError:
        if path.suffix.lower() in (".xyz", ".extxyz"):
            return xyz_fallback(path)
        return {
            "status": "ASE_REQUIRED",
            "parser": None,
            "errors": ["ASE is required for CIF/POSCAR/PDB/GEN input"],
            "warnings": [],
        }

    try:
        atoms = read(path)
    except Exception as exc:  # parser errors are user-facing audit evidence
        return {"status": "FAIL", "parser": "ASE", "errors": [f"ASE read failed: {exc}"]}

    positions = atoms.get_positions()
    finite = bool(positions.size) and bool(__import__("numpy").isfinite(positions).all())
    warnings: List[str] = []
    errors: List[str] = []
    if not finite:
        errors.append("non-finite Cartesian coordinate")
    minimum_distance = None
    if len(atoms) > 1:
        try:
            import numpy as np  # type: ignore

            distances = atoms.get_all_distances(mic=bool(atoms.pbc.any()))
            distances = distances[np.triu_indices(len(atoms), k=1)]
            if len(distances):
                minimum_distance = float(distances.min())
                if minimum_distance < short_contact:
                    errors.append(f"short contact below audit threshold {short_contact} A")
        except Exception as exc:
            warnings.append(f"minimum-distance audit unavailable: {exc}")

    formula = atoms.get_chemical_formula(mode="hill")
    result: Dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "parser": "ASE",
        "atom_count": len(atoms),
        "formula": formula,
        "elements": dict(Counter(atoms.get_chemical_symbols())),
        "cell_angstrom": atoms.cell.tolist(),
        "cell_volume_angstrom3": float(atoms.get_volume()),
        "pbc": [bool(value) for value in atoms.pbc],
        "positions_angstrom": positions.tolist(),
        "minimum_distance_angstrom": minimum_distance,
        "finite_coordinates": finite,
        "errors": errors,
        "warnings": warnings + [
            "ASE audit does not establish CIF occupancy/disorder/symmetry equivalence; use pymatgen/spglib when required"
        ],
        "raw_structure_unchanged": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("structure", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--short-contact-angstrom", type=float, default=0.8)
    args = parser.parse_args()
    record = ase_audit(args.structure, args.short_contact_angstrom)
    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if record["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
