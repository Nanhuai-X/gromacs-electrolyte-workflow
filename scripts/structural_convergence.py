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
    if len(rows) < 3:
        result = {"status": "STATISTICALLY_UNRESOLVED", "reason": "fewer than three blocks"}
        dump_json(result, args.out)
        print(result["status"])
        return 2
    metrics = {}
    for key in rows[0]:
        if key == args.time_col or not key.upper().startswith("CN"):
            continue
        try:
            vals = [float(r[key]) for r in rows]
            times = [float(r[args.time_col]) for r in rows]
        except (KeyError, ValueError):
            continue
        slope, _, r2 = linear_fit(times, vals)
        tail = vals[-2:]
        metrics[key] = {"mean": mean(vals), "sd": stdev(vals), "slope_per_ns": slope,
                        "last_two_delta": tail[1] - tail[0], "r2": r2}
    stable = bool(metrics) and all(abs(v["slope_per_ns"]) < 0.05 and abs(v["last_two_delta"]) < 0.10 for v in metrics.values())
    result = {"status": "PASS" if stable else "PASS WITH LIMITATIONS", "STRUCTURAL_PLATEAU_DETECTED": stable, "metrics": metrics}
    dump_json(result, args.out)
    print(result["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
