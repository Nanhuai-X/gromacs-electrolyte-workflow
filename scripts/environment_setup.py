#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from common import dump_json, load_data

PACKAGE_PLAN = {
    "python3": "approved package plan: python3 (and python3-venv if the project virtualenv is absent)",
    "gcc": "approved package plan: build-essential (gcc/g++/make)",
    "cmake": "approved package plan: cmake >= 3.28",
    "make": "approved package plan: build-essential (make)",
    "packmol": "approved package plan: Packmol from the approved project environment or distribution package",
    "gromacs_cpu_or_cuda_prefix": "approved package plan: use the existing user-prefix GROMACS build or a separately approved source build; never apt install Ubuntu gromacs",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runtime-script")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm-file")
    args = ap.parse_args()
    data = load_data(args.preflight)
    missing = data.get("missing_core", [])
    plan = {
        "status": "NO_ACTION_REQUIRED" if not missing else "ENVIRONMENT_BLOCKED",
        "missing_core": missing,
        "missing_core_plan": {name: PACKAGE_PLAN.get(name, "manual audit required") for name in missing},
        "source_paths": data.get("setup_plan", {}),
        "automatic_install": False,
        "commands_requiring_user_approval": [
            "install only the missing core dependency after an explicit audit and approval",
            "never install Ubuntu gromacs when a project CPU/CUDA prefix is available",
            "do not use sudo/apt/pip automatically from this Skill",
        ],
    }
    if args.execute:
        if args.confirm_file is None or not Path(args.confirm_file).is_file():
            plan["status"] = "CONFIRMATION_REQUIRED"
        elif missing:
            plan["status"] = "INSTALLATION_NOT_IMPLEMENTED_BY_SKILL"
            plan["reason"] = (
                "This Skill writes no sudo/apt/pip changes; use the approved project "
                "installation stage after reviewing missing_core_plan."
            )
        else:
            runtime = Path(args.runtime_script or "environment_runtime.sh")
            setup = data.get("setup_plan") if isinstance(data.get("setup_plan"), dict) else {}
            loader = setup.get("source_cpu_environment") or setup.get("source_cuda_environment")
            python_env = setup.get("source_python_environment")
            if not loader and not python_env:
                plan["status"] = "RUNTIME_PATH_REQUIRED"
                plan["reason"] = (
                    "Preflight did not provide environment loader or Python virtualenv paths."
                )
                dump_json(plan, args.out)
                print(plan["status"])
                return 2
            lines = ["#!/usr/bin/env bash", "set -euo pipefail"]
            if loader:
                lines.append(f"source {shlex.quote(str(loader))}")
            if python_env:
                lines.append(f"source {shlex.quote(str(python_env))}")
            runtime.write_text("\n".join(lines) + "\n", encoding="utf-8")
            runtime.chmod(0o755)
            plan["status"] = "PASS"
            plan["runtime_script"] = str(runtime)
    dump_json(plan, args.out)
    print(plan["status"])
    return 0 if plan["status"] in ("NO_ACTION_REQUIRED", "PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
