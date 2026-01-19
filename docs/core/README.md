# Core Modules

> Auto-generated documentation for `codebase_index/` root modules

This directory contains documentation for the core modules of codebase-index.

## Module Index

| Module | Description |
|--------|-------------|
| [call_graph.md](call_graph.md) | Call graph query functions for impact analysis |
| [cli.md](cli.md) | Command-line interface and argument parsing |
| [config.md](config.md) | Configuration constants and YAML loading utilities |
| [incremental.md](incremental.md) | Incremental index updates via file hash comparison |
| [scanner.md](scanner.md) | Main scanner orchestrator coordinating all parsers and analyzers |
| [utils.md](utils.md) | Common utility functions for hashing, git, and file operations |

## Architecture Overview

```
CLI (cli.py)
    |
    v
CodebaseScanner (scanner.py)
    |
    +-- Parsers (Python, TypeScript, SQL, Docker)
    +-- Domain Scanners (routes, deps, env, todos, etc.)
    +-- Analyzers (imports, auth, complexity, tests, etc.)
    |
    v
Index Output (JSON)
    |
    v
Query Functions (call_graph.py, cli.py navigation)
    |
    v
IncrementalUpdater (incremental.py) for updates
```

## Key Entry Points

- **`main()`** in `cli.py`: CLI entry point
- **`CodebaseScanner.scan()`** in `scanner.py`: Full codebase scan
- **`incremental_update()`** in `incremental.py`: Partial index update
- **`cg_query_callers()`** in `call_graph.py`: Find callers of a function

## Configuration

All modules respect the configuration defined in `config.py`. Use `--config` to load custom YAML configuration or `--init-config` to generate a template.

---
*Generated for codebase-index core modules*
