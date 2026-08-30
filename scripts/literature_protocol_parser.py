#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, load_data

DEFAULTS = {
    "temperature_K": 298.15,
    "pressure_bar": 1.0,
    "dt_ps": 0.002,
    "constraints": "h-bonds",
    "lincs_order": 4,
    "lincs_iter": 1,
    "cutoff_scheme": "Verlet",
    "coulombtype": "PME",
    "anneal_duration_ps": 600,
    "npt_minimum_ns": 5,
    "npt_extension_ns": 2,
    "npt_maximum_ns": 10,
    "nvt_transition_ns": 1,
    "production_ns": 20,
}

def deep_get(data, key):
    if key in data:
        return data[key]
    for value in data.values():
        if isinstance(value, dict):
            found = deep_get(value, key)
            if found is not None:
                return found
    return None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--mode", choices=["reproduction", "reference_guided", "literature", "default", "hybrid"], default="default")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    source = load_data(args.input) or {}
    if not isinstance(source, dict):
        raise SystemExit("protocol input must be a mapping")
    resolved, filled, unresolved = {}, [], []
    for key, default in DEFAULTS.items():
        value = deep_get(source, key)
        if args.mode == "default":
            value = default
            filled.append(key)
        elif args.mode in ("literature", "reproduction"):
            if value is None:
                unresolved.append(key)
        elif value is None:
            value = default
            filled.append(key)
        resolved[key] = value
    result = {
        "PROTOCOL_SOURCE": source.get("source") or source.get("protocol_source") or args.mode,
        "mode": args.mode,
        "resolved": resolved,
        "DEFAULT_FILLED": filled,
        "unresolved": unresolved,
        "deviations": source.get("deviations", []),
        "status": "PROTOCOL_UNRESOLVED" if unresolved else "PASS",
    }
    dump_json(result, args.out)
    print(result["status"])
    return 0 if not unresolved else 2

if __name__ == "__main__":
    raise SystemExit(main())
