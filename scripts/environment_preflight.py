#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
from pathlib import Path

from common import dump_json, load_data, run_capture

def executable(path: str | Path | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    return str(p) if p.is_file() and os.access(p, os.X_OK) else None


def probe(path: str | None, args: list[str]) -> dict:
    if not path:
        return {"available": False, "path": None}
    try:
        result = run_capture([path, *args])
        return {
            "available": True,
            "probe_ok": result["returncode"] == 0,
            "path": path,
            "returncode": result["returncode"],
            "stdout": result["stdout"][-3000:],
            "stderr": result["stderr"][-3000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": path, "error": str(exc)}


def filesystem_type(project: Path) -> str | None:
    try:
        lines = subprocess.run(
            ["df", "-T", str(project)], text=True, capture_output=True, check=False
        ).stdout.splitlines()
        if len(lines) >= 2:
            return lines[-1].split()[1]
    except OSError:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--project-root",
        default=os.environ.get("GROMACS_PROJECT_ROOT"),
        help="configured control/provenance root; defaults to GROMACS_PROJECT_ROOT",
    )
    ap.add_argument(
        "--config",
        help="optional YAML/JSON config containing system.execution_root",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    project_root = args.project_root
    if not project_root and args.config:
        config = load_data(args.config) or {}
        system = config.get("system") if isinstance(config.get("system"), dict) else {}
        project_root = system.get("execution_root")
    if project_root in ("", "TODO", "null"):
        project_root = None
    if not project_root:
        result = {
            "status": "PROJECT_ROOT_REQUIRED",
            "project_root": None,
            "is_wsl": False,
            "filesystem_type": None,
            "tools": {},
            "optional_quantum": {},
            "missing_core": ["project_root"],
            "configuration_policy": (
                "Pass --project-root or set GROMACS_PROJECT_ROOT; no machine-specific "
                "control-root fallback is used."
            ),
            "setup_plan": {
                "actions_if_missing": [
                    "configure the control/provenance root explicitly",
                    "rerun environment_preflight.py after the root is available",
                ]
            },
        }
        dump_json(result, args.out)
        print(result["status"])
        return 2
    project = Path(project_root).resolve()
    release = platform.release()
    proc_version = (
        Path("/proc/version").read_text(errors="replace")
        if Path("/proc/version").exists()
        else ""
    )
    is_wsl = (
        "microsoft" in release.lower()
        or "wsl" in release.lower()
        or "microsoft" in proc_version.lower()
    )
    fs = filesystem_type(project)

    gmx_path = shutil.which("gmx")
    cpu_gmx = executable(os.environ.get("GMX_CPU_BIN")) or gmx_path
    cuda_gmx = executable(os.environ.get("GMX_CUDA_BIN"))
    nvcc_path = (
        shutil.which("nvcc")
        or executable(os.environ.get("CUDA_NVCC"))
    )
    packmol_path = (
        shutil.which("packmol")
        or executable(project / ".venv" / "bin" / "packmol")
        or executable(project / ".venv" / "Scripts" / "packmol.exe")
    )
    python_path = (
        shutil.which("python3")
        or shutil.which("python")
        or executable(project / ".venv" / "bin" / "python")
        or executable(project / ".venv" / "Scripts" / "python.exe")
    )
    tools = {
        "gmx_path": probe(gmx_path, ["--version"]),
        "gmx_cpu_prefix": probe(cpu_gmx, ["--version"]),
        "gmx_cuda_prefix": probe(cuda_gmx, ["--version"]),
        "nvcc": probe(nvcc_path, ["--version"]),
        "nvidia_smi": probe(
            shutil.which("nvidia-smi"),
            ["--query-gpu=name,driver_version", "--format=csv,noheader"],
        ),
        "packmol": probe(packmol_path, ["-h"]),
        "python3": probe(python_path, ["--version"]),
        "gcc": probe(shutil.which("gcc"), ["--version"]),
        "cmake": probe(shutil.which("cmake"), ["--version"]),
        "make": probe(shutil.which("make"), ["--version"]),
        "git": probe(shutil.which("git"), ["--version"]),
    }
    gaussian_root = os.environ.get("GAUSSIAN_RESP_WORKFLOW_ROOT")
    gaussian_root = gaussian_root if gaussian_root and Path(gaussian_root).is_dir() else None
    optional = {
        "gaussian_workflow_source": {
            "available": bool(gaussian_root),
            "path": gaussian_root,
        },
        "gaussian": probe(shutil.which("g16") or shutil.which("g09"), ["--version"]),
        "formchk": probe(shutil.which("formchk"), ["--help"]),
        "multiwfn": probe(
            shutil.which("Multiwfn") or executable(os.environ.get("MULTIWFN_BIN")),
            ["-h"],
        ),
    }
    core_names = ("python3", "gcc", "cmake", "make", "packmol")
    core_ok = (
        all(tools[name]["available"] for name in core_names)
        and bool(cpu_gmx or cuda_gmx)
    )
    missing_core = [name for name in core_names if not tools[name]["available"]]
    if not cpu_gmx and not cuda_gmx:
        missing_core.append("gromacs_cpu_or_cuda_prefix")
    status = (
        "PASS"
        if is_wsl and fs == "ext4" and core_ok
        else ("PASS_WITH_LIMITATIONS" if core_ok else "ENVIRONMENT_BLOCKED")
    )
    result = {
        "status": status,
        "project_root": str(project),
        "is_wsl": is_wsl,
        "kernel": release,
        "filesystem_type": fs,
        "tools": tools,
        "optional_quantum": optional,
        "missing_core": sorted(set(missing_core)),
        "configuration_policy": (
            "Backend-specific; inspect configured binaries and virtualenv before any "
            "install; no automatic sudo/apt/pip action"
        ),
        "setup_plan": {
            "source_cpu_environment": str(project / "scripts/env_gromacs_cpu.sh"),
            "source_cuda_environment": str(project / "scripts/env_gromacs_cuda.sh"),
            "source_python_environment": str(project / ".venv/bin/activate"),
            "source_python_environment_windows": str(project / ".venv/Scripts/activate"),
            "actions_if_missing": [
                "repair PATH by sourcing the existing project environment loader",
                "if a core binary is truly absent, stop and produce an approved installation plan",
                "do not install a second GROMACS or ignore WSL-installed binaries",
            ],
        },
    }
    dump_json(result, args.out)
    print(status)
    return 0 if status != "ENVIRONMENT_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
