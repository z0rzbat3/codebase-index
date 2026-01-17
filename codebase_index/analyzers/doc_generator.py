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

        for func_key, func_data in self.call_graph.items():
            calls_list = func_data.get("calls", [])

            # Check if this function calls our symbol
            for call in calls_list:
                if name.lower() in call.lower() or call.lower() in name.lower():
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
            # Get file summary if available
            file_hash = f.get("hash", "")
            summary = self.summaries.get(file_hash, {}).get("summary", "-")
            if len(summary) > 60:
                summary = summary[:57] + "..."
            lines.append(f"| `{fname}` | {category} | {line_count} | {summary} |")

        lines.append("")

        # Key classes and functions
        classes, functions = self._get_symbols_in_module(module_path)

        if classes:
            lines.append("## Classes")
            lines.append("")
            for cls in classes[:10]:
                cls_name = cls.get("name", "")
                cls_summary = cls.get("summary", cls.get("docstring", ""))
                if cls_summary:
                    if len(cls_summary) > 100:
                        cls_summary = cls_summary[:97] + "..."
                    lines.append(f"### {cls_name}")
                    lines.append("")
                    lines.append(cls_summary)
                    lines.append("")

                # List methods
                methods = self._get_methods_for_class(cls_name, module_path)
                if methods:
                    lines.append("**Methods:**")
                    for m in methods[:8]:
                        m_name = m.get("name", "")
                        # Prefer summary, then docstring first line
                        m_desc = m.get("summary", "")
                        if not m_desc:
                            docstring = m.get("docstring", "")
                            if docstring:
                                m_desc = docstring.split("\n")[0].strip()
                        if m_desc and len(m_desc) > 50:
                            m_desc = m_desc[:47] + "..."
                        lines.append(f"- `{m_name}()` - {m_desc or 'No description'}")
                    if len(methods) > 8:
                        lines.append(f"- ... and {len(methods) - 8} more")
                    lines.append("")

            if len(classes) > 10:
                lines.append(f"*... and {len(classes) - 10} more classes*")
                lines.append("")

        if functions:
            lines.append("## Functions")
            lines.append("")
            lines.append("| Function | Description |")
            lines.append("|----------|-------------|")
            for func in functions[:15]:
                func_name = func.get("name", "")
                func_summary = func.get("summary", func.get("docstring", "-"))
                if func_summary and len(func_summary) > 60:
                    func_summary = func_summary[:57] + "..."
                lines.append(f"| `{func_name}()` | {func_summary or '-'} |")
            if len(functions) > 15:
                lines.append(f"| ... | *{len(functions) - 15} more functions* |")
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

        for func_key, func_data in self.call_graph.items():
            calls_list = func_data.get("calls", [])

            for call in calls_list:
                if name.lower() in call.lower():
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
                    "coupling_score": 0,
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
        lines.append(f"- **Languages:** {', '.join(summary.get('languages', {}).keys())}")
        lines.append("")

        # Component overview
        lines.append("## Components")
        lines.append("")
        lines.append("| Component | Files | Classes | Functions | Coupling |")
        lines.append("|-----------|-------|---------|-----------|----------|")

        for comp in components[:15]:
            name = comp["name"]
            files = len(comp["files"])
            classes = len(comp["classes"])
            functions = len(comp["functions"])
            coupling = f"{comp['coupling_score']:.2f}" if comp["coupling_score"] else "-"
            lines.append(f"| `{name}` | {files} | {classes} | {functions} | {coupling} |")

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
        if component["coupling_score"]:
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
        entry_points = []
        caller_counts: dict[str, int] = {}

        for func_key, func_data in self.call_graph.items():
            for call in func_data.get("calls", []):
                caller_counts[call] = caller_counts.get(call, 0) + 1

        # Sort by caller count
        sorted_functions = sorted(caller_counts.items(), key=lambda x: x[1], reverse=True)

        lines.append("## Most Called Functions")
        lines.append("")
        lines.append("These functions are central to the data flow:")
        lines.append("")
        lines.append("| Function | Times Called |")
        lines.append("|----------|--------------|")
        for func_name, count in sorted_functions[:20]:
            lines.append(f"| `{func_name}` | {count} |")
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

        # Start from functions that have calls but few callers
        starters = []
        for func_key, func_data in self.call_graph.items():
            calls = func_data.get("calls", [])
            if len(calls) >= 2:
                # Check if this function is rarely called
                is_rarely_called = True
                for other_key, other_data in self.call_graph.items():
                    if func_key in other_data.get("calls", []):
                        is_rarely_called = False
                        break
                if is_rarely_called:
                    starters.append((func_key, calls))

        # Build chains from starters
        for func_key, calls in starters[:10]:
            chain = [func_key.split(":")[-1] if ":" in func_key else func_key]
            current_calls = calls

            for _ in range(max_depth - 1):
                if not current_calls:
                    break
                # Pick first call that exists in call graph
                next_call = None
                for call in current_calls:
                    for other_key in self.call_graph:
                        if call in other_key:
                            next_call = call
                            current_calls = self.call_graph[other_key].get("calls", [])
                            break
                    if next_call:
                        break

                if next_call:
                    chain.append(next_call)
                else:
                    if current_calls:
                        chain.append(current_calls[0])
                    break

            if len(chain) >= 3:
                chains.append(chain)

        return chains

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
