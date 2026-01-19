# TodoScanner

> Auto-generated from `codebase_index/scanners/todo.py`

## Overview

Scans for TODO, FIXME, HACK, and XXX comments in source code. Supports Python and TypeScript/JavaScript comment styles. Useful for tracking technical debt, pending work, and code quality issues.

## Classes

### `TodoScanner`

Scan for TODO, FIXME, HACK, XXX comments.

#### Class Attributes

- `PATTERNS`: Regex patterns for different comment styles:
  - Python: `# TODO: message`
  - TypeScript/JS: `// TODO: message`
  - Multiline: `/* TODO: message */`

- `FILE_PATTERNS`: Glob patterns for files to scan:
  - `**/*.py`
  - `**/*.ts`, `**/*.tsx`
  - `**/*.js`, `**/*.jsx`

#### Methods

- `scan(root: Path, exclude: list[str]) -> list[dict[str, Any]]`: Scans all files for TODO/FIXME comments.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns
  - **Returns**: List of todo items

- `_scan_file(filepath: Path, root: Path) -> list[dict[str, Any]]`: Scans a single file for TODOs.
  - Case-insensitive matching
  - Only matches once per line (first match wins)

## Supported Comment Types

| Type | Description |
|------|-------------|
| `TODO` | Pending tasks or features to implement |
| `FIXME` | Known bugs or issues to fix |
| `HACK` | Workarounds or temporary solutions |
| `XXX` | Areas needing attention or review |

## Todo Item Structure

```python
{
    "type": "TODO",
    "message": "Implement caching for this endpoint",
    "file": "api/routes.py",
    "line": 42
}
```

## Detected Patterns

```python
# TODO: Add input validation
# FIXME: This breaks on edge case
# HACK: Workaround for upstream bug
# XXX: Review security implications
```

```typescript
// TODO: Refactor this component
/* FIXME: Memory leak in useEffect */
```

## Usage

```python
from pathlib import Path
from codebase_index.scanners.todo import TodoScanner

scanner = TodoScanner()
todos = scanner.scan(Path("/path/to/project"), exclude=[])

# Group by type
by_type = {}
for todo in todos:
    t = todo["type"]
    by_type.setdefault(t, []).append(todo)

for todo_type, items in by_type.items():
    print(f"\n{todo_type} ({len(items)} items):")
    for item in items:
        print(f"  {item['file']}:{item['line']} - {item['message']}")
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/todo.py | Lines: 96*
