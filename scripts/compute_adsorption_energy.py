#!/usr/bin/env python3
"""Compute CP2K adsorption-energy bookkeeping with explicit assumptions."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


HARTREE_TO_EV = 27.211386245988
INVARIANT_KEYS = (
    "functional",
    "dispersion",
    "basis",
    "potential",
    "cutoff",
    "rel_cutoff",
    "charge_spin",
    "kpoints",
    "eps_scf",
)


def compare_invariants(settings: Optional[Mapping[str, Mapping[str, Any]]]) -> Dict[str, Any]:
    """Compare settings for complex, host, and adsorbate calculations."""

    labels = ("complex", "host", "adsorbate")
    if settings is None:
        return {
            "status": "NOT_PROVIDED",
            "consistent": None,
            "mismatches": {},
        }
    missing = [label for label in labels if not isinstance(settings.get(label), Mapping)]
    if missing:
        return {
            "status": "INVALID",
            "consistent": False,
            "mismatches": {"missing_calculations": missing},
        }

    mismatches: Dict[str, Dict[str, Any]] = {}
    for key in INVARIANT_KEYS:
        values = {label: settings[label].get(key) for label in labels}
        if len({json.dumps(value, sort_keys=True, default=str) for value in values.values()}) > 1:
            mismatches[key] = values
    return {
        "status": "PASS" if not mismatches else "MISMATCH",
        "consistent": not mismatches,
        "mismatches": mismatches,
    }


def compute_adsorption_energy(
    complex_energy_au: float,
    host_energy_au: float,
    adsorbate_energy_au: float,
    settings: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Return E_ads = E_complex - E_host - E_adsorbate.

    Energies are expected in Hartree. The result is also reported in electron
    volts. This function performs bookkeeping only; it does not decide the
    reference state or geometry policy.
    """

    energies = {
        "complex": float(complex_energy_au),
        "host": float(host_energy_au),
        "adsorbate": float(adsorbate_energy_au),
    }
    invalid = [label for label, value in energies.items() if not math.isfinite(value)]
    if invalid:
        return {
            "status": "FAIL",
            "error": "non-finite energy: " + ", ".join(invalid),
            "sign_convention": "E_ads = E_complex - E_host - E_adsorbate",
        }

    energy_au = energies["complex"] - energies["host"] - energies["adsorbate"]
    invariant_check = compare_invariants(settings)
    status = "FAIL" if invariant_check["consistent"] is False else "PASS"
    limitations = [
        "This is energy bookkeeping; reference-state and geometry decisions remain scientific gates.",
    ]
    if invariant_check["status"] == "NOT_PROVIDED":
        limitations.append("Same-theory settings were not supplied and were not checked.")
    if invariant_check["status"] == "MISMATCH":
        limitations.append("Complex, host, and adsorbate settings are inconsistent.")
    return {
        "schema_version": "1.0",
        "status": status,
        "energies_hartree": energies,
        "adsorption_energy_hartree": energy_au,
        "adsorption_energy_ev": energy_au * HARTREE_TO_EV,
        "sign_convention": "E_ads = E_complex - E_host - E_adsorbate",
        "negative_is_favorable_under_this_convention": True,
        "invariant_check": invariant_check,
        "limitations": limitations,
    }


def _read_json(value: str) -> Dict[str, Any]:
    path = Path(value)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("settings JSON must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complex-energy-au", type=float, required=True)
    parser.add_argument("--host-energy-au", type=float, required=True)
    parser.add_argument("--adsorbate-energy-au", type=float, required=True)
    parser.add_argument("--settings-json", help="JSON object or path with complex/host/adsorbate settings")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        settings = _read_json(args.settings_json) if args.settings_json else None
        result = compute_adsorption_energy(
            args.complex_energy_au,
            args.host_energy_au,
            args.adsorbate_energy_au,
            settings,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "FAIL", "error": str(exc)}
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
