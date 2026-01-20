# {{class_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{docstring}}

## Table: `{{table_name}}`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
{{#each columns}}
| `{{name}}` | `{{type}}` | {{nullable}} | {{default}} | {{description}} |
{{/each}}

## Primary Key

- `{{primary_key}}`

## Relationships

{{#each relationships}}
- **{{name}}** (`{{type}}`): → `{{target_table}}` via `{{foreign_key}}`
{{/each}}

## Indexes

{{#each indexes}}
- `{{name}}`: ({{columns}}) {{#if unique}}UNIQUE{{/if}}
{{/each}}

## Usage

```python
from {{module}} import {{class_name}}

# Create
record = {{class_name}}({{example_create}})
db.add(record)

# Query
result = db.query({{class_name}}).filter_by({{example_filter}}).first()
```

---
*Source: `{{source_path}}` ({{line_count}} lines)*
