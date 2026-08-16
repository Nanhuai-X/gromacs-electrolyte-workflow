#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import dump_json, sha256

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = {"status": "PASS", "inputs": [], "raw_modified": False}
    for item in args.inputs:
        p = Path(item)
        if not p.is_file():
            result["status"] = "FAIL"
            result["inputs"].append({"path": str(p), "missing": True})
        else:
            result["inputs"].append({"path": str(p), "sha256": sha256(p), "role": "read-only source"})
    dump_json(result, out / "topology_manifest.json")
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
