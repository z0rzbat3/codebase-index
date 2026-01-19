# TestCoverageMapper

> Auto-generated from `codebase_index/analyzers/coverage.py`

## Overview

Maps source files to their corresponding test files by analyzing naming conventions and directory structure.

## Classes

### `TestCoverageMapper`

Maps source files to their corresponding test files.

#### Methods

- `__init__(root: Path)`: Initialize with project root directory.
- `collect_test_files(exclude: list[str]) -> None`: Collect all test files in the project using glob patterns.
- `map_source_to_test(source_files: list[dict[str, Any]]) -> dict[str, Any]`: Map source files to potential test files.
- `_find_test_file(source_path: str) -> str | None`: Find a test file for a given source file.
- `clear() -> None`: Clear collected test files.

## Test File Patterns

The mapper looks for test files matching:
- `**/test_*.py`
- `**/tests/test_*.py`
- `**/*_test.py`
- `**/tests/**/*.py`

## Return Structure

```python
{
    "covered": [
        {"source": "mymodule.py", "test": "tests/test_mymodule.py"}
    ],
    "uncovered": ["other.py"],
    "test_files": ["tests/test_mymodule.py", ...],
    "coverage_percentage": 75.0
}
```

## Matching Logic

For a source file like `agent_service.py`, the mapper looks for:
1. Direct match: `test_agent_service.py` or `agent_service_test.py`
2. Partial match: `test_agent.py` (matches first part of underscore-separated name)

## Usage

```python
from pathlib import Path
from codebase_index.analyzers.coverage import TestCoverageMapper

mapper = TestCoverageMapper(Path("."))
mapper.collect_test_files(exclude=["venv/*"])
coverage = mapper.map_source_to_test(index_data["files"])

print(f"Coverage: {coverage['coverage_percentage']}%")
print(f"Uncovered: {coverage['uncovered']}")
```

---
*Source: codebase_index/analyzers/coverage.py | Lines: 140*
