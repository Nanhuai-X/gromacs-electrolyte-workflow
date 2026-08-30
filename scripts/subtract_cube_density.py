#!/usr/bin/env python3
"""Audit and subtract CP2K Gaussian cube density files on a common grid."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


Number3 = Tuple[float, float, float]


def _float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def _close(left: Sequence[float], right: Sequence[float], tolerance: float) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= tolerance for a, b in zip(left, right))


def _atom_matches(left: str, right: str, tolerance: float) -> bool:
    """Compare atom number/charge/coordinates without depending on formatting."""

    left_fields = left.split()
    right_fields = right.split()
    if len(left_fields) != len(right_fields) or not left_fields:
        return False
    if left_fields[0] != right_fields[0]:
        return False
    for left_value, right_value in zip(left_fields[1:], right_fields[1:]):
        try:
            if abs(_float(left_value) - _float(right_value)) > tolerance:
                return False
        except ValueError:
            if left_value != right_value:
                return False
    return True


@dataclass(frozen=True)
class CubeData:
    path: Path
    header: Tuple[str, ...]
    atom_count: int
    origin: Number3
    grid_counts: Tuple[int, int, int]
    grid_signs: Tuple[int, int, int]
    grid_vectors: Tuple[Number3, Number3, Number3]
    atom_lines: Tuple[str, ...]
    values: Tuple[float, ...]


def read_cube(path: Path) -> CubeData:
    """Read one scalar cube and reject incomplete or non-finite data."""

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 6:
        raise ValueError(f"cube has fewer than six header lines: {path}")
    try:
        atom_fields = lines[2].split()
        atom_count_raw = int(atom_fields[0])
        atom_count = abs(atom_count_raw)
        origin = tuple(_float(item) for item in atom_fields[1:4])
        if len(origin) != 3:
            raise ValueError
        grid_counts: List[int] = []
        grid_signs: List[int] = []
        grid_vectors: List[Number3] = []
        for line in lines[3:6]:
            fields = line.split()
            raw_count = int(fields[0])
            grid_counts.append(abs(raw_count))
            grid_signs.append(1 if raw_count >= 0 else -1)
            grid_vectors.append(tuple(_float(item) for item in fields[1:4]))
        if len(origin) != 3 or any(len(vector) != 3 for vector in grid_vectors):
            raise ValueError
    except (IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid cube header: {path}") from exc
    if atom_count == 0 or any(count <= 0 for count in grid_counts):
        raise ValueError(f"cube has invalid atom count or grid: {path}")

    atom_start = 6
    atom_end = atom_start + atom_count
    if len(lines) < atom_end:
        raise ValueError(f"cube atom block is incomplete: {path}")
    atom_lines = tuple(lines[atom_start:atom_end])
    for line in atom_lines:
        fields = line.split()
        if len(fields) < 5:
            raise ValueError(f"invalid cube atom line: {path}")
        try:
            [_float(item) for item in fields[1:5]]
        except ValueError as exc:
            raise ValueError(f"invalid cube atom coordinates: {path}") from exc

    values: List[float] = []
    for line in lines[atom_end:]:
        for token in line.split():
            try:
                value = _float(token)
            except ValueError as exc:
                raise ValueError(f"invalid cube value in {path}: {token}") from exc
            if not math.isfinite(value):
                raise ValueError(f"non-finite cube value in {path}")
            values.append(value)
    expected = grid_counts[0] * grid_counts[1] * grid_counts[2]
    if len(values) != expected:
        raise ValueError(f"cube value count {len(values)} does not match grid size {expected}: {path}")
    return CubeData(
        path=path,
        header=tuple(lines[:atom_end]),
        atom_count=atom_count,
        origin=(origin[0], origin[1], origin[2]),
        grid_counts=(grid_counts[0], grid_counts[1], grid_counts[2]),
        grid_signs=(grid_signs[0], grid_signs[1], grid_signs[2]),
        grid_vectors=(
            (grid_vectors[0][0], grid_vectors[0][1], grid_vectors[0][2]),
            (grid_vectors[1][0], grid_vectors[1][1], grid_vectors[1][2]),
            (grid_vectors[2][0], grid_vectors[2][1], grid_vectors[2][2]),
        ),
        atom_lines=atom_lines,
        values=tuple(values),
    )


def audit_cubes(cubes: Sequence[CubeData], tolerance: float = 1.0e-8) -> Dict[str, Any]:
    """Compare metadata and value lengths for two or more cubes."""

    if len(cubes) < 2:
        raise ValueError("at least two cubes are required")
    reference = cubes[0]
    mismatches: List[str] = []
    for candidate in cubes[1:]:
        label = candidate.path.name
        if candidate.atom_count != reference.atom_count:
            mismatches.append(f"{label}: atom count differs")
        if not _close(candidate.origin, reference.origin, tolerance):
            mismatches.append(f"{label}: origin differs")
        if candidate.grid_counts != reference.grid_counts:
            mismatches.append(f"{label}: grid dimensions differ")
        if candidate.grid_signs != reference.grid_signs:
            mismatches.append(f"{label}: grid unit convention differs")
        for index, (left, right) in enumerate(zip(candidate.grid_vectors, reference.grid_vectors), start=1):
            if not _close(left, right, tolerance):
                mismatches.append(f"{label}: grid vector {index} differs")
        if len(candidate.atom_lines) != len(reference.atom_lines):
            mismatches.append(f"{label}: atom block length differs")
        else:
            for index, (left, right) in enumerate(zip(candidate.atom_lines, reference.atom_lines), start=1):
                if not _atom_matches(left, right, tolerance):
                    mismatches.append(f"{label}: atom line {index} differs")
                    break
        if len(candidate.values) != len(reference.values):
            mismatches.append(f"{label}: value count differs")
    return {
        "schema_version": "1.0",
        "status": "PASS" if not mismatches else "FAIL",
        "cube_count": len(cubes),
        "reference": str(reference.path),
        "grid_counts": reference.grid_counts,
        "grid_signs": reference.grid_signs,
        "value_count": len(reference.values),
        "tolerance": tolerance,
        "mismatches": mismatches,
    }


def subtract_cubes(complex_cube: CubeData, host_cube: CubeData, adsorbate_cube: CubeData, tolerance: float = 1.0e-8) -> Tuple[CubeData, Dict[str, Any]]:
    """Return a new in-memory cube for rho_complex-rho_host-rho_adsorbate."""

    audit = audit_cubes((complex_cube, host_cube, adsorbate_cube), tolerance)
    if audit["status"] != "PASS":
        raise ValueError("cube metadata mismatch: " + "; ".join(audit["mismatches"]))
    values = tuple(a - b - c for a, b, c in zip(complex_cube.values, host_cube.values, adsorbate_cube.values))
    result = CubeData(
        path=Path("difference.cube"),
        header=complex_cube.header,
        atom_count=complex_cube.atom_count,
        origin=complex_cube.origin,
        grid_counts=complex_cube.grid_counts,
        grid_signs=complex_cube.grid_signs,
        grid_vectors=complex_cube.grid_vectors,
        atom_lines=complex_cube.atom_lines,
        values=values,
    )
    return result, audit


def write_cube(cube: CubeData, output: Path) -> None:
    """Write a scalar cube with six scientific values per data line."""

    lines = list(cube.header)
    for start in range(0, len(cube.values), 6):
        lines.append(" ".join(f"{value: .8E}" for value in cube.values[start : start + 6]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complex", dest="complex_path", type=Path, required=True)
    parser.add_argument("--host", dest="host_path", type=Path, required=True)
    parser.add_argument("--adsorbate", dest="adsorbate_path", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--tolerance", type=float, default=1.0e-8)
    args = parser.parse_args()
    try:
        cubes = tuple(read_cube(path) for path in (args.complex_path, args.host_path, args.adsorbate_path))
        difference, audit = subtract_cubes(*cubes, tolerance=args.tolerance)
        if args.output:
            write_cube(difference, args.output)
        result: Dict[str, Any] = {
            **audit,
            "inputs": [str(path) for path in (args.complex_path, args.host_path, args.adsorbate_path)],
            "output": str(args.output) if args.output else None,
            "formula": "rho_complex - rho_host_same_geometry - rho_adsorbate_same_cell",
        }
    except (OSError, ValueError) as exc:
        result = {"schema_version": "1.0", "status": "FAIL", "error": str(exc)}
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.audit_output:
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        args.audit_output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
