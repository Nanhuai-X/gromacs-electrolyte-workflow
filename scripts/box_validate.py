#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import dump_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--expected-atoms", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    lines = Path(args.structure).read_text(encoding="utf-8", errors="replace").splitlines()
    count = sum(1 for line in lines if line.startswith(("ATOM", "HETATM")))
    result = {"status": "PASS" if args.expected_atoms in (None, count) and count > 0 else "FAIL",
              "atom_count": count, "expected_atoms": args.expected_atoms,
              "overlap_check": "requires coordinate-level validator"}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
