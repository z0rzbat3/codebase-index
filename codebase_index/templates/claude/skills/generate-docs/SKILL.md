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
| **Init** | `/generate-docs --init` | Auto-generate config from project structure |
| **Full** | `/generate-docs` | Generate all docs |
| **Incremental** | `/generate-docs --incremental` | Only changed files |
| **Verify** | `/generate-docs --verify` | Check staleness |
| **Review** | `/generate-docs --review` | Validate accuracy |

---

## Prerequisite: Generate index.json

**Before any mode**, ensure `index.json` exists. If not, generate it:

### Step 1: Analyze Project Structure

Review the project to determine appropriate exclusions:

```bash
# Check what directories exist
ls -la

# Look for common directories to exclude
# - node_modules, .venv, __pycache__, dist, build
# - .git, .archive, logs, backups
# - vendor, third-party, versions
```

### Step 2: Generate Index with Exclusions

```bash
codebase-index . -o index.json --build-embeddings \
  --exclude-dirs node_modules .venv __pycache__ dist build .git .archive logs backups vendor third-party
```

**Adjust exclusions based on project:**
- Python: add `.pytest_cache`, `*.egg-info`
- Node: add `coverage`, `.next`, `.nuxt`
- Monorepo: exclude non-relevant packages

### Step 3: Verify Index Quality

```bash
# Check summary
codebase-index --load index.json --summary

# Verify file count is reasonable (not scanning junk)
codebase-index --load index.json --path summary.total_files
```

**If too many files**: Add more exclusions and regenerate.

### Why This Matters

The index provides:
- **File categorization**: routes, models, schemas, services
- **Symbol extraction**: functions, classes, methods with signatures
- **Call graph**: what calls what (for impact analysis)
- **Semantic embeddings**: for intelligent doc generation

Without an index, `/generate-docs --init` would have to manually scan with Glob, missing the rich metadata codebase-index provides.

---

## Mode: Init (`--init`)

Auto-generate `.doc-config.json` using a hybrid approach: Glob/Grep/Read for directory scanning, enriched by `index.json` metadata.

### What It Does

1. **Scans project** with Glob to find source directories
2. **Reads files** with Grep/Read to detect patterns (imports, decorators)
3. **Enriches with index.json** for accurate categorization (API endpoints, DB models)
4. **Creates `.doc-config.json`** with mappings
5. **Creates `docs/` directory structure** (optional with `--generate`)

### Two-Layer Detection

**Layer 1: Directory Scanning (Glob/Grep/Read)**

| Directory Pattern | Template | Detection |
|-------------------|----------|-----------|
| `*/routers/*`, `*/routes/*`, `*/endpoints/*` | `api-endpoint` | Directory name |
| `*/models/*` | `db-model` | Directory name + ORM imports |
| `*/schemas/*`, `*/serializers/*` | `module` | Directory name |
| `*/services/*`, `*/utils/*`, `*/helpers/*` | `module` | Directory name |
| `*/pages/*`, `*/views/*` | `frontend-page` | Directory name + React/Vue imports |
| `*/components/*`, `*/hooks/*` | `module` | Directory name |

**Layer 2: Index Enrichment (codebase-index)**

When `index.json` exists, use it to confirm/override:

| Index Data | Confirms | Override |
|------------|----------|----------|
| `api_endpoints[].file` | Files with actual routes | Use `api-endpoint` even if not in routers/ |
| `database.tables[].file` | Files with actual models | Use `db-model` even if not in models/ |
| `summary.by_category` | File categorization | Accurate counts per directory |
| `symbol_index` | Functions, classes | Better doc content generation |

### Usage

```bash
# Basic init - scans project, creates config
/generate-docs --init

# Init and immediately generate docs
/generate-docs --init --generate
```

### Init Algorithm (Hybrid)

```bash
# Step 1: Find source directories with Glob
find src -type d -name "*.py" -o -name "*.ts" -o -name "*.tsx" | ...

# Step 2: For each directory, detect template
# - Check directory name patterns
# - Grep for imports (SQLAlchemy, FastAPI, React)
grep -l "from fastapi" src/api/routers/*.py

# Step 3: If index.json exists, enrich with metadata
if [ -f index.json ]; then
  # Get confirmed API files
  codebase-index --load index.json --path api_endpoints

  # Get confirmed DB model files
  codebase-index --load index.json --path database.tables

  # Get file counts per category
  codebase-index --load index.json --path summary.by_category
fi

# Step 4: Merge and create config
```

**Pseudocode:**

```python
def init_config(source_root="src"):
    mappings = []

    # Layer 1: Glob/Grep scanning
    for dir_path in find_source_directories(source_root):
        files = glob(f"{dir_path}/*.py") + glob(f"{dir_path}/*.ts*")

        # Detect template from directory name
        template = detect_template_from_dirname(dir_path)

        # Refine with content inspection
        if template == "module" and has_route_decorators(files):
            template = "api-endpoint"
        if template == "module" and has_orm_base(files):
            template = "db-model"

        mappings.append({"source": dir_path, "template": template, ...})

    # Layer 2: Index enrichment (if available)
    if path_exists("index.json"):
        index = load_json("index.json")

        # Override with confirmed API files
        api_files = {ep["file"] for ep in index.get("api_endpoints", [])}
        for m in mappings:
            if any(f in api_files for f in files_in(m["source"])):
                m["template"] = "api-endpoint"

        # Override with confirmed DB models
        model_files = {t["file"] for t in index.get("database", {}).get("tables", [])}
        for m in mappings:
            if any(f in model_files for f in files_in(m["source"])):
                m["template"] = "db-model"

    return create_config(mappings)

def detect_template_from_dirname(dir_path):
    name = dir_path.split("/")[-1]

    if name in ["routers", "routes", "endpoints", "api"]:
        return "api-endpoint"
    if name == "models":
        return "db-model"  # Will verify with content/index
    if name in ["pages", "views"]:
        return "frontend-page"
    return "module"

def has_route_decorators(files):
    # Grep for @router, @app.get, @api_view, etc.
    return grep_any(files, r"@(router|app)\.(get|post|put|delete)")

def has_orm_base(files):
    # Grep for SQLAlchemy, Django, Pydantic base classes
    return grep_any(files, r"class \w+\((Base|Model|BaseModel)\)")
```

### Example Output

```
$ /generate-docs --init

Scanning project structure...

Layer 1 - Directory detection:
  ✓ src/api/routers      (5 .py files)  → api-endpoint (dirname)
  ✓ src/api/services     (3 .py files)  → module
  ? src/core/handlers    (4 .py files)  → module (has @router?)

Layer 2 - Index enrichment:
  Reading index.json...
  ✓ src/core/handlers has 8 endpoints → api-endpoint (upgraded)
  ✓ src/db/models confirmed 6 tables  → db-model

Final mappings:
  ✓ src/api/routers      → api-endpoint
  ✓ src/api/services     → module
  ✓ src/api/schemas      → module
  ✓ src/core/handlers    → api-endpoint (from index)
  ✓ src/db/models        → db-model
  ✓ src/db/repositories  → module
  ✓ src/frontend/pages   → frontend-page
  ✓ src/frontend/hooks   → module

Created:
  ✓ .doc-config.json (8 mappings)

Next steps:
  1. Review .doc-config.json and adjust if needed
  2. Add forbidden_terms for your project
  3. Run: /generate-docs --generate
```

### Generated Config

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

### Flags

| Flag | Description |
|------|-------------|
| `--init` | Run init mode (requires index.json) |
| `--generate` | Run full generation after init |
| `--force` | Overwrite existing `.doc-config.json` |

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
# First time setup (in order)
codebase-index . -o index.json --build-embeddings --exclude-dirs node_modules .venv __pycache__
/generate-docs --init                    # Create .doc-config.json (uses index.json)
/generate-docs --generate                # Generate all docs

# Or combined:
/generate-docs --init --generate         # Init + generate docs immediately

# Incremental (after code changes)
/generate-docs --incremental             # Only update changed files

# Verification
/generate-docs --verify                  # Check what's stale (no changes)

# Review (validation)
/generate-docs --review                  # Validate all docs (100% coverage)
/generate-docs --review --fix            # Fix all issues found

# Specific directory
/generate-docs src/api/routers           # Generate docs for specific dir
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
