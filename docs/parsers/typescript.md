# TypeScript Parser Module

> Auto-generated from `codebase_index/parsers/typescript.py`

## Overview

TypeScript/React regex-based parser for codebase-index. Extracts components, hooks, functions, types, interfaces, and imports from TypeScript and JavaScript files. Supports configurable internal import aliases.

## Classes

### `TypeScriptParser`

TypeScript/React parser using regex patterns.

**Attributes:**
- `internal_patterns`: List of patterns for internal imports (default: `[".", "@/", "~/"]`)

**Registration:** `@ParserRegistry.register("typescript", [".ts", ".tsx", ".js", ".jsx"])`

#### Methods

- `configure(config: dict[str, Any]) -> None`: Configure the parser. Supports custom internal import prefixes via `imports.internal_prefixes`.

- `scan(filepath: Path) -> dict[str, Any]`: Scan a TypeScript/React file.

  **Returns dict with:**
  - `components`: React components (PascalCase exported functions/consts)
  - `hooks`: React hooks (functions starting with `use`)
  - `functions`: Other exported functions
  - `types`: Exported type definitions
  - `interfaces`: Exported interface definitions
  - `imports`: Dict with `internal` and `external` lists
  - `api_calls`: Detected fetch/axios calls
  - `routes`: Express/Next.js route definitions

- `_process_line(line: str, line_num: int, result: dict) -> None`: Process a single line of code for pattern matching.

- `_categorize_import(module: str, imports: dict) -> None`: Categorize import as internal or external based on configured patterns.

## Detection Patterns

### Components & Hooks
```typescript
export function UserProfile() { }     // Component (PascalCase)
export function useAuth() { }         // Hook (starts with 'use')
export const Button = () => { }       // Component (PascalCase const)
export const useForm = () => { }      // Hook (starts with 'use')
```

### Types & Interfaces
```typescript
export type UserProps = { }           // Type
export interface IUser { }            // Interface
```

### Imports
```typescript
import { Button } from './Button'     // Internal (starts with '.')
import { api } from '@/lib/api'       // Internal (starts with '@/')
import React from 'react'             // External
import { z } from 'zod'               // External
```

### Routes (Express)
```typescript
app.get('/users', handler)            // Express route
router.post('/login', handler)        // Express route
```

### API Calls
```typescript
fetch('/api/users')                   // Fetch call
axios.get('/api/data')                // Axios call
```

## Output Structure

```python
{
    "components": [{"name": "UserProfile", "line": 10}],
    "hooks": [{"name": "useAuth", "line": 25}],
    "functions": [{"name": "formatDate", "line": 50}],
    "types": [{"name": "UserProps", "line": 5}],
    "interfaces": [{"name": "IUser", "line": 8}],
    "imports": {
        "internal": ["./Button", "@/lib/api"],
        "external": ["react", "zod"]
    },
    "api_calls": [{"url": "/api/users", "line": 30}],
    "routes": [{"method": "GET", "path": "/users", "line": 15, "framework": "express"}]
}
```

## Usage

```python
from codebase_index.parsers.typescript import TypeScriptParser

parser = TypeScriptParser()
parser.configure({
    "imports": {"internal_prefixes": ["@myapp", "~"]}
})

result = parser.scan(Path("src/components/UserList.tsx"))

print("Components:", [c["name"] for c in result["components"]])
print("Hooks:", [h["name"] for h in result["hooks"]])
print("External deps:", result["imports"]["external"])
```

## Limitations

- Regex-based parsing may miss complex patterns
- Does not perform full TypeScript type resolution
- Arrow functions without `export` keyword are not detected

---
*Source: codebase_index/parsers/typescript.py | Lines: 191*
