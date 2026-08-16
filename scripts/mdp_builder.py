#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import dump_json, load_data

DEFAULT = {
    "temperature_K": 298.15,
    "pressure_bar": 1.0,
    "dt_ps": 0.002,
    "constraints": "h-bonds",
    "lincs_order": 4,
    "lincs_iter": 1,
    "tcoupl": "Nose-Hoover",
    "tau_t_ps": 1.0,
    "pcoupl": "C-rescale",
    "pcoupltype": "isotropic",
    "tau_p_ps": 5.0,
    "compressibility_bar_inv": 4.5e-5,
    "coulombtype": "PME",
    "cutoff_scheme": "Verlet",
    "pbc": "xyz",
    "dispersion_correction": "no",
    "nstxout_compressed": 1000,
    "nstenergy": 1000,
    "nstlog": 5000,
    "checkpoint_minutes": 15,
    "em_emtol": 1000,
    "em_max_steps": 50000,
    "anneal_steps": 300000,
    "anneal_times_ps": [0, 100, 200, 350, 500, 600],
    "anneal_temps_K": [298.15, 298.15, 350, 350, 298.15, 298.15],
    "npt_steps": 2500000,
    "transition_steps": 500000,
    "production_steps": 10000000,
}


def resolved_values(data: dict) -> tuple[dict, dict]:
    if isinstance(data.get("resolved"), dict):
        source = data["resolved"]
    elif isinstance(data.get("values"), dict):
        source = data["values"]
    else:
        source = data
    values = dict(DEFAULT)
    sources = {key: "default_protocol" for key in values}
    field_sources = data.get("field_sources", {})

    def source_for(path: str) -> str:
        return field_sources.get(path, "resolved_input")

    for key in (
        "temperature_K",
        "pressure_bar",
        "dt_ps",
        "constraints",
        "lincs_order",
        "lincs_iter",
        "coulombtype",
        "cutoff_scheme",
        "pbc",
        "dispersion_correction",
    ):
        if key in source and source[key] is not None:
            values[key] = source[key]
            sources[key] = data.get("field_sources", {}).get(key, "resolved_input")

    thermostat = source.get("thermostat", {})
    if isinstance(thermostat, dict):
        for key, out_key in (
            ("name", "tcoupl"),
            ("tau_t_ps", "tau_t_ps"),
            ("ref_t_K", "temperature_K"),
        ):
            if key in thermostat and thermostat[key] is not None:
                if (
                    key == "ref_t_K"
                    and data.get("field_sources", {}).get("thermostat.ref_t_K") == "default_protocol"
                ):
                    continue
                values[out_key] = thermostat[key]
                sources[out_key] = "resolved_input"

    barostat = source.get("barostat", {})
    if isinstance(barostat, dict):
        for key, out_key in (
            ("name", "pcoupl"),
            ("type", "pcoupltype"),
            ("tau_p_ps", "tau_p_ps"),
            ("ref_p_bar", "pressure_bar"),
            ("compressibility_bar_inv", "compressibility_bar_inv"),
        ):
            if key in barostat and barostat[key] is not None:
                if (
                    key == "ref_p_bar"
                    and data.get("field_sources", {}).get("barostat.ref_p_bar") == "default_protocol"
                ):
                    continue
                values[out_key] = barostat[key]
                sources[out_key] = "resolved_input"

    electro = source.get("electrostatics", {})
    if isinstance(electro, dict):
        for key in ("coulombtype", "cutoff_scheme", "pbc", "dispersion_correction"):
            if key in electro and electro[key] is not None:
                values[key] = electro[key]
                sources[key] = "resolved_input"

    stages = source.get("stages", {})
    if isinstance(stages, dict):
        em = stages.get("em", {})
        if isinstance(em, dict):
            if em.get("emtol") is not None:
                values["em_emtol"] = em["emtol"]
                sources["em_emtol"] = source_for("stages.em.emtol")
            if em.get("max_steps") is not None:
                values["em_max_steps"] = em["max_steps"]
                sources["em_max_steps"] = source_for("stages.em.max_steps")
        anneal = stages.get("nvt_anneal", {})
        if isinstance(anneal, dict):
            if anneal.get("duration_ps") is not None:
                values["anneal_steps"] = int(
                    round(float(anneal["duration_ps"]) / float(values["dt_ps"]))
                )
                sources["anneal_steps"] = source_for("stages.nvt_anneal.duration_ps")
            if anneal.get("times_ps") is not None:
                values["anneal_times_ps"] = anneal["times_ps"]
                sources["anneal_times_ps"] = source_for("stages.nvt_anneal.times_ps")
            if anneal.get("temperatures_K") is not None:
                values["anneal_temps_K"] = anneal["temperatures_K"]
                sources["anneal_temps_K"] = source_for("stages.nvt_anneal.temperatures_K")
        npt = stages.get("npt", {})
        if isinstance(npt, dict) and npt.get("minimum_ns") is not None:
            values["npt_steps"] = int(
                round(float(npt["minimum_ns"]) * 1000 / float(values["dt_ps"]))
            )
            sources["npt_steps"] = source_for("stages.npt.minimum_ns")
        transition = stages.get("nvt_transition", {})
        if isinstance(transition, dict) and transition.get("duration_ns") is not None:
            values["transition_steps"] = int(
                round(float(transition["duration_ns"]) * 1000 / float(values["dt_ps"]))
            )
            sources["transition_steps"] = source_for("stages.nvt_transition.duration_ns")
        production = stages.get("production", {})
        if isinstance(production, dict) and production.get("duration_ns") is not None:
            values["production_steps"] = int(
                round(float(production["duration_ns"]) * 1000 / float(values["dt_ps"]))
            )
            sources["production_steps"] = source_for("stages.production.duration_ns")

    output = source.get("output", {})
    if isinstance(output, dict):
        for key in ("nstxout_compressed", "nstenergy", "nstlog", "checkpoint_minutes"):
            if key in output and output[key] is not None:
                values[key] = output[key]
                sources[key] = "resolved_input"

    for key in ("nsteps", "npt_steps", "transition_steps", "production_steps"):
        if key in source and source[key] is not None:
            values[key] = source[key]
    return values, sources


def common_lines(values: dict) -> list[str]:
    return [
        "integrator = md",
        f"dt = {values['dt_ps']}",
        f"constraints = {values['constraints']}",
        f"lincs-order = {values['lincs_order']}",
        f"lincs-iter = {values['lincs_iter']}",
        f"coulombtype = {values['coulombtype']}",
        f"cutoff-scheme = {values['cutoff_scheme']}",
        f"pbc = {values['pbc']}",
        f"dispersion-correction = {values['dispersion_correction']}",
        f"nstxout-compressed = {values['nstxout_compressed']}",
        f"nstenergy = {values['nstenergy']}",
        f"nstlog = {values['nstlog']}",
    ]


def thermostat_lines(values: dict) -> list[str]:
    return [
        f"tcoupl = {values['tcoupl']}",
        "tc-grps = System",
        f"tau-t = {values['tau_t_ps']}",
        f"ref-t = {values['temperature_K']}",
    ]


def write_mdp(path: Path, values: dict, stage: str) -> None:
    if stage == "em":
        lines = [
            "; resolved by gromacs-electrolyte-workflow",
            "integrator = steep",
            f"emtol = {values['em_emtol']}",
            f"nsteps = {values['em_max_steps']}",
            f"coulombtype = {values['coulombtype']}",
            f"cutoff-scheme = {values['cutoff_scheme']}",
            f"pbc = {values['pbc']}",
        ]
    else:
        lines = ["; resolved by gromacs-electrolyte-workflow", *common_lines(values)]
        if stage == "anneal":
            lines += [
                f"nsteps = {values['anneal_steps']}",
                "continuation = no",
                "gen-vel = yes",
                *thermostat_lines(values),
                "annealing = single",
                f"annealing-npoints = {len(values['anneal_times_ps'])}",
                "annealing-time = " + " ".join(map(str, values["anneal_times_ps"])),
                "annealing-temp = " + " ".join(map(str, values["anneal_temps_K"])),
            ]
        elif stage == "npt":
            lines += [
                f"nsteps = {values['npt_steps']}",
                "continuation = yes",
                "gen-vel = no",
                *thermostat_lines(values),
                f"pcoupl = {values['pcoupl']}",
                f"pcoupltype = {values['pcoupltype']}",
                f"tau-p = {values['tau_p_ps']}",
                f"ref-p = {values['pressure_bar']}",
                f"compressibility = {values['compressibility_bar_inv']}",
            ]
        elif stage == "nvt_transition":
            lines += [
                f"nsteps = {values['transition_steps']}",
                "continuation = yes",
                "gen-vel = no",
                *thermostat_lines(values),
            ]
        elif stage == "production":
            lines += [
                f"nsteps = {values['production_steps']}",
                "continuation = yes",
                "gen-vel = no",
                *thermostat_lines(values),
            ]
        else:
            raise ValueError(stage)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--resolved-protocol")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    source_path = args.resolved_protocol or args.config
    data = load_data(source_path) if source_path else {}
    values, sources = resolved_values(data or {})
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stage in ("em", "anneal", "npt", "nvt_transition", "production"):
        write_mdp(out / (stage + ".mdp"), values, stage)
    resolved = {
        "values": values,
        "field_sources": sources,
        "expected_frames_production": values["production_steps"] // values["nstxout_compressed"] + 1,
    }
    dump_json(resolved, out / "resolved_protocol.json")
    print(json.dumps(resolved, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
