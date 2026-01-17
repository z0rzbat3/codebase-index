# Codebase-Index: Full API Documentation

> Auto-generated using codebase-index on itself

## `codebase_index.py`

### `def get_config_template() -> str`
*Line 264*

Generate a well-documented YAML config template for LLMs to customize.

### `def load_config(config_path: Path) -> dict`
*Line 460*

Load configuration from YAML file, merged with defaults.

### `def get_file_hash(filepath: Path) -> str`
*Line 489*

Generate SHA256 hash of file contents.

### `def count_lines(filepath: Path) -> int`
*Line 498*

Count lines in a file.

### `def get_git_info(root: Path) -> dict`
*Line 507*

Get git metadata.

### `def categorize_file(filepath: str, categories: dict) -> str`
*Line 535*

Categorize a file based on path patterns.

### `def should_exclude(path: Path, exclude_patterns: list) -> bool`
*Line 543*

Check if path should be excluded.

### `def cg_query_function(call_graph: dict, func_name: str) -> dict`
*Line 2923*

Query what a specific function calls (fuzzy match).

### `def cg_query_file(call_graph: dict, file_path: str) -> dict`
*Line 2942*

Query all functions in a specific file.

### `def cg_query_callers(call_graph: dict, func_name: str) -> dict`
*Line 2959*

Query what functions call a specific function (inverse lookup).

### `def main()`
*Line 2989*

*No documentation*

### `class DependenciesScanner`
*Line 559*

Scan for project dependencies from requirements.txt, package.json, etc.

**Methods:**

- `scan(root) -> dict` (line 562)
  Scan for all dependency files.
- `_parse_requirements(filepath) -> list` (line 596)
  Parse requirements.txt file.
- `_parse_pyproject(filepath) -> list` (line 614)
  Parse pyproject.toml for dependencies.
- `_parse_package_json(filepath) -> dict` (line 632)
  Parse package.json for dependencies.

### `class EnvScanner`
*Line 650*

Scan for environment variable usage (names only, no values).

**Methods:**

- `scan(root) -> dict` (line 653)
  Scan for environment variables.
- `_parse_dotenv(filepath) -> list` (line 693)
  Parse .env file for variable names (NOT values).
- `_scan_python_env(filepath) -> set` (line 711)
  Scan Python file for environment variable access.
- `_scan_typescript_env(filepath) -> set` (line 734)
  Scan TypeScript file for environment variable access.

### `class TodoScanner`
*Line 762*

Scan for TODO, FIXME, HACK, XXX comments.

**Methods:**

- `scan(root, exclude) -> list` (line 771)
  Scan all files for TODO/FIXME comments.
- `_scan_file(filepath, root) -> list` (line 785)
  Scan a single file for TODOs.

### `class RoutePrefixScanner`
*Line 815*

Scan FastAPI main.py for router prefixes to build full paths.

**Methods:**

- `scan(root) -> dict` (line 818)
  Scan for include_router calls to extract prefixes.
- `_scan_main_file(filepath) -> dict` (line 833)
  Scan a main.py file for include_router calls.

### `class ImportAggregator`
*Line 907*

Aggregate all imports across the codebase and detect missing/unused deps.

**Methods:**

- `__init__()` (line 910)
- `add_imports(imports, filepath)` (line 915)
  Add imports from a file.
- `add_internal_module(module_name)` (line 928)
  Register a module as internal to the project.
- `analyze(declared_deps) -> dict` (line 933)
  Analyze imports against declared dependencies.  Returns:     dict with missing_d...

### `class AuthScanner`
*Line 1040*

Scan for authentication requirements per endpoint.

**Methods:**

- `scan_file(filepath, routes) -> list` (line 1056)
  Scan a file and annotate routes with auth requirements.
- `_check_auth_around_line(lines, line_num) -> str` (line 1086)
  Check for auth patterns around a specific line.

### `class TestCoverageMapper`
*Line 1105*

Map source files to their corresponding test files.

**Methods:**

- `__init__(root)` (line 1108)
- `collect_test_files(exclude)` (line 1113)
  Collect all test files in the project.
- `map_source_to_test(source_files) -> dict` (line 1128)
  Map source files to potential test files.
- `_find_test_file(source_path) -> str` (line 1173)
  Find a test file for a given source file.

### `class HttpCallsScanner`
*Line 1208*

Scan for external HTTP calls (httpx, requests, aiohttp, fetch).

**Methods:**

- `scan(root, exclude) -> dict` (line 1234)
  Scan for external HTTP calls.
- `_scan_python_file(filepath, root) -> list` (line 1271)
  Scan a Python file for HTTP calls.
- `_scan_ts_file(filepath, root) -> list` (line 1306)
  Scan a TypeScript file for HTTP calls.
- `_extract_domain(url) -> str` (line 1343)
  Extract domain from URL.

### `class ComplexityAnalyzer`
*Line 1363*

Analyze code complexity and flag large files/functions.

**Methods:**

- `analyze(files) -> dict` (line 1374)
  Analyze all files for complexity issues.

### `class MiddlewareScanner`
*Line 1444*

Scan for FastAPI/Starlette middleware configuration.

**Methods:**

- `scan(root, exclude) -> dict` (line 1458)
  Scan for middleware usage.
- `_scan_file(filepath, root) -> dict` (line 1475)
  Scan a file for middleware.

### `class WebSocketScanner`
*Line 1528*

Scan for WebSocket endpoints.

**Methods:**

- `scan(root, exclude) -> dict` (line 1531)
  Scan for WebSocket endpoints.
- `_scan_file(filepath, root) -> list` (line 1547)
  Scan a file for WebSocket endpoints.

### `class AlembicScanner`
*Line 1603*

Scan for Alembic database migrations.

**Methods:**

- `scan(root) -> dict` (line 1606)
  Scan for Alembic migrations.
- `_scan_migrations(migrations_dir, root) -> list` (line 1641)
  Scan migration files.
- `_parse_migration(filepath, root) -> dict` (line 1655)
  Parse a single migration file.

### `class OrphanedFileScanner`
*Line 1722*

Detect Python files that are never imported anywhere.

**Methods:**

- `__init__()` (line 1756)
- `scan(root, files, exclude) -> dict` (line 1761)
  Detect orphaned files.  Args:     root: Project root     files: List of file inf...
- `_path_to_module(path) -> str` (line 1842)
  Convert file path to Python module name.
- `_is_excluded(filename) -> bool` (line 1851)
  Check if file matches excluded patterns.
- `_is_entry_point(path, filename) -> bool` (line 1858)
  Check if file is an entry point.
- `_is_imported(path, module_name) -> bool` (line 1873)
  Check if a file/module is imported anywhere.

### `class PythonScanner`
*Line 1904*

Scan Python files using AST for accurate extraction.

**Methods:**

- `scan(filepath) -> dict` (line 1907)
  Scan a Python file and extract structure.
- `_get_name(node) -> str` (line 2009)
  Get name from AST node.
- `_get_decorator_name(node) -> str` (line 2019)
  Extract decorator name.
- `_extract_signature(node) -> dict` (line 2029)
  Extract function signature (parameters and return type).
- `_get_annotation(node) -> str` (line 2082)
  Extract type annotation as string.
- `_extract_calls(node) -> list` (line 2110)
  Extract all function/method calls from a function body. Returns raw call strings...
- `_get_call_name(node) -> str` (line 2130)
  Extract the name of a call target.
- `_get_function_body_hash(node) -> str` (line 2150)
  Generate a normalized hash of function body for duplicate detection. Normalizes ...
- `_extract_route_info(decorator, func_name, line) -> dict` (line 2176)
  Extract FastAPI route information from decorator.
- `_categorize_import(module, imports)` (line 2203)
  Categorize import as internal or external.
- `_scan_regex(filepath) -> dict` (line 2223)
  Fallback regex-based scanning for files with syntax errors.

### `class TypeScriptScanner`
*Line 2278*

Scan TypeScript/React files using regex patterns.

**Methods:**

- `scan(filepath) -> dict` (line 2281)
  Scan a TypeScript/React file.

### `class SQLScanner`
*Line 2365*

Scan SQL files for table definitions.

**Methods:**

- `scan(filepath) -> dict` (line 2368)
  Scan a SQL file.

### `class DockerScanner`
*Line 2401*

Scan Docker Compose files.

**Methods:**

- `scan(filepath) -> dict` (line 2404)
  Scan a docker-compose file.
- `_scan_regex(filepath) -> dict` (line 2447)
  Fallback regex scanning if YAML not available.

### `class CodebaseScanner`
*Line 2477*

Main scanner that orchestrates all language-specific scanners.

**Methods:**

- `__init__(root, exclude, exclude_extensions, include_hash)` (line 2480)
- `scan() -> dict` (line 2511)
  Scan the entire codebase.
- `_truncate_docstring(docstring, max_length) -> str` (line 2812)
  Truncate docstring to first line or max length.
- `_build_meta() -> dict` (line 2822)
  Build metadata section.
- `_walk_files()` (line 2836)
  Walk directory and yield files to scan.
- `_scan_file(filepath) -> dict` (line 2847)
  Scan a single file.
- `_update_summary(summary, file_info)` (line 2902)
  Update summary statistics.

---

## `codebase_index/analyzers/auth.py`

### `def check_endpoint_auth(signature: str, decorators: list[str] | None, config: dict[str, Any] | None) -> dict[str, Any]`
*Line 353*

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



### `class AuthScanner`
*Line 64*

Scan for authentication requirements per endpoint.

Uses precise function signature parsing instead of broad context matching.
Config-driven for easy customization.

**Methods:**

- `__init__() -> None` (line 72)
  Initialize with default auth patterns.
- `_compile_patterns(patterns) -> None` (line 78)
  Compile regex patterns for efficient matching.
- `configure(config) -> None` (line 95)
  Configure the scanner with auth patterns from config.  Config format: ```yaml au...
- `scan_file(filepath, routes) -> list[dict[str, Any]]` (line 142)
  Scan a file and annotate routes with auth requirements.  Args:     filepath: Pat...
- `_extract_function_signatures_ast(content) -> dict[str, dict[str, Any]]` (line 191)
  Extract function signatures using AST for precise parameter analysis.  Returns: ...
- `_get_signature_text(content, node) -> str` (line 223)
  Extract the raw function signature text.
- `_get_decorator_text(content, node) -> str` (line 242)
  Extract decorator text above the function.
- `_detect_auth(handler, route_line, lines, function_signatures) -> str | None` (line 259)
  Detect auth requirement using multiple strategies.  Strategy 1: AST-based signat...
- `_detect_auth_from_lines(handler, route_line, lines) -> str | None` (line 296)
  Fallback: detect auth by extracting function signature from lines.  Only looks a...

---

## `codebase_index/analyzers/complexity.py`

### `class ComplexityAnalyzer`
*Line 18*

Analyze code complexity and flag large files/functions.

**Methods:**

- `__init__(file_lines_warning, file_lines_critical, function_lines_warning, function_lines_critical, class_methods_warning, class_methods_critical)` (line 21)
  Initialize the complexity analyzer.  Args:     file_lines_warning: Lines thresho...
- `analyze(files) -> dict[str, Any]` (line 48)
  Analyze all files for complexity issues.  Args:     files: List of file info dic...
- `_analyze_file(file_info, result) -> None` (line 75)
  Analyze a single file for complexity.

---

## `codebase_index/analyzers/coupling.py`

### `class CouplingAnalyzer`
*Line 21*

Analyze coupling between files to identify tightly related code.

Coupling score is computed from:
- Call frequency: How often functions in A call functions in B
- Import dependency: Direct imports between files
- Shared imports: Common external dependencies
- Naming similarity: Similar file/functio

**Methods:**

- `__init__(index_data) -> None` (line 41)
  Initialize the coupling analyzer.  Args:     index_data: The loaded index data.
- `files_by_path() -> dict[str, dict[str, Any]]` (line 55)
  Get files indexed by path.
- `call_graph() -> dict[str, Any]` (line 65)
  Get the call graph from the index.
- `reverse_calls() -> dict[str, set[str]]` (line 72)
  Build reverse call mapping (callee -> caller files).
- `file_imports() -> dict[str, set[str]]` (line 85)
  Get imports for each file.
- `analyze(file_path, top_k) -> dict[str, Any]` (line 103)
  Find files most tightly coupled to the given file.  Args:     file_path: Path to...
- `_normalize_path(file_path) -> str` (line 160)
  Normalize file path for matching.
- `_calculate_coupling(file_a, file_b) -> dict[str, Any]` (line 176)
  Calculate coupling score between two files.  Returns:     Dict with total score,...
- `_count_calls_between(from_file, to_file) -> int` (line 240)
  Count how many times functions in from_file call functions in to_file.
- `_has_import(from_file, to_file) -> bool` (line 268)
  Check if from_file imports from to_file.
- `_count_shared_imports(file_a, file_b) -> int` (line 288)
  Count shared external imports between two files.
- `_name_similarity(file_a, file_b) -> float` (line 299)
  Calculate naming similarity between files.
- `_build_summary(result) -> str` (line 333)
  Build a human-readable summary.

---

## `codebase_index/analyzers/coverage.py`

### `class TestCoverageMapper`
*Line 21*

Map source files to their corresponding test files.

**Methods:**

- `__init__(root)` (line 24)
  Initialize the test coverage mapper.  Args:     root: Project root directory.
- `collect_test_files(exclude) -> None` (line 35)
  Collect all test files in the project.  Args:     exclude: Exclusion patterns.
- `map_source_to_test(source_files) -> dict[str, Any]` (line 55)
  Map source files to potential test files.  Args:     source_files: List of file ...
- `_find_test_file(source_path) -> str | None` (line 108)
  Find a test file for a given source file.  Args:     source_path: Path to the so...
- `clear() -> None` (line 136)
  Clear collected test files.

---

## `codebase_index/analyzers/impact.py`

### `class ImpactAnalyzer`
*Line 22*

Analyze the impact radius of file changes.

**Methods:**

- `__init__(index_data) -> None` (line 25)
  Initialize the impact analyzer.  Args:     index_data: The loaded index data.
- `files_by_path() -> dict[str, dict[str, Any]]` (line 38)
  Get files indexed by path.
- `call_graph() -> dict[str, Any]` (line 48)
  Get the call graph from the index.
- `reverse_call_graph() -> dict[str, list[str]]` (line 55)
  Build reverse call graph (callee -> callers).
- `analyze_file(file_path) -> dict[str, Any]` (line 67)
  Analyze the impact radius of changes to a file.  Args:     file_path: Path to th...
- `_find_file(file_path) -> dict[str, Any] | None` (line 132)
  Find file in index by exact or partial path match.
- `_extract_symbols(file_path, exports) -> list[dict[str, Any]]` (line 149)
  Extract function and class symbols from exports.
- `_find_direct_callers(file_path, symbols) -> list[dict[str, Any]]` (line 180)
  Find functions that directly call symbols in this file.
- `_find_transitive_callers(direct_callers, depth) -> list[dict[str, Any]]` (line 225)
  Find functions that transitively depend on the file.
- `_find_affected_tests(callers, file_path) -> list[dict[str, Any]]` (line 262)
  Find tests that could be affected by changes.
- `_find_affected_endpoints(file_path, symbols, callers) -> list[dict[str, Any]]` (line 335)
  Find API endpoints that could be affected.
- `_build_summary(result) -> str` (line 378)
  Build a human-readable summary.

---

## `codebase_index/analyzers/imports.py`

### `class ImportAggregator`
*Line 43*

Aggregate all imports across the codebase and detect missing/unused deps.

**Methods:**

- `__init__() -> None` (line 46)
- `add_imports(imports, filepath) -> None` (line 51)
  Add imports from a file.  Args:     imports: List of import module names.     fi...
- `add_internal_module(module_name) -> None` (line 70)
  Register a module as internal to the project.  Args:     module_name: Name of th...
- `analyze(declared_deps) -> dict[str, Any]` (line 80)
  Analyze imports against declared dependencies.  Args:     declared_deps: List of...
- `clear() -> None` (line 158)
  Clear all collected data.

---

## `codebase_index/analyzers/orphans.py`

### `class OrphanedFileScanner`
*Line 20*

Detect Python files that are never imported anywhere.

**Methods:**

- `__init__() -> None` (line 54)
- `scan(root, files, exclude) -> dict[str, Any]` (line 59)
  Detect orphaned files.  Args:     root: Project root.     files: List of file in...
- `_path_to_module(path) -> str` (line 147)
  Convert file path to Python module name.
- `_is_excluded(filename) -> bool` (line 154)
  Check if file matches excluded patterns.
- `_is_entry_point(path, filename) -> bool` (line 161)
  Check if file is an entry point.
- `_is_imported(path, module_name) -> bool` (line 176)
  Check if a file/module is imported anywhere.
- `clear() -> None` (line 199)
  Clear collected data.

---

## `codebase_index/analyzers/schema_mapper.py`

### `class SchemaMapper`
*Line 22*

Map schemas to endpoints that use them.

**Methods:**

- `__init__(index_data, root) -> None` (line 25)
  Initialize the schema mapper.  Args:     index_data: The loaded index data.     ...
- `_infer_root() -> Path` (line 39)
  Infer root directory from index metadata.
- `schemas() -> list[dict[str, Any]]` (line 46)
  Get all schemas from the index.
- `endpoints() -> list[dict[str, Any]]` (line 53)
  Get all endpoints from the index.
- `files_by_path() -> dict[str, dict[str, Any]]` (line 62)
  Get files indexed by path.
- `find_endpoints_for_schema(schema_name) -> dict[str, Any]` (line 71)
  Find endpoints that use a given schema.  Args:     schema_name: The schema name ...
- `_find_matching_schemas(schema_name) -> list[dict[str, Any]]` (line 141)
  Find schemas matching the given name (supports fuzzy matching).
- `_scan_file_for_schema_usage(file_path, endpoints, schema_names) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]` (line 160)
  Scan a source file to find schema usages in endpoints.  Returns:     List of (en...
- `_extract_function_schema_info(tree, content, schema_names) -> dict[str, list[dict[str, Any]]]` (line 212)
  Extract schema usage info from functions using AST.  Returns:     Dict mapping f...
- `_get_node_source(lines, node) -> str` (line 281)
  Get the source text for an AST node.
- `_scan_lines_for_schema(lines, endpoint_line, schema_names) -> list[dict[str, Any]]` (line 301)
  Fallback: scan lines around endpoint for schema references.  Looks for patterns ...
- `_build_summary(result) -> str` (line 354)
  Build a human-readable summary.

---

## `codebase_index/analyzers/semantic.py`

### `def build_embeddings(index_data: dict[str, Any], root: Path | None, model: str) -> dict[str, Any]`
*Line 412*

Convenience function to build embeddings.

Args:
    index_data: The codebase index.
    root: Root directory for reading source files.
    model: Model key or HuggingFace model name.

Returns:
    Updated index with embeddings.

### `def semantic_search(index_data: dict[str, Any], query: str, top_k: int, model: str | None) -> dict[str, Any]`
*Line 437*

Convenience function for semantic search.

Args:
    index_data: Index with embeddings.
    query: Search query.
    top_k: Number of results.
    model: Model to use (should match what was used for embeddings).

Returns:
    Search results.

### `def check_semantic_available() -> bool`
*Line 473*

Check if semantic search dependencies are available.

### `def list_models() -> dict[str, Any]`
*Line 478*

List available embedding models.

### `class SemanticSearcher`
*Line 63*

Semantic search over code using embeddings.

Embeds actual code bodies (not just names) using code-specific models
for better semantic matching.

**Methods:**

- `__init__(model_key, cache_dir) -> None` (line 71)
  Initialize semantic searcher.  Args:     model_key: Model key from MODELS dict, ...
- `model() -> Any` (line 106)
  Lazy-load the embedding model.
- `build_embeddings(index_data, root) -> dict[str, Any]` (line 116)
  Build embeddings for all symbols in the index.  Args:     index_data: The codeba...
- `_create_symbol_info(symbol, file_path, symbol_type, source_lines, class_name) -> dict[str, Any]` (line 204)
  Create symbol info with code body for embedding.
- `_extract_code_body(lines, start_line, max_lines) -> str` (line 269)
  Extract function/class body from source lines.
- `load_embeddings(embedding_data) -> None` (line 314)
  Load pre-computed embeddings.  Args:     embedding_data: Embedding data from ind...
- `search(query, top_k, min_score) -> dict[str, Any]` (line 344)
  Search for code matching the query.  Args:     query: Natural language or code q...
- `_cosine_similarity(query, embeddings) -> Any` (line 401)
  Compute cosine similarity between query and all embeddings.

---

## `codebase_index/analyzers/staleness.py`

### `class StalenessChecker`
*Line 22*

Check if an index file is stale compared to the codebase.

**Methods:**

- `__init__(root, index_data) -> None` (line 25)
  Initialize the staleness checker.  Args:     root: Root directory of the codebas...
- `check() -> dict[str, Any]` (line 36)
  Check if the index is stale.  Returns:     Dictionary with staleness information...
- `_get_git_changes_since(since) -> dict[str, list[str]] | None` (line 114)
  Get files changed in git since the given time.  Returns:     Dict with 'modified...
- `_get_modified_files_since(since, indexed_files) -> list[str]` (line 200)
  Fallback: check file modification times.  Args:     since: Check for files modif...
- `_build_summary(result) -> str` (line 230)
  Build a human-readable summary.

---

## `codebase_index/analyzers/summaries.py`

### `def generate_summaries(index_data: dict[str, Any], root: Path, force: bool, provider: str | None, model: str | None, api_key: str | None) -> dict[str, Any]`
*Line 379*

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

### `def check_summaries_available() -> bool`
*Line 420*

Check if summary generation dependencies are available.

### `def check_api_key() -> bool`
*Line 425*

Check if any API key is configured.

### `def get_available_provider() -> str | None`
*Line 434*

Get the first available provider based on API keys.

### `class SummaryGenerator`
*Line 82*

Generate LLM summaries for code symbols.

Supports multiple providers (OpenRouter, Anthropic, OpenAI-compatible)
with caching based on code hash to avoid regenerating unchanged code.

**Methods:**

- `__init__(provider, model, api_key, base_url) -> None` (line 90)
  Initialize the summary generator.  Args:     provider: Provider name (openrouter...
- `_detect_provider() -> str | None` (line 145)
  Detect provider from available environment variables.
- `client() -> Any` (line 156)
  Lazy-load the HTTP client.
- `load_cache(cache_data) -> None` (line 162)
  Load existing summary cache.
- `generate_summaries(index_data, root, force) -> dict[str, Any]` (line 166)
  Generate summaries for all functions in the index.  Args:     index_data: The co...
- `_generate_symbol_summary(symbol, source_lines, language, force, stats, class_name) -> None` (line 222)
  Generate summary for a single symbol.
- `_read_file(file_path) -> list[str]` (line 274)
  Read file content as lines.
- `_extract_code(lines, start_line, max_lines) -> str` (line 282)
  Extract code snippet starting from a line.
- `_call_llm(code, language) -> str` (line 324)
  Call the LLM to generate a summary.
- `_call_anthropic(prompt) -> str` (line 334)
  Call Anthropic API directly.
- `_call_openai_compatible(prompt) -> str` (line 350)
  Call OpenAI-compatible API (OpenRouter, OpenAI, etc.).
- `_clean_summary(summary) -> str` (line 366)
  Clean up common issues in generated summaries.

---

## `codebase_index/analyzers/test_mapper.py`

### `class TestMapper`
*Line 20*

Map symbols to their tests.

**Methods:**

- `__init__(index_data) -> None` (line 23)
  Initialize the test mapper.  Args:     index_data: The loaded index data.
- `test_files() -> list[dict[str, Any]]` (line 35)
  Get all test files from the index.
- `call_graph() -> dict[str, Any]` (line 58)
  Get the call graph from the index.
- `find_tests_for(symbol) -> dict[str, Any]` (line 64)
  Find tests for a given symbol.  Args:     symbol: The symbol to find tests for (...
- `_imports_symbol(imports, symbol, class_name, method_name) -> bool` (line 134)
  Check if the imports contain the symbol.
- `_calls_symbol(file_path, symbol, class_name, method_name) -> bool` (line 182)
  Check if the file calls the symbol based on call graph.
- `_find_matching_test_functions(exports, class_name, method_name) -> list[str]` (line 208)
  Find test functions that match naming conventions.
- `_find_callers_in_tests(symbol) -> list[str]` (line 266)
  Find test functions that call the symbol.
- `_build_summary(result) -> str` (line 297)
  Build a human-readable summary.

---

## `codebase_index/call_graph.py`

### `def cg_query_function(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]`
*Line 15*

Query what a specific function calls (fuzzy match).

Args:
    call_graph: The call graph dictionary.
    func_name: Function name to search for.

Returns:
    Dictionary with query info and matching results.

### `def cg_query_file(call_graph: dict[str, Any], file_path: str) -> dict[str, Any]`
*Line 43*

Query all functions in a specific file.

Args:
    call_graph: The call graph dictionary.
    file_path: File path to search for.

Returns:
    Dictionary with query info and matching results.

### `def cg_query_callers(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]`
*Line 69*

Query what functions call a specific function (inverse lookup).

Args:
    call_graph: The call graph dictionary.
    func_name: Function name to find callers of.

Returns:
    Dictionary with query info and matching results.

---

## `codebase_index/cli.py`

### `def create_parser() -> argparse.ArgumentParser`
*Line 38*

Create the argument parser.

### `def setup_logging(verbose: bool) -> None`
*Line 286*

Configure logging based on verbosity.

### `def main() -> None`
*Line 295*

Main entry point for the CLI.

### `def load_index(load_path: str, verbose: bool) -> dict[str, Any]`
*Line 563*

Load an existing index file.

### `def scan_codebase(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]`
*Line 575*

Scan the codebase and return the result.

### `def handle_cg_query(args: argparse.Namespace, result: dict[str, Any]) -> None`
*Line 641*

Handle call graph queries.

---

## `codebase_index/config.py`

### `def load_config(config_path: Path) -> dict[str, Any]`
*Line 278*

Load configuration from YAML file, merged with defaults.

Args:
    config_path: Path to the YAML configuration file.

Returns:
    Configuration dictionary with user values merged over defaults.

Raises:
    SystemExit: If PyYAML is not installed.
    FileNotFoundError: If config file doesn't exist.

### `def get_config_template() -> str`
*Line 310*

Generate a well-documented YAML config template for LLMs to customize.

---

## `codebase_index/incremental.py`

### `def incremental_update(root: Path, index_data: dict[str, Any], exclude: list[str], exclude_extensions: set[str] | None, config: dict[str, Any] | None) -> dict[str, Any]`
*Line 340*

Convenience function to perform incremental update.

Args:
    root: Root directory of the codebase.
    index_data: Existing index data.
    exclude: Patterns to exclude.
    exclude_extensions: File extensions to exclude.
    config: Configuration dictionary.

Returns:
    Update result with changes and new index.

### `class IncrementalUpdater`
*Line 22*

Incrementally update an existing index.

Compares file hashes to detect changes and only re-scans modified files.
Much faster than full re-scan for large codebases with few changes.

**Methods:**

- `__init__(root, index_data, exclude, exclude_extensions) -> None` (line 30)
  Initialize the incremental updater.  Args:     root: Root directory of the codeb...
- `update(scanner) -> dict[str, Any]` (line 57)
  Perform incremental update.  Args:     scanner: CodebaseScanner instance to use ...
- `_get_current_files() -> list[Path]` (line 120)
  Get list of current files in codebase (respecting exclusions).
- `_compute_hash(file_path) -> str` (line 143)
  Compute SHA-256 hash of file contents.
- `_apply_updates(scanner, changes) -> dict[str, Any]` (line 152)
  Apply the detected changes to create updated index.  Args:     scanner: Codebase...
- `_scan_files(scanner, file_paths, updated) -> None` (line 240)
  Scan specific files and add results to updated index.  Args:     scanner: Codeba...
- `_detect_language(suffix) -> str` (line 318)
  Detect language from file extension.

---

## `codebase_index/parsers/base.py`

### `class ParserRegistry`
*Line 31*

Registry for language parsers.

Manages parser classes and their file extension mappings.
Supports dynamic registration of custom parsers and config injection.

**Methods:**

- `register(cls, language, extensions) -> Callable[[Type['BaseParser']], Type['BaseParser']]` (line 44)
  Decorator to register a parser class.  Args:     language: Language name (e.g., ...
- `register_parser(cls, language, extensions, parser_class) -> None` (line 70)
  Register a parser class for a language.  Args:     language: Language name.     ...
- `get_parser(cls, filepath, config) -> tuple['BaseParser' | None, str | None]` (line 95)
  Get the appropriate parser for a file, configured with the given config.  Args: ...
- `_get_configured_parser(cls, language, config) -> 'BaseParser' | None` (line 120)
  Get or create a parser instance with the given config.
- `get_parser_for_language(cls, language, config) -> 'BaseParser' | None` (line 143)
  Get parser by language name.  Args:     language: Language name.     config: Con...
- `list_languages(cls) -> list[str]` (line 161)
  Get list of registered languages.
- `list_extensions(cls) -> dict[str, str]` (line 166)
  Get mapping of extensions to languages.
- `clear(cls) -> None` (line 171)
  Clear all registered parsers. Useful for testing.

### `class BaseParser(ABC)`
*Line 178*

Abstract base class for language parsers.

Subclasses must implement the `scan` method to extract
structural information from source files.

The scan method should return a dictionary with language-specific
keys. Common keys include:
- classes: List of class definitions
- functions: List of function

**Methods:**

- `__init__() -> None` (line 196)
  Initialize the parser with empty config.
- `configure(config) -> None` (line 200)
  Configure the parser with the given config.  Subclasses can override to extract ...
- `scan(filepath) -> dict[str, Any]` (line 212)
  Scan a source file and extract structural information.  Args:     filepath: Path...
- `scan_with_fallback(filepath) -> dict[str, Any]` (line 230)
  Scan with fallback to regex if AST parsing fails.  Override this in subclasses t...
- `get_empty_result() -> dict[str, Any]` (line 244)
  Get an empty result structure for this parser.  Subclasses can override to provi...
- `_match_patterns(text, patterns, pattern_key) -> list[dict[str, Any]]` (line 256)
  Match text against a list of config patterns.  Helper method for subclasses to u...

---

## `codebase_index/parsers/docker.py`

### `def _get_docker_parser(filepath: Path) -> tuple[DockerParser | None, str | None]`
*Line 131*

Check if file is a docker-compose file.

### `class DockerParser(BaseParser)`
*Line 22*

Docker Compose parser using PyYAML.

Falls back to regex parsing if PyYAML is not available.

**Methods:**

- `scan(filepath) -> dict[str, Any]` (line 31)
  Scan a docker-compose file.  Args:     filepath: Path to the docker-compose file...
- `_scan_regex(filepath) -> dict[str, Any]` (line 97)
  Fallback regex scanning if YAML not available.

---

## `codebase_index/parsers/python.py`

### `class PythonParser(BaseParser)`
*Line 44*

Python parser using the ast module for accurate extraction.

Falls back to regex parsing for files with syntax errors.
Supports configurable patterns for routes, models, and schemas.

**Methods:**

- `__init__() -> None` (line 54)
  Initialize the Python parser with default config.
- `configure(config) -> None` (line 63)
  Configure the parser with patterns from config.  Args:     config: Configuration...
- `scan(filepath) -> dict[str, Any]` (line 99)
  Scan a Python file and extract structure using AST.  Args:     filepath: Path to...
- `_process_class(node, result) -> None` (line 149)
  Process a class definition node.
- `_process_function(node, result) -> None` (line 244)
  Process a top-level function definition node.
- `_extract_route_info(decorator, func_name, line, pattern, match) -> dict[str, Any] | None` (line 284)
  Extract route information from a decorator.
- `_get_name(node) -> str` (line 319)
  Get name from AST node.
- `_get_decorator_name(node) -> str | None` (line 329)
  Extract decorator name.
- `_matches_base_class(bases, pattern) -> bool` (line 339)
  Check if any base class matches the pattern.  Uses exact matching for simple nam...
- `_extract_signature(node) -> dict[str, Any]` (line 361)
  Extract function signature (parameters and return type).
- `_get_annotation(node) -> str | None` (line 411)
  Extract type annotation as string.
- `_extract_calls(node) -> list[str]` (line 443)
  Extract all function/method calls from a function body.  Returns raw call string...
- `_get_call_name(node) -> str | None` (line 465)
  Extract the name of a call target.
- `_get_function_body_hash(node) -> str | None` (line 481)
  Generate a normalized hash of function body for duplicate detection.  Uses AST s...
- `_categorize_import(module, imports) -> None` (line 510)
  Categorize import as internal or external.
- `_scan_regex(filepath) -> dict[str, Any]` (line 533)
  Fallback regex-based scanning for files with syntax errors.

---

## `codebase_index/parsers/sql.py`

### `class SQLParser(BaseParser)`
*Line 21*

SQL parser using regex patterns.

Extracts table definitions, indexes, and views.

**Methods:**

- `scan(filepath) -> dict[str, Any]` (line 28)
  Scan a SQL file.  Args:     filepath: Path to the SQL file.  Returns:     Dictio...

---

## `codebase_index/parsers/typescript.py`

### `class TypeScriptParser(BaseParser)`
*Line 23*

TypeScript/React parser using regex patterns.

Extracts components, hooks, functions, types, interfaces, and imports.
Supports configurable internal import aliases.

**Methods:**

- `__init__() -> None` (line 31)
  Initialize with default config.
- `configure(config) -> None` (line 37)
  Configure the parser.  Args:     config: Configuration dictionary.
- `scan(filepath) -> dict[str, Any]` (line 59)
  Scan a TypeScript/React file.  Args:     filepath: Path to the TypeScript file. ...
- `_process_line(line, line_num, result) -> None` (line 92)
  Process a single line of code.
- `_categorize_import(module, imports) -> None` (line 170)
  Categorize import as internal or external.

---

## `codebase_index/scanner.py`

### `class CodebaseScanner`
*Line 53*

Main scanner that orchestrates all language-specific scanners and analyzers.

**Methods:**

- `__init__(root, exclude, exclude_extensions, include_hash, config)` (line 56)
  Initialize the codebase scanner.  Args:     root: Root directory to scan.     ex...
- `scan() -> dict[str, Any]` (line 110)
  Scan the entire codebase.  Returns:     Complete codebase index dictionary.
- `_init_result() -> dict[str, Any]` (line 159)
  Initialize the result structure.
- `_build_meta() -> dict[str, Any]` (line 194)
  Build metadata section.
- `_walk_files() -> Iterator[Path]` (line 208)
  Walk directory and yield files to scan.
- `_scan_file(filepath) -> dict[str, Any] | None` (line 222)
  Scan a single file.
- `_build_file_info(filepath, rel_path, language, parser, category) -> dict[str, Any]` (line 251)
  Build file info dictionary.
- `_process_file_data(file_info, result, route_prefixes) -> None` (line 281)
  Process scanned file data into result collections.
- `_process_python_file(file_info, result, route_prefixes) -> None` (line 296)
  Process Python file data.
- `_process_docker_file(exports, result) -> None` (line 365)
  Process Docker Compose file data.
- `_index_python_symbols(file_info, result) -> None` (line 375)
  Index Python symbols (functions, classes, methods).
- `_build_call_graph(result) -> None` (line 420)
  Build call graph and detect code duplicates.
- `_add_to_call_graph(func_info, file_path, class_name, result, body_hash_index) -> None` (line 458)
  Add a function/method to the call graph.
- `_update_summary(summary, file_info) -> None` (line 496)
  Update summary statistics.
- `_finalize_summary(result) -> None` (line 510)
  Add final summary counts from analysis results.

---

## `codebase_index/scanners/alembic.py`

### `class AlembicScanner`
*Line 20*

Scan for Alembic database migrations.

**Methods:**

- `scan(root) -> dict[str, Any]` (line 23)
  Scan for Alembic migrations.  Args:     root: Project root directory.  Returns: ...
- `_scan_migrations(migrations_dir, root) -> list[dict[str, Any]]` (line 66)
  Scan migration files.
- `_parse_migration(filepath, root) -> dict[str, Any] | None` (line 80)
  Parse a single migration file.

---

## `codebase_index/scanners/dependencies.py`

### `class DependenciesScanner`
*Line 21*

Scan for project dependencies from requirements.txt, package.json, etc.

**Methods:**

- `scan(root) -> dict[str, Any]` (line 24)
  Scan for all dependency files.  Args:     root: Project root directory.  Returns...
- `_parse_requirements(filepath) -> list[str]` (line 70)
  Parse requirements.txt file.  Args:     filepath: Path to requirements.txt.  Ret...
- `_parse_pyproject(filepath) -> list[str]` (line 96)
  Parse pyproject.toml for dependencies.  Args:     filepath: Path to pyproject.to...
- `_parse_package_json(filepath) -> dict[str, list[str]]` (line 133)
  Parse package.json for dependencies.  Args:     filepath: Path to package.json. ...

---

## `codebase_index/scanners/env.py`

### `class EnvScanner`
*Line 24*

Scan for environment variable usage (names only, no values).

**Methods:**

- `scan(root, exclude) -> dict[str, Any]` (line 27)
  Scan for environment variables.  Args:     root: Project root directory.     exc...
- `_parse_dotenv(filepath) -> list[str]` (line 79)
  Parse .env file for variable names (NOT values).  Args:     filepath: Path to .e...
- `_scan_python_env(filepath) -> set[str]` (line 105)
  Scan Python file for environment variable access.  Args:     filepath: Path to P...
- `_scan_typescript_env(filepath) -> set[str]` (line 145)
  Scan TypeScript file for environment variable access.  Args:     filepath: Path ...

---

## `codebase_index/scanners/http_calls.py`

### `class HttpCallsScanner`
*Line 22*

Scan for external HTTP calls (httpx, requests, aiohttp, fetch).

**Methods:**

- `scan(root, exclude) -> dict[str, Any]` (line 48)
  Scan for external HTTP calls.  Args:     root: Project root directory.     exclu...
- `_scan_python_file(filepath, root) -> list[dict[str, Any]]` (line 97)
  Scan a Python file for HTTP calls.
- `_scan_ts_file(filepath, root) -> list[dict[str, Any]]` (line 131)
  Scan a TypeScript file for HTTP calls.

---

## `codebase_index/scanners/middleware.py`

### `class MiddlewareScanner`
*Line 22*

Scan for FastAPI/Starlette middleware configuration.

**Methods:**

- `scan(root, exclude) -> dict[str, Any]` (line 36)
  Scan for middleware usage.  Args:     root: Project root directory.     exclude:...
- `_scan_file(filepath, root) -> dict[str, list[dict[str, Any]]]` (line 61)
  Scan a file for middleware.

---

## `codebase_index/scanners/routes.py`

### `class RoutePrefixScanner`
*Line 23*

Scan FastAPI main.py for router prefixes to build full paths.

**Methods:**

- `scan(root, exclude) -> dict[str, str]` (line 26)
  Scan for include_router calls to extract prefixes.  Args:     root: Project root...
- `_scan_main_file(filepath) -> dict[str, str]` (line 51)
  Scan a main.py file for include_router calls.  Args:     filepath: Path to the m...

---

## `codebase_index/scanners/todo.py`

### `class TodoScanner`
*Line 22*

Scan for TODO, FIXME, HACK, XXX comments.

**Methods:**

- `scan(root, exclude) -> list[dict[str, Any]]` (line 41)
  Scan all files for TODO/FIXME comments.  Args:     root: Project root directory....
- `_scan_file(filepath, root) -> list[dict[str, Any]]` (line 63)
  Scan a single file for TODOs.  Args:     filepath: Path to the file.     root: P...

---

## `codebase_index/scanners/websocket.py`

### `class WebSocketScanner`
*Line 22*

Scan for WebSocket endpoints.

**Methods:**

- `scan(root, exclude) -> dict[str, Any]` (line 25)
  Scan for WebSocket endpoints.  Args:     root: Project root directory.     exclu...
- `_scan_file(filepath, root) -> list[dict[str, Any]]` (line 50)
  Scan a file for WebSocket endpoints.

---

## `codebase_index/utils.py`

### `def get_file_hash(filepath: Path) -> str`
*Line 21*

Generate SHA256 hash of file contents.

Args:
    filepath: Path to the file to hash.

Returns:
    Hash string in format "sha256:<first 16 chars of hex>".

Raises:
    FileNotFoundError: If the file doesn't exist.
    PermissionError: If the file can't be read.

### `def count_lines(filepath: Path) -> int`
*Line 42*

Count lines in a file.

Args:
    filepath: Path to the file.

Returns:
    Number of lines in the file, or 0 if the file can't be read.

### `def get_git_info(root: Path) -> dict[str, Any] | None`
*Line 60*

Get git metadata for a repository.

Args:
    root: Root directory of the git repository.

Returns:
    Dictionary with 'commit', 'branch', and 'dirty' keys,
    or None if not a git repository or git is unavailable.

### `def categorize_file(filepath: str, categories: dict[str, str]) -> str`
*Line 109*

Categorize a file based on path patterns.

Args:
    filepath: Relative path to the file.
    categories: Dict mapping regex patterns to category names.

Returns:
    Category name, or "other" if no pattern matches.

### `def should_exclude(path: Path, exclude_patterns: list[str]) -> bool`
*Line 126*

Check if path should be excluded based on patterns.

Args:
    path: Path to check.
    exclude_patterns: List of patterns. Patterns starting with '*'
        match suffixes, others match directory names.

Returns:
    True if the path should be excluded.

### `def normalize_module_name(name: str) -> str`
*Line 150*

Normalize a module/package name for comparison.

Converts hyphens to underscores and lowercases.

Args:
    name: Module or package name.

Returns:
    Normalized name.

### `def extract_domain(url: str) -> str | None`
*Line 165*

Extract domain from a URL.

Args:
    url: URL string.

Returns:
    Domain name, or None if extraction fails.

### `def truncate_string(text: str | None, max_length: int) -> str | None`
*Line 188*

Truncate a string to a maximum length.

Args:
    text: String to truncate.
    max_length: Maximum length.

Returns:
    Truncated string with "..." suffix if needed, or None if input is None.

---

