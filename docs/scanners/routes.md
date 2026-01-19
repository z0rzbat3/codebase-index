# RoutePrefixScanner

> Auto-generated from `codebase_index/scanners/routes.py`

## Overview

Scans FastAPI application entry points (main.py, app.py) for router prefix configurations. Extracts the mapping between router modules and their URL prefixes, enabling reconstruction of full API paths.

## Classes

### `RoutePrefixScanner`

Scan FastAPI main.py for router prefixes to build full paths.

#### Methods

- `scan(root: Path, exclude: list[str] | None = None) -> dict[str, str]`: Scans for include_router calls to extract prefixes.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns (defaults to `DEFAULT_EXCLUDE`)
  - **Returns**: Dictionary mapping router names to their prefixes

- `_scan_main_file(filepath: Path) -> dict[str, str]`: Scans a main.py file for include_router calls.
  - Parses `include_router()` calls with prefix arguments
  - Also handles router imports to match router names

## Detected Patterns

### Direct include_router
```python
app.include_router(agents.router, prefix="/api/v1/agents")
app.include_router(router, prefix="/api/v1/users", tags=["users"])
```

### Import-based routers
```python
from .routers import agents, chat, users
app.include_router(agents.router, prefix="/agents")
```

## Scanned Files

Searches for router configurations in:
- `{root}/**/main.py`
- `{root}/**/app.py`

## Usage

```python
from pathlib import Path
from codebase_index.scanners.routes import RoutePrefixScanner

scanner = RoutePrefixScanner()
prefixes = scanner.scan(Path("/path/to/project"))

# Example output: {"agents": "/api/v1/agents", "users": "/api/v1/users"}
for router_name, prefix in prefixes.items():
    print(f"Router '{router_name}' mounted at '{prefix}'")
```

## Integration with Route Analysis

This scanner's output can be combined with endpoint scanning to build full API paths:

```python
# If endpoint is @router.get("/list") in agents.py
# and prefix is "/api/v1/agents"
# Full path is: GET /api/v1/agents/list
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/routes.py | Lines: 95*
