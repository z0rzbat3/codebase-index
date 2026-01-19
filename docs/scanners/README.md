# Scanners Module

> Auto-generated documentation for `codebase_index/scanners/`

## Overview

The scanners module contains specialized analyzers that extract structured information from codebases. Each scanner focuses on a specific aspect of the project: dependencies, environment variables, API patterns, and more.

All scanners are instantiated by `CodebaseScanner` and their results are included in the generated index.

## Scanner Index

| Scanner | File | Description |
|---------|------|-------------|
| [AlembicScanner](alembic.md) | `alembic.py` | Scans Alembic database migrations and extracts revision info |
| [DependenciesScanner](dependencies.md) | `dependencies.py` | Extracts Python and Node.js dependencies from package files |
| [EnvScanner](env.md) | `env.py` | Finds environment variable names in code and .env files |
| [HttpCallsScanner](http_calls.md) | `http_calls.py` | Detects external HTTP calls (requests, httpx, fetch, axios) |
| [MiddlewareScanner](middleware.md) | `middleware.py` | Identifies FastAPI/Starlette middleware configuration |
| [RoutePrefixScanner](routes.md) | `routes.py` | Extracts FastAPI router prefixes for full path reconstruction |
| [TodoScanner](todo.md) | `todo.py` | Finds TODO, FIXME, HACK, XXX comments in code |
| [WebSocketScanner](websocket.md) | `websocket.py` | Detects WebSocket endpoints in FastAPI applications |

## Common Interface

All scanners follow a similar pattern:

```python
class SomeScanner:
    def scan(self, root: Path, exclude: list[str] = None) -> dict | list:
        """
        Args:
            root: Project root directory
            exclude: Patterns to exclude (optional for some scanners)

        Returns:
            Structured data specific to the scanner type
        """
```

## Usage Example

```python
from pathlib import Path
from codebase_index.scanners.dependencies import DependenciesScanner
from codebase_index.scanners.todo import TodoScanner
from codebase_index.scanners.http_calls import HttpCallsScanner

root = Path("/path/to/project")
exclude = ["venv", "node_modules", ".git"]

# Scan dependencies
deps_scanner = DependenciesScanner()
deps = deps_scanner.scan(root)
print(f"Python packages: {len(deps['python'])}")

# Scan TODOs
todo_scanner = TodoScanner()
todos = todo_scanner.scan(root, exclude)
print(f"Open TODOs: {len(todos)}")

# Scan external API calls
http_scanner = HttpCallsScanner()
calls = http_scanner.scan(root, exclude)
print(f"External domains: {calls['unique_domains']}")
```

## Architecture

```
codebase_index/scanners/
    __init__.py           # Package exports
    alembic.py            # AlembicScanner
    dependencies.py       # DependenciesScanner
    env.py                # EnvScanner
    http_calls.py         # HttpCallsScanner
    middleware.py         # MiddlewareScanner
    routes.py             # RoutePrefixScanner
    todo.py               # TodoScanner
    websocket.py          # WebSocketScanner
```

## Integration

Scanners are used by `CodebaseScanner` in `codebase_index/scanner.py`:

```python
class CodebaseScanner:
    def __init__(self):
        self.alembic_scanner = AlembicScanner()
        self.deps_scanner = DependenciesScanner()
        self.env_scanner = EnvScanner()
        # ... etc
```

Results are aggregated into the final index JSON under their respective keys.

---
*Source: codebase_index/scanners/*
