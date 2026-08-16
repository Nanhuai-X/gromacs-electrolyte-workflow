#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, load_data

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = load_data(args.registry) or {}
    required = ("qm_method", "basis", "geometry_hash", "esp_inputs", "equivalence_groups", "charge")
    missing = [k for k in required if data.get(k) in (None, "", "TODO", "NOT_REPORTED")]
    result = {"status": "READY_FOR_APPROVAL" if not missing else "REQUIRES_APPROVED_INPUTS",
              "protocol": "RESP1", "missing": missing, "source_registry": args.registry}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if not missing else 2

if __name__ == "__main__":
    raise SystemExit(main())
