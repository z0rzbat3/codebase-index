# MiddlewareScanner

> Auto-generated from `codebase_index/scanners/middleware.py`

## Overview

Scans for FastAPI/Starlette middleware configuration. Identifies both standard framework middleware and custom middleware implementations. Useful for understanding request/response processing pipelines and security configurations.

## Classes

### `MiddlewareScanner`

Scan for FastAPI/Starlette middleware configuration.

#### Class Attributes

- `KNOWN_MIDDLEWARE`: Dictionary mapping middleware names to descriptions:
  - `CORSMiddleware` - CORS - Cross-Origin Resource Sharing
  - `GZipMiddleware` - GZip - Response compression
  - `TrustedHostMiddleware` - Security - Host header validation
  - `HTTPSRedirectMiddleware` - Security - HTTPS redirect
  - `SessionMiddleware` - Session management
  - `AuthenticationMiddleware` - Authentication
  - `BaseHTTPMiddleware` - Custom HTTP middleware

#### Methods

- `scan(root: Path, exclude: list[str]) -> dict[str, Any]`: Scans for middleware usage.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns
  - **Returns**: Dictionary with:
    - `middleware`: List of standard middleware info dicts
    - `custom_middleware`: List of custom middleware info dicts

- `_scan_file(filepath: Path, root: Path) -> dict[str, list[dict[str, Any]]]`: Scans a file for middleware.
  - Returns dict with `standard` and `custom` lists

## Detected Patterns

### add_middleware Method
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(CustomMiddleware)
```

### Decorator Pattern
```python
@app.middleware("http")
async def my_middleware(request, call_next):
    ...
```

## Middleware Info Structure

```python
{
    "name": "CORSMiddleware",
    "file": "app/main.py",
    "line": 15,
    "description": "CORS - Cross-Origin Resource Sharing"  # only for known middleware
}
```

For decorator-based middleware:
```python
{
    "name": "my_middleware",
    "type": "decorator",
    "file": "app/main.py",
    "line": 20
}
```

## Usage

```python
from pathlib import Path
from codebase_index.scanners.middleware import MiddlewareScanner

scanner = MiddlewareScanner()
result = scanner.scan(Path("/path/to/project"), exclude=[])

print("Standard middleware:")
for mw in result["middleware"]:
    print(f"  {mw['name']}: {mw.get('description', 'N/A')}")

print("\nCustom middleware:")
for mw in result["custom_middleware"]:
    print(f"  {mw['name']} ({mw['file']}:{mw['line']})")
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/middleware.py | Lines: 110*
