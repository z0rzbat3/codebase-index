"""
Test coverage mapper for codebase_index.

Maps source files to their corresponding test files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class TestCoverageMapper:
    """Map source files to their corresponding test files."""

    def __init__(self, root: Path):
        """
        Initialize the test coverage mapper.

        Args:
            root: Project root directory.
        """
        self.root = root
        self.test_files: set[str] = set()
        self.source_to_test: dict[str, str] = {}

    def collect_test_files(self, exclude: list[str]) -> None:
        """
        Collect all test files in the project.

        Args:
            exclude: Exclusion patterns.
        """
        patterns = [
            "**/test_*.py",
            "**/tests/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py",
        ]

        for pattern in patterns:
            for test_file in self.root.glob(pattern):
                if not should_exclude(test_file, exclude):
                    rel_path = str(test_file.relative_to(self.root))
                    self.test_files.add(rel_path)

    def map_source_to_test(self, source_files: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Map source files to potential test files.

        Args:
            source_files: List of file info dictionaries.

        Returns:
            Dictionary with covered files, uncovered files, test files, and coverage %.
        """
        coverage_map: dict[str, Any] = {
            "covered": [],
            "uncovered": [],
            "test_files": sorted(self.test_files),
            "coverage_percentage": 0.0,
        }

        testable_sources: list[str] = []

        for source_file in source_files:
            path = source_file.get("path", "")
            language = source_file.get("language", "")
            category = source_file.get("category", "")

            # Only check Python source files (not tests themselves)
            if language != "python":
                continue
            if category == "test" or "test" in path.lower():
                continue
            if path.startswith("tests/"):
                continue

            testable_sources.append(path)

            # Look for corresponding test file
            test_file = self._find_test_file(path)
            if test_file:
                coverage_map["covered"].append({
                    "source": path,
                    "test": test_file,
                })
                self.source_to_test[path] = test_file
            else:
                coverage_map["uncovered"].append(path)

        # Calculate coverage percentage
        if testable_sources:
            coverage_map["coverage_percentage"] = round(
                len(coverage_map["covered"]) / len(testable_sources) * 100, 1
            )

        return coverage_map

    def _find_test_file(self, source_path: str) -> str | None:
        """
        Find a test file for a given source file.

        Args:
            source_path: Path to the source file.

        Returns:
            Path to the test file, or None if not found.
        """
        path = Path(source_path)
        name = path.stem  # e.g., "agent_service"

        # Check for pattern matches
        for test_path in self.test_files:
            test_name = Path(test_path).name

            # Direct name match
            if test_name == f"test_{name}.py" or test_name == f"{name}_test.py":
                return test_path

            # Partial match (e.g., test_agent.py for agent_service.py)
            base_name = name.split("_")[0]
            if test_name == f"test_{base_name}.py":
                return test_path

        return None

    def clear(self) -> None:
        """Clear collected test files."""
        self.test_files.clear()
        self.source_to_test.clear()
