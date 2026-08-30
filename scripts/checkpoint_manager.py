#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import dump_json, sha256

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--stage", default="continuation")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = Path(args.checkpoint)
    ok = p.is_file() and p.stat().st_size > 0
    result = {"status": "PASS" if ok else "FAIL", "checkpoint": str(p),
              "exists": p.is_file(), "size": p.stat().st_size if p.exists() else 0,
              "sha256": sha256(p) if ok else None, "stage": args.stage}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
