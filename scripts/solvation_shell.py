#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from collections import Counter
from common import dump_json, mean, stdev

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--species-col", default="species")
    ap.add_argument("--count-col", default="count")
    args = ap.parse_args()
    with open(args.input, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    groups = {}
    for row in rows:
        groups.setdefault(row[args.species_col], []).append(float(row[args.count_col]))
    result = {"status": "PASS" if groups else "FAIL",
              "species": {k: {"mean": mean(v), "sd": stdev(v), "n": len(v)} for k, v in groups.items()}}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if groups else 2

if __name__ == "__main__":
    raise SystemExit(main())
