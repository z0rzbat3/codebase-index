"""
Test mapper for codebase_index.

Maps symbols (functions, classes) to their tests by analyzing
imports, call graphs, and naming conventions.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class TestMapper:
    """Map symbols to their tests."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the test mapper.

        Args:
            index_data: The loaded index data.
        """
        self.index_data = index_data
        self._test_files: list[dict[str, Any]] | None = None
        self._call_graph: dict[str, Any] | None = None

    @property
    def test_files(self) -> list[dict[str, Any]]:
        """Get all test files from the index."""
        if self._test_files is None:
            self._test_files = []
            for file_info in self.index_data.get("files", []):
                path = file_info.get("path", "")
                # Common test file patterns
                if (
                    path.startswith("test_")
                    or path.startswith("tests/")
                    or "/test_" in path
                    or "/tests/" in path
                    or path.endswith("_test.py")
                    or path.endswith(".test.ts")
                    or path.endswith(".test.js")
                    or path.endswith(".spec.ts")
                    or path.endswith(".spec.js")
                    or "/__tests__/" in path
                ):
                    self._test_files.append(file_info)
        return self._test_files

    @property
    def call_graph(self) -> dict[str, Any]:
        """Get the call graph from the index."""
        if self._call_graph is None:
            self._call_graph = self.index_data.get("call_graph", {})
        return self._call_graph

    def find_tests_for(self, symbol: str) -> dict[str, Any]:
        """
        Find tests for a given symbol.

        Args:
            symbol: The symbol to find tests for (e.g., "AgentFactory.create",
                   "my_function", "MyClass").

        Returns:
            Dictionary with:
            - symbol: The queried symbol
            - tests: List of matching test info
            - test_files: List of test files that reference the symbol
            - coverage_estimate: Rough estimate of test coverage
        """
        result: dict[str, Any] = {
            "symbol": symbol,
            "tests": [],
            "test_files": [],
            "importers": [],
            "callers": [],
            "summary": "",
        }

        # Parse the symbol
        parts = symbol.split(".")
        if len(parts) == 2:
            class_name, method_name = parts
        else:
            class_name = None
            method_name = symbol

        # Find test files that import or reference this symbol
        for test_file in self.test_files:
            file_path = test_file.get("path", "")
            exports = test_file.get("exports", {})

            # Check imports
            imports = exports.get("imports", [])
            imports_symbol = self._imports_symbol(imports, symbol, class_name, method_name)

            # Check function calls in the call graph
            calls_symbol = self._calls_symbol(file_path, symbol, class_name, method_name)

            # Check test function names for naming convention matches
            test_functions = self._find_matching_test_functions(
                exports, class_name, method_name
            )

            if imports_symbol or calls_symbol or test_functions:
                test_info = {
                    "file": file_path,
                    "imports_symbol": imports_symbol,
                    "calls_symbol": calls_symbol,
                    "test_functions": test_functions,
                }
                result["test_files"].append(file_path)
                result["tests"].append(test_info)

                if imports_symbol:
                    result["importers"].append(file_path)

        # Find callers from call graph
        result["callers"] = self._find_callers_in_tests(symbol)

        # Build summary
        result["summary"] = self._build_summary(result)

        return result

    def _imports_symbol(
        self,
        imports: dict[str, Any] | list[Any],
        symbol: str,
        class_name: str | None,
        method_name: str,
    ) -> bool:
        """Check if the imports contain the symbol."""
        # Handle dict format: {"internal": [...], "external": [...]}
        if isinstance(imports, dict):
            all_imports = []
            for key in ["internal", "external"]:
                all_imports.extend(imports.get(key, []))
            imports = all_imports

        for imp in imports:
            # Handle string imports (module names)
            if isinstance(imp, str):
                # Check if symbol or class name is in the import path
                if symbol in imp or (class_name and class_name in imp):
                    return True
                if method_name in imp:
                    return True
                continue

            # Handle dict imports (structured format)
            if isinstance(imp, dict):
                # Direct import
                if imp.get("name") == symbol:
                    return True
                if imp.get("name") == class_name:
                    return True
                if imp.get("name") == method_name:
                    return True

                # Check alias
                if imp.get("alias") == symbol:
                    return True
                if imp.get("alias") == class_name:
                    return True

                # Check module path
                module = imp.get("module", "")
                if symbol in module or (class_name and class_name in module):
                    return True

        return False

    def _calls_symbol(
        self,
        file_path: str,
        symbol: str,
        class_name: str | None,
        method_name: str,
    ) -> bool:
        """Check if the file calls the symbol based on call graph."""
        for func_key, func_data in self.call_graph.items():
            if not func_key.startswith(file_path + ":"):
                continue

            calls = func_data.get("calls", [])
            for call in calls:
                if call == symbol:
                    return True
                if call == method_name:
                    return True
                if class_name and call.endswith(f".{method_name}"):
                    return True
                # Handle self.method() patterns
                if call.endswith(f".{method_name}"):
                    return True

        return False

    def _find_matching_test_functions(
        self,
        exports: dict[str, Any],
        class_name: str | None,
        method_name: str,
    ) -> list[str]:
        """Find test functions that match naming conventions."""
        matches = []

        # Build patterns to match
        patterns = []

        # test_<method_name>
        patterns.append(re.compile(rf"^test_.*{re.escape(method_name)}.*$", re.IGNORECASE))

        # test<MethodName> (camelCase)
        camel_method = method_name[0].upper() + method_name[1:] if method_name else ""
        if camel_method:
            patterns.append(re.compile(rf"^test.*{re.escape(camel_method)}.*$"))

        # For class methods: test_<class>_<method>
        if class_name:
            patterns.append(
                re.compile(
                    rf"^test_.*{re.escape(class_name)}.*{re.escape(method_name)}.*$",
                    re.IGNORECASE,
                )
            )
            # TestClassName
            patterns.append(re.compile(rf"^Test{re.escape(class_name)}$"))

        # Check functions
        for func in exports.get("functions", []):
            func_name = func.get("name", "")
            for pattern in patterns:
                if pattern.match(func_name):
                    matches.append(func_name)
                    break

        # Check classes (test classes)
        for cls in exports.get("classes", []):
            cls_name = cls.get("name", "")
            for pattern in patterns:
                if pattern.match(cls_name):
                    matches.append(cls_name)
                    break

            # Check methods within test classes
            if cls_name.startswith("Test"):
                for method in cls.get("methods", []):
                    method_name_in_cls = method.get("name", "")
                    for pattern in patterns:
                        if pattern.match(method_name_in_cls):
                            matches.append(f"{cls_name}.{method_name_in_cls}")
                            break

        return matches

    def _find_callers_in_tests(self, symbol: str) -> list[str]:
        """Find test functions that call the symbol."""
        callers = []

        for func_key, func_data in self.call_graph.items():
            # Check if this is a test file
            file_path = func_key.split(":")[0] if ":" in func_key else ""
            is_test = (
                file_path.startswith("test_")
                or "/test_" in file_path
                or "/tests/" in file_path
                or file_path.endswith("_test.py")
            )

            if not is_test:
                continue

            calls = func_data.get("calls", [])
            if symbol in calls:
                callers.append(func_key)
            else:
                # Check partial matches
                parts = symbol.split(".")
                method = parts[-1] if parts else symbol
                for call in calls:
                    if call.endswith(f".{method}") or call == method:
                        callers.append(func_key)
                        break

        return callers

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Build a human-readable summary."""
        parts = []

        num_tests = len(result["tests"])
        num_callers = len(result["callers"])

        if num_tests == 0:
            parts.append(f"No tests found for '{result['symbol']}'")
        else:
            parts.append(f"Found {num_tests} test file(s) for '{result['symbol']}'")

        if num_callers > 0:
            parts.append(f"{num_callers} test function(s) call this symbol")

        test_funcs = []
        for test in result["tests"]:
            test_funcs.extend(test.get("test_functions", []))
        if test_funcs:
            parts.append(f"Matching test functions: {', '.join(test_funcs[:5])}")
            if len(test_funcs) > 5:
                parts.append(f"...and {len(test_funcs) - 5} more")

        return "; ".join(parts)
