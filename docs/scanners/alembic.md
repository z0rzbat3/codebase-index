# AlembicScanner

> Auto-generated from `codebase_index/scanners/alembic.py`

## Overview

Scans for Alembic database migrations and extracts revision information. Detects migration files in standard Alembic directory structures and parses metadata including revision IDs, down-revisions, messages, and database operations.

## Classes

### `AlembicScanner`

Scan for Alembic database migrations.

#### Methods

- `scan(root: Path) -> dict[str, Any]`: Scans for Alembic migrations in the project.
  - **Args**: `root` - Project root directory
  - **Returns**: Dictionary with:
    - `migrations`: List of migration info dicts
    - `total`: Total count of migrations
    - `latest_revision`: Most recent revision ID
    - `has_alembic`: Boolean indicating Alembic presence

- `_scan_migrations(migrations_dir: Path, root: Path) -> list[dict[str, Any]]`: Scans migration files in a directory.

- `_parse_migration(filepath: Path, root: Path) -> dict[str, Any] | None`: Parses a single migration file extracting:
  - `file`: Relative file path
  - `filename`: File name
  - `revision`: Revision ID
  - `down_revision`: Previous revision (or None for initial)
  - `message`: Migration description from docstring
  - `create_date`: Creation date if present
  - `operations`: List of detected operations (create_table, add_column, etc.)

## Detected Operations

The scanner identifies these Alembic operations:
- `create_table` / `drop_table`
- `add_column` / `drop_column`
- `create_index` / `drop_index`
- `alter_column`
- `create_foreign_key`

## Migration Directory Locations

Searches for migrations in:
- `{root}/migrations/versions/`
- `{root}/alembic/versions/`

Also checks for `alembic.ini` at the project root.

## Usage

```python
from pathlib import Path
from codebase_index.scanners.alembic import AlembicScanner

scanner = AlembicScanner()
result = scanner.scan(Path("/path/to/project"))

if result["has_alembic"]:
    print(f"Found {result['total']} migrations")
    print(f"Latest revision: {result['latest_revision']}")

    for migration in result["migrations"]:
        print(f"  {migration['revision']}: {migration.get('message', 'No message')}")
```

## Called By

- `CodebaseScanner.__init__` - Instantiated during scanner initialization

---
*Source: codebase_index/scanners/alembic.py | Lines: 142*
