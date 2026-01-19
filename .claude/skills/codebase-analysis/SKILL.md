---
name: codebase-analysis
description: Analyze code structure, find function callers, measure change impact, and search code semantically. Use when asked about dependencies, what calls a function, impact of changes, code architecture, or finding code by concept.
allowed-tools: Bash(codebase-index:*), Read, Glob
---

# Codebase Analysis

Use `codebase-index` with the pre-built index at `index.json`.

## Commands

### Before modifying a file - check impact
```bash
codebase-index --load index.json --impact path/to/file.py
```
Shows what depends on the file and what might break.

### Find what calls a function/class
```bash
codebase-index --load index.json --callers SymbolName
```
Reverse dependency lookup - one command instead of multiple greps.

### Get documentation for a symbol
```bash
codebase-index --load index.json --doc ClassName.method
```
Returns signature, callers, callees, and source code.

### Search by concept (semantic)
```bash
codebase-index --load index.json --search "retry logic with backoff"
```
Finds code by meaning using embeddings. Lower `--search-threshold` (default 0.3) for more results.

### Codebase overview
```bash
codebase-index --load index.json --summary
```

## When to Use Each

| User Says | Command |
|-----------|---------|
| "What calls X?" / "What uses X?" | `--callers X` |
| "What happens if I change X?" | `--impact path/to/file.py` |
| "How does X work?" / "Show me X" | `--doc X` |
| "Find code that does Y" | `--search "Y"` |
| "What's in this codebase?" | `--summary` |

## Index Freshness

The index updates automatically on commit via pre-commit hook. To manually update:
```bash
codebase-index --load index.json --update -o index.json
```

## Limitations

Static analysis cannot detect:
- Dynamic dispatch (`getattr()`, `handlers[key]()`)
- Runtime configuration
- Metaprogramming

Check `dynamic_calls` field in output for flagged patterns.
