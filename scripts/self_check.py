#!/usr/bin/env python3
"""Check the public CP2K workflow package without running CP2K."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "LICENSE",
    "agents/openai.yaml",
    "assets/template_registry.json",
    "assets/failure_regressions.json",
    "assets/values.example.json",
    "references/cp2k_2024.md",
    "references/cp2k_2026.md",
    "references/portability.md",
    "scripts/input_lint.py",
    "scripts/render_versioned_template.py",
    "scripts/compute_adsorption_energy.py",
    "scripts/subtract_cube_density.py",
    "scripts/run_cp2k.py",
    "tests/test_skill_extensions.py",
)

LOCAL_ONLY_PATH_PARTS = {
    "manual_cache",
    "project_adapters",
    "local_adapters",
}

RUNTIME_PATH_PARTS = {
    "runs",
    "calculations",
    "__pycache__",
    ".pytest_cache",
}

FORBIDDEN_TEXT_MARKERS = (
    "codex-cp2k",
    "acxhdl",
    "zif90",
    "zif108",
    "/public/home/",
    "/public/software/",
)


def _relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


def _iter_files(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*") if path.is_file())


def _validate_registry(root: Path, errors: List[str]) -> Dict[str, Any]:
    path = root / "assets" / "template_registry.json"
    if not path.is_file():
        return {}
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid template registry: {exc}")
        return {}

    if not isinstance(registry, dict):
        errors.append("template registry must be a JSON object")
        return {}
    versions = registry.get("versions", {})
    templates = registry.get("templates", {})
    if set(versions) != set(templates):
        errors.append("registry versions and template versions differ")
    for version, workflows in templates.items():
        if not isinstance(workflows, dict):
            errors.append(f"registry templates for {version} are not an object")
            continue
        for workflow, relative in workflows.items():
            if not isinstance(relative, str):
                errors.append(f"registry path for {version}/{workflow} is not a string")
                continue
            candidate = (root / "assets" / relative).resolve()
            try:
                candidate.relative_to((root / "assets").resolve())
            except ValueError:
                errors.append(f"registry path escapes assets: {version}/{workflow}")
                continue
            if not candidate.is_file():
                errors.append(f"missing registered resource: {version}/{workflow} -> {relative}")
    return registry


def check_package(root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing {relative}")

    for path in _iter_files(root):
        relative = _relative(path, root)
        parts = set(Path(relative).parts)
        local_only = parts & LOCAL_ONLY_PATH_PARTS
        runtime_only = parts & RUNTIME_PATH_PARTS
        if local_only:
            errors.append(f"local-only file is present: {relative}")
            continue
        if runtime_only:
            warnings.append(f"runtime file is present and should not be released: {relative}")
            continue
        if path.resolve() == Path(__file__).resolve():
            # The marker list below is intentionally present in this checker.
            continue
        if path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".template", ".sh"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace").lower().replace("\\", "/")
            except OSError as exc:
                errors.append(f"cannot read {relative}: {exc}")
                continue
            for marker in FORBIDDEN_TEXT_MARKERS:
                if marker in text:
                    errors.append(f"machine/project-specific marker {marker!r} in {relative}")
            if path.suffix.lower() == ".json":
                try:
                    json.loads(text)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSON in {relative}: {exc}")

    registry = _validate_registry(root, errors)
    if registry and not registry.get("workflow_status"):
        warnings.append("registry has no workflow_status evidence matrix")

    status = "PASS" if not errors else "FAIL"
    return {
        "schema_version": "1.0",
        "status": status,
        "skill_root": str(root),
        "registered_versions": sorted(registry.get("versions", {})),
        "template_families": sorted(
            _relative(path, root)
            for path in (root / "assets").glob("templates_*")
            if path.is_dir()
        ),
        "errors": errors,
        "warnings": warnings,
        "formal_cp2k_execution": "NOT_PERFORMED",
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = check_package(root)
    payload = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if record["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
