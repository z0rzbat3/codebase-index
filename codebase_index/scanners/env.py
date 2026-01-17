"""
Environment variables scanner for codebase_index.

Scans for environment variable usage in code and .env files.
Note: Only extracts variable NAMES, never values.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude
from codebase_index.config import DEFAULT_EXCLUDE

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class EnvScanner:
    """Scan for environment variable usage (names only, no values)."""

    def scan(self, root: Path, exclude: list[str] | None = None) -> dict[str, Any]:
        """
        Scan for environment variables.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            Dictionary with dotenv files and usage in Python/TypeScript.
        """
        exclude = exclude or DEFAULT_EXCLUDE

        result: dict[str, Any] = {
            "dotenv_files": {},       # .env files and their var names
            "python_usage": set(),    # os.environ, os.getenv usage
            "typescript_usage": set(),  # process.env usage
            "docker_usage": set(),    # Docker compose env vars
        }

        # Scan .env files (names only, NO VALUES)
        for env_file in root.glob("**/.env*"):
            if should_exclude(env_file, exclude):
                continue
            if env_file.is_file():
                env_vars = self._parse_dotenv(env_file)
                if env_vars:
                    rel_path = str(env_file.relative_to(root))
                    result["dotenv_files"][rel_path] = env_vars

        # Scan Python files for os.environ/os.getenv
        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            found_vars = self._scan_python_env(py_file)
            result["python_usage"].update(found_vars)

        # Scan TypeScript files for process.env
        for pattern in ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]:
            for ts_file in root.glob(pattern):
                if should_exclude(ts_file, exclude):
                    continue
                found_vars = self._scan_typescript_env(ts_file)
                result["typescript_usage"].update(found_vars)

        # Convert sets to sorted lists
        result["python_usage"] = sorted(result["python_usage"])
        result["typescript_usage"] = sorted(result["typescript_usage"])
        result["docker_usage"] = sorted(result["docker_usage"])

        return result

    def _parse_dotenv(self, filepath: Path) -> list[str]:
        """
        Parse .env file for variable names (NOT values).

        Args:
            filepath: Path to .env file.

        Returns:
            List of variable names.
        """
        env_vars: list[str] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Extract variable name (before =)
                    match = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", line)
                    if match:
                        env_vars.append(match.group(1))
        except (OSError, IOError) as e:
            logger.debug("Could not parse %s: %s", filepath, e)
        return env_vars

    def _scan_python_env(self, filepath: Path) -> set[str]:
        """
        Scan Python file for environment variable access.

        Args:
            filepath: Path to Python file.

        Returns:
            Set of variable names accessed.
        """
        env_vars: set[str] = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # os.environ["VAR"] or os.environ.get("VAR") with bracket
            for match in re.finditer(
                r'os\.environ(?:\.get)?\s*\[\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                content,
            ):
                env_vars.add(match.group(1))

            # os.getenv("VAR")
            for match in re.finditer(
                r'os\.getenv\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                content,
            ):
                env_vars.add(match.group(1))

            # os.environ.get("VAR")
            for match in re.finditer(
                r'os\.environ\.get\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                content,
            ):
                env_vars.add(match.group(1))

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)
        return env_vars

    def _scan_typescript_env(self, filepath: Path) -> set[str]:
        """
        Scan TypeScript file for environment variable access.

        Args:
            filepath: Path to TypeScript file.

        Returns:
            Set of variable names accessed.
        """
        env_vars: set[str] = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # process.env.VAR_NAME
            for match in re.finditer(
                r'process\.env\.([A-Z_][A-Z0-9_]*)',
                content,
            ):
                env_vars.add(match.group(1))

            # process.env["VAR_NAME"] or process.env['VAR_NAME']
            for match in re.finditer(
                r'process\.env\[["\']([A-Z_][A-Z0-9_]*)["\']\]',
                content,
            ):
                env_vars.add(match.group(1))

            # import.meta.env.VITE_VAR (Vite)
            for match in re.finditer(
                r'import\.meta\.env\.([A-Z_][A-Z0-9_]*)',
                content,
            ):
                env_vars.add(match.group(1))

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)
        return env_vars
