"""Version-bound CP2K input templates and static validation utilities."""

from .input_validator import ValidationResult, validate_input
from .template_registry import get_template, list_templates, render_template

__all__ = [
    "ValidationResult",
    "get_template",
    "list_templates",
    "render_template",
    "validate_input",
]
