#!/usr/bin/env python3
"""Parse common CP2K output evidence; never equate file existence with PASS."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION_RE = re.compile(r"CP2K\s+version\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)", re.I)
# CP2K has emitted both ``[a.u.] : value`` (older releases) and
# ``[hartree] value`` (2026.x) forms.  Keep the unit/colon portion
# permissive while anchoring on the FORCE_EVAL total-energy record.
ENERGY_RE = re.compile(
    r"ENERGY\|\s+Total\s+FORCE_EVAL.*?energy\s+\[(?:hartree|a\.u\.)\]\s*:?\s*"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    re.I,
)
SCF_ITER_RE = re.compile(r"SCF\s+ITERATION\s+([0-9]+)|OT\s+iteration\s+([0-9]+)", re.I)
SCF_RESIDUAL_RE = re.compile(r"(?:EPS_SCF|residual|RMS)\D{0,20}([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)", re.I)


def parse_output(text: str, return_code: Optional[int] = None) -> Dict[str, Any]:
    energies = [float(match.group(1)) for match in ENERGY_RE.finditer(text)]
    cycles = []
    for match in SCF_ITER_RE.finditer(text):
        cycles.append(int(match.group(1) or match.group(2)))
    residuals = [float(match.group(1)) for match in SCF_RESIDUAL_RE.finditer(text)]
    errors = [line.strip() for line in text.splitlines() if re.search(r"\b(ERROR|FATAL|ABORT)\b", line, re.I)]
    warnings = [line.strip() for line in text.splitlines() if re.search(r"\bWARNING\b", line, re.I)]
    normal = bool(re.search(r"PROGRAM\s+STOPPED\s+IN|CP2K\|\s+Normal\s+termination", text, re.I))
    scf_converged = bool(re.search(r"SCF\s+run\s+converged|converged\s+SCF", text, re.I))
    geometry_completed = bool(re.search(r"GEOMETRY\s+OPTIMIZATION\s+COMPLETED", text, re.I))
    version_match = VERSION_RE.search(text)
    result = {
        "schema_version": "1.0",
        "cp2k_version": version_match.group(1) if version_match else None,
        "return_code": return_code,
        "normal_termination": normal,
        "scf_converged": scf_converged,
        "scf_cycles": cycles,
        "scf_cycle_count": max(cycles) if cycles else None,
        "scf_residuals": residuals,
        "total_energy_au": energies[-1] if energies else None,
        "energy_history_au": energies,
        "geometry_completed": geometry_completed,
        "errors": errors,
        "warnings": warnings,
        "finite_energy": bool(energies) and all(math.isfinite(value) for value in energies),
    }
    result["status"] = (
        "PASS"
        if normal and scf_converged and not errors and (return_code in (None, 0))
        else "FAIL"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--return-code", type=int)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = parse_output(args.output.read_text(encoding="utf-8", errors="replace"), args.return_code)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
