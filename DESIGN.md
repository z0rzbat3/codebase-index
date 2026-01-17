# Codebase Index - Design Document

## Overview

A CLI tool that generates comprehensive, accurate inventories of codebases. Designed for modern full-stack applications (React, Python, Docker, PostgreSQL).

---

## Core Philosophy

1. **Discovery over declaration** - Scan actual files, don't trust config
2. **Convention-aware** - Understand common patterns (pages/, services/, etc.)
3. **Language-specific parsing** - Use appropriate patterns per language
4. **Diffable output** - Generate deterministic JSON for version control
5. **Validation mode** - Compare reality vs existing index

---

## Proposed CLI Interface

```bash
# Generate fresh index
codebase-index scan [path] [options]

# Validate existing index against reality
codebase-index validate <index.json> [path]

# Show diff between two indexes
codebase-index diff <old.json> <new.json>

# Interactive setup
codebase-index init
```

### Options

```
--output, -o      Output file (default: stdout)
--format, -f      json|yaml|sqlite (default: json)
--config, -c      Config file path (default: .codebase-index.yaml)
--verbose, -v     Show scanning progress
--hash            Include file content hashes (sha256)
--deps            Analyze import/dependency relationships
--git             Include git metadata (commit, branch, last modified)
```

---

## Architecture

```
codebase-index/
├── codebase-index           # Main CLI entry point (bash or python)
├── scanners/
│   ├── python_scanner.py    # Python: classes, functions, decorators, imports
│   ├── typescript_scanner.py # TS/TSX: components, hooks, exports, imports
│   ├── sql_scanner.py       # SQL: tables, columns, indexes
│   ├── docker_scanner.py    # Docker: services, ports, volumes
│   └── generic_scanner.py   # Fallback: file metadata only
├── outputs/
│   ├── json_output.py       # JSON formatter
│   ├── yaml_output.py       # YAML formatter
│   └── sqlite_output.py     # SQLite writer
├── templates/
│   └── config.yaml          # Default config template
├── config.py                # Config loader
├── utils.py                 # Shared utilities (hashing, git, etc.)
└── DESIGN.md                # This file
```

---

## Scanner Specifications

### Python Scanner

**Discovers:**
| Item | Pattern | Example |
|------|---------|---------|
| Classes | `^class (\w+)(\(.*\))?:` | `class UserService:` |
| Functions | `^(async )?def (\w+)\(` | `async def create_user(` |
| FastAPI routes | `@router\.(get\|post\|put\|patch\|delete)\("([^"]+)"` | `@router.post("/users")` |
| SQLAlchemy models | `__tablename__ = ["'](\w+)["']` | `__tablename__ = "users"` |
| Pydantic schemas | `class (\w+)\(BaseModel\)` | `class UserCreate(BaseModel)` |
| Imports | `^from ([\w.]+) import\|^import ([\w.]+)` | `from fastapi import Router` |
| Decorators | `^@(\w+)` | `@function_tool` |

**Categorization by path:**
```python
PYTHON_CATEGORIES = {
    "*/routers/*.py": "router",
    "*/services/*.py": "service",
    "*/schemas/*.py": "schema",
    "*/models/*.py": "model",
    "*/tests/*.py": "test",
    "*/auth/*.py": "auth",
}
```

### TypeScript/React Scanner

**Discovers:**
| Item | Pattern | Example |
|------|---------|---------|
| Components | `export (default )?(function\|const) (\w+)` | `export default function Chat()` |
| Hooks | `export (function\|const) use(\w+)` | `export function useAgents()` |
| Types/Interfaces | `export (type\|interface) (\w+)` | `export interface User {` |
| Imports | `import .+ from ["']([^"']+)["']` | `import { useState } from 'react'` |
| API calls | `fetch\(["']([^"']+)["']\|axios\.(get\|post)` | `fetch('/api/users')` |

**Categorization by path:**
```typescript
TS_CATEGORIES = {
    "*/pages/*.tsx": "page",
    "*/components/*.tsx": "component",
    "*/components/**/*.tsx": "component",
    "*/hooks/*.ts": "hook",
    "*/api/*.ts": "api-client",
    "*/types/*.ts": "types",
}
```

### SQL Scanner

**Discovers:**
| Item | Pattern | Example |
|------|---------|---------|
| Tables | `CREATE TABLE (IF NOT EXISTS )?["']?(\w+)["']?` | `CREATE TABLE users` |
| Columns | `(\w+)\s+(VARCHAR\|INT\|TEXT\|...)` | `email VARCHAR(255)` |
| Foreign keys | `REFERENCES (\w+)\((\w+)\)` | `REFERENCES users(id)` |
| Indexes | `CREATE INDEX (\w+) ON (\w+)` | `CREATE INDEX idx_email ON users` |

### Docker Scanner

**Discovers:**
| Item | Source | Example |
|------|--------|---------|
| Services | `docker-compose.yaml` services section | `api`, `db`, `frontend` |
| Ports | `ports:` mapping | `8000:8000` |
| Volumes | `volumes:` mapping | `./data:/var/lib/postgresql/data` |
| Networks | `networks:` section | `app-network` |
| Environment | `environment:` or `env_file:` | `DATABASE_URL` |

---

## Output Schema (JSON)

```json
{
  "meta": {
    "generated_at": "2025-01-17T12:49:00Z",
    "tool_version": "1.0.0",
    "git": {
      "commit": "fb4d17d",
      "branch": "develop",
      "dirty": false
    },
    "config": {
      "root": "/home/user/project",
      "exclude": ["node_modules", "__pycache__", ".git"]
    }
  },

  "summary": {
    "total_files": 245,
    "total_lines": 71000,
    "by_language": {
      "python": { "files": 89, "lines": 29000 },
      "typescript": { "files": 45, "lines": 17000 },
      "sql": { "files": 12, "lines": 800 }
    },
    "by_category": {
      "pages": 18,
      "components": 19,
      "services": 13,
      "models": 10,
      "routers": 10,
      "schemas": 10
    }
  },

  "files": [
    {
      "path": "src/api/services/chat_service.py",
      "language": "python",
      "category": "service",
      "size_bytes": 14163,
      "lines": 420,
      "hash": "sha256:abc123...",
      "last_modified": "2025-01-15T23:37:00Z",
      "exports": {
        "classes": ["ChatService"],
        "functions": ["chat", "stream_chat", "get_history"]
      },
      "imports": {
        "internal": ["agent_service", "mcp_service"],
        "external": ["fastapi", "openai_agents"]
      }
    }
  ],

  "api_endpoints": [
    {
      "method": "POST",
      "path": "/api/v1/chat/stream",
      "handler": "stream_chat",
      "file": "src/api/routers/chat.py",
      "line": 45
    }
  ],

  "database": {
    "tables": [
      {
        "name": "users",
        "file": "src/db/models/user.py",
        "columns": ["id", "email", "password_hash", "created_at"],
        "relationships": {
          "has_many": ["agents", "teams"],
          "belongs_to": []
        }
      }
    ]
  },

  "docker": {
    "services": [
      {
        "name": "api",
        "image": "python:3.11",
        "ports": ["8000:8000"],
        "depends_on": ["db", "redis"]
      }
    ]
  },

  "domains": {
    "auth": {
      "files": ["src/auth/dependencies.py", "src/auth/jwt.py"],
      "endpoints": ["/auth/login", "/auth/register", "/auth/logout"],
      "models": ["User"]
    },
    "chat": {
      "files": ["src/api/routers/chat.py", "src/api/services/chat_service.py"],
      "endpoints": ["/chat/stream", "/chat/history"],
      "models": ["ChatSession", "ChatMessage"]
    }
  }
}
```

---

## Config File (.codebase-index.yaml)

```yaml
# .codebase-index.yaml
version: 1

# Root directory (default: current directory)
root: .

# Files/directories to exclude
exclude:
  - node_modules
  - __pycache__
  - .git
  - .venv
  - "*.pyc"
  - "*.log"
  - dist
  - build

# Language detection overrides
languages:
  python:
    extensions: [".py"]
    exclude: ["*_test.py", "conftest.py"]  # optional
  typescript:
    extensions: [".ts", ".tsx"]
    exclude: ["*.d.ts", "*.test.ts"]
  sql:
    extensions: [".sql"]
    paths: ["migrations/", "sql/"]

# Category mappings (override defaults)
categories:
  python:
    "src/api/routers/*.py": router
    "src/api/services/*.py": service
    "src/api/schemas/*.py": schema
    "src/db/models/*.py": model
    "src/auth/*.py": auth
    "tests/**/*.py": test
  typescript:
    "src/frontend/src/pages/*.tsx": page
    "src/frontend/src/components/**/*.tsx": component
    "src/frontend/src/hooks/*.ts": hook

# Domain groupings (for the "domains" section)
domains:
  auth:
    paths: ["src/auth/", "src/api/routers/auth.py"]
    patterns: ["*auth*", "*login*", "*register*"]
  chat:
    paths: ["src/api/routers/chat.py", "src/api/services/chat_service.py"]
    patterns: ["*chat*", "*message*", "*session*"]
  agents:
    paths: ["src/api/routers/agents.py", "src/openai_agents/"]
    patterns: ["*agent*"]

# Output options
output:
  format: json  # json, yaml, sqlite
  include_hash: true
  include_deps: true
  include_git: true
  pretty: true
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] CLI argument parsing
- [ ] Config file loading
- [ ] File discovery (walk directory, apply excludes)
- [ ] Basic metadata extraction (size, lines, hash)
- [ ] JSON output

### Phase 2: Python Scanner
- [ ] Class extraction
- [ ] Function extraction
- [ ] FastAPI route extraction
- [ ] SQLAlchemy model extraction
- [ ] Import analysis
- [ ] Categorization

### Phase 3: TypeScript Scanner
- [ ] Component extraction
- [ ] Hook extraction
- [ ] Import analysis
- [ ] Categorization

### Phase 4: SQL & Docker Scanners
- [ ] SQL table/column extraction
- [ ] Docker service extraction

### Phase 5: Advanced Features
- [ ] Dependency graph generation
- [ ] Domain auto-grouping
- [ ] Validation mode
- [ ] Diff mode
- [ ] SQLite output

---

## Questions to Resolve

1. **Implementation language**: Python (better parsing) or Bash (simpler, portable)?
   - Recommendation: Python for scanners, thin bash wrapper for CLI

2. **AST vs Regex**: Use Python's `ast` module for accurate parsing, or regex for speed?
   - Recommendation: Regex first (faster, good enough for 90% of cases), AST optional

3. **Incremental scanning**: Should we support scanning only changed files?
   - Recommendation: V2 feature, use git diff + cached index

4. **Output size**: Full file list can be huge. Summarize by default, full with flag?
   - Recommendation: Always include full, let users filter with jq

---

## Testing Strategy

Use this repository (Multi-Agent-System-MCP-Server) as the test case:
- Known file counts to validate against
- Complex enough to stress-test scanners
- Has Python, TypeScript, SQL, Docker

Expected output validation:
- 18 pages (not 17)
- 19 components (not 24)
- 13 services (not 11)
- ~80 API endpoints (not 48)
- Marketplace module detected
- Audit module detected
