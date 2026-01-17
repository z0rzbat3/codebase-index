# Codebase-Index: Complete Reference

> Auto-generated documentation with full coverage of all modules, classes, and methods.

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Core Classes](#core-classes)
3. [Parsers](#parsers)
4. [Scanners](#scanners)
5. [Analyzers](#analyzers)
6. [Utility Functions](#utility-functions)
7. [Call Graph](#call-graph)
8. [Configuration](#configuration)

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `codebase-index .` | Scan current directory |
| `codebase-index . -o index.json` | Save to file |
| `codebase-index --load index.json --check` | Check staleness |
| `codebase-index --load index.json --impact FILE` | Impact analysis |
| `codebase-index --load index.json --coupled-with FILE` | Coupling analysis |
| `codebase-index --load index.json --tests-for SYMBOL` | Find tests |
| `codebase-index --load index.json --schema NAME` | Schema usage |
| `codebase-index --load index.json --search QUERY` | Semantic search |
| `codebase-index . --build-embeddings` | Build embeddings |
| `codebase-index . --generate-summaries` | LLM summaries |
| `codebase-index --load index.json --update` | Incremental update |
| `codebase-index --load index.json --cg-query FUNC` | Call graph query |
| `codebase-index --load index.json --cg-callers FUNC` | Reverse call graph |

---

## Core Classes

### `codebase_index.py`

**Path:** `codebase_index.py`  
**Lines:** 3159

#### `class DependenciesScanner`

*Defined at line 559*

**Description:**
> Scan for project dependencies from requirements.txt, package.json, etc.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 562 | `dict` | Scan for all dependency files. |
| `_parse_requirements` | 596 | `list` | Parse requirements.txt file. |
| `_parse_pyproject` | 614 | `list` | Parse pyproject.toml for dependencies. |
| `_parse_package_json` | 632 | `dict` | Parse package.json for dependencies. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict`

Scan for all dependency files.

##### `_parse_requirements(self: None, filepath: Path) -> list`

Parse requirements.txt file.

##### `_parse_pyproject(self: None, filepath: Path) -> list`

Parse pyproject.toml for dependencies.

##### `_parse_package_json(self: None, filepath: Path) -> dict`

Parse package.json for dependencies.

</details>

#### `class EnvScanner`

*Defined at line 650*

**Description:**
> Scan for environment variable usage (names only, no values).

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 653 | `dict` | Scan for environment variables. |
| `_parse_dotenv` | 693 | `list` | Parse .env file for variable names (NOT values). |
| `_scan_python_env` | 711 | `set` | Scan Python file for environment variable access. |
| `_scan_typescript_env` | 734 | `set` | Scan TypeScript file for environment variable access. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict`

Scan for environment variables.

##### `_parse_dotenv(self: None, filepath: Path) -> list`

Parse .env file for variable names (NOT values).

##### `_scan_python_env(self: None, filepath: Path) -> set`

Scan Python file for environment variable access.

##### `_scan_typescript_env(self: None, filepath: Path) -> set`

Scan TypeScript file for environment variable access.

</details>

#### `class TodoScanner`

*Defined at line 762*

**Description:**
> Scan for TODO, FIXME, HACK, XXX comments.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 771 | `list` | Scan all files for TODO/FIXME comments. |
| `_scan_file` | 785 | `list` | Scan a single file for TODOs. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list) -> list`

Scan all files for TODO/FIXME comments.

##### `_scan_file(self: None, filepath: Path, root: Path) -> list`

Scan a single file for TODOs.

</details>

#### `class RoutePrefixScanner`

*Defined at line 815*

**Description:**
> Scan FastAPI main.py for router prefixes to build full paths.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 818 | `dict` | Scan for include_router calls to extract prefixes. |
| `_scan_main_file` | 833 | `dict` | Scan a main.py file for include_router calls. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict`

Scan for include_router calls to extract prefixes.

##### `_scan_main_file(self: None, filepath: Path) -> dict`

Scan a main.py file for include_router calls.

</details>

#### `class ImportAggregator`

*Defined at line 907*

**Description:**
> Aggregate all imports across the codebase and detect missing/unused deps.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 910 | `-` | - |
| `add_imports` | 915 | `-` | Add imports from a file. |
| `add_internal_module` | 928 | `-` | Register a module as internal to the project. |
| `analyze` | 933 | `dict` | Analyze imports against declared dependencies.  Returns:    ... |

<details>
<summary>Method Details</summary>

##### `__init__(self: None)`

*No documentation*

##### `add_imports(self: None, imports: list, filepath: str)`

Add imports from a file.

##### `add_internal_module(self: None, module_name: str)`

Register a module as internal to the project.

##### `analyze(self: None, declared_deps: list) -> dict`

Analyze imports against declared dependencies.

Returns:
    dict with missing_deps and unused_deps

</details>

#### `class AuthScanner`

*Defined at line 1040*

**Description:**
> Scan for authentication requirements per endpoint.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan_file` | 1056 | `list` | Scan a file and annotate routes with auth requirements. |
| `_check_auth_around_line` | 1086 | `str` | Check for auth patterns around a specific line. |

<details>
<summary>Method Details</summary>

##### `scan_file(self: None, filepath: Path, routes: list) -> list`

Scan a file and annotate routes with auth requirements.

##### `_check_auth_around_line(self: None, lines: list, line_num: int) -> str`

Check for auth patterns around a specific line.

</details>

#### `class TestCoverageMapper`

*Defined at line 1105*

**Description:**
> Map source files to their corresponding test files.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 1108 | `-` | - |
| `collect_test_files` | 1113 | `-` | Collect all test files in the project. |
| `map_source_to_test` | 1128 | `dict` | Map source files to potential test files. |
| `_find_test_file` | 1173 | `str` | Find a test file for a given source file. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path)`

*No documentation*

##### `collect_test_files(self: None, exclude: list)`

Collect all test files in the project.

##### `map_source_to_test(self: None, source_files: list) -> dict`

Map source files to potential test files.

##### `_find_test_file(self: None, source_path: str) -> str`

Find a test file for a given source file.

</details>

#### `class HttpCallsScanner`

*Defined at line 1208*

**Description:**
> Scan for external HTTP calls (httpx, requests, aiohttp, fetch).

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 1234 | `dict` | Scan for external HTTP calls. |
| `_scan_python_file` | 1271 | `list` | Scan a Python file for HTTP calls. |
| `_scan_ts_file` | 1306 | `list` | Scan a TypeScript file for HTTP calls. |
| `_extract_domain` | 1343 | `str` | Extract domain from URL. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list) -> dict`

Scan for external HTTP calls.

##### `_scan_python_file(self: None, filepath: Path, root: Path) -> list`

Scan a Python file for HTTP calls.

##### `_scan_ts_file(self: None, filepath: Path, root: Path) -> list`

Scan a TypeScript file for HTTP calls.

##### `_extract_domain(self: None, url: str) -> str`

Extract domain from URL.

</details>

#### `class ComplexityAnalyzer`

*Defined at line 1363*

**Description:**
> Analyze code complexity and flag large files/functions.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `analyze` | 1374 | `dict` | Analyze all files for complexity issues. |

<details>
<summary>Method Details</summary>

##### `analyze(self: None, files: list) -> dict`

Analyze all files for complexity issues.

</details>

#### `class MiddlewareScanner`

*Defined at line 1444*

**Description:**
> Scan for FastAPI/Starlette middleware configuration.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 1458 | `dict` | Scan for middleware usage. |
| `_scan_file` | 1475 | `dict` | Scan a file for middleware. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list) -> dict`

Scan for middleware usage.

##### `_scan_file(self: None, filepath: Path, root: Path) -> dict`

Scan a file for middleware.

</details>

#### `class WebSocketScanner`

*Defined at line 1528*

**Description:**
> Scan for WebSocket endpoints.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 1531 | `dict` | Scan for WebSocket endpoints. |
| `_scan_file` | 1547 | `list` | Scan a file for WebSocket endpoints. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list) -> dict`

Scan for WebSocket endpoints.

##### `_scan_file(self: None, filepath: Path, root: Path) -> list`

Scan a file for WebSocket endpoints.

</details>

#### `class AlembicScanner`

*Defined at line 1603*

**Description:**
> Scan for Alembic database migrations.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 1606 | `dict` | Scan for Alembic migrations. |
| `_scan_migrations` | 1641 | `list` | Scan migration files. |
| `_parse_migration` | 1655 | `dict` | Parse a single migration file. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict`

Scan for Alembic migrations.

##### `_scan_migrations(self: None, migrations_dir: Path, root: Path) -> list`

Scan migration files.

##### `_parse_migration(self: None, filepath: Path, root: Path) -> dict`

Parse a single migration file.

</details>

#### `class OrphanedFileScanner`

*Defined at line 1722*

**Description:**
> Detect Python files that are never imported anywhere.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 1756 | `-` | - |
| `scan` | 1761 | `dict` | Detect orphaned files.  Args:     root: Project root     fil... |
| `_path_to_module` | 1842 | `str` | Convert file path to Python module name. |
| `_is_excluded` | 1851 | `bool` | Check if file matches excluded patterns. |
| `_is_entry_point` | 1858 | `bool` | Check if file is an entry point. |
| `_is_imported` | 1873 | `bool` | Check if a file/module is imported anywhere. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None)`

*No documentation*

##### `scan(self: None, root: Path, files: list, exclude: list) -> dict`

Detect orphaned files.

Args:
    root: Project root
    files: List of file info dicts from main scan
    exclude: Exclusion patterns

##### `_path_to_module(self: None, path: str) -> str`

Convert file path to Python module name.

##### `_is_excluded(self: None, filename: str) -> bool`

Check if file matches excluded patterns.

##### `_is_entry_point(self: None, path: str, filename: str) -> bool`

Check if file is an entry point.

##### `_is_imported(self: None, path: str, module_name: str) -> bool`

Check if a file/module is imported anywhere.

</details>

#### `class PythonScanner`

*Defined at line 1904*

**Description:**
> Scan Python files using AST for accurate extraction.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 1907 | `dict` | Scan a Python file and extract structure. |
| `_get_name` | 2009 | `str` | Get name from AST node. |
| `_get_decorator_name` | 2019 | `str` | Extract decorator name. |
| `_extract_signature` | 2029 | `dict` | Extract function signature (parameters and return type). |
| `_get_annotation` | 2082 | `str` | Extract type annotation as string. |
| `_extract_calls` | 2110 | `list` | Extract all function/method calls from a function body. Retu... |
| `_get_call_name` | 2130 | `str` | Extract the name of a call target. |
| `_get_function_body_hash` | 2150 | `str` | Generate a normalized hash of function body for duplicate de... |
| `_extract_route_info` | 2176 | `dict` | Extract FastAPI route information from decorator. |
| `_categorize_import` | 2203 | `-` | Categorize import as internal or external. |
| `_scan_regex` | 2223 | `dict` | Fallback regex-based scanning for files with syntax errors. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict`

Scan a Python file and extract structure.

##### `_get_name(self: None, node: None) -> str`

Get name from AST node.

##### `_get_decorator_name(self: None, node: None) -> str`

Extract decorator name.

##### `_extract_signature(self: None, node: None) -> dict`

Extract function signature (parameters and return type).

##### `_get_annotation(self: None, node: None) -> str`

Extract type annotation as string.

##### `_extract_calls(self: None, node: None) -> list`

Extract all function/method calls from a function body.
Returns raw call strings for LLM to analyze.

##### `_get_call_name(self: None, node: None) -> str`

Extract the name of a call target.

##### `_get_function_body_hash(self: None, node: None) -> str`

Generate a normalized hash of function body for duplicate detection.
Normalizes variable names to detect structurally similar code.

##### `_extract_route_info(self: None, decorator: None, func_name: str, line: int) -> dict`

Extract FastAPI route information from decorator.

##### `_categorize_import(self: None, module: str, imports: dict)`

Categorize import as internal or external.

##### `_scan_regex(self: None, filepath: Path) -> dict`

Fallback regex-based scanning for files with syntax errors.

</details>

#### `class TypeScriptScanner`

*Defined at line 2278*

**Description:**
> Scan TypeScript/React files using regex patterns.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 2281 | `dict` | Scan a TypeScript/React file. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict`

Scan a TypeScript/React file.

</details>

#### `class SQLScanner`

*Defined at line 2365*

**Description:**
> Scan SQL files for table definitions.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 2368 | `dict` | Scan a SQL file. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict`

Scan a SQL file.

</details>

#### `class DockerScanner`

*Defined at line 2401*

**Description:**
> Scan Docker Compose files.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 2404 | `dict` | Scan a docker-compose file. |
| `_scan_regex` | 2447 | `dict` | Fallback regex scanning if YAML not available. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict`

Scan a docker-compose file.

##### `_scan_regex(self: None, filepath: Path) -> dict`

Fallback regex scanning if YAML not available.

</details>

#### `class CodebaseScanner`

*Defined at line 2477*

**Description:**
> Main scanner that orchestrates all language-specific scanners.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 2480 | `-` | - |
| `scan` | 2511 | `dict` | Scan the entire codebase. |
| `_truncate_docstring` | 2812 | `str` | Truncate docstring to first line or max length. |
| `_build_meta` | 2822 | `dict` | Build metadata section. |
| `_walk_files` | 2836 | `-` | Walk directory and yield files to scan. |
| `_scan_file` | 2847 | `dict` | Scan a single file. |
| `_update_summary` | 2902 | `-` | Update summary statistics. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path, exclude: list, exclude_extensions: set, include_hash: bool)`

*No documentation*

##### `scan(self: None) -> dict`

Scan the entire codebase.

##### `_truncate_docstring(self: None, docstring: str, max_length: int) -> str`

Truncate docstring to first line or max length.

##### `_build_meta(self: None) -> dict`

Build metadata section.

##### `_walk_files(self: None)`

Walk directory and yield files to scan.

##### `_scan_file(self: None, filepath: Path) -> dict`

Scan a single file.

##### `_update_summary(self: None, summary: dict, file_info: dict)`

Update summary statistics.

</details>

#### `def get_config_template() -> str`

*Defined at line 264*

Generate a well-documented YAML config template for LLMs to customize.

#### `def load_config(config_path: Path) -> dict`

*Defined at line 460*

Load configuration from YAML file, merged with defaults.

#### `def get_file_hash(filepath: Path) -> str`

*Defined at line 489*

Generate SHA256 hash of file contents.

#### `def count_lines(filepath: Path) -> int`

*Defined at line 498*

Count lines in a file.

#### `def get_git_info(root: Path) -> dict`

*Defined at line 507*

Get git metadata.

#### `def categorize_file(filepath: str, categories: dict) -> str`

*Defined at line 535*

Categorize a file based on path patterns.

#### `def should_exclude(path: Path, exclude_patterns: list) -> bool`

*Defined at line 543*

Check if path should be excluded.

#### `def cg_query_function(call_graph: dict, func_name: str) -> dict`

*Defined at line 2923*

Query what a specific function calls (fuzzy match).

#### `def cg_query_file(call_graph: dict, file_path: str) -> dict`

*Defined at line 2942*

Query all functions in a specific file.

#### `def cg_query_callers(call_graph: dict, func_name: str) -> dict`

*Defined at line 2959*

Query what functions call a specific function (inverse lookup).

#### `def main()`

*Defined at line 2989*

*No documentation*

---

## codebase_index

### `call_graph.py`

**Path:** `codebase_index/call_graph.py`  
**Lines:** 103

#### `def cg_query_function(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]`

*Defined at line 15*

Query what a specific function calls (fuzzy match).

Args:
    call_graph: The call graph dictionary.
    func_name: Function name to search for.

Returns:
    Dictionary with query info and matching results.

#### `def cg_query_file(call_graph: dict[str, Any], file_path: str) -> dict[str, Any]`

*Defined at line 43*

Query all functions in a specific file.

Args:
    call_graph: The call graph dictionary.
    file_path: File path to search for.

Returns:
    Dictionary with query info and matching results.

#### `def cg_query_callers(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]`

*Defined at line 69*

Query what functions call a specific function (inverse lookup).

Args:
    call_graph: The call graph dictionary.
    func_name: Function name to find callers of.

Returns:
    Dictionary with query info and matching results.

---

### `cli.py`

**Path:** `codebase_index/cli.py`  
**Lines:** 661

#### `def create_parser() -> argparse.ArgumentParser`

*Defined at line 38*

Create the argument parser.

#### `def setup_logging(verbose: bool) -> None`

*Defined at line 286*

Configure logging based on verbosity.

#### `def main() -> None`

*Defined at line 295*

Main entry point for the CLI.

#### `def load_index(load_path: str, verbose: bool) -> dict[str, Any]`

*Defined at line 563*

Load an existing index file.

#### `def scan_codebase(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]`

*Defined at line 575*

Scan the codebase and return the result.

#### `def handle_cg_query(args: argparse.Namespace, result: dict[str, Any]) -> None`

*Defined at line 641*

Handle call graph queries.

---

### `config.py`

**Path:** `codebase_index/config.py`  
**Lines:** 570

#### `def load_config(config_path: Path) -> dict[str, Any]`

*Defined at line 278*

Load configuration from YAML file, merged with defaults.

Args:
    config_path: Path to the YAML configuration file.

Returns:
    Configuration dictionary with user values merged over defaults.

Raises:
    SystemExit: If PyYAML is not installed.
    FileNotFoundError: If config file doesn't exist.

#### `def get_config_template() -> str`

*Defined at line 310*

Generate a well-documented YAML config template for LLMs to customize.

---

### `incremental.py`

**Path:** `codebase_index/incremental.py`  
**Lines:** 379

#### `class IncrementalUpdater`

*Defined at line 22*

**Description:**
> Incrementally update an existing index.

Compares file hashes to detect changes and only re-scans modified files.
Much faster than full re-scan for large codebases with few changes.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 30 | `None` | Initialize the incremental updater.  Args:     root: Root di... |
| `update` | 57 | `dict[str, Any]` | Perform incremental update.  Args:     scanner: CodebaseScan... |
| `_get_current_files` | 120 | `list[Path]` | Get list of current files in codebase (respecting exclusions... |
| `_compute_hash` | 143 | `str` | Compute SHA-256 hash of file contents. |
| `_apply_updates` | 152 | `dict[str, Any]` | Apply the detected changes to create updated index.  Args:  ... |
| `_scan_files` | 240 | `None` | Scan specific files and add results to updated index.  Args:... |
| `_detect_language` | 318 | `str` | Detect language from file extension. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path, index_data: dict[str, Any], exclude: list[str], exclude_extensions: set[str] | None) -> None`

Initialize the incremental updater.

Args:
    root: Root directory of the codebase.
    index_data: The existing index data to update.
    exclude: Patterns to exclude from scanning.
    exclude_extensions: File extensions to exclude.

##### `update(self: None, scanner: Any) -> dict[str, Any]`

Perform incremental update.

Args:
    scanner: CodebaseScanner instance to use for re-scanning files.

Returns:
    Dictionary with update results and statistics.

##### `_get_current_files(self: None) -> list[Path]`

Get list of current files in codebase (respecting exclusions).

##### `_compute_hash(self: None, file_path: Path) -> str`

Compute SHA-256 hash of file contents.

##### `_apply_updates(self: None, scanner: Any, changes: dict[str, Any]) -> dict[str, Any]`

Apply the detected changes to create updated index.

Args:
    scanner: CodebaseScanner to use for re-scanning.
    changes: Dictionary with added/updated/deleted file lists.

Returns:
    Updated index data.

##### `_scan_files(self: None, scanner: Any, file_paths: set[str], updated: dict[str, Any]) -> None`

Scan specific files and add results to updated index.

Args:
    scanner: CodebaseScanner instance.
    file_paths: Set of relative file paths to scan.
    updated: Index dictionary to update.

##### `_detect_language(self: None, suffix: str) -> str`

Detect language from file extension.

</details>

#### `def incremental_update(root: Path, index_data: dict[str, Any], exclude: list[str], exclude_extensions: set[str] | None, config: dict[str, Any] | None) -> dict[str, Any]`

*Defined at line 340*

Convenience function to perform incremental update.

Args:
    root: Root directory of the codebase.
    index_data: Existing index data.
    exclude: Patterns to exclude.
    exclude_extensions: File extensions to exclude.
    config: Configuration dictionary.

Returns:
    Update result with changes and new index.

---

### `scanner.py`

**Path:** `codebase_index/scanner.py`  
**Lines:** 556

#### `class CodebaseScanner`

*Defined at line 53*

**Description:**
> Main scanner that orchestrates all language-specific scanners and analyzers.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 56 | `-` | Initialize the codebase scanner.  Args:     root: Root direc... |
| `scan` | 110 | `dict[str, Any]` | Scan the entire codebase.  Returns:     Complete codebase in... |
| `_init_result` | 159 | `dict[str, Any]` | Initialize the result structure. |
| `_build_meta` | 194 | `dict[str, Any]` | Build metadata section. |
| `_walk_files` | 208 | `Iterator[Path]` | Walk directory and yield files to scan. |
| `_scan_file` | 222 | `dict[str, Any] | None` | Scan a single file. |
| `_build_file_info` | 251 | `dict[str, Any]` | Build file info dictionary. |
| `_process_file_data` | 281 | `None` | Process scanned file data into result collections. |
| `_process_python_file` | 296 | `None` | Process Python file data. |
| `_process_docker_file` | 365 | `None` | Process Docker Compose file data. |
| `_index_python_symbols` | 375 | `None` | Index Python symbols (functions, classes, methods). |
| `_build_call_graph` | 420 | `None` | Build call graph and detect code duplicates. |
| `_add_to_call_graph` | 458 | `None` | Add a function/method to the call graph. |
| `_update_summary` | 496 | `None` | Update summary statistics. |
| `_finalize_summary` | 510 | `None` | Add final summary counts from analysis results. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path, exclude: list[str] | None, exclude_extensions: set[str] | None, include_hash: bool, config: dict[str, Any] | None)`

Initialize the codebase scanner.

Args:
    root: Root directory to scan.
    exclude: Patterns to exclude (directories, file patterns).
    exclude_extensions: File extensions to exclude.
    include_hash: Whether to include file hashes.
    config: Configuration dictionary (merged with defaults).

##### `scan(self: None) -> dict[str, Any]`

Scan the entire codebase.

Returns:
    Complete codebase index dictionary.

##### `_init_result(self: None) -> dict[str, Any]`

Initialize the result structure.

##### `_build_meta(self: None) -> dict[str, Any]`

Build metadata section.

##### `_walk_files(self: None) -> Iterator[Path]`

Walk directory and yield files to scan.

##### `_scan_file(self: None, filepath: Path) -> dict[str, Any] | None`

Scan a single file.

##### `_build_file_info(self: None, filepath: Path, rel_path: str, language: str, parser: Any, category: str) -> dict[str, Any]`

Build file info dictionary.

##### `_process_file_data(self: None, file_info: dict[str, Any], result: dict[str, Any], route_prefixes: dict[str, str]) -> None`

Process scanned file data into result collections.

##### `_process_python_file(self: None, file_info: dict[str, Any], result: dict[str, Any], route_prefixes: dict[str, str]) -> None`

Process Python file data.

##### `_process_docker_file(self: None, exports: dict[str, Any], result: dict[str, Any]) -> None`

Process Docker Compose file data.

##### `_index_python_symbols(self: None, file_info: dict[str, Any], result: dict[str, Any]) -> None`

Index Python symbols (functions, classes, methods).

##### `_build_call_graph(self: None, result: dict[str, Any]) -> None`

Build call graph and detect code duplicates.

##### `_add_to_call_graph(self: None, func_info: dict[str, Any], file_path: str, class_name: str | None, result: dict[str, Any], body_hash_index: dict[str, list[dict[str, Any]]]) -> None`

Add a function/method to the call graph.

##### `_update_summary(self: None, summary: dict[str, Any], file_info: dict[str, Any]) -> None`

Update summary statistics.

##### `_finalize_summary(self: None, result: dict[str, Any]) -> None`

Add final summary counts from analysis results.

</details>

---

### `utils.py`

**Path:** `codebase_index/utils.py`  
**Lines:** 204

#### `def get_file_hash(filepath: Path) -> str`

*Defined at line 21*

Generate SHA256 hash of file contents.

Args:
    filepath: Path to the file to hash.

Returns:
    Hash string in format "sha256:<first 16 chars of hex>".

Raises:
    FileNotFoundError: If the file doesn't exist.
    PermissionError: If the file can't be read.

#### `def count_lines(filepath: Path) -> int`

*Defined at line 42*

Count lines in a file.

Args:
    filepath: Path to the file.

Returns:
    Number of lines in the file, or 0 if the file can't be read.

#### `def get_git_info(root: Path) -> dict[str, Any] | None`

*Defined at line 60*

Get git metadata for a repository.

Args:
    root: Root directory of the git repository.

Returns:
    Dictionary with 'commit', 'branch', and 'dirty' keys,
    or None if not a git repository or git is unavailable.

#### `def categorize_file(filepath: str, categories: dict[str, str]) -> str`

*Defined at line 109*

Categorize a file based on path patterns.

Args:
    filepath: Relative path to the file.
    categories: Dict mapping regex patterns to category names.

Returns:
    Category name, or "other" if no pattern matches.

#### `def should_exclude(path: Path, exclude_patterns: list[str]) -> bool`

*Defined at line 126*

Check if path should be excluded based on patterns.

Args:
    path: Path to check.
    exclude_patterns: List of patterns. Patterns starting with '*'
        match suffixes, others match directory names.

Returns:
    True if the path should be excluded.

#### `def normalize_module_name(name: str) -> str`

*Defined at line 150*

Normalize a module/package name for comparison.

Converts hyphens to underscores and lowercases.

Args:
    name: Module or package name.

Returns:
    Normalized name.

#### `def extract_domain(url: str) -> str | None`

*Defined at line 165*

Extract domain from a URL.

Args:
    url: URL string.

Returns:
    Domain name, or None if extraction fails.

#### `def truncate_string(text: str | None, max_length: int) -> str | None`

*Defined at line 188*

Truncate a string to a maximum length.

Args:
    text: String to truncate.
    max_length: Maximum length.

Returns:
    Truncated string with "..." suffix if needed, or None if input is None.

---

## Analyzers

### `auth.py`

**Path:** `codebase_index/analyzers/auth.py`  
**Lines:** 400

#### `class AuthScanner`

*Defined at line 64*

**Description:**
> Scan for authentication requirements per endpoint.

Uses precise function signature parsing instead of broad context matching.
Config-driven for easy customization.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 72 | `None` | Initialize with default auth patterns. |
| `_compile_patterns` | 78 | `None` | Compile regex patterns for efficient matching. |
| `configure` | 95 | `None` | Configure the scanner with auth patterns from config.  Confi... |
| `scan_file` | 142 | `list[dict[str, Any]]` | Scan a file and annotate routes with auth requirements.  Arg... |
| `_extract_function_signatures_ast` | 191 | `dict[str, dict[str, Any]]` | Extract function signatures using AST for precise parameter ... |
| `_get_signature_text` | 223 | `str` | Extract the raw function signature text. |
| `_get_decorator_text` | 242 | `str` | Extract decorator text above the function. |
| `_detect_auth` | 259 | `str | None` | Detect auth requirement using multiple strategies.  Strategy... |
| `_detect_auth_from_lines` | 296 | `str | None` | Fallback: detect auth by extracting function signature from ... |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

Initialize with default auth patterns.

##### `_compile_patterns(self: None, patterns: dict[str, Any]) -> None`

Compile regex patterns for efficient matching.

##### `configure(self: None, config: dict[str, Any]) -> None`

Configure the scanner with auth patterns from config.

Config format:
```yaml
auth:
  parameters:
    - "Depends\s*\(\s*get_current_user"
    - "current_user\s*:"
  decorators:
    - "@login_required"
    - "@jwt_required"
```

##### `scan_file(self: None, filepath: Path, routes: list[dict[str, Any]]) -> list[dict[str, Any]]`

Scan a file and annotate routes with auth requirements.

Args:
    filepath: Path to the file.
    routes: List of route dictionaries to annotate.

Returns:
    List of routes with auth_required field added.

##### `_extract_function_signatures_ast(self: None, content: str) -> dict[str, dict[str, Any]]`

Extract function signatures using AST for precise parameter analysis.

Returns:
    Dict mapping function name to signature info.

##### `_get_signature_text(self: None, content: str, node: ast.FunctionDef) -> str`

Extract the raw function signature text.

##### `_get_decorator_text(self: None, content: str, node: ast.FunctionDef) -> str`

Extract decorator text above the function.

##### `_detect_auth(self: None, handler: str, route_line: int, lines: list[str], function_signatures: dict[str, dict[str, Any]]) -> str | None`

Detect auth requirement using multiple strategies.

Strategy 1: AST-based signature matching (most accurate)
Strategy 2: Line-based signature extraction (fallback)

Returns:
    Auth type string if auth detected, None otherwise.

##### `_detect_auth_from_lines(self: None, handler: str, route_line: int, lines: list[str]) -> str | None`

Fallback: detect auth by extracting function signature from lines.

Only looks at the actual function definition, NOT broad context.

</details>

#### `def check_endpoint_auth(signature: str, decorators: list[str] | None, config: dict[str, Any] | None) -> dict[str, Any]`

*Defined at line 353*

Utility function: Check if an endpoint requires auth.

Designed for LLM agents to easily check auth requirements.

Args:
    signature: The function signature string.
    decorators: Optional list of decorator strings.
    config: Optional config with custom auth patterns.

Returns:
    {"auth_required": bool, "auth_type": str | None}

Example:
    >>> check_endpoint_auth("def foo(current_user: User = Depends(get_current_user))")
    {"auth_required": True, "auth_type": "parameter:Depends..."}

    >>> check_endpoint_auth("def health_check(db: Session = Depends(get_db))")
    {"auth_required": False, "auth_type": None}

---

### `complexity.py`

**Path:** `codebase_index/analyzers/complexity.py`  
**Lines:** 141

#### `class ComplexityAnalyzer`

*Defined at line 18*

**Description:**
> Analyze code complexity and flag large files/functions.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 21 | `-` | Initialize the complexity analyzer.  Args:     file_lines_wa... |
| `analyze` | 48 | `dict[str, Any]` | Analyze all files for complexity issues.  Args:     files: L... |
| `_analyze_file` | 75 | `None` | Analyze a single file for complexity. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, file_lines_warning: int, file_lines_critical: int, function_lines_warning: int, function_lines_critical: int, class_methods_warning: int, class_methods_critical: int)`

Initialize the complexity analyzer.

Args:
    file_lines_warning: Lines threshold for file warning.
    file_lines_critical: Lines threshold for critical file warning.
    function_lines_warning: Lines threshold for function warning.
    function_lines_critical: Lines threshold for critical function warning.
    class_methods_warning: Methods threshold for class warning.
    class_methods_critical: Methods threshold for critical class warning.

##### `analyze(self: None, files: list[dict[str, Any]]) -> dict[str, Any]`

Analyze all files for complexity issues.

Args:
    files: List of file info dictionaries.

Returns:
    Dictionary with large files, functions, complex classes, and summary.

##### `_analyze_file(self: None, file_info: dict[str, Any], result: dict[str, Any]) -> None`

Analyze a single file for complexity.

</details>

---

### `coupling.py`

**Path:** `codebase_index/analyzers/coupling.py`  
**Lines:** 349

#### `class CouplingAnalyzer`

*Defined at line 21*

**Description:**
> Analyze coupling between files to identify tightly related code.

Coupling score is computed from:
- Call frequency: How often functions in A call functions in B
- Import dependency: Direct imports between files
- Shared imports: Common external dependencies
- Naming similarity: Similar file/function names

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 41 | `None` | Initialize the coupling analyzer.  Args:     index_data: The... |
| `files_by_path` | 55 | `dict[str, dict[str, Any]]` | Get files indexed by path. |
| `call_graph` | 65 | `dict[str, Any]` | Get the call graph from the index. |
| `reverse_calls` | 72 | `dict[str, set[str]]` | Build reverse call mapping (callee -> caller files). |
| `file_imports` | 85 | `dict[str, set[str]]` | Get imports for each file. |
| `analyze` | 103 | `dict[str, Any]` | Find files most tightly coupled to the given file.  Args:   ... |
| `_normalize_path` | 160 | `str` | Normalize file path for matching. |
| `_calculate_coupling` | 176 | `dict[str, Any]` | Calculate coupling score between two files.  Returns:     Di... |
| `_count_calls_between` | 240 | `int` | Count how many times functions in from_file call functions i... |
| `_has_import` | 268 | `bool` | Check if from_file imports from to_file. |
| `_count_shared_imports` | 288 | `int` | Count shared external imports between two files. |
| `_name_similarity` | 299 | `float` | Calculate naming similarity between files. |
| `_build_summary` | 333 | `str` | Build a human-readable summary. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, index_data: dict[str, Any]) -> None`

Initialize the coupling analyzer.

Args:
    index_data: The loaded index data.

##### `files_by_path(self: None) -> dict[str, dict[str, Any]]`

Get files indexed by path.

##### `call_graph(self: None) -> dict[str, Any]`

Get the call graph from the index.

##### `reverse_calls(self: None) -> dict[str, set[str]]`

Build reverse call mapping (callee -> caller files).

##### `file_imports(self: None) -> dict[str, set[str]]`

Get imports for each file.

##### `analyze(self: None, file_path: str, top_k: int) -> dict[str, Any]`

Find files most tightly coupled to the given file.

Args:
    file_path: Path to the file to analyze.
    top_k: Number of coupled files to return.

Returns:
    Dictionary with coupled files, scores, and reasons.

##### `_normalize_path(self: None, file_path: str) -> str`

Normalize file path for matching.

##### `_calculate_coupling(self: None, file_a: str, file_b: str) -> dict[str, Any]`

Calculate coupling score between two files.

Returns:
    Dict with total score, component scores, and reasons.

##### `_count_calls_between(self: None, from_file: str, to_file: str) -> int`

Count how many times functions in from_file call functions in to_file.

##### `_has_import(self: None, from_file: str, to_file: str) -> bool`

Check if from_file imports from to_file.

##### `_count_shared_imports(self: None, file_a: str, file_b: str) -> int`

Count shared external imports between two files.

##### `_name_similarity(self: None, file_a: str, file_b: str) -> float`

Calculate naming similarity between files.

##### `_build_summary(self: None, result: dict[str, Any]) -> str`

Build a human-readable summary.

</details>

---

### `coverage.py`

**Path:** `codebase_index/analyzers/coverage.py`  
**Lines:** 139

#### `class TestCoverageMapper`

*Defined at line 21*

**Description:**
> Map source files to their corresponding test files.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 24 | `-` | Initialize the test coverage mapper.  Args:     root: Projec... |
| `collect_test_files` | 35 | `None` | Collect all test files in the project.  Args:     exclude: E... |
| `map_source_to_test` | 55 | `dict[str, Any]` | Map source files to potential test files.  Args:     source_... |
| `_find_test_file` | 108 | `str | None` | Find a test file for a given source file.  Args:     source_... |
| `clear` | 136 | `None` | Clear collected test files. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path)`

Initialize the test coverage mapper.

Args:
    root: Project root directory.

##### `collect_test_files(self: None, exclude: list[str]) -> None`

Collect all test files in the project.

Args:
    exclude: Exclusion patterns.

##### `map_source_to_test(self: None, source_files: list[dict[str, Any]]) -> dict[str, Any]`

Map source files to potential test files.

Args:
    source_files: List of file info dictionaries.

Returns:
    Dictionary with covered files, uncovered files, test files, and coverage %.

##### `_find_test_file(self: None, source_path: str) -> str | None`

Find a test file for a given source file.

Args:
    source_path: Path to the source file.

Returns:
    Path to the test file, or None if not found.

##### `clear(self: None) -> None`

Clear collected test files.

</details>

---

### `impact.py`

**Path:** `codebase_index/analyzers/impact.py`  
**Lines:** 406

#### `class ImpactAnalyzer`

*Defined at line 22*

**Description:**
> Analyze the impact radius of file changes.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 25 | `None` | Initialize the impact analyzer.  Args:     index_data: The l... |
| `files_by_path` | 38 | `dict[str, dict[str, Any]]` | Get files indexed by path. |
| `call_graph` | 48 | `dict[str, Any]` | Get the call graph from the index. |
| `reverse_call_graph` | 55 | `dict[str, list[str]]` | Build reverse call graph (callee -> callers). |
| `analyze_file` | 67 | `dict[str, Any]` | Analyze the impact radius of changes to a file.  Args:     f... |
| `_find_file` | 132 | `dict[str, Any] | None` | Find file in index by exact or partial path match. |
| `_extract_symbols` | 149 | `list[dict[str, Any]]` | Extract function and class symbols from exports. |
| `_find_direct_callers` | 180 | `list[dict[str, Any]]` | Find functions that directly call symbols in this file. |
| `_find_transitive_callers` | 225 | `list[dict[str, Any]]` | Find functions that transitively depend on the file. |
| `_find_affected_tests` | 262 | `list[dict[str, Any]]` | Find tests that could be affected by changes. |
| `_find_affected_endpoints` | 335 | `list[dict[str, Any]]` | Find API endpoints that could be affected. |
| `_build_summary` | 378 | `str` | Build a human-readable summary. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, index_data: dict[str, Any]) -> None`

Initialize the impact analyzer.

Args:
    index_data: The loaded index data.

##### `files_by_path(self: None) -> dict[str, dict[str, Any]]`

Get files indexed by path.

##### `call_graph(self: None) -> dict[str, Any]`

Get the call graph from the index.

##### `reverse_call_graph(self: None) -> dict[str, list[str]]`

Build reverse call graph (callee -> callers).

##### `analyze_file(self: None, file_path: str) -> dict[str, Any]`

Analyze the impact radius of changes to a file.

Args:
    file_path: Path to the file to analyze.

Returns:
    Dictionary with:
    - file: The analyzed file path
    - symbols: Functions/classes defined in the file
    - direct_callers: Functions that directly call symbols in this file
    - transitive_callers: Functions that indirectly depend on this file
    - affected_tests: Test files/functions that could be affected
    - affected_endpoints: Endpoints that use symbols from this file
    - summary: Human-readable summary

##### `_find_file(self: None, file_path: str) -> dict[str, Any] | None`

Find file in index by exact or partial path match.

##### `_extract_symbols(self: None, file_path: str, exports: dict[str, Any]) -> list[dict[str, Any]]`

Extract function and class symbols from exports.

##### `_find_direct_callers(self: None, file_path: str, symbols: list[dict[str, Any]]) -> list[dict[str, Any]]`

Find functions that directly call symbols in this file.

##### `_find_transitive_callers(self: None, direct_callers: list[dict[str, Any]], depth: int) -> list[dict[str, Any]]`

Find functions that transitively depend on the file.

##### `_find_affected_tests(self: None, callers: list[dict[str, Any]], file_path: str) -> list[dict[str, Any]]`

Find tests that could be affected by changes.

##### `_find_affected_endpoints(self: None, file_path: str, symbols: list[dict[str, Any]], callers: list[dict[str, Any]]) -> list[dict[str, Any]]`

Find API endpoints that could be affected.

##### `_build_summary(self: None, result: dict[str, Any]) -> str`

Build a human-readable summary.

</details>

---

### `imports.py`

**Path:** `codebase_index/analyzers/imports.py`  
**Lines:** 162

#### `class ImportAggregator`

*Defined at line 43*

**Description:**
> Aggregate all imports across the codebase and detect missing/unused deps.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 46 | `None` | - |
| `add_imports` | 51 | `None` | Add imports from a file.  Args:     imports: List of import ... |
| `add_internal_module` | 70 | `None` | Register a module as internal to the project.  Args:     mod... |
| `analyze` | 80 | `dict[str, Any]` | Analyze imports against declared dependencies.  Args:     de... |
| `clear` | 158 | `None` | Clear all collected data. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

*No documentation*

##### `add_imports(self: None, imports: list[str], filepath: str) -> None`

Add imports from a file.

Args:
    imports: List of import module names.
    filepath: Path to the file containing these imports.

##### `add_internal_module(self: None, module_name: str) -> None`

Register a module as internal to the project.

Args:
    module_name: Name of the internal module.

##### `analyze(self: None, declared_deps: list[str]) -> dict[str, Any]`

Analyze imports against declared dependencies.

Args:
    declared_deps: List of declared package names from requirements.txt etc.

Returns:
    Dictionary with analysis results including missing and unused deps.

##### `clear(self: None) -> None`

Clear all collected data.

</details>

---

### `orphans.py`

**Path:** `codebase_index/analyzers/orphans.py`  
**Lines:** 203

#### `class OrphanedFileScanner`

*Defined at line 20*

**Description:**
> Detect Python files that are never imported anywhere.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 54 | `None` | - |
| `scan` | 59 | `dict[str, Any]` | Detect orphaned files.  Args:     root: Project root.     fi... |
| `_path_to_module` | 147 | `str` | Convert file path to Python module name. |
| `_is_excluded` | 154 | `bool` | Check if file matches excluded patterns. |
| `_is_entry_point` | 161 | `bool` | Check if file is an entry point. |
| `_is_imported` | 176 | `bool` | Check if a file/module is imported anywhere. |
| `clear` | 199 | `None` | Clear collected data. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

*No documentation*

##### `scan(self: None, root: Path, files: list[dict[str, Any]], exclude: list[str]) -> dict[str, Any]`

Detect orphaned files.

Args:
    root: Project root.
    files: List of file info dicts from main scan.
    exclude: Exclusion patterns.

Returns:
    Dictionary with orphaned files, entry points, and counts.

##### `_path_to_module(self: None, path: str) -> str`

Convert file path to Python module name.

##### `_is_excluded(self: None, filename: str) -> bool`

Check if file matches excluded patterns.

##### `_is_entry_point(self: None, path: str, filename: str) -> bool`

Check if file is an entry point.

##### `_is_imported(self: None, path: str, module_name: str | None) -> bool`

Check if a file/module is imported anywhere.

##### `clear(self: None) -> None`

Clear collected data.

</details>

---

### `schema_mapper.py`

**Path:** `codebase_index/analyzers/schema_mapper.py`  
**Lines:** 391

#### `class SchemaMapper`

*Defined at line 22*

**Description:**
> Map schemas to endpoints that use them.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 25 | `None` | Initialize the schema mapper.  Args:     index_data: The loa... |
| `_infer_root` | 39 | `Path` | Infer root directory from index metadata. |
| `schemas` | 46 | `list[dict[str, Any]]` | Get all schemas from the index. |
| `endpoints` | 53 | `list[dict[str, Any]]` | Get all endpoints from the index. |
| `files_by_path` | 62 | `dict[str, dict[str, Any]]` | Get files indexed by path. |
| `find_endpoints_for_schema` | 71 | `dict[str, Any]` | Find endpoints that use a given schema.  Args:     schema_na... |
| `_find_matching_schemas` | 141 | `list[dict[str, Any]]` | Find schemas matching the given name (supports fuzzy matchin... |
| `_scan_file_for_schema_usage` | 160 | `list[tuple[dict[str, Any], list[dict[str, Any]]]]` | Scan a source file to find schema usages in endpoints.  Retu... |
| `_extract_function_schema_info` | 212 | `dict[str, list[dict[str, Any]]]` | Extract schema usage info from functions using AST.  Returns... |
| `_get_node_source` | 281 | `str` | Get the source text for an AST node. |
| `_scan_lines_for_schema` | 301 | `list[dict[str, Any]]` | Fallback: scan lines around endpoint for schema references. ... |
| `_build_summary` | 354 | `str` | Build a human-readable summary. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, index_data: dict[str, Any], root: Path | None) -> None`

Initialize the schema mapper.

Args:
    index_data: The loaded index data.
    root: Root directory of the codebase (for file scanning).

##### `_infer_root(self: None) -> Path`

Infer root directory from index metadata.

##### `schemas(self: None) -> list[dict[str, Any]]`

Get all schemas from the index.

##### `endpoints(self: None) -> list[dict[str, Any]]`

Get all endpoints from the index.

##### `files_by_path(self: None) -> dict[str, dict[str, Any]]`

Get files indexed by path.

##### `find_endpoints_for_schema(self: None, schema_name: str) -> dict[str, Any]`

Find endpoints that use a given schema.

Args:
    schema_name: The schema name to search for (e.g., "AgentConfig",
                "CreateUserRequest"). Supports fuzzy matching.

Returns:
    Dictionary with:
    - schema: The queried schema name
    - matched_schemas: Schemas matching the query
    - endpoints: Endpoints using the schema
    - usages: Detailed usage info (request vs response)
    - summary: Human-readable summary

##### `_find_matching_schemas(self: None, schema_name: str) -> list[dict[str, Any]]`

Find schemas matching the given name (supports fuzzy matching).

##### `_scan_file_for_schema_usage(self: None, file_path: str, endpoints: list[dict[str, Any]], schema_names: set[str]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]`

Scan a source file to find schema usages in endpoints.

Returns:
    List of (endpoint, usages) tuples.

##### `_extract_function_schema_info(self: None, tree: ast.AST, content: str, schema_names: set[str]) -> dict[str, list[dict[str, Any]]]`

Extract schema usage info from functions using AST.

Returns:
    Dict mapping function name to list of schema usages.

##### `_get_node_source(self: None, lines: list[str], node: ast.AST) -> str`

Get the source text for an AST node.

##### `_scan_lines_for_schema(self: None, lines: list[str], endpoint_line: int, schema_names: set[str]) -> list[dict[str, Any]]`

Fallback: scan lines around endpoint for schema references.

Looks for patterns like:
- response_model=SchemaName
- param: SchemaName
- -> SchemaName

##### `_build_summary(self: None, result: dict[str, Any]) -> str`

Build a human-readable summary.

</details>

---

### `semantic.py`

**Path:** `codebase_index/analyzers/semantic.py`  
**Lines:** 480

#### `class SemanticSearcher`

*Defined at line 63*

**Description:**
> Semantic search over code using embeddings.

Embeds actual code bodies (not just names) using code-specific models
for better semantic matching.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 71 | `None` | Initialize semantic searcher.  Args:     model_key: Model ke... |
| `model` | 106 | `Any` | Lazy-load the embedding model. |
| `build_embeddings` | 116 | `dict[str, Any]` | Build embeddings for all symbols in the index.  Args:     in... |
| `_create_symbol_info` | 204 | `dict[str, Any]` | Create symbol info with code body for embedding. |
| `_extract_code_body` | 269 | `str` | Extract function/class body from source lines. |
| `load_embeddings` | 314 | `None` | Load pre-computed embeddings.  Args:     embedding_data: Emb... |
| `search` | 344 | `dict[str, Any]` | Search for code matching the query.  Args:     query: Natura... |
| `_cosine_similarity` | 401 | `Any` | Compute cosine similarity between query and all embeddings. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, model_key: str, cache_dir: Path | None) -> None`

Initialize semantic searcher.

Args:
    model_key: Model key from MODELS dict, or a HuggingFace model name.
    cache_dir: Directory to cache the model.

##### `model(self: None) -> Any`

Lazy-load the embedding model.

##### `build_embeddings(self: None, index_data: dict[str, Any], root: Path | None) -> dict[str, Any]`

Build embeddings for all symbols in the index.

Args:
    index_data: The codebase index data.
    root: Root directory to read source files from.

Returns:
    Dictionary with embeddings that can be stored in the index.

##### `_create_symbol_info(self: None, symbol: dict[str, Any], file_path: str, symbol_type: str, source_lines: list[str], class_name: str | None) -> dict[str, Any]`

Create symbol info with code body for embedding.

##### `_extract_code_body(self: None, lines: list[str], start_line: int, max_lines: int) -> str`

Extract function/class body from source lines.

##### `load_embeddings(self: None, embedding_data: dict[str, Any]) -> None`

Load pre-computed embeddings.

Args:
    embedding_data: Embedding data from index.

##### `search(self: None, query: str, top_k: int, min_score: float) -> dict[str, Any]`

Search for code matching the query.

Args:
    query: Natural language or code query
           (e.g., "retry logic with backoff" or "def retry")
    top_k: Number of results to return.
    min_score: Minimum similarity score (0-1).

Returns:
    Dictionary with search results.

##### `_cosine_similarity(self: None, query: Any, embeddings: Any) -> Any`

Compute cosine similarity between query and all embeddings.

</details>

#### `def build_embeddings(index_data: dict[str, Any], root: Path | None, model: str) -> dict[str, Any]`

*Defined at line 412*

Convenience function to build embeddings.

Args:
    index_data: The codebase index.
    root: Root directory for reading source files.
    model: Model key or HuggingFace model name.

Returns:
    Updated index with embeddings.

#### `def semantic_search(index_data: dict[str, Any], query: str, top_k: int, model: str | None) -> dict[str, Any]`

*Defined at line 437*

Convenience function for semantic search.

Args:
    index_data: Index with embeddings.
    query: Search query.
    top_k: Number of results.
    model: Model to use (should match what was used for embeddings).

Returns:
    Search results.

#### `def check_semantic_available() -> bool`

*Defined at line 473*

Check if semantic search dependencies are available.

#### `def list_models() -> dict[str, Any]`

*Defined at line 478*

List available embedding models.

---

### `staleness.py`

**Path:** `codebase_index/analyzers/staleness.py`  
**Lines:** 258

#### `class StalenessChecker`

*Defined at line 22*

**Description:**
> Check if an index file is stale compared to the codebase.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 25 | `None` | Initialize the staleness checker.  Args:     root: Root dire... |
| `check` | 36 | `dict[str, Any]` | Check if the index is stale.  Returns:     Dictionary with s... |
| `_get_git_changes_since` | 114 | `dict[str, list[str]] | None` | Get files changed in git since the given time.  Returns:    ... |
| `_get_modified_files_since` | 200 | `list[str]` | Fallback: check file modification times.  Args:     since: C... |
| `_build_summary` | 230 | `str` | Build a human-readable summary. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, root: Path, index_data: dict[str, Any]) -> None`

Initialize the staleness checker.

Args:
    root: Root directory of the codebase.
    index_data: The loaded index data.

##### `check(self: None) -> dict[str, Any]`

Check if the index is stale.

Returns:
    Dictionary with staleness information:
    - is_stale: bool
    - index_age_hours: float
    - changed_files: list of changed file paths
    - new_files: list of new file paths
    - deleted_files: list of deleted file paths
    - summary: human-readable summary

##### `_get_git_changes_since(self: None, since: datetime) -> dict[str, list[str]] | None`

Get files changed in git since the given time.

Returns:
    Dict with 'modified', 'added', 'deleted' lists, or None if not a git repo.

##### `_get_modified_files_since(self: None, since: datetime, indexed_files: set[str]) -> list[str]`

Fallback: check file modification times.

Args:
    since: Check for files modified after this time.
    indexed_files: Set of file paths in the index.

Returns:
    List of modified file paths.

##### `_build_summary(self: None, result: dict[str, Any]) -> str`

Build a human-readable summary.

</details>

---

### `summaries.py`

**Path:** `codebase_index/analyzers/summaries.py`  
**Lines:** 442

#### `class SummaryGenerator`

*Defined at line 82*

**Description:**
> Generate LLM summaries for code symbols.

Supports multiple providers (OpenRouter, Anthropic, OpenAI-compatible)
with caching based on code hash to avoid regenerating unchanged code.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 90 | `None` | Initialize the summary generator.  Args:     provider: Provi... |
| `_detect_provider` | 145 | `str | None` | Detect provider from available environment variables. |
| `client` | 156 | `Any` | Lazy-load the HTTP client. |
| `load_cache` | 162 | `None` | Load existing summary cache. |
| `generate_summaries` | 166 | `dict[str, Any]` | Generate summaries for all functions in the index.  Args:   ... |
| `_generate_symbol_summary` | 222 | `None` | Generate summary for a single symbol. |
| `_read_file` | 274 | `list[str]` | Read file content as lines. |
| `_extract_code` | 282 | `str` | Extract code snippet starting from a line. |
| `_call_llm` | 324 | `str` | Call the LLM to generate a summary. |
| `_call_anthropic` | 334 | `str` | Call Anthropic API directly. |
| `_call_openai_compatible` | 350 | `str` | Call OpenAI-compatible API (OpenRouter, OpenAI, etc.). |
| `_clean_summary` | 366 | `str` | Clean up common issues in generated summaries. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, provider: str | None, model: str | None, api_key: str | None, base_url: str | None) -> None`

Initialize the summary generator.

Args:
    provider: Provider name (openrouter, anthropic, openai) or auto-detect.
    model: Model name (provider-specific).
    api_key: API key (or use environment variable).
    base_url: Custom base URL for API.

##### `_detect_provider(self: None) -> str | None`

Detect provider from available environment variables.

##### `client(self: None) -> Any`

Lazy-load the HTTP client.

##### `load_cache(self: None, cache_data: dict[str, str]) -> None`

Load existing summary cache.

##### `generate_summaries(self: None, index_data: dict[str, Any], root: Path, force: bool) -> dict[str, Any]`

Generate summaries for all functions in the index.

Args:
    index_data: The codebase index data.
    root: Root directory of the codebase.
    force: If True, regenerate all summaries (ignore cache).

Returns:
    Dictionary with summary statistics and cache.

##### `_generate_symbol_summary(self: None, symbol: dict[str, Any], source_lines: list[str], language: str, force: bool, stats: dict[str, int], class_name: str | None) -> None`

Generate summary for a single symbol.

##### `_read_file(self: None, file_path: Path) -> list[str]`

Read file content as lines.

##### `_extract_code(self: None, lines: list[str], start_line: int, max_lines: int) -> str`

Extract code snippet starting from a line.

##### `_call_llm(self: None, code: str, language: str) -> str`

Call the LLM to generate a summary.

##### `_call_anthropic(self: None, prompt: str) -> str`

Call Anthropic API directly.

##### `_call_openai_compatible(self: None, prompt: str) -> str`

Call OpenAI-compatible API (OpenRouter, OpenAI, etc.).

##### `_clean_summary(self: None, summary: str) -> str`

Clean up common issues in generated summaries.

</details>

#### `def generate_summaries(index_data: dict[str, Any], root: Path, force: bool, provider: str | None, model: str | None, api_key: str | None) -> dict[str, Any]`

*Defined at line 379*

Convenience function to generate summaries.

Args:
    index_data: The codebase index.
    root: Root directory of the codebase.
    force: Regenerate all summaries.
    provider: API provider (openrouter, anthropic, openai).
    model: Model to use.
    api_key: API key (alternative to environment variable).

Returns:
    Updated index with summaries and cache.

#### `def check_summaries_available() -> bool`

*Defined at line 420*

Check if summary generation dependencies are available.

#### `def check_api_key() -> bool`

*Defined at line 425*

Check if any API key is configured.

#### `def get_available_provider() -> str | None`

*Defined at line 434*

Get the first available provider based on API keys.

---

### `test_mapper.py`

**Path:** `codebase_index/analyzers/test_mapper.py`  
**Lines:** 320

#### `class TestMapper`

*Defined at line 20*

**Description:**
> Map symbols to their tests.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 23 | `None` | Initialize the test mapper.  Args:     index_data: The loade... |
| `test_files` | 35 | `list[dict[str, Any]]` | Get all test files from the index. |
| `call_graph` | 58 | `dict[str, Any]` | Get the call graph from the index. |
| `find_tests_for` | 64 | `dict[str, Any]` | Find tests for a given symbol.  Args:     symbol: The symbol... |
| `_imports_symbol` | 134 | `bool` | Check if the imports contain the symbol. |
| `_calls_symbol` | 182 | `bool` | Check if the file calls the symbol based on call graph. |
| `_find_matching_test_functions` | 208 | `list[str]` | Find test functions that match naming conventions. |
| `_find_callers_in_tests` | 266 | `list[str]` | Find test functions that call the symbol. |
| `_build_summary` | 297 | `str` | Build a human-readable summary. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None, index_data: dict[str, Any]) -> None`

Initialize the test mapper.

Args:
    index_data: The loaded index data.

##### `test_files(self: None) -> list[dict[str, Any]]`

Get all test files from the index.

##### `call_graph(self: None) -> dict[str, Any]`

Get the call graph from the index.

##### `find_tests_for(self: None, symbol: str) -> dict[str, Any]`

Find tests for a given symbol.

Args:
    symbol: The symbol to find tests for (e.g., "AgentFactory.create",
           "my_function", "MyClass").

Returns:
    Dictionary with:
    - symbol: The queried symbol
    - tests: List of matching test info
    - test_files: List of test files that reference the symbol
    - coverage_estimate: Rough estimate of test coverage

##### `_imports_symbol(self: None, imports: dict[str, Any] | list[Any], symbol: str, class_name: str | None, method_name: str) -> bool`

Check if the imports contain the symbol.

##### `_calls_symbol(self: None, file_path: str, symbol: str, class_name: str | None, method_name: str) -> bool`

Check if the file calls the symbol based on call graph.

##### `_find_matching_test_functions(self: None, exports: dict[str, Any], class_name: str | None, method_name: str) -> list[str]`

Find test functions that match naming conventions.

##### `_find_callers_in_tests(self: None, symbol: str) -> list[str]`

Find test functions that call the symbol.

##### `_build_summary(self: None, result: dict[str, Any]) -> str`

Build a human-readable summary.

</details>

---

## Parsers

### `base.py`

**Path:** `codebase_index/parsers/base.py`  
**Lines:** 284

#### `class ParserRegistry`

*Defined at line 31*

**Description:**
> Registry for language parsers.

Manages parser classes and their file extension mappings.
Supports dynamic registration of custom parsers and config injection.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `register` | 44 | `Callable[[Type['BaseParser']], Type['BaseParser']]` | Decorator to register a parser class.  Args:     language: L... |
| `register_parser` | 70 | `None` | Register a parser class for a language.  Args:     language:... |
| `get_parser` | 95 | `tuple['BaseParser' | None, str | None]` | Get the appropriate parser for a file, configured with the g... |
| `_get_configured_parser` | 120 | `'BaseParser' | None` | Get or create a parser instance with the given config. |
| `get_parser_for_language` | 143 | `'BaseParser' | None` | Get parser by language name.  Args:     language: Language n... |
| `list_languages` | 161 | `list[str]` | Get list of registered languages. |
| `list_extensions` | 166 | `dict[str, str]` | Get mapping of extensions to languages. |
| `clear` | 171 | `None` | Clear all registered parsers. Useful for testing. |

<details>
<summary>Method Details</summary>

##### `register(cls: None, language: str, extensions: list[str]) -> Callable[[Type['BaseParser']], Type['BaseParser']]`

Decorator to register a parser class.

Args:
    language: Language name (e.g., "python", "rust").
    extensions: List of file extensions (e.g., [".py", ".pyw"]).

Returns:
    Decorator function.

Example:
    @ParserRegistry.register("python", [".py", ".pyw"])
    class PythonParser(BaseParser):
        ...

##### `register_parser(cls: None, language: str, extensions: list[str], parser_class: Type['BaseParser']) -> None`

Register a parser class for a language.

Args:
    language: Language name.
    extensions: List of file extensions.
    parser_class: Parser class (stored, instantiated on demand with config).

##### `get_parser(cls: None, filepath: Path, config: dict[str, Any] | None) -> tuple['BaseParser' | None, str | None]`

Get the appropriate parser for a file, configured with the given config.

Args:
    filepath: Path to the file.
    config: Configuration dictionary to pass to the parser.

Returns:
    Tuple of (parser instance, language name), or (None, None) if no parser.

##### `_get_configured_parser(cls: None, language: str, config: dict[str, Any] | None) -> 'BaseParser' | None`

Get or create a parser instance with the given config.

##### `get_parser_for_language(cls: None, language: str, config: dict[str, Any] | None) -> 'BaseParser' | None`

Get parser by language name.

Args:
    language: Language name.
    config: Configuration dictionary.

Returns:
    Parser instance or None.

##### `list_languages(cls: None) -> list[str]`

Get list of registered languages.

##### `list_extensions(cls: None) -> dict[str, str]`

Get mapping of extensions to languages.

##### `clear(cls: None) -> None`

Clear all registered parsers. Useful for testing.

</details>

#### `class BaseParser(ABC)`

*Defined at line 178*

**Description:**
> Abstract base class for language parsers.

Subclasses must implement the `scan` method to extract
structural information from source files.

The scan method should return a dictionary with language-specific
keys. Common keys include:
- classes: List of class definitions
- functions: List of function definitions
- imports: Dict with 'internal' and 'external' lists
- error: Error message if parsing failed

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 196 | `None` | Initialize the parser with empty config. |
| `configure` | 200 | `None` | Configure the parser with the given config.  Subclasses can ... |
| `scan` | 212 | `dict[str, Any]` | Scan a source file and extract structural information.  Args... |
| `scan_with_fallback` | 230 | `dict[str, Any]` | Scan with fallback to regex if AST parsing fails.  Override ... |
| `get_empty_result` | 244 | `dict[str, Any]` | Get an empty result structure for this parser.  Subclasses c... |
| `_match_patterns` | 256 | `list[dict[str, Any]]` | Match text against a list of config patterns.  Helper method... |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

Initialize the parser with empty config.

##### `configure(self: None, config: dict[str, Any]) -> None`

Configure the parser with the given config.

Subclasses can override to extract specific config values.

Args:
    config: Configuration dictionary.

##### `scan(self: None, filepath: Path) -> dict[str, Any]`

Scan a source file and extract structural information.

Args:
    filepath: Path to the source file.

Returns:
    Dictionary containing extracted information.
    Should include an 'error' key if parsing failed.

The returned dict structure varies by language but typically includes:
- classes: List of class info dicts
- functions: List of function info dicts
- imports: Dict with 'internal' and 'external' import lists

##### `scan_with_fallback(self: None, filepath: Path) -> dict[str, Any]`

Scan with fallback to regex if AST parsing fails.

Override this in subclasses that support regex fallback.

Args:
    filepath: Path to the source file.

Returns:
    Dictionary containing extracted information.

##### `get_empty_result(self: None) -> dict[str, Any]`

Get an empty result structure for this parser.

Subclasses can override to provide language-specific structure.

##### `_match_patterns(self: None, text: str, patterns: list[dict[str, Any]], pattern_key: str) -> list[dict[str, Any]]`

Match text against a list of config patterns.

Helper method for subclasses to use config-driven pattern matching.

Args:
    text: Text to match against.
    patterns: List of pattern dicts from config.
    pattern_key: Key in pattern dict containing the regex.

Returns:
    List of matching pattern dicts.

</details>

---

### `docker.py`

**Path:** `codebase_index/parsers/docker.py`  
**Lines:** 142

#### `class DockerParser(BaseParser)`

*Defined at line 22*

**Description:**
> Docker Compose parser using PyYAML.

Falls back to regex parsing if PyYAML is not available.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 31 | `dict[str, Any]` | Scan a docker-compose file.  Args:     filepath: Path to the... |
| `_scan_regex` | 97 | `dict[str, Any]` | Fallback regex scanning if YAML not available. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict[str, Any]`

Scan a docker-compose file.

Args:
    filepath: Path to the docker-compose file.

Returns:
    Dictionary with services, networks, and volumes.

##### `_scan_regex(self: None, filepath: Path) -> dict[str, Any]`

Fallback regex scanning if YAML not available.

</details>

#### `def _get_docker_parser(filepath: Path) -> tuple[DockerParser | None, str | None]`

*Defined at line 131*

Check if file is a docker-compose file.

---

### `python.py`

**Path:** `codebase_index/parsers/python.py`  
**Lines:** 617

#### `class PythonParser(BaseParser)`

*Defined at line 44*

**Description:**
> Python parser using the ast module for accurate extraction.

Falls back to regex parsing for files with syntax errors.
Supports configurable patterns for routes, models, and schemas.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 54 | `None` | Initialize the Python parser with default config. |
| `configure` | 63 | `None` | Configure the parser with patterns from config.  Args:     c... |
| `scan` | 99 | `dict[str, Any]` | Scan a Python file and extract structure using AST.  Args:  ... |
| `_process_class` | 149 | `None` | Process a class definition node. |
| `_process_function` | 244 | `None` | Process a top-level function definition node. |
| `_extract_route_info` | 284 | `dict[str, Any] | None` | Extract route information from a decorator. |
| `_get_name` | 319 | `str` | Get name from AST node. |
| `_get_decorator_name` | 329 | `str | None` | Extract decorator name. |
| `_matches_base_class` | 339 | `bool` | Check if any base class matches the pattern.  Uses exact mat... |
| `_extract_signature` | 361 | `dict[str, Any]` | Extract function signature (parameters and return type). |
| `_get_annotation` | 411 | `str | None` | Extract type annotation as string. |
| `_extract_calls` | 443 | `list[str]` | Extract all function/method calls from a function body.  Ret... |
| `_get_call_name` | 465 | `str | None` | Extract the name of a call target. |
| `_get_function_body_hash` | 481 | `str | None` | Generate a normalized hash of function body for duplicate de... |
| `_categorize_import` | 510 | `None` | Categorize import as internal or external. |
| `_scan_regex` | 533 | `dict[str, Any]` | Fallback regex-based scanning for files with syntax errors. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

Initialize the Python parser with default config.

##### `configure(self: None, config: dict[str, Any]) -> None`

Configure the parser with patterns from config.

Args:
    config: Configuration dictionary with routes, models, schemas sections.

##### `scan(self: None, filepath: Path) -> dict[str, Any]`

Scan a Python file and extract structure using AST.

Args:
    filepath: Path to the Python file.

Returns:
    Dictionary with classes, functions, imports, routes, models, schemas.

##### `_process_class(self: None, node: ast.ClassDef, result: dict[str, Any]) -> None`

Process a class definition node.

##### `_process_function(self: None, node: ast.FunctionDef | ast.AsyncFunctionDef, result: dict[str, Any]) -> None`

Process a top-level function definition node.

##### `_extract_route_info(self: None, decorator: ast.expr, func_name: str, line: int, pattern: dict[str, Any], match: re.Match) -> dict[str, Any] | None`

Extract route information from a decorator.

##### `_get_name(self: None, node: ast.expr) -> str`

Get name from AST node.

##### `_get_decorator_name(self: None, node: ast.expr) -> str | None`

Extract decorator name.

##### `_matches_base_class(self: None, bases: list[str], pattern: str) -> bool`

Check if any base class matches the pattern.

Uses exact matching for simple names, or suffix matching for dotted names.
E.g., pattern "Base" matches "Base" but not "BaseModel".
Pattern "models.Model" matches "models.Model" or "django.db.models.Model".

##### `_extract_signature(self: None, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]`

Extract function signature (parameters and return type).

##### `_get_annotation(self: None, node: ast.expr | None) -> str | None`

Extract type annotation as string.

##### `_extract_calls(self: None, node: ast.AST) -> list[str]`

Extract all function/method calls from a function body.

Returns raw call strings for analysis.

##### `_get_call_name(self: None, node: ast.expr) -> str | None`

Extract the name of a call target.

##### `_get_function_body_hash(self: None, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None`

Generate a normalized hash of function body for duplicate detection.

Uses AST structure for comparison, ignoring variable names.

##### `_categorize_import(self: None, module: str, imports: dict[str, list[str]]) -> None`

Categorize import as internal or external.

##### `_scan_regex(self: None, filepath: Path) -> dict[str, Any]`

Fallback regex-based scanning for files with syntax errors.

</details>

---

### `sql.py`

**Path:** `codebase_index/parsers/sql.py`  
**Lines:** 78

#### `class SQLParser(BaseParser)`

*Defined at line 21*

**Description:**
> SQL parser using regex patterns.

Extracts table definitions, indexes, and views.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 28 | `dict[str, Any]` | Scan a SQL file.  Args:     filepath: Path to the SQL file. ... |

<details>
<summary>Method Details</summary>

##### `scan(self: None, filepath: Path) -> dict[str, Any]`

Scan a SQL file.

Args:
    filepath: Path to the SQL file.

Returns:
    Dictionary with tables, indexes, and views.

</details>

---

### `typescript.py`

**Path:** `codebase_index/parsers/typescript.py`  
**Lines:** 190

#### `class TypeScriptParser(BaseParser)`

*Defined at line 23*

**Description:**
> TypeScript/React parser using regex patterns.

Extracts components, hooks, functions, types, interfaces, and imports.
Supports configurable internal import aliases.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `__init__` | 31 | `None` | Initialize with default config. |
| `configure` | 37 | `None` | Configure the parser.  Args:     config: Configuration dicti... |
| `scan` | 59 | `dict[str, Any]` | Scan a TypeScript/React file.  Args:     filepath: Path to t... |
| `_process_line` | 92 | `None` | Process a single line of code. |
| `_categorize_import` | 170 | `None` | Categorize import as internal or external. |

<details>
<summary>Method Details</summary>

##### `__init__(self: None) -> None`

Initialize with default config.

##### `configure(self: None, config: dict[str, Any]) -> None`

Configure the parser.

Args:
    config: Configuration dictionary.

##### `scan(self: None, filepath: Path) -> dict[str, Any]`

Scan a TypeScript/React file.

Args:
    filepath: Path to the TypeScript file.

Returns:
    Dictionary with components, hooks, functions, types, interfaces, imports.

##### `_process_line(self: None, line: str, line_num: int, result: dict[str, Any]) -> None`

Process a single line of code.

##### `_categorize_import(self: None, module: str, imports: dict[str, list[str]]) -> None`

Categorize import as internal or external.

</details>

---

## Scanners

### `alembic.py`

**Path:** `codebase_index/scanners/alembic.py`  
**Lines:** 141

#### `class AlembicScanner`

*Defined at line 20*

**Description:**
> Scan for Alembic database migrations.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 23 | `dict[str, Any]` | Scan for Alembic migrations.  Args:     root: Project root d... |
| `_scan_migrations` | 66 | `list[dict[str, Any]]` | Scan migration files. |
| `_parse_migration` | 80 | `dict[str, Any] | None` | Parse a single migration file. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict[str, Any]`

Scan for Alembic migrations.

Args:
    root: Project root directory.

Returns:
    Dictionary with migrations list, total count, and latest revision.

##### `_scan_migrations(self: None, migrations_dir: Path, root: Path) -> list[dict[str, Any]]`

Scan migration files.

##### `_parse_migration(self: None, filepath: Path, root: Path) -> dict[str, Any] | None`

Parse a single migration file.

</details>

---

### `dependencies.py`

**Path:** `codebase_index/scanners/dependencies.py`  
**Lines:** 155

#### `class DependenciesScanner`

*Defined at line 21*

**Description:**
> Scan for project dependencies from requirements.txt, package.json, etc.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 24 | `dict[str, Any]` | Scan for all dependency files.  Args:     root: Project root... |
| `_parse_requirements` | 70 | `list[str]` | Parse requirements.txt file.  Args:     filepath: Path to re... |
| `_parse_pyproject` | 96 | `list[str]` | Parse pyproject.toml for dependencies.  Args:     filepath: ... |
| `_parse_package_json` | 133 | `dict[str, list[str]]` | Parse package.json for dependencies.  Args:     filepath: Pa... |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path) -> dict[str, Any]`

Scan for all dependency files.

Args:
    root: Project root directory.

Returns:
    Dictionary with 'python' and 'node' dependency lists.

##### `_parse_requirements(self: None, filepath: Path) -> list[str]`

Parse requirements.txt file.

Args:
    filepath: Path to requirements.txt.

Returns:
    List of package names (without version specifiers).

##### `_parse_pyproject(self: None, filepath: Path) -> list[str]`

Parse pyproject.toml for dependencies.

Args:
    filepath: Path to pyproject.toml.

Returns:
    List of package names.

##### `_parse_package_json(self: None, filepath: Path) -> dict[str, list[str]]`

Parse package.json for dependencies.

Args:
    filepath: Path to package.json.

Returns:
    Dictionary with 'dependencies' and 'devDependencies' lists.

</details>

---

### `env.py`

**Path:** `codebase_index/scanners/env.py`  
**Lines:** 183

#### `class EnvScanner`

*Defined at line 24*

**Description:**
> Scan for environment variable usage (names only, no values).

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 27 | `dict[str, Any]` | Scan for environment variables.  Args:     root: Project roo... |
| `_parse_dotenv` | 79 | `list[str]` | Parse .env file for variable names (NOT values).  Args:     ... |
| `_scan_python_env` | 105 | `set[str]` | Scan Python file for environment variable access.  Args:    ... |
| `_scan_typescript_env` | 145 | `set[str]` | Scan TypeScript file for environment variable access.  Args:... |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str] | None) -> dict[str, Any]`

Scan for environment variables.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    Dictionary with dotenv files and usage in Python/TypeScript.

##### `_parse_dotenv(self: None, filepath: Path) -> list[str]`

Parse .env file for variable names (NOT values).

Args:
    filepath: Path to .env file.

Returns:
    List of variable names.

##### `_scan_python_env(self: None, filepath: Path) -> set[str]`

Scan Python file for environment variable access.

Args:
    filepath: Path to Python file.

Returns:
    Set of variable names accessed.

##### `_scan_typescript_env(self: None, filepath: Path) -> set[str]`

Scan TypeScript file for environment variable access.

Args:
    filepath: Path to TypeScript file.

Returns:
    Set of variable names accessed.

</details>

---

### `http_calls.py`

**Path:** `codebase_index/scanners/http_calls.py`  
**Lines:** 165

#### `class HttpCallsScanner`

*Defined at line 22*

**Description:**
> Scan for external HTTP calls (httpx, requests, aiohttp, fetch).

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 48 | `dict[str, Any]` | Scan for external HTTP calls.  Args:     root: Project root ... |
| `_scan_python_file` | 97 | `list[dict[str, Any]]` | Scan a Python file for HTTP calls. |
| `_scan_ts_file` | 131 | `list[dict[str, Any]]` | Scan a TypeScript file for HTTP calls. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str]) -> dict[str, Any]`

Scan for external HTTP calls.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    Dictionary with Python and TypeScript calls, totals, and unique domains.

##### `_scan_python_file(self: None, filepath: Path, root: Path) -> list[dict[str, Any]]`

Scan a Python file for HTTP calls.

##### `_scan_ts_file(self: None, filepath: Path, root: Path) -> list[dict[str, Any]]`

Scan a TypeScript file for HTTP calls.

</details>

---

### `middleware.py`

**Path:** `codebase_index/scanners/middleware.py`  
**Lines:** 109

#### `class MiddlewareScanner`

*Defined at line 22*

**Description:**
> Scan for FastAPI/Starlette middleware configuration.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 36 | `dict[str, Any]` | Scan for middleware usage.  Args:     root: Project root dir... |
| `_scan_file` | 61 | `dict[str, list[dict[str, Any]]]` | Scan a file for middleware. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str]) -> dict[str, Any]`

Scan for middleware usage.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    Dictionary with standard and custom middleware lists.

##### `_scan_file(self: None, filepath: Path, root: Path) -> dict[str, list[dict[str, Any]]]`

Scan a file for middleware.

</details>

---

### `routes.py`

**Path:** `codebase_index/scanners/routes.py`  
**Lines:** 94

#### `class RoutePrefixScanner`

*Defined at line 23*

**Description:**
> Scan FastAPI main.py for router prefixes to build full paths.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 26 | `dict[str, str]` | Scan for include_router calls to extract prefixes.  Args:   ... |
| `_scan_main_file` | 51 | `dict[str, str]` | Scan a main.py file for include_router calls.  Args:     fil... |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str] | None) -> dict[str, str]`

Scan for include_router calls to extract prefixes.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    Dictionary mapping router names to their prefixes.

##### `_scan_main_file(self: None, filepath: Path) -> dict[str, str]`

Scan a main.py file for include_router calls.

Args:
    filepath: Path to the main.py file.

Returns:
    Dictionary mapping router names to prefixes.

</details>

---

### `todo.py`

**Path:** `codebase_index/scanners/todo.py`  
**Lines:** 95

#### `class TodoScanner`

*Defined at line 22*

**Description:**
> Scan for TODO, FIXME, HACK, XXX comments.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 41 | `list[dict[str, Any]]` | Scan all files for TODO/FIXME comments.  Args:     root: Pro... |
| `_scan_file` | 63 | `list[dict[str, Any]]` | Scan a single file for TODOs.  Args:     filepath: Path to t... |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str]) -> list[dict[str, Any]]`

Scan all files for TODO/FIXME comments.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    List of todo items with type, message, file, and line.

##### `_scan_file(self: None, filepath: Path, root: Path) -> list[dict[str, Any]]`

Scan a single file for TODOs.

Args:
    filepath: Path to the file.
    root: Project root for relative path calculation.

Returns:
    List of todo items from this file.

</details>

---

### `websocket.py`

**Path:** `codebase_index/scanners/websocket.py`  
**Lines:** 98

#### `class WebSocketScanner`

*Defined at line 22*

**Description:**
> Scan for WebSocket endpoints.

**Methods:**

| Method | Line | Returns | Description |
|--------|------|---------|-------------|
| `scan` | 25 | `dict[str, Any]` | Scan for WebSocket endpoints.  Args:     root: Project root ... |
| `_scan_file` | 50 | `list[dict[str, Any]]` | Scan a file for WebSocket endpoints. |

<details>
<summary>Method Details</summary>

##### `scan(self: None, root: Path, exclude: list[str]) -> dict[str, Any]`

Scan for WebSocket endpoints.

Args:
    root: Project root directory.
    exclude: Exclusion patterns.

Returns:
    Dictionary with endpoint list and total count.

##### `_scan_file(self: None, filepath: Path, root: Path) -> list[dict[str, Any]]`

Scan a file for WebSocket endpoints.

</details>

---

## Call Graph

Top functions by number of outgoing calls:

| Function | File | Calls |
|----------|------|-------|
| `main` | `cli.py` | 51 |
| `CodebaseScanner.scan` | `codebase_index.py` | 46 |
| `main` | `codebase_index.py` | 32 |
| `ImportAggregator.analyze` | `codebase_index.py` | 24 |
| `ImportAggregator.analyze` | `imports.py` | 23 |
| `CodebaseScanner.scan` | `scanner.py` | 22 |
| `PythonScanner.scan` | `codebase_index.py` | 21 |
| `CodebaseScanner.__init__` | `scanner.py` | 20 |
| `CodebaseScanner.__init__` | `codebase_index.py` | 19 |
| `OrphanedFileScanner.scan` | `codebase_index.py` | 18 |
| `OrphanedFileScanner.scan` | `orphans.py` | 18 |
| `TypeScriptScanner.scan` | `codebase_index.py` | 17 |
| `scan_codebase` | `cli.py` | 17 |
| `ImpactAnalyzer._find_affected_tests` | `impact.py` | 17 |
| `WebSocketScanner._scan_file` | `codebase_index.py` | 16 |
| `WebSocketScanner._scan_file` | `websocket.py` | 16 |
| `DockerParser.scan` | `docker.py` | 15 |
| `PythonParser._scan_regex` | `python.py` | 15 |
| `StalenessChecker.check` | `staleness.py` | 15 |
| `SemanticSearcher.build_embeddings` | `semantic.py` | 15 |

---

## Configuration

Default config patterns are defined in `config.py`. Key sections:

- **Routes:** FastAPI/Flask/Django endpoint patterns
- **Models:** SQLAlchemy/Django ORM detection
- **Schemas:** Pydantic/serializer detection
- **Auth:** Authentication decorator/parameter patterns
- **Exclude:** Default directory/file exclusions

Generate a config template with:
```bash
codebase-index --init-config > codebase_index.yaml
```
