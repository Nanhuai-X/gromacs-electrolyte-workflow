#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, load_data

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = load_data(args.registry) or {}
    factor = data.get("interpolation_factor")
    missing = [k for k in ("gas_charge_file", "aqueous_charge_file", "atom_mapping") if not data.get(k)]
    if factor in (None, "", "TODO") or not (0.0 <= float(factor) <= 1.0):
        missing.append("interpolation_factor_0_to_1")
    result = {"status": "READY_FOR_APPROVAL" if not missing else "REQUIRES_APPROVED_INPUTS",
              "protocol": "RESP2", "missing": missing,
              "scientific_action": "no fitting or interpolation is performed by this plan script"}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if not missing else 2

if __name__ == "__main__":
    raise SystemExit(main())
