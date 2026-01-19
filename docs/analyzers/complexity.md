# ComplexityAnalyzer

> Auto-generated from `codebase_index/analyzers/complexity.py`

## Overview

Analyzes code complexity and flags large files/functions based on configurable thresholds.

## Classes

### `ComplexityAnalyzer`

Analyzes code complexity and flags large files/functions.

#### Constructor

```python
def __init__(
    self,
    file_lines_warning: int = 500,
    file_lines_critical: int = 1000,
    function_lines_warning: int = 50,
    function_lines_critical: int = 100,
    class_methods_warning: int = 15,
    class_methods_critical: int = 25,
)
```

#### Methods

- `analyze(files: list[dict[str, Any]]) -> dict[str, Any]`: Analyze all files for complexity issues.
- `_analyze_file(file_info, result) -> None`: Analyze a single file for complexity.

## Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| File lines | 500 | 1000 |
| Function lines | 50 | 100 |
| Class methods | 15 | 25 |

## Return Structure

```python
{
    "large_files": [
        {"path": str, "lines": int, "severity": "warning"|"critical"}
    ],
    "large_functions": [
        {"path": str, "function": str, "lines": int, "severity": str}
    ],
    "complex_classes": [
        {"path": str, "class": str, "methods": int, "severity": str}
    ],
    "summary": {
        "files_warning": int,
        "files_critical": int,
        "functions_warning": int,
        "functions_critical": int,
    }
}
```

## Usage

```python
from codebase_index.analyzers.complexity import ComplexityAnalyzer

# Default thresholds
analyzer = ComplexityAnalyzer()
results = analyzer.analyze(index_data["files"])

# Custom thresholds
analyzer = ComplexityAnalyzer(
    file_lines_critical=800,
    function_lines_warning=30
)
results = analyzer.analyze(files)

# Check results
for f in results["large_files"]:
    print(f"{f['path']}: {f['lines']} lines ({f['severity']})")
```

---
*Source: codebase_index/analyzers/complexity.py | Lines: 142*
