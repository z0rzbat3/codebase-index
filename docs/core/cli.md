# cli

> Auto-generated from `codebase_index/cli.py`

## Overview

CLI interface for codebase_index. Provides the command-line interface for scanning codebases, querying indexes, and running analysis tools.

## Constants

### `INDEX_SCHEMA`

Template describing the structure of index.json with field descriptions for meta, summary, symbol_index, call_graph, files, centrality, semantic, dependencies, api_endpoints, database, and test_coverage sections.

## Functions

### `get_index_schema() -> dict`

Return the index schema template.

### `get_keys_at_path(data, path, limit) -> dict`

List keys at a given JSON path for navigating large indexes.

**Parameters:**
- `data`: The index data
- `path`: Dot-notation path (empty string for root)
- `limit`: Optional limit on results

### `find_symbol_by_name(data, name) -> dict`

Find a symbol by name across functions, classes, and methods (supports partial matching).

### `get_data_at_path(data, path, limit) -> dict`

Extract data at a dot-notation path (e.g., 'symbol_index.functions').

### `create_parser() -> argparse.ArgumentParser`

Create the argument parser with all CLI options including:
- Basic scanning options (`path`, `-o`, `--load`, `--summary`)
- Exclusion options (`--exclude`, `--exclude-dirs`, `--exclude-ext`)
- Configuration (`--config`, `--init-config`)
- Call graph queries (`--callers`)
- Analysis queries (`--check`, `--tests`, `--impact`, `--doc`)
- Index navigation (`--schema`, `--keys`, `--get`, `--path`, `--limit`)
- Semantic search (`--build-embeddings`, `--search`)

### `setup_logging(verbose) -> None`

Configure logging based on verbosity level.

### `main() -> None`

Main entry point for the CLI. Orchestrates:
1. Config loading and validation
2. Index loading or codebase scanning
3. Query handling (callers, impact, tests, doc, search)
4. Output generation

### `load_index(load_path, verbose) -> dict[str, Any]`

Load an existing index file from disk.

### `scan_codebase(args, config) -> dict[str, Any]`

Scan the codebase and return the result using CodebaseScanner.

### `handle_cg_query(args, result) -> None`

Handle call graph queries (--callers).

## Usage

```python
# Programmatic usage
from codebase_index.cli import main, create_parser, load_index

# Parse custom args
parser = create_parser()
args = parser.parse_args(['--load', 'index.json', '--callers', 'MyFunc'])

# Load and query an index
index = load_index('index.json', verbose=False)
```

```bash
# Command-line usage
codebase-index .                           # Scan current directory
codebase-index --load index.json --callers MyFunc
codebase-index --load index.json --doc MyClass
codebase-index --load index.json --schema
```

---
*Source: codebase_index/cli.py | Lines: 870*
