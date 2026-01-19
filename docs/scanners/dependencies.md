# DependenciesScanner

> Auto-generated from `codebase_index/scanners/dependencies.py`

## Overview

Scans for project dependencies from multiple package manager formats: Python's requirements.txt and pyproject.toml, and Node.js's package.json. Extracts package names (without version specifiers) and organizes them by ecosystem.

## Classes

### `DependenciesScanner`

Scan for project dependencies from requirements.txt, package.json, etc.

#### Methods

- `scan(root: Path) -> dict[str, Any]`: Scans for all dependency files.
  - **Args**: `root` - Project root directory
  - **Returns**: Dictionary with:
    - `python`: List of Python package names (deduplicated)
    - `node`: Dict with `dependencies` and `devDependencies` lists

- `_parse_requirements(filepath: Path) -> list[str]`: Parses requirements.txt file.
  - Skips comments, empty lines, and pip options (lines starting with `-`)
  - Extracts package names before version specifiers (`==`, `>=`, etc.)

- `_parse_pyproject(filepath: Path) -> list[str]`: Parses pyproject.toml for dependencies.
  - Uses `tomllib` (Python 3.11+) or falls back to `tomli`
  - Supports `[project.dependencies]` format
  - Supports `[project.optional-dependencies]` groups
  - Supports Poetry format: `[tool.poetry.dependencies]` and `[tool.poetry.group.*.dependencies]`
  - Filters out self-references and Python version specifiers

- `_parse_pyproject_regex(filepath: Path) -> list[str]`: Fallback regex parsing when no TOML library is available.

- `_parse_package_json(filepath: Path) -> dict[str, list[str]]`: Parses package.json for dependencies.
  - Returns dict with `dependencies` and `devDependencies` lists

## Package.json Locations

Searches for package.json in:
- `{root}/package.json`
- `{root}/frontend/package.json`
- `{root}/src/frontend/package.json`
- `{root}/client/package.json`
- `{root}/web/package.json`

## Usage

```python
from pathlib import Path
from codebase_index.scanners.dependencies import DependenciesScanner

scanner = DependenciesScanner()
result = scanner.scan(Path("/path/to/project"))

print(f"Python deps: {len(result['python'])}")
for pkg in result["python"]:
    print(f"  - {pkg}")

print(f"Node deps: {len(result['node']['dependencies'])}")
print(f"Node devDeps: {len(result['node']['devDependencies'])}")
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/dependencies.py | Lines: 212*
