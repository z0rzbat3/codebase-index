"""
Codebase Index - A CLI tool to generate comprehensive codebase inventories.

Supports pluggable language parsers for Python (AST), TypeScript (regex),
SQL (regex), Docker (YAML), and custom languages.
"""

__version__ = "2.2.0"
__author__ = "Isaac"

from codebase_index.scanner import CodebaseScanner
from codebase_index.config import DEFAULT_CONFIG, DEFAULT_EXCLUDE

__all__ = [
    "CodebaseScanner",
    "DEFAULT_CONFIG",
    "DEFAULT_EXCLUDE",
    "__version__",
]
