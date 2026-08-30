#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from common import dump_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--charge-col", default="charge")
    args = ap.parse_args()
    with open(args.input, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    values = [float(r[args.charge_col]) for r in rows]
    total = sum(values)
    result = {"status": "PASS" if abs(total) <= 1e-8 else "FAIL",
              "atom_count": len(values), "total_charge_e": total,
              "closure_tolerance_e": 1e-8, "automatic_correction": False}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
