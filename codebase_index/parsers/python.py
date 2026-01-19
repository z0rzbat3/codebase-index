"""
Python AST-based parser for codebase_index.

Supports configurable patterns for routes, models, schemas via config.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.config import STDLIB_MODULES, DEFAULT_CONFIG
from codebase_index.parsers.base import BaseParser, ParserRegistry

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


# Default route patterns (FastAPI/Starlette)
DEFAULT_ROUTE_PATTERNS = [
    {"regex": r"(router|app)\.(get|post|put|patch|delete|head|options)", "framework": "fastapi"},
]

# Default model patterns (marker-based is most reliable)
DEFAULT_MODEL_PATTERNS = [
    {"marker": "__tablename__", "type": "sqlalchemy"},
    {"base_class": "DeclarativeBase", "type": "sqlalchemy"},
]

# Default schema patterns
DEFAULT_SCHEMA_PATTERNS = [
    {"base_class": "BaseModel", "type": "pydantic"},
    {"base_class": "BaseSettings", "type": "pydantic"},
]


@ParserRegistry.register("python", [".py", ".pyw"])
class PythonParser(BaseParser):
    """
    Python parser using the ast module for accurate extraction.

    Falls back to regex parsing for files with syntax errors.
    Supports configurable patterns for routes, models, and schemas.
    """

    supports_fallback = True

    def __init__(self) -> None:
        """Initialize the Python parser with default config."""
        super().__init__()
        # These will be populated by configure() or use defaults
        self.internal_prefixes: list[str] = ["src", "app", "api", "lib", "core", "modules"]
        self.route_patterns: list[dict[str, Any]] = DEFAULT_ROUTE_PATTERNS.copy()
        self.model_patterns: list[dict[str, Any]] = DEFAULT_MODEL_PATTERNS.copy()
        self.schema_patterns: list[dict[str, Any]] = DEFAULT_SCHEMA_PATTERNS.copy()

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the parser with patterns from config.

        Args:
            config: Configuration dictionary with routes, models, schemas sections.
        """
        super().configure(config)

        # Import classification
        imports_config = config.get("imports", {})
        if imports_config.get("internal_prefixes"):
            self.internal_prefixes = imports_config["internal_prefixes"]

        # Route detection patterns
        routes_config = config.get("routes", {})
        if routes_config.get("enabled", True) and routes_config.get("patterns"):
            self.route_patterns = routes_config["patterns"]

        # Model detection patterns
        models_config = config.get("models", {})
        if models_config.get("enabled", True) and models_config.get("patterns"):
            self.model_patterns = models_config["patterns"]

        # Schema detection patterns
        schemas_config = config.get("schemas", {})
        if schemas_config.get("enabled", True) and schemas_config.get("patterns"):
            self.schema_patterns = schemas_config["patterns"]

        logger.debug(
            "PythonParser configured: %d route patterns, %d model patterns, %d schema patterns",
            len(self.route_patterns),
            len(self.model_patterns),
            len(self.schema_patterns),
        )

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a Python file and extract structure using AST.

        Args:
            filepath: Path to the Python file.

        Returns:
            Dictionary with classes, functions, imports, routes, models, schemas.
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
            "imports": {"internal": [], "external": [], "names": []},  # names = imported symbols
            "routes": [],           # Generic routes (config-driven)
            "models": [],           # ORM models (config-driven)
            "schemas": [],          # Validation schemas (config-driven)
            # Legacy keys for backwards compatibility
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
            # Module-level symbols
            "constants": [],        # UPPER_CASE assignments
            "module_vars": [],      # Other module-level assignments
            "type_aliases": [],     # Type alias definitions
        }

        # Process module-level assignments (constants, type aliases)
        self._process_module_assignments(tree, result)

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
                # Also store the imported names (e.g., 'AgentFactory' from 'from x import AgentFactory')
                for alias in node.names:
                    name = alias.name
                    if name != "*":
                        self._add_imported_name(name, result["imports"])

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

        # Check for schema patterns (Pydantic, DRF serializers, etc.)
        is_schema = False
        for pattern in self.schema_patterns:
            base_class = pattern.get("base_class")
            if base_class and self._matches_base_class(class_info["bases"], base_class):
                schema_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "type": pattern.get("type", "unknown"),
                    "base": base_class,
                }
                result["schemas"].append(schema_info)
                # Legacy support
                if pattern.get("type") == "pydantic":
                    result["pydantic_models"].append(node.name)
                is_schema = True
                break

        # Check for model patterns (SQLAlchemy, Django ORM, etc.)
        # Skip if already identified as a schema (e.g., Pydantic models are not DB models)
        if not is_schema:
            model_found = False
            for pattern in self.model_patterns:
                if model_found:
                    break

                # Check base class pattern
                base_class = pattern.get("base_class")
                if base_class and self._matches_base_class(class_info["bases"], base_class):
                    model_info = {
                        "class": node.name,
                        "line": node.lineno,
                        "type": pattern.get("type", "unknown"),
                    }
                    result["models"].append(model_info)
                    model_found = True
                    continue

                # Check marker pattern (e.g., __tablename__)
                marker = pattern.get("marker")
                if marker:
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == marker:
                                    table_name = None
                                    if isinstance(item.value, ast.Constant):
                                        table_name = item.value.value
                                    model_info = {
                                        "class": node.name,
                                        "line": node.lineno,
                                        "type": pattern.get("type", "unknown"),
                                    }
                                    if table_name:
                                        model_info["table"] = table_name
                                    result["models"].append(model_info)
                                    # Legacy support
                                    if pattern.get("type") == "sqlalchemy" and table_name:
                                        result["sqlalchemy_tables"].append({
                                            "class": node.name,
                                            "table": table_name,
                                        })
                                    model_found = True
                                    break
                        if model_found:
                            break

        # Process methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                dynamic_calls = self._extract_dynamic_calls(item)
                method_info: dict[str, Any] = {
                    "name": item.name,
                    "line": item.lineno,
                    "async": isinstance(item, ast.AsyncFunctionDef),
                    "signature": self._extract_signature(item),
                    "docstring": ast.get_docstring(item),
                    "calls": self._extract_calls(item),
                    "body_hash": self._get_function_body_hash(item),
                }
                if dynamic_calls:
                    method_info["dynamic_calls"] = dynamic_calls
                class_info["methods"].append(method_info)

        result["classes"].append(class_info)

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        result: dict[str, Any],
    ) -> None:
        """Process a top-level function definition node."""
        # Extract calls and dynamic call warnings
        dynamic_calls = self._extract_dynamic_calls(node)

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

        # Add dynamic call warnings if any were detected
        if dynamic_calls:
            func_info["dynamic_calls"] = dynamic_calls

        result["functions"].append(func_info)

        # Check for route decorators using config patterns
        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            if not dec_name:
                continue

            for pattern in self.route_patterns:
                regex = pattern.get("regex")
                if regex:
                    match = re.match(regex, dec_name)
                    if match:
                        route_info = self._extract_route_info(
                            dec, node, pattern, match
                        )
                        if route_info:
                            result["routes"].append(route_info)
                            # Legacy support for fastapi_routes
                            if pattern.get("framework") in ("fastapi", "starlette"):
                                result["fastapi_routes"].append(route_info)
                        break

    def _process_module_assignments(self, tree: ast.Module, result: dict[str, Any]) -> None:
        """
        Extract module-level constants, variables, and type aliases.

        Only processes top-level assignments, not nested ones.
        """
        for node in tree.body:
            # Simple assignment: NAME = value
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._categorize_assignment(target.id, node, result)

            # Annotated assignment: NAME: Type = value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                info: dict[str, Any] = {
                    "name": name,
                    "line": node.lineno,
                }

                # Get annotation
                if hasattr(ast, 'unparse'):
                    try:
                        info["annotation"] = ast.unparse(node.annotation)
                    except Exception:
                        pass

                # Get value if present
                if node.value and hasattr(ast, 'unparse'):
                    try:
                        value_str = ast.unparse(node.value)
                        info["value_preview"] = value_str[:200]
                    except Exception:
                        pass

                # Categorize: TypeAlias, constant, or variable
                annotation_str = info.get("annotation", "")
                if "TypeAlias" in annotation_str:
                    result["type_aliases"].append(info)
                elif self._is_constant_name(name):
                    result["constants"].append(info)
                elif not name.startswith("_"):
                    result["module_vars"].append(info)

    def _categorize_assignment(self, name: str, node: ast.Assign, result: dict[str, Any]) -> None:
        """Categorize a module-level assignment as constant or variable."""
        info: dict[str, Any] = {
            "name": name,
            "line": node.lineno,
        }

        try:
            # Get value preview
            if hasattr(ast, 'unparse'):
                value_str = ast.unparse(node.value)
                info["value_preview"] = value_str[:200]

            # Infer type from value
            if isinstance(node.value, ast.Dict):
                info["inferred_type"] = "dict"
            elif isinstance(node.value, ast.List):
                info["inferred_type"] = "list"
            elif isinstance(node.value, ast.Set):
                info["inferred_type"] = "set"
            elif isinstance(node.value, ast.Constant):
                val = node.value.value
                info["inferred_type"] = type(val).__name__
                # Store simple values directly
                if isinstance(val, (str, int, float, bool)) and len(str(val)) < 100:
                    info["value"] = val
            elif isinstance(node.value, ast.Call):
                # e.g., CONFIG = load_config()
                call_name = self._get_call_name(node.value.func)
                if call_name:
                    info["initializer"] = call_name
        except Exception:
            pass

        # Categorize by naming convention
        if self._is_constant_name(name):
            result["constants"].append(info)
        elif not name.startswith("_"):
            result["module_vars"].append(info)

    def _is_constant_name(self, name: str) -> bool:
        """Check if name follows constant naming convention (UPPER_CASE)."""
        # Handle _PRIVATE_CONSTANTS too
        check_name = name[1:] if name.startswith("_") and len(name) > 1 else name
        return check_name.isupper() and not check_name.startswith("__")

    def _extract_route_info(
        self,
        decorator: ast.expr,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        pattern: dict[str, Any],
        match: re.Match,
    ) -> dict[str, Any] | None:
        """Extract route information from a decorator and function."""
        if not isinstance(decorator, ast.Call):
            return None

        func_name = func_node.name
        line = func_node.lineno

        # Try to extract HTTP method from regex groups
        method = "GET"
        if match.lastindex and match.lastindex >= 2:
            method = match.group(2).upper()
        elif match.lastindex and match.lastindex >= 1:
            # Check if the captured group looks like an HTTP method
            captured = match.group(1)
            if captured.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                method = captured.upper()

        # Extract path from first argument
        path = None
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            path = decorator.args[0].value

        # Extract summary/description from decorator keyword arguments
        summary = None
        description = None
        for keyword in decorator.keywords:
            if keyword.arg == "summary" and isinstance(keyword.value, ast.Constant):
                summary = keyword.value.value
            elif keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                description = keyword.value.value

        # Get function docstring
        docstring = ast.get_docstring(func_node)

        # Build description: prefer decorator summary, then docstring first line
        route_description = summary
        if not route_description and docstring:
            route_description = docstring.split("\n")[0].strip()

        return {
            "method": method,
            "path": path,
            "handler": func_name,
            "function": func_name,  # Alias for compatibility
            "line": line,
            "framework": pattern.get("framework", "unknown"),
            "summary": summary,
            "description": route_description,
            "docstring": docstring,
        }

    def _get_name(self, node: ast.expr) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            # Handle Generic[T], Dict[str, Any], etc.
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            # Fallback for older Python
            base = self._get_name(node.value)
            return f"{base}[...]"
        # Fallback: use ast.unparse if available
        if hasattr(ast, 'unparse'):
            return ast.unparse(node)
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

    def _matches_base_class(self, bases: list[str], pattern: str) -> bool:
        """
        Check if any base class matches the pattern.

        Uses exact matching for simple names, or suffix matching for dotted names.
        E.g., pattern "Base" matches "Base" but not "BaseModel".
        Pattern "models.Model" matches "models.Model" or "django.db.models.Model".
        """
        for base in bases:
            # Exact match
            if base == pattern:
                return True
            # Suffix match for dotted patterns (e.g., "models.Model" matches "django.db.models.Model")
            if "." in pattern and base.endswith("." + pattern.split(".")[-1]):
                # Check if the pattern's components match the end of the base
                if base.endswith(pattern) or base == pattern.split(".")[-1]:
                    return True
            # For simple patterns like "Model", also check the last component of dotted bases
            if "." not in pattern and base.split(".")[-1] == pattern:
                return True
        return False

    def _extract_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        """Extract function signature (parameters and return type)."""
        signature: dict[str, Any] = {
            "params": [],
            "return_type": None,
            "formatted": None,  # Human-readable formatted signature
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

        # Generate formatted signature for markdown output
        signature["formatted"] = self._format_signature(node, signature)

        return signature

    def _format_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        signature: dict[str, Any],
    ) -> str:
        """
        Generate a formatted, markdown-ready signature string.

        Example output: "async def fetch_data(url: str, timeout: int = 30) -> Response"
        """
        parts = []

        # async prefix
        if isinstance(node, ast.AsyncFunctionDef):
            parts.append("async ")

        parts.append(f"def {node.name}(")

        # Format parameters
        param_strs = []
        for param in signature["params"]:
            param_str = param["name"]
            if param.get("type"):
                param_str += f": {param['type']}"
            if param.get("has_default"):
                param_str += " = ..."
            param_strs.append(param_str)

        parts.append(", ".join(param_strs))
        parts.append(")")

        # Return type
        if signature.get("return_type"):
            parts.append(f" -> {signature['return_type']}")

        return "".join(parts)

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

    def _extract_dynamic_calls(self, node: ast.AST) -> list[dict[str, Any]]:
        """
        Detect dynamic dispatch patterns that static analysis cannot resolve.

        Returns list of warnings about dynamic calls that may have unknown targets.
        """
        dynamic_calls: list[dict[str, Any]] = []

        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            warning = self._detect_dynamic_pattern(child)
            if warning:
                dynamic_calls.append(warning)

        return dynamic_calls

    def _detect_dynamic_pattern(self, node: ast.Call) -> dict[str, Any] | None:
        """
        Check if a call uses dynamic dispatch.

        Returns warning dict if dynamic, None otherwise.
        """
        # Pattern 1: getattr(obj, "method")() - calling result of getattr
        if isinstance(node.func, ast.Call):
            inner = node.func
            if isinstance(inner.func, ast.Name) and inner.func.id == "getattr":
                return {
                    "line": node.lineno,
                    "pattern": "getattr_call",
                    "description": "Dynamic method call via getattr()",
                    "severity": "info",
                }

        # Pattern 2: handlers[key]() - subscript dispatch
        if isinstance(node.func, ast.Subscript):
            try:
                container = ast.unparse(node.func.value) if hasattr(ast, 'unparse') else "container"
            except Exception:
                container = "container"
            return {
                "line": node.lineno,
                "pattern": "subscript_dispatch",
                "description": f"Dynamic dispatch via {container}[key]()",
                "severity": "info",
            }

        # Pattern 3: getattr() call itself (may be called later)
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            return {
                "line": node.lineno,
                "pattern": "getattr",
                "description": "getattr() lookup - target determined at runtime",
                "severity": "info",
            }

        # Pattern 4: eval/exec (dangerous dynamic code execution)
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            return {
                "line": node.lineno,
                "pattern": "eval_exec",
                "description": f"{node.func.id}() executes dynamic code",
                "severity": "warning",
            }

        # Pattern 5: importlib.import_module
        if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
            return {
                "line": node.lineno,
                "pattern": "dynamic_import",
                "description": "Dynamic import - module determined at runtime",
                "severity": "info",
            }

        # Pattern 6: globals()/locals() access followed by call
        if isinstance(node.func, ast.Subscript):
            if isinstance(node.func.value, ast.Call):
                inner_call = node.func.value
                if isinstance(inner_call.func, ast.Name) and inner_call.func.id in ("globals", "locals"):
                    return {
                        "line": node.lineno,
                        "pattern": "globals_locals_dispatch",
                        "description": f"Dynamic dispatch via {inner_call.func.id}()[key]()",
                        "severity": "warning",
                    }

        return None

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

    def _add_imported_name(self, name: str, imports: dict[str, list[str]]) -> None:
        """Add an imported symbol name to the names list."""
        if "names" not in imports:
            imports["names"] = []
        if name not in imports["names"]:
            imports["names"].append(name)

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
            "imports": {"internal": [], "external": [], "names": []},
            "routes": [],
            "models": [],
            "schemas": [],
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
            "_fallback": "regex",
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
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

            # Routes - use config patterns
            for pattern in self.route_patterns:
                regex = pattern.get("regex")
                if regex:
                    route_match = re.search(rf'@{regex}\s*\(\s*["\']([^"\']+)["\']', line)
                    if route_match:
                        method = "GET"
                        if route_match.lastindex and route_match.lastindex >= 1:
                            # Extract method from decorator name
                            dec_match = re.search(regex, line)
                            if dec_match and dec_match.lastindex and dec_match.lastindex >= 2:
                                method = dec_match.group(2).upper()
                        result["routes"].append({
                            "method": method,
                            "path": route_match.group(1),
                            "line": i,
                            "framework": pattern.get("framework", "unknown"),
                        })
                        # Legacy support
                        if pattern.get("framework") in ("fastapi", "starlette"):
                            result["fastapi_routes"].append({
                                "method": method,
                                "path": route_match.group(1),
                                "line": i,
                            })
                        break

            # Models - check for marker patterns
            for pattern in self.model_patterns:
                marker = pattern.get("marker")
                if marker:
                    marker_match = re.search(rf'{marker}\s*=\s*["\'](\w+)["\']', line)
                    if marker_match:
                        result["models"].append({
                            "table": marker_match.group(1),
                            "line": i,
                            "type": pattern.get("type", "unknown"),
                        })
                        # Legacy support
                        if pattern.get("type") == "sqlalchemy":
                            result["sqlalchemy_tables"].append({
                                "table": marker_match.group(1),
                                "line": i,
                            })
                        break

        return result
