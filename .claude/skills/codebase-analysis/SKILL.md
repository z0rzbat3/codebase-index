---
name: codebase-analysis
description: Explore codebase, analyze code, review code, assess code quality, evaluate architecture, find callers, measure impact, search semantically, generate documentation, navigate index. Triggers on: dependencies, what calls, who calls, what uses, callers, impact, blast radius, code architecture, find function, search code, explore codebase, analyse code, review code, review documentation, document, create documentation, evaluate, assess, index structure, list symbols, list functions, list classes, how many files, how many lines, codebase stats, inventory.
allowed-tools: Bash(codebase-index:*), Bash(pip:*), Bash(cp:*), Bash(chmod:*), Bash(mkdir:*), Read, Glob, Write
user-invocable: true
---

# Codebase Analysis

Use `codebase-index` to analyze code structure, dependencies, and impact.

## Setup (run if index.json missing or codebase-index not installed)

### 1. Check/Install codebase-index
```bash
# Check if installed
which codebase-index || pip install codebase-index[semantic]
```

### 2. Build index for current project
```bash
codebase-index . -o index.json --build-embeddings
```

### 3. (Optional) Install pre-commit hook to keep index fresh
```bash
mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e
if [ ! -f "index.json" ]; then
    codebase-index . -o index.json --build-embeddings
    git add index.json
    exit 0
fi
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|pyw|ts|tsx|js|jsx|sql)$|docker-compose\.ya?ml$' || true)
if [ -z "$STAGED_FILES" ]; then exit 0; fi
echo "Updating codebase index..."
codebase-index --load index.json --update --build-embeddings -o index.json 2>/dev/null
git add index.json
EOF
chmod +x .git/hooks/pre-commit
```

## When to Use Each Command

| User Says | Command |
|-----------|---------|
| "What calls X?" / "What uses X?" | `--callers X` |
| "What happens if I change X?" | `--impact path/to/file.py` |
| "How does X work?" / "Show me X" | `--doc X` |
| "Find code that does Y" | `--search "Y"` |
| "What's in this codebase?" | `--summary` |
| "What's the index structure?" | `--schema` |
| "List all functions/classes" | `--keys symbol_index` |
| "Find symbol named X" | `--get X` |
| "How many files/lines?" | `--path summary.total_files` |

## Commands (use after setup)

### Before modifying a file - check impact
```bash
codebase-index --load index.json --impact path/to/file.py
```

### Find what calls a function/class
```bash
codebase-index --load index.json --callers SymbolName
```

### Get documentation for a symbol
```bash
codebase-index --load index.json --doc ClassName.method
```

### Search by concept (semantic)
```bash
codebase-index --load index.json --search "retry logic with backoff"
```

### Codebase overview
```bash
codebase-index --load index.json --summary
```

## Index Navigation (for large codebases)

Use these commands to explore the index structure directly without loading it all into context.

### See index structure/schema
```bash
codebase-index --load index.json --schema
```

### List keys at any level
```bash
# Root level keys
codebase-index --load index.json --keys

# Keys under a specific section
codebase-index --load index.json --keys symbol_index
codebase-index --load index.json --keys centrality
```

### Find a symbol by name
```bash
# Searches functions, classes, and methods
codebase-index --load index.json --get MyClassName
codebase-index --load index.json --get parse  # partial match
```

### Extract data at specific path
```bash
# Get a single value
codebase-index --load index.json --path summary.total_files

# Get array with limit
codebase-index --load index.json --path symbol_index.functions --limit 10
codebase-index --load index.json --path centrality.hub_components --limit 5

# Navigate nested structures
codebase-index --load index.json --path call_graph
```

## Index Freshness

The index updates automatically on commit via pre-commit hook. To manually update:
```bash
codebase-index --load index.json --update -o index.json
```

## Decision Tree

```
User asks about code analysis
         │
         ▼
    index.json exists?
      /          \
    YES           NO
     │             │
     ▼             ▼
  Run command   codebase-index installed?
                  /          \
                YES           NO
                 │             │
                 ▼             ▼
           Build index    Install first:
           (step 2)       pip install codebase-index[semantic]
                          then build index
```

## Limitations

Static analysis cannot detect:
- Dynamic dispatch (`getattr()`, `handlers[key]()`)
- Runtime configuration
- Metaprogramming
