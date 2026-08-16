#!/usr/bin/env python3
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from common import dump_json, sha256

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--command", nargs="*")
    args = ap.parse_args()
    out = Path(args.out)
    record = {"timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "files": {str(Path(p)): sha256(p) for p in (args.hash or []) if Path(p).is_file()}}
    if args.command:
        record["command"] = args.command
    records = []
    if out.exists():
        try:
            records = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records = []
    if not isinstance(records, list):
        records = [records]
    records.append(record)
    dump_json(records, out)
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
