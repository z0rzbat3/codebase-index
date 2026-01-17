"""
Python AST-based parser for codebase_index.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.config import STDLIB_MODULES
from codebase_index.parsers.base import BaseParser, ParserRegistry

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


@ParserRegistry.register("python", [".py", ".pyw"])
class PythonParser(BaseParser):
    """
    Python parser using the ast module for accurate extraction.

    Falls back to regex parsing for files with syntax errors.
    """

    supports_fallback = True

    def __init__(self, internal_prefixes: list[str] | None = None):
        """
        Initialize the Python parser.

        Args:
            internal_prefixes: List of module prefixes considered internal
                to the project. If None, uses common defaults.
        """
        self.internal_prefixes = internal_prefixes or [
            "src", "app", "api", "lib", "core", "modules", "db", "auth", "agents"
        ]

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a Python file and extract structure using AST.

        Args:
            filepath: Path to the Python file.

        Returns:
            Dictionary with classes, functions, imports, routes, etc.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError as e:
            logger.debug("Syntax error in %s: %s, falling back to regex", filepath, e)
            return self._scan_regex(filepath)
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return {"error": str(e)}

        result: dict[str, Any] = {
            "classes": [],
            "functions": [],
            "imports": {"internal": [], "external": []},
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._process_class(node, result)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (col_offset == 0)
                if hasattr(node, 'col_offset') and node.col_offset == 0:
                    self._process_function(node, result)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._categorize_import(alias.name, result["imports"])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._categorize_import(node.module, result["imports"])

        return result

    def _process_class(self, node: ast.ClassDef, result: dict[str, Any]) -> None:
        """Process a class definition node."""
        class_info: dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, 'end_lineno', None),
            "bases": [self._get_name(b) for b in node.bases],
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node),
            "methods": [],
        }

        # Check for Pydantic model
        if any("BaseModel" in str(b) for b in class_info["bases"]):
            result["pydantic_models"].append(node.name)

        # Process methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = {
                    "name": item.name,
                    "line": item.lineno,
                    "async": isinstance(item, ast.AsyncFunctionDef),
                    "signature": self._extract_signature(item),
                    "docstring": ast.get_docstring(item),
                    "calls": self._extract_calls(item),
                    "body_hash": self._get_function_body_hash(item),
                }
                class_info["methods"].append(method_info)

        result["classes"].append(class_info)

        # Check for SQLAlchemy __tablename__
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            result["sqlalchemy_tables"].append({
                                "class": node.name,
                                "table": item.value.value,
                            })

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        result: dict[str, Any],
    ) -> None:
        """Process a top-level function definition node."""
        func_info: dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, 'end_lineno', None),
            "async": isinstance(node, ast.AsyncFunctionDef),
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "signature": self._extract_signature(node),
            "docstring": ast.get_docstring(node),
            "calls": self._extract_calls(node),
            "body_hash": self._get_function_body_hash(node),
        }
        result["functions"].append(func_info)

        # Check for FastAPI route decorators
        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            if dec_name and re.match(
                r"(router|app)\.(get|post|put|patch|delete|head|options)",
                dec_name,
            ):
                route_info = self._extract_route_info(dec, node.name, node.lineno)
                if route_info:
                    result["fastapi_routes"].append(route_info)

    def _get_name(self, node: ast.expr) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return str(node)

    def _get_decorator_name(self, node: ast.expr) -> str | None:
        """Extract decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return None

    def _extract_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        """Extract function signature (parameters and return type)."""
        signature: dict[str, Any] = {
            "params": [],
            "return_type": None,
        }

        args = node.args

        # Positional args
        for i, arg in enumerate(args.args):
            param: dict[str, Any] = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            default_offset = len(args.args) - len(args.defaults)
            if i >= default_offset:
                param["has_default"] = True
            signature["params"].append(param)

        # *args
        if args.vararg:
            signature["params"].append({
                "name": f"*{args.vararg.arg}",
                "type": self._get_annotation(args.vararg.annotation),
            })

        # Keyword-only args
        for i, arg in enumerate(args.kwonlyargs):
            param = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                param["has_default"] = True
            signature["params"].append(param)

        # **kwargs
        if args.kwarg:
            signature["params"].append({
                "name": f"**{args.kwarg.arg}",
                "type": self._get_annotation(args.kwarg.annotation),
            })

        # Return type
        if node.returns:
            signature["return_type"] = self._get_annotation(node.returns)

        return signature

    def _get_annotation(self, node: ast.expr | None) -> str | None:
        """Extract type annotation as string."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            base = self._get_annotation(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = ", ".join(
                    self._get_annotation(e) or "" for e in node.slice.elts
                )
            else:
                args = self._get_annotation(node.slice)
            return f"{base}[{args}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union types with | syntax (Python 3.10+)
            left = self._get_annotation(node.left)
            right = self._get_annotation(node.right)
            return f"{left} | {right}"
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_annotation(e) or "" for e in node.elts)
        else:
            # Python 3.9+ has ast.unparse
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            return str(node)

    def _extract_calls(self, node: ast.AST) -> list[str]:
        """
        Extract all function/method calls from a function body.

        Returns raw call strings for analysis.
        """
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_name(child.func)
                if call_str:
                    calls.append(call_str)

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_calls = []
        for call in calls:
            if call not in seen:
                seen.add(call)
                unique_calls.append(call)
        return unique_calls

    def _get_call_name(self, node: ast.expr) -> str | None:
        """Extract the name of a call target."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_call_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Subscript):
            value = self._get_call_name(node.value)
            return f"{value}[...]" if value else None
        elif isinstance(node, ast.Call):
            return self._get_call_name(node.func)
        return None

    def _get_function_body_hash(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
        """
        Generate a normalized hash of function body for duplicate detection.

        Uses AST structure for comparison, ignoring variable names.
        """
        try:
            body = node.body
            # Skip docstring if present
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
            ):
                body = body[1:]

            if not body:
                return None

            # Use ast.dump for structural comparison
            body_str = ""
            for stmt in body:
                body_str += ast.dump(stmt, annotate_fields=False)

            return hashlib.md5(body_str.encode()).hexdigest()[:12]
        except Exception as e:
            logger.debug("Could not hash function body: %s", e)
            return None

    def _extract_route_info(
        self,
        decorator: ast.expr,
        func_name: str,
        line: int,
    ) -> dict[str, Any] | None:
        """Extract FastAPI route information from decorator."""
        if not isinstance(decorator, ast.Call):
            return None

        dec_name = self._get_decorator_name(decorator)
        if not dec_name:
            return None

        match = re.match(
            r"(router|app)\.(get|post|put|patch|delete|head|options)",
            dec_name,
        )
        if not match:
            return None

        method = match.group(2).upper()
        path = None

        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            path = decorator.args[0].value

        return {
            "method": method,
            "path": path,
            "handler": func_name,
            "line": line,
        }

    def _categorize_import(self, module: str, imports: dict[str, list[str]]) -> None:
        """Categorize import as internal or external."""
        root_module = module.split(".")[0]

        # Check if it's a stdlib module
        if root_module in STDLIB_MODULES:
            if root_module not in imports["external"]:
                imports["external"].append(root_module)
            return

        # Check if it matches internal prefixes
        is_internal = any(
            root_module.startswith(prefix) or root_module == prefix
            for prefix in self.internal_prefixes
        )

        if is_internal:
            if module not in imports["internal"]:
                imports["internal"].append(module)
        else:
            if root_module not in imports["external"]:
                imports["external"].append(root_module)

    def _scan_regex(self, filepath: Path) -> dict[str, Any]:
        """Fallback regex-based scanning for files with syntax errors."""
        result: dict[str, Any] = {
            "classes": [],
            "functions": [],
            "imports": {"internal": [], "external": []},
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
            "_fallback": "regex",
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return result

        for i, line in enumerate(lines, 1):
            # Classes
            match = re.match(r"^class\s+(\w+)", line)
            if match:
                result["classes"].append({"name": match.group(1), "line": i})

            # Functions
            match = re.match(r"^(async\s+)?def\s+(\w+)", line)
            if match:
                result["functions"].append({
                    "name": match.group(2),
                    "line": i,
                    "async": bool(match.group(1)),
                })

            # Routes
            match = re.match(r'^@(router|app)\.(get|post|put|patch|delete)\(["\']([^"\']+)', line)
            if match:
                result["fastapi_routes"].append({
                    "method": match.group(2).upper(),
                    "path": match.group(3),
                    "line": i,
                })

            # Tables
            match = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', line)
            if match:
                result["sqlalchemy_tables"].append({
                    "table": match.group(1),
                    "line": i,
                })

        return result
