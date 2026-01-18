"""
Documentation generator for codebase_index.

Generates rich documentation for symbols by combining:
- Symbol info (name, signature, docstring)
- LLM summary
- Call graph (what it calls, what calls it)
- Related tests
- Code snippet

Output is formatted as Markdown.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

# Built-in functions and common patterns to filter from data flow analysis
BUILTIN_FUNCTIONS = {
    # Python built-ins
    "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "sum", "min", "max", "abs", "round", "pow", "divmod",
    "open", "print", "input", "type", "isinstance", "issubclass",
    "hasattr", "getattr", "setattr", "delattr", "callable",
    "iter", "next", "repr", "format", "hash", "id", "hex", "oct", "bin",
    "ord", "chr", "bytes", "bytearray", "memoryview",
    "all", "any", "dir", "vars", "locals", "globals", "eval", "exec",
    "compile", "super", "object", "classmethod", "staticmethod", "property",
    # Common method calls to filter
    "append", "extend", "insert", "remove", "pop", "clear", "copy",
    "get", "keys", "values", "items", "update", "setdefault",
    "add", "discard", "union", "intersection", "difference",
    "join", "split", "strip", "replace", "find", "startswith", "endswith",
    "lower", "upper", "title", "format", "encode", "decode",
    "read", "write", "close", "seek", "tell", "flush",
    # Common attribute access patterns
    "self", "cls",
    # Standard library modules/classes
    "Path", "PurePath", "pathlib",
    "re", "match", "search", "findall", "finditer", "sub", "compile",
    "os", "sys", "io", "json", "yaml", "csv", "xml",
    "datetime", "date", "time", "timedelta",
    "collections", "itertools", "functools",
    "typing", "Any", "Optional", "Union", "List", "Dict", "Set", "Tuple",
    "logging", "logger", "debug", "info", "warning", "error", "critical",
    "hashlib", "sha256", "md5",
    "ast", "parse", "walk", "NodeVisitor",
    "argparse", "ArgumentParser",
    "threading", "Lock", "Thread",
    "concurrent", "futures", "ThreadPoolExecutor",
    "subprocess", "Popen",
    "urllib", "requests",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
}

# Patterns that indicate non-meaningful calls (method calls on objects)
FILTER_PATTERNS = {
    ".get", ".append", ".extend", ".add", ".update", ".pop", ".remove",
    ".read", ".write", ".close", ".encode", ".decode",
    ".split", ".join", ".strip", ".replace", ".format",
    ".keys", ".values", ".items",
    ".group", ".groups", ".match", ".search", ".findall", ".finditer",
    ".relative_to", ".exists", ".mkdir", ".is_file", ".is_dir", ".stat",
    "logger.", "logging.", "log.",
    "re.", "os.", "sys.", "json.", "yaml.", "ast.",
    "Path(", "hashlib.", "datetime.",
}


class DocumentationGenerator:
    """
    Generate documentation for code symbols.

    Combines data from multiple index sources to produce
    comprehensive documentation.
    """

    def __init__(self, index_data: dict[str, Any], root: Path | None = None) -> None:
        """
        Initialize the documentation generator.

        Args:
            index_data: The loaded codebase index.
            root: Root directory for reading source files.
        """
        self.index_data = index_data
        self.root = root
        self.symbol_index = index_data.get("symbol_index", {})
        self.call_graph = index_data.get("call_graph", {})

    def generate_for_symbol(self, symbol_name: str) -> dict[str, Any]:
        """
        Generate documentation for a symbol.

        Args:
            symbol_name: Name of the symbol (function, class, or method).
                         Supports partial matching and Class.method format.

        Returns:
            Dictionary with documentation data and formatted markdown.
        """
        # Find matching symbols
        matches = self._find_symbols(symbol_name)

        if not matches:
            return {
                "symbol": symbol_name,
                "error": f"No symbol found matching '{symbol_name}'",
                "markdown": f"# Error\n\nNo symbol found matching `{symbol_name}`",
            }

        # Generate docs for each match
        docs = []
        for match in matches:
            doc = self._generate_symbol_doc(match)
            docs.append(doc)

        # Combine into final output
        if len(docs) == 1:
            markdown = docs[0]["markdown"]
        else:
            markdown = f"# Documentation for '{symbol_name}'\n\n"
            markdown += f"Found {len(docs)} matching symbols.\n\n---\n\n"
            markdown += "\n\n---\n\n".join(d["markdown"] for d in docs)

        return {
            "symbol": symbol_name,
            "matches": len(docs),
            "docs": docs,
            "markdown": markdown,
        }

    def _find_symbols(self, name: str) -> list[dict[str, Any]]:
        """Find symbols matching the given name."""
        matches = []
        name_lower = name.lower()

        # Check if it's a Class.method format
        if "." in name:
            class_name, method_name = name.rsplit(".", 1)
        else:
            class_name, method_name = None, None

        # Search functions
        for func in self.symbol_index.get("functions", []):
            func_name = func.get("name", "")
            if name_lower == func_name.lower() or name_lower in func_name.lower():
                matches.append({**func, "type": "function"})

        # Search classes
        for cls in self.symbol_index.get("classes", []):
            cls_name = cls.get("name", "")
            if name_lower == cls_name.lower() or name_lower in cls_name.lower():
                matches.append({**cls, "type": "class"})

        # Search methods
        for method in self.symbol_index.get("methods", []):
            meth_name = method.get("name", "")
            meth_class = method.get("class", "")
            full_name = f"{meth_class}.{meth_name}"

            # Match by full name or partial
            if class_name and method_name:
                # Exact Class.method search
                if (class_name.lower() == meth_class.lower() and
                    method_name.lower() == meth_name.lower()):
                    matches.append({**method, "type": "method"})
            elif name_lower in full_name.lower() or name_lower == meth_name.lower():
                matches.append({**method, "type": "method"})

        return matches

    def _generate_symbol_doc(self, symbol: dict[str, Any]) -> dict[str, Any]:
        """Generate documentation for a single symbol."""
        sym_type = symbol.get("type", "unknown")
        name = symbol.get("name", "")
        file_path = symbol.get("file", "")
        line = symbol.get("line", 0)

        # Build full name for methods
        if sym_type == "method":
            class_name = symbol.get("class", "")
            full_name = f"{class_name}.{name}"
        else:
            full_name = name

        # Gather information
        summary = symbol.get("summary", "")
        docstring = symbol.get("docstring", "")
        signature = symbol.get("signature", {})

        # Get call graph info
        callers = self._get_callers(full_name, file_path)
        calls = self._get_calls(full_name, file_path)

        # Get tests
        tests = self._get_tests(full_name)

        # Get code snippet
        code_snippet = self._get_code_snippet(file_path, line)

        # Build markdown
        markdown = self._format_markdown(
            full_name=full_name,
            sym_type=sym_type,
            file_path=file_path,
            line=line,
            summary=summary,
            docstring=docstring,
            signature=signature,
            callers=callers,
            calls=calls,
            tests=tests,
            code_snippet=code_snippet,
        )

        return {
            "name": full_name,
            "type": sym_type,
            "file": file_path,
            "line": line,
            "summary": summary,
            "docstring": docstring,
            "callers": callers,
            "calls": calls,
            "tests": tests,
            "markdown": markdown,
        }

    def _get_callers(self, name: str, file_path: str) -> list[dict[str, Any]]:
        """Get functions that call this symbol."""
        callers = []

        # Extract base name for matching (e.g., "Class.method" -> "method", "func" -> "func")
        base_name = name.split(".")[-1].lower() if "." in name else name.lower()

        for func_key, func_data in self.call_graph.items():
            calls_list = func_data.get("calls", [])

            # Check if this function calls our symbol
            for call in calls_list:
                call_lower = call.lower()
                call_base = call.split(".")[-1].lower() if "." in call else call_lower

                # Match: exact match, or call ends with our name, or base names match
                is_match = (
                    call_lower == name.lower() or
                    call_lower == base_name or
                    call_base == base_name or
                    call_lower.endswith("." + base_name)
                )

                if is_match:
                    # Parse func_key (format: "file:name" or "file:Class.method")
                    if ":" in func_key:
                        caller_file, caller_name = func_key.split(":", 1)
                    else:
                        caller_file, caller_name = "", func_key

                    callers.append({
                        "name": caller_name,
                        "file": caller_file,
                        "line": func_data.get("line", 0),
                    })
                    break

        return callers[:20]  # Limit results

    def _get_calls(self, name: str, file_path: str) -> list[str]:
        """Get functions that this symbol calls."""
        # Find the symbol in call graph
        for func_key, func_data in self.call_graph.items():
            if name in func_key:
                return func_data.get("calls", [])[:20]

        return []

    def _get_tests(self, name: str) -> list[dict[str, Any]]:
        """Get tests for this symbol."""
        from codebase_index.analyzers.test_mapper import TestMapper

        try:
            mapper = TestMapper(self.index_data)
            result = mapper.find_tests_for(name)
            return result.get("tests", [])[:10]
        except Exception as e:
            logger.debug("Error getting tests: %s", e)
            return []

    def _get_code_snippet(self, file_path: str, line: int, context: int = 30) -> str:
        """Get code snippet from source file."""
        if not self.root or not file_path:
            return ""

        full_path = self.root / file_path
        if not full_path.exists():
            return ""

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if line < 1 or line > len(lines):
                return ""

            # Get lines around the symbol
            start = line - 1
            end = min(start + context, len(lines))

            # Find end of function/class
            code_lines = lines[start:end]
            if not code_lines:
                return ""

            first_line = code_lines[0]
            base_indent = len(first_line) - len(first_line.lstrip())
            result_lines = [first_line]

            for ln in code_lines[1:]:
                stripped = ln.strip()
                if not stripped:
                    result_lines.append(ln)
                    continue

                current_indent = len(ln) - len(ln.lstrip())
                if current_indent <= base_indent and stripped:
                    if stripped.startswith(("def ", "class ", "async def ", "@")):
                        break
                result_lines.append(ln)

            return "".join(result_lines).rstrip()

        except (OSError, IOError) as e:
            logger.debug("Error reading %s: %s", full_path, e)
            return ""

    def _format_markdown(
        self,
        full_name: str,
        sym_type: str,
        file_path: str,
        line: int,
        summary: str,
        docstring: str,
        signature: dict[str, Any],
        callers: list[dict[str, Any]],
        calls: list[str],
        tests: list[dict[str, Any]],
        code_snippet: str,
    ) -> str:
        """Format documentation as Markdown."""
        lines = []

        # Header
        lines.append(f"# {full_name}")
        lines.append("")
        lines.append(f"**Type:** {sym_type}")
        lines.append(f"**File:** `{file_path}:{line}`")
        lines.append("")

        # Summary
        if summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(summary)
            lines.append("")

        # Docstring
        if docstring and docstring != summary:
            lines.append("## Description")
            lines.append("")
            lines.append(docstring)
            lines.append("")

        # Signature
        if signature:
            formatted = signature.get("formatted")
            if formatted:
                lines.append("## Signature")
                lines.append("")
                lines.append("```python")
                lines.append(formatted)
                lines.append("```")
                lines.append("")

            # Parameters
            params = signature.get("params", [])
            if params:
                lines.append("## Parameters")
                lines.append("")
                lines.append("| Name | Type | Default |")
                lines.append("|------|------|---------|")
                for p in params:
                    p_name = p.get("name", "")
                    p_type = p.get("type", "-")
                    p_default = "..." if p.get("has_default") else "-"
                    lines.append(f"| `{p_name}` | `{p_type}` | {p_default} |")
                lines.append("")

            # Return type
            return_type = signature.get("return_type")
            if return_type:
                lines.append(f"**Returns:** `{return_type}`")
                lines.append("")

        # What it calls
        if calls:
            lines.append("## Calls")
            lines.append("")
            for call in calls[:15]:
                lines.append(f"- `{call}`")
            if len(calls) > 15:
                lines.append(f"- ... and {len(calls) - 15} more")
            lines.append("")

        # What calls it
        if callers:
            lines.append("## Called By")
            lines.append("")
            for caller in callers[:15]:
                c_name = caller.get("name", "")
                c_file = caller.get("file", "")
                c_line = caller.get("line", 0)
                lines.append(f"- `{c_name}` in `{c_file}:{c_line}`")
            if len(callers) > 15:
                lines.append(f"- ... and {len(callers) - 15} more")
            lines.append("")

        # Tests
        if tests:
            lines.append("## Tests")
            lines.append("")
            for test in tests[:10]:
                test_file = test.get("file", "")
                test_funcs = test.get("test_functions", [])
                lines.append(f"**{test_file}:**")
                for tf in test_funcs[:5]:
                    lines.append(f"- `{tf}`")
                if len(test_funcs) > 5:
                    lines.append(f"- ... and {len(test_funcs) - 5} more")
            lines.append("")

        # Code snippet
        if code_snippet:
            lines.append("## Source Code")
            lines.append("")
            lines.append("```python")
            lines.append(code_snippet)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)


def generate_doc_for_symbol(
    index_data: dict[str, Any],
    symbol_name: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Convenience function to generate documentation for a symbol.

    Args:
        index_data: The codebase index.
        symbol_name: Symbol to document.
        root: Root directory for reading source files.

    Returns:
        Documentation data with markdown output.
    """
    generator = DocumentationGenerator(index_data, root=root)
    return generator.generate_for_symbol(symbol_name)


class APIReferenceGenerator:
    """
    Generate API reference documentation from index data.

    Creates markdown documentation for API endpoints grouped by router/file.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the API reference generator.

        Args:
            index_data: The loaded codebase index.
        """
        self.index_data = index_data
        self.endpoints = index_data.get("api_endpoints", [])
        self.schemas = index_data.get("schemas", [])
        self.symbol_index = index_data.get("symbol_index", {})
        self.router_prefixes = index_data.get("router_prefixes", {})

        # Build function lookup for fast description access
        self._func_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        for func in self.symbol_index.get("functions", []):
            key = (func.get("file", ""), func.get("name", ""))
            self._func_lookup[key] = func

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """
        Generate API reference documentation.

        Args:
            output_dir: Directory to write documentation files.

        Returns:
            Summary of generated files.
        """
        api_dir = output_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)

        # Group endpoints by file/router
        routers = self._group_by_router()

        generated_files = []
        for router_name, endpoints in routers.items():
            filename = self._sanitize_filename(router_name)
            filepath = api_dir / f"{filename}.md"

            content = self._generate_router_doc(router_name, endpoints)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(str(filepath))

        # Generate index file
        index_path = api_dir / "README.md"
        index_content = self._generate_api_index(routers)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "api",
            "files": generated_files,
            "routers": len(routers),
            "endpoints": len(self.endpoints),
        }

    def _group_by_router(self) -> dict[str, list[dict[str, Any]]]:
        """Group endpoints by their source file (router)."""
        routers: dict[str, list[dict[str, Any]]] = {}

        for endpoint in self.endpoints:
            file_path = endpoint.get("file", "unknown")
            # Extract router name from file path
            router_name = Path(file_path).stem

            if router_name not in routers:
                routers[router_name] = []
            routers[router_name].append(endpoint)

        # Sort endpoints within each router by path
        for router_name in routers:
            routers[router_name].sort(key=lambda e: (e.get("path", ""), e.get("method", "")))

        return routers

    def _sanitize_filename(self, name: str) -> str:
        """Convert router name to valid filename."""
        # Replace problematic characters
        safe_name = name.replace("/", "_").replace("\\", "_")
        safe_name = safe_name.replace(" ", "_").lower()
        return safe_name or "api"

    def _get_function_description(self, file_path: str, func_name: str) -> str:
        """Get function description from symbol_index (summary or docstring)."""
        key = (file_path, func_name)
        func_info = self._func_lookup.get(key)

        if not func_info:
            return ""

        # Prefer LLM summary, then docstring first line
        summary = func_info.get("summary", "")
        if summary:
            return summary

        docstring = func_info.get("docstring", "")
        if docstring:
            # Return first line of docstring
            first_line = docstring.split("\n")[0].strip()
            if first_line:
                return first_line[:100]

        return ""

    def _get_full_path(self, endpoint: dict[str, Any]) -> str:
        """Get full endpoint path including router prefix if available."""
        # Use stored full_path if available (calculated by scanner)
        stored_full_path = endpoint.get("full_path")
        if stored_full_path:
            return stored_full_path

        # Fallback: recalculate from prefix mapping
        path = endpoint.get("path", "/")
        file_path = endpoint.get("file", "")

        # Check if we have a prefix for this router file
        prefix = self.router_prefixes.get(file_path, "")
        if prefix:
            # Combine prefix and path, avoiding double slashes
            if prefix.endswith("/") and path.startswith("/"):
                return prefix + path[1:]
            elif not prefix.endswith("/") and not path.startswith("/"):
                return prefix + "/" + path
            else:
                return prefix + path

        return path

    def _generate_router_doc(self, router_name: str, endpoints: list[dict[str, Any]]) -> str:
        """Generate documentation for a single router."""
        lines = []

        # Header
        title = router_name.replace("_", " ").title()
        lines.append(f"# {title} API")
        lines.append("")

        # Get base path from first endpoint (if consistent)
        base_paths = set()
        for ep in endpoints:
            path = ep.get("path", "")
            parts = path.split("/")
            if len(parts) > 2:
                base_paths.add("/".join(parts[:3]))

        if len(base_paths) == 1:
            lines.append(f"**Base path:** `{base_paths.pop()}`")
            lines.append("")

        # Source file
        if endpoints:
            source_file = endpoints[0].get("file", "")
            if source_file:
                lines.append(f"**Source:** `{source_file}`")
                lines.append("")

        lines.append("## Endpoints")
        lines.append("")

        # Table of contents
        lines.append("| Method | Path | Description |")
        lines.append("|--------|------|-------------|")
        for ep in endpoints:
            method = ep.get("method", "GET").upper()
            path = self._get_full_path(ep)
            func_name = ep.get("function", "") or ep.get("handler", "")
            file_path = ep.get("file", "")

            # Get description: prefer endpoint's description (from decorator/docstring),
            # then lookup from symbol_index, then humanized function name
            desc = ep.get("description", "")
            if not desc:
                desc = self._get_function_description(file_path, func_name)
            if not desc:
                # Fallback to humanized function name
                desc = func_name.replace("_", " ").title() if func_name else "-"
            elif len(desc) > 60:
                desc = desc[:57] + "..."

            lines.append(f"| `{method}` | `{path}` | {desc} |")
        lines.append("")

        # Detailed endpoint documentation
        for ep in endpoints:
            lines.extend(self._format_endpoint(ep))
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_endpoint(self, endpoint: dict[str, Any]) -> list[str]:
        """Format a single endpoint as markdown."""
        lines = []

        method = endpoint.get("method", "GET").upper()
        path = self._get_full_path(endpoint)
        func_name = endpoint.get("function", "") or endpoint.get("handler", "")
        auth = endpoint.get("auth_required", False)
        file_path = endpoint.get("file", "")
        line = endpoint.get("line", 0)

        # Header
        lines.append(f"### {method} {path}")
        lines.append("")

        # Description: prefer endpoint's description, then lookup from symbol_index
        desc = endpoint.get("description", "")
        if not desc:
            desc = self._get_function_description(file_path, func_name)
        if desc:
            lines.append(desc)
            lines.append("")

        # Function name and location
        if func_name:
            lines.append(f"**Function:** `{func_name}`")
            if file_path and line:
                lines.append(f"**Location:** `{file_path}:{line}`")
            lines.append("")

        # Auth requirement
        auth_str = "Required" if auth else "Not required"
        lines.append(f"**Authentication:** {auth_str}")
        lines.append("")

        # Path parameters
        path_params = endpoint.get("path_params", [])
        if path_params:
            lines.append("**Path Parameters:**")
            lines.append("")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for param in path_params:
                if isinstance(param, dict):
                    p_name = param.get("name", "")
                    p_type = param.get("type", "string")
                    lines.append(f"| `{p_name}` | `{p_type}` | - |")
                else:
                    lines.append(f"| `{param}` | `string` | - |")
            lines.append("")

        # Query parameters
        query_params = endpoint.get("query_params", [])
        if query_params:
            lines.append("**Query Parameters:**")
            lines.append("")
            lines.append("| Name | Type | Required | Default |")
            lines.append("|------|------|----------|---------|")
            for param in query_params:
                if isinstance(param, dict):
                    p_name = param.get("name", "")
                    p_type = param.get("type", "string")
                    p_required = "Yes" if param.get("required") else "No"
                    p_default = param.get("default", "-")
                    lines.append(f"| `{p_name}` | `{p_type}` | {p_required} | {p_default} |")
                else:
                    lines.append(f"| `{param}` | `string` | No | - |")
            lines.append("")

        # Request body schema
        request_schema = endpoint.get("request_schema")
        if request_schema:
            lines.append("**Request Body:**")
            lines.append("")
            lines.append(f"Schema: `{request_schema}`")
            lines.append("")
            # Try to find schema details
            schema_info = self._find_schema(request_schema)
            if schema_info:
                lines.extend(self._format_schema_fields(schema_info))

        # Response schema
        response_schema = endpoint.get("response_schema")
        if response_schema:
            lines.append("**Response:**")
            lines.append("")
            lines.append(f"Schema: `{response_schema}`")
            lines.append("")
            schema_info = self._find_schema(response_schema)
            if schema_info:
                lines.extend(self._format_schema_fields(schema_info))

        # Example curl command
        lines.append("**Example:**")
        lines.append("")
        lines.append("```bash")
        curl_cmd = self._generate_curl_example(endpoint)
        lines.append(curl_cmd)
        lines.append("```")
        lines.append("")

        return lines

    def _find_schema(self, schema_name: str) -> dict[str, Any] | None:
        """Find schema details by name."""
        for schema in self.schemas:
            if schema.get("name") == schema_name:
                return schema
        return None

    def _format_schema_fields(self, schema: dict[str, Any]) -> list[str]:
        """Format schema fields as a table."""
        lines = []
        fields = schema.get("fields", [])

        if not fields:
            return lines

        lines.append("| Field | Type | Required |")
        lines.append("|-------|------|----------|")

        for field in fields:
            if isinstance(field, dict):
                f_name = field.get("name", "")
                f_type = field.get("type", "any")
                f_required = "Yes" if field.get("required") else "No"
                lines.append(f"| `{f_name}` | `{f_type}` | {f_required} |")
            elif isinstance(field, str):
                lines.append(f"| `{field}` | - | - |")

        lines.append("")
        return lines

    def _generate_curl_example(self, endpoint: dict[str, Any]) -> str:
        """Generate a curl example for the endpoint."""
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path", "/")
        auth = endpoint.get("auth_required", False)

        # Replace path parameters with placeholders
        example_path = path
        for param in endpoint.get("path_params", []):
            if isinstance(param, dict):
                param_name = param.get("name", "")
            else:
                param_name = param
            example_path = example_path.replace(f"{{{param_name}}}", f"{{YOUR_{param_name.upper()}}}")

        parts = [f"curl -X {method}"]
        parts.append(f"http://localhost:8000{example_path}")

        if auth:
            parts.append('-H "Authorization: Bearer {YOUR_TOKEN}"')

        if method in ("POST", "PUT", "PATCH"):
            parts.append('-H "Content-Type: application/json"')
            request_schema = endpoint.get("request_schema")
            if request_schema:
                parts.append(f"-d '{{\"...\": \"see {request_schema} schema\"}}'")
            else:
                parts.append("-d '{}'")

        # Format with line continuation for readability
        if len(parts) > 2:
            return " \\\n  ".join(parts)
        return " ".join(parts)

    def _generate_api_index(self, routers: dict[str, list[dict[str, Any]]]) -> str:
        """Generate the API index/README file."""
        lines = []

        lines.append("# API Reference")
        lines.append("")
        lines.append("Auto-generated API documentation from codebase-index.")
        lines.append("")

        # Summary
        total_endpoints = sum(len(eps) for eps in routers.values())
        lines.append(f"**Total Routers:** {len(routers)}")
        lines.append(f"**Total Endpoints:** {total_endpoints}")
        lines.append("")

        # Handle empty API case
        if not routers:
            lines.append("*No API endpoints detected in this project.*")
            lines.append("")
            lines.append("This project may not have HTTP API endpoints, or they may use ")
            lines.append("a framework not currently supported by codebase-index.")
            lines.append("")
            return "\n".join(lines)

        # Table of routers
        lines.append("## Routers")
        lines.append("")
        lines.append("| Router | Endpoints | File |")
        lines.append("|--------|-----------|------|")

        for router_name, endpoints in sorted(routers.items()):
            filename = self._sanitize_filename(router_name)
            count = len(endpoints)
            source = endpoints[0].get("file", "") if endpoints else ""
            lines.append(f"| [{router_name}]({filename}.md) | {count} | `{source}` |")

        lines.append("")
        return "\n".join(lines)


def generate_api_reference(
    index_data: dict[str, Any],
    output_dir: Path,
    template_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Convenience function to generate API reference documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.
        template_dir: Optional custom templates directory.

    Returns:
        Summary of generated files.
    """
    generator = APIReferenceGenerator(index_data)
    return generator.generate(output_dir)


class ModuleREADMEGenerator:
    """
    Generate README files for each module/directory.

    Creates markdown documentation summarizing each module's contents,
    key symbols, dependencies, and related files.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the module README generator.

        Args:
            index_data: The loaded codebase index.
        """
        self.index_data = index_data
        self.files = index_data.get("files", [])
        self.symbol_index = index_data.get("symbol_index", {})
        self.call_graph = index_data.get("call_graph", {})
        self.summaries = index_data.get("summaries", {}).get("cache", {})

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """
        Generate module README files.

        Args:
            output_dir: Directory to write documentation files.

        Returns:
            Summary of generated files.
        """
        modules_dir = output_dir / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)

        # Group files by directory (module)
        modules = self._group_by_module()

        generated_files = []
        for module_path, module_files in modules.items():
            # Create safe filename from module path
            safe_name = module_path.replace("/", "_").replace("\\", "_") or "root"
            filepath = modules_dir / f"{safe_name}.md"

            content = self._generate_module_doc(module_path, module_files)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(str(filepath))

        # Generate index
        index_path = modules_dir / "README.md"
        index_content = self._generate_modules_index(modules)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "modules",
            "files": generated_files,
            "modules": len(modules),
        }

    def _group_by_module(self) -> dict[str, list[dict[str, Any]]]:
        """Group files by their parent directory."""
        modules: dict[str, list[dict[str, Any]]] = {}

        for file_info in self.files:
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            # Get parent directory as module
            parent = str(Path(file_path).parent)
            if parent == ".":
                parent = "root"

            if parent not in modules:
                modules[parent] = []
            modules[parent].append(file_info)

        # Sort files within each module
        for module in modules:
            modules[module].sort(key=lambda f: f.get("path", ""))

        return modules

    def _generate_module_doc(self, module_path: str, files: list[dict[str, Any]]) -> str:
        """Generate documentation for a single module."""
        lines = []

        # Header
        module_name = Path(module_path).name or "Root"
        lines.append(f"# {module_name}")
        lines.append("")
        lines.append(f"**Path:** `{module_path}`")
        lines.append("")

        # Module summary from file summaries
        module_summary = self._get_module_summary(files)
        if module_summary:
            lines.append("## Overview")
            lines.append("")
            lines.append(module_summary)
            lines.append("")

        # Files table
        lines.append("## Files")
        lines.append("")
        lines.append("| File | Category | Lines | Purpose |")
        lines.append("|------|----------|-------|---------|")

        for f in files:
            fname = Path(f.get("path", "")).name
            category = f.get("category", "-")
            line_count = f.get("lines", 0)
            # Get file summary - check direct field first, then hash lookup, then docstring fallback
            summary = f.get("summary", "")
            if not summary:
                file_hash = f.get("hash", "")
                summary = self.summaries.get(file_hash, {}).get("summary", "")
            if not summary:
                # Fallback: use first class/function docstring as file purpose
                exports = f.get("exports", {})
                for cls in exports.get("classes", []):
                    if cls.get("docstring"):
                        summary = cls["docstring"].split("\n")[0].strip()
                        break
                if not summary:
                    for func in exports.get("functions", []):
                        if func.get("docstring"):
                            summary = func["docstring"].split("\n")[0].strip()
                            break
            if not summary:
                summary = "-"
            lines.append(f"| `{fname}` | {category} | {line_count} | {summary} |")

        lines.append("")

        # Key classes and functions
        classes, functions = self._get_symbols_in_module(module_path)

        if classes:
            lines.append("## Classes")
            lines.append("")
            for cls in classes:  # Show all classes
                cls_name = cls.get("name", "")
                cls_summary = cls.get("summary", cls.get("docstring", ""))
                if cls_summary:
                    lines.append(f"### {cls_name}")
                    lines.append("")
                    lines.append(cls_summary)
                    lines.append("")

                # List methods
                methods = self._get_methods_for_class(cls_name, module_path)
                if methods:
                    lines.append("**Methods:**")
                    for m in methods:  # Show all methods
                        m_name = m.get("name", "")
                        # Prefer summary, then docstring first line
                        m_desc = m.get("summary", "")
                        if not m_desc:
                            docstring = m.get("docstring", "")
                            if docstring:
                                m_desc = docstring.split("\n")[0].strip()
                        # For __init__, provide a sensible default
                        if not m_desc and m_name == "__init__":
                            m_desc = f"Initialize {cls_name}"
                        lines.append(f"- `{m_name}()` - {m_desc or '-'}")
                    lines.append("")

        if functions:
            lines.append("## Functions")
            lines.append("")
            lines.append("| Function | Description |")
            lines.append("|----------|-------------|")
            for func in functions:  # Show all functions
                func_name = func.get("name", "")
                func_summary = func.get("summary", func.get("docstring", "-"))
                lines.append(f"| `{func_name}()` | {func_summary or '-'} |")
            lines.append("")

        # Dependencies
        internal_deps, external_deps = self._get_dependencies(files)

        if internal_deps or external_deps:
            lines.append("## Dependencies")
            lines.append("")

            if internal_deps:
                lines.append("**Internal:**")
                for dep in sorted(internal_deps)[:10]:
                    lines.append(f"- `{dep}`")
                if len(internal_deps) > 10:
                    lines.append(f"- ... and {len(internal_deps) - 10} more")
                lines.append("")

            if external_deps:
                lines.append("**External:**")
                for dep in sorted(external_deps)[:10]:
                    lines.append(f"- `{dep}`")
                if len(external_deps) > 10:
                    lines.append(f"- ... and {len(external_deps) - 10} more")
                lines.append("")

        return "\n".join(lines)

    def _get_module_summary(self, files: list[dict[str, Any]]) -> str:
        """Generate a module summary from file summaries."""
        summaries = []
        for f in files:
            # Check direct summary field first
            summary = f.get("summary", "")
            if not summary:
                # Fall back to hash lookup
                file_hash = f.get("hash", "")
                if file_hash and file_hash in self.summaries:
                    summary = self.summaries[file_hash].get("summary", "")
            if summary:
                summaries.append(summary)

        if not summaries:
            return ""

        # Combine first few summaries
        if len(summaries) == 1:
            return summaries[0]

        # Return combined summary
        combined = " ".join(summaries[:3])
        if len(combined) > 300:
            combined = combined[:297] + "..."
        return combined

    def _get_symbols_in_module(
        self, module_path: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Get classes and functions defined in this module."""
        classes = []
        functions = []

        for cls in self.symbol_index.get("classes", []):
            file_path = cls.get("file", "")
            if file_path.startswith(module_path + "/") or Path(file_path).parent == Path(module_path):
                classes.append(cls)

        for func in self.symbol_index.get("functions", []):
            file_path = func.get("file", "")
            if file_path.startswith(module_path + "/") or Path(file_path).parent == Path(module_path):
                functions.append(func)

        return classes, functions

    def _get_methods_for_class(self, class_name: str, module_path: str) -> list[dict[str, Any]]:
        """Get methods for a class in this module."""
        methods = []
        for method in self.symbol_index.get("methods", []):
            if method.get("class") == class_name:
                file_path = method.get("file", "")
                if file_path.startswith(module_path + "/") or Path(file_path).parent == Path(module_path):
                    methods.append(method)
        return methods

    def _get_dependencies(
        self, files: list[dict[str, Any]]
    ) -> tuple[set[str], set[str]]:
        """Get internal and external dependencies for module files."""
        internal: set[str] = set()
        external: set[str] = set()

        for f in files:
            imports = f.get("imports", {})
            for imp in imports.get("internal", []):
                internal.add(imp)
            for imp in imports.get("external", []):
                # Extract just the package name
                pkg = imp.split(".")[0]
                external.add(pkg)

        return internal, external

    def _generate_modules_index(self, modules: dict[str, list[dict[str, Any]]]) -> str:
        """Generate the modules index/README file."""
        lines = []

        lines.append("# Modules Reference")
        lines.append("")
        lines.append("Auto-generated module documentation from codebase-index.")
        lines.append("")

        # Summary
        total_files = sum(len(files) for files in modules.values())
        lines.append(f"**Total Modules:** {len(modules)}")
        lines.append(f"**Total Files:** {total_files}")
        lines.append("")

        # Table of modules
        lines.append("## Modules")
        lines.append("")
        lines.append("| Module | Files | Description |")
        lines.append("|--------|-------|-------------|")

        for module_path in sorted(modules.keys()):
            files = modules[module_path]
            safe_name = module_path.replace("/", "_").replace("\\", "_") or "root"
            count = len(files)

            # Get brief description from first file's summary
            desc = "-"
            if files:
                first_hash = files[0].get("hash", "")
                if first_hash in self.summaries:
                    desc = self.summaries[first_hash].get("summary", "-")
                    if len(desc) > 50:
                        desc = desc[:47] + "..."

            lines.append(f"| [{module_path}]({safe_name}.md) | {count} | {desc} |")

        lines.append("")
        return "\n".join(lines)


def generate_module_readmes(
    index_data: dict[str, Any],
    output_dir: Path,
    template_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Convenience function to generate module README documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.
        template_dir: Optional custom templates directory.

    Returns:
        Summary of generated files.
    """
    generator = ModuleREADMEGenerator(index_data)
    return generator.generate(output_dir)


class FunctionReferenceGenerator:
    """
    Generate detailed function/class reference documentation.

    Creates comprehensive documentation for each symbol including
    signatures, parameters, call graph info, and tests.
    """

    def __init__(self, index_data: dict[str, Any], root: Path | None = None) -> None:
        """
        Initialize the function reference generator.

        Args:
            index_data: The loaded codebase index.
            root: Root directory for reading source files.
        """
        self.index_data = index_data
        self.root = root
        self.symbol_index = index_data.get("symbol_index", {})
        self.call_graph = index_data.get("call_graph", {})
        self.test_coverage = index_data.get("test_coverage", {})

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """
        Generate function reference documentation.

        Args:
            output_dir: Directory to write documentation files.

        Returns:
            Summary of generated files.
        """
        ref_dir = output_dir / "reference"
        ref_dir.mkdir(parents=True, exist_ok=True)

        # Group symbols by file/module
        modules = self._group_by_file()

        generated_files = []
        total_symbols = 0

        for file_path, symbols in modules.items():
            # Create safe filename
            safe_name = file_path.replace("/", "_").replace("\\", "_")
            safe_name = safe_name.replace(".py", "").replace(".ts", "").replace(".js", "")
            filepath = ref_dir / f"{safe_name}.md"

            content = self._generate_file_reference(file_path, symbols)
            total_symbols += len(symbols.get("classes", [])) + len(symbols.get("functions", []))

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(str(filepath))

        # Generate index
        index_path = ref_dir / "README.md"
        index_content = self._generate_reference_index(modules)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "reference",
            "files": generated_files,
            "modules": len(modules),
            "symbols": total_symbols,
        }

    def _group_by_file(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        """Group symbols by their source file."""
        modules: dict[str, dict[str, list[dict[str, Any]]]] = {}

        # Group classes
        for cls in self.symbol_index.get("classes", []):
            file_path = cls.get("file", "")
            if not file_path:
                continue
            if file_path not in modules:
                modules[file_path] = {"classes": [], "functions": [], "methods": []}
            modules[file_path]["classes"].append(cls)

        # Group functions
        for func in self.symbol_index.get("functions", []):
            file_path = func.get("file", "")
            if not file_path:
                continue
            if file_path not in modules:
                modules[file_path] = {"classes": [], "functions": [], "methods": []}
            modules[file_path]["functions"].append(func)

        # Group methods with their classes
        for method in self.symbol_index.get("methods", []):
            file_path = method.get("file", "")
            if not file_path:
                continue
            if file_path not in modules:
                modules[file_path] = {"classes": [], "functions": [], "methods": []}
            modules[file_path]["methods"].append(method)

        return modules

    def _generate_file_reference(
        self, file_path: str, symbols: dict[str, list[dict[str, Any]]]
    ) -> str:
        """Generate reference documentation for a file."""
        lines = []

        # Header
        module_name = Path(file_path).stem
        lines.append(f"# {module_name} Reference")
        lines.append("")
        lines.append(f"**File:** `{file_path}`")
        lines.append("")

        classes = symbols.get("classes", [])
        functions = symbols.get("functions", [])
        methods = symbols.get("methods", [])

        # Table of contents
        if classes or functions:
            lines.append("## Contents")
            lines.append("")
            if classes:
                lines.append("### Classes")
                for cls in classes:
                    cls_name = cls.get("name", "")
                    lines.append(f"- [{cls_name}](#{cls_name.lower()})")
                lines.append("")
            if functions:
                lines.append("### Functions")
                for func in functions:
                    func_name = func.get("name", "")
                    lines.append(f"- [{func_name}](#{func_name.lower()})")
                lines.append("")
            lines.append("---")
            lines.append("")

        # Document classes
        if classes:
            lines.append("## Classes")
            lines.append("")

            for cls in classes:
                lines.extend(self._format_class(cls, methods, file_path))
                lines.append("---")
                lines.append("")

        # Document functions
        if functions:
            lines.append("## Functions")
            lines.append("")

            for func in functions:
                lines.extend(self._format_function(func, file_path))
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _format_class(
        self, cls: dict[str, Any], all_methods: list[dict[str, Any]], file_path: str
    ) -> list[str]:
        """Format a class as markdown."""
        lines = []

        name = cls.get("name", "")
        line_num = cls.get("line", 0)
        docstring = cls.get("docstring", "")
        summary = cls.get("summary", "")
        bases = cls.get("bases", [])

        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"**Location:** `{file_path}:{line_num}`")

        if bases:
            bases_str = ", ".join(f"`{b}`" for b in bases)
            lines.append(f"**Inherits:** {bases_str}")
        lines.append("")

        # Summary or docstring
        if summary:
            lines.append(summary)
            lines.append("")
        elif docstring:
            lines.append(docstring)
            lines.append("")

        # Get methods for this class
        class_methods = [m for m in all_methods if m.get("class") == name]

        if class_methods:
            lines.append("#### Methods")
            lines.append("")

            for method in class_methods:
                lines.extend(self._format_method(method, file_path))

        # Callers
        callers = self._get_callers(name, file_path)
        if callers:
            lines.append("#### Used By")
            lines.append("")
            for caller in callers[:10]:
                c_name = caller.get("name", "")
                c_file = caller.get("file", "")
                lines.append(f"- `{c_name}` in `{c_file}`")
            if len(callers) > 10:
                lines.append(f"- ... and {len(callers) - 10} more")
            lines.append("")

        # Tests
        tests = self._get_tests(name)
        if tests:
            lines.append("#### Tests")
            lines.append("")
            for test in tests[:5]:
                test_file = test.get("file", "")
                lines.append(f"- `{test_file}`")
            lines.append("")

        return lines

    def _format_method(self, method: dict[str, Any], file_path: str) -> list[str]:
        """Format a method as markdown."""
        lines = []

        name = method.get("name", "")
        line_num = method.get("line", 0)
        signature = method.get("signature", {})
        summary = method.get("summary", "")
        docstring = method.get("docstring", "")

        lines.append(f"##### `{name}()`")
        lines.append("")

        # Signature
        formatted_sig = signature.get("formatted")
        if formatted_sig:
            lines.append("```python")
            lines.append(formatted_sig)
            lines.append("```")
            lines.append("")

        # Summary
        if summary:
            lines.append(summary)
            lines.append("")
        elif docstring:
            # Truncate long docstrings
            if len(docstring) > 200:
                docstring = docstring[:197] + "..."
            lines.append(docstring)
            lines.append("")

        # Parameters
        params = signature.get("params", [])
        if params:
            lines.append("**Parameters:**")
            lines.append("")
            for p in params:
                p_name = p.get("name", "")
                p_type = p.get("type", "")
                if p_type:
                    lines.append(f"- `{p_name}`: `{p_type}`")
                else:
                    lines.append(f"- `{p_name}`")
            lines.append("")

        # Return type
        return_type = signature.get("return_type")
        if return_type:
            lines.append(f"**Returns:** `{return_type}`")
            lines.append("")

        return lines

    def _format_function(self, func: dict[str, Any], file_path: str) -> list[str]:
        """Format a function as markdown."""
        lines = []

        name = func.get("name", "")
        line_num = func.get("line", 0)
        signature = func.get("signature", {})
        summary = func.get("summary", "")
        docstring = func.get("docstring", "")

        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"**Location:** `{file_path}:{line_num}`")
        lines.append("")

        # Signature
        formatted_sig = signature.get("formatted")
        if formatted_sig:
            lines.append("```python")
            lines.append(formatted_sig)
            lines.append("```")
            lines.append("")

        # Summary
        if summary:
            lines.append(summary)
            lines.append("")
        elif docstring:
            lines.append(docstring)
            lines.append("")

        # Parameters
        params = signature.get("params", [])
        if params:
            lines.append("**Parameters:**")
            lines.append("")
            lines.append("| Name | Type | Default |")
            lines.append("|------|------|---------|")
            for p in params:
                p_name = p.get("name", "")
                p_type = p.get("type", "-")
                p_default = "..." if p.get("has_default") else "-"
                lines.append(f"| `{p_name}` | `{p_type}` | {p_default} |")
            lines.append("")

        # Return type
        return_type = signature.get("return_type")
        if return_type:
            lines.append(f"**Returns:** `{return_type}`")
            lines.append("")

        # What it calls
        calls = self._get_calls(name, file_path)
        if calls:
            lines.append("**Calls:**")
            lines.append("")
            for call in calls[:10]:
                lines.append(f"- `{call}`")
            if len(calls) > 10:
                lines.append(f"- ... and {len(calls) - 10} more")
            lines.append("")

        # What calls it
        callers = self._get_callers(name, file_path)
        if callers:
            lines.append("**Called By:**")
            lines.append("")
            for caller in callers[:10]:
                c_name = caller.get("name", "")
                c_file = caller.get("file", "")
                lines.append(f"- `{c_name}` in `{c_file}`")
            if len(callers) > 10:
                lines.append(f"- ... and {len(callers) - 10} more")
            lines.append("")

        # Tests
        tests = self._get_tests(name)
        if tests:
            lines.append("**Tests:**")
            lines.append("")
            for test in tests[:5]:
                test_file = test.get("file", "")
                lines.append(f"- `{test_file}`")
            lines.append("")

        return lines

    def _get_calls(self, name: str, file_path: str) -> list[str]:
        """Get functions that this symbol calls."""
        for func_key, func_data in self.call_graph.items():
            if name in func_key:
                return func_data.get("calls", [])[:20]
        return []

    def _get_callers(self, name: str, file_path: str) -> list[dict[str, Any]]:
        """Get functions that call this symbol."""
        callers = []

        # Extract base name for matching
        base_name = name.split(".")[-1].lower() if "." in name else name.lower()

        for func_key, func_data in self.call_graph.items():
            calls_list = func_data.get("calls", [])

            for call in calls_list:
                call_lower = call.lower()
                call_base = call.split(".")[-1].lower() if "." in call else call_lower

                # Match: exact match, or call ends with our name, or base names match
                is_match = (
                    call_lower == name.lower() or
                    call_lower == base_name or
                    call_base == base_name or
                    call_lower.endswith("." + base_name)
                )

                if is_match:
                    if ":" in func_key:
                        caller_file, caller_name = func_key.split(":", 1)
                    else:
                        caller_file, caller_name = "", func_key

                    callers.append({
                        "name": caller_name,
                        "file": caller_file,
                    })
                    break

        return callers[:20]

    def _get_tests(self, name: str) -> list[dict[str, Any]]:
        """Get tests for this symbol."""
        tests = []

        # test_coverage structure: {"covered": [{"source": ..., "test": ...}], ...}
        covered = self.test_coverage.get("covered", [])

        for entry in covered:
            source = entry.get("source", "")
            test_file = entry.get("test", "")
            # Check if the symbol name appears in the source path
            if name.lower() in source.lower():
                tests.append({"file": test_file})

        return tests[:10]

    def _generate_reference_index(
        self, modules: dict[str, dict[str, list[dict[str, Any]]]]
    ) -> str:
        """Generate the reference index/README file."""
        lines = []

        lines.append("# Function Reference")
        lines.append("")
        lines.append("Auto-generated function and class reference from codebase-index.")
        lines.append("")

        # Summary
        total_classes = sum(
            len(syms.get("classes", [])) for syms in modules.values()
        )
        total_functions = sum(
            len(syms.get("functions", [])) for syms in modules.values()
        )
        lines.append(f"**Total Files:** {len(modules)}")
        lines.append(f"**Total Classes:** {total_classes}")
        lines.append(f"**Total Functions:** {total_functions}")
        lines.append("")

        # Table of files
        lines.append("## Files")
        lines.append("")
        lines.append("| File | Classes | Functions |")
        lines.append("|------|---------|-----------|")

        for file_path in sorted(modules.keys()):
            symbols = modules[file_path]
            safe_name = file_path.replace("/", "_").replace("\\", "_")
            safe_name = safe_name.replace(".py", "").replace(".ts", "").replace(".js", "")
            num_classes = len(symbols.get("classes", []))
            num_functions = len(symbols.get("functions", []))
            lines.append(f"| [{file_path}]({safe_name}.md) | {num_classes} | {num_functions} |")

        lines.append("")
        return "\n".join(lines)


def generate_function_reference(
    index_data: dict[str, Any],
    output_dir: Path,
    root: Path | None = None,
    template_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Convenience function to generate function reference documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.
        root: Root directory for reading source files.
        template_dir: Optional custom templates directory.

    Returns:
        Summary of generated files.
    """
    generator = FunctionReferenceGenerator(index_data, root=root)
    return generator.generate(output_dir)


class DocDiffChecker:
    """
    Check documentation freshness against source files.

    Compares modification times between generated docs and their
    corresponding source files to identify stale documentation.
    """

    def __init__(
        self, index_data: dict[str, Any], doc_dir: Path, root: Path
    ) -> None:
        """
        Initialize the doc diff checker.

        Args:
            index_data: The loaded codebase index.
            doc_dir: Directory containing generated documentation.
            root: Root directory of the codebase.
        """
        self.index_data = index_data
        self.doc_dir = Path(doc_dir)
        self.root = Path(root)
        self.files = index_data.get("files", [])
        self.api_endpoints = index_data.get("api_endpoints", [])

    def check(self) -> dict[str, Any]:
        """
        Check documentation freshness.

        Returns:
            Dictionary with stale, missing, and ok documentation.
        """
        stale = []
        missing = []
        ok = []

        # Check API docs
        api_results = self._check_api_docs()
        stale.extend(api_results["stale"])
        missing.extend(api_results["missing"])
        ok.extend(api_results["ok"])

        # Check module docs
        module_results = self._check_module_docs()
        stale.extend(module_results["stale"])
        missing.extend(module_results["missing"])
        ok.extend(module_results["ok"])

        # Check reference docs
        ref_results = self._check_reference_docs()
        stale.extend(ref_results["stale"])
        missing.extend(ref_results["missing"])
        ok.extend(ref_results["ok"])

        return {
            "stale": stale,
            "missing": missing,
            "ok": ok,
            "summary": f"{len(stale)} stale, {len(missing)} missing, {len(ok)} ok",
        }

    def _check_api_docs(self) -> dict[str, list[Any]]:
        """Check API documentation freshness."""
        stale = []
        missing = []
        ok = []

        api_dir = self.doc_dir / "api"

        # Group endpoints by router file
        routers: dict[str, list[dict[str, Any]]] = {}
        for ep in self.api_endpoints:
            file_path = ep.get("file", "")
            router_name = Path(file_path).stem
            if router_name not in routers:
                routers[router_name] = []
            routers[router_name].append(ep)

        for router_name, endpoints in routers.items():
            if not endpoints:
                continue

            source_file = endpoints[0].get("file", "")
            doc_file = api_dir / f"{router_name}.md"

            result = self._compare_times(source_file, doc_file)
            if result["status"] == "stale":
                stale.append(result)
            elif result["status"] == "missing":
                missing.append(result)
            else:
                ok.append(str(doc_file))

        return {"stale": stale, "missing": missing, "ok": ok}

    def _check_module_docs(self) -> dict[str, list[Any]]:
        """Check module documentation freshness."""
        stale = []
        missing = []
        ok = []

        modules_dir = self.doc_dir / "modules"

        # Group files by parent directory
        modules: dict[str, list[dict[str, Any]]] = {}
        for f in self.files:
            file_path = f.get("path", "")
            parent = str(Path(file_path).parent)
            if parent == ".":
                parent = "root"
            if parent not in modules:
                modules[parent] = []
            modules[parent].append(f)

        for module_path, files in modules.items():
            safe_name = module_path.replace("/", "_").replace("\\", "_") or "root"
            doc_file = modules_dir / f"{safe_name}.md"

            # Find most recently modified source file in module
            latest_source = None
            latest_time = 0

            for f in files:
                source_path = self.root / f.get("path", "")
                if source_path.exists():
                    mtime = source_path.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_source = f.get("path", "")

            if latest_source:
                result = self._compare_times(latest_source, doc_file)
                if result["status"] == "stale":
                    stale.append(result)
                elif result["status"] == "missing":
                    missing.append(result)
                else:
                    ok.append(str(doc_file))

        return {"stale": stale, "missing": missing, "ok": ok}

    def _check_reference_docs(self) -> dict[str, list[Any]]:
        """Check reference documentation freshness."""
        stale = []
        missing = []
        ok = []

        ref_dir = self.doc_dir / "reference"
        symbol_index = self.index_data.get("symbol_index", {})

        # Get unique source files from symbols
        source_files: set[str] = set()
        for cls in symbol_index.get("classes", []):
            source_files.add(cls.get("file", ""))
        for func in symbol_index.get("functions", []):
            source_files.add(func.get("file", ""))

        for source_file in source_files:
            if not source_file:
                continue

            safe_name = source_file.replace("/", "_").replace("\\", "_")
            safe_name = safe_name.replace(".py", "").replace(".ts", "").replace(".js", "")
            doc_file = ref_dir / f"{safe_name}.md"

            result = self._compare_times(source_file, doc_file)
            if result["status"] == "stale":
                stale.append(result)
            elif result["status"] == "missing":
                missing.append(result)
            else:
                ok.append(str(doc_file))

        return {"stale": stale, "missing": missing, "ok": ok}

    def _compare_times(self, source_file: str, doc_file: Path) -> dict[str, Any]:
        """Compare modification times between source and doc file."""
        source_path = self.root / source_file

        if not doc_file.exists():
            return {
                "status": "missing",
                "source": source_file,
                "suggested_doc": str(doc_file),
                "reason": "Documentation does not exist",
            }

        if not source_path.exists():
            # Source file doesn't exist, doc is orphaned but ok
            return {"status": "ok"}

        source_mtime = source_path.stat().st_mtime
        doc_mtime = doc_file.stat().st_mtime

        if source_mtime > doc_mtime:
            from datetime import datetime

            return {
                "status": "stale",
                "doc": str(doc_file),
                "source": source_file,
                "source_modified": datetime.fromtimestamp(source_mtime).isoformat(),
                "doc_modified": datetime.fromtimestamp(doc_mtime).isoformat(),
                "reason": "Source newer than documentation",
            }

        return {"status": "ok"}


def check_doc_freshness(
    index_data: dict[str, Any],
    doc_dir: Path,
    root: Path,
) -> dict[str, Any]:
    """
    Check documentation freshness against source files.

    Args:
        index_data: The codebase index.
        doc_dir: Directory containing generated documentation.
        root: Root directory of the codebase.

    Returns:
        Dictionary with stale, missing, and ok documentation.
    """
    checker = DocDiffChecker(index_data, doc_dir, root)
    return checker.check()


class ArchitectureGenerator:
    """
    Generate architecture documentation using LLM analysis.

    Creates high-level architecture docs including component diagrams,
    data flow, and design decisions based on call graph and coupling analysis.
    """

    def __init__(
        self,
        index_data: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """
        Initialize the architecture generator.

        Args:
            index_data: The loaded codebase index.
            provider: LLM provider (openrouter, anthropic, openai).
            model: Model to use.
            api_key: API key for the provider.
        """
        self.index_data = index_data
        self.provider = provider
        self.model = model
        self.api_key = api_key

        self.files = index_data.get("files", [])
        self.call_graph = index_data.get("call_graph", {})
        self.coupling = index_data.get("coupling_analysis", {})
        self.summaries = index_data.get("summaries", {}).get("cache", {})
        self.symbol_index = index_data.get("symbol_index", {})

        self._llm_client = None

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """
        Generate architecture documentation.

        Args:
            output_dir: Directory to write documentation files.

        Returns:
            Summary of generated files.
        """
        arch_dir = output_dir / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Identify major components/subsystems
        components = self._identify_components()

        # Generate main architecture overview
        overview_path = arch_dir / "overview.md"
        overview_content = self._generate_overview(components)
        with open(overview_path, "w", encoding="utf-8") as f:
            f.write(overview_content)
        generated_files.append(str(overview_path))

        # Generate component docs for major subsystems
        for component in components[:10]:  # Limit to top 10
            comp_name = component["name"]
            safe_name = comp_name.replace("/", "_").replace("\\", "_")
            comp_path = arch_dir / f"{safe_name}.md"

            comp_content = self._generate_component_doc(component)
            with open(comp_path, "w", encoding="utf-8") as f:
                f.write(comp_content)
            generated_files.append(str(comp_path))

        # Generate data flow doc
        flow_path = arch_dir / "data_flow.md"
        flow_content = self._generate_data_flow()
        with open(flow_path, "w", encoding="utf-8") as f:
            f.write(flow_content)
        generated_files.append(str(flow_path))

        # Generate index
        index_path = arch_dir / "README.md"
        index_content = self._generate_arch_index(components)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "architecture",
            "files": generated_files,
            "components": len(components),
        }

    def _identify_components(self) -> list[dict[str, Any]]:
        """Identify major components/subsystems from the codebase structure."""
        components: dict[str, dict[str, Any]] = {}

        # Group files by top-level directory
        for f in self.files:
            file_path = f.get("path", "")
            parts = Path(file_path).parts

            if len(parts) < 2:
                comp_name = "root"
            else:
                # Use first meaningful directory
                comp_name = parts[0]
                if comp_name in ("src", "lib", "app"):
                    comp_name = parts[1] if len(parts) > 1 else comp_name

            if comp_name not in components:
                components[comp_name] = {
                    "name": comp_name,
                    "files": [],
                    "classes": [],
                    "functions": [],
                    "coupling_score": None,  # None = not calculated, 0 = calculated as 0
                }

            components[comp_name]["files"].append(f)

        # Add symbols to components
        for cls in self.symbol_index.get("classes", []):
            file_path = cls.get("file", "")
            for comp_name, comp in components.items():
                if any(cf.get("path") == file_path for cf in comp["files"]):
                    comp["classes"].append(cls)
                    break

        for func in self.symbol_index.get("functions", []):
            file_path = func.get("file", "")
            for comp_name, comp in components.items():
                if any(cf.get("path") == file_path for cf in comp["files"]):
                    comp["functions"].append(func)
                    break

        # Calculate coupling scores
        for comp_name, comp in components.items():
            total_coupling = 0
            count = 0
            for f in comp["files"]:
                file_path = f.get("path", "")
                if file_path in self.coupling:
                    total_coupling += self.coupling[file_path].get("score", 0)
                    count += 1
            if count > 0:
                comp["coupling_score"] = total_coupling / count

        # Sort by file count (larger components first)
        sorted_components = sorted(
            components.values(),
            key=lambda c: len(c["files"]),
            reverse=True,
        )

        return sorted_components

    def _generate_overview(self, components: list[dict[str, Any]]) -> str:
        """Generate the architecture overview document."""
        lines = []

        lines.append("# Architecture Overview")
        lines.append("")

        # Project summary
        meta = self.index_data.get("meta", {})
        summary = self.index_data.get("summary", {})

        lines.append("## Project Summary")
        lines.append("")
        lines.append(f"- **Total Files:** {summary.get('total_files', 0)}")
        lines.append(f"- **Total Lines:** {summary.get('total_lines', 0):,}")
        languages = list(summary.get('by_language', {}).keys())
        if languages:
            lines.append(f"- **Languages:** {', '.join(languages)}")
        else:
            lines.append("- **Languages:** Not detected")
        lines.append("")

        # Component overview
        lines.append("## Components")
        lines.append("")

        # Check if any component has coupling data
        has_coupling = any(comp["coupling_score"] is not None for comp in components)

        if has_coupling:
            lines.append("| Component | Files | Classes | Functions | Coupling |")
            lines.append("|-----------|-------|---------|-----------|----------|")
        else:
            lines.append("| Component | Files | Classes | Functions |")
            lines.append("|-----------|-------|---------|-----------|")

        for comp in components[:15]:
            name = comp["name"]
            files = len(comp["files"])
            classes = len(comp["classes"])
            functions = len(comp["functions"])
            if has_coupling:
                coupling = f"{comp['coupling_score']:.2f}" if comp["coupling_score"] is not None else "-"
                lines.append(f"| `{name}` | {files} | {classes} | {functions} | {coupling} |")
            else:
                lines.append(f"| `{name}` | {files} | {classes} | {functions} |")

        lines.append("")

        # ASCII component diagram
        lines.append("## Component Diagram")
        lines.append("")
        lines.append("```")
        lines.extend(self._generate_ascii_diagram(components[:8]))
        lines.append("```")
        lines.append("")

        # Key architectural patterns
        lines.append("## Architectural Patterns")
        lines.append("")
        patterns = self._detect_patterns()
        for pattern in patterns:
            lines.append(f"- **{pattern['name']}:** {pattern['description']}")
        lines.append("")

        return "\n".join(lines)

    def _generate_ascii_diagram(self, components: list[dict[str, Any]]) -> list[str]:
        """Generate ASCII component diagram."""
        lines = []

        if not components:
            return ["No components found"]

        # Simple box diagram
        max_name_len = max(len(c["name"]) for c in components)
        box_width = max(max_name_len + 4, 20)

        # Draw components in rows
        row_size = 3
        for i in range(0, len(components), row_size):
            row = components[i : i + row_size]

            # Top border
            top_line = ""
            for comp in row:
                top_line += "+" + "-" * (box_width - 2) + "+  "
            lines.append(top_line.rstrip())

            # Component name
            name_line = ""
            for comp in row:
                name = comp["name"][:box_width - 4]
                padding = box_width - 4 - len(name)
                left_pad = padding // 2
                right_pad = padding - left_pad
                name_line += "|" + " " * left_pad + name + " " * right_pad + "|  "
            lines.append(name_line.rstrip())

            # Stats line
            stats_line = ""
            for comp in row:
                stats = f"{len(comp['files'])}f {len(comp['classes'])}c"
                stats = stats[:box_width - 4]
                padding = box_width - 4 - len(stats)
                left_pad = padding // 2
                right_pad = padding - left_pad
                stats_line += "|" + " " * left_pad + stats + " " * right_pad + "|  "
            lines.append(stats_line.rstrip())

            # Bottom border
            bot_line = ""
            for comp in row:
                bot_line += "+" + "-" * (box_width - 2) + "+  "
            lines.append(bot_line.rstrip())

            # Connection lines between rows
            if i + row_size < len(components):
                conn_line = ""
                for _ in row:
                    conn_line += " " * (box_width // 2) + "|" + " " * (box_width // 2) + " "
                lines.append(conn_line.rstrip())
                lines.append(conn_line.rstrip())

        return lines

    def _detect_patterns(self) -> list[dict[str, str]]:
        """Detect architectural patterns from the codebase."""
        patterns = []

        # Check for API layer
        api_files = [f for f in self.files if "router" in f.get("path", "").lower() or "api" in f.get("path", "").lower()]
        if api_files:
            patterns.append({
                "name": "API Layer",
                "description": f"REST/HTTP API with {len(api_files)} router files",
            })

        # Check for service layer
        service_files = [f for f in self.files if "service" in f.get("path", "").lower()]
        if service_files:
            patterns.append({
                "name": "Service Layer",
                "description": f"Business logic encapsulated in {len(service_files)} service files",
            })

        # Check for repository/data layer
        repo_files = [f for f in self.files if "repository" in f.get("path", "").lower() or "repo" in f.get("path", "").lower()]
        model_files = [f for f in self.files if "model" in f.get("path", "").lower()]
        if repo_files or model_files:
            patterns.append({
                "name": "Data Layer",
                "description": f"Data access with {len(repo_files)} repositories and {len(model_files)} models",
            })

        # Check for test coverage
        test_files = [f for f in self.files if "test" in f.get("path", "").lower()]
        if test_files:
            patterns.append({
                "name": "Test Suite",
                "description": f"{len(test_files)} test files for quality assurance",
            })

        # Check for schema/DTO layer
        schema_files = [f for f in self.files if "schema" in f.get("path", "").lower()]
        if schema_files:
            patterns.append({
                "name": "Schema/DTO Layer",
                "description": f"{len(schema_files)} schema files for data validation",
            })

        return patterns

    def _generate_component_doc(self, component: dict[str, Any]) -> str:
        """Generate documentation for a single component."""
        lines = []

        name = component["name"]
        lines.append(f"# {name.title()} Component")
        lines.append("")

        # Overview
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Files:** {len(component['files'])}")
        lines.append(f"- **Classes:** {len(component['classes'])}")
        lines.append(f"- **Functions:** {len(component['functions'])}")
        if component["coupling_score"] is not None:
            lines.append(f"- **Coupling Score:** {component['coupling_score']:.2f}")
        lines.append("")

        # Key classes
        if component["classes"]:
            lines.append("## Key Classes")
            lines.append("")
            for cls in component["classes"][:10]:
                cls_name = cls.get("name", "")
                summary = cls.get("summary", cls.get("docstring", ""))
                if summary:
                    summary = summary.split("\n")[0][:80]
                lines.append(f"### {cls_name}")
                lines.append("")
                if summary:
                    lines.append(summary)
                    lines.append("")
                file_path = cls.get("file", "")
                line_num = cls.get("line", 0)
                lines.append(f"**Location:** `{file_path}:{line_num}`")
                lines.append("")

        # Key functions
        if component["functions"]:
            lines.append("## Key Functions")
            lines.append("")
            lines.append("| Function | File | Description |")
            lines.append("|----------|------|-------------|")
            for func in component["functions"][:15]:
                func_name = func.get("name", "")
                file_path = Path(func.get("file", "")).name
                summary = func.get("summary", "-")
                if len(summary) > 50:
                    summary = summary[:47] + "..."
                lines.append(f"| `{func_name}` | `{file_path}` | {summary} |")
            lines.append("")

        # Files in component
        lines.append("## Files")
        lines.append("")
        lines.append("| File | Category | Lines |")
        lines.append("|------|----------|-------|")
        for f in component["files"][:20]:
            file_path = f.get("path", "")
            category = f.get("category", "-")
            line_count = f.get("lines", 0)
            lines.append(f"| `{file_path}` | {category} | {line_count} |")
        if len(component["files"]) > 20:
            lines.append(f"| ... | ... | *{len(component['files']) - 20} more* |")
        lines.append("")

        return "\n".join(lines)

    def _generate_data_flow(self) -> str:
        """Generate data flow documentation."""
        lines = []

        lines.append("# Data Flow")
        lines.append("")
        lines.append("This document describes how data flows through the system based on call graph analysis.")
        lines.append("")

        # Identify entry points (functions with many callers)
        caller_counts: dict[str, int] = {}

        for func_key, func_data in self.call_graph.items():
            for call in func_data.get("calls", []):
                # Filter out built-ins and common patterns
                if self._is_meaningful_function(call):
                    caller_counts[call] = caller_counts.get(call, 0) + 1

        # Sort by caller count
        sorted_functions = sorted(caller_counts.items(), key=lambda x: x[1], reverse=True)

        lines.append("## Most Called Functions")
        lines.append("")
        lines.append("These functions are central to the data flow:")
        lines.append("")
        lines.append("| Function | Times Called |")
        lines.append("|----------|--------------|")
        shown = 0
        for func_name, count in sorted_functions:
            if shown >= 20:
                break
            lines.append(f"| `{func_name}` | {count} |")
            shown += 1
        lines.append("")

        # Identify call chains
        lines.append("## Call Chains")
        lines.append("")
        lines.append("Key execution paths through the system:")
        lines.append("")

        # Find some interesting call chains
        chains = self._find_call_chains()
        for i, chain in enumerate(chains[:5], 1):
            lines.append(f"### Chain {i}")
            lines.append("")
            lines.append("```")
            lines.append(" → ".join(chain))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _find_call_chains(self, max_depth: int = 5) -> list[list[str]]:
        """Find interesting call chains from the call graph."""
        chains = []

        # Build a mapping of function names to their call graph keys
        func_name_to_key: dict[str, str] = {}
        for func_key in self.call_graph:
            # Extract function name from key (format: "file:func" or just "func")
            func_name = func_key.split(":")[-1] if ":" in func_key else func_key
            if self._is_meaningful_function(func_name):
                func_name_to_key[func_name] = func_key

        # Use BFS to find longer chains - try all paths
        def build_chain(start_name: str, start_calls: list[str]) -> list[str]:
            """Build the longest possible chain from a starting function."""
            best_chain = [start_name]
            queue = [(start_name, start_calls, [start_name])]

            while queue:
                current_name, current_calls, current_chain = queue.pop(0)

                if len(current_chain) >= max_depth:
                    if len(current_chain) > len(best_chain):
                        best_chain = current_chain[:]
                    continue

                found_next = False
                for call in current_calls:
                    if call in func_name_to_key and call not in current_chain:
                        next_key = func_name_to_key[call]
                        next_data = self.call_graph.get(next_key, {})
                        next_calls = [c for c in next_data.get("calls", [])
                                      if self._is_meaningful_function(c)]
                        new_chain = current_chain + [call]

                        if len(new_chain) > len(best_chain):
                            best_chain = new_chain[:]

                        # Continue exploring (limit branching to avoid explosion)
                        if len(queue) < 100:
                            queue.append((call, next_calls, new_chain))
                        found_next = True

                if not found_next and len(current_chain) > len(best_chain):
                    best_chain = current_chain[:]

            return best_chain

        # Find entry points - functions with many calls but rarely called
        starters = []
        for func_key, func_data in self.call_graph.items():
            func_name = func_key.split(":")[-1] if ":" in func_key else func_key
            if not self._is_meaningful_function(func_name):
                continue

            calls = [c for c in func_data.get("calls", []) if self._is_meaningful_function(c)]
            calls_in_graph = [c for c in calls if c in func_name_to_key]

            if len(calls_in_graph) >= 2:
                # Check if rarely called
                is_rarely_called = True
                for other_key, other_data in self.call_graph.items():
                    other_calls = other_data.get("calls", [])
                    if func_name in other_calls or func_key in other_calls:
                        is_rarely_called = False
                        break
                if is_rarely_called:
                    starters.append((func_name, calls_in_graph, len(calls_in_graph)))

        # Sort by number of meaningful calls (more calls = more interesting)
        starters.sort(key=lambda x: -x[2])

        # Build chains from top starters
        seen_chains = set()
        for func_name, calls, _ in starters[:20]:
            chain = build_chain(func_name, calls)
            chain_key = " → ".join(chain)
            if len(chain) >= 2 and chain_key not in seen_chains:
                chains.append(chain)
                seen_chains.add(chain_key)
                if len(chains) >= 5:
                    break

        return chains

    def _is_meaningful_function(self, func_name: str) -> bool:
        """Check if a function name is meaningful (not a built-in or common pattern)."""
        if not func_name:
            return False

        # Get base name (after last dot)
        base_name = func_name.split(".")[-1] if "." in func_name else func_name

        # Filter built-ins
        if base_name in BUILTIN_FUNCTIONS:
            return False

        # Filter common patterns like obj.get, list.append, etc.
        for pattern in FILTER_PATTERNS:
            if pattern in func_name:
                return False

        # Filter calls that look like attribute access (e.g., "file_info.get", "result[...].append")
        if "[" in func_name or "]" in func_name:
            return False

        # Filter very short names (likely variables or simple calls)
        if len(base_name) <= 2:
            return False

        # Filter names that are all lowercase and short (likely common methods)
        if base_name.islower() and len(base_name) <= 4 and base_name not in {"main", "init", "scan", "run", "load", "save"}:
            return False

        return True

    def _generate_arch_index(self, components: list[dict[str, Any]]) -> str:
        """Generate the architecture index/README file."""
        lines = []

        lines.append("# Architecture Documentation")
        lines.append("")
        lines.append("Auto-generated architecture documentation from codebase-index.")
        lines.append("")

        # Links
        lines.append("## Documents")
        lines.append("")
        lines.append("- [Overview](overview.md) - High-level architecture overview")
        lines.append("- [Data Flow](data_flow.md) - How data flows through the system")
        lines.append("")

        lines.append("## Component Documentation")
        lines.append("")
        for comp in components[:10]:
            name = comp["name"]
            safe_name = name.replace("/", "_").replace("\\", "_")
            files = len(comp["files"])
            lines.append(f"- [{name}]({safe_name}.md) - {files} files")
        lines.append("")

        return "\n".join(lines)


def generate_architecture_docs(
    index_data: dict[str, Any],
    output_dir: Path,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    template_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Generate architecture documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.
        provider: LLM provider for enhanced descriptions.
        model: Model to use.
        api_key: API key for the provider.
        template_dir: Optional custom templates directory.

    Returns:
        Summary of generated files.
    """
    generator = ArchitectureGenerator(
        index_data,
        provider=provider,
        model=model,
        api_key=api_key,
    )
    return generator.generate(output_dir)


class ProjectHealthGenerator:
    """
    Generate project health documentation.

    Creates pages for dependencies, code health, environment variables,
    and import analysis.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        """Initialize the project health generator."""
        self.index_data = index_data
        self.dependencies = index_data.get("dependencies", {})
        self.import_analysis = index_data.get("import_analysis", {})
        self.complexity = index_data.get("complexity_warnings", {})
        self.orphans = index_data.get("orphaned_files", {})
        self.duplicates = index_data.get("potential_duplicates", [])
        self.env_vars = index_data.get("environment_variables", {})
        self.test_coverage = index_data.get("test_coverage", {})

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate project health documentation."""
        health_dir = output_dir / "health"
        health_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Dependencies page
        deps_path = health_dir / "dependencies.md"
        deps_content = self._generate_dependencies_page()
        with open(deps_path, "w", encoding="utf-8") as f:
            f.write(deps_content)
        generated_files.append(str(deps_path))

        # Code health page
        health_path = health_dir / "code_health.md"
        health_content = self._generate_code_health_page()
        with open(health_path, "w", encoding="utf-8") as f:
            f.write(health_content)
        generated_files.append(str(health_path))

        # Environment variables page
        env_path = health_dir / "environment.md"
        env_content = self._generate_environment_page()
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)
        generated_files.append(str(env_path))

        # Import analysis page
        imports_path = health_dir / "imports.md"
        imports_content = self._generate_imports_page()
        with open(imports_path, "w", encoding="utf-8") as f:
            f.write(imports_content)
        generated_files.append(str(imports_path))

        # Index page
        index_path = health_dir / "README.md"
        index_content = self._generate_health_index()
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "health",
            "files": generated_files,
        }

    def _generate_dependencies_page(self) -> str:
        """Generate dependencies documentation."""
        lines = []
        lines.append("# Dependencies")
        lines.append("")
        lines.append("Project dependencies and their versions.")
        lines.append("")

        has_content = False

        # Python dependencies from pyproject.toml/requirements.txt
        python_deps = self.dependencies.get("python", [])
        if python_deps and isinstance(python_deps, list):
            # Filter out self-references and invalid entries
            valid_deps = [d for d in python_deps if isinstance(d, str) and d.replace("-", "").replace("_", "").isalnum()]
            if valid_deps:
                lines.append("## Python Dependencies")
                lines.append("")
                lines.append("| Package |")
                lines.append("|---------|")
                for dep in sorted(set(valid_deps)):
                    lines.append(f"| `{dep}` |")
                lines.append("")
                has_content = True

        # Node.js dependencies
        node_deps = self.dependencies.get("node", {})
        if node_deps:
            prod_deps = node_deps.get("dependencies", {})
            dev_deps = node_deps.get("devDependencies", {})

            if prod_deps or dev_deps:
                lines.append("## Node.js Dependencies")
                lines.append("")

                if prod_deps:
                    lines.append("### Production")
                    lines.append("")
                    lines.append("| Package | Version |")
                    lines.append("|---------|---------|")
                    for name, version in prod_deps.items():
                        lines.append(f"| `{name}` | {version} |")
                    lines.append("")

                if dev_deps:
                    lines.append("### Development")
                    lines.append("")
                    lines.append("| Package | Version |")
                    lines.append("|---------|---------|")
                    for name, version in dev_deps.items():
                        lines.append(f"| `{name}` | {version} |")
                    lines.append("")

                has_content = True

        if not has_content:
            lines.append("*No dependencies detected.*")
            lines.append("")

        return "\n".join(lines)

    def _generate_code_health_page(self) -> str:
        """Generate code health documentation."""
        lines = []
        lines.append("# Code Health")
        lines.append("")
        lines.append("Analysis of code quality issues including complexity, duplicates, and unused files.")
        lines.append("")

        # Summary
        complexity_issues = self.complexity.get("issues", [])
        orphan_files = self.orphans.get("orphaned", [])
        duplicate_groups = self.duplicates

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Complexity Issues:** {len(complexity_issues)}")
        lines.append(f"- **Orphaned Files:** {len(orphan_files)}")
        lines.append(f"- **Duplicate Groups:** {len(duplicate_groups)}")
        lines.append("")

        # Complexity warnings
        if complexity_issues:
            lines.append("## Complexity Warnings")
            lines.append("")
            lines.append("Files or functions that exceed recommended size thresholds.")
            lines.append("")
            lines.append("| File | Issue | Value | Threshold |")
            lines.append("|------|-------|-------|-----------|")
            for issue in complexity_issues[:20]:
                file_path = issue.get("file", "")
                issue_type = issue.get("type", "")
                value = issue.get("value", 0)
                threshold = issue.get("threshold", 0)
                lines.append(f"| `{file_path}` | {issue_type} | {value} | {threshold} |")
            if len(complexity_issues) > 20:
                lines.append(f"| ... | *{len(complexity_issues) - 20} more* | | |")
            lines.append("")

        # Orphaned files
        if orphan_files:
            lines.append("## Orphaned Files")
            lines.append("")
            lines.append("Files that are never imported anywhere in the codebase.")
            lines.append("")
            lines.append("| File | Lines | Reason |")
            lines.append("|------|-------|--------|")
            for orphan in orphan_files[:20]:
                if isinstance(orphan, dict):
                    file_path = orphan.get("file", "")
                    line_count = orphan.get("lines", 0)
                    reason = orphan.get("reason", "Not imported")
                else:
                    file_path = orphan
                    line_count = "-"
                    reason = "Not imported"
                lines.append(f"| `{file_path}` | {line_count} | {reason} |")
            if len(orphan_files) > 20:
                lines.append(f"| ... | | *{len(orphan_files) - 20} more* |")
            lines.append("")

        # Potential duplicates
        if duplicate_groups:
            lines.append("## Potential Duplicates")
            lines.append("")
            lines.append("Functions with similar signatures that may be duplicated.")
            lines.append("")
            for i, group in enumerate(duplicate_groups[:10], 1):
                lines.append(f"### Group {i}")
                lines.append("")
                functions = group.get("functions", [])
                if functions:
                    lines.append("| Function | File | Line |")
                    lines.append("|----------|------|------|")
                    for func in functions:
                        name = func.get("name", "")
                        file_path = func.get("file", "")
                        line_num = func.get("line", 0)
                        lines.append(f"| `{name}` | `{file_path}` | {line_num} |")
                lines.append("")
            if len(duplicate_groups) > 10:
                lines.append(f"*... and {len(duplicate_groups) - 10} more groups*")
                lines.append("")

        # Test coverage summary
        coverage = self.test_coverage
        if coverage:
            covered = coverage.get("covered", [])
            uncovered = coverage.get("uncovered", [])
            coverage_pct = coverage.get("coverage_percentage", 0)

            lines.append("## Test Coverage")
            lines.append("")
            lines.append(f"- **Coverage:** {coverage_pct:.1f}%")
            lines.append(f"- **Covered Files:** {len(covered)}")
            lines.append(f"- **Uncovered Files:** {len(uncovered)}")
            lines.append("")

            if uncovered:
                lines.append("### Uncovered Files")
                lines.append("")
                for f in uncovered[:10]:
                    if isinstance(f, dict):
                        file_path = f.get("source", f.get("file", ""))
                    else:
                        file_path = f
                    lines.append(f"- `{file_path}`")
                if len(uncovered) > 10:
                    lines.append(f"- *... and {len(uncovered) - 10} more*")
                lines.append("")

        return "\n".join(lines)

    def _generate_environment_page(self) -> str:
        """Generate environment variables documentation."""
        lines = []
        lines.append("# Environment Variables")
        lines.append("")
        lines.append("Environment variables used by this project.")
        lines.append("")

        if not self.env_vars:
            lines.append("*No environment variables detected.*")
            lines.append("")
            return "\n".join(lines)

        # Handle the actual data structure: {category: [var_names]} or {category: {file: [vars]}}
        all_vars: list[tuple[str, str]] = []  # (var_name, source)

        for category, data in self.env_vars.items():
            if isinstance(data, list):
                # Format: {"python_usage": ["VAR1", "VAR2"]}
                for var_name in data:
                    if isinstance(var_name, str) and var_name.isupper():
                        all_vars.append((var_name, category))
            elif isinstance(data, dict):
                # Format: {"dotenv_files": {"file.env": ["VAR1", "VAR2"]}}
                for file_path, vars_list in data.items():
                    if isinstance(vars_list, list):
                        for var_name in vars_list:
                            if isinstance(var_name, str):
                                all_vars.append((var_name, file_path))

        if not all_vars:
            lines.append("*No environment variables detected.*")
            lines.append("")
            return "\n".join(lines)

        # Deduplicate and sort
        seen = set()
        unique_vars = []
        for var_name, source in sorted(all_vars):
            if var_name not in seen:
                seen.add(var_name)
                unique_vars.append((var_name, source))

        lines.append("| Variable | Source |")
        lines.append("|----------|--------|")
        for var_name, source in unique_vars:
            # Clean up source name
            source_display = source.replace("_usage", "").replace("_", " ").title()
            lines.append(f"| `{var_name}` | {source_display} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_imports_page(self) -> str:
        """Generate import analysis documentation."""
        lines = []
        lines.append("# Import Analysis")
        lines.append("")
        lines.append("Analysis of imports including missing and unused dependencies.")
        lines.append("")

        missing = self.import_analysis.get("missing", [])
        unused = self.import_analysis.get("unused", [])
        stdlib = self.import_analysis.get("stdlib", [])
        third_party = self.import_analysis.get("third_party", [])

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Missing Dependencies:** {len(missing)}")
        lines.append(f"- **Unused Dependencies:** {len(unused)}")
        lines.append(f"- **Standard Library:** {len(stdlib)}")
        lines.append(f"- **Third Party:** {len(third_party)}")
        lines.append("")

        # Missing dependencies
        if missing:
            lines.append("## Missing Dependencies")
            lines.append("")
            lines.append("Packages imported but not declared in requirements/dependencies.")
            lines.append("")
            for pkg in missing[:20]:
                lines.append(f"- `{pkg}`")
            if len(missing) > 20:
                lines.append(f"- *... and {len(missing) - 20} more*")
            lines.append("")

        # Unused dependencies
        if unused:
            lines.append("## Unused Dependencies")
            lines.append("")
            lines.append("Packages declared but never imported.")
            lines.append("")
            for pkg in unused[:20]:
                lines.append(f"- `{pkg}`")
            if len(unused) > 20:
                lines.append(f"- *... and {len(unused) - 20} more*")
            lines.append("")

        # Third party imports
        if third_party:
            lines.append("## Third Party Imports")
            lines.append("")
            lines.append("| Package | Import Count |")
            lines.append("|---------|--------------|")
            # Count imports
            counts: dict[str, int] = {}
            for imp in third_party:
                pkg = imp.split(".")[0] if isinstance(imp, str) else imp.get("name", "").split(".")[0]
                counts[pkg] = counts.get(pkg, 0) + 1
            for pkg, count in sorted(counts.items(), key=lambda x: -x[1])[:20]:
                lines.append(f"| `{pkg}` | {count} |")
            lines.append("")

        return "\n".join(lines)

    def _generate_health_index(self) -> str:
        """Generate the health index/README file."""
        lines = []
        lines.append("# Project Health")
        lines.append("")
        lines.append("Project health and dependency analysis.")
        lines.append("")

        # Quick stats
        complexity_issues = len(self.complexity.get("issues", []))
        orphan_files = len(self.orphans.get("orphaned", []))
        duplicate_groups = len(self.duplicates)
        missing_deps = len(self.import_analysis.get("missing", []))
        unused_deps = len(self.import_analysis.get("unused", []))
        env_vars = len(self.env_vars)

        lines.append("## Quick Stats")
        lines.append("")
        lines.append(f"- **Complexity Issues:** {complexity_issues}")
        lines.append(f"- **Orphaned Files:** {orphan_files}")
        lines.append(f"- **Potential Duplicates:** {duplicate_groups}")
        lines.append(f"- **Missing Dependencies:** {missing_deps}")
        lines.append(f"- **Unused Dependencies:** {unused_deps}")
        lines.append(f"- **Environment Variables:** {env_vars}")
        lines.append("")

        lines.append("## Documents")
        lines.append("")
        lines.append("- [Dependencies](dependencies.md) - Project dependencies")
        lines.append("- [Code Health](code_health.md) - Complexity, duplicates, orphans")
        lines.append("- [Environment](environment.md) - Environment variables")
        lines.append("- [Imports](imports.md) - Import analysis")
        lines.append("")

        return "\n".join(lines)


def generate_health_docs(
    index_data: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """
    Generate project health documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.

    Returns:
        Summary of generated files.
    """
    generator = ProjectHealthGenerator(index_data)
    return generator.generate(output_dir)
