"""
Language parsers for codebase_index.

Each parser extracts structural information from source files.
Custom parsers can be added by inheriting from BaseParser.
"""

from codebase_index.parsers.base import BaseParser, ParserRegistry
from codebase_index.parsers.python import PythonParser
from codebase_index.parsers.typescript import TypeScriptParser
from codebase_index.parsers.sql import SQLParser
from codebase_index.parsers.docker import DockerParser

__all__ = [
    "BaseParser",
    "ParserRegistry",
    "PythonParser",
    "TypeScriptParser",
    "SQLParser",
    "DockerParser",
]
