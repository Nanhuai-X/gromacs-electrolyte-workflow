#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import dump_json, load_data

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    cfg = load_data(args.config) or {}
    seed = cfg.get("seed")
    box = cfg.get("box_nm")
    components = cfg.get("components", [])
    missing = [name for name, value in (("seed", seed), ("box_nm", box), ("components", components)) if value in (None, [], "TODO")]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = {"status": "PLAN_ONLY" if missing else "PASS", "missing": missing}
    if not missing:
        lines = [f"tolerance {cfg.get('tolerance_nm', 'TODO')}", f"seed {seed}", "output packed.pdb", "filetype pdb"]
        for c in components:
            lines += [f"structure {c['structure']}", f"  number {c['count']}", "end structure"]
        (out / "packmol.inp").write_text("\n".join(lines) + "\n", encoding="utf-8")
    dump_json(result, out / "packmol_plan.json")
    print(result["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
