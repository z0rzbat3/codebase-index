# ImportAggregator

> Auto-generated from `codebase_index/analyzers/imports.py`

## Overview

Aggregates imports across the codebase and detects missing/unused dependencies by comparing imports against declared dependencies.

## Classes

### `ImportAggregator`

Aggregates all imports across the codebase and detects missing/unused deps.

#### Methods

- `__init__()`: Initialize empty import collections.
- `add_imports(imports: list[str], filepath: str) -> None`: Add imports from a file.
- `add_internal_module(module_name: str) -> None`: Register a module as internal to the project.
- `analyze(declared_deps: list[str]) -> dict[str, Any]`: Analyze imports against declared dependencies.
- `clear() -> None`: Clear all collected data.

## Constants

### `PKG_TO_IMPORT`

Mapping of package names to import names for common mismatches:
- `pillow` -> `pil`
- `pyyaml` -> `yaml`
- `beautifulsoup4` -> `bs4`
- `scikit_learn` -> `sklearn`
- etc.

### `UMBRELLA_PACKAGES`

Packages that include multiple import namespaces:
- `fastapi` includes `fastapi`, `starlette`

## Return Structure

```python
{
    "total_unique_imports": 45,
    "third_party_imports": ["requests", "pydantic", ...],
    "missing_deps": [
        {"module": "undeclared_pkg", "used_in": ["file1.py", "file2.py"]}
    ],
    "unused_deps": ["declared_but_unused"]
}
```

## Usage

```python
from codebase_index.analyzers.imports import ImportAggregator

aggregator = ImportAggregator()

# Collect imports from all files
for file_info in index_data["files"]:
    imports = file_info["exports"].get("imports", {}).get("external", [])
    aggregator.add_imports(imports, file_info["path"])

# Mark internal modules
aggregator.add_internal_module("codebase_index")

# Analyze against requirements.txt
declared = ["requests", "pydantic", "click"]
results = aggregator.analyze(declared)

print(f"Missing: {results['missing_deps']}")
print(f"Unused: {results['unused_deps']}")
```

---
*Source: codebase_index/analyzers/imports.py | Lines: 163*
