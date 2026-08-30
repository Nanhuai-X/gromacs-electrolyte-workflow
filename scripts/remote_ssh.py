#!/usr/bin/env python3
"""Secure SSH preflight and read-only remote command helper.

The helper requires an explicit known_hosts file. It never prints private-key
contents and never auto-accepts a new host key.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def quote_command(parts: List[str]) -> str:
    # shlex.join is unavailable in the Python 3.7 runtime used by this project.
    return " ".join(shlex.quote(part) for part in parts)


def validate_ssh_inputs(
    host: str, user: str, key: Path, port: int, known_hosts: Optional[Path]
) -> Dict[str, Any]:
    if not host or any(character.isspace() for character in host):
        raise ValueError("host is required and must not contain whitespace")
    if not user or any(character.isspace() for character in user):
        raise ValueError("user is required and must not contain whitespace")
    if not key.is_file() or key.stat().st_size == 0:
        raise ValueError("private key file is missing or empty")
    if not known_hosts or not known_hosts.is_file() or known_hosts.stat().st_size == 0:
        raise ValueError("known_hosts file is required for strict host-key verification")
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return {
        "host": host,
        "user": user,
        "port": port,
        "key_path": str(key.resolve()),
        "known_hosts_path": str(known_hosts.resolve()),
        "secret_content_collected": False,
    }


def build_ssh_command(
    host: str, user: str, key: Path, port: int, known_hosts: Path, remote_command: List[str]
) -> List[str]:
    validate_ssh_inputs(host, user, key, port, known_hosts)
    command = [
        "ssh",
        "-i",
        str(key),
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        f"{user}@{host}",
    ]
    if remote_command:
        command.append(quote_command(remote_command))
    return command


def run_remote(
    host: str,
    user: str,
    key: Path,
    port: int,
    known_hosts: Path,
    remote_command: List[str],
    timeout: float = 30.0,
) -> Dict[str, Any]:
    command = build_ssh_command(host, user, key, port, known_hosts, remote_command)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "SSH_TIMEOUT", "returncode": None, "stdout": "", "stderr": ""}
    return {
        "status": "PASS" if result.returncode == 0 else "SSH_COMMAND_FAILED",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command_metadata": {
            "host": host,
            "user": user,
            "port": port,
            "remote_command": remote_command,
            "strict_host_key_checking": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--remote-dir", default=None)
    parser.add_argument("--command", nargs="*")
    args = parser.parse_args()
    remote_command = args.command or ["hostname"]
    if args.remote_dir:
        remote_command = ["bash", "-lc", f"cd {shlex.quote(args.remote_dir)} && {quote_command(remote_command)}"]
    try:
        result = run_remote(args.host, args.user, args.key, args.port, args.known_hosts, remote_command)
    except ValueError as exc:
        result = {"status": "SSH_CONFIGURATION_ERROR", "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
