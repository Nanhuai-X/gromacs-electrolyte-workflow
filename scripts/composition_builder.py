#!/usr/bin/env python3
from __future__ import annotations
import argparse
import math
from fractions import Fraction
from functools import reduce
from common import dump_json, load_data, write_table

def lcm(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = load_data(args.config) or {}
    components = cfg.get("components", [])
    base = (cfg.get("system") or {}).get("base_component_count")
    if base in ("", "null", "TODO"):
        base = None
    if not components:
        raise SystemExit("no components")
    ratios = [Fraction(str(c["ratio"])) for c in components]
    den = reduce(lcm, (r.denominator for r in ratios), 1)
    primitive = [r.numerator * (den // r.denominator) for r in ratios]
    result = {"status": "PASS", "ratio_basis": primitive, "components": []}
    if base is None:
        result.update({"status": "COUNT_REQUIRED", "message": "set system.base_component_count; no formal box was built"})
        dump_json(result, args.out)
        print("COUNT_REQUIRED")
        return 2
    base = int(base)
    if base % primitive[0] != 0:
        result.update({"status": "BASE_COUNT_NOT_DIVISIBLE", "message": "base count is not an integer multiple of the first ratio unit"})
        dump_json(result, args.out)
        print(result["status"])
        return 2
    multiplier = base // primitive[0]
    counts = [n * multiplier for n in primitive]
    for comp, count, ratio in zip(components, counts, ratios):
        result["components"].append({"name": comp["name"], "ratio": str(ratio), "count": count})
    result["total_molecules"] = sum(counts)
    result["base_component_count"] = base
    rows = [{"name": c["name"], "ratio": c["ratio"], "count": c["count"]} for c in result["components"]]
    out = args.out
    dump_json(result, out)
    if str(out).endswith(".json"):
        write_table(rows, str(out)[:-5] + ".csv", ["name", "ratio", "count"])
    print("PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
