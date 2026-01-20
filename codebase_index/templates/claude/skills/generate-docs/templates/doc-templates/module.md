# {{module_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{docstring}}

{{#if classes}}
## Classes

{{#each classes}}
### `{{name}}`

{{docstring}}

{{#if methods}}
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
{{#each methods}}
| `{{name}}` | {{params}} | `{{returns}}` | {{description}} |
{{/each}}
{{/if}}

{{/each}}
{{/if}}

{{#if functions}}
## Functions

{{#each functions}}
### `{{name}}({{params}})`

{{docstring}}

**Parameters:**
{{#each parameters}}
- `{{name}}` (`{{type}}`): {{description}}
{{/each}}

**Returns:** `{{return_type}}` - {{return_description}}

{{#if raises}}
**Raises:**
{{#each raises}}
- `{{exception}}`: {{condition}}
{{/each}}
{{/if}}

{{/each}}
{{/if}}

{{#if constants}}
## Constants

| Name | Value | Description |
|------|-------|-------------|
{{#each constants}}
| `{{name}}` | `{{value}}` | {{description}} |
{{/each}}
{{/if}}

## Usage

```python
{{usage_example}}
```

---
*Source: `{{source_path}}` ({{line_count}} lines)*
