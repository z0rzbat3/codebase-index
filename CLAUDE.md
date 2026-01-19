# codebase-index: Claude Code Integration

Pre-built index at `index.json` (336 symbols, embeddings included). Kept fresh via pre-commit hook.

## Use codebase-index Instead of Native Tools For:

### 1. BEFORE modifying any file - check impact first
```bash
codebase-index --load index.json --impact codebase_index/parsers/python.py
```
Shows what depends on the file. Review before making breaking changes.

### 2. Finding what calls a function/class
```bash
codebase-index --load index.json --callers CodebaseScanner
```
One command instead of multiple grep iterations.

### 3. Understanding a symbol (rich docs)
```bash
codebase-index --load index.json --doc SemanticSearcher.search
```
Returns signature, callers, callees, and source code.

### 4. Finding code by concept (semantic search)
```bash
codebase-index --load index.json --search "error handling with retry"
```
Finds code by meaning, not just keywords.

### 5. Index navigation (surgical extraction)
```bash
# See index structure
codebase-index --load index.json --schema

# List keys at any level
codebase-index --load index.json --keys              # root keys
codebase-index --load index.json --keys symbol_index # drill down

# Find symbol by name (partial match)
codebase-index --load index.json --get CodebaseScanner

# Extract specific data
codebase-index --load index.json --path summary.total_files
codebase-index --load index.json --path symbol_index.functions --limit 5
```
For large indexes: explore structure without loading everything into context.

## Still Use Native Tools For:
- Reading specific files → `Read`
- Simple text search → `Grep`
- Finding files by pattern → `Glob`

## Architecture Quick Reference

```
codebase_index/           # Main package
├── parsers/              # PythonParser (AST), TypeScriptParser (regex)
├── scanners/             # Routes, auth, deps, middleware, etc.
├── analyzers/            # Impact, semantic search, complexity
├── cli.py                # Entry point → main()
└── scanner.py            # CodebaseScanner orchestrates everything

codebase_index.py         # Legacy monolith - 91 symbols, avoid modifying
```

## Key Symbols
- `CodebaseScanner` - Main orchestrator, called from cli.py
- `ParserRegistry` - Plugin system (`@ParserRegistry.register`)
- `SemanticSearcher` - Embedding-based search
- `ImpactAnalyzer` - Blast radius analysis

## New Features (just added)
- **Constants indexed**: `MODELS`, `DEFAULT_MODEL`, etc. now searchable
- **Semantic tags**: Code tagged with `[caching]`, `[error-handling]`, etc.
- **Dynamic call warnings**: `getattr()`, `eval()` patterns flagged in index

## Limitations
Static analysis cannot detect:
- Dynamic dispatch (`getattr()`, `handlers[key]()`)
- Runtime configuration
- Metaprogramming

Check `dynamic_calls` field in function/method info for flagged patterns.
