#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from common import dump_json, read_xvg, finite

def first_minimum(rows: list[list[float]], peak_index: int) -> int | None:
    for i in range(peak_index + 1, len(rows) - 1):
        if rows[i][1] <= rows[i - 1][1] and rows[i][1] <= rows[i + 1][1]:
            return i
    return None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cn-xvg")
    ap.add_argument("--fixed-cutoff-nm", type=float)
    args = ap.parse_args()
    rdf = [r[:2] for r in read_xvg(args.rdf) if len(r) >= 2 and finite(r[0]) and finite(r[1])]
    if not rdf:
        raise SystemExit("empty RDF")
    peak_index = max(range(len(rdf)), key=lambda i: rdf[i][1])
    minimum_index = first_minimum(rdf, peak_index)
    result = {"peak_r_nm": rdf[peak_index][0], "peak_g_r": rdf[peak_index][1],
              "first_minimum_r_nm": None if minimum_index is None else rdf[minimum_index][0],
              "first_shell_detected": minimum_index is not None,
              "status": "PASS" if minimum_index is not None else "NO_PHYSICAL_FIRST_SHELL"}
    if args.fixed_cutoff_nm is not None:
        result["fixed_cutoff_nm"] = args.fixed_cutoff_nm
        result["fixed_cutoff_label"] = "separate diagnostic, not first-shell minimum"
    if args.cn_xvg:
        cn = [r[:2] for r in read_xvg(args.cn_xvg) if len(r) >= 2]
        if cn:
            cutoff = rdf[minimum_index][0] if minimum_index is not None else args.fixed_cutoff_nm
            result["cn_at_cutoff"] = next((r[1] for r in reversed(cn) if cutoff is None or r[0] <= cutoff), None)
    dump_json(result, args.out)
    print(result["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
