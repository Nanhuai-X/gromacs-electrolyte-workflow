#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from common import dump_json

def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ref, cand = read(args.reference), read(args.candidate)
    same = len(ref) == len(cand) and all(a.get("atom_index") == b.get("atom_index") and a.get("atom_name") == b.get("atom_name") for a, b in zip(ref, cand))
    result = {"status": "PASS" if same else "FAIL", "reference_atoms": len(ref), "candidate_atoms": len(cand), "order_and_names_equal": same}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if same else 2

if __name__ == "__main__":
    raise SystemExit(main())
