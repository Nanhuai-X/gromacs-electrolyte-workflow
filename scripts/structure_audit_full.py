#!/usr/bin/env python3
"""Optional pymatgen/spglib-backed periodic structure audit.

No structure is repaired or rewritten. Missing scientific-parser dependencies
are reported as NOT_VALIDATED rather than silently downgraded to PASS.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def audit_structure(path: Path, symprecs: List[float], short_contact: float) -> Dict[str, Any]:
    try:
        from pymatgen.core import Structure  # type: ignore
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer  # type: ignore
    except ImportError as exc:
        return {
            "status": "NOT_VALIDATED",
            "complete_audit": False,
            "missing_dependency": "pymatgen",
            "error": str(exc),
            "raw_structure_unchanged": True,
        }

    try:
        structure = Structure.from_file(str(path))
    except Exception as exc:
        return {"status": "FAIL", "complete_audit": False, "error": str(exc), "raw_structure_unchanged": True}

    errors: List[str] = []
    warnings: List[str] = []
    occupancies = []
    for index, site in enumerate(structure.sites, start=1):
        occupancy = float(site.species.num_atoms)
        occupancies.append(occupancy)
        if not math.isfinite(occupancy) or occupancy <= 0 or occupancy > 1.000001:
            errors.append(f"site {index}: invalid occupancy {occupancy}")
        if len(site.species) > 1 or abs(occupancy - 1.0) > 1e-6:
            warnings.append(f"site {index}: partial occupancy or disorder requires scientific review")
        if not all(math.isfinite(float(value)) for value in site.frac_coords):
            errors.append(f"site {index}: non-finite fractional coordinate")

    minimum_distance = None
    if len(structure) > 1:
        distances = []
        for i in range(len(structure)):
            for j in range(i + 1, len(structure)):
                distance = float(structure.get_distance(i, j))
                if math.isfinite(distance):
                    distances.append(distance)
        if distances:
            minimum_distance = min(distances)
            if minimum_distance < short_contact:
                errors.append(f"short contact below audit threshold {short_contact} A")

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    declared_match = re.search(
        r"(?im)^\s*_(?:symmetry_space_group_name_H-M|space_group_name_H-M_alt)\s+['\"]?(.+?)['\"]?\s*$",
        raw_text,
    )
    symmetry = []
    for symprec in symprecs:
        try:
            analyzer = SpacegroupAnalyzer(structure, symprec=symprec)
            symmetry.append(
                {
                    "symprec": symprec,
                    "symbol": analyzer.get_space_group_symbol(),
                    "number": analyzer.get_space_group_number(),
                }
            )
        except Exception as exc:
            symmetry.append({"symprec": symprec, "status": "UNAVAILABLE", "error": str(exc)})

    result = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "complete_audit": True,
        "parser": "pymatgen",
        "atom_count": len(structure),
        "formula": structure.composition.formula,
        "reduced_formula": structure.composition.reduced_formula,
        "elements": dict(Counter(str(site.specie) for site in structure.sites)),
        "cell_angstrom": structure.lattice.matrix.tolist(),
        "cell_volume_angstrom3": float(structure.volume),
        "fractional_coordinates": structure.frac_coords.tolist(),
        "cartesian_coordinates": structure.cart_coords.tolist(),
        "occupancies": occupancies,
        "declared_symmetry": declared_match.group(1).strip() if declared_match else None,
        "detected_symmetry": symmetry,
        "minimum_distance_angstrom": minimum_distance,
        "errors": errors,
        "warnings": warnings,
        "raw_structure_unchanged": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("structure", type=Path)
    parser.add_argument("--symprec", type=float, action="append")
    parser.add_argument("--short-contact-angstrom", type=float, default=0.8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_structure(args.structure, args.symprec or [1e-5, 1e-3, 1e-2], args.short_contact_angstrom)
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
