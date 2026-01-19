# EnvScanner

> Auto-generated from `codebase_index/scanners/env.py`

## Overview

Scans for environment variable usage across the codebase. Extracts variable NAMES only (never values) from .env files and detects usage patterns in Python, TypeScript/JavaScript, and Docker files.

**Security Note**: This scanner intentionally only extracts variable names, never their values.

## Classes

### `EnvScanner`

Scan for environment variable usage (names only, no values).

#### Methods

- `scan(root: Path, exclude: list[str] | None = None) -> dict[str, Any]`: Scans for environment variables.
  - **Args**:
    - `root` - Project root directory
    - `exclude` - Exclusion patterns (defaults to `DEFAULT_EXCLUDE`)
  - **Returns**: Dictionary with:
    - `dotenv_files`: Dict mapping .env file paths to list of variable names
    - `python_usage`: Sorted list of env vars accessed in Python code
    - `typescript_usage`: Sorted list of env vars accessed in TS/JS code
    - `docker_usage`: Sorted list of env vars in Docker files

- `_parse_dotenv(filepath: Path) -> list[str]`: Parses .env file for variable names.
  - Matches pattern: `VAR_NAME=` (uppercase with underscores)
  - Skips comments and empty lines

- `_scan_python_env(filepath: Path) -> set[str]`: Scans Python file for env var access.
  - Detects: `os.environ["VAR"]`, `os.environ.get("VAR")`, `os.getenv("VAR")`

- `_scan_typescript_env(filepath: Path) -> set[str]`: Scans TypeScript/JavaScript for env var access.
  - Detects: `process.env.VAR_NAME`, `process.env["VAR_NAME"]`
  - Detects Vite: `import.meta.env.VITE_VAR`

## Detected Patterns

### Python
```python
os.environ["DATABASE_URL"]
os.environ.get("API_KEY")
os.getenv("SECRET_TOKEN")
```

### TypeScript/JavaScript
```typescript
process.env.NODE_ENV
process.env["DATABASE_URL"]
import.meta.env.VITE_API_URL  // Vite
```

## Usage

```python
from pathlib import Path
from codebase_index.scanners.env import EnvScanner

scanner = EnvScanner()
result = scanner.scan(Path("/path/to/project"))

print("Environment files found:")
for filepath, vars in result["dotenv_files"].items():
    print(f"  {filepath}: {vars}")

print(f"\nPython env vars: {result['python_usage']}")
print(f"TypeScript env vars: {result['typescript_usage']}")
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/env.py | Lines: 184*
