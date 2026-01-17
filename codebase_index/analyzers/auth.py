"""
Auth requirements scanner for codebase_index.

Scans for authentication requirements per endpoint by analyzing
the actual function signature and decorators - NOT broad context.

Config-driven for easy customization by LLM agents.
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


# Default auth patterns - config-driven, easily customizable by LLM
# Patterns are checked against function parameters and decorators
DEFAULT_AUTH_PATTERNS = {
    # Parameter patterns: checked against function signature
    # Format: regex patterns that match auth dependencies in parameters
    "parameters": [
        # FastAPI Depends() patterns
        r"Depends\s*\(\s*get_current_user",
        r"Depends\s*\(\s*get_current_active_user",
        r"Depends\s*\(\s*require_auth",
        r"Depends\s*\(\s*auth_required",
        r"Depends\s*\(\s*get_user",
        r"Depends\s*\(\s*verify_token",
        r"Depends\s*\(\s*oauth2_scheme",
        r"Depends\s*\(\s*get_api_key",
        # Type hint patterns (current_user: User)
        r"current_user\s*:\s*\w+",
        r"user\s*:\s*User\s*=",
        r"authenticated_user",
    ],
    # Decorator patterns: checked against decorators above the function
    "decorators": [
        # Python/Flask/Django decorators
        r"@login_required",
        r"@require_auth",
        r"@authenticated",
        r"@jwt_required",
        r"@permission_required",
        r"@permissions_required",
        r"@auth_required",
        r"@requires_auth",
        r"@token_required",
        r"@api_key_required",
        # Class-based permission patterns
        r"@permission_classes",
        r"IsAuthenticated",
    ],
}


class AuthScanner:
    """
    Scan for authentication requirements per endpoint.

    Uses precise function signature parsing instead of broad context matching.
    Config-driven for easy customization.
    """

    def __init__(self) -> None:
        """Initialize with default auth patterns."""
        self.param_patterns: list[re.Pattern] = []
        self.decorator_patterns: list[re.Pattern] = []
        self._compile_patterns(DEFAULT_AUTH_PATTERNS)

    def _compile_patterns(self, patterns: dict[str, Any]) -> None:
        """Compile regex patterns for efficient matching."""
        self.param_patterns = []
        self.decorator_patterns = []

        for pattern in patterns.get("parameters", []):
            try:
                self.param_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning("Invalid parameter pattern %r: %s", pattern, e)

        for pattern in patterns.get("decorators", []):
            try:
                self.decorator_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning("Invalid decorator pattern %r: %s", pattern, e)

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the scanner with auth patterns from config.

        Config format:
        ```yaml
        auth:
          parameters:
            - "Depends\\s*\\(\\s*get_current_user"
            - "current_user\\s*:"
          decorators:
            - "@login_required"
            - "@jwt_required"
        ```
        """
        auth_config = config.get("auth", {})

        # Check for new format (parameters/decorators)
        if auth_config.get("parameters") or auth_config.get("decorators"):
            patterns = {
                "parameters": auth_config.get("parameters", []),
                "decorators": auth_config.get("decorators", []),
            }
            self._compile_patterns(patterns)
            logger.debug(
                "AuthScanner configured: %d param patterns, %d decorator patterns",
                len(self.param_patterns),
                len(self.decorator_patterns),
            )
        # Legacy format support (list of {regex, type} dicts)
        elif auth_config.get("patterns"):
            # Convert legacy format to new format
            legacy = auth_config["patterns"]
            patterns = {"parameters": [], "decorators": []}
            for item in legacy:
                regex = item.get("regex", "")
                if regex.startswith("@"):
                    patterns["decorators"].append(regex)
                else:
                    patterns["parameters"].append(regex)
            self._compile_patterns(patterns)
            logger.debug("AuthScanner using legacy patterns (converted)")
        else:
            # Use defaults
            self._compile_patterns(DEFAULT_AUTH_PATTERNS)
            logger.debug("AuthScanner using default patterns")

    def scan_file(
        self,
        filepath: Path,
        routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Scan a file and annotate routes with auth requirements.

        Args:
            filepath: Path to the file.
            routes: List of route dictionaries to annotate.

        Returns:
            List of routes with auth_required field added.
        """
        if not routes:
            return routes

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except (OSError, IOError) as e:
            logger.debug("Could not read %s: %s", filepath, e)
            return routes

        # Try AST parsing for precise signature extraction
        function_signatures = self._extract_function_signatures_ast(content)

        # Annotate each route
        annotated_routes: list[dict[str, Any]] = []
        for route in routes:
            route_copy = dict(route)
            handler = route.get("handler", "")
            route_line = route.get("line", 0)

            # Check auth using multiple strategies
            auth_info = self._detect_auth(
                handler, route_line, lines, function_signatures
            )

            route_copy["auth_required"] = auth_info is not None
            if auth_info:
                route_copy["auth_type"] = auth_info

            annotated_routes.append(route_copy)

        return annotated_routes

    def _extract_function_signatures_ast(
        self, content: str
    ) -> dict[str, dict[str, Any]]:
        """
        Extract function signatures using AST for precise parameter analysis.

        Returns:
            Dict mapping function name to signature info.
        """
        signatures: dict[str, dict[str, Any]] = {}

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return signatures

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get the raw signature text
                sig_text = self._get_signature_text(content, node)
                # Get decorator text
                decorator_text = self._get_decorator_text(content, node)

                signatures[node.name] = {
                    "line": node.lineno,
                    "signature": sig_text,
                    "decorators": decorator_text,
                    "params": [arg.arg for arg in node.args.args],
                }

        return signatures

    def _get_signature_text(self, content: str, node: ast.FunctionDef) -> str:
        """Extract the raw function signature text."""
        lines = content.split("\n")
        start_line = node.lineno - 1  # 0-indexed

        # Find the end of the signature (the colon)
        sig_lines = []
        for i in range(start_line, min(start_line + 20, len(lines))):
            line = lines[i]
            sig_lines.append(line)
            if ":" in line and not line.strip().startswith("#"):
                # Check if this colon ends the signature (not in a type hint)
                # Simple heuristic: if line ends with : or ): it's the end
                stripped = line.rstrip()
                if stripped.endswith(":") or stripped.endswith("):"):
                    break

        return "\n".join(sig_lines)

    def _get_decorator_text(self, content: str, node: ast.FunctionDef) -> str:
        """Extract decorator text above the function."""
        lines = content.split("\n")
        func_line = node.lineno - 1  # 0-indexed

        # Look backwards for decorators
        decorator_lines = []
        for i in range(func_line - 1, max(func_line - 10, -1), -1):
            line = lines[i].strip()
            if line.startswith("@"):
                decorator_lines.insert(0, line)
            elif line and not line.startswith("#"):
                # Hit non-decorator, non-comment line
                break

        return "\n".join(decorator_lines)

    def _detect_auth(
        self,
        handler: str,
        route_line: int,
        lines: list[str],
        function_signatures: dict[str, dict[str, Any]],
    ) -> str | None:
        """
        Detect auth requirement using multiple strategies.

        Strategy 1: AST-based signature matching (most accurate)
        Strategy 2: Line-based signature extraction (fallback)

        Returns:
            Auth type string if auth detected, None otherwise.
        """
        # Strategy 1: Use AST-extracted signature if available
        if handler in function_signatures:
            sig_info = function_signatures[handler]

            # Check signature for parameter patterns
            signature = sig_info.get("signature", "")
            for pattern in self.param_patterns:
                if pattern.search(signature):
                    return f"parameter:{pattern.pattern[:30]}"

            # Check decorators
            decorators = sig_info.get("decorators", "")
            for pattern in self.decorator_patterns:
                if pattern.search(decorators):
                    return f"decorator:{pattern.pattern[:30]}"

            return None

        # Strategy 2: Fallback to line-based extraction
        return self._detect_auth_from_lines(handler, route_line, lines)

    def _detect_auth_from_lines(
        self,
        handler: str,
        route_line: int,
        lines: list[str],
    ) -> str | None:
        """
        Fallback: detect auth by extracting function signature from lines.

        Only looks at the actual function definition, NOT broad context.
        """
        if route_line <= 0 or route_line > len(lines):
            return None

        # Find the function definition starting from route_line
        func_start = None
        for i in range(route_line - 1, min(route_line + 5, len(lines))):
            line = lines[i] if i < len(lines) else ""
            if re.match(r"\s*(async\s+)?def\s+", line):
                func_start = i
                break

        if func_start is None:
            return None

        # Extract just the function signature (until the colon)
        signature_lines = []
        for i in range(func_start, min(func_start + 10, len(lines))):
            line = lines[i]
            signature_lines.append(line)
            if line.rstrip().endswith(":"):
                break

        signature = "\n".join(signature_lines)

        # Check parameter patterns against signature only
        for pattern in self.param_patterns:
            if pattern.search(signature):
                return f"parameter:{pattern.pattern[:30]}"

        # Check decorators (lines immediately before function)
        decorator_lines = []
        for i in range(func_start - 1, max(func_start - 5, -1), -1):
            line = lines[i].strip()
            if line.startswith("@"):
                decorator_lines.append(line)
            elif line and not line.startswith("#"):
                break

        decorators = "\n".join(decorator_lines)
        for pattern in self.decorator_patterns:
            if pattern.search(decorators):
                return f"decorator:{pattern.pattern[:30]}"

        return None


def check_endpoint_auth(
    signature: str,
    decorators: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Utility function: Check if an endpoint requires auth.

    Designed for LLM agents to easily check auth requirements.

    Args:
        signature: The function signature string.
        decorators: Optional list of decorator strings.
        config: Optional config with custom auth patterns.

    Returns:
        {"auth_required": bool, "auth_type": str | None}

    Example:
        >>> check_endpoint_auth("def foo(current_user: User = Depends(get_current_user))")
        {"auth_required": True, "auth_type": "parameter:Depends..."}

        >>> check_endpoint_auth("def health_check(db: Session = Depends(get_db))")
        {"auth_required": False, "auth_type": None}
    """
    scanner = AuthScanner()
    if config:
        scanner.configure(config)

    # Check parameters
    for pattern in scanner.param_patterns:
        if pattern.search(signature):
            return {
                "auth_required": True,
                "auth_type": f"parameter:{pattern.pattern[:40]}",
            }

    # Check decorators
    if decorators:
        decorator_text = "\n".join(decorators)
        for pattern in scanner.decorator_patterns:
            if pattern.search(decorator_text):
                return {
                    "auth_required": True,
                    "auth_type": f"decorator:{pattern.pattern[:40]}",
                }

    return {"auth_required": False, "auth_type": None}
