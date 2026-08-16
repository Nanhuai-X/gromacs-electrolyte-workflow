#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import load_data

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = load_data(args.protocol)
    values = data.get("values", data)
    text = "# Resolved electrolyte MD methods\n\n"
    for key in sorted(values):
        text += f"- {key}: {values[key]}\n"
    Path(args.out).write_text(text, encoding="utf-8")
    print(args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
