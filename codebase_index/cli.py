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
from codebase_index.call_graph import cg_query_function, cg_query_file, cg_query_callers
from codebase_index.analyzers.staleness import StalenessChecker
from codebase_index.analyzers.test_mapper import TestMapper
from codebase_index.analyzers.impact import ImpactAnalyzer
from codebase_index.analyzers.schema_mapper import SchemaMapper
from codebase_index.analyzers.coupling import CouplingAnalyzer

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive codebase inventory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  codebase-index .                    # Scan current directory
  codebase-index ./src -o index.json  # Scan src, output to file
  codebase-index . --summary          # Quick overview only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM AGENT WORKFLOW (Recommended Sequence)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: EXPLORE - Run initial scan with defaults
  codebase-index . --summary --no-hash

Step 2: ANALYZE - Review the output, identify:
  - What framework is used (FastAPI, Django, Flask, Express, etc.)
  - Project structure (where are routes, models, tests)
  - What's missing or incorrectly detected

Step 3: CONFIGURE (if needed) - Create custom config
  codebase-index --init-config > codebase_index.yaml
  # Then customize the YAML for the project's framework/patterns

Step 4: SCAN - Run full scan with config
  codebase-index . --config codebase_index.yaml -o index.json

Step 5: QUERY - Use analysis commands as needed
  codebase-index --load index.json --check          # Check staleness
  codebase-index --load index.json --impact file.py # Impact analysis
  codebase-index --load index.json --tests-for Foo  # Find tests
  codebase-index --load index.json --schema User    # Schema usage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIG FILE GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The config file controls pattern matching. Key sections:

  auth.parameters:   Regex patterns for auth in function signatures
                     e.g., "Depends\\s*\\(\\s*get_current_user"

  auth.decorators:   Regex patterns for auth decorators
                     e.g., "@login_required", "@jwt_required"

  models.patterns:   How to detect ORM models (base_class or marker)
  schemas.patterns:  How to detect Pydantic/serializer schemas
  routes.patterns:   How to detect API endpoints
  exclude:           Directories/extensions/patterns to skip

When customizing:
  - Use regex patterns (remember to escape backslashes in YAML)
  - Test incrementally: change one section, re-run, verify
  - Check --verbose output to see what patterns are being used

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYSIS QUERIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --check              Check if index is stale (files changed since scan)
  --tests-for SYMBOL   Find tests for a function/class
  --impact FILE        Show what depends on a file (callers, tests, endpoints)
  --schema NAME        Find endpoints using a schema
  --cg-query FUNC      What does FUNC call?
  --cg-callers FUNC    What calls FUNC?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISCLAIMER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This tool uses static analysis (AST parsing + regex patterns). It may:

  - MISS things: Dynamic routes, metaprogramming, runtime-generated code,
    unusual patterns not covered by default config

  - FALSE POSITIVES: Patterns that look like routes/models but aren't,
    inherited auth that isn't detected, similar naming conventions

For best results:
  - Always verify critical findings against actual source code
  - Customize the config for your specific framework/patterns
  - Use --verbose to understand what's being detected and why
  - Report issues: https://github.com/anthropics/codebase-index/issues
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
        "--cg-query",
        metavar="FUNC",
        help="What does FUNC call? (fuzzy match on function name)",
    )
    cg_group.add_argument(
        "--cg-file",
        metavar="FILE",
        help="Show call graph for all functions in FILE",
    )
    cg_group.add_argument(
        "--cg-callers",
        metavar="FUNC",
        help="What functions call FUNC? (inverse lookup)",
    )

    # Analysis query options
    analysis_group = parser.add_argument_group("Analysis Queries")
    analysis_group.add_argument(
        "--check",
        action="store_true",
        help="Check if loaded index is stale (use with --load)",
    )
    analysis_group.add_argument(
        "--tests-for",
        metavar="SYMBOL",
        help="Find tests for a function/class (e.g., 'AgentFactory.create')",
    )
    analysis_group.add_argument(
        "--impact",
        metavar="FILE",
        help="Show impact radius: callers, affected tests, affected endpoints",
    )
    analysis_group.add_argument(
        "--schema",
        metavar="NAME",
        help="Find endpoints using a schema (e.g., 'AgentConfig')",
    )
    analysis_group.add_argument(
        "--coupled-with",
        metavar="FILE",
        help="Find files tightly coupled to FILE (likely need changes together)",
    )
    analysis_group.add_argument(
        "--summary-for",
        metavar="SYMBOL",
        help="Get LLM-generated summary for a function/method (e.g., 'scan_file', 'Parser.parse')",
    )
    analysis_group.add_argument(
        "--doc-for",
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
    advanced_group.add_argument(
        "--generate-summaries",
        action="store_true",
        help="Generate LLM summaries for functions (requires API key)",
    )
    advanced_group.add_argument(
        "--force-summaries",
        action="store_true",
        help="Regenerate LLM summaries even for functions with existing docstrings",
    )
    advanced_group.add_argument(
        "--summary-provider",
        metavar="PROVIDER",
        choices=["openrouter", "anthropic", "openai"],
        help="Summary provider: openrouter, anthropic, openai (auto-detects from API key)",
    )
    advanced_group.add_argument(
        "--summary-model",
        metavar="MODEL",
        help="Model for summaries (e.g., anthropic/claude-3-haiku, gpt-4o-mini)",
    )
    advanced_group.add_argument(
        "--api-key",
        metavar="KEY",
        help="API key for summaries (alternative to environment variable)",
    )

    # Documentation generation
    docs_group = parser.add_argument_group("Documentation Generation")
    docs_group.add_argument(
        "--generate-docs",
        action="store_true",
        help="Generate documentation from the index",
    )
    docs_group.add_argument(
        "--output-dir",
        metavar="DIR",
        default="docs/generated",
        help="Output directory for generated docs (default: docs/generated)",
    )
    docs_group.add_argument(
        "--doc-layers",
        metavar="LAYERS",
        default="all",
        help="Comma-separated doc layers: api,modules,reference,architecture or 'all' (default: all)",
    )
    docs_group.add_argument(
        "--doc-diff",
        metavar="DIR",
        help="Check documentation freshness against source files in DIR",
    )
    docs_group.add_argument(
        "--doc-template",
        metavar="DIR",
        help="Custom Jinja2 templates directory for documentation generation",
    )
    docs_group.add_argument(
        "--init-templates",
        metavar="DIR",
        help="Export default documentation templates to DIR for customization",
    )
    docs_group.add_argument(
        "--watch",
        action="store_true",
        help="Watch for file changes and regenerate documentation automatically",
    )
    docs_group.add_argument(
        "--init-mkdocs",
        metavar="DIR",
        help="Generate mkdocs.yml config for docs in DIR (e.g., --init-mkdocs docs/)",
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

    # Handle --init-templates: export default templates
    if args.init_templates:
        from codebase_index.analyzers.templates import create_template_dir, check_jinja2_available

        if not check_jinja2_available():
            print(
                "Error: Jinja2 is required for templates.\n"
                "Install with: pip install jinja2",
                file=sys.stderr,
            )
            sys.exit(1)

        template_dir = Path(args.init_templates)
        create_template_dir(template_dir)
        print(f"Default templates exported to: {template_dir}")
        print("Customize the .j2 files and use with --doc-template")
        return

    # Handle --init-mkdocs: generate mkdocs.yml config
    if args.init_mkdocs:
        from codebase_index.analyzers.mkdocs import generate_mkdocs_config

        docs_dir = Path(args.init_mkdocs)
        if not docs_dir.exists():
            print(f"Error: Directory not found: {docs_dir}", file=sys.stderr)
            sys.exit(1)

        config_path = generate_mkdocs_config(docs_dir)
        print(f"Generated: {config_path}")
        print("Run 'mkdocs serve' to preview documentation")
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
    has_cg_query = args.cg_query or args.cg_file or args.cg_callers

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
        config_dirs = config_exclude.get("directories", [])
        if config_dirs:
            exclude.extend(config_dirs)
        config_patterns = config_exclude.get("patterns", [])
        if config_patterns:
            exclude.extend(config_patterns)

        exclude_extensions: set[str] = set()
        if args.exclude_ext:
            for ext in args.exclude_ext:
                if not ext.startswith('.'):
                    ext = '.' + ext
                exclude_extensions.add(ext.lower())

        # Add extension exclusions from config
        config_exts = config_exclude.get("extensions", [])
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

    # Handle --tests-for: find tests for a symbol
    if args.tests_for:
        mapper = TestMapper(result)
        tests_result = mapper.find_tests_for(args.tests_for)
        print(json.dumps(tests_result, indent=2, default=str))
        return

    # Handle --impact: analyze impact radius of a file
    if args.impact:
        analyzer = ImpactAnalyzer(result)
        impact_result = analyzer.analyze_file(args.impact)
        print(json.dumps(impact_result, indent=2, default=str))
        return

    # Handle --schema: find endpoints using a schema
    if args.schema:
        root = Path(args.path).resolve()
        mapper = SchemaMapper(result, root=root)
        schema_result = mapper.find_endpoints_for_schema(args.schema)
        print(json.dumps(schema_result, indent=2, default=str))
        return

    # Handle --coupled-with: find tightly coupled files
    if args.coupled_with:
        analyzer = CouplingAnalyzer(result)
        coupling_result = analyzer.analyze(args.coupled_with)
        print(json.dumps(coupling_result, indent=2, default=str))
        return

    # Handle --summary-for: get summary for a symbol
    if args.summary_for:
        symbol = args.summary_for
        symbol_index = result.get("symbol_index", {})
        matches = []

        # Search functions
        for func in symbol_index.get("functions", []):
            if symbol.lower() in func.get("name", "").lower():
                matches.append({
                    "type": "function",
                    "name": func.get("name"),
                    "file": func.get("file"),
                    "line": func.get("line"),
                    "summary": func.get("summary") or func.get("docstring") or "(no summary)",
                })

        # Search methods (Class.method format)
        for method in symbol_index.get("methods", []):
            method_name = method.get("name", "")
            class_name = method.get("class", "")
            full_name = f"{class_name}.{method_name}"

            if symbol.lower() in full_name.lower() or symbol.lower() in method_name.lower():
                matches.append({
                    "type": "method",
                    "name": full_name,
                    "file": method.get("file"),
                    "line": method.get("line"),
                    "summary": method.get("summary") or method.get("docstring") or "(no summary)",
                })

        if not matches:
            print(json.dumps({"symbol": symbol, "error": "No matching symbols found"}, indent=2))
        else:
            print(json.dumps({"symbol": symbol, "matches": matches}, indent=2))
        return

    # Handle --doc-for: generate full documentation for a symbol
    if args.doc_for:
        from codebase_index.analyzers.doc_generator import generate_doc_for_symbol

        root = Path(args.path).resolve()
        doc_result = generate_doc_for_symbol(result, args.doc_for, root=root)

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
            print(f"Building embeddings with model: {model_name}", file=sys.stderr)

        result = build_embeddings(result, root=root, model=model)

        if args.verbose:
            semantic = result.get("semantic", {})
            print(f"  Generated embeddings for {semantic.get('count', 0)} symbols", file=sys.stderr)
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

    # Handle --generate-summaries: LLM-generated function descriptions
    if args.generate_summaries:
        from codebase_index.analyzers.summaries import (
            generate_summaries,
            check_summaries_available,
            check_api_key,
            get_available_provider,
        )

        if not check_summaries_available():
            print(
                "Error: Summary generation requires httpx.\n"
                "Install with: pip install codebase-index[summaries]",
                file=sys.stderr,
            )
            sys.exit(1)

        api_key = getattr(args, 'api_key', None)

        if not api_key and not check_api_key():
            print(
                "Error: No API key found. Either:\n"
                "  - Pass --api-key KEY\n"
                "  - Set OPENROUTER_API_KEY (recommended - access any model)\n"
                "  - Set ANTHROPIC_API_KEY\n"
                "  - Set OPENAI_API_KEY",
                file=sys.stderr,
            )
            sys.exit(1)

        root = Path(args.path).resolve()
        provider = getattr(args, 'summary_provider', None)
        model = getattr(args, 'summary_model', None)

        # If API key passed via argument, need to specify provider too
        if api_key and not provider:
            print(
                "Error: --api-key requires --summary-provider to be specified.\n"
                "Example: --api-key sk-... --summary-provider openrouter",
                file=sys.stderr,
            )
            sys.exit(1)

        force = getattr(args, 'force_summaries', False)

        if args.verbose:
            detected_provider = provider or get_available_provider()
            print(f"Generating LLM summaries (provider: {detected_provider})...", file=sys.stderr)
            if force:
                print("  Force mode: regenerating all summaries", file=sys.stderr)

        result = generate_summaries(result, root, force=force, provider=provider, model=model, api_key=api_key)

        if args.verbose:
            summaries = result.get("summaries", {})
            stats = summaries.get("stats", {})
            print(f"  Provider: {summaries.get('provider', 'unknown')}", file=sys.stderr)
            print(f"  Model: {summaries.get('model', 'unknown')}", file=sys.stderr)
            print(f"  Generated: {stats.get('generated', 0)}", file=sys.stderr)
            print(f"  Cached: {stats.get('cached', 0)}", file=sys.stderr)
            print(f"  Skipped: {stats.get('skipped', 0)}", file=sys.stderr)
            if stats.get('errors', 0) > 0:
                print(f"  Errors: {stats.get('errors', 0)}", file=sys.stderr)

        # Fall through to output the updated index

    # Handle --generate-docs: generate documentation from index
    if args.generate_docs:
        from codebase_index.analyzers.doc_generator import (
            generate_api_reference,
            generate_module_readmes,
            generate_function_reference,
            generate_architecture_docs,
        )

        output_dir = Path(args.output_dir)
        layers = args.doc_layers.lower().split(",")
        template_dir = Path(args.doc_template) if args.doc_template else None

        if args.verbose:
            print(f"Generating documentation to: {output_dir}", file=sys.stderr)
            print(f"Layers: {layers}", file=sys.stderr)
            if template_dir:
                print(f"Using templates from: {template_dir}", file=sys.stderr)

        generated = []

        # Parse which layers to generate
        generate_all = "all" in layers
        generate_api = generate_all or "api" in layers
        generate_modules = generate_all or "modules" in layers
        generate_reference = generate_all or "reference" in layers
        generate_architecture = generate_all or "architecture" in layers

        # Generate API reference
        if generate_api:
            api_result = generate_api_reference(result, output_dir, template_dir=template_dir)
            generated.append(api_result)
            if args.verbose:
                print(f"  API: {api_result.get('endpoints', 0)} endpoints in {api_result.get('routers', 0)} routers", file=sys.stderr)

        # Generate Module READMEs
        if generate_modules:
            modules_result = generate_module_readmes(result, output_dir, template_dir=template_dir)
            generated.append(modules_result)
            if args.verbose:
                print(f"  Modules: {modules_result.get('modules', 0)} modules documented", file=sys.stderr)

        # Generate Function Reference
        if generate_reference:
            root = Path(args.path).resolve()
            ref_result = generate_function_reference(result, output_dir, root=root, template_dir=template_dir)
            generated.append(ref_result)
            if args.verbose:
                print(f"  Reference: {ref_result.get('symbols', 0)} symbols in {ref_result.get('modules', 0)} files", file=sys.stderr)

        # Generate Architecture docs
        if generate_architecture:
            arch_result = generate_architecture_docs(
                result,
                output_dir,
                provider=getattr(args, "summary_provider", None),
                model=getattr(args, "summary_model", None),
                api_key=getattr(args, "api_key", None),
                template_dir=template_dir,
            )
            generated.append(arch_result)
            if args.verbose:
                print(f"  Architecture: {arch_result.get('components', 0)} components documented", file=sys.stderr)

        # Output summary
        summary = {
            "documentation": {
                "output_dir": str(output_dir),
                "layers": layers,
                "generated": generated,
            }
        }
        print(json.dumps(summary, indent=2))

        # If --watch is specified, start watching for changes
        if args.watch:
            from codebase_index.analyzers.watcher import watch_and_regenerate

            root = Path(args.path).resolve()

            def regenerate():
                """Regenerate documentation."""
                # Re-scan the codebase
                nonlocal result
                result = scan_codebase(args, config)

                # Regenerate each layer
                if generate_api:
                    generate_api_reference(result, output_dir, template_dir=template_dir)
                if generate_modules:
                    generate_module_readmes(result, output_dir, template_dir=template_dir)
                if generate_reference:
                    generate_function_reference(result, output_dir, root=root, template_dir=template_dir)
                if generate_architecture:
                    generate_architecture_docs(
                        result,
                        output_dir,
                        provider=getattr(args, "summary_provider", None),
                        model=getattr(args, "summary_model", None),
                        api_key=getattr(args, "api_key", None),
                        template_dir=template_dir,
                    )

            watch_and_regenerate(root, regenerate, verbose=args.verbose)

        return

    # Handle --doc-diff: check documentation freshness
    if args.doc_diff:
        from codebase_index.analyzers.doc_generator import check_doc_freshness

        doc_dir = Path(args.doc_diff)
        root = Path(args.path).resolve()

        if not doc_dir.exists():
            print(f"Error: Documentation directory '{doc_dir}' does not exist", file=sys.stderr)
            sys.exit(1)

        diff_result = check_doc_freshness(result, doc_dir, root)

        if args.verbose:
            print(f"Documentation freshness check: {diff_result.get('summary', '')}", file=sys.stderr)

        print(json.dumps(diff_result, indent=2))
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
    config_dirs = config_exclude.get("directories", [])
    if config_dirs:
        exclude.extend(config_dirs)

    # Add pattern exclusions from config
    config_patterns = config_exclude.get("patterns", [])
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
    config_exts = config_exclude.get("extensions", [])
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

    if args.cg_query:
        query_result = cg_query_function(call_graph, args.cg_query)
    elif args.cg_file:
        query_result = cg_query_file(call_graph, args.cg_file)
    elif args.cg_callers:
        query_result = cg_query_callers(call_graph, args.cg_callers)
    else:
        return

    print(json.dumps(query_result, indent=2))


if __name__ == "__main__":
    main()
