"""
CLI interface for codebase_index.

Provides the command-line interface for scanning codebases.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index import __version__
from codebase_index.config import (
    DEFAULT_CONFIG,
    DEFAULT_EXCLUDE,
    get_config_template,
    load_config,
)
from codebase_index.scanner import CodebaseScanner
from codebase_index.call_graph import cg_query_callers
from codebase_index.analyzers.staleness import StalenessChecker
from codebase_index.analyzers.test_mapper import TestMapper
from codebase_index.analyzers.impact import ImpactAnalyzer

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Understand code before changing it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  codebase-index .                    # Scan current directory
  codebase-index ./src -o index.json  # Scan src, output to file
  codebase-index . --summary          # Quick overview only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Scan:   codebase-index . -o index.json
2. Query:  codebase-index --load index.json --callers MyFunction
3. Update: codebase-index --load index.json --update -o index.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYSIS QUERIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --check            Check if index is stale (files changed since scan)
  --update           Incrementally update the index
  --callers SYMBOL   What calls SYMBOL? (inverse call graph)
  --impact FILE      Blast radius: callers, tests, endpoints affected
  --tests SYMBOL     Find tests for a function/class
  --doc SYMBOL       Full documentation for a symbol

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEMANTIC SEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --build-embeddings   Build semantic index (requires sentence-transformers)
  --search QUERY       Search code by description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISCLAIMER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This tool uses static analysis (AST parsing). It may miss dynamic code,
metaprogramming, or runtime-generated patterns. Always verify critical
findings against actual source code.
        """,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to scan (default: current directory)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--load",
        metavar="FILE",
        help="Load existing index file instead of scanning",
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        help="Skip file hash generation",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Only output summary",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Additional patterns to exclude",
    )
    parser.add_argument(
        "--exclude-dirs",
        nargs="+",
        metavar="DIR",
        help="Directories to exclude (e.g., docs vendor third-party)",
    )
    parser.add_argument(
        "--exclude-ext",
        nargs="+",
        metavar="EXT",
        help="File extensions to exclude (e.g., .md .txt .log)",
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--config",
        metavar="FILE",
        help="Load config from YAML file (for Django, Flask, Express, etc.)",
    )
    config_group.add_argument(
        "--init-config",
        action="store_true",
        help="Generate a starter config file (customize with LLM, then use --config)",
    )

    # Call graph query options
    cg_group = parser.add_argument_group("Call Graph Queries")
    cg_group.add_argument(
        "--callers",
        metavar="SYMBOL",
        help="What calls SYMBOL? (inverse call graph lookup)",
    )

    # Analysis query options
    analysis_group = parser.add_argument_group("Analysis Queries")
    analysis_group.add_argument(
        "--check",
        action="store_true",
        help="Check if loaded index is stale (use with --load)",
    )
    analysis_group.add_argument(
        "--tests",
        metavar="SYMBOL",
        help="Find tests for a function/class (e.g., 'AgentFactory.create')",
    )
    analysis_group.add_argument(
        "--impact",
        metavar="FILE",
        help="Show impact radius: callers, affected tests, affected endpoints",
    )
    analysis_group.add_argument(
        "--doc",
        metavar="SYMBOL",
        help="Generate full documentation for a symbol (signature, callers, tests, code)",
    )

    # Advanced features
    advanced_group = parser.add_argument_group("Advanced Features")
    advanced_group.add_argument(
        "--update",
        action="store_true",
        help="Incrementally update loaded index (only re-scan changed files)",
    )
    advanced_group.add_argument(
        "--search",
        metavar="QUERY",
        help="Semantic search: find code by description (requires --build-embeddings first)",
    )
    advanced_group.add_argument(
        "--build-embeddings",
        action="store_true",
        help="Build embeddings for semantic search (requires sentence-transformers)",
    )
    advanced_group.add_argument(
        "--embedding-model",
        metavar="MODEL",
        default="unixcoder",
        help="Embedding model: unixcoder (default), codebert, codet5, minilm, or HuggingFace name",
    )
    advanced_group.add_argument(
        "--search-threshold",
        metavar="SCORE",
        type=float,
        default=0.3,
        help="Minimum similarity score for semantic search (0.0-1.0, default: 0.3). Lower = more results.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"codebase_index {__version__}",
    )

    return parser


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Handle --init-config: just output the template and exit
    if args.init_config:
        print(get_config_template())
        return

    # Load config if specified
    config = DEFAULT_CONFIG
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file '{config_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        config = load_config(config_path)
        if args.verbose:
            print(f"Loaded config: {config_path}", file=sys.stderr)
            # Show what's in the config
            routes = config.get("routes", {}).get("patterns", [])
            models = config.get("models", {}).get("patterns", [])
            schemas = config.get("schemas", {}).get("patterns", [])
            auth = config.get("auth", {}).get("patterns", [])
            exclude = config.get("exclude", {})
            exclude_dirs = exclude.get("directories", [])
            exclude_exts = exclude.get("extensions", [])
            print(f"  routes: {len(routes)} patterns", file=sys.stderr)
            print(f"  models: {len(models)} patterns", file=sys.stderr)
            print(f"  schemas: {len(schemas)} patterns", file=sys.stderr)
            print(f"  auth: {len(auth)} patterns", file=sys.stderr)
            if exclude_dirs or exclude_exts:
                print(f"  exclude: {len(exclude_dirs)} dirs, {len(exclude_exts)} extensions", file=sys.stderr)
            else:
                print(f"  exclude: none configured", file=sys.stderr)

    # Check if we have call graph query options
    has_cg_query = args.callers

    # Track changed files for incremental embedding updates
    changed_files: set[str] | None = None

    # Load existing index or scan
    if args.load:
        result = load_index(args.load, args.verbose)
    else:
        result = scan_codebase(args, config)

    # Handle --update: incremental update
    if args.update:
        if not args.load:
            print("Error: --update requires --load to specify an index file", file=sys.stderr)
            sys.exit(1)
        from codebase_index.incremental import incremental_update

        root = Path(args.path).resolve()
        exclude = DEFAULT_EXCLUDE.copy()
        if args.exclude:
            exclude.extend(args.exclude)
        if args.exclude_dirs:
            exclude.extend(args.exclude_dirs)

        # Add directory exclusions from config (critical for --update to work correctly)
        config_exclude = config.get("exclude", {})
        config_dirs = config_exclude.get("directories") or []
        if config_dirs:
            exclude.extend(config_dirs)
        config_patterns = config_exclude.get("patterns") or []
        if config_patterns:
            exclude.extend(config_patterns)

        exclude_extensions: set[str] = set()
        if args.exclude_ext:
            for ext in args.exclude_ext:
                if not ext.startswith('.'):
                    ext = '.' + ext
                exclude_extensions.add(ext.lower())

        # Add extension exclusions from config
        config_exts = config_exclude.get("extensions") or []
        for ext in config_exts:
            if not ext.startswith('.'):
                ext = '.' + ext
            exclude_extensions.add(ext.lower())

        if args.verbose:
            if config_dirs:
                print(f"Config excluded directories: {config_dirs}", file=sys.stderr)
            if config_patterns:
                print(f"Config excluded patterns: {config_patterns}", file=sys.stderr)
            if config_exts:
                print(f"Config excluded extensions: {config_exts}", file=sys.stderr)

        update_result = incremental_update(
            root=root,
            index_data=result,
            exclude=exclude,
            exclude_extensions=exclude_extensions,
            config=config,
        )

        changes = update_result["changes"]
        if args.verbose:
            print(f"Incremental update complete:", file=sys.stderr)
            print(f"  Added: {len(changes['added'])} files", file=sys.stderr)
            print(f"  Updated: {len(changes['updated'])} files", file=sys.stderr)
            print(f"  Deleted: {len(changes['deleted'])} files", file=sys.stderr)
            print(f"  Unchanged: {changes['unchanged']} files", file=sys.stderr)
            print(f"  Duration: {changes['duration_ms']}ms", file=sys.stderr)

        # Track changed files for incremental embedding updates
        changed_files = set(changes['added']) | set(changes['updated']) | set(changes['deleted'])

        # Use the updated index for output
        result = update_result["index"]

    # Handle --check: staleness check
    if args.check:
        if not args.load:
            print("Error: --check requires --load to specify an index file", file=sys.stderr)
            sys.exit(1)
        root = Path(args.path).resolve()
        index_file = Path(args.load).resolve()
        checker = StalenessChecker(root, result, index_file=index_file)
        staleness = checker.check()
        print(json.dumps(staleness, indent=2, default=str))
        return

    # Handle --tests: find tests for a symbol
    if args.tests:
        mapper = TestMapper(result)
        tests_result = mapper.find_tests_for(args.tests)
        print(json.dumps(tests_result, indent=2, default=str))
        return

    # Handle --impact: analyze impact radius of a file
    if args.impact:
        analyzer = ImpactAnalyzer(result)
        impact_result = analyzer.analyze_file(args.impact)
        print(json.dumps(impact_result, indent=2, default=str))
        return

    # Handle --doc: generate full documentation for a symbol
    if args.doc:
        from codebase_index.analyzers.doc_generator import generate_doc_for_symbol

        root = Path(args.path).resolve()
        doc_result = generate_doc_for_symbol(result, args.doc, root=root)

        # Print markdown to stdout (can be piped to file or pager)
        print(doc_result.get("markdown", ""))
        return

    # Handle --build-embeddings: generate embeddings for semantic search
    if args.build_embeddings:
        from codebase_index.analyzers.semantic import (
            build_embeddings,
            check_semantic_available,
            MODELS,
            DEFAULT_MODEL,
        )

        if not check_semantic_available():
            print(
                "Error: Semantic search requires sentence-transformers.\n"
                "Install with: pip install codebase-index[semantic]",
                file=sys.stderr,
            )
            sys.exit(1)

        root = Path(args.path).resolve()
        model = getattr(args, 'embedding_model', None) or DEFAULT_MODEL

        if args.verbose:
            model_info = MODELS.get(model, {})
            model_name = model_info.get("name", model) if model_info else model
            if changed_files is not None:
                print(f"Building embeddings (incremental) with model: {model_name}", file=sys.stderr)
                print(f"  Changed files: {len(changed_files)}", file=sys.stderr)
            else:
                print(f"Building embeddings (full) with model: {model_name}", file=sys.stderr)

        result = build_embeddings(result, root=root, model=model, changed_files=changed_files)

        if args.verbose:
            semantic = result.get("semantic", {})
            print(f"  Total embeddings: {semantic.get('count', 0)} symbols", file=sys.stderr)
            print(f"  Model: {semantic.get('model', 'unknown')}", file=sys.stderr)

        # Fall through to output the updated index

    # Handle --search: semantic search
    if args.search:
        from codebase_index.analyzers.semantic import (
            semantic_search,
            check_semantic_available,
        )

        if not check_semantic_available():
            print(
                "Error: Semantic search requires sentence-transformers.\n"
                "Install with: pip install codebase-index[semantic]",
                file=sys.stderr,
            )
            sys.exit(1)

        threshold = getattr(args, 'search_threshold', 0.3)
        search_result = semantic_search(result, args.search, min_score=threshold)
        print(json.dumps(search_result, indent=2, default=str))
        return

    # Handle call graph queries
    if has_cg_query:
        handle_cg_query(args, result)
        return

    # Summary only mode
    if args.summary:
        result = {
            "meta": result["meta"],
            "summary": result["summary"],
        }

    # Output
    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        if args.verbose:
            print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


def load_index(load_path: str, verbose: bool) -> dict[str, Any]:
    """Load an existing index file."""
    path = Path(load_path)
    if not path.exists():
        print(f"Error: Index file '{path}' does not exist", file=sys.stderr)
        sys.exit(1)
    if verbose:
        print(f"Loading index from: {path}", file=sys.stderr)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_codebase(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    """Scan the codebase and return the result."""
    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Error: Path '{root}' does not exist", file=sys.stderr)
        sys.exit(1)

    exclude = DEFAULT_EXCLUDE.copy()
    if args.exclude:
        exclude.extend(args.exclude)

    # Add directory exclusions from CLI
    if args.exclude_dirs:
        exclude.extend(args.exclude_dirs)

    # Add directory exclusions from config
    config_exclude = config.get("exclude", {})
    config_dirs = config_exclude.get("directories") or []
    if config_dirs:
        exclude.extend(config_dirs)

    # Add pattern exclusions from config
    config_patterns = config_exclude.get("patterns") or []
    if config_patterns:
        exclude.extend(config_patterns)

    # Add extension exclusions (normalize to have leading dot)
    exclude_extensions: set[str] = set()
    if args.exclude_ext:
        for ext in args.exclude_ext:
            if not ext.startswith('.'):
                ext = '.' + ext
            exclude_extensions.add(ext.lower())

    # Add extension exclusions from config
    config_exts = config_exclude.get("extensions") or []
    for ext in config_exts:
        if not ext.startswith('.'):
            ext = '.' + ext
        exclude_extensions.add(ext.lower())

    if args.verbose:
        print(f"Scanning: {root}", file=sys.stderr)
        if config_dirs:
            print(f"Config excluded directories: {config_dirs}", file=sys.stderr)
        if args.exclude_dirs:
            print(f"CLI excluded directories: {args.exclude_dirs}", file=sys.stderr)
        if config_exts:
            print(f"Config excluded extensions: {config_exts}", file=sys.stderr)
        if args.exclude_ext:
            print(f"CLI excluded extensions: {args.exclude_ext}", file=sys.stderr)

    scanner = CodebaseScanner(
        root=root,
        exclude=exclude,
        exclude_extensions=exclude_extensions,
        include_hash=not args.no_hash,
        config=config,
    )

    # Suppress SyntaxWarnings from scanned files (e.g., invalid escape sequences)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        return scanner.scan()


def handle_cg_query(args: argparse.Namespace, result: dict[str, Any]) -> None:
    """Handle call graph queries."""
    call_graph = result.get("call_graph", {})
    if not call_graph:
        print("Error: No call graph data available", file=sys.stderr)
        sys.exit(1)

    if args.callers:
        query_result = cg_query_callers(call_graph, args.callers)
        print(json.dumps(query_result, indent=2))


if __name__ == "__main__":
    main()
