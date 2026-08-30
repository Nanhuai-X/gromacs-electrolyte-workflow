#!/usr/bin/env python3
"""Extract parameter observations and build user-confirmation candidates.

The script never silently adopts a literature value. It records observations,
their source, and three cost/accuracy candidates that remain blocked until the
user confirms one.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


PATTERNS = {
    "kpoints": r"(?i)(?:k[- ]?points?|mesh|网格)\D{0,20}(\d+\s*[xX*]\s*\d+\s*[xX*]\s*\d+)",
    "cutoff_ry": r"(?i)(?:cut[- ]?off|截断)\D{0,20}(\d+(?:\.\d+)?)\s*(?:ry|rydberg)",
    "rel_cutoff_ry": r"(?i)(?:rel[_ -]?cutoff|相对截断)\D{0,20}(\d+(?:\.\d+)?)\s*(?:ry|rydberg)",
    "eps_scf": r"(?i)(?:eps[_ -]?scf|scf\s*tolerance|scf\s*threshold|残差)\D{0,20}(\d+(?:\.\d+)?[Ee][+-]?\d+)",
    "max_scf": r"(?i)(?:max[_ -]?scf|maximum\s*scf)\D{0,20}(\d+)",
    "smearing": r"(?i)(?:smearing|展宽|sigma)\D{0,20}(\d+(?:\.\d+)?)\s*(?:ev|电子伏)?",
    "basis": r"(?i)(?:basis[_ -]?set|基组)\D{0,30}([A-Z0-9][A-Z0-9_.+-]{3,})",
    "functional": r"(?i)\b(PBE0|HSE06|BLYP|PBE|SCAN|\w+D3(?:\(BJ\))?)\b",
    "geometry_force": r"(?i)(?:max[_ -]?force|最大力)\D{0,20}(\d+(?:\.\d+)?[Ee][+-]?\d+|\d+(?:\.\d+)?)",
}


def read_reference(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in {".txt", ".md", ".rst", ".yaml", ".yml"}:
        return source.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            return "\n".join(page.extract_text() or "" for page in PdfReader(str(source)).pages)
        except ImportError:
            return ""
    return ""


def extract_observations(source: Path) -> List[Dict[str, Any]]:
    text = read_reference(source)
    observations: List[Dict[str, Any]] = []
    if not text:
        return [{"source": str(source), "status": "TEXT_EXTRACTION_UNAVAILABLE", "observations": []}]
    for name, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 100)
            stop = min(len(text), match.end() + 100)
            observations.append(
                {
                    "source": str(source),
                    "parameter": name,
                    "value": match.group(1) if match.groups() else match.group(0),
                    "context": re.sub(r"\s+", " ", text[start:stop]).strip(),
                    "evidence_level": "LITERATURE_OBSERVED",
                }
            )
    return observations


def build_literature_plan(references: Iterable[Any], workflow: str, priority: str) -> Dict[str, Any]:
    references = list(references)
    observations = []
    for reference in references:
        reference_path = Path(reference)
        observations.extend(extract_observations(reference_path))
    observed = {}
    for item in observations:
        parameter = item.get("parameter")
        if parameter and parameter not in observed:
            observed[parameter] = item["value"]
    candidates = {
        "COST_EFFECTIVE": {
            "priority": "cost",
            "intent": "smallest validated numerical setup; still requires property-specific convergence",
            "observed_literature_values": observed,
            "unresolved_values": ["cutoff", "rel_cutoff", "kpoints", "eps_scf"],
        },
        "BALANCED": {
            "priority": "balanced",
            "intent": "moderate cost with explicit force/property checks",
            "observed_literature_values": observed,
            "unresolved_values": ["cutoff", "rel_cutoff", "kpoints", "eps_scf"],
        },
        "HIGH_PRECISION": {
            "priority": "accuracy",
            "intent": "tighter numerical and property validation; higher cost",
            "observed_literature_values": observed,
            "unresolved_values": ["cutoff", "rel_cutoff", "kpoints", "eps_scf"],
        },
    }
    return {
        "schema_version": "1.0",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "workflow": workflow,
        "requested_priority": priority,
        "references": [
            {
                "path": str(path),
                "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None,
            }
            for path in references
        ],
        "observations": observations,
        "candidates": candidates,
        "status": "USER_CONFIRMATION_REQUIRED",
        "execution_allowed": False,
        "note": "Literature observations inform candidates; they do not replace convergence evidence or user approval.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", action="append", required=True, help="local PDF/text path, DOI, or URL")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--priority", choices=["cost", "balanced", "accuracy"], default="balanced")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_literature_plan(args.reference, args.workflow, args.priority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
