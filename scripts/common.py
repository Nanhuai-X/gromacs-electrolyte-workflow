#!/usr/bin/env python3
from __future__ import annotations
import csv
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any, Iterable

def load_data(path: str | Path) -> Any:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError as exc:
        raise RuntimeError("YAML input requires PyYAML; use JSON for a stdlib-only run") from exc

def dump_json(data: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def run_capture(argv: list[str], cwd: str | Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(argv, cwd=cwd, text=True, errors="replace", capture_output=True, check=False)
    return {"argv": argv, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

def read_table(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def write_table(rows: list[dict[str, Any]], path: str | Path, fieldnames: list[str] | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with p.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False

def mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return float("nan")
    fmean = getattr(statistics, "fmean", None)
    return fmean(vals) if callable(fmean) else statistics.mean(vals)

def stdev(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    return statistics.stdev(vals) if len(vals) > 1 else 0.0

def linear_fit(x: Iterable[float], y: Iterable[float]) -> tuple[float, float, float]:
    xs, ys = [float(v) for v in x], [float(v) for v in y]
    if len(xs) != len(ys) or len(xs) < 2:
        return float("nan"), float("nan"), float("nan")
    xm, ym = mean(xs), mean(ys)
    den = sum((a - xm) ** 2 for a in xs)
    if den == 0:
        return float("nan"), ym, float("nan")
    slope = sum((a - xm) * (b - ym) for a, b in zip(xs, ys)) / den
    intercept = ym - slope * xm
    ss_tot = sum((b - ym) ** 2 for b in ys)
    ss_res = sum((b - (slope * a + intercept)) ** 2 for a, b in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return slope, intercept, r2

def read_xvg(path: str | Path) -> list[list[float]]:
    rows = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line[0] in "#@":
            continue
        try:
            rows.append([float(part) for part in line.split()])
        except ValueError:
            continue
    return rows
