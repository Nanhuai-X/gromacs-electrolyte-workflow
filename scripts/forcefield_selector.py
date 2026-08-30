#!/usr/bin/env python3
from __future__ import annotations
import argparse
from common import dump_json, load_data

REQUIRED = ("source", "source_hash", "complete", "compatible")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidate")
    args = ap.parse_args()
    data = load_data(args.registry) or {}
    candidates = data.get("candidates", data if isinstance(data, list) else [])
    if not isinstance(candidates, list):
        raise SystemExit("registry must contain candidates")
    ranked = []
    for c in candidates:
        missing = [k for k in REQUIRED if not c.get(k) or c.get(k) in ("TODO", "SOURCE_UNKNOWN", "NOT_REPORTED")]
        score = int(bool(c.get("complete"))) + int(bool(c.get("compatible"))) + int(bool(c.get("validated")))
        ranked.append({"id": c.get("id"), "score": score, "missing": missing, "candidate": c})
    ranked.sort(key=lambda x: (-x["score"], str(x["id"])))
    selected = next((x for x in ranked if not x["missing"] and (args.candidate is None or x["id"] == args.candidate)), None)
    result = {"status": "PASS" if selected else "FAIL", "selected": selected, "ranked": ranked}
    dump_json(result, args.out)
    print(result["status"])
    return 0 if selected else 2

if __name__ == "__main__":
    raise SystemExit(main())
