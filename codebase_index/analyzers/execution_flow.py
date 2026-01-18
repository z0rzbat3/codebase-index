"""
Execution flow analyzer - traces code paths from entry points.

Analyzes the call graph to build execution flow trees showing
how code flows from entry points (main, CLI handlers, routes)
through the system.
"""

from __future__ import annotations

from typing import Any


# Entry point detection patterns
ENTRY_POINT_NAMES = {
    "main",
    "cli",
    "run",
    "start",
    "app",
    "execute",
}

ENTRY_POINT_PREFIXES = {
    "setup_",  # setup functions
}

ENTRY_POINT_DECORATORS = {
    "click.command",
    "click.group",
    "typer.command",
    "app.route",
    "app.get",
    "app.post",
    "app.put",
    "app.delete",
    "router.get",
    "router.post",
    "router.put",
    "router.delete",
}


class ExecutionFlowAnalyzer:
    """
    Analyze execution flow from entry points through the call graph.

    Identifies entry points and traces execution paths to show
    how code flows through the system.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the execution flow analyzer.

        Args:
            index_data: The loaded codebase index.
        """
        self.call_graph = index_data.get("call_graph", {})
        self.symbol_index = index_data.get("symbol_index", {})
        self.files = index_data.get("files", [])

        # Build reverse lookup: function name -> full key
        self._func_to_key: dict[str, list[str]] = {}
        for key in self.call_graph:
            if ":" in key:
                _, func_name = key.rsplit(":", 1)
                if func_name not in self._func_to_key:
                    self._func_to_key[func_name] = []
                self._func_to_key[func_name].append(key)

    def analyze(self, max_depth: int = 6) -> dict[str, Any]:
        """
        Analyze execution flow from all detected entry points.

        Args:
            max_depth: Maximum depth to trace calls.

        Returns:
            Execution flow analysis results.
        """
        entry_points = self.find_entry_points()
        flows = []

        for ep in entry_points:
            flow = self.trace_flow(ep["key"], max_depth=max_depth)
            flows.append({
                "entry_point": ep,
                "flow": flow,
                "depth": self._get_max_depth(flow),
                "total_calls": self._count_calls(flow),
            })

        # Sort by total calls (most connected first)
        flows.sort(key=lambda x: x["total_calls"], reverse=True)

        # Filter out entry points with 0 traced calls (not useful)
        useful_flows = [f for f in flows if f["total_calls"] > 0]
        useful_entry_points = [f["entry_point"] for f in useful_flows]

        return {
            "entry_points": useful_entry_points,
            "flows": useful_flows,
            "summary": {
                "total_entry_points": len(entry_points),
                "max_depth": max(f["depth"] for f in flows) if flows else 0,
                "total_unique_functions": len(self._get_all_functions(flows)),
            },
        }

    def find_entry_points(self) -> list[dict[str, Any]]:
        """
        Find entry point functions in the codebase.

        Returns:
            List of entry point info dicts.
        """
        entry_points = []
        seen_names = set()

        # Check functions in symbol index
        for func in self.symbol_index.get("functions", []):
            name = func.get("name", "").lower()
            file_path = func.get("file", "")
            decorators = func.get("decorators", [])

            is_entry = False
            reason = ""

            # Check name patterns
            if name in ENTRY_POINT_NAMES:
                is_entry = True
                reason = f"name matches '{name}'"
            elif name.startswith("main"):
                is_entry = True
                reason = "name starts with 'main'"

            # Check prefix patterns (test_, setup_, etc.)
            for prefix in ENTRY_POINT_PREFIXES:
                if name.startswith(prefix):
                    is_entry = True
                    reason = f"name starts with '{prefix}'"
                    break

            # Check for __main__ block (file-level)
            if file_path.endswith("__main__.py"):
                is_entry = True
                reason = "__main__.py file"

            # Check decorators
            for dec in decorators:
                dec_lower = dec.lower()
                for pattern in ENTRY_POINT_DECORATORS:
                    if pattern in dec_lower:
                        is_entry = True
                        reason = f"decorator '{dec}'"
                        break

            if is_entry:
                key = f"{file_path}:{func.get('name', '')}"
                # Avoid duplicates (same function name in different files)
                if key not in seen_names:
                    seen_names.add(key)
                    entry_points.append({
                        "name": func.get("name", ""),
                        "file": file_path,
                        "line": func.get("line", 0),
                        "key": key,
                        "reason": reason,
                    })

        # Also check call graph for main functions not in symbol_index
        for key, data in self.call_graph.items():
            if ":" in key:
                file_path, func_name = key.rsplit(":", 1)
                if func_name.lower() in ENTRY_POINT_NAMES and key not in seen_names:
                    seen_names.add(key)
                    entry_points.append({
                        "name": func_name,
                        "file": file_path,
                        "line": data.get("line", 0),
                        "key": key,
                        "reason": f"name matches '{func_name.lower()}'",
                    })

        return entry_points

    def trace_flow(
        self,
        start_key: str,
        max_depth: int = 6,
        visited: set[str] | None = None,
    ) -> dict[str, Any]:
        """
        Trace execution flow from a starting function.

        Args:
            start_key: The call graph key to start from (file:function).
            max_depth: Maximum depth to trace.
            visited: Set of already visited keys (for cycle detection).

        Returns:
            Flow tree structure.
        """
        if visited is None:
            visited = set()

        if start_key in visited or max_depth <= 0:
            return {"truncated": True, "reason": "cycle" if start_key in visited else "max_depth"}

        visited = visited | {start_key}

        # Get call data
        call_data = self.call_graph.get(start_key, {})
        calls = call_data.get("calls", [])

        # Parse the key
        if ":" in start_key:
            file_path, func_name = start_key.rsplit(":", 1)
        else:
            file_path, func_name = "", start_key

        # Build flow node
        node = {
            "name": func_name,
            "file": file_path,
            "line": call_data.get("line", 0),
            "key": start_key,
            "calls": [],
        }

        # Trace each call - only include internal (resolved) calls
        for call in calls:
            # Skip standard library / built-in calls
            if self._is_stdlib_call(call):
                continue

            # Find the full key for this call
            call_keys = self._resolve_call(call, file_path)

            if call_keys:
                # Trace the first matching call (could be multiple in different files)
                for call_key in call_keys[:1]:  # Take first match
                    child_flow = self.trace_flow(call_key, max_depth - 1, visited)
                    node["calls"].append(child_flow)
            # Skip external/unresolved calls - don't add them to the tree

        return node

    def _resolve_call(self, call_name: str, current_file: str) -> list[str]:
        """Resolve a call name to its full call graph key(s)."""
        # Handle method calls like "self.method" or "obj.method"
        if "." in call_name:
            parts = call_name.split(".")
            base_name = parts[-1]  # Get the method name
        else:
            base_name = call_name

        # Look up in our reverse index
        if base_name in self._func_to_key:
            keys = self._func_to_key[base_name]
            # Prefer same-file matches
            same_file = [k for k in keys if k.startswith(current_file)]
            if same_file:
                return same_file
            return keys

        return []

    def _is_stdlib_call(self, call: str) -> bool:
        """Check if a call is to stdlib/builtins."""
        stdlib_prefixes = {
            "print", "len", "str", "int", "float", "bool", "list", "dict", "set",
            "open", "range", "enumerate", "zip", "map", "filter", "sorted",
            "isinstance", "hasattr", "getattr", "setattr",
            "os.", "sys.", "json.", "re.", "pathlib.", "typing.",
            "logging.", "hashlib.", "datetime.", "collections.",
        }
        call_lower = call.lower()
        return any(call_lower.startswith(p) or call_lower == p.rstrip(".")
                   for p in stdlib_prefixes)

    def _get_max_depth(self, flow: dict[str, Any], current: int = 0) -> int:
        """Get maximum depth of a flow tree."""
        if not flow.get("calls"):
            return current
        return max(
            self._get_max_depth(child, current + 1)
            for child in flow["calls"]
        )

    def _count_calls(self, flow: dict[str, Any]) -> int:
        """Count total calls in a flow tree."""
        count = len(flow.get("calls", []))
        for child in flow.get("calls", []):
            count += self._count_calls(child)
        return count

    def _get_all_functions(self, flows: list[dict[str, Any]]) -> set[str]:
        """Get all unique function keys from flows."""
        functions = set()

        def collect(flow: dict[str, Any]) -> None:
            key = flow.get("key", "")
            if key and not flow.get("external"):
                functions.add(key)
            for child in flow.get("calls", []):
                collect(child)

        for f in flows:
            collect(f.get("flow", {}))

        return functions

    def format_flow_tree(self, flow: dict[str, Any], indent: int = 0) -> str:
        """
        Format a flow tree as a readable ASCII tree.

        Args:
            flow: The flow tree to format.
            indent: Current indentation level.

        Returns:
            Formatted tree string.
        """
        lines = []
        prefix = "  " * indent
        connector = "├─ " if indent > 0 else ""

        name = flow.get("name", "?")
        file_path = flow.get("file", "")
        line = flow.get("line", 0)

        if flow.get("truncated"):
            reason = flow.get("reason", "")
            lines.append(f"{prefix}{connector}... ({reason})")
        elif flow.get("external"):
            lines.append(f"{prefix}{connector}{name} [external]")
        else:
            location = f"{file_path}:{line}" if file_path else ""
            lines.append(f"{prefix}{connector}{name} ({location})")

            calls = flow.get("calls", [])
            for i, child in enumerate(calls):
                # Use └─ for last item
                child_lines = self.format_flow_tree(child, indent + 1)
                lines.append(child_lines)

        return "\n".join(lines)


def analyze_execution_flow(
    index_data: dict[str, Any],
    max_depth: int = 6,
) -> dict[str, Any]:
    """
    Convenience function to analyze execution flow.

    Args:
        index_data: The codebase index.
        max_depth: Maximum depth to trace.

    Returns:
        Execution flow analysis results.
    """
    analyzer = ExecutionFlowAnalyzer(index_data)
    return analyzer.analyze(max_depth=max_depth)
