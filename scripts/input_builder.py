#!/usr/bin/env python3
"""Small structured CP2K input tree for deterministic rendering and parsing."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple


def _value_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return str(value)


@dataclass
class Section:
    name: str
    enabled: bool = True
    header: Optional[str] = None
    comments: List[str] = field(default_factory=list)
    keywords: List[Tuple[str, Any]] = field(default_factory=list)
    sections: List["Section"] = field(default_factory=list)

    def add_keyword(self, name: str, value: Any) -> "Section":
        name = name.upper()
        for existing, existing_value in self.keywords:
            if existing == name and _value_text(existing_value) != _value_text(value):
                raise ValueError(f"incompatible duplicate keyword {name} in &{self.name}")
        self.keywords.append((name, value))
        return self

    def add_section(
        self,
        name: str,
        enabled: bool = True,
        comments: Optional[Iterable[str]] = None,
        header: Optional[str] = None,
    ) -> "Section":
        child = Section(name.upper(), enabled=enabled, header=header, comments=list(comments or []))
        self.sections.append(child)
        return child

    def render(self, level: int = 0) -> str:
        if not self.enabled:
            return ""
        indent = "  " * level
        opening = indent + "&" + self.name + ((" " + self.header) if self.header else "")
        lines = [opening]
        lines.extend(indent + "  # " + comment for comment in self.comments)
        lines.extend(indent + "  " + key + " " + _value_text(value) for key, value in self.keywords)
        for child in self.sections:
            rendered = child.render(level + 1)
            if rendered:
                lines.append(rendered)
        lines.append(indent + "&END " + self.name)
        return "\n".join(lines)

    def find(self, name: str) -> Optional["Section"]:
        target = name.upper()
        if self.name == target:
            return self
        for child in self.sections:
            found = child.find(target)
            if found:
                return found
        return None


class CP2KInput:
    def __init__(self) -> None:
        self.sections: List[Section] = []

    def add_section(
        self,
        name: str,
        enabled: bool = True,
        comments: Optional[Iterable[str]] = None,
        header: Optional[str] = None,
    ) -> Section:
        section = Section(name.upper(), enabled=enabled, header=header, comments=list(comments or []))
        self.sections.append(section)
        return section

    def find(self, name: str) -> Optional[Section]:
        for section in self.sections:
            found = section.find(name)
            if found:
                return found
        return None

    def render(self) -> str:
        return "\n".join(section.render(0) for section in self.sections if section.enabled) + "\n"

    @classmethod
    def parse(cls, text: str) -> "CP2KInput":
        root = cls()
        stack: List[Section] = []
        open_re = re.compile(r"^\s*&([A-Za-z_][A-Za-z0-9_]*)\b(.*)$")
        end_re = re.compile(r"^\s*&END(?:\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$", re.I)
        for line_number, raw in enumerate(text.splitlines(), start=1):
            line = raw.split("!", 1)[0].strip()
            if not line or line.startswith("#"):
                continue
            end_match = end_re.match(line)
            if end_match:
                if not stack:
                    raise ValueError(f"line {line_number}: unmatched &END")
                expected = stack.pop().name
                declared = (end_match.group(1) or expected).upper()
                if declared != expected:
                    raise ValueError(f"line {line_number}: &END {declared} closes &{expected}")
                continue
            open_match = open_re.match(line)
            if open_match:
                section = Section(open_match.group(1).upper(), header=open_match.group(2).strip() or None)
                if stack:
                    stack[-1].sections.append(section)
                else:
                    root.sections.append(section)
                stack.append(section)
                continue
            if not stack:
                raise ValueError(f"line {line_number}: keyword outside a section")
            fields = line.split(None, 1)
            if len(fields) == 1:
                stack[-1].add_keyword(fields[0], "")
            else:
                stack[-1].add_keyword(fields[0], fields[1])
        if stack:
            raise ValueError("unclosed sections: " + ", ".join(item.name for item in stack))
        return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.input:
        raise SystemExit("--input is required")
    tree = CP2KInput.parse(args.input.read_text(encoding="utf-8"))
    rendered = tree.render()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "PASS", "sections": [section.name for section in tree.sections]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
