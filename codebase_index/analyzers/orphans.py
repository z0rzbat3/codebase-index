"""
Orphaned file scanner for codebase_index.

Detects Python files that are never imported anywhere (dead code).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class OrphanedFileScanner:
    """Detect Python files that are never imported anywhere."""

    # Files that are entry points (run directly, not imported)
    ENTRY_POINT_PATTERNS = [
        r"^main\.py$",
        r"^app\.py$",
        r"^run_.*\.py$",
        r"^start_.*\.py$",
        r"^manage\.py$",
        r"^setup\.py$",
        r"^conftest\.py$",
        r"^wsgi\.py$",
        r"^asgi\.py$",
    ]

    # Files that are always excluded from orphan detection
    EXCLUDED_PATTERNS = [
        r"^__init__\.py$",
        r"^__main__\.py$",
        r"^conftest\.py$",
        r"^test_.*\.py$",
        r".*_test\.py$",
    ]

    # Directories that contain entry points
    ENTRY_POINT_DIRS = [
        "migrations",
        "alembic",
        "scripts",
        "examples",
        "tests",
    ]

    def __init__(self) -> None:
        self.all_files: set[str] = set()
        self.all_imports: dict[str, list[str]] = {}
        self.imported_modules: set[str] = set()

    def scan(
        self,
        root: Path,
        files: list[dict[str, Any]],
        exclude: list[str],
    ) -> dict[str, Any]:
        """
        Detect orphaned files.

        Args:
            root: Project root.
            files: List of file info dicts from main scan.
            exclude: Exclusion patterns.

        Returns:
            Dictionary with orphaned files, entry points, and counts.
        """
        result: dict[str, Any] = {
            "orphaned_files": [],
            "entry_points": [],
            "total_python_files": 0,
            "orphaned_count": 0,
            "orphaned_lines": 0,
        }

        # Step 1: Collect all Python files and their module names
        python_files: list[dict[str, Any]] = []
        for file_info in files:
            if file_info.get("language") != "python":
                continue

            path = file_info["path"]
            python_files.append(file_info)
            result["total_python_files"] += 1

            # Extract module name from path
            module_name = self._path_to_module(path)
            if module_name:
                if module_name not in self.all_imports:
                    self.all_imports[module_name] = []
                self.all_imports[module_name].append(path)

        # Step 2: Collect all imports from all files
        for file_info in python_files:
            exports = file_info.get("exports", {})
            imports = exports.get("imports", {})

            # Internal imports point to other project files
            for imp in imports.get("internal", []):
                module = imp.split(".")[0] if imp else None
                if module:
                    self.imported_modules.add(module.lower())

                # Also add full import path
                if imp:
                    self.imported_modules.add(imp.lower().replace(".", "/"))

        # Step 3: Find orphaned files
        for file_info in python_files:
            path = file_info["path"]
            filename = Path(path).name

            # Skip excluded patterns
            if self._is_excluded(filename):
                continue

            # Skip entry point patterns
            if self._is_entry_point(path, filename):
                result["entry_points"].append(path)
                continue

            # Check if this file is imported anywhere
            module_name = self._path_to_module(path)
            if not self._is_imported(path, module_name):
                result["orphaned_files"].append({
                    "path": path,
                    "lines": file_info.get("lines", 0),
                    "module_name": module_name,
                })
                result["orphaned_lines"] += file_info.get("lines", 0)

        result["orphaned_count"] = len(result["orphaned_files"])

        # Sort by lines (biggest orphans first)
        result["orphaned_files"].sort(key=lambda x: x["lines"], reverse=True)

        return result

    def _path_to_module(self, path: str) -> str:
        """Convert file path to Python module name."""
        p = Path(path)
        if p.name == "__init__.py":
            return p.parent.name
        return p.stem

    def _is_excluded(self, filename: str) -> bool:
        """Check if file matches excluded patterns."""
        for pattern in self.EXCLUDED_PATTERNS:
            if re.match(pattern, filename):
                return True
        return False

    def _is_entry_point(self, path: str, filename: str) -> bool:
        """Check if file is an entry point."""
        # Check filename patterns
        for pattern in self.ENTRY_POINT_PATTERNS:
            if re.match(pattern, filename):
                return True

        # Check if in entry point directory
        path_lower = path.lower()
        for dir_name in self.ENTRY_POINT_DIRS:
            if f"/{dir_name}/" in path_lower or path_lower.startswith(f"{dir_name}/"):
                return True

        return False

    def _is_imported(self, path: str, module_name: str | None) -> bool:
        """Check if a file/module is imported anywhere."""
        if not module_name:
            return True  # Can't determine, assume used

        module_lower = module_name.lower()

        # Direct module name match
        if module_lower in self.imported_modules:
            return True

        # Check path-based imports
        path_as_module = path.replace("/", ".").replace("\\", ".").lower()
        path_as_module = re.sub(r"\.py$", "", path_as_module)

        for imported in self.imported_modules:
            if module_lower in imported or imported in path_as_module:
                return True
            if imported.replace(".", "/") in path.lower():
                return True

        return False

    def clear(self) -> None:
        """Clear collected data."""
        self.all_files.clear()
        self.all_imports.clear()
        self.imported_modules.clear()
