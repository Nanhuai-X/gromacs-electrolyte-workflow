#!/usr/bin/env python3
"""Plan separate periodic charge calculations and their validation gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


SUPPORTED_METHODS = {"hirshfeld", "mulliken", "lowdin", "periodic_resp", "repeat_like"}


def build_charge_plan(methods: Iterable[str]) -> Dict[str, Any]:
    normalized = [method.strip().lower() for method in methods]
    invalid = [method for method in normalized if method not in SUPPORTED_METHODS]
    if invalid:
        raise ValueError("unsupported charge method: " + ", ".join(invalid))
    return {
        "schema_version": "1.0",
        "methods": list(dict.fromkeys(normalized)),
        "reference_density_required": True,
        "separate_outputs": {method: f"{method}.csv" for method in dict.fromkeys(normalized)},
        "validation_gates": [
            "scf_converged",
            "total_charge_closure",
            "atom_mapping",
            "equivalence_statistics",
            "chemical_sanity",
        ],
        "esp_methods_require": ["sampling_settings", "fit_quality", "sampling_sensitivity"],
        "repeat_like_semantics": "Use REPEAT_LIKE unless exact original REPEAT equivalence is independently established.",
        "posthoc_charge_shift": "FORBIDDEN",
        "recommended_method": None,
        "gromacs_status": "GROMACS_CHARGE_CANDIDATE_ONLY",
        "execution_allowed": False,
        "status": "USER_CONFIRMATION_REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = build_charge_plan(args.method)
    except ValueError as exc:
        print(json.dumps({"status": "CHARGE_PLAN_ERROR", "error": str(exc)}, indent=2))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
