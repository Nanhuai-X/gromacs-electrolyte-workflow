#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, linear_fit, read_xvg

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--msd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--windows", default="5:20,10:20")
    ap.add_argument("--dimension", type=int, default=3)
    args = ap.parse_args()
    rows = [r[:2] for r in read_xvg(args.msd) if len(r) >= 2]
    results = []
    for spec in args.windows.split(","):
        lo, hi = [float(x) for x in spec.split(":")]
        chosen = [(t, v) for t, v in rows if lo <= t <= hi]
        if len(chosen) < 3:
            continue
        slope, intercept, r2 = linear_fit([x[0] for x in chosen], [x[1] for x in chosen])
        results.append({"window": spec, "slope_msd_per_time": slope, "intercept": intercept,
                        "r2": r2, "D_in_msd_units": slope / (2 * args.dimension), "n": len(chosen)})
    quality = bool(results) and max(r["r2"] for r in results) >= 0.95
    result = {"status": "PASS" if results else "STATISTICALLY_UNRESOLVED",
              "MSD_DIFFUSIVE_REGIME_IDENTIFIED": bool(results),
              "DIFFUSION_COEFFICIENT_PRODUCTION_QUALITY": False,
              "reason": "block uncertainty and unit audit are required before a production-quality coefficient",
              "fits": results}
    dump_json(result, args.out)
    print(result["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
