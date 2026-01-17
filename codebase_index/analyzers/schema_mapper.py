"""
Schema-to-endpoint mapper for codebase_index.

Maps Pydantic/TypeScript schemas to the endpoints that use them
as request or response bodies by scanning source files directly.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class SchemaMapper:
    """Map schemas to endpoints that use them."""

    def __init__(self, index_data: dict[str, Any], root: Path | None = None) -> None:
        """
        Initialize the schema mapper.

        Args:
            index_data: The loaded index data.
            root: Root directory of the codebase (for file scanning).
        """
        self.index_data = index_data
        self.root = root or self._infer_root()
        self._schemas: list[dict[str, Any]] | None = None
        self._endpoints: list[dict[str, Any]] | None = None
        self._files_by_path: dict[str, dict[str, Any]] | None = None

    def _infer_root(self) -> Path:
        """Infer root directory from index metadata."""
        meta = self.index_data.get("meta", {})
        root_path = meta.get("root_path", ".")
        return Path(root_path)

    @property
    def schemas(self) -> list[dict[str, Any]]:
        """Get all schemas from the index."""
        if self._schemas is None:
            self._schemas = self.index_data.get("schemas", [])
        return self._schemas

    @property
    def endpoints(self) -> list[dict[str, Any]]:
        """Get all endpoints from the index."""
        if self._endpoints is None:
            self._endpoints = self.index_data.get("api_endpoints", [])
            if not self._endpoints:
                self._endpoints = self.index_data.get("endpoints", [])
        return self._endpoints

    @property
    def files_by_path(self) -> dict[str, dict[str, Any]]:
        """Get files indexed by path."""
        if self._files_by_path is None:
            self._files_by_path = {}
            for file_info in self.index_data.get("files", []):
                path = file_info.get("path", "")
                self._files_by_path[path] = file_info
        return self._files_by_path

    def find_endpoints_for_schema(self, schema_name: str) -> dict[str, Any]:
        """
        Find endpoints that use a given schema.

        Args:
            schema_name: The schema name to search for (e.g., "AgentConfig",
                        "CreateUserRequest"). Supports fuzzy matching.

        Returns:
            Dictionary with:
            - schema: The queried schema name
            - matched_schemas: Schemas matching the query
            - endpoints: Endpoints using the schema
            - usages: Detailed usage info (request vs response)
            - summary: Human-readable summary
        """
        result: dict[str, Any] = {
            "schema": schema_name,
            "matched_schemas": [],
            "endpoints": [],
            "usages": [],
            "summary": "",
        }

        # Find matching schemas
        matched_schemas = self._find_matching_schemas(schema_name)
        result["matched_schemas"] = matched_schemas

        if not matched_schemas:
            result["summary"] = f"No schemas found matching '{schema_name}'"
            return result

        # Get all schema names to search for
        schema_names = {s.get("name") for s in matched_schemas}

        # Group endpoints by file for efficient scanning
        endpoints_by_file: dict[str, list[dict[str, Any]]] = {}
        for endpoint in self.endpoints:
            file_path = endpoint.get("file", "")
            if file_path not in endpoints_by_file:
                endpoints_by_file[file_path] = []
            endpoints_by_file[file_path].append(endpoint)

        # Scan each file for schema usages
        seen_endpoints = set()
        for file_path, file_endpoints in endpoints_by_file.items():
            usages = self._scan_file_for_schema_usage(
                file_path, file_endpoints, schema_names
            )
            for endpoint, usage_list in usages:
                endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
                if endpoint_key not in seen_endpoints:
                    seen_endpoints.add(endpoint_key)
                    result["endpoints"].append({
                        "method": endpoint.get("method"),
                        "path": endpoint.get("path"),
                        "full_path": endpoint.get("full_path"),
                        "handler": endpoint.get("handler"),
                        "file": endpoint.get("file"),
                    })
                    result["usages"].append({
                        "endpoint": endpoint_key,
                        "usages": usage_list,
                    })

        # Build summary
        result["summary"] = self._build_summary(result)

        return result

    def _find_matching_schemas(self, schema_name: str) -> list[dict[str, Any]]:
        """Find schemas matching the given name (supports fuzzy matching)."""
        matches = []
        pattern = re.compile(re.escape(schema_name), re.IGNORECASE)

        for schema in self.schemas:
            name = schema.get("name", "")
            # Exact match (highest priority)
            if name.lower() == schema_name.lower():
                matches.append(schema)
            # Partial match
            elif pattern.search(name):
                matches.append(schema)
            # Check if schema name contains the search term
            elif schema_name.lower() in name.lower():
                matches.append(schema)

        return matches

    def _scan_file_for_schema_usage(
        self,
        file_path: str,
        endpoints: list[dict[str, Any]],
        schema_names: set[str],
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """
        Scan a source file to find schema usages in endpoints.

        Returns:
            List of (endpoint, usages) tuples.
        """
        results = []

        # Try to read the file
        full_path = self.root / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except (OSError, IOError) as e:
            logger.debug("Could not read %s: %s", full_path, e)
            return results

        # Parse with AST for accurate function analysis
        try:
            tree = ast.parse(content)
            func_info = self._extract_function_schema_info(tree, content, schema_names)
        except SyntaxError:
            func_info = {}

        # Match endpoints to functions and find usages
        for endpoint in endpoints:
            handler = endpoint.get("handler", "")
            endpoint_line = endpoint.get("line", 0)
            usages = []

            # Check AST-extracted info
            if handler in func_info:
                usages.extend(func_info[handler])

            # Fallback: scan lines around the endpoint
            if not usages:
                usages = self._scan_lines_for_schema(
                    lines, endpoint_line, schema_names
                )

            if usages:
                results.append((endpoint, usages))

        return results

    def _extract_function_schema_info(
        self,
        tree: ast.AST,
        content: str,
        schema_names: set[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Extract schema usage info from functions using AST.

        Returns:
            Dict mapping function name to list of schema usages.
        """
        func_info: dict[str, list[dict[str, Any]]] = {}
        lines = content.split("\n")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            usages = []

            # Check decorators for response_model
            for decorator in node.decorator_list:
                decorator_text = self._get_node_source(lines, decorator)
                for schema in schema_names:
                    # response_model=SchemaName
                    if re.search(rf"response_model\s*=\s*{re.escape(schema)}", decorator_text):
                        usages.append({
                            "type": "response_model",
                            "schema": schema,
                            "location": f"decorator at line {decorator.lineno}",
                        })
                    # List[SchemaName] or list[SchemaName]
                    if re.search(rf"[Ll]ist\s*\[\s*{re.escape(schema)}\s*\]", decorator_text):
                        usages.append({
                            "type": "response_model",
                            "schema": f"List[{schema}]",
                            "location": f"decorator at line {decorator.lineno}",
                        })

            # Check function parameters for schema types
            for arg in node.args.args:
                if arg.annotation:
                    annotation_text = self._get_node_source(lines, arg.annotation)
                    for schema in schema_names:
                        if schema in annotation_text:
                            usages.append({
                                "type": "request_body",
                                "schema": schema,
                                "param_name": arg.arg,
                                "location": f"parameter '{arg.arg}'",
                            })

            # Check return type annotation
            if node.returns:
                return_text = self._get_node_source(lines, node.returns)
                for schema in schema_names:
                    if schema in return_text:
                        usages.append({
                            "type": "return_type",
                            "schema": schema,
                            "location": "return type annotation",
                        })

            if usages:
                func_info[node.name] = usages

        return func_info

    def _get_node_source(self, lines: list[str], node: ast.AST) -> str:
        """Get the source text for an AST node."""
        try:
            start_line = node.lineno - 1
            end_line = getattr(node, "end_lineno", node.lineno) - 1
            start_col = node.col_offset
            end_col = getattr(node, "end_col_offset", len(lines[end_line]) if end_line < len(lines) else 0)

            if start_line == end_line:
                return lines[start_line][start_col:end_col]
            else:
                result = [lines[start_line][start_col:]]
                for i in range(start_line + 1, end_line):
                    result.append(lines[i])
                if end_line < len(lines):
                    result.append(lines[end_line][:end_col])
                return "\n".join(result)
        except (IndexError, AttributeError):
            return ""

    def _scan_lines_for_schema(
        self,
        lines: list[str],
        endpoint_line: int,
        schema_names: set[str],
    ) -> list[dict[str, Any]]:
        """
        Fallback: scan lines around endpoint for schema references.

        Looks for patterns like:
        - response_model=SchemaName
        - param: SchemaName
        - -> SchemaName
        """
        usages = []

        # Look at decorator line and function signature (5 lines before to 10 after)
        start = max(0, endpoint_line - 5)
        end = min(len(lines), endpoint_line + 10)

        context = "\n".join(lines[start:end])

        for schema in schema_names:
            # response_model=SchemaName
            if re.search(rf"response_model\s*=\s*{re.escape(schema)}", context):
                usages.append({
                    "type": "response_model",
                    "schema": schema,
                })

            # param: SchemaName or param: SchemaName = ...
            if re.search(rf":\s*{re.escape(schema)}\s*[=,)]", context):
                usages.append({
                    "type": "request_body",
                    "schema": schema,
                })

            # -> SchemaName (return type)
            if re.search(rf"->\s*{re.escape(schema)}", context):
                usages.append({
                    "type": "return_type",
                    "schema": schema,
                })

            # List[SchemaName]
            if re.search(rf"[Ll]ist\s*\[\s*{re.escape(schema)}\s*\]", context):
                usages.append({
                    "type": "response_model",
                    "schema": f"List[{schema}]",
                })

        return usages

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Build a human-readable summary."""
        parts = []

        num_schemas = len(result["matched_schemas"])
        num_endpoints = len(result["endpoints"])

        if num_schemas == 0:
            parts.append(f"No schemas found matching '{result['schema']}'")
        elif num_schemas == 1:
            parts.append(f"Found schema: {result['matched_schemas'][0].get('name')}")
        else:
            names = [s.get("name") for s in result["matched_schemas"][:3]]
            parts.append(f"Found {num_schemas} matching schemas: {', '.join(names)}")
            if num_schemas > 3:
                parts.append(f"...and {num_schemas - 3} more")

        if num_endpoints == 0:
            parts.append("No endpoints use this schema")
        else:
            parts.append(f"{num_endpoints} endpoint(s) use this schema")

            # Count usage types
            request_count = 0
            response_count = 0
            for usage in result["usages"]:
                for u in usage.get("usages", []):
                    if u.get("type") == "request_body":
                        request_count += 1
                    elif u.get("type") in ("response_model", "return_type"):
                        response_count += 1

            if request_count > 0:
                parts.append(f"{request_count} as request body")
            if response_count > 0:
                parts.append(f"{response_count} as response")

        return "; ".join(parts)
