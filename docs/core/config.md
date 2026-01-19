# config

> Auto-generated from `codebase_index/config.py`

## Overview

Configuration constants and loading utilities for codebase_index. Defines default exclusion patterns, standard library modules, and framework-specific detection patterns.

## Constants

### `DEFAULT_EXCLUDE`

List of default patterns to exclude from scanning:
- Build directories: `node_modules`, `__pycache__`, `dist`, `build`, `.next`
- Version control: `.git`
- Virtual environments: `.venv`, `venv`
- Cache directories: `coverage`, `.pytest_cache`, `.mypy_cache`
- File patterns: `*.pyc`, `*.pyo`, `*.log`, `*.egg-info`, `.DS_Store`

### `STDLIB_MODULES`

Frozenset of Python 3.9+ standard library module names. Used for distinguishing stdlib from third-party imports during import analysis.

### `DEFAULT_CONFIG`

Default configuration dictionary with sections for:
- **project**: name and description
- **routes**: Web framework route detection patterns (FastAPI, Flask, Django)
- **models**: ORM model detection (SQLAlchemy, Django, Tortoise)
- **schemas**: Schema/serializer detection (Pydantic, DRF, Marshmallow)
- **auth**: Authentication patterns (parameters and decorators)
- **middleware**: Middleware detection (FastAPI, Django, Express)
- **websockets**: WebSocket endpoint detection
- **categories**: File categorization patterns for Python and TypeScript
- **imports**: Internal vs external import classification
- **migrations**: Database migration detection
- **complexity**: Thresholds for file/function size warnings
- **exclude**: Additional exclusion patterns

## Functions

### `load_config(config_path) -> dict[str, Any]`

Load configuration from YAML file, merged with defaults.

**Parameters:**
- `config_path`: Path to the YAML configuration file

**Returns:** Configuration dictionary with user values merged over defaults

**Raises:**
- `SystemExit`: If PyYAML is not installed
- `FileNotFoundError`: If config file doesn't exist

### `get_config_template() -> str`

Generate a well-documented YAML config template for LLMs to customize. Includes extensive comments explaining each section and how to adapt for different frameworks.

## Usage

```python
from codebase_index.config import DEFAULT_CONFIG, DEFAULT_EXCLUDE, load_config
from pathlib import Path

# Use defaults
config = DEFAULT_CONFIG.copy()

# Load custom config
custom_config = load_config(Path('codebase-index.yaml'))

# Generate template
from codebase_index.config import get_config_template
print(get_config_template())
```

---
*Source: codebase_index/config.py | Lines: 571*
