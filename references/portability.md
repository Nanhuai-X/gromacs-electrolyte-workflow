# Portability across agent hosts

## Source of truth

The portable contract is the root `SKILL.md`. Scripts are ordinary Python
entry points and use explicit command-line arguments. JSON, YAML, and Markdown
files are human-readable artifacts. No script requires a plugin, hook, slash
command, model-specific tool, or persistent agent session.

## Invocation pattern

An agent should:

1. read `SKILL.md`;
2. read only the reference file needed for the active branch;
3. invoke scripts with an absolute path when the current working directory is
   not the skill root;
4. retain stdout/stderr and generated JSON as provenance;
5. ask the user before external submission or any other remote mutation.

Hosts with a native skill directory can copy the complete folder. Hosts without
one can use the root file as an instruction document. `agents/openai.yaml` is
optional metadata and must not be treated as a dependency.

## Runtime assumptions

- Python 3.9 or newer is recommended.
- Core orchestration uses the standard library.
- `ase`, `pymatgen`, `spglib`, `numpy`, `psutil`, and `pypdf` are optional;
  missing optional support must be reported as `NOT_VALIDATED`.
- CP2K, a scheduler, and an SSH client are external programs and are never
  installed or guessed by this package.

## Path and secret rules

Use `pathlib` and explicit paths. Keep project output, downloaded manual caches,
local adapters, private keys, `known_hosts`, scheduler credentials, and site
configuration outside the public skill directory. Never print secret contents.
