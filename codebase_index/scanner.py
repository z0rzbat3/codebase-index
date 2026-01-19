"""
Main scanner orchestrator for codebase_index.

Coordinates all parsers, scanners, and analyzers to produce a complete codebase index.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.config import DEFAULT_CONFIG, DEFAULT_EXCLUDE
from codebase_index.utils import (
    categorize_file,
    count_lines,
    get_file_hash,
    get_git_info,
    should_exclude,
    truncate_string,
)
from codebase_index.parsers import ParserRegistry, PythonParser, TypeScriptParser, SQLParser, DockerParser
from codebase_index.parsers.docker import DockerParser as DockerParserClass
from codebase_index.scanners import (
    DependenciesScanner,
    EnvScanner,
    TodoScanner,
    RoutePrefixScanner,
    HttpCallsScanner,
    MiddlewareScanner,
    WebSocketScanner,
    AlembicScanner,
)
from codebase_index.analyzers import (
    ImportAggregator,
    AuthScanner,
    ComplexityAnalyzer,
    TestCoverageMapper,
    OrphanedFileScanner,
    ExecutionFlowAnalyzer,
    CentralityAnalyzer,
)

if TYPE_CHECKING:
    from typing import Any, Iterator

logger = logging.getLogger(__name__)

# Tool version - import from package
from codebase_index import __version__ as VERSION


class CodebaseScanner:
    """Main scanner that orchestrates all language-specific scanners and analyzers."""

    def __init__(
        self,
        root: Path,
        exclude: list[str] | None = None,
        exclude_extensions: set[str] | None = None,
        include_hash: bool = True,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the codebase scanner.

        Args:
            root: Root directory to scan.
            exclude: Patterns to exclude (directories, file patterns).
            exclude_extensions: File extensions to exclude.
            include_hash: Whether to include file hashes.
            config: Configuration dictionary (merged with defaults).
        """
        self.root = root.resolve()
        self.exclude = exclude or DEFAULT_EXCLUDE.copy()
        self.exclude_extensions = exclude_extensions or set()
        self.include_hash = include_hash
        self.config = config or DEFAULT_CONFIG

        # Initialize domain scanners
        self.deps_scanner = DependenciesScanner()
        self.env_scanner = EnvScanner()
        self.todo_scanner = TodoScanner()
        self.route_prefix_scanner = RoutePrefixScanner()
        self.http_calls_scanner = HttpCallsScanner()
        self.middleware_scanner = MiddlewareScanner()
        self.websocket_scanner = WebSocketScanner()
        self.alembic_scanner = AlembicScanner()

        # Initialize analyzers
        self.import_aggregator = ImportAggregator()
        self.auth_scanner = AuthScanner()
        self.auth_scanner.configure(self.config)  # Pass auth patterns from config
        self.test_mapper = TestCoverageMapper(self.root)
        complexity_config = self.config.get("complexity", {})
        self.complexity_analyzer = ComplexityAnalyzer(
            file_lines_warning=complexity_config.get("max_file_lines", 500),
            file_lines_critical=complexity_config.get("max_file_lines", 500) * 2,
        )
        self.orphaned_scanner = OrphanedFileScanner()

        # Get category patterns from config
        self.python_categories = self.config.get("categories", {}).get(
            "python", DEFAULT_CONFIG["categories"]["python"]
        )
        self.typescript_categories = self.config.get("categories", {}).get(
            "typescript", DEFAULT_CONFIG["categories"]["typescript"]
        )

    def scan(self) -> dict[str, Any]:
        """
        Scan the entire codebase.

        Returns:
            Complete codebase index dictionary.
        """
        result = self._init_result()

        # Get route prefixes first for full path resolution
        route_prefixes = self.route_prefix_scanner.scan(self.root, self.exclude)

        # Collect test files for coverage mapping
        self.test_mapper.collect_test_files(self.exclude)

        # Scan all files
        for filepath in self._walk_files():
            file_info = self._scan_file(filepath)
            if file_info:
                result["files"].append(file_info)
                self._update_summary(result["summary"], file_info)
                self._process_file_data(file_info, result, route_prefixes)

        # Build call graph and detect duplicates
        self._build_call_graph(result)

        # Run architectural analyzers (need call graph)
        result["execution_flow"] = ExecutionFlowAnalyzer(result).analyze()
        result["centrality"] = CentralityAnalyzer(result).analyze()

        # Run domain scanners
        result["dependencies"] = self.deps_scanner.scan(self.root)
        result["environment_variables"] = self.env_scanner.scan(self.root, self.exclude)
        result["todos"] = self.todo_scanner.scan(self.root, self.exclude)
        result["middleware"] = self.middleware_scanner.scan(self.root, self.exclude)
        result["websockets"] = self.websocket_scanner.scan(self.root, self.exclude)
        result["migrations"] = self.alembic_scanner.scan(self.root)
        result["external_http_calls"] = self.http_calls_scanner.scan(self.root, self.exclude)

        # Run analyzers
        python_deps = result["dependencies"].get("python", [])
        result["import_analysis"] = self.import_aggregator.analyze(python_deps)
        result["test_coverage"] = self.test_mapper.map_source_to_test(result["files"])
        result["complexity_warnings"] = self.complexity_analyzer.analyze(result["files"])
        result["orphaned_files"] = self.orphaned_scanner.scan(
            self.root, result["files"], self.exclude
        )

        # Update summary with analysis results
        self._finalize_summary(result)

        return result

    def _init_result(self) -> dict[str, Any]:
        """Initialize the result structure."""
        return {
            "meta": self._build_meta(),
            "summary": {
                "total_files": 0,
                "total_lines": 0,
                "by_language": {},
                "by_category": {},
            },
            "files": [],
            "api_endpoints": [],
            "schemas": [],
            "database": {"tables": []},
            "docker": {"services": [], "networks": [], "volumes": []},
            "dependencies": {},
            "environment_variables": {},
            "todos": [],
            "import_analysis": {},
            "test_coverage": {},
            "external_http_calls": {},
            "complexity_warnings": {},
            "middleware": {},
            "websockets": {},
            "migrations": {},
            "orphaned_files": {},
            "symbol_index": {
                "functions": [],
                "classes": [],
                "methods": [],
            },
            "router_prefixes": {},
            "call_graph": {},
            "potential_duplicates": [],
            "execution_flow": {},
            "centrality": {},
        }

    def _build_meta(self) -> dict[str, Any]:
        """Build metadata section."""
        meta: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": VERSION,
            "root": str(self.root),
        }

        git_info = get_git_info(self.root)
        if git_info:
            meta["git"] = git_info

        return meta

    def _walk_files(self) -> Iterator[Path]:
        """Walk directory and yield files to scan."""
        for root, dirs, files in os.walk(self.root):
            # Filter out excluded directories
            dirs[:] = [
                d for d in dirs
                if not should_exclude(Path(root) / d, self.exclude)
            ]

            for filename in files:
                filepath = Path(root) / filename
                if not should_exclude(filepath, self.exclude):
                    yield filepath

    def _scan_file(self, filepath: Path) -> dict[str, Any] | None:
        """Scan a single file."""
        rel_path = str(filepath.relative_to(self.root))
        suffix = filepath.suffix.lower()

        # Check extension exclusions
        if self.exclude_extensions and suffix in self.exclude_extensions:
            return None

        # Check for Docker files by name
        docker_parser, docker_lang = DockerParserClass.get_for_file(filepath)
        if docker_parser and docker_lang:
            return self._build_file_info(filepath, rel_path, docker_lang, docker_parser)

        # Get parser from registry (pass config for framework-specific patterns)
        parser, language = ParserRegistry.get_parser(filepath, self.config)
        if not parser:
            return None

        # Determine category
        if language == "python":
            category = categorize_file(rel_path, self.python_categories)
        elif language == "typescript":
            category = categorize_file(rel_path, self.typescript_categories)
        else:
            category = "other"

        return self._build_file_info(filepath, rel_path, language, parser, category)

    def _build_file_info(
        self,
        filepath: Path,
        rel_path: str,
        language: str,
        parser: Any,
        category: str = "other",
    ) -> dict[str, Any]:
        """Build file info dictionary."""
        file_info: dict[str, Any] = {
            "path": rel_path,
            "language": language,
            "category": category,
            "size_bytes": filepath.stat().st_size,
            "lines": count_lines(filepath),
        }

        if self.include_hash:
            try:
                file_info["hash"] = get_file_hash(filepath)
            except (OSError, IOError):
                pass

        # Scan file contents
        exports = parser.scan(filepath)
        if exports and not exports.get("error"):
            file_info["exports"] = exports

        return file_info

    def _process_file_data(
        self,
        file_info: dict[str, Any],
        result: dict[str, Any],
        route_prefixes: dict[str, str],
    ) -> None:
        """Process scanned file data into result collections."""
        exports = file_info.get("exports", {})
        language = file_info.get("language")

        if language == "python":
            self._process_python_file(file_info, result, route_prefixes)
        elif language == "docker":
            self._process_docker_file(exports, result)

    def _process_python_file(
        self,
        file_info: dict[str, Any],
        result: dict[str, Any],
        route_prefixes: dict[str, str],
    ) -> None:
        """Process Python file data."""
        exports = file_info.get("exports", {})
        file_path = file_info["path"]

        # Register internal module
        path_parts = Path(file_path).with_suffix("").parts
        for part in path_parts:
            if part and not part.startswith("_"):
                self.import_aggregator.add_internal_module(part)

        # Aggregate imports
        if exports.get("imports"):
            all_imports = (
                exports["imports"].get("external", [])
                + exports["imports"].get("internal", [])
            )
            self.import_aggregator.add_imports(all_imports, file_path)

        # Process API endpoints
        if exports.get("fastapi_routes"):
            router_name = Path(file_path).stem
            prefix = route_prefixes.get(router_name, "")

            # Store prefix mapping by file path for doc generator
            if prefix:
                result["router_prefixes"][file_path] = prefix

            annotated_routes = self.auth_scanner.scan_file(
                self.root / file_path,
                exports["fastapi_routes"],
            )

            for route in annotated_routes:
                full_path = prefix + (route.get("path") or "")
                result["api_endpoints"].append({
                    **route,
                    "full_path": full_path,
                    "file": file_path,
                })

        # Process database tables (legacy SQLAlchemy key)
        if exports.get("sqlalchemy_tables"):
            for table in exports["sqlalchemy_tables"]:
                result["database"]["tables"].append({
                    **table,
                    "file": file_path,
                })

        # Process generic models (config-driven, e.g., Django ORM)
        if exports.get("models"):
            for model in exports["models"]:
                result["database"]["tables"].append({
                    **model,
                    "file": file_path,
                })

        # Aggregate schemas (Pydantic, DRF serializers, etc.)
        if exports.get("schemas"):
            for schema in exports["schemas"]:
                result["schemas"].append({
                    **schema,
                    "file": file_path,
                })

        # Build symbol index
        self._index_python_symbols(file_info, result)

    def _process_docker_file(
        self,
        exports: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Process Docker Compose file data."""
        result["docker"]["services"].extend(exports.get("services", []))
        result["docker"]["networks"].extend(exports.get("networks", []))
        result["docker"]["volumes"].extend(exports.get("volumes", []))

    def _index_python_symbols(
        self,
        file_info: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Index Python symbols (functions, classes, methods)."""
        exports = file_info.get("exports", {})
        file_path = file_info["path"]

        # Index functions
        for func in exports.get("functions", []):
            if isinstance(func, dict):
                result["symbol_index"]["functions"].append({
                    "name": func.get("name"),
                    "file": file_path,
                    "line": func.get("line"),
                    "async": func.get("async", False),
                    "signature": func.get("signature"),
                    "docstring": truncate_string(func.get("docstring")),
                })

        # Index classes and methods
        for cls in exports.get("classes", []):
            if isinstance(cls, dict):
                result["symbol_index"]["classes"].append({
                    "name": cls.get("name"),
                    "file": file_path,
                    "line": cls.get("line"),
                    "bases": cls.get("bases", []),
                    "docstring": truncate_string(cls.get("docstring")),
                    "method_count": len(cls.get("methods", [])),
                })

                for method in cls.get("methods", []):
                    if isinstance(method, dict):
                        result["symbol_index"]["methods"].append({
                            "name": method.get("name"),
                            "class": cls.get("name"),
                            "file": file_path,
                            "line": method.get("line"),
                            "async": method.get("async", False),
                            "signature": method.get("signature"),
                            "docstring": truncate_string(method.get("docstring")),
                        })

    def _build_call_graph(self, result: dict[str, Any]) -> None:
        """Build call graph and detect code duplicates."""
        body_hash_index: dict[str, list[dict[str, Any]]] = {}

        for file_info in result["files"]:
            if file_info.get("language") != "python":
                continue

            file_path = file_info["path"]
            exports = file_info.get("exports", {})

            # Process functions
            for func in exports.get("functions", []):
                if isinstance(func, dict):
                    self._add_to_call_graph(func, file_path, None, result, body_hash_index)

            # Process methods
            for cls in exports.get("classes", []):
                if isinstance(cls, dict):
                    class_name = cls.get("name")
                    for method in cls.get("methods", []):
                        if isinstance(method, dict):
                            self._add_to_call_graph(
                                method, file_path, class_name, result, body_hash_index
                            )

        # Find potential duplicates
        for body_hash, functions in body_hash_index.items():
            if len(functions) > 1:
                result["potential_duplicates"].append({
                    "hash": body_hash,
                    "count": len(functions),
                    "functions": functions,
                })

        # Sort duplicates by count
        result["potential_duplicates"].sort(key=lambda x: x["count"], reverse=True)

    def _add_to_call_graph(
        self,
        func_info: dict[str, Any],
        file_path: str,
        class_name: str | None,
        result: dict[str, Any],
        body_hash_index: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Add a function/method to the call graph."""
        func_name = func_info.get("name")
        calls = func_info.get("calls", [])

        if class_name:
            full_name = f"{file_path}:{class_name}.{func_name}"
        else:
            full_name = f"{file_path}:{func_name}"

        if calls:
            result["call_graph"][full_name] = {
                "file": file_path,
                "line": func_info.get("line"),
                "calls": calls,
            }
            if class_name:
                result["call_graph"][full_name]["class"] = class_name

        # Track body hash for duplicate detection
        body_hash = func_info.get("body_hash")
        if body_hash:
            if body_hash not in body_hash_index:
                body_hash_index[body_hash] = []
            body_hash_index[body_hash].append({
                "name": f"{class_name}.{func_name}" if class_name else func_name,
                "file": file_path,
                "line": func_info.get("line"),
                "type": "method" if class_name else "function",
            })

    def _update_summary(self, summary: dict[str, Any], file_info: dict[str, Any]) -> None:
        """Update summary statistics."""
        summary["total_files"] += 1
        summary["total_lines"] += file_info.get("lines", 0)

        lang = file_info.get("language", "other")
        if lang not in summary["by_language"]:
            summary["by_language"][lang] = {"files": 0, "lines": 0}
        summary["by_language"][lang]["files"] += 1
        summary["by_language"][lang]["lines"] += file_info.get("lines", 0)

        cat = file_info.get("category", "other")
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

    def _finalize_summary(self, result: dict[str, Any]) -> None:
        """Add final summary counts from analysis results."""
        summary = result["summary"]

        summary["todos_count"] = len(result["todos"])
        summary["env_vars_count"] = (
            len(result["environment_variables"].get("python_usage", []))
            + len(result["environment_variables"].get("typescript_usage", []))
        )
        summary["api_endpoints_count"] = len(result["api_endpoints"])
        summary["auth_required_endpoints"] = sum(
            1 for ep in result["api_endpoints"] if ep.get("auth_required")
        )
        summary["schemas_count"] = len(result["schemas"])
        summary["database_tables_count"] = len(result["database"]["tables"])
        summary["test_coverage_percent"] = result["test_coverage"].get(
            "coverage_percentage", 0
        )
        summary["external_http_calls"] = result["external_http_calls"].get(
            "total_external_calls", 0
        )
        summary["complexity_issues"] = (
            len(result["complexity_warnings"].get("large_files", []))
            + len(result["complexity_warnings"].get("complex_classes", []))
        )
        summary["middleware_count"] = (
            len(result["middleware"].get("middleware", []))
            + len(result["middleware"].get("custom_middleware", []))
        )
        summary["websocket_endpoints"] = result["websockets"].get("total", 0)
        summary["migrations_count"] = result["migrations"].get("total", 0)
        summary["orphaned_files_count"] = result["orphaned_files"].get("orphaned_count", 0)
        summary["orphaned_lines"] = result["orphaned_files"].get("orphaned_lines", 0)
        summary["total_functions"] = len(result["symbol_index"]["functions"])
        summary["total_classes"] = len(result["symbol_index"]["classes"])
        summary["total_methods"] = len(result["symbol_index"]["methods"])
        summary["documented_functions"] = sum(
            1 for f in result["symbol_index"]["functions"] if f.get("docstring")
        )
        summary["documented_classes"] = sum(
            1 for c in result["symbol_index"]["classes"] if c.get("docstring")
        )
        summary["call_graph_entries"] = len(result["call_graph"])
        summary["potential_duplicate_groups"] = len(result["potential_duplicates"])
        summary["total_duplicated_functions"] = sum(
            d["count"] for d in result["potential_duplicates"]
        )

        # Add architectural analysis summary
        if result.get("execution_flow"):
            ef_summary = result["execution_flow"].get("summary", {})
            summary["entry_points_count"] = ef_summary.get("total_entry_points", 0)
            summary["max_call_depth"] = ef_summary.get("max_depth", 0)

        if result.get("centrality"):
            c_summary = result["centrality"].get("summary", {})
            summary["core_functions"] = c_summary.get("core_count", 0)
            summary["hub_functions"] = c_summary.get("hub_count", 0)
            summary["utility_functions"] = c_summary.get("utility_count", 0)
            summary["isolated_functions"] = c_summary.get("isolated_count", 0)

        # Generate README badges
        result["badges"] = self._generate_badges(summary)

    def _generate_badges(self, summary: dict[str, Any]) -> dict[str, Any]:
        """
        Generate shields.io badge URLs for README.

        Returns both individual badge URLs and a ready-to-paste markdown block.
        """
        from urllib.parse import quote

        def badge_url(label: str, value: str, color: str) -> str:
            """Generate a shields.io badge URL."""
            label_encoded = quote(label, safe="")
            value_encoded = quote(str(value), safe="")
            return f"https://img.shields.io/badge/{label_encoded}-{value_encoded}-{color}"

        def format_number(n: int) -> str:
            """Format large numbers (e.g., 11770 -> 11.8k)."""
            if n >= 1000:
                return f"{n/1000:.1f}k"
            return str(n)

        # Calculate documentation coverage
        total_funcs = summary.get("total_functions", 0)
        doc_funcs = summary.get("documented_functions", 0)
        doc_coverage = round(doc_funcs / total_funcs * 100) if total_funcs > 0 else 0

        # Determine colors based on values
        doc_color = "brightgreen" if doc_coverage >= 80 else "yellow" if doc_coverage >= 50 else "red"
        test_cov = summary.get("test_coverage_percent", 0)
        test_color = "brightgreen" if test_cov >= 80 else "yellow" if test_cov >= 50 else "red"

        badges = {
            "files": {
                "url": badge_url("files", str(summary.get("total_files", 0)), "blue"),
                "markdown": f"![Files]({badge_url('files', str(summary.get('total_files', 0)), 'blue')})",
            },
            "lines": {
                "url": badge_url("lines", format_number(summary.get("total_lines", 0)), "blue"),
                "markdown": f"![Lines]({badge_url('lines', format_number(summary.get('total_lines', 0)), 'blue')})",
            },
            "functions": {
                "url": badge_url("functions", str(summary.get("total_functions", 0)), "blue"),
                "markdown": f"![Functions]({badge_url('functions', str(summary.get('total_functions', 0)), 'blue')})",
            },
            "classes": {
                "url": badge_url("classes", str(summary.get("total_classes", 0)), "blue"),
                "markdown": f"![Classes]({badge_url('classes', str(summary.get('total_classes', 0)), 'blue')})",
            },
            "doc_coverage": {
                "url": badge_url("doc coverage", f"{doc_coverage}%", doc_color),
                "markdown": f"![Doc Coverage]({badge_url('doc coverage', f'{doc_coverage}%', doc_color)})",
            },
            "test_coverage": {
                "url": badge_url("test coverage", f"{test_cov}%", test_color),
                "markdown": f"![Test Coverage]({badge_url('test coverage', f'{test_cov}%', test_color)})",
            },
            "api_endpoints": {
                "url": badge_url("endpoints", str(summary.get("api_endpoints_count", 0)), "green"),
                "markdown": f"![Endpoints]({badge_url('endpoints', str(summary.get('api_endpoints_count', 0)), 'green')})",
            },
            "todos": {
                "url": badge_url("TODOs", str(summary.get("todos_count", 0)), "orange"),
                "markdown": f"![TODOs]({badge_url('TODOs', str(summary.get('todos_count', 0)), 'orange')})",
            },
        }

        # Generate combined markdown block
        primary_badges = ["files", "lines", "doc_coverage"]
        if summary.get("api_endpoints_count", 0) > 0:
            primary_badges.append("api_endpoints")
        if summary.get("test_coverage_percent", 0) > 0:
            primary_badges.append("test_coverage")

        badges["markdown_block"] = " ".join(badges[b]["markdown"] for b in primary_badges)

        return badges
