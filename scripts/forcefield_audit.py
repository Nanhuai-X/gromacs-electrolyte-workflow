#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, load_data

REQUIRED = (
    "source", "source_hash", "atomtypes", "masses", "charges", "lj",
    "bonded", "combination_rule", "fudgeLJ", "fudgeQQ", "nrexcl"
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = load_data(args.input) or {}
    missing = [k for k in REQUIRED if k not in data or data[k] in (None, "", "TODO", "SOURCE_UNKNOWN", "NOT_REPORTED")]
    result = {"status": "PASS" if not missing else "FAIL", "missing": missing, "input": args.input}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if not missing else 2

if __name__ == "__main__":
    raise SystemExit(main())
