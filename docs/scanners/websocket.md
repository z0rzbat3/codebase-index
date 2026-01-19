# WebSocketScanner

> Auto-generated from `codebase_index/scanners/websocket.py`

## Overview

Scans for WebSocket endpoints in FastAPI and other Python web frameworks. Detects decorator-based WebSocket routes and functions with WebSocket type hints. Useful for mapping real-time API endpoints.

## Classes

### `WebSocketScanner`

Scan for WebSocket endpoints.

#### Methods

- `scan(root: Path, exclude: list[str]) -> dict[str, Any]`: Scans for WebSocket endpoints.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns
  - **Returns**: Dictionary with:
    - `endpoints`: List of endpoint info dicts
    - `total`: Total count of endpoints

- `_scan_file(filepath: Path, root: Path) -> list[dict[str, Any]]`: Scans a file for WebSocket endpoints.

## Detected Patterns

### Decorator-based Routes
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ...

@app.websocket("/chat/{room_id}")
async def chat_handler(websocket: WebSocket, room_id: str):
    ...
```

### Type Hint Detection
Functions with `WebSocket` in their parameter type hints are also detected (as backup):
```python
async def handle_connection(ws: WebSocket):
    ...
```

## Endpoint Info Structure

```python
{
    "path": "/ws/chat",
    "handler": "chat_endpoint",
    "file": "api/websocket.py",
    "line": 15
}
```

For type-hint inferred endpoints:
```python
{
    "path": "(inferred from type hint)",
    "handler": "handle_connection",
    "file": "api/websocket.py",
    "line": 30
}
```

## Usage

```python
from pathlib import Path
from codebase_index.scanners.websocket import WebSocketScanner

scanner = WebSocketScanner()
result = scanner.scan(Path("/path/to/project"), exclude=[])

print(f"Found {result['total']} WebSocket endpoints:")
for endpoint in result["endpoints"]:
    print(f"  {endpoint['path']} -> {endpoint['handler']}")
    print(f"    ({endpoint['file']}:{endpoint['line']})")
```

## Handler Detection

The scanner looks up to 5 lines after a `@websocket` decorator to find the async function definition. This handles cases with multiple decorators or blank lines.

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/websocket.py | Lines: 99*
