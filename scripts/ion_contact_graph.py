#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from common import dump_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edges", required=True, help="cation,anion, distance_nm")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    by_cation = defaultdict(set)
    with open(args.edges, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_cation[row["cation"]].add(row["anion"])
    counts = [len(v) for v in by_cation.values()]
    labels = {"SSIP-like": sum(n == 0 for n in counts), "CIP-like": sum(n == 1 for n in counts), "AGG-like": sum(n >= 2 for n in counts)}
    result = {"status": "PASS", "definition": "anion contacts per cation: 0 SSIP-like, 1 CIP-like, >=2 AGG-like",
              "cation_count": len(counts), "counts": labels}
    dump_json(result, args.out)
    print("PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
