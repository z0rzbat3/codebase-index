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
