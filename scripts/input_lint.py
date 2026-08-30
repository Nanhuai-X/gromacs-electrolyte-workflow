#!/usr/bin/env python3
"""Static CP2K input lint; never substitutes for an executable smoke test."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SECTION_OPEN = re.compile(r"^\s*&([A-Za-z_][A-Za-z0-9_]*)\b", re.I)
SECTION_END = re.compile(r"^\s*&END(?:\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$", re.I)


def clean(line: str) -> str:
    return line.split("!", 1)[0].strip()


def _has_nested_section(text: str, parent: str, child: str) -> bool:
    """Return whether *child* is opened directly inside *parent*."""

    stack: List[str] = []
    for raw in text.splitlines():
        line = clean(raw)
        end_match = SECTION_END.match(line)
        if end_match:
            if stack:
                stack.pop()
            continue
        open_match = SECTION_OPEN.match(line)
        if not open_match:
            continue
        name = open_match.group(1).upper()
        if stack and stack[-1] == parent.upper() and name == child.upper():
            return True
        stack.append(name)
    return False


def _has_direct_keyword(text: str, section: str, keyword: str) -> bool:
    """Return whether a keyword appears directly in a named section."""

    stack: List[str] = []
    target = section.upper()
    expected = keyword.upper()
    for raw in text.splitlines():
        line = clean(raw)
        end_match = SECTION_END.match(line)
        if end_match:
            if stack:
                stack.pop()
            continue
        open_match = SECTION_OPEN.match(line)
        if open_match:
            stack.append(open_match.group(1).upper())
            continue
        if stack and stack[-1] == target:
            name = line.split(None, 1)[0].upper() if line else ""
            if name == expected:
                return True
    return False


def lint_text(text: str, version: Optional[str] = None) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    stack: List[str] = []
    top_level: Dict[str, int] = {}
    lines = text.splitlines()

    unresolved = sorted(set(re.findall(r"\{\{[^}]+\}\}", text)))
    if unresolved:
        errors.append("unresolved template tokens: " + ", ".join(unresolved))
    if re.search(r"\bIGNORE_CONVERGENCE_FAILURE\b", text, re.I):
        errors.append("IGNORE_CONVERGENCE_FAILURE is forbidden")

    for number, raw in enumerate(lines, start=1):
        line = clean(raw)
        if not line or line.startswith("#"):
            continue
        end_match = SECTION_END.match(line)
        if end_match:
            if not stack:
                errors.append(f"line {number}: unmatched &END")
                continue
            declared = (end_match.group(1) or "").upper()
            opened = stack.pop()
            if declared and declared != opened:
                errors.append(f"line {number}: &END {declared} closes &{opened}")
            continue
        open_match = SECTION_OPEN.match(line)
        if open_match:
            name = open_match.group(1).upper()
            stack.append(name)
            if len(stack) == 1:
                top_level[name] = top_level.get(name, 0) + 1

    if stack:
        errors.append("unclosed sections: " + ", ".join("&" + item for item in stack))
    if top_level.get("GLOBAL", 0) > 1:
        errors.append("duplicate top-level GLOBAL section")
    if top_level.get("FORCE_EVAL", 0) > 1:
        errors.append("duplicate top-level FORCE_EVAL section")
    upper = text.upper()
    for required in ("&GLOBAL", "&FORCE_EVAL", "&SUBSYS"):
        if required not in upper:
            errors.append(f"missing required section {required}")

    normalized_version = (version or "").lower()
    if normalized_version.startswith("2024"):
        if _has_direct_keyword(text, "DOS", "NLUMO"):
            errors.append("2024.x trap: NLUMO must not be placed directly in PRINT/DOS")
        if _has_nested_section(text, "DOS", "CURVE"):
            errors.append("2024.x trap: nested DOS/CURVE layout is not accepted by this project profile")
        if _has_nested_section(text, "DOS", "PDOS"):
            errors.append("2024.x trap: nested DOS/PDOS layout is not accepted by this project profile")
        if re.search(r"\bOT\b", upper) and re.search(r"\bADDED_MOS\b", upper):
            errors.append("2024.x trap: OT and ADDED_MOS combination requires a validated alternate recipe")
    if "&FORCE_EVAL" in upper and "&DFT" not in upper:
        warnings.append("FORCE_EVAL has no visible DFT section; validate the intended run type")
    return {
        "schema_version": "1.0",
        "valid": not errors,
        "version": version,
        "line_count": len(lines),
        "sections": top_level,
        "errors": errors,
        "warnings": warnings,
        "static_only": True,
        "smoke_test_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = lint_text(args.input.read_text(encoding="utf-8"), args.version)
    payload = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if record["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
