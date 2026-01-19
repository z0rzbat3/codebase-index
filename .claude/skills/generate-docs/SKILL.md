---
name: generate-docs
description: Generate and maintain documentation using 1:1 source-to-doc mirroring. Each source file gets its own doc file. Supports full generation, incremental updates, validation, and review. Triggers on: generate docs, create documentation, document codebase, update docs, check docs, stale docs, review docs, validate docs.
allowed-tools: Bash(codebase-index:*), Bash(git:*), Bash(jq:*), Bash(md5sum:*), Bash(date:*), Bash(wc:*), Bash(find:*), Bash(mkdir:*), Read, Glob, Grep, Write, Task
user-invocable: true
subagent: doc-generator
---

# Generate & Maintain Documentation

Generate documentation using **1:1 mirror strategy**: each source file gets its own doc file.

## Subagent (MANDATORY)

**Definition:** `.claude/agents/doc-generator.md`

**⚠️ ALL documentation operations MUST use `doc-generator` subagent:**
- Generate → doc-generator
- Review → doc-generator
- Fix → doc-generator
- Incremental → doc-generator

**Do NOT use:** ai-dev, documentation-knowledge, Explore, or any other subagent for doc work.

The skill spawns `doc-generator` clones in parallel. Each clone handles one directory assignment. See the subagent definition for its protocol and scope.

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
    "forbidden_terms": [],
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

### Step 3: Generate Docs (Parallel Clones)

**Spawn doc-generator clones in parallel - one per mapping:**

```python
# Orchestrator builds inventory from config
inventory = []
for mapping in config["mappings"]:
    inventory.append({
        "source_dir": mapping["source"],
        "docs_dir": mapping["docs"],
        "template": mapping["template"],
        "extensions": mapping["extensions"]
    })

# Spawn ALL clones in ONE message (parallel)
for item in inventory:
    Task(
        subagent_type="doc-generator",
        prompt=f"""
ASSIGNMENT:
  source_dir: {item["source_dir"]}
  docs_dir: {item["docs_dir"]}
  template: {item["template"]}
  extensions: {item["extensions"]}
  forbidden_terms: {config["validation"]["forbidden_terms"]}
  max_lines: {config["options"]["max_lines_per_doc"]}

Generate docs for this directory following the doc-generator protocol.
""",
        description=f"Generate {item['docs_dir']} docs"
    )
```

**Key: All Task calls in SINGLE message = parallel execution**

Each clone:
- Reads its assigned source directory
- Writes docs to its assigned docs directory
- Creates README.md index
- Reports completion

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

Validate docs against actual source code.

### ⚠️ MANDATORY: 100% Coverage

**Review ALL docs. No sampling. No exceptions.**

```
1. List ALL .md files in docs_root recursively
2. For EACH file, run ALL validation checks
3. Report issues for EVERY file
4. With --fix: Fix ALL issues found
```

**Do NOT:**
- Sample "a few files" for validation
- Skip files because they're "not in mappings"
- Ignore legacy/architecture docs

### Validation Scope

**Validation rules apply to ALL files in `docs_root`:**
- Mirror-mapped docs (from config mappings)
- Legacy docs (architecture/, development/, guides/)
- Contributing docs
- ALL .md files without exception

If a doc has forbidden terms → fix it or delete it
If a doc has invalid symbols → regenerate it
No file gets a pass.

### Checks

1. **Symbol Accuracy** (MOST IMPORTANT)
   - Read source file and doc file side-by-side
   - Verify documented classes/functions actually exist
   - Check if method signatures match
   - Detect renamed/removed symbols documented as if they exist

2. **Reference Validation**
   - All `file:line` references are within file bounds
   - All linked files actually exist

3. **Content Drift**
   - Compare doc descriptions to source docstrings
   - Flag docs that describe different behavior than code
   - Detect outdated examples

4. **Forbidden Terms** (applies to ALL docs)
   - Check for terms in `forbidden_terms` config array
   - Applies to ALL .md files in docs_root, not just mapped docs
   - If found: delete the term, rewrite the section, or delete the file
   - No exceptions - legacy docs get fixed too

5. **Completeness**
   - All required sections present
   - No empty sections

### Review Process

**Do NOT just grep for banned words.** Actually compare doc to source:

```
For each doc file:
  1. Read the doc file
  2. Read the corresponding source file
  3. Extract symbols from source (classes, functions, methods)
  4. Extract documented symbols from doc
  5. Compare: Are documented symbols in source? Are descriptions accurate?
  6. Report discrepancies
```

### Review Output

```
Documentation Review Report
===========================

docs/api/routers/agents.md
  ✅ All symbols verified in source
  ✅ Line references valid
  ⚠️  Missing section: Usage Examples

docs/db/models/user.md
  ❌ Symbol mismatch: Doc says `get_by_email()` but source has `find_by_email()`
  ❌ Invalid reference: src/db/models/user.py:250 (file has 180 lines)
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

## Execution Strategy

**Pattern: Orchestrator + Parallel Subagent Clones**

```
Orchestrator (you)
    |
    ├── Read .doc-config.json
    ├── Build inventory/checklist from mappings
    ├── Spawn N doc-generator clones in parallel
    |       |
    |       ├── Clone 1: src/api/routers → docs/api/routers
    |       ├── Clone 2: src/api/services → docs/api/services
    |       ├── Clone 3: src/db/models → docs/db/models
    |       └── Clone N: ...
    |
    └── Collect results, report summary
```

### Subagent: `doc-generator`

Each clone is a `doc-generator` subagent (defined in `.claude/agents/doc-generator.md`) with:
- **Scope**: One directory assignment only
- **Permissions**: Read source, Write docs (in assigned dir only)
- **Output**: Completion report with file count

### Spawning Pattern

```
# Spawn ALL clones in a SINGLE message (parallel execution)
# Each clone gets one assignment from the inventory

Task tool call 1:
  subagent_type: "doc-generator"
  prompt: "ASSIGNMENT: source_dir=src/api/routers, docs_dir=docs/api/routers, template=api-endpoint..."

Task tool call 2:
  subagent_type: "doc-generator"
  prompt: "ASSIGNMENT: source_dir=src/api/services, docs_dir=docs/api/services, template=module..."

Task tool call 3:
  subagent_type: "doc-generator"
  prompt: "ASSIGNMENT: source_dir=src/db/models, docs_dir=docs/db/models, template=db-model..."

# All 3 run in parallel
```

### Why This Works

1. **True parallelism**: Multiple clones work simultaneously
2. **Clear scope**: Each clone knows exactly its assignment
3. **Isolated writes**: No conflicts, each writes to different dir
4. **Scalable**: 5 dirs = 5 clones, 20 dirs = 20 clones

### Permission Handling

**Current behavior:** Each clone may prompt for write permission.

**Ideal behavior:** Pre-approve docs/ directory writes at skill invocation.

**Workaround:** If permission prompts are disruptive:
- Approve "Write to docs/" on first prompt
- Session should cache for subsequent writes to same directory tree
- Or: Run with `--dangerously-skip-permissions` if you trust the operation

### Inventory Format

Before spawning, orchestrator builds checklist:

```
INVENTORY (from .doc-config.json):
[ ] src/api/routers → docs/api/routers (api-endpoint, .py)
[ ] src/api/services → docs/api/services (module, .py)
[ ] src/db/models → docs/db/models (db-model, .py)
[ ] src/frontend/pages → docs/frontend/pages (frontend-page, .tsx)
...
```

Then spawn one clone per checklist item, all in parallel.

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
