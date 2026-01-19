# AuthScanner

> Auto-generated from `codebase_index/analyzers/auth.py`

## Overview

Scans for authentication requirements per endpoint by analyzing function signatures and decorators. Config-driven for easy customization by LLM agents.

## Classes

### `AuthScanner`

Scans for authentication requirements per endpoint using precise function signature parsing instead of broad context matching.

#### Methods

- `__init__() -> None`: Initialize with default auth patterns.
- `configure(config: dict[str, Any]) -> None`: Configure the scanner with custom auth patterns from config. Supports both new format (parameters/decorators) and legacy format.
- `scan_file(filepath: Path, routes: list[dict[str, Any]]) -> list[dict[str, Any]]`: Scan a file and annotate routes with `auth_required` field.
- `_extract_function_signatures_ast(content: str) -> dict[str, dict[str, Any]]`: Extract function signatures using AST for precise parameter analysis.
- `_get_signature_text(content: str, node: ast.FunctionDef) -> str`: Extract the raw function signature text.
- `_get_decorator_text(content: str, node: ast.FunctionDef) -> str`: Extract decorator text above the function.
- `_detect_auth(handler, route_line, lines, function_signatures) -> str | None`: Detect auth requirement using AST-based or line-based strategies.
- `_detect_auth_from_lines(handler, route_line, lines) -> str | None`: Fallback line-based auth detection.

## Functions

### `check_endpoint_auth(signature, decorators, config)`

Utility function to check if an endpoint requires auth. Designed for LLM agents.

**Parameters:**
- `signature: str` - The function signature string
- `decorators: list[str] | None` - Optional list of decorator strings
- `config: dict[str, Any] | None` - Optional config with custom auth patterns

**Returns:** `dict[str, Any]` - `{"auth_required": bool, "auth_type": str | None}`

## Constants

### `DEFAULT_AUTH_PATTERNS`

Default auth patterns config with two categories:
- `parameters`: FastAPI Depends() patterns, type hint patterns
- `decorators`: Flask/Django/JWT decorators, permission classes

## Usage

```python
from codebase_index.analyzers.auth import AuthScanner, check_endpoint_auth

# Check a single endpoint
result = check_endpoint_auth(
    "def foo(current_user: User = Depends(get_current_user))"
)
# {"auth_required": True, "auth_type": "parameter:Depends..."}

# Scan a file's routes
scanner = AuthScanner()
scanner.configure({"auth": {"decorators": ["@custom_auth"]}})
annotated = scanner.scan_file(Path("routes.py"), routes)
```

---
*Source: codebase_index/analyzers/auth.py | Lines: 401*
