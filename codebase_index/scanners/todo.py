"""
TODO/FIXME scanner for codebase_index.

Scans for TODO, FIXME, HACK, XXX comments in code.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class TodoScanner:
    """Scan for TODO, FIXME, HACK, XXX comments."""

    # Patterns for different comment styles
    PATTERNS = [
        (r'#\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+)$', 'python'),
        (r'//\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+)$', 'typescript'),
        (r'/\*\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)\*/', 'multiline'),
    ]

    # File patterns to scan
    FILE_PATTERNS = [
        "**/*.py",
        "**/*.ts",
        "**/*.tsx",
        "**/*.js",
        "**/*.jsx",
    ]

    def scan(self, root: Path, exclude: list[str]) -> list[dict[str, Any]]:
        """
        Scan all files for TODO/FIXME comments.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            List of todo items with type, message, file, and line.
        """
        todos: list[dict[str, Any]] = []

        for pattern in self.FILE_PATTERNS:
            for filepath in root.glob(pattern):
                if should_exclude(filepath, exclude):
                    continue
                file_todos = self._scan_file(filepath, root)
                todos.extend(file_todos)

        return todos

    def _scan_file(self, filepath: Path, root: Path) -> list[dict[str, Any]]:
        """
        Scan a single file for TODOs.

        Args:
            filepath: Path to the file.
            root: Project root for relative path calculation.

        Returns:
            List of todo items from this file.
        """
        todos: list[dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, _ in self.PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        todos.append({
                            "type": match.group(1).upper(),
                            "message": match.group(2).strip(),
                            "file": rel_path,
                            "line": i,
                        })
                        break  # Only match once per line

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s for TODOs: %s", filepath, e)
        return todos
