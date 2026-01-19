# {{filename}}

> Auto-generated from `{{source_path}}`

## Overview

{{description}}

## Endpoints

{{#each endpoints}}
### `{{method}} {{path}}`

{{description}}

**Auth:** {{auth_required}}

{{#if request_body}}
**Request Body:**
```json
{{request_body}}
```
{{/if}}

{{#if query_params}}
**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
{{#each query_params}}
| `{{name}}` | `{{type}}` | {{required}} | {{description}} |
{{/each}}
{{/if}}

**Response:** `{{response_code}}`
```json
{{response}}
```

**Example:**
```bash
curl -X {{method}} http://localhost:8000{{path}} \
  -H "Authorization: Bearer $TOKEN"
```
{{/each}}

## Dependencies

- {{#each dependencies}}{{this}}{{/each}}

---
*Source: `{{source_path}}` ({{line_count}} lines)*
