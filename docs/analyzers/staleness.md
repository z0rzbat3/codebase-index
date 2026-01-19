# StalenessChecker

> Auto-generated from `codebase_index/analyzers/staleness.py`

## Overview

Compares an index file against the current state of the codebase to determine if the index is out of date using git history or file modification times.

## Classes

### `StalenessChecker`

Checks if an index file is stale compared to the codebase.

#### Class Constants

**`INDEX_FILE_PATTERNS`** - Patterns excluded from staleness checks:
- `index.json`, `codebase_index.json`, `codebase-index.json`
- `.codebase-index.json`, `*_index.json`

#### Methods

- `__init__(root: Path, index_data: dict, index_file: Path | None)`: Initialize with root directory, index data, and optional index file path.
- `check() -> dict[str, Any]`: Check if the index is stale.
- `_get_git_changes_since(since: datetime) -> dict[str, list[str]] | None`: Get files changed in git since the given time.
- `_get_modified_files_since(since, indexed_files) -> list[str]`: Fallback: check file modification times.
- `_filter_index_files(files) -> list[str]`: Filter out index files from the change list.
- `_build_summary(result) -> str`: Build a human-readable summary.

## Return Structure

```python
{
    "is_stale": True,
    "index_age_hours": 24.5,
    "index_generated_at": "2024-01-15T10:30:00Z",
    "changed_files": ["src/module.py"],
    "new_files": ["src/new_file.py"],
    "deleted_files": ["src/old_file.py"],
    "total_changes": 3,
    "summary": "Index is 24.5 hours old; 3 files changed (1 modified, 1 added, 1 deleted); Recommend: regenerate index"
}
```

## Change Detection

1. **Primary:** Git history since index generation timestamp
   - Committed changes via `git log --since`
   - Uncommitted changes via `git status --porcelain`

2. **Fallback:** File modification times (if git unavailable)
   - Compares mtime against index generation time

## Usage

```python
from pathlib import Path
from codebase_index.analyzers.staleness import StalenessChecker

checker = StalenessChecker(
    root=Path("."),
    index_data=index_data,
    index_file=Path("index.json")
)
result = checker.check()

if result["is_stale"]:
    print(result["summary"])
    print(f"Changed files: {result['changed_files']}")
else:
    print("Index is up to date")
```

---
*Source: codebase_index/analyzers/staleness.py | Lines: 319*
