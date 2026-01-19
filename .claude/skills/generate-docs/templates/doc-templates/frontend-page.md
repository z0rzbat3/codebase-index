# {{component_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{description}}

## Route

| Property | Value |
|----------|-------|
| Path | `{{route_path}}` |
| Auth Required | {{auth_required}} |
| Layout | {{layout}} |

## Props

{{#if props}}
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
{{#each props}}
| `{{name}}` | `{{type}}` | {{required}} | {{default}} | {{description}} |
{{/each}}
{{else}}
*No props*
{{/if}}

## State

{{#each state}}
- `{{name}}`: `{{type}}` - {{description}}
{{/each}}

## Hooks

{{#each hooks}}
- `{{name}}()` - {{description}}
{{/each}}

## Key Components

{{#each components}}
- `<{{name}}>` - {{description}}
{{/each}}

## API Calls

{{#each api_calls}}
- `{{method}} {{endpoint}}` - {{description}}
{{/each}}

---
*Source: `{{source_path}}` ({{line_count}} lines)*
