#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from common import load_data

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    lines = ["# Electrolyte GROMACS generated report", "", "## Evidence", ""]
    for item in args.manifest:
        p = Path(item)
        lines += [f"### {p}", ""]
        try:
            lines.append(json.dumps(load_data(p), indent=2, sort_keys=True))
        except Exception as exc:
            lines.append(json.dumps({"error": str(exc)}))
        lines.append("")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
