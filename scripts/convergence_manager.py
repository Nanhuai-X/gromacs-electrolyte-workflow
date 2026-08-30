#!/usr/bin/env python3
"""Create property-specific convergence plans without inventing thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


METRICS = {
    "single_point": ["scf_residual", "total_energy"],
    "geo_opt": ["max_force", "rms_force", "max_displacement", "rms_displacement"],
    "cell_opt": ["max_force", "stress", "cell_change", "volume_change"],
    "band": ["scf_residual", "kpath_definition", "band_energy_stability", "vbm_cbm_stability"],
    "dos": ["scf_residual", "state_count", "energy_window", "broadening_sensitivity"],
    "pdos": ["scf_residual", "state_count", "orbital_projection", "energy_window"],
    "elf": ["scf_residual", "cube_grid", "cube_finite_values"],
    "electron_density": ["scf_residual", "cube_grid", "cube_finite_values"],
    "charge_density_difference": ["cube_grid", "origin", "voxel_axes", "integrated_residual"],
    "adsorption_energy": ["three_energy_consistency", "reference_state", "energy_difference"],
    "work_function": ["scf_residual", "vacuum_plateau", "slab_thickness", "vacuum_size"],
    "periodic_charge": ["scf_residual", "charge_closure", "mapping", "fit_quality", "sampling_sensitivity"],
}


def build_convergence_plan(workflow: str, priority: str = "balanced") -> Dict[str, Any]:
    metrics = METRICS.get(workflow, ["scf_residual", "property_specific_validation"])
    axes = ["CUTOFF", "REL_CUTOFF", "kpoints", "basis_level", "EPS_SCF"]
    if workflow in {"geo_opt", "cell_opt"}:
        axes.append("geometry_thresholds")
    if workflow in {"work_function", "charge_density_difference"}:
        axes.extend(["vacuum_size", "grid_shape"])
    if workflow in {"dos", "pdos", "band"}:
        axes.extend(["ADDED_MOS", "smearing_or_broadening"])
    return {
        "schema_version": "1.0",
        "workflow": workflow,
        "priority": priority,
        "metrics": metrics,
        "candidate_axes": axes,
        "candidate_profiles": ["COST_EFFECTIVE", "BALANCED", "HIGH_PRECISION"],
        "thresholds": None,
        "requires_user_confirmation": True,
        "note": "Thresholds must come from the user, literature, or an explicitly approved project profile; no universal value is assumed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--priority", choices=["cost", "balanced", "accuracy"], default="balanced")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = build_convergence_plan(args.workflow, args.priority)
    payload = json.dumps(plan, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
