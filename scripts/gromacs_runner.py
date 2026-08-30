#!/usr/bin/env python3
from __future__ import annotations
import argparse
import shlex
import subprocess
from pathlib import Path
from common import dump_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["em", "anneal", "npt", "nvt_transition", "production"])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--topology", required=True)
    ap.add_argument("--input", required=True, help="coordinate or prior-stage input")
    ap.add_argument("--checkpoint")
    ap.add_argument("--gmx", default="gmx")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm-file")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if "maxwarn" in str(vars(args)).lower():
        raise SystemExit("maxwarn is forbidden")
    if args.stage in ("npt", "nvt_transition", "production") and not args.checkpoint:
        raise SystemExit("continuation stage requires --checkpoint")
    if args.stage == "production" and (not args.execute or not args.confirm_file or not Path(args.confirm_file).is_file()):
        result = {"status": "PLAN_ONLY", "reason": "production requires explicit --execute and confirmation file"}
        dump_json(result, args.out)
        print("PLAN_ONLY")
        return 0
    cmd = [args.gmx, "grompp", "-f", args.input, "-p", args.topology, "-o", str(run_dir / "stage.tpr"), "-pp", str(run_dir / "processed.top")]
    if args.checkpoint:
        cmd += ["-t", args.checkpoint]
    commands = [cmd, [args.gmx, "mdrun", "-deffnm", str(run_dir / "stage"), "-cpt", "15"]]
    result = {"status": "PLAN_ONLY", "commands": [shlex.join(c) for c in commands], "stage": args.stage}
    if args.execute:
        result["runs"] = []
        for command in commands:
            proc = subprocess.run(command, cwd=run_dir, text=True, capture_output=True, check=False)
            result["runs"].append({"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            if proc.returncode != 0:
                result["status"] = "FAIL"
                break
        else:
            result["status"] = "PASS"
    dump_json(result, args.out)
    print(result["status"])
    return 0 if result["status"] in ("PASS", "PLAN_ONLY") else 2

if __name__ == "__main__":
    raise SystemExit(main())
