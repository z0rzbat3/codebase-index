---
name: generate-docs
description: Generate and maintain documentation using parallel subagents coordinated via codebase-index. Supports full generation, incremental updates, and staleness verification. Triggers on: generate docs, create documentation, document codebase, update docs, check docs, stale docs, incremental docs, verify documentation.
allowed-tools: Bash(codebase-index:*), Bash(git:*), Bash(jq:*), Bash(md5sum:*), Bash(date:*), Bash(wc:*), Bash(cat:*), Read, Glob, Grep, Write, Task
user-invocable: true
---

# Generate & Maintain Documentation

Generate and maintain documentation using parallel subagents coordinated via `codebase-index`.

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Full** | `/generate-docs` | Regenerate all documentation |
| **Incremental** | `/generate-docs --incremental` | Only document changed files |
| **Verify** | `/generate-docs --verify` | Check what's stale (no changes) |
| **Diff** | `/generate-docs --diff` | Preview what would be updated |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        .doc-manifest.json                        │
│  Tracks: file hashes, doc locations, last updated timestamps    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  --verify     │   │  --incremental  │   │  (full)         │
│  Compare      │   │  Regenerate     │   │  Regenerate     │
│  hashes only  │   │  stale only     │   │  everything     │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

## Prerequisites

```bash
# Install codebase-index if needed
which codebase-index || pip install codebase-index[semantic]

# Build/update index
codebase-index . -o index.json --build-embeddings
```

## The Manifest File

`.doc-manifest.json` tracks documentation state:

```json
{
  "version": "1.0",
  "last_full_generation": "2024-01-19T20:00:00Z",
  "index_hash": "abc123def456",
  "source_to_doc": {
    "src/api/routers/": {
      "doc_path": "docs/api/API_REFERENCE.md",
      "source_hash": "hash_of_all_files_in_dir",
      "doc_hash": "hash_of_generated_doc",
      "last_updated": "2024-01-19T20:00:00Z",
      "line_count": 3483
    },
    "src/db/models/": {
      "doc_path": "docs/architecture/DATABASE_SCHEMA.md",
      "source_hash": "...",
      "doc_hash": "...",
      "last_updated": "...",
      "line_count": 816
    }
  }
}
```

---

## Mode: Full Generation

**When:** First run, major refactors, or forced refresh.

```
/generate-docs
/generate-docs src/api src/db src/auth
```

### Steps

1. **Query index for structure**
```bash
codebase-index --load index.json --summary
codebase-index --load index.json --keys file_index
```

2. **Identify non-overlapping documentation areas**

Good divisions:
- `src/api/routers/` → `docs/api/API_REFERENCE.md`
- `src/db/models/` → `docs/architecture/DATABASE_SCHEMA.md`
- `src/auth/` → `docs/architecture/AUTHENTICATION.md`
- `src/frontend/src/pages/` → `docs/architecture/FRONTEND.md`
- `src/core/` → `docs/architecture/CORE.md`

3. **Spawn parallel documentation-knowledge subagents**

For each area, use Task tool:
```
subagent_type: "documentation-knowledge"
run_in_background: true
prompt: [Include files, output path, scope]
```

4. **Update manifest after completion**

```bash
# Calculate source hash for a directory
find src/api/routers -name "*.py" -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1

# Calculate doc hash
md5sum docs/api/API_REFERENCE.md | cut -d' ' -f1
```

5. **Write updated .doc-manifest.json**

---

## Mode: Verify (--verify)

**When:** Pre-commit check, CI validation, checking doc health.

```
/generate-docs --verify
```

### Steps

1. **Load manifest**
```bash
cat .doc-manifest.json
```

2. **For each source_to_doc entry, compare current hash to stored hash**

```bash
# Current source hash
CURRENT=$(find src/api/routers -name "*.py" -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1)

# Stored hash from manifest
STORED=$(jq -r '.source_to_doc["src/api/routers/"].source_hash' .doc-manifest.json)

# Compare
if [ "$CURRENT" != "$STORED" ]; then
  echo "STALE: src/api/routers/ → docs/api/API_REFERENCE.md"
fi
```

3. **Output staleness report**

```
Documentation Status:
✅ docs/api/API_REFERENCE.md (up to date)
⚠️  docs/architecture/DATABASE_SCHEMA.md (STALE - src/db/models/ changed)
✅ docs/architecture/AUTHENTICATION.md (up to date)
⚠️  docs/architecture/FRONTEND.md (STALE - src/frontend/src/pages/ changed)
❌ docs/architecture/CORE.md (MISSING - src/core/ not documented)

Summary: 2 stale, 1 missing, 2 current
```

4. **Exit with code indicating staleness**
- Exit 0: All docs current
- Exit 1: Some docs stale (useful for CI gates)

---

## Mode: Incremental (--incremental)

**When:** Regular maintenance, post-commit updates.

```
/generate-docs --incremental
```

### Steps

1. **Run verify to identify stale docs**

2. **For each stale entry, regenerate only that doc**

```
# Only spawn subagents for stale areas
If src/db/models/ is stale:
  → Spawn documentation-knowledge for DATABASE_SCHEMA.md only

If src/api/routers/ is current:
  → Skip, don't regenerate
```

3. **Update manifest entries for regenerated docs only**

4. **Report what was updated**

```
Incremental Documentation Update:
  Regenerated: docs/architecture/DATABASE_SCHEMA.md (816 lines)
  Regenerated: docs/architecture/FRONTEND.md (796 lines)
  Skipped: 3 docs (already current)

Total: 2 regenerated, 3 skipped
```

---

## Mode: Diff (--diff)

**When:** Preview before committing to regeneration.

```
/generate-docs --diff
```

### Steps

1. **Run verify to identify stale docs**

2. **For each stale entry, show what would change**

```
Documentation Diff Preview:

src/db/models/ → docs/architecture/DATABASE_SCHEMA.md
  Source changes:
    M src/db/models/user.py (added 2 columns)
    A src/db/models/audit_log.py (new file)
  Expected doc changes:
    + New table: audit_log
    + New columns in user table

src/frontend/src/pages/ → docs/architecture/FRONTEND.md
  Source changes:
    M src/frontend/src/pages/Dashboard.tsx (refactored)
  Expected doc changes:
    ~ Updated Dashboard page documentation

Run '/generate-docs --incremental' to apply these changes.
```

---

## Documentation Mapping Configuration

Create `.doc-config.json` to define source-to-doc mappings:

```json
{
  "mappings": [
    {
      "source": "src/api/routers/",
      "doc": "docs/api/API_REFERENCE.md",
      "type": "api",
      "description": "REST API endpoint documentation"
    },
    {
      "source": "src/db/models/",
      "doc": "docs/architecture/DATABASE_SCHEMA.md",
      "type": "database",
      "description": "Database schema and relationships"
    },
    {
      "source": "src/auth/",
      "doc": "docs/architecture/AUTHENTICATION.md",
      "type": "module",
      "description": "Authentication system"
    },
    {
      "source": "src/frontend/src/pages/",
      "doc": "docs/architecture/FRONTEND.md",
      "type": "frontend",
      "description": "Frontend pages and components"
    },
    {
      "source": "src/openai_agents/",
      "doc": "docs/architecture/AGENT_FRAMEWORK.md",
      "type": "module",
      "description": "Agent framework core"
    }
  ],
  "exclude": [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/node_modules/**",
    "**/.git/**"
  ]
}
```

---

## Helper Scripts

### Calculate Directory Hash

```bash
calc_dir_hash() {
  local dir="$1"
  local ext="${2:-py}"
  find "$dir" -name "*.$ext" -type f -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1
}

# Usage
calc_dir_hash "src/api/routers" "py"
calc_dir_hash "src/frontend/src/pages" "tsx"
```

### Check Single Mapping Staleness

```bash
check_stale() {
  local source="$1"
  local manifest=".doc-manifest.json"

  current=$(find "$source" -type f \( -name "*.py" -o -name "*.tsx" -o -name "*.ts" \) -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)
  stored=$(jq -r --arg src "$source" '.source_to_doc[$src].source_hash // "none"' "$manifest")

  if [ "$current" != "$stored" ]; then
    echo "STALE"
  else
    echo "CURRENT"
  fi
}
```

### Initialize Manifest

```bash
init_manifest() {
  cat > .doc-manifest.json << 'EOF'
{
  "version": "1.0",
  "last_full_generation": null,
  "index_hash": null,
  "source_to_doc": {}
}
EOF
}
```

---

## Integration with Git Hooks

### Pre-commit (fast staleness check)

The pre-commit hook should:
1. Update index.json (existing behavior)
2. Run quick staleness check
3. Warn (don't block) if docs are stale

See: `.git/hooks/pre-commit` or `.github/hooks/pre-commit`

### CI/CD (actual regeneration)

GitHub Action should:
1. Run on merge to main/develop
2. Execute `/generate-docs --incremental`
3. Commit updated docs or create PR

See: `.github/workflows/docs-maintenance.yml`

---

## Best Practices

1. **Initialize manifest early** - Run full generation to create baseline
2. **Configure mappings** - Create `.doc-config.json` for your project
3. **Use --verify in CI** - Fail builds if docs are stale
4. **Use --incremental for updates** - Don't regenerate unchanged docs
5. **Review --diff before applying** - Understand what will change
6. **Commit manifest with docs** - Track state in version control

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No manifest found | Run `/generate-docs` (full) first to create it |
| All docs show stale | Manifest may be outdated; run full generation |
| Hash mismatch on unchanged files | Check for whitespace/formatting changes |
| Incremental misses files | Update `.doc-config.json` mappings |
| CI fails on staleness | Run `/generate-docs --incremental` locally first |

---

## Quick Reference

```bash
# First time setup
/generate-docs                    # Full generation, creates manifest

# Regular maintenance
/generate-docs --verify           # Check what's stale
/generate-docs --diff             # Preview changes
/generate-docs --incremental      # Update stale docs only

# Specific areas
/generate-docs src/api src/db     # Full generation for specific dirs
/generate-docs --incremental src/api  # Incremental for specific dir
```
