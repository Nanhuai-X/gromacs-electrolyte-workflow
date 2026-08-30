#!/usr/bin/env python3
"""Compatibility entry point for the portable CP2K input linter."""

from input_lint import lint_text, main

__all__ = ["lint_text", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
