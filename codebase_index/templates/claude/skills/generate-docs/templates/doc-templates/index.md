# {{directory_name}}

> Documentation index for `{{source_directory}}/`

## Overview

{{directory_description}}

## Contents

| File | Description | Lines |
|------|-------------|-------|
{{#each files}}
| [{{name}}]({{filename}}.md) | {{description}} | {{lines}} |
{{/each}}

## Quick Links

{{#each files}}
- [{{name}}]({{filename}}.md) - {{short_description}}
{{/each}}

## Structure

```
{{source_directory}}/
{{#each files}}
├── {{filename}}{{extension}}
{{/each}}
```

---
*Last updated: {{timestamp}}*
