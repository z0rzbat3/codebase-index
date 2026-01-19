---
name: generate-docs
description: Generate and maintain documentation using 1:1 source-to-doc mirroring. Each source file gets its own doc file. Supports full generation, incremental updates, validation, and review. Triggers on: generate docs, create documentation, document codebase, update docs, check docs, stale docs, review docs, validate docs.
allowed-tools: Bash(codebase-index:*), Bash(git:*), Bash(jq:*), Bash(md5sum:*), Bash(date:*), Bash(wc:*), Bash(find:*), Bash(mkdir:*), Read, Glob, Grep, Write, Task
user-invocable: true
---

# Generate & Maintain Documentation

Generate documentation using **1:1 mirror strategy**: each source file gets its own doc file.

## Strategy: Mirror

```
src/                          →    docs/
├── api/                           ├── api/
│   ├── routers/                   │   ├── routers/
│   │   ├── agents.py              │   │   ├── agents.md
│   │   ├── chat.py                │   │   ├── chat.md
│   │   └── users.py               │   │   └── users.md
│   └── services/                  │   ├── services/
│       └── agent_service.py       │   │   └── agent_service.md
│                                  │   └── README.md  ← Index
├── db/                            ├── db/
│   └── models/                    │   └── models/
│       ├── user.py                │       ├── user.md
│       └── session.py             │       ├── session.md
│                                  │       └── README.md
└── frontend/                      └── frontend/
    └── src/                           └── src/
        └── pages/                         └── pages/
            ├── Dashboard.tsx                  ├── Dashboard.md
            └── Login.tsx                      ├── Login.md
                                               └── README.md
```

**Benefits:**
- Small files (~50-200 lines each)
- Change one source → update one doc
- Easy to review, easy to find
- Meaningful git diffs

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Full** | `/generate-docs` | Generate all docs |
| **Incremental** | `/generate-docs --incremental` | Only changed files |
| **Verify** | `/generate-docs --verify` | Check staleness |
| **Review** | `/generate-docs --review` | Validate accuracy |

---

## Configuration: `.doc-config.json`

```json
{
  "version": "2.0",
  "strategy": "mirror",
  "source_root": "src",
  "docs_root": "docs",
  "index_files": true,

  "mappings": [
    {
      "source": "src/api/routers",
      "docs": "docs/api/routers",
      "template": "api-endpoint",
      "extensions": [".py"]
    },
    {
      "source": "src/db/models",
      "docs": "docs/db/models",
      "template": "db-model",
      "extensions": [".py"]
    },
    {
      "source": "src/frontend/src/pages",
      "docs": "docs/frontend/pages",
      "template": "frontend-page",
      "extensions": [".tsx", ".ts"]
    },
    {
      "source": "src/openai_agents",
      "docs": "docs/agents",
      "template": "module",
      "extensions": [".py"]
    }
  ],

  "exclude": [
    "**/__pycache__/**",
    "**/__init__.py",
    "**/node_modules/**",
    "**/*.test.*",
    "**/*.spec.*"
  ],

  "validation": {
    "check_references": true,
    "check_symbols": true,
    "forbidden_terms": ["chainlit", "deprecated"],
    "required_sections": ["Overview"]
  }
}
```

---

## Templates

Templates define the structure for each doc type. Located in `.doc-templates/`.

### Template: `api-endpoint.md`

```markdown
# {{filename}}

> Auto-generated from `{{source_path}}`

## Overview

{{description}}

## Endpoints

{{#each endpoints}}
### `{{method}} {{path}}`

{{description}}

**Auth:** {{auth_required}}

**Request:**
{{#if request_body}}
```json
{{request_body}}
```
{{/if}}

**Response:**
```json
{{response}}
```

**Example:**
```bash
curl -X {{method}} http://localhost:8000{{path}}
```
{{/each}}

## Dependencies

{{dependencies}}

---
*Generated: {{timestamp}} | Source: {{source_path}}:{{line_count}} lines*
```

### Template: `db-model.md`

```markdown
# {{class_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{docstring}}

## Table: `{{table_name}}`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
{{#each columns}}
| `{{name}}` | {{type}} | {{constraints}} | {{description}} |
{{/each}}

## Relationships

{{#each relationships}}
- **{{name}}**: {{type}} → `{{target}}`
{{/each}}

## Indexes

{{#each indexes}}
- `{{name}}`: {{columns}}
{{/each}}

---
*Generated: {{timestamp}} | Source: {{source_path}}*
```

### Template: `frontend-page.md`

```markdown
# {{component_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{description}}

## Route

- **Path:** `{{route}}`
- **Auth Required:** {{auth_required}}

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
{{#each props}}
| `{{name}}` | `{{type}}` | {{required}} | {{description}} |
{{/each}}

## Hooks Used

{{#each hooks}}
- `{{name}}`: {{description}}
{{/each}}

## State

{{#each state}}
- `{{name}}`: `{{type}}`
{{/each}}

---
*Generated: {{timestamp}} | Source: {{source_path}}*
```

### Template: `module.md`

```markdown
# {{module_name}}

> Auto-generated from `{{source_path}}`

## Overview

{{docstring}}

## Classes

{{#each classes}}
### `{{name}}`

{{docstring}}

#### Methods

{{#each methods}}
- `{{signature}}`: {{description}}
{{/each}}
{{/each}}

## Functions

{{#each functions}}
### `{{name}}({{params}})`

{{docstring}}

**Returns:** `{{return_type}}`
{{/each}}

## Usage

```python
{{usage_example}}
```

---
*Generated: {{timestamp}} | Source: {{source_path}}*
```

### Template: `index.md` (README.md for directories)

```markdown
# {{directory_name}}

> Index for `{{source_directory}}`

## Contents

{{#each files}}
- [{{name}}]({{link}}) - {{description}}
{{/each}}

## Overview

{{directory_description}}

## Quick Reference

| File | Type | Lines | Last Updated |
|------|------|-------|--------------|
{{#each files}}
| [{{name}}]({{link}}) | {{type}} | {{lines}} | {{updated}} |
{{/each}}
```

---

## Execution Steps

### Step 1: Load Configuration

```bash
# Check for config
if [ ! -f .doc-config.json ]; then
  echo "No .doc-config.json found. Creating default..."
  # Create default config
fi

# Load config
CONFIG=$(cat .doc-config.json)
```

### Step 2: Query Index for Files

```bash
# Get all source files from index
codebase-index --load index.json --keys file_index

# For each mapping, get matching files
codebase-index --load index.json --path "file_index" | \
  jq -r '.[] | select(.path | startswith("src/api/routers"))'
```

### Step 3: Generate Docs (Parallel by Directory)

For each mapping in config:

1. **List source files**
```bash
find src/api/routers -name "*.py" -type f | grep -v __pycache__
```

2. **Create output directory**
```bash
mkdir -p docs/api/routers
```

3. **Spawn subagent for each file** (batch by directory for efficiency)

```
Use Task tool with:
  subagent_type: "documentation-knowledge"
  prompt: |
    Document this single file using the api-endpoint template.

    Source: src/api/routers/agents.py
    Output: docs/api/routers/agents.md
    Template: api-endpoint

    Read the source file, extract:
    - All endpoints (method, path, auth, request/response)
    - Dependencies
    - Any docstrings

    Generate markdown following the template structure.
    Keep it concise: aim for 50-150 lines.
```

4. **Generate index file**
```
After all files in directory are done:
  Generate docs/api/routers/README.md
  List all documented files with descriptions
```

### Step 4: Update Manifest

```json
{
  "version": "2.0",
  "strategy": "mirror",
  "last_updated": "2024-01-19T20:00:00Z",
  "files": {
    "src/api/routers/agents.py": {
      "doc_path": "docs/api/routers/agents.md",
      "source_hash": "abc123",
      "doc_hash": "def456",
      "last_updated": "2024-01-19T20:00:00Z",
      "line_count": 85
    }
  },
  "indexes": {
    "docs/api/routers/README.md": {
      "source_dir": "src/api/routers",
      "last_updated": "2024-01-19T20:00:00Z"
    }
  }
}
```

---

## Mode: Incremental (`--incremental`)

Only regenerate docs for changed source files.

```bash
# 1. Get changed files since last generation
CHANGED=$(find src -newer .doc-manifest.json -name "*.py" -o -name "*.ts" -o -name "*.tsx")

# 2. For each changed file, check if it has a mapping
for file in $CHANGED; do
  # Find matching mapping
  # Regenerate only that doc
done

# 3. Update affected index files
```

---

## Mode: Review (`--review`)

Validate generated docs against codebase.

### Checks

1. **Reference Validation**
   - All `file:line` references exist
   - All function/class names exist in index

2. **Symbol Validation**
   - Documented symbols match actual code
   - No phantom/removed symbols

3. **Term Validation**
   - No forbidden terms (from config)
   - No references to removed technologies

4. **Completeness**
   - All required sections present
   - No empty sections

### Review Output

```
Documentation Review Report
===========================

docs/api/routers/agents.md
  ✅ All references valid
  ✅ All symbols found
  ✅ No forbidden terms
  ⚠️  Missing section: Usage Examples

docs/db/models/user.md
  ❌ Invalid reference: src/db/models/user.py:250 (file has 180 lines)
  ❌ Forbidden term found: "chainlit" on line 45
  ✅ All required sections present

Summary: 15 files reviewed, 2 issues found
```

### Review Commands

```bash
# Full review
/generate-docs --review

# Review specific directory
/generate-docs --review docs/api/

# Review and auto-fix (regenerate invalid docs)
/generate-docs --review --fix
```

---

## Parallel Execution Strategy

Divide work by directory to avoid conflicts:

```
Batch 1: src/api/routers/*.py    → docs/api/routers/
Batch 2: src/api/services/*.py   → docs/api/services/
Batch 3: src/db/models/*.py      → docs/db/models/
Batch 4: src/frontend/pages/*.tsx → docs/frontend/pages/
Batch 5: src/openai_agents/*.py  → docs/agents/
```

Each batch runs in parallel as a separate subagent. Within each batch, files are processed sequentially to maintain consistency.

---

## Quick Reference

```bash
# Setup
./scripts/setup-doc-maintenance.sh

# Full generation
/generate-docs

# Check what's stale
/generate-docs --verify

# Update only changed
/generate-docs --incremental

# Validate accuracy
/generate-docs --review

# Specific directory
/generate-docs src/api/routers

# Review and fix
/generate-docs --review --fix
```

---

## File Size Guidelines

| Doc Type | Target Lines | Max Lines |
|----------|--------------|-----------|
| API endpoint | 50-150 | 200 |
| DB model | 30-80 | 120 |
| Frontend page | 40-100 | 150 |
| Module | 50-150 | 200 |
| Index (README) | 20-50 | 80 |

If a doc exceeds max lines, consider splitting the source file.

---

## Migration from v1 (Monolithic)

If you have existing monolithic docs:

1. **Archive old docs**
```bash
mv docs/api/API_REFERENCE.md .archive/docs/
```

2. **Update config to v2**
```bash
# Change strategy to "mirror"
jq '.strategy = "mirror" | .version = "2.0"' .doc-config.json > tmp && mv tmp .doc-config.json
```

3. **Run full generation**
```bash
/generate-docs
```

4. **Review and validate**
```bash
/generate-docs --review
```
