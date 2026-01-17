"""
Impact radius analyzer for codebase_index.

Analyzes the impact radius of changes to a file by finding:
- Functions/classes defined in the file
- Callers of those functions
- Affected tests
- Affected endpoints/routes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Analyze the impact radius of file changes."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the impact analyzer.

        Args:
            index_data: The loaded index data.
        """
        self.index_data = index_data
        self._files_by_path: dict[str, dict[str, Any]] | None = None
        self._call_graph: dict[str, Any] | None = None
        self._reverse_call_graph: dict[str, list[str]] | None = None

    @property
    def files_by_path(self) -> dict[str, dict[str, Any]]:
        """Get files indexed by path."""
        if self._files_by_path is None:
            self._files_by_path = {}
            for file_info in self.index_data.get("files", []):
                path = file_info.get("path", "")
                self._files_by_path[path] = file_info
        return self._files_by_path

    @property
    def call_graph(self) -> dict[str, Any]:
        """Get the call graph from the index."""
        if self._call_graph is None:
            self._call_graph = self.index_data.get("call_graph", {})
        return self._call_graph

    @property
    def reverse_call_graph(self) -> dict[str, list[str]]:
        """Build reverse call graph (callee -> callers)."""
        if self._reverse_call_graph is None:
            self._reverse_call_graph = {}
            for func_key, func_data in self.call_graph.items():
                calls = func_data.get("calls", [])
                for call in calls:
                    if call not in self._reverse_call_graph:
                        self._reverse_call_graph[call] = []
                    self._reverse_call_graph[call].append(func_key)
        return self._reverse_call_graph

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        """
        Analyze the impact radius of changes to a file.

        Args:
            file_path: Path to the file to analyze.

        Returns:
            Dictionary with:
            - file: The analyzed file path
            - symbols: Functions/classes defined in the file
            - direct_callers: Functions that directly call symbols in this file
            - transitive_callers: Functions that indirectly depend on this file
            - affected_tests: Test files/functions that could be affected
            - affected_endpoints: Endpoints that use symbols from this file
            - summary: Human-readable summary
        """
        result: dict[str, Any] = {
            "file": file_path,
            "symbols": [],
            "direct_callers": [],
            "transitive_callers": [],
            "affected_tests": [],
            "affected_endpoints": [],
            "summary": "",
        }

        # Find the file in the index (try both exact and partial match)
        file_info = self._find_file(file_path)
        if not file_info:
            result["summary"] = f"File not found in index: {file_path}"
            return result

        actual_path = file_info.get("path", file_path)
        result["file"] = actual_path

        # Get symbols defined in this file
        exports = file_info.get("exports", {})
        symbols = self._extract_symbols(actual_path, exports)
        result["symbols"] = symbols

        # Find direct callers
        direct_callers = self._find_direct_callers(actual_path, symbols)
        result["direct_callers"] = direct_callers

        # Find transitive callers (up to 2 levels deep)
        transitive_callers = self._find_transitive_callers(direct_callers, depth=2)
        result["transitive_callers"] = transitive_callers

        # Find affected tests
        all_callers = direct_callers + transitive_callers
        affected_tests = self._find_affected_tests(all_callers, actual_path)
        result["affected_tests"] = affected_tests

        # Find affected endpoints
        affected_endpoints = self._find_affected_endpoints(
            actual_path, symbols, all_callers
        )
        result["affected_endpoints"] = affected_endpoints

        # Build summary
        result["summary"] = self._build_summary(result)

        return result

    def _find_file(self, file_path: str) -> dict[str, Any] | None:
        """Find file in index by exact or partial path match."""
        # Exact match
        if file_path in self.files_by_path:
            return self.files_by_path[file_path]

        # Partial match (path ends with the given path)
        for path, file_info in self.files_by_path.items():
            if path.endswith(file_path) or file_path.endswith(path):
                return file_info
            # Also try without leading ./
            clean_path = file_path.lstrip("./")
            if path.endswith(clean_path) or path == clean_path:
                return file_info

        return None

    def _extract_symbols(
        self, file_path: str, exports: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract function and class symbols from exports."""
        symbols = []

        for func in exports.get("functions", []):
            symbols.append({
                "name": func.get("name"),
                "type": "function",
                "qualified": f"{file_path}:{func.get('name')}",
            })

        for cls in exports.get("classes", []):
            class_name = cls.get("name")
            symbols.append({
                "name": class_name,
                "type": "class",
                "qualified": f"{file_path}:{class_name}",
            })
            # Add methods
            for method in cls.get("methods", []):
                method_name = method.get("name")
                symbols.append({
                    "name": f"{class_name}.{method_name}",
                    "type": "method",
                    "qualified": f"{file_path}:{class_name}.{method_name}",
                })

        return symbols

    def _find_direct_callers(
        self, file_path: str, symbols: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find functions that directly call symbols in this file."""
        callers = []
        seen = set()

        # Get symbol names to match
        symbol_names = set()
        for sym in symbols:
            symbol_names.add(sym["name"])
            # Also add variations
            parts = sym["name"].split(".")
            if len(parts) > 1:
                symbol_names.add(parts[-1])  # Just the method name

        # Search call graph for callers
        for func_key, func_data in self.call_graph.items():
            calls = func_data.get("calls", [])

            for call in calls:
                # Check if call matches any symbol
                matched = False
                if call in symbol_names:
                    matched = True
                else:
                    # Check if call ends with a symbol method
                    for sym_name in symbol_names:
                        if call.endswith(f".{sym_name}") or call == sym_name:
                            matched = True
                            break

                if matched and func_key not in seen:
                    seen.add(func_key)
                    caller_file = func_key.split(":")[0] if ":" in func_key else ""
                    # Skip self-references
                    if caller_file != file_path:
                        callers.append({
                            "function": func_key,
                            "file": caller_file,
                            "calls": call,
                        })

        return callers

    def _find_transitive_callers(
        self, direct_callers: list[dict[str, Any]], depth: int = 2
    ) -> list[dict[str, Any]]:
        """Find functions that transitively depend on the file."""
        transitive = []
        seen = {c["function"] for c in direct_callers}
        current_level = [c["function"] for c in direct_callers]

        for _ in range(depth):
            next_level = []
            for func_key in current_level:
                # Extract function name from qualified path
                func_name = func_key.split(":")[-1] if ":" in func_key else func_key

                # Find callers of this function
                for caller, calls in self.call_graph.items():
                    if caller in seen:
                        continue
                    call_list = calls.get("calls", [])
                    if func_name in call_list or any(
                        c.endswith(f".{func_name}") for c in call_list
                    ):
                        seen.add(caller)
                        next_level.append(caller)
                        caller_file = caller.split(":")[0] if ":" in caller else ""
                        transitive.append({
                            "function": caller,
                            "file": caller_file,
                            "depth": _ + 1,
                        })

            current_level = next_level
            if not current_level:
                break

        return transitive

    def _find_affected_tests(
        self, callers: list[dict[str, Any]], file_path: str
    ) -> list[dict[str, Any]]:
        """Find tests that could be affected by changes."""
        affected = []
        seen = set()

        def is_test_path(path: str) -> bool:
            return (
                path.startswith("test_")
                or "/test_" in path
                or "/tests/" in path
                or path.endswith("_test.py")
                or path.endswith(".test.ts")
                or path.endswith(".test.js")
                or path.endswith(".spec.ts")
                or path.endswith(".spec.js")
                or "/__tests__/" in path
            )

        # Check if any caller is in a test file
        for caller in callers:
            caller_file = caller.get("file", "")
            if is_test_path(caller_file) and caller_file not in seen:
                seen.add(caller_file)
                affected.append({
                    "file": caller_file,
                    "function": caller.get("function"),
                    "reason": "calls symbol",
                })

        # Also check for test files that import from this file
        for path, file_info in self.files_by_path.items():
            if not is_test_path(path) or path in seen:
                continue

            exports = file_info.get("exports", {})
            imports = exports.get("imports", {})

            # Handle dict format: {"internal": [...], "external": [...]}
            if isinstance(imports, dict):
                all_imports = []
                for key in ["internal", "external"]:
                    all_imports.extend(imports.get(key, []))
                imports = all_imports

            for imp in imports:
                # Handle string imports
                if isinstance(imp, str):
                    # Check if import references the target file
                    target_module = file_path.replace("/", ".").replace(".py", "")
                    if file_path in imp or target_module in imp:
                        seen.add(path)
                        affected.append({
                            "file": path,
                            "reason": "imports from file",
                        })
                        break
                # Handle dict imports
                elif isinstance(imp, dict):
                    module = imp.get("module", "")
                    if file_path in module or module.endswith(
                        file_path.replace("/", ".").replace(".py", "")
                    ):
                        seen.add(path)
                        affected.append({
                            "file": path,
                            "reason": "imports from file",
                        })
                        break

        return affected

    def _find_affected_endpoints(
        self,
        file_path: str,
        symbols: list[dict[str, Any]],
        callers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find API endpoints that could be affected."""
        affected = []
        seen = set()

        # Get all endpoints from the index
        endpoints = self.index_data.get("endpoints", [])

        # Check if any endpoint is in the same file
        for endpoint in endpoints:
            endpoint_file = endpoint.get("file", "")
            endpoint_key = f"{endpoint.get('method', '')} {endpoint.get('path', '')}"

            if endpoint_key in seen:
                continue

            # Direct: endpoint in the same file
            if endpoint_file == file_path:
                seen.add(endpoint_key)
                affected.append({
                    **endpoint,
                    "reason": "defined in file",
                })
                continue

            # Indirect: endpoint's handler calls symbols from this file
            handler = endpoint.get("handler", "")
            caller_files = {c.get("file") for c in callers}

            if endpoint_file in caller_files:
                seen.add(endpoint_key)
                affected.append({
                    **endpoint,
                    "reason": "handler calls symbol",
                })

        return affected

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Build a human-readable summary."""
        parts = []

        num_symbols = len(result["symbols"])
        num_direct = len(result["direct_callers"])
        num_transitive = len(result["transitive_callers"])
        num_tests = len(result["affected_tests"])
        num_endpoints = len(result["affected_endpoints"])

        parts.append(f"File defines {num_symbols} symbol(s)")

        if num_direct > 0 or num_transitive > 0:
            parts.append(
                f"Impact: {num_direct} direct caller(s), "
                f"{num_transitive} transitive"
            )
        else:
            parts.append("No callers found")

        if num_tests > 0:
            parts.append(f"{num_tests} test(s) affected")
        else:
            parts.append("No tests affected")

        if num_endpoints > 0:
            parts.append(f"{num_endpoints} endpoint(s) affected")

        return "; ".join(parts)
