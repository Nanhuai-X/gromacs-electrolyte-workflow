#!/usr/bin/env python3
"""Deterministic natural-language task routing for CP2K workflows."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


RULES = [
    ("charge_density_difference", [r"差分\s*电荷", r"电荷密度差", r"density\s*difference", r"delta[_ -]?rho"]),
    ("adsorption_energy", [r"吸附能", r"adsorption\s*energy", r"e[_ -]?ads"]),
    ("periodic_charge", [r"hirshfeld", r"mulliken", r"lowdin", r"resp", r"repeat", r"周期.*电荷", r"电荷拟合", r"电荷"]),
    ("work_function", [r"功函数", r"work\s*function", r"surface\s*potential"]),
    ("band", [r"能带", r"band\s*(structure|path)?", r"bandstructure"]),
    ("pdos", [r"pdos", r"投影态密度", r"projected\s*density"]),
    ("dos", [r"(?<!p)dos", r"态密度", r"density\s*of\s*states"]),
    ("elf", [r"\belf\b", r"elf", r"电子局域函数", r"localization\s*function"]),
    ("electron_density", [r"电子密度", r"electron\s*density", r"density\s*cube"]),
    ("neb", [r"\bneb\b", r"迁移能", r"nudged\s*elastic"]),
    ("aimd", [r"\baimd\b", r"分子动力学", r"molecular\s*dynamics"]),
    ("vibration", [r"振动", r"频率", r"vibrat", r"phonon"]),
    ("cell_opt", [r"晶胞优化", r"晶格优化", r"cell[_ -]?opt", r"lattice\s*optimization"]),
    ("geo_opt", [r"几何优化", r"结构优化", r"优化.*结构", r"优化.*几何", r"优化这个", r"geo[_ -]?opt", r"geometry\s*optimization"]),
    ("single_point", [r"单点", r"single[_ -]?point", r"total\s*energy", r"算能量"]),
]

SCIENTIFIC_GATES = {
    "adsorption_energy": ["adsorption_reference_state", "adsorbate_charge"],
    "charge_density_difference": ["fragment_coordinate_frame", "fragment_charge_state"],
    "work_function": ["slab_orientation", "slab_thickness", "vacuum_and_dipole_policy"],
    "neb": ["initial_endpoint", "final_endpoint", "atom_mapping"],
    "aimd": ["ensemble", "temperature", "timestep", "simulation_length"],
    "periodic_charge": ["charge_definition", "total_charge_closure_policy"],
    "cell_opt": ["cell_optimization_intent"],
}


def route_task(task_text: str) -> Dict[str, Any]:
    text = task_text.strip().lower()
    workflows: List[str] = []
    for workflow, patterns in RULES:
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            workflows.append(workflow)

    # A request for a density difference is not automatically a population
    # charge request merely because both contain the word "charge".
    explicit_charge_method = any(
        token in text for token in ("hirshfeld", "mulliken", "lowdin", "resp", "repeat", "周期")
    )
    if "charge_density_difference" in workflows and "periodic_charge" in workflows and not explicit_charge_method:
        workflows.remove("periodic_charge")

    if not workflows:
        return {
            "status": "TASK_UNRESOLVED",
            "task_text": task_text,
            "workflows": [],
            "prerequisites": [],
            "scientific_gates": [],
        }

    prerequisites: List[str] = []
    if any(item in workflows for item in ("band", "dos", "pdos", "elf", "electron_density", "periodic_charge")):
        prerequisites.extend(["reference_scf", "basis_potential_audit"])
    if "band" in workflows:
        prerequisites.append("kpath_audit")
    if "charge_density_difference" in workflows:
        prerequisites.append("same_grid_cube_audit")
    if "adsorption_energy" in workflows:
        prerequisites.append("three_energy_tasks")
    if "work_function" in workflows:
        prerequisites.append("vacuum_plateau_audit")
    if any(item in workflows for item in ("geo_opt", "cell_opt")):
        prerequisites.append("geometry_convergence")

    gates = []
    for workflow in workflows:
        gates.extend(SCIENTIFIC_GATES.get(workflow, []))
    return {
        "status": "ROUTED",
        "task_text": task_text,
        "workflows": workflows,
        "prerequisites": list(dict.fromkeys(prerequisites)),
        "scientific_gates": list(dict.fromkeys(gates)),
        "execution_blocked_until": "SCIENTIFIC_DECISION_REQUIRED" if gates else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = route_task(args.task)
    payload = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if record["status"] == "ROUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
