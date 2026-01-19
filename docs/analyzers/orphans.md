# OrphanedFileScanner

> Auto-generated from `codebase_index/analyzers/orphans.py`

## Overview

Detects Python files that are never imported anywhere (potential dead code).

## Classes

### `OrphanedFileScanner`

Detects Python files that are never imported anywhere.

#### Class Constants

**`ENTRY_POINT_PATTERNS`** - Files run directly (not imported):
- `main.py`, `app.py`, `run_*.py`, `start_*.py`
- `manage.py`, `setup.py`, `conftest.py`
- `wsgi.py`, `asgi.py`

**`EXCLUDED_PATTERNS`** - Always excluded from orphan detection:
- `__init__.py`, `__main__.py`, `conftest.py`
- `test_*.py`, `*_test.py`

**`ENTRY_POINT_DIRS`** - Directories containing entry points:
- `migrations`, `alembic`, `scripts`, `examples`, `tests`

#### Methods

- `__init__()`: Initialize empty collections.
- `scan(root: Path, files: list[dict], exclude: list[str]) -> dict[str, Any]`: Detect orphaned files.
- `_path_to_module(path: str) -> str`: Convert file path to Python module name.
- `_is_excluded(filename: str) -> bool`: Check if file matches excluded patterns.
- `_is_entry_point(path: str, filename: str) -> bool`: Check if file is an entry point.
- `_is_imported(path: str, module_name: str | None) -> bool`: Check if a file/module is imported anywhere.
- `clear() -> None`: Clear collected data.

## Return Structure

```python
{
    "orphaned_files": [
        {"path": "unused_module.py", "lines": 150, "module_name": "unused_module"}
    ],
    "entry_points": ["main.py", "cli.py"],
    "total_python_files": 50,
    "orphaned_count": 3,
    "orphaned_lines": 450
}
```

## Usage

```python
from pathlib import Path
from codebase_index.analyzers.orphans import OrphanedFileScanner

scanner = OrphanedFileScanner()
results = scanner.scan(
    root=Path("."),
    files=index_data["files"],
    exclude=["venv/*", "build/*"]
)

print(f"Found {results['orphaned_count']} orphaned files ({results['orphaned_lines']} lines)")
for orphan in results["orphaned_files"]:
    print(f"  {orphan['path']} ({orphan['lines']} lines)")
```

---
*Source: codebase_index/analyzers/orphans.py | Lines: 204*
