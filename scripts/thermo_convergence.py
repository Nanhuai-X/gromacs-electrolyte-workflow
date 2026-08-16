#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from common import dump_json, linear_fit, mean, stdev

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--time-col", default="time_ns")
    args = ap.parse_args()
    with open(args.input, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("empty table")
    numeric = [k for k in rows[0] if k != args.time_col]
    metrics = {}
    for key in numeric:
        try:
            vals = [float(r[key]) for r in rows]
            times = [float(r[args.time_col]) for r in rows]
        except (KeyError, ValueError):
            continue
        slope, intercept, r2 = linear_fit(times, vals)
        metrics[key] = {"mean": mean(vals), "sd": stdev(vals), "slope_per_ns": slope, "r2": r2}
    result = {"status": "PASS" if metrics else "FAIL", "rows": len(rows), "metrics": metrics}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if metrics else 2

if __name__ == "__main__":
    raise SystemExit(main())
