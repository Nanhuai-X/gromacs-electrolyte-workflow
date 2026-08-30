"""Static checks for CP2K input structure and known version traps.

This is deliberately not a replacement for running the exact CP2K executable.
It catches deterministic mistakes before submission and leaves executable-level
syntax and capability checks to the runner/parser gates.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


SUPPORTED_VERSIONS = ("2024.1", "2026.2")
_HEADER = re.compile(r"^\s*&([A-Za-z][A-Za-z0-9_]*)(?:\s+.*)?$")
_END = re.compile(r"^\s*&END(?:\s+([A-Za-z][A-Za-z0-9_]*))?\s*$", re.IGNORECASE)
_META = re.compile(r"^\s*!\s*(?:WORKFLOW_|CODEX_)([A-Z0-9_]+)\s*:\s*(.*?)\s*$")
_TOKEN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
_FLOAT = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?$")
_ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr",
    "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
}
_ELEMENT_KEYS = {item.upper() for item in _ELEMENTS}
_REPEATABLE_KEYWORDS = {
    "BASIS_SET_FILE_NAME",
    "POTENTIAL_FILE_NAME",
    "SPECIAL_POINT",
}
_REPEATABLE_SECTIONS = {"FORCE_EVAL", "KIND", "KPOINT_SET", "CONSTRAINT", "RESTRAINT"}


@dataclass(frozen=True)
class Diagnostic:
    level: str
    code: str
    message: str
    line: Optional[int] = None
    path: Tuple[str, ...] = ()

    def as_dict(self) -> Dict[str, object]:
        result: Dict[str, object] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.line is not None:
            result["line"] = self.line
        if self.path:
            result["path"] = "/".join(self.path)
        return result


@dataclass(frozen=True)
class ValidationResult:
    version: Optional[str]
    workflow: Optional[str]
    diagnostics: Tuple[Diagnostic, ...]

    @property
    def errors(self) -> Tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.level == "ERROR")

    @property
    def warnings(self) -> Tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.level == "WARNING")

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "workflow": self.workflow,
            "ok": self.ok,
            "errors": [item.as_dict() for item in self.errors],
            "warnings": [item.as_dict() for item in self.warnings],
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }


def _without_comment(line: str) -> str:
    return line.split("!", 1)[0].rstrip()


def _is_coordinate_or_cell_line(path: Sequence[str], key: str, value: str) -> bool:
    if key in _ELEMENT_KEYS and value:
        first = value.split()[0]
        if _FLOAT.match(first):
            return True
    if path and path[-1] == "CELL" and key in {"A", "B", "C"}:
        return True
    return False


def _keyword(line: str, path: Sequence[str]) -> Optional[Tuple[str, str]]:
    tokens = line.strip().split(None, 1)
    if not tokens:
        return None
    key = tokens[0].upper().lstrip("=")
    if not re.match(r"^[A-Z][A-Z0-9_]*$", key):
        return None
    value = tokens[1].strip() if len(tokens) == 2 else ""
    if value.startswith("="):
        value = value[1:].strip()
    if _is_coordinate_or_cell_line(path, key, value):
        return None
    return key, value


def _meta_and_lines(text: str) -> Tuple[Dict[str, str], List[Tuple[int, str]]]:
    metadata: Dict[str, str] = {}
    lines: List[Tuple[int, str]] = []
    for number, original in enumerate(text.splitlines(), start=1):
        match = _META.match(original)
        if match:
            metadata[match.group(1)] = match.group(2)
        lines.append((number, _without_comment(original)))
    return metadata, lines


def _has_path(paths: Iterable[Tuple[str, ...]], names: Sequence[str]) -> bool:
    wanted = tuple(name.upper() for name in names)
    return any(tuple(path[-len(wanted):]) == wanted for path in paths if len(path) >= len(wanted))


def _path_contains(path: Sequence[str], name: str) -> bool:
    wanted = name.upper()
    return any(item.split("#", 1)[0] == wanted for item in path)


def validate_input(
    text: str,
    version: Optional[str] = None,
    workflow: Optional[str] = None,
    strict: bool = False,
) -> ValidationResult:
    """Validate section nesting plus portable CP2K version traps."""

    metadata, lines = _meta_and_lines(text)
    declared_version = metadata.get("CP2K_VERSION")
    declared_workflow = metadata.get("WORKFLOW")
    active_version = version or declared_version
    active_workflow = workflow or declared_workflow
    diagnostics: List[Diagnostic] = []

    def add(level: str, code: str, message: str, line: Optional[int] = None, path: Sequence[str] = ()) -> None:
        actual = "ERROR" if strict and level == "WARNING" else level
        diagnostics.append(Diagnostic(actual, code, message, line, tuple(path)))

    if active_version not in SUPPORTED_VERSIONS:
        add("ERROR", "UNKNOWN_CP2K_VERSION", "version must be exactly 2024.1 or 2026.2")
    if declared_version and version and declared_version != version:
        add(
            "ERROR",
            "VERSION_METADATA_MISMATCH",
            "input metadata declares %s but validator was asked for %s" % (declared_version, version),
        )
    workflow_alias = {declared_workflow or "", workflow or ""} == {"dos", "pdos"}
    if declared_workflow and workflow and declared_workflow != workflow and not workflow_alias:
        add(
            "ERROR",
            "WORKFLOW_METADATA_MISMATCH",
            "input metadata declares %s but validator was asked for %s" % (declared_workflow, workflow),
        )
    if _TOKEN.search(text):
        add("ERROR", "UNRESOLVED_TEMPLATE_SLOT", "rendered CP2K input still contains a template slot")

    stack: List[str] = []
    instance_stack: List[str] = []
    section_counts: Dict[Tuple[Tuple[str, ...], str], int] = {}
    section_paths: List[Tuple[str, ...]] = []
    keywords: List[Tuple[Tuple[str, ...], str, str, int]] = []

    for number, line in lines:
        if not line.strip():
            continue
        end_match = _END.match(line)
        if end_match:
            closing = (end_match.group(1) or "").upper()
            if not stack:
                add("ERROR", "UNMATCHED_END", "section end has no open section", number)
            elif closing and closing != stack[-1]:
                add(
                    "ERROR",
                    "MISMATCHED_END",
                    "expected &END %s but found &END %s" % (stack[-1], closing),
                    number,
                    tuple(stack),
                )
                stack.pop()
                instance_stack.pop()
            else:
                stack.pop()
                instance_stack.pop()
            continue

        header = _HEADER.match(line)
        if header:
            name = header.group(1).upper()
            parent = tuple(stack)
            count_key = (parent, name)
            section_counts[count_key] = section_counts.get(count_key, 0) + 1
            count = section_counts[count_key]
            if count > 1 and name not in _REPEATABLE_SECTIONS:
                add("ERROR", "DUPLICATE_SECTION", "section %s is repeated but is not a registered repeatable section" % name, number, parent)
            stack.append(name)
            instance_stack.append(name if count == 1 else "%s#%d" % (name, count))
            section_paths.append(tuple(stack))
            continue

        parsed = _keyword(line, stack)
        if parsed:
            key, value = parsed
            keywords.append((tuple(instance_stack), key, value, number))

    for name in reversed(stack):
        add("ERROR", "UNCLOSED_SECTION", "section %s has no matching &END" % name)

    seen: Dict[Tuple[Tuple[str, ...], str], Tuple[str, int]] = {}
    for path, key, value, number in keywords:
        identity = (path, key)
        if key in _REPEATABLE_KEYWORDS or key.startswith("CODEX_"):
            continue
        if identity in seen:
            old_value, old_line = seen[identity]
            if old_value != value:
                add(
                    "ERROR",
                    "DUPLICATE_INCOMPATIBLE_KEYWORD",
                    "%s is defined twice with different values (%s and %s)" % (key, old_value, value),
                    number,
                    path,
                )
            else:
                add(
                    "ERROR",
                    "DUPLICATE_KEYWORD",
                    "%s is defined twice; use one authoritative value" % key,
                    number,
                    path,
                )
        else:
            seen[identity] = (value, number)

    if active_version == "2024.1":
        for path in section_paths:
            if path[-1] == "CURVE" and "DOS" in path:
                add("ERROR", "CP2K_2024_LEGACY_DOS", "2024.1 does not use DOS/CURVE syntax", path=path)
            if path[-1] == "PDOS" and "DOS" in path:
                add("ERROR", "CP2K_2024_LEGACY_PDOS", "2024.1 PDOS must be a sibling PRINT section, not nested in DOS", path=path)
            if path[-1] == "OT" and _path_contains(path, "SCF"):
                if any(key == "ADDED_MOS" and _path_contains(other_path, "SCF") for other_path, key, _, _ in keywords):
                    add("ERROR", "CP2K_2024_OT_ADDED_MOS", "2024.1 cannot combine SCF/OT with SCF/ADDED_MOS", path=path)

        for path, key, _, number in keywords:
            if key in {"ENERGY_UNIT", "ENERGY_ZERO", "BROADEN"} and _path_contains(path, "DOS"):
                add("ERROR", "CP2K_2024_DOS_CURVE_KEYWORD", "%s belongs to the 2026.2 DOS/CURVE layout" % key, number, path)

        if active_workflow == "geo_opt" and _has_path(section_paths, ("KPOINTS",)) and _has_path(section_paths, ("OT",)):
            add("ERROR", "CP2K_2024_GEOOPT_KPOINT_OT", "2024.1 GEO_OPT template must not combine explicit KPOINTS with OT")

    if active_version == "2026.2" and any(path[-1] == "PDOS" and "DOS" in path for path in section_paths):
        add("WARNING", "CP2K_2026_NESTED_DOS_LAYOUT", "2026.2 nested DOS/PDOS layout is version-bound and must not be copied to 2024.1")

    if active_workflow == "band_structure":
        if not _has_path(section_paths, ("BAND_STRUCTURE",)):
            add("ERROR", "BAND_SECTION_MISSING", "band workflow requires PRINT/BAND_STRUCTURE")
        if not _has_path(section_paths, ("KPOINT_SET",)):
            add("ERROR", "KPOINT_SET_MISSING", "band workflow requires at least one BAND_STRUCTURE/KPOINT_SET")
        if not any(key == "NPOINTS" and _path_contains(path, "KPOINT_SET") for path, key, _, _ in keywords):
            add("ERROR", "KPOINT_COUNT_MISSING", "each band path must declare NPOINTS")
        if not any(key == "SPECIAL_POINT" and _path_contains(path, "KPOINT_SET") for path, key, _, _ in keywords):
            add("ERROR", "SPECIAL_POINT_MISSING", "band path must declare SPECIAL_POINT endpoints")

    if active_workflow in {"elf_density", "charge_density_difference"}:
        for section in ("ELF_CUBE", "E_DENSITY_CUBE"):
            if not _has_path(section_paths, (section,)):
                add("ERROR", "CUBE_SECTION_MISSING", "%s workflow requires PRINT/%s" % (active_workflow, section))
            if not any(key == "STRIDE" and _path_contains(path, section) for path, key, _, _ in keywords):
                add("WARNING", "CUBE_GRID_UNSPECIFIED", "%s has no explicit STRIDE; common-grid subtraction cannot be assumed" % section)

    if active_workflow == "work_function":
        if not _has_path(section_paths, ("V_HARTREE_CUBE",)):
            add("ERROR", "HARTREE_POTENTIAL_MISSING", "work-function workflow requires PRINT/V_HARTREE_CUBE or an equivalent validated potential output")
        add("WARNING", "WORK_FUNCTION_SLAB_GATE", "work function is valid only after slab/vacuum and vacuum-plateau checks")
        if active_version == "2024.1" and not _has_path(section_paths, ("PLANAR_AVERAGED_V_HARTREE",)):
            add("WARNING", "WORK_FUNCTION_2024_POSTPROCESS", "2024.1 template uses V_HARTREE_CUBE plus external planar averaging; no universal one-keyword work function is assumed")

    if active_workflow == "periodic_resp":
        if not _has_path(section_paths, ("PROPERTIES", "RESP")):
            add("ERROR", "RESP_SECTION_MISSING", "periodic RESP workflow requires FORCE_EVAL/PROPERTIES/RESP")
        if not any(key == "INTEGER_TOTAL_CHARGE" and _path_contains(path, "RESP") for path, key, _, _ in keywords):
            add("WARNING", "RESP_CHARGE_CONSTRAINT_UNSPECIFIED", "periodic charge closure is not explicit without INTEGER_TOTAL_CHARGE")

    if active_workflow == "repeat_like":
        required = {"USE_REPEAT_METHOD", "INTEGER_TOTAL_CHARGE", "AUTO_VDW_RADII_TABLE"}
        present = {key for _, key, _, _ in keywords}
        for key in sorted(required - present):
            add("ERROR", "REPEAT_LIKE_KEYWORD_MISSING", "REPEAT-like template requires %s" % key)
        if not _has_path(section_paths, ("SPHERE_SAMPLING",)):
            add("ERROR", "REPEAT_SPHERE_SAMPLING_MISSING", "REPEAT-like template requires RESP/SPHERE_SAMPLING")

    if active_workflow == "charge_population":
        population_sections = {"MULLIKEN", "LOWDIN", "HIRSHFELD"}
        if not any(path[-1] in population_sections for path in section_paths):
            add("ERROR", "POPULATION_SECTION_MISSING", "charge population workflow requires MULLIKEN, LOWDIN, or HIRSHFELD")

    return ValidationResult(active_version, active_workflow, tuple(diagnostics))
