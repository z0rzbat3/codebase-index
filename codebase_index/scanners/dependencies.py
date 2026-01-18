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

        def extract_pkg_name(dep_string: str) -> str | None:
            """Extract package name from dependency string like 'pkg>=1.0'."""
            match = re.match(r'^([a-zA-Z0-9_-]+)', dep_string)
            return match.group(1).lower() if match else None

        try:
            # Use tomllib (Python 3.11+) or fall back to tomli
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore
                except ImportError:
                    # Fall back to regex parsing if no TOML library available
                    return self._parse_pyproject_regex(filepath)

            with open(filepath, "rb") as f:
                data = tomllib.load(f)

            # Get project name to filter self-references
            project_name = data.get("project", {}).get("name", "").lower()

            # [project.dependencies]
            for dep in data.get("project", {}).get("dependencies", []):
                pkg = extract_pkg_name(dep)
                if pkg and pkg != project_name:
                    deps.append(pkg)

            # [project.optional-dependencies]
            optional_deps = data.get("project", {}).get("optional-dependencies", {})
            for group_deps in optional_deps.values():
                for dep in group_deps:
                    pkg = extract_pkg_name(dep)
                    # Skip self-references like "codebase-index[yaml]"
                    if pkg and pkg != project_name:
                        deps.append(pkg)

            # [tool.poetry.dependencies] (Poetry format)
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            for pkg_name in poetry_deps:
                if pkg_name.lower() != "python":
                    deps.append(pkg_name.lower())

            # [tool.poetry.group.*.dependencies] (Poetry groups)
            poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
            for group in poetry_groups.values():
                for pkg_name in group.get("dependencies", {}):
                    if pkg_name.lower() != "python":
                        deps.append(pkg_name.lower())

        except (OSError, IOError) as e:
            logger.warning("Could not parse %s: %s", filepath, e)

        return deps

    def _parse_pyproject_regex(self, filepath: Path) -> list[str]:
        """
        Fallback regex parsing for pyproject.toml when no TOML library is available.

        Args:
            filepath: Path to pyproject.toml.

        Returns:
            List of package names.
        """
        deps: list[str] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Match dependencies = ["pkg1", "pkg2>=1.0"]
            match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                deps_str = match.group(1)
                for dep_match in re.finditer(r'"([a-zA-Z0-9_-]+)', deps_str):
                    deps.append(dep_match.group(1).lower())

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
