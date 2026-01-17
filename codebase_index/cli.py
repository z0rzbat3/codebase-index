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

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive codebase inventory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codebase_index .                    # Scan current directory
  codebase_index ./src -o index.json  # Scan src, output to file
  codebase_index . --no-hash          # Skip file hashes (faster)
  codebase_index . --summary          # Only show summary

Configuration (for non-FastAPI projects):
  codebase_index --init-config        # Generate starter config (edit with LLM)
  codebase_index . --config my.yaml   # Use custom config for Django/Flask/etc.

Exclusion examples:
  codebase_index . --exclude-dirs docs vendor  # Exclude specific directories
  codebase_index . --exclude-ext .md .txt      # Exclude file extensions
  codebase_index . --exclude "*.generated.*"   # Exclude patterns

Call graph queries (use with --load for speed):
  codebase_index --load index.json --cg-query ChatService.stream_chat
  codebase_index --load index.json --cg-file src/api/services/chat_service.py
  codebase_index --load index.json --cg-callers AgentFactory.create

LLM Workflow (for any project):
  1. Run: codebase_index --init-config > codebase_index.yaml
  2. Ask Claude/GPT: "Customize this config for my Django project"
  3. Run: codebase_index . --config codebase_index.yaml -o index.json
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
    has_cg_query = args.cg_query or args.cg_file or args.cg_callers

    # Load existing index or scan
    if args.load:
        result = load_index(args.load, args.verbose)
    else:
        result = scan_codebase(args, config)

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
