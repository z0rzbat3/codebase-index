# Python Parser Module

> Auto-generated from `codebase_index/parsers/python.py`

## Overview

Python AST-based parser for codebase-index. Uses the `ast` module for accurate code extraction with configurable patterns for routes, models, and schemas. Falls back to regex parsing for files with syntax errors.

## Classes

### `PythonParser`

Python parser using the ast module for accurate extraction.

**Attributes:**
- `supports_fallback = True`: Falls back to regex for syntax errors
- `internal_prefixes`: List of prefixes for internal imports (default: `["src", "app", "api", "lib", "core", "modules"]`)
- `route_patterns`: Configurable route detection patterns
- `model_patterns`: Configurable ORM model patterns
- `schema_patterns`: Configurable validation schema patterns

**Registration:** `@ParserRegistry.register("python", [".py", ".pyw"])`

#### Methods

- `configure(config: dict[str, Any]) -> None`: Configure parser with patterns from config. Supports `imports`, `routes`, `models`, `schemas` sections.

- `scan(filepath: Path) -> dict[str, Any]`: Scan a Python file and extract structure using AST.

  **Returns dict with:**
  - `classes`: List of class definitions with methods, bases, decorators
  - `functions`: List of top-level functions with signatures, calls, docstrings
  - `imports`: Dict with `internal`, `external`, and `names` lists
  - `routes`: Generic routes (config-driven)
  - `models`: ORM models (config-driven)
  - `schemas`: Validation schemas (config-driven)
  - `constants`: UPPER_CASE module-level assignments
  - `module_vars`: Other module-level assignments
  - `type_aliases`: Type alias definitions
  - Legacy keys: `fastapi_routes`, `sqlalchemy_tables`, `pydantic_models`

#### Key Internal Methods

- `_process_class(node, result)`: Extract class info including methods, bases, decorators, and detect models/schemas
- `_process_function(node, result)`: Extract function info and detect route decorators
- `_extract_signature(node) -> dict`: Extract function parameters and return type
- `_extract_calls(node) -> list[str]`: Extract all function/method calls from a function body
- `_extract_dynamic_calls(node) -> list[dict]`: Detect dynamic dispatch patterns (getattr, eval, etc.)
- `_categorize_import(module, imports)`: Classify imports as internal or external
- `_scan_regex(filepath) -> dict`: Fallback regex-based scanning

## Default Patterns

```python
# Route patterns (FastAPI/Starlette)
DEFAULT_ROUTE_PATTERNS = [
    {"regex": r"(router|app)\.(get|post|put|patch|delete|head|options)", "framework": "fastapi"},
]

# Model patterns (SQLAlchemy)
DEFAULT_MODEL_PATTERNS = [
    {"marker": "__tablename__", "type": "sqlalchemy"},
    {"base_class": "DeclarativeBase", "type": "sqlalchemy"},
]

# Schema patterns (Pydantic)
DEFAULT_SCHEMA_PATTERNS = [
    {"base_class": "BaseModel", "type": "pydantic"},
    {"base_class": "BaseSettings", "type": "pydantic"},
]
```

## Dynamic Call Detection

The parser flags dynamic dispatch patterns that static analysis cannot resolve:
- `getattr()` lookups
- Subscript dispatch (`handlers[key]()`)
- `eval()`/`exec()` calls
- `importlib.import_module()`
- `globals()`/`locals()` dispatch

## Usage

```python
from codebase_index.parsers.python import PythonParser

parser = PythonParser()
parser.configure({
    "imports": {"internal_prefixes": ["myapp", "lib"]},
    "routes": {"enabled": True, "patterns": [...]},
})

result = parser.scan(Path("app/main.py"))

for cls in result["classes"]:
    print(f"Class: {cls['name']} (bases: {cls['bases']})")
    for method in cls["methods"]:
        print(f"  - {method['signature']['formatted']}")
```

---
*Source: codebase_index/parsers/python.py | Lines: 902*
