"""
Dependencies scanner for codebase_index.

Scans requirements.txt, pyproject.toml, and package.json for declared dependencies.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class DependenciesScanner:
    """Scan for project dependencies from requirements.txt, package.json, etc."""

    def scan(self, root: Path) -> dict[str, Any]:
        """
        Scan for all dependency files.

        Args:
            root: Project root directory.

        Returns:
            Dictionary with 'python' and 'node' dependency lists.
        """
        result: dict[str, Any] = {
            "python": [],
            "node": {"dependencies": [], "devDependencies": []},
        }

        # Python: requirements.txt files
        req_files = list(root.glob("requirements*.txt"))
        for req_file in req_files:
            deps = self._parse_requirements(req_file)
            result["python"].extend(deps)

        # Python: pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            deps = self._parse_pyproject(pyproject)
            result["python"].extend(deps)

        # Remove duplicates
        result["python"] = list(set(result["python"]))

        # Node: package.json
        package_json = root / "package.json"
        if not package_json.exists():
            # Check common frontend directories
            for subdir in ["frontend", "src/frontend", "client", "web"]:
                alt_path = root / subdir / "package.json"
                if alt_path.exists():
                    package_json = alt_path
                    break

        if package_json.exists():
            node_deps = self._parse_package_json(package_json)
            result["node"] = node_deps

        return result

    def _parse_requirements(self, filepath: Path) -> list[str]:
        """
        Parse requirements.txt file.

        Args:
            filepath: Path to requirements.txt.

        Returns:
            List of package names (without version specifiers).
        """
        deps: list[str] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments, empty lines, and options
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Extract package name (before ==, >=, <, etc.)
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.append(match.group(1).lower())
        except (OSError, IOError) as e:
            logger.warning("Could not parse %s: %s", filepath, e)
        return deps

    def _parse_pyproject(self, filepath: Path) -> list[str]:
        """
        Parse pyproject.toml for dependencies.

        Args:
            filepath: Path to pyproject.toml.

        Returns:
            List of package names.
        """
        deps: list[str] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple regex parsing for dependencies array
            # Matches: dependencies = ["pkg1", "pkg2>=1.0"]
            match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                deps_str = match.group(1)
                for dep_match in re.finditer(r'"([a-zA-Z0-9_-]+)', deps_str):
                    deps.append(dep_match.group(1).lower())

            # Also check [project.optional-dependencies] and [tool.poetry.dependencies]
            for dep_match in re.finditer(
                r'^\s*([a-zA-Z0-9_-]+)\s*=',
                content,
                re.MULTILINE,
            ):
                name = dep_match.group(1).lower()
                if name not in ("python", "name", "version", "description"):
                    deps.append(name)

        except (OSError, IOError) as e:
            logger.warning("Could not parse %s: %s", filepath, e)
        return deps

    def _parse_package_json(self, filepath: Path) -> dict[str, list[str]]:
        """
        Parse package.json for dependencies.

        Args:
            filepath: Path to package.json.

        Returns:
            Dictionary with 'dependencies' and 'devDependencies' lists.
        """
        result: dict[str, list[str]] = {
            "dependencies": [],
            "devDependencies": [],
        }
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            result["dependencies"] = list(data.get("dependencies", {}).keys())
            result["devDependencies"] = list(data.get("devDependencies", {}).keys())
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.warning("Could not parse %s: %s", filepath, e)
        return result
