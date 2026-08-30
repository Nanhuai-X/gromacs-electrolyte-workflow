#!/usr/bin/env python3
"""Fetch and hash only the exact official CP2K manual branch."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


OFFICIAL_HOST = "manual.cp2k.org"


def validate_manual_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == OFFICIAL_HOST and parsed.path.endswith("/CP2K_INPUT.html")


def validate_official_url(url: str) -> bool:
    """Allow the index and section pages below the official CP2K manual host."""

    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == OFFICIAL_HOST
        and "/CP2K_INPUT" in parsed.path
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_official(url: str) -> bytes:
    if not validate_official_url(url):
        raise ValueError("manual URL is outside the official CP2K HTTPS allowlist")
    request = Request(url, headers={"User-Agent": "CP2K-Materials-Workflow/1.0"})
    with urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        if not validate_official_url(final_url):
            raise ValueError("official manual request redirected outside the allowed CP2K host")
        return response.read()


def section_url(base_url: str, section: str) -> str:
    """Convert a relative CP2K_INPUT section path into an official URL."""

    relative = safe_section_path(section).strip("/")
    if not relative.startswith("CP2K_INPUT/"):
        relative = "CP2K_INPUT/" + relative
    if not relative.endswith(".html"):
        relative += ".html"
    return urljoin(base_url, relative)


def safe_section_path(section: str) -> str:
    parsed = urlparse(section)
    if parsed.scheme or parsed.netloc or section.startswith("/") or ".." in Path(section).parts:
        raise ValueError("section must be a relative official-manual path")
    return section.replace("\\", "/")


def load_registry(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cache_manual(
    version: str,
    registry_path: Path,
    cache_root: Path,
    force: bool = False,
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    registry = load_registry(registry_path)
    record = registry.get("versions", {}).get(version)
    if not record:
        raise ValueError(f"unsupported CP2K version: {version}")
    url = record.get("manual_url")
    if not url or not validate_manual_url(url):
        raise ValueError("registry manual URL is not an allowed official CP2K URL")
    destination = cache_root / version
    html_path = destination / "CP2K_INPUT.html"
    manifest_path = destination / "manual_manifest.yaml"
    if (html_path.exists() or manifest_path.exists()) and not force:
        return {"status": "EXISTS", "version": version, "cache_root": str(destination)}

    data = fetch_official(url)
    destination.mkdir(parents=True, exist_ok=True)
    html_path.write_bytes(data)
    cached_sections = []
    for section in sections or []:
        relative = safe_section_path(section)
        section_link = section_url(url, relative)
        section_data = fetch_official(section_link)
        section_file = destination / "sections" / relative
        section_file.parent.mkdir(parents=True, exist_ok=True)
        section_file.write_bytes(section_data)
        cached_sections.append(
            {
                "requested": section,
                "url": section_link,
                "local_file": str(section_file.relative_to(destination)),
                "sha256": sha256_bytes(section_data),
            }
        )
    manifest = {
        "schema_version": "1.0",
        "cp2k_version": version,
        "manual_url": url,
        "manual_branch": url.rstrip("/").split("/")[-2],
        "manual_git_revision": record.get("manual_git_revision"),
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "content_sha256": sha256_bytes(data),
        "status": "CACHED" if cached_sections else "CACHED_INDEX",
        "sections": cached_sections,
        "keywords_checked": [],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--version", required=True)
    parser.add_argument("--registry", type=Path, default=root / "assets" / "template_registry.json")
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.cwd() / "manual_cache",
        help="runtime cache directory (default: ./manual_cache in the caller's working directory)",
    )
    parser.add_argument("--section", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        record = cache_manual(args.version, args.registry, args.cache_root, args.force, args.section)
    except Exception as exc:
        print(json.dumps({"status": "MANUAL_FETCH_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
