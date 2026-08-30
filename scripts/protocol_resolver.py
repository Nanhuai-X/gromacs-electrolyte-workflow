#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy

from common import dump_json, load_data

DEFAULT_PROTOCOL = {
    "temperature_K": 298.15,
    "pressure_bar": 1.0,
    "dt_ps": 0.002,
    "constraints": "h-bonds",
    "lincs_order": 4,
    "lincs_iter": 1,
    "thermostat": {"name": "Nose-Hoover", "tau_t_ps": 1.0, "ref_t_K": 298.15},
    "barostat": {
        "name": "C-rescale",
        "type": "isotropic",
        "tau_p_ps": 5.0,
        "ref_p_bar": 1.0,
        "compressibility_bar_inv": 4.5e-5,
    },
    "electrostatics": {
        "coulombtype": "PME",
        "cutoff_scheme": "Verlet",
        "pbc": "xyz",
        "dispersion_correction": "no",
    },
    "stages": {
        "em": {"method": "steep", "emtol": 1000, "max_steps": 50000},
        "nvt_anneal": {
            "duration_ps": 600,
            "times_ps": [0, 100, 200, 350, 500, 600],
            "temperatures_K": [298.15, 298.15, 350, 350, 298.15, 298.15],
        },
        "npt": {"minimum_ns": 5, "extension_ns": 2, "maximum_ns": 10},
        "nvt_transition": {"duration_ns": 1},
        "production": {"duration_ns": 20},
    },
    "output": {
        "nstxout_compressed": 1000,
        "nstenergy": 1000,
        "nstlog": 5000,
        "checkpoint_minutes": 15,
    },
    "charge_method": {"method": None, "source": "USER_DECISION_REQUIRED"},
}

REQUIRED_REPRODUCTION = (
    ("temperature_K",),
    ("pressure_bar",),
    ("dt_ps",),
    ("thermostat", "name"),
    ("barostat", "name"),
    ("electrostatics", "coulombtype"),
    ("stages", "npt", "minimum_ns"),
    ("stages", "production", "duration_ns"),
)

TRACKED_REFERENCE_PATHS = (
    ("temperature_K",),
    ("pressure_bar",),
    ("dt_ps",),
    ("constraints",),
    ("lincs_order",),
    ("lincs_iter",),
    ("thermostat", "name"),
    ("thermostat", "tau_t_ps"),
    ("thermostat", "ref_t_K"),
    ("barostat", "name"),
    ("barostat", "type"),
    ("barostat", "tau_p_ps"),
    ("barostat", "ref_p_bar"),
    ("barostat", "compressibility_bar_inv"),
    ("electrostatics", "coulombtype"),
    ("electrostatics", "cutoff_scheme"),
    ("electrostatics", "pbc"),
    ("electrostatics", "dispersion_correction"),
    ("stages", "em", "method"),
    ("stages", "em", "emtol"),
    ("stages", "em", "max_steps"),
    ("stages", "nvt_anneal", "duration_ps"),
    ("stages", "nvt_anneal", "times_ps"),
    ("stages", "nvt_anneal", "temperatures_K"),
    ("stages", "npt", "minimum_ns"),
    ("stages", "npt", "extension_ns"),
    ("stages", "npt", "maximum_ns"),
    ("stages", "nvt_transition", "duration_ns"),
    ("stages", "production", "duration_ns"),
    ("output", "nstxout_compressed"),
    ("output", "nstenergy"),
    ("output", "nstlog"),
    ("output", "checkpoint_minutes"),
)


def deep_merge(base, override, source_map, prefix=""):
    if not isinstance(override, dict):
        return deepcopy(override)
    result = deepcopy(base)
    for key, value in override.items():
        if value is None:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value, source_map, path)
        else:
            result[key] = deepcopy(value)
            source_map[path] = "literature_or_user"
    return result


def get_path(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def find_protocol_input(data):
    if not isinstance(data, dict):
        return {}
    if isinstance(data.get("literature_protocol"), dict):
        return data["literature_protocol"]
    protocol = data.get("protocol")
    if isinstance(protocol, dict):
        if isinstance(protocol.get("literature"), dict):
            return protocol["literature"]
        return protocol
    return data


def protocol_values(input_protocol: dict) -> dict:
    values = deepcopy(input_protocol)
    for key in ("mode", "source", "doi", "reference"):
        values.pop(key, None)
    return values


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument(
        "--mode",
        choices=["default", "reproduction", "reference_guided", "hybrid"],
        default=None,
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    raw = load_data(args.input) or {}
    input_protocol = find_protocol_input(raw)
    protocol_container = raw.get("protocol") if isinstance(raw.get("protocol"), dict) else {}
    mode = (
        args.mode
        or protocol_container.get("mode")
        or input_protocol.get("mode")
        or raw.get("mode")
        or "default"
    )
    if mode == "literature":
        mode = "reproduction"

    source_map = {}
    resolved = deepcopy(DEFAULT_PROTOCOL)
    filled = []
    if mode != "default":
        values = protocol_values(input_protocol)
        resolved = deep_merge(resolved, values, source_map)
        if mode in ("reference_guided", "hybrid"):
            filled = [
                ".".join(path)
                for path in TRACKED_REFERENCE_PATHS
                if get_path(input_protocol, path) is None
            ]

    unresolved = []
    if mode == "reproduction":
        for path in REQUIRED_REPRODUCTION:
            if get_path(input_protocol, path) is None:
                unresolved.append(".".join(path))

    field_sources = {}

    def record(value, prefix=""):
        if isinstance(value, dict):
            for key, sub in value.items():
                record(sub, f"{prefix}.{key}" if prefix else key)
        else:
            field_sources[prefix] = source_map.get(prefix, "default_protocol")

    record(resolved)
    result = {
        "status": "PASS" if not unresolved else "PROTOCOL_UNRESOLVED",
        "mode": mode,
        "resolved": resolved,
        "field_sources": field_sources,
        "DEFAULT_FILLED": filled,
        "unresolved_required": unresolved,
        "literature_source": input_protocol.get("source")
        or input_protocol.get("reference")
        or raw.get("literature_reference"),
        "execution_policy": (
            "resolved protocol is required before MDP generation; literature values "
            "override defaults only when explicitly supplied; every fallback is listed"
        ),
    }
    dump_json(result, args.out)
    print(result["status"])
    return 0 if not unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
