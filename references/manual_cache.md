# Manual cache and exact-version manifest

The manual is a versioned scientific dependency. Do not use an unversioned
blog, a remembered keyword, or a template from another CP2K release as the
authority for a formal input.

## Cache layout

```text
manual_cache/
  2024.1/
    manual_manifest.yaml
    CP2K_INPUT.html
    sections/
  2026.2/
    manual_manifest.yaml
    CP2K_INPUT.html
    sections/
```

The cache is optional for a smoke test, but required before claiming a formal
workflow is version validated. The resolver must record the URL, branch,
retrieval time, content hash, CP2K binary version, and sections consulted. If
network access is unavailable, return `MANUAL_REQUIRED` and do not claim the
syntax is validated.

Keep the cache in the user's calculation or runtime directory rather than in a
shared/public skill checkout. Pass `--cache-root <runtime-directory>` explicitly
when the calling agent's working directory is ambiguous.

## Manifest example

```yaml
schema_version: "1.0"
cp2k_version: "2024.1"
manual_url: "https://manual.cp2k.org/cp2k-2024_1-branch/CP2K_INPUT.html"
manual_branch: "cp2k-2024_1-branch"
retrieved_at_utc: "..."
content_sha256: "..."
sections:
  - path: "FORCE_EVAL/DFT/PRINT/DOS"
    purpose: "DOS syntax"
    local_file: "sections/dos.md"
  - path: "FORCE_EVAL/DFT/PRINT/PDOS"
    purpose: "PDOS syntax"
    local_file: "sections/pdos.md"
keywords_checked:
  - "SCF"
  - "ADDED_MOS"
  - "ELF_CUBE"
  - "E_DENSITY_CUBE"
template_registry_hash: "..."
binary_smoke_test:
  executable: "..."
  version_output_sha256: "..."
  status: "PASS|FAIL"
```

`manual_manifest.yaml` is evidence metadata. It does not grant permission to
skip an executable smoke test. A template is eligible for submission only
when the declared CP2K version, manual branch, template registry entry, and
local lint/smoke evidence agree.

## Version split used by this package

The project intentionally keeps the 2024.1 legacy DOS/PDOS sibling-print
layout separate from the 2026.2 nested DOS/CURVE/PDOS layout. The full details
and known regressions are in `cp2k_2024.md`, `cp2k_2026.md`, and the copied
`assets/template_registry.json`.
