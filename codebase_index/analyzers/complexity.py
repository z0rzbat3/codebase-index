"""
Complexity analyzer for codebase_index.

Analyzes code complexity and flags large files/functions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """Analyze code complexity and flag large files/functions."""

    def __init__(
        self,
        file_lines_warning: int = 500,
        file_lines_critical: int = 1000,
        function_lines_warning: int = 50,
        function_lines_critical: int = 100,
        class_methods_warning: int = 15,
        class_methods_critical: int = 25,
    ):
        """
        Initialize the complexity analyzer.

        Args:
            file_lines_warning: Lines threshold for file warning.
            file_lines_critical: Lines threshold for critical file warning.
            function_lines_warning: Lines threshold for function warning.
            function_lines_critical: Lines threshold for critical function warning.
            class_methods_warning: Methods threshold for class warning.
            class_methods_critical: Methods threshold for critical class warning.
        """
        self.file_lines_warning = file_lines_warning
        self.file_lines_critical = file_lines_critical
        self.function_lines_warning = function_lines_warning
        self.function_lines_critical = function_lines_critical
        self.class_methods_warning = class_methods_warning
        self.class_methods_critical = class_methods_critical

    def analyze(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze all files for complexity issues.

        Args:
            files: List of file info dictionaries.

        Returns:
            Dictionary with large files, functions, complex classes, and summary.
        """
        result: dict[str, Any] = {
            "large_files": [],
            "large_functions": [],
            "complex_classes": [],
            "summary": {
                "files_warning": 0,
                "files_critical": 0,
                "functions_warning": 0,
                "functions_critical": 0,
            },
        }

        for file_info in files:
            self._analyze_file(file_info, result)

        return result

    def _analyze_file(self, file_info: dict[str, Any], result: dict[str, Any]) -> None:
        """Analyze a single file for complexity."""
        # Check file size
        lines = file_info.get("lines", 0)
        if lines >= self.file_lines_critical:
            result["large_files"].append({
                "path": file_info["path"],
                "lines": lines,
                "severity": "critical",
            })
            result["summary"]["files_critical"] += 1
        elif lines >= self.file_lines_warning:
            result["large_files"].append({
                "path": file_info["path"],
                "lines": lines,
                "severity": "warning",
            })
            result["summary"]["files_warning"] += 1

        # Check functions
        exports = file_info.get("exports", {})
        functions = exports.get("functions", [])

        for func in functions:
            if isinstance(func, dict):
                start_line = func.get("line", 0)
                end_line = func.get("end_line")
                if start_line and end_line:
                    func_lines = end_line - start_line
                    if func_lines >= self.function_lines_critical:
                        result["large_functions"].append({
                            "path": file_info["path"],
                            "function": func.get("name", ""),
                            "lines": func_lines,
                            "severity": "critical",
                        })
                        result["summary"]["functions_critical"] += 1
                    elif func_lines >= self.function_lines_warning:
                        result["large_functions"].append({
                            "path": file_info["path"],
                            "function": func.get("name", ""),
                            "lines": func_lines,
                            "severity": "warning",
                        })
                        result["summary"]["functions_warning"] += 1

        # Check classes
        classes = exports.get("classes", [])
        for cls in classes:
            if isinstance(cls, dict):
                methods = cls.get("methods", [])
                method_count = len(methods)

                if method_count >= self.class_methods_critical:
                    result["complex_classes"].append({
                        "path": file_info["path"],
                        "class": cls.get("name", ""),
                        "methods": method_count,
                        "severity": "critical",
                    })
                elif method_count >= self.class_methods_warning:
                    result["complex_classes"].append({
                        "path": file_info["path"],
                        "class": cls.get("name", ""),
                        "methods": method_count,
                        "severity": "warning",
                    })
