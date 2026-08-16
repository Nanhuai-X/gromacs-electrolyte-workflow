#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json

OPTIONS = {
    "RESP1": {
        "status": "RECOMMENDED_DEFAULT",
        "cost": "lower",
        "description": "One formal RESP charge workflow; usually lower Gaussian and Multiwfn cost.",
        "scientific_note": "Does not include the RESP2 gas/implicit-solvent interpolation."
    },
    "RESP2": {
        "status": "USER_APPROVAL_REQUIRED",
        "cost": "higher",
        "description": "Gas plus implicit-solvent RESP branches followed by sourced interpolation.",
        "scientific_note": "Often more environment-aware, but not universally more accurate and requires extra QM/ESP work."
    },
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["RESP1", "RESP2"])
    ap.add_argument("--literature-method")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not args.method:
        result = {"status": "USER_DECISION_REQUIRED", "question": "Choose RESP1 or RESP2 before Gaussian work.",
                  "options": OPTIONS, "literature_method": args.literature_method}
    else:
        result = {"status": "PASS", "selected_method": args.method, "choice": OPTIONS[args.method],
                  "literature_method": args.literature_method,
                  "override_policy": "a complete approved literature method/basis/functional/profile overrides the default field by field"}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
