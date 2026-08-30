#!/usr/bin/env python3
"""Render one registry-approved template and run the static input lint."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict

from input_lint import lint_text


TOKEN = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


def read_values(value: str) -> Dict[str, Any]:
    candidate = Path(value)
    try:
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        else:
            payload = json.loads(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"values must be a JSON object or a readable JSON file: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("values JSON must contain an object")
    return payload


def resolve_template(template_root: Path, relative: str, version: str) -> Path:
    """Resolve a registry path while allowing older registry family names."""

    root = template_root.resolve()
    candidates = [root / relative]
    family = "templates_" + version.split(".", 1)[0]
    candidates.append(root / family / Path(relative).name)
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    raise SystemExit(f"template not found for {version}: {relative}")


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--values-json", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=skill_root / "assets" / "template_registry.json")
    parser.add_argument("--template-root", type=Path, default=skill_root / "assets")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    version_templates = registry.get("templates", {}).get(args.version)
    if version_templates is None:
        raise SystemExit(f"no registry entry for CP2K {args.version}")
    relative = version_templates.get(args.workflow)
    if not relative:
        raise SystemExit(f"workflow {args.workflow!r} is not registered for {args.version}")
    if not str(relative).endswith(".template"):
        raise SystemExit(f"workflow {args.workflow!r} is a workflow manifest, not a renderable input template")

    template = resolve_template(args.template_root, str(relative), args.version)
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing output: {args.output}; use --force explicitly")

    values = read_values(args.values_json)
    rendered = template.read_text(encoding="utf-8")
    missing = []
    for match in sorted(set(TOKEN.findall(rendered))):
        if match not in values:
            missing.append(match)
        else:
            rendered = rendered.replace("{{" + match + "}}", str(values[match]))
    if missing:
        print(json.dumps({"status": "INPUT_NOT_WRITTEN", "missing_values": missing}, indent=2, sort_keys=True))
        return 2
    lint = lint_text(rendered, args.version)
    if not lint["valid"]:
        print(json.dumps({"status": "INPUT_NOT_WRITTEN", "lint": lint}, indent=2, sort_keys=True))
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    result = {
        "status": "WRITTEN",
        "version": args.version,
        "workflow": args.workflow,
        "template": str(template),
        "output": str(args.output),
        "lint": lint,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
