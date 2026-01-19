# HttpCallsScanner

> Auto-generated from `codebase_index/scanners/http_calls.py`

## Overview

Scans for external HTTP calls in Python and TypeScript/JavaScript code. Detects usage of common HTTP client libraries and extracts URL, method, and location information. Useful for API dependency mapping and security auditing.

## Classes

### `HttpCallsScanner`

Scan for external HTTP calls (httpx, requests, aiohttp, fetch).

#### Class Attributes

- `PYTHON_PATTERNS`: Regex patterns for Python HTTP libraries (requests, httpx, aiohttp)
- `TS_PATTERNS`: Regex patterns for JS/TS HTTP libraries (fetch, axios)

#### Methods

- `scan(root: Path, exclude: list[str]) -> dict[str, Any]`: Scans for external HTTP calls.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns
  - **Returns**: Dictionary with:
    - `python_calls`: List of HTTP call dicts from Python files
    - `typescript_calls`: List of HTTP call dicts from TS/JS files
    - `total_external_calls`: Combined count
    - `unique_domains`: Sorted list of unique domains called

- `_scan_python_file(filepath: Path, root: Path) -> list[dict[str, Any]]`: Scans Python file for HTTP calls.

- `_scan_ts_file(filepath: Path, root: Path) -> list[dict[str, Any]]`: Scans TypeScript/JavaScript file for HTTP calls.

## Detected Libraries

### Python
- `requests` - requests.get(), requests.post(), etc.
- `httpx` - httpx.get(), httpx.AsyncClient(), etc.
- `aiohttp` - session.get(), aiohttp.ClientSession()

### TypeScript/JavaScript
- `fetch` - fetch("url"), fetch(`template`)
- `axios` - axios.get(), axios({ url: "..." })

## Call Info Structure

Each detected call contains:
```python
{
    "file": "relative/path/to/file.py",
    "line": 42,
    "library": "requests",
    "method": "POST",
    "url": "https://api.example.com/endpoint"
}
```

## Usage

```python
from pathlib import Path
from codebase_index.scanners.http_calls import HttpCallsScanner

scanner = HttpCallsScanner()
result = scanner.scan(Path("/path/to/project"), exclude=[])

print(f"Total external calls: {result['total_external_calls']}")
print(f"Unique domains: {result['unique_domains']}")

for call in result["python_calls"]:
    print(f"  {call['method']} {call['url']} ({call['file']}:{call['line']})")
```

## Notes

- Internal API calls (paths starting with `/` or `{`) are filtered out
- Domain extraction handles protocol prefixes and port numbers

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/http_calls.py | Lines: 166*
