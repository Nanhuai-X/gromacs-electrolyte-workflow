#!/usr/bin/env python3
"""Require an explicit user choice before execution parameters become active."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, Optional


def approve_plan(
    plan: Dict[str, Any], choice: str, confirmed: bool, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if not confirmed:
        raise ValueError("explicit user confirmation is required before execution")
    if plan.get("status") != "USER_CONFIRMATION_REQUIRED":
        raise ValueError("parameter plan is not awaiting confirmation")
    if choice not in plan.get("candidates", {}):
        raise ValueError(f"unknown parameter candidate: {choice}")
    candidate = dict(plan["candidates"][choice])
    overrides = dict(overrides or {})
    unresolved = set(candidate.get("unresolved_values", []))
    missing = unresolved - set(overrides)
    if missing:
        raise ValueError("candidate still has unresolved numerical values: " + ", ".join(sorted(missing)))
    if overrides:
        candidate["confirmed_values"] = overrides
        candidate["unresolved_values"] = sorted(unresolved - set(overrides))
    if candidate.get("unresolved_values"):
        raise ValueError("candidate still has unresolved numerical values")
    return {
        "schema_version": "1.0",
        "approved": True,
        "approved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "choice": choice,
        "candidate": candidate,
        "source_plan": plan,
        "execution_allowed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--choice", required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--overrides-json", default="{}")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    try:
        overrides = json.loads(args.overrides_json)
        if isinstance(overrides, str) and Path(overrides).is_file():
            overrides = json.loads(Path(overrides).read_text(encoding="utf-8"))
        result = approve_plan(plan, args.choice, args.confirm, overrides)
    except ValueError as exc:
        print(json.dumps({"status": "PARAMETER_CONFIRMATION_REQUIRED", "error": str(exc)}, indent=2))
        return 3
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
