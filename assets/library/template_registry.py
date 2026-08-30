"""Safe access to the public CP2K-version-bound template archive."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


SKILL_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = SKILL_ROOT / "assets"
REGISTRY_PATH = ASSET_ROOT / "template_registry.json"
_TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class RegistryError(ValueError):
    """Raised when a version/workflow is not in the controlled registry."""


def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    """Load a registry without modifying it."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError("template registry is missing: %s" % path) from exc
    if not isinstance(data, dict) or "templates" not in data:
        raise RegistryError("invalid template registry: %s" % path)
    return data


def _template_record(version: str, workflow: str, registry: Mapping[str, Any]) -> str:
    versions = registry.get("templates", {})
    if version not in versions:
        raise RegistryError("unsupported CP2K version: %s" % version)
    record = versions[version].get(workflow)
    if record is None:
        raise RegistryError("no template for %s/%s" % (version, workflow))
    if isinstance(record, str):
        return record
    if isinstance(record, dict) and isinstance(record.get("path"), str):
        return record["path"]
    raise RegistryError("invalid template record for %s/%s" % (version, workflow))


def get_template(
    version: str,
    workflow: str,
    registry: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Return a registered template path for an exact CP2K version/workflow."""

    active = registry if registry is not None else load_registry()
    relative = _template_record(version, workflow, active)
    path = (ASSET_ROOT / relative).resolve()
    try:
        path.relative_to(ASSET_ROOT.resolve())
    except ValueError as exc:
        raise RegistryError("template path escapes the asset directory: %s" % relative) from exc
    if not path.is_file():
        raise RegistryError("registered template is missing: %s" % path)
    return path


def list_templates(
    version: Optional[str] = None,
    registry: Optional[Mapping[str, Any]] = None,
) -> Iterable[Dict[str, str]]:
    """List registered templates; the result is deterministic and read-only."""

    active = registry if registry is not None else load_registry()
    versions = active.get("templates", {})
    selected = [version] if version is not None else sorted(versions)
    rows = []
    for item in selected:
        if item not in versions:
            raise RegistryError("unsupported CP2K version: %s" % item)
        for workflow in sorted(versions[item]):
            rows.append(
                {
                    "version": item,
                    "workflow": workflow,
                    "path": _template_record(item, workflow, active),
                }
            )
    return rows


def render_slots(template_text: str, values: Mapping[str, Any]) -> str:
    """Render only explicit ``{{UPPER_CASE_SLOT}}`` tokens.

    No expression evaluation or arbitrary formatting is performed.  Missing
    slots and unresolved slots are hard errors so an unfinished template can
    never be submitted as a CP2K input by accident.
    """

    required = sorted(set(_TOKEN.findall(template_text)))
    missing = [token for token in required if token not in values]
    if missing:
        raise RegistryError("missing template slots: %s" % ", ".join(missing))

    rendered = template_text
    for token in required:
        replacement = str(values[token])
        rendered = rendered.replace("{{%s}}" % token, replacement)
    unresolved = sorted(set(_TOKEN.findall(rendered)))
    if unresolved:
        raise RegistryError("unresolved template slots: %s" % ", ".join(unresolved))
    return rendered


def render_template(
    version: str,
    workflow: str,
    values: Mapping[str, Any],
    registry: Optional[Mapping[str, Any]] = None,
) -> str:
    """Read and render one registered template with strict slot handling."""

    path = get_template(version, workflow, registry=registry)
    return render_slots(path.read_text(encoding="utf-8"), values)
