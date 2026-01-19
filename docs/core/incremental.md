# incremental

> Auto-generated from `codebase_index/incremental.py`

## Overview

Incremental updater for codebase_index. Updates an existing index by only re-scanning files that have changed, rather than doing a full re-scan of the entire codebase.

## Classes

### `IncrementalUpdater`

Incrementally update an existing index by comparing file hashes to detect changes. Much faster than full re-scan for large codebases with few changes.

#### Constructor

```python
IncrementalUpdater(
    root: Path,
    index_data: dict[str, Any],
    exclude: list[str],
    exclude_extensions: set[str] | None = None
)
```

**Parameters:**
- `root`: Root directory of the codebase
- `index_data`: The existing index data to update
- `exclude`: Patterns to exclude from scanning
- `exclude_extensions`: File extensions to exclude

#### Methods

- `update(scanner) -> dict[str, Any]`: Perform incremental update using the provided CodebaseScanner. Returns dictionary with update results and statistics including added, updated, deleted, unchanged counts, and duration_ms.

- `_get_current_files() -> list[Path]`: Get list of current files in codebase respecting exclusions and supported parsers from ParserRegistry.

- `_compute_hash(file_path) -> str`: Compute SHA-256 hash of file contents (first 16 hex chars).

- `_apply_updates(scanner, changes) -> dict[str, Any]`: Apply detected changes to create updated index. Preserves semantic embeddings and analysis results while rebuilding file-specific data.

- `_scan_files(scanner, file_paths, updated) -> None`: Scan specific files and add results to updated index including endpoints, schemas, and call graph entries.

- `_detect_language(suffix) -> str`: Detect language from file extension.

## Functions

### `incremental_update(root, index_data, exclude, exclude_extensions, config) -> dict[str, Any]`

Convenience function to perform incremental update.

**Parameters:**
- `root`: Root directory of the codebase
- `index_data`: Existing index data
- `exclude`: Patterns to exclude
- `exclude_extensions`: File extensions to exclude
- `config`: Configuration dictionary

**Returns:** Update result with `status`, `changes`, and `index` keys.

## Usage

```python
from pathlib import Path
from codebase_index.incremental import incremental_update

# Perform incremental update
result = incremental_update(
    root=Path('.'),
    index_data=existing_index,
    exclude=['node_modules', '__pycache__'],
    exclude_extensions={'.log'},
    config=my_config
)

print(f"Added: {len(result['changes']['added'])}")
print(f"Updated: {len(result['changes']['updated'])}")
print(f"Deleted: {len(result['changes']['deleted'])}")
print(f"Duration: {result['changes']['duration_ms']}ms")
```

---
*Source: codebase_index/incremental.py | Lines: 423*
