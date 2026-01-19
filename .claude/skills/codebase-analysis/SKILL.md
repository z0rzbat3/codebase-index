---
name: codebase-analysis
description: Analyze code structure, find function callers, measure change impact, and search code semantically. Use when asked about dependencies, what calls a function, impact of changes, code architecture, or finding code by concept.
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
