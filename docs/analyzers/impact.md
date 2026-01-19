# ImpactAnalyzer

> Auto-generated from `codebase_index/analyzers/impact.py`

## Overview

Analyzes the impact radius of changes to a file by finding functions/classes defined in the file, callers of those functions, affected tests, and affected endpoints/routes.

## Classes

### `ImpactAnalyzer`

Analyzes the impact radius of file changes.

#### Properties

- `files_by_path: dict[str, dict[str, Any]]`: Files indexed by path (lazy-loaded).
- `call_graph: dict[str, Any]`: Call graph from the index (lazy-loaded).
- `reverse_call_graph: dict[str, list[str]]`: Reverse call graph - callee to callers (lazy-built).

#### Methods

- `__init__(index_data: dict[str, Any])`: Initialize with loaded index data.
- `analyze_file(file_path: str) -> dict[str, Any]`: Analyze the impact radius of changes to a file.
- `_find_file(file_path) -> dict[str, Any] | None`: Find file by exact or partial path match.
- `_extract_symbols(file_path, exports) -> list[dict[str, Any]]`: Extract function and class symbols from exports.
- `_find_direct_callers(file_path, symbols) -> list[dict[str, Any]]`: Find functions that directly call symbols in this file.
- `_find_transitive_callers(direct_callers, depth) -> list[dict[str, Any]]`: Find functions that transitively depend on the file.
- `_find_affected_tests(callers, file_path) -> list[dict[str, Any]]`: Find tests that could be affected by changes.
- `_find_affected_endpoints(file_path, symbols, callers) -> list[dict[str, Any]]`: Find API endpoints that could be affected.
- `_build_summary(result) -> str`: Build a human-readable summary.

## Return Structure

```python
{
    "file": "path/to/file.py",
    "symbols": [
        {"name": "MyClass", "type": "class", "qualified": "file.py:MyClass"}
    ],
    "direct_callers": [
        {"function": "other.py:func", "file": "other.py", "calls": "MyClass"}
    ],
    "transitive_callers": [
        {"function": "another.py:caller", "file": "another.py", "depth": 1}
    ],
    "affected_tests": [
        {"file": "tests/test_file.py", "reason": "imports from file"}
    ],
    "affected_endpoints": [
        {"method": "GET", "path": "/api/resource", "reason": "handler calls symbol"}
    ],
    "summary": "File defines 5 symbol(s); Impact: 3 direct caller(s), 7 transitive; 2 test(s) affected"
}
```

## Usage

```python
from codebase_index.analyzers.impact import ImpactAnalyzer

analyzer = ImpactAnalyzer(index_data)
impact = analyzer.analyze_file("codebase_index/parsers/python.py")

print(impact["summary"])
# "File defines 8 symbol(s); Impact: 5 direct caller(s), 12 transitive; 3 test(s) affected"

for caller in impact["direct_callers"]:
    print(f"  {caller['function']} calls {caller['calls']}")
```

---
*Source: codebase_index/analyzers/impact.py | Lines: 407*
