#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, load_data
from structure_adapter import extract_structure


def _not_set(value) -> bool:
    return value in (None, "", "TODO", "NOT_REPORTED")


def _as_options(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    raise ValueError("qm.route_options must be a string or list")


def _protocol_values(path: str | None) -> dict:
    if not path:
        return {}
    payload = load_data(path) or {}
    if isinstance(payload.get("resolved"), dict):
        return payload["resolved"]
    return payload


def _qm_values(cfg: dict, protocol: dict) -> dict:
    # A resolved literature protocol has precedence over the raw user config.
    qm = {}
    if isinstance(cfg.get("qm"), dict):
        qm.update(cfg["qm"])
    if isinstance(cfg.get("literature_protocol"), dict) and isinstance(
        cfg["literature_protocol"].get("qm"), dict
    ):
        qm.update(cfg["literature_protocol"]["qm"])
    if isinstance(protocol.get("qm"), dict):
        qm.update(protocol["qm"])
    for key in (
        "method",
        "basis",
        "functional",
        "dispersion",
        "solvent_model",
        "route",
        "route_options",
        "charge",
        "multiplicity",
        "geometry",
    ):
        if key in cfg and key not in qm:
            qm[key] = cfg[key]
    return qm


def _route(qm: dict) -> tuple[str | None, list[str], list[str]]:
    unresolved: list[str] = []
    warnings: list[str] = []
    method = qm.get("method")
    functional = qm.get("functional")
    basis = qm.get("basis")
    route_method = qm.get("route_method") or functional or method
    if _not_set(route_method):
        unresolved.append("qm.method_or_functional")
    if _not_set(basis):
        unresolved.append("qm.basis")

    explicit_route = qm.get("route")
    if _not_set(explicit_route):
        options = _as_options(qm.get("route_options"))
        route = None if unresolved else f"#p {route_method}/{basis}"
        if route is not None and options:
            route += " " + " ".join(options)
    else:
        route = str(explicit_route).strip()
        if not route.startswith("#"):
            route = "#p " + route
        options = _as_options(qm.get("route_options"))
        if options:
            route += " " + " ".join(options)

    dispersion = qm.get("dispersion")
    if not _not_set(dispersion) and str(dispersion).lower() not in (
        "none",
        "off",
        "no",
    ):
        if route is None or (
            "dispersion" not in route.lower() and "d3" not in route.lower()
        ):
            unresolved.append("qm.dispersion: encode it in qm.route or qm.route_options")
    solvent = qm.get("solvent_model")
    if not _not_set(solvent) and str(solvent).lower() not in (
        "none",
        "gas",
        "vacuum",
    ):
        if route is None or "scrf" not in route.lower():
            unresolved.append(
                "qm.solvent_model: encode it in qm.route or qm.route_options"
            )
    if functional and method and str(functional).lower() != str(method).lower():
        warnings.append(
            "qm.functional differs from qm.method; route_method/functional was used explicitly"
        )
    return route, unresolved, warnings


def _confirmation_matches(path: str | None, source_sha256: str) -> bool:
    if not path:
        return False
    confirmation = load_data(path) or {}
    confirmed = confirmation.get("confirmed") is True or confirmation.get("status") in (
        "CONFIRMED",
        "PASS",
    )
    return bool(confirmed and confirmation.get("source_sha256") == source_sha256)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--resolved-protocol")
    ap.add_argument("--structure", help="XYZ, MOL V2000, SDF V2000, or PDB input")
    ap.add_argument("--structure-confirmation", help="sidecar with status and source_sha256")
    ap.add_argument("--connectivity-approved", action="store_true")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    if not args.config and not args.resolved_protocol:
        ap.error("one of --config or --resolved-protocol is required")

    cfg = (load_data(args.config) or {}) if args.config else {}
    protocol = _protocol_values(args.resolved_protocol)
    qm = _qm_values(cfg, protocol)
    unresolved: list[str] = []
    warnings: list[str] = []
    structure_record = None

    if args.structure:
        try:
            structure_record = extract_structure(Path(args.structure))
            if not qm.get("geometry"):
                qm["geometry"] = structure_record["geometry"]
            if not _confirmation_matches(
                args.structure_confirmation, structure_record["source_sha256"]
            ):
                unresolved.append("structure_confirmation")
            connectivity_approved = args.connectivity_approved or bool(
                cfg.get("connectivity_approved")
            )
            if (
                not structure_record["connectivity_in_file"]
                and not connectivity_approved
            ):
                unresolved.append("connectivity_review")
        except (OSError, ValueError) as exc:
            unresolved.append("structure_input")
            warnings.append(str(exc))

    geometry = qm.get("geometry") or cfg.get("geometry")
    charge = qm.get("charge", cfg.get("charge"))
    multiplicity = qm.get("multiplicity", cfg.get("multiplicity"))
    route, route_unresolved, route_warnings = _route(qm)
    unresolved.extend(route_unresolved)
    warnings.extend(route_warnings)
    for key, value in (
        ("geometry", geometry),
        ("charge", charge),
        ("multiplicity", multiplicity),
    ):
        if _not_set(value):
            unresolved.append(key)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "PLAN_ONLY" if unresolved else "PASS",
        "config": str(args.config) if args.config else None,
        "resolved_protocol": str(args.resolved_protocol)
        if args.resolved_protocol
        else None,
        "structure": structure_record,
        "qm": qm,
        "unresolved": sorted(set(unresolved)),
        "warnings": warnings,
        "policy": (
            "No QM method, basis, route option, solvent model, dispersion, geometry, "
            "charge, multiplicity, connectivity, or structure identity is guessed."
        ),
    }
    if route:
        result["route"] = route
    if not unresolved:
        gjf = (
            "%chk=job.chk\n"
            f"{route}\n\n"
            "approved input\n\n"
            f"{charge} {multiplicity}\n\n"
            f"{geometry}\n"
        )
        (out / "job.gjf").write_text(gjf, encoding="utf-8")
        result["input"] = str(out / "job.gjf")
    else:
        result["reason"] = (
            "Supply a confirmed structure and explicit identity/QM settings before "
            "Gaussian execution; use the Gaussian molecule workflow for prepare/confirm."
        )
    dump_json(result, out / "gaussian_plan.json")
    print(result["status"])
    return 0 if not unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
