#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
from pathlib import Path
from common import dump_json, sha256

COMMON = [
    "inspect_environment.py",
    "prepare_resp_job.py",
    "run_gaussian_resp.py",
    "convert_chk_fchk.py",
    "run_multiwfn_native_resp.py",
    "parse_resp_output.py",
    "validate_resp_charges.py",
]
RESP1_EXTRA = ["export_forcefield_charges.py"]
RESP2_EXTRA = ["prepare_resp2_jobs.py", "build_resp2_charges.py", "validate_multiconformer_resp2.py", "analyze_resp2_dipoles.py"]
REQUIRED_REFS = [
    "SKILL.md",
    "references/formal_resp_definition.md",
    "references/formal_resp2_definition.md",
    "references/gaussian_resp_workflow.md",
]
PROFILE_NAMES = {
    "resp1": ["resp1_bayly_standard.yaml", "resp1_classic.yaml"],
    "resp2": ["resp2.yaml", "resp2_delta_0p5.yaml", "resp2_delta_0p6.yaml"],
}

def candidates() -> list[Path]:
    values = []
    env = os.environ.get("GAUSSIAN_RESP_WORKFLOW_ROOT")
    if env:
        values.append(Path(env))
    return values

def build_route(root: Path, workflow: str) -> dict:
    missing = [rel for rel in REQUIRED_REFS if not (root / rel).is_file()]
    extras = RESP1_EXTRA if workflow.startswith("resp1") else RESP2_EXTRA
    required_scripts = COMMON + extras
    missing_scripts = [name for name in required_scripts if not (root / "scripts" / name).is_file()]
    profiles = []
    for name in PROFILE_NAMES["resp1" if workflow.startswith("resp1") else "resp2"]:
        p = root / "profiles" / name
        if p.is_file():
            profiles.append({"path": str(p), "sha256": sha256(p)})
    status = "FOUND" if not missing and not missing_scripts else "ROUTE_INCOMPLETE"
    steps = [
        "audit Gaussian/formchk/Multiwfn and record versions",
        "validate structure, charge, multiplicity, atom order and equivalence groups",
        "prepare Gaussian input and manifest",
        "run Gaussian optimization or frozen-geometry ESP single point",
        "convert CHK to FCHK and validate atom metadata",
        "run native Multiwfn two-stage RESP (menu 7 -> 18 -> 1)",
        "parse and validate charge vector and formal-charge closure",
    ]
    if workflow.startswith("resp2"):
        steps += [
            "repeat the same frozen-geometry route with CPCM-water",
            "mix q=(1-delta)*q_gas+delta*q_aqueous with the approved profile",
            "validate delta identity, mapping, equivalence and closure",
        ]
    return {
        "status": status,
        "workflow": workflow,
        "source_root": str(root),
        "source_skill_sha256": sha256(root / "SKILL.md") if (root / "SKILL.md").is_file() else None,
        "missing_references": missing,
        "missing_scripts": missing_scripts,
        "profiles": profiles,
        "steps": steps,
        "execution": "PLAN_ONLY; no Gaussian, formchk, Multiwfn, or GROMACS process was started",
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", choices=["resp1", "resp2", "resp1_multiconformer", "resp2_multiconformer"], required=True)
    ap.add_argument("--source-root")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    roots = [Path(args.source_root)] if args.source_root else candidates()
    route = next((build_route(root, args.workflow) for root in roots if (root / "SKILL.md").is_file()), None)
    if route is None:
        route = {"status": "DEPENDENCY_BLOCKED", "workflow": args.workflow,
                 "searched_roots": [str(p) for p in roots],
                 "execution": "PLAN_ONLY; no process was started"}
    dump_json(route, args.out)
    print(route["status"])
    return 0 if route["status"] == "FOUND" else 2

if __name__ == "__main__":
    raise SystemExit(main())
