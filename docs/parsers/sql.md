# SQL Parser Module

> Auto-generated from `codebase_index/parsers/sql.py`

## Overview

SQL regex-based parser for codebase-index. Extracts table definitions, indexes, and views from SQL files using pattern matching.

## Classes

### `SQLParser`

SQL parser using regex patterns. Extracts DDL statements for tables, indexes, and views.

**Registration:** `@ParserRegistry.register("sql", [".sql"])`

#### Methods

- `scan(filepath: Path) -> dict[str, Any]`: Scan a SQL file.

  **Returns dict with:**
  - `tables`: List of table definitions `{"name": "table_name"}`
  - `indexes`: List of index definitions `{"name": "idx_name", "table": "table_name"}`
  - `views`: List of view definitions `{"name": "view_name"}`
  - `error`: Error message if file could not be read

## Supported SQL Patterns

### Tables
```sql
CREATE TABLE users ...
CREATE TABLE IF NOT EXISTS users ...
CREATE TABLE `users` ...
CREATE TABLE "users" ...
```

### Indexes
```sql
CREATE INDEX idx_email ON users ...
CREATE UNIQUE INDEX idx_email ON users ...
```

### Views
```sql
CREATE VIEW active_users AS ...
CREATE OR REPLACE VIEW active_users AS ...
```

## Output Structure

```python
{
    "tables": [
        {"name": "users"},
        {"name": "orders"}
    ],
    "indexes": [
        {"name": "idx_users_email", "table": "users"},
        {"name": "idx_orders_date", "table": "orders"}
    ],
    "views": [
        {"name": "active_users"},
        {"name": "order_summary"}
    ]
}
```

## Usage

```python
from codebase_index.parsers.sql import SQLParser

parser = SQLParser()
result = parser.scan(Path("migrations/001_initial.sql"))

print(f"Tables: {[t['name'] for t in result['tables']]}")
print(f"Indexes: {[i['name'] for i in result['indexes']]}")
print(f"Views: {[v['name'] for v in result['views']]}")
```

## Limitations

- Regex-based parsing may miss complex or non-standard SQL syntax
- Does not extract column definitions or constraints
- Does not parse stored procedures or functions

---
*Source: codebase_index/parsers/sql.py | Lines: 79*
