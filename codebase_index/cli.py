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

import shutil

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


# Index schema template - describes the structure of index.json
INDEX_SCHEMA = {
    "meta": {
        "_description": "Metadata about the scan",
        "scanned_at": "ISO timestamp of scan",
        "root": "Root directory scanned",
        "git_branch": "Current git branch (if git repo)",
        "git_commit": "Current git commit hash",
        "version": "codebase-index version",
    },
    "summary": {
        "_description": "Aggregate statistics",
        "total_files": "int - Number of files scanned",
        "total_lines": "int - Total lines of code",
        "total_functions": "int - Function count",
        "total_classes": "int - Class count",
        "total_methods": "int - Method count",
        "by_language": "dict - Files/lines per language",
        "by_category": "dict - Files grouped by type (routes, models, etc.)",
    },
    "symbol_index": {
        "_description": "All code symbols indexed",
        "functions": "[{name, file, line, signature, docstring, async}]",
        "classes": "[{name, file, line, bases, docstring, method_count}]",
        "methods": "[{name, class, file, line, signature, docstring, async}]",
    },
    "call_graph": {
        "_description": "Function call relationships",
        "_format": "{symbol_key: {file, line, calls: [called_symbols]}}",
        "_example": "file.py:func_name → {file: 'file.py', line: 10, calls: ['other_func']}",
    },
    "files": {
        "_description": "List of all scanned files",
        "_format": "[{path, size, language, hash, exports}]",
    },
    "centrality": {
        "_description": "Symbol importance analysis",
        "core_components": "High in-degree (many callers) - critical code",
        "hub_components": "High out-degree (calls many) - orchestrators",
        "utility_components": "Balanced - helper functions",
        "isolated_components": "Low connectivity - possibly dead code",
        "classifications": "{symbol: classification}",
    },
    "semantic": {
        "_description": "Embeddings for semantic search",
        "embeddings": "[[float]] - Vector embeddings",
        "symbols": "[str] - Symbol names matching embeddings",
        "model": "Model used for embeddings",
        "count": "Number of embedded symbols",
    },
    "dependencies": {
        "_description": "Project dependencies",
        "python": "[packages from requirements.txt/pyproject.toml]",
        "node": "[packages from package.json]",
    },
    "api_endpoints": {
        "_description": "HTTP routes/endpoints",
        "_format": "[{method, path, file, line, handler, auth_required}]",
    },
    "database": {
        "_description": "Database tables and schemas",
        "tables": "[{name, file, line, columns}]",
    },
    "test_coverage": {
        "_description": "Test file mapping",
        "test_files": "[paths to test files]",
        "source_to_test": "{source_file: [test_files]}",
    },
}


def get_index_schema() -> dict:
    """Return the index schema template."""
    return INDEX_SCHEMA


def get_keys_at_path(data: dict, path: str, limit: int | None = None) -> dict:
    """List keys at a given JSON path.

    Args:
        data: The index data
        path: Dot-notation path (empty string for root)
        limit: Optional limit on results

    Returns:
        Dict with keys and their types/counts
    """
    # Navigate to path
    current = data
    if path:
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return {"error": f"Index {idx} out of range", "path": path}
            else:
                return {"error": f"Path '{part}' not found", "path": path}

    # Describe what's at this path
    if isinstance(current, dict):
        keys_info = []
        for k, v in current.items():
            if isinstance(v, dict):
                keys_info.append({"key": k, "type": "object", "count": len(v)})
            elif isinstance(v, list):
                keys_info.append({"key": k, "type": "array", "count": len(v)})
            else:
                keys_info.append({"key": k, "type": type(v).__name__, "value": _truncate(v)})

        if limit:
            keys_info = keys_info[:limit]

        return {"path": path or "(root)", "keys": keys_info}

    elif isinstance(current, list):
        # Show array info
        sample = current[:limit] if limit else current[:5]
        return {
            "path": path,
            "type": "array",
            "count": len(current),
            "sample": sample,
            "note": f"Use --path '{path}.0' to access first item" if current else None,
        }
    else:
        return {"path": path, "type": type(current).__name__, "value": current}


def _truncate(value, max_len: int = 50) -> str:
    """Truncate a value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def find_symbol_by_name(data: dict, name: str) -> dict:
    """Find a symbol by name across functions, classes, and methods.

    Args:
        data: The index data
        name: Symbol name to find (can be partial)

    Returns:
        Dict with matching symbols and their details
    """
    results = []
    symbol_index = data.get("symbol_index", {})
    call_graph = data.get("call_graph", {})

    name_lower = name.lower()

    # Search functions
    for func in symbol_index.get("functions", []):
        if name_lower in func.get("name", "").lower():
            func_copy = dict(func)
            func_copy["_type"] = "function"
            # Add call graph info
            key = f"{func['file']}:{func['name']}"
            if key in call_graph:
                func_copy["calls"] = call_graph[key].get("calls", [])
            results.append(func_copy)

    # Search classes
    for cls in symbol_index.get("classes", []):
        if name_lower in cls.get("name", "").lower():
            cls_copy = dict(cls)
            cls_copy["_type"] = "class"
            # Find methods for this class
            methods = [m for m in symbol_index.get("methods", [])
                      if m.get("class") == cls["name"]]
            cls_copy["methods"] = [m["name"] for m in methods]
            results.append(cls_copy)

    # Search methods
    for method in symbol_index.get("methods", []):
        full_name = f"{method.get('class', '')}.{method.get('name', '')}"
        if name_lower in full_name.lower() or name_lower in method.get("name", "").lower():
            method_copy = dict(method)
            method_copy["_type"] = "method"
            # Add call graph info
            key = f"{method['file']}:{method.get('class', '')}.{method['name']}"
            if key in call_graph:
                method_copy["calls"] = call_graph[key].get("calls", [])
            results.append(method_copy)

    if not results:
        return {"query": name, "count": 0, "results": [], "hint": "Try a partial name or check --keys symbol_index"}

    return {"query": name, "count": len(results), "results": results}


def get_data_at_path(data: dict, path: str, limit: int | None = None) -> dict:
    """Extract data at a dot-notation path.

    Args:
        data: The index data
        path: Dot-notation path (e.g., 'symbol_index.functions')
        limit: Optional limit for array results

    Returns:
        The data at the path, or error info
    """
    current = data
    parts = path.split(".")

    for i, part in enumerate(parts):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return {
                    "error": f"Index {idx} out of range (array has {len(current)} items)",
                    "path": ".".join(parts[:i+1]),
                }
        else:
            # Try to find similar keys for helpful error
            available = list(current.keys()) if isinstance(current, dict) else []
            return {
                "error": f"Key '{part}' not found",
                "path": ".".join(parts[:i+1]),
                "available_keys": available[:10] if available else None,
            }

    # Apply limit to arrays
    if isinstance(current, list) and limit:
        return {
            "path": path,
            "total": len(current),
            "limited_to": limit,
            "data": current[:limit],
        }

    return {"path": path, "data": current}


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
INDEX NAVIGATION (for LLMs traversing large indexes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --schema             Show index structure template (what fields exist)
  --keys [PATH]        List keys at path (empty=root). Example: --keys symbol_index
  --get SYMBOL         Get full details for a symbol by name
  --path PATH          Extract data at dot-notation path. Example: --path summary.total_files
  --limit N            Limit array results (use with --path or --keys)

Examples:
  codebase-index --load index.json --schema                    # See structure
  codebase-index --load index.json --keys                      # List top-level keys
  codebase-index --load index.json --keys symbol_index         # List keys under symbol_index
  codebase-index --load index.json --get CodebaseScanner       # Full info for a symbol
  codebase-index --load index.json --path "symbol_index.functions" --limit 5

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

    # Documentation maintenance setup
    docs_group = parser.add_argument_group("Documentation Maintenance")
    docs_group.add_argument(
        "--init-docs",
        action="store_true",
        help="Initialize documentation maintenance system (Claude skills, workflows, hooks)",
    )
    docs_group.add_argument(
        "--init-docs-force",
        action="store_true",
        help="Force overwrite existing files when initializing docs system",
    )
    docs_group.add_argument(
        "--init-docs-skip-hooks",
        action="store_true",
        help="Skip pre-commit hook installation",
    )
    docs_group.add_argument(
        "--init-docs-skip-workflow",
        action="store_true",
        help="Skip GitHub workflow installation",
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

    # Index navigation options (for LLMs)
    nav_group = parser.add_argument_group(
        "Index Navigation",
        "Query the index structure directly (useful for LLMs exploring large indexes)"
    )
    nav_group.add_argument(
        "--schema",
        action="store_true",
        help="Show index structure template with field descriptions",
    )
    nav_group.add_argument(
        "--keys",
        nargs="?",
        const="",
        metavar="PATH",
        help="List keys at JSON path (omit PATH for root keys). E.g., --keys symbol_index",
    )
    nav_group.add_argument(
        "--get",
        metavar="SYMBOL",
        help="Get full details for a symbol by name (searches functions, classes, methods)",
    )
    nav_group.add_argument(
        "--path",
        dest="json_path",
        metavar="JSONPATH",
        help="Extract data at dot-notation path. E.g., --path summary.total_files",
    )
    nav_group.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit array results when using --path or --keys (default: no limit)",
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


def get_templates_dir() -> Path:
    """Get the path to bundled templates directory."""
    # Try importlib.resources first (Python 3.9+)
    try:
        from importlib.resources import files
        return Path(str(files("codebase_index") / "templates"))
    except (ImportError, TypeError):
        # Fallback: relative to this file
        return Path(__file__).parent / "templates"


def init_docs(
    force: bool = False,
    skip_hooks: bool = False,
    skip_workflow: bool = False,
) -> dict[str, list[str]]:
    """Initialize documentation maintenance system.

    Copies Claude skills, agents, workflows, and hooks to the current project.

    Args:
        force: Overwrite existing files
        skip_hooks: Don't install pre-commit hook
        skip_workflow: Don't copy GitHub workflow

    Returns:
        Dict with 'created', 'skipped', and 'errors' lists
    """
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        return {
            "created": [],
            "skipped": [],
            "errors": [f"Templates directory not found: {templates_dir}"],
        }

    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    # 1. Copy .claude/skills/generate-docs/
    src_skill = templates_dir / "claude" / "skills" / "generate-docs"
    dst_skill = Path(".claude/skills/generate-docs")
    if dst_skill.exists() and not force:
        skipped.append(str(dst_skill))
    else:
        try:
            dst_skill.parent.mkdir(parents=True, exist_ok=True)
            if dst_skill.exists():
                shutil.rmtree(dst_skill)
            shutil.copytree(src_skill, dst_skill)
            created.append(str(dst_skill))
        except Exception as e:
            errors.append(f"Failed to copy skill: {e}")

    # 2. Copy .claude/agents/doc-generator.md
    src_agent = templates_dir / "claude" / "agents" / "doc-generator.md"
    dst_agent = Path(".claude/agents/doc-generator.md")
    if dst_agent.exists() and not force:
        skipped.append(str(dst_agent))
    else:
        try:
            dst_agent.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_agent, dst_agent)
            created.append(str(dst_agent))
        except Exception as e:
            errors.append(f"Failed to copy agent: {e}")

    # 3. Create .doc-config.json
    dst_config = Path(".doc-config.json")
    if dst_config.exists() and not force:
        skipped.append(str(dst_config))
    else:
        try:
            config_content = {
                "version": "2.0",
                "strategy": "mirror",
                "description": "Documentation mapping configuration for /generate-docs skill",
                "source_root": "src",
                "docs_root": "docs",
                "index_files": True,
                "mappings": [
                    {
                        "source": "src/api/routers",
                        "docs": "docs/api/routers",
                        "template": "api-endpoint",
                        "extensions": [".py"],
                    },
                    {
                        "source": "src/db/models",
                        "docs": "docs/db/models",
                        "template": "db-model",
                        "extensions": [".py"],
                    },
                    {
                        "source": "src/services",
                        "docs": "docs/services",
                        "template": "module",
                        "extensions": [".py"],
                    },
                ],
                "exclude": [
                    "**/__pycache__/**",
                    "**/__init__.py",
                    "**/__main__.py",
                    "**/test_*.py",
                    "**/*_test.py",
                    "**/node_modules/**",
                    "**/dist/**",
                    "**/.venv/**",
                ],
                "validation": {
                    "check_references": True,
                    "check_symbols": True,
                    "forbidden_terms": [],
                    "required_sections": ["Overview"],
                },
            }
            with open(dst_config, "w", encoding="utf-8") as f:
                json.dump(config_content, f, indent=2)
                f.write("\n")
            created.append(str(dst_config))
        except Exception as e:
            errors.append(f"Failed to create config: {e}")

    # 4. Create .doc-manifest.json
    dst_manifest = Path(".doc-manifest.json")
    if dst_manifest.exists() and not force:
        skipped.append(str(dst_manifest))
    else:
        try:
            manifest_content = {
                "version": "2.0",
                "strategy": "mirror",
                "last_updated": None,
                "files": {},
                "indexes": {},
            }
            with open(dst_manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_content, f, indent=2)
                f.write("\n")
            created.append(str(dst_manifest))
        except Exception as e:
            errors.append(f"Failed to create manifest: {e}")

    # 5. Install pre-commit hook (append if exists)
    if not skip_hooks:
        src_hook = templates_dir / "hooks" / "pre-commit-docs"
        dst_hook = Path(".git/hooks/pre-commit")

        if not Path(".git").exists():
            skipped.append(str(dst_hook) + " (not a git repo)")
        elif dst_hook.exists():
            # Check if hook already has doc staleness check
            try:
                hook_content = dst_hook.read_text(encoding="utf-8")
                if "check_doc_staleness" in hook_content:
                    skipped.append(str(dst_hook) + " (already has doc check)")
                else:
                    # Append our hook
                    with open(dst_hook, "a", encoding="utf-8") as f:
                        f.write("\n")
                        f.write(src_hook.read_text(encoding="utf-8"))
                    created.append(str(dst_hook) + " (appended)")
            except Exception as e:
                errors.append(f"Failed to update hook: {e}")
        else:
            try:
                dst_hook.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_hook, dst_hook)
                dst_hook.chmod(0o755)
                created.append(str(dst_hook))
            except Exception as e:
                errors.append(f"Failed to create hook: {e}")

    # 6. Copy GitHub workflow
    if not skip_workflow:
        src_workflow = templates_dir / "workflows" / "docs-maintenance.yml"
        dst_workflow = Path(".github/workflows/docs-maintenance.yml")

        if dst_workflow.exists() and not force:
            skipped.append(str(dst_workflow))
        else:
            try:
                dst_workflow.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_workflow, dst_workflow)
                created.append(str(dst_workflow))
            except Exception as e:
                errors.append(f"Failed to copy workflow: {e}")

    return {"created": created, "skipped": skipped, "errors": errors}


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Handle --init-config: just output the template and exit
    if args.init_config:
        print(get_config_template())
        return

    # Handle --init-docs: initialize documentation maintenance system
    if args.init_docs:
        result = init_docs(
            force=args.init_docs_force,
            skip_hooks=args.init_docs_skip_hooks,
            skip_workflow=args.init_docs_skip_workflow,
        )

        print("Initializing documentation maintenance system...\n")

        if result["created"]:
            print("Created:")
            for path in result["created"]:
                print(f"  + {path}")

        if result["skipped"]:
            print("\nSkipped (already exist):")
            for path in result["skipped"]:
                print(f"  - {path}")

        if result["errors"]:
            print("\nErrors:")
            for error in result["errors"]:
                print(f"  ! {error}")

        print("\nNext steps:")
        print("  1. Edit .doc-config.json for your project structure")
        print("  2. Run /generate-docs to create initial documentation")
        print("  3. Add ANTHROPIC_API_KEY to GitHub Secrets (if using workflow)")
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

    # Handle --schema: show index structure template
    if args.schema:
        schema = get_index_schema()
        print(json.dumps(schema, indent=2))
        return

    # Handle --keys: list keys at a path
    if args.keys is not None:
        keys_result = get_keys_at_path(result, args.keys, limit=args.limit)
        print(json.dumps(keys_result, indent=2, default=str))
        return

    # Handle --get: find symbol by name
    if args.get:
        symbol_result = find_symbol_by_name(result, args.get)
        print(json.dumps(symbol_result, indent=2, default=str))
        return

    # Handle --path: extract data at path
    if args.json_path:
        path_result = get_data_at_path(result, args.json_path, limit=args.limit)
        print(json.dumps(path_result, indent=2, default=str))
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
