# scanner

> Auto-generated from `codebase_index/scanner.py`

## Overview

Main scanner orchestrator for codebase_index. Coordinates all parsers, scanners, and analyzers to produce a complete codebase index.

## Classes

### `CodebaseScanner`

Main scanner that orchestrates all language-specific scanners and analyzers.

#### Constructor

```python
CodebaseScanner(
    root: Path,
    exclude: list[str] | None = None,
    exclude_extensions: set[str] | None = None,
    include_hash: bool = True,
    config: dict[str, Any] | None = None
)
```

**Parameters:**
- `root`: Root directory to scan
- `exclude`: Patterns to exclude (directories, file patterns)
- `exclude_extensions`: File extensions to exclude
- `include_hash`: Whether to include file hashes
- `config`: Configuration dictionary (merged with defaults)

#### Methods

- `scan() -> dict[str, Any]`: Scan the entire codebase. Returns complete codebase index dictionary with all analysis results.

#### Internal Methods

- `_init_result() -> dict[str, Any]`: Initialize the result structure with all index sections
- `_build_meta() -> dict[str, Any]`: Build metadata section with git info
- `_walk_files() -> Iterator[Path]`: Walk directory and yield files to scan
- `_scan_file(filepath) -> dict[str, Any] | None`: Scan a single file using appropriate parser
- `_build_file_info(...)`: Build file info dictionary with exports
- `_process_file_data(...)`: Process scanned file data into result collections
- `_process_python_file(...)`: Process Python file data (routes, models, schemas)
- `_process_docker_file(...)`: Process Docker Compose file data
- `_index_python_symbols(...)`: Index Python symbols (functions, classes, methods)
- `_build_call_graph(result)`: Build call graph and detect code duplicates
- `_add_to_call_graph(...)`: Add a function/method to the call graph
- `_update_summary(summary, file_info)`: Update summary statistics
- `_finalize_summary(result)`: Add final summary counts from analysis results
- `_generate_badges(summary)`: Generate shields.io badge URLs for README

#### Integrated Components

**Domain Scanners:**
- `DependenciesScanner`: Package dependencies
- `EnvScanner`: Environment variables
- `TodoScanner`: TODO/FIXME comments
- `RoutePrefixScanner`: API route prefixes
- `HttpCallsScanner`: External HTTP calls
- `MiddlewareScanner`: Middleware detection
- `WebSocketScanner`: WebSocket endpoints
- `AlembicScanner`: Database migrations

**Analyzers:**
- `ImportAggregator`: Import analysis
- `AuthScanner`: Authentication requirements
- `ComplexityAnalyzer`: Code complexity warnings
- `TestCoverageMapper`: Test file mapping
- `OrphanedFileScanner`: Unused file detection
- `ExecutionFlowAnalyzer`: Call flow analysis
- `CentralityAnalyzer`: Symbol importance

## Usage

```python
from pathlib import Path
from codebase_index.scanner import CodebaseScanner

scanner = CodebaseScanner(
    root=Path('.'),
    exclude=['node_modules', '__pycache__'],
    include_hash=True,
    config={'routes': {'enabled': True}}
)

result = scanner.scan()
print(f"Files: {result['summary']['total_files']}")
print(f"Functions: {result['summary']['total_functions']}")
print(f"Endpoints: {result['summary']['api_endpoints_count']}")
```

---
*Source: codebase_index/scanner.py | Lines: 662*
