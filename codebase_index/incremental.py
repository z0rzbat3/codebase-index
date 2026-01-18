"""
Incremental updater for codebase_index.

Updates an existing index by only re-scanning files that have changed,
rather than doing a full re-scan of the entire codebase.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """
    Incrementally update an existing index.

    Compares file hashes to detect changes and only re-scans modified files.
    Much faster than full re-scan for large codebases with few changes.
    """

    def __init__(
        self,
        root: Path,
        index_data: dict[str, Any],
        exclude: list[str],
        exclude_extensions: set[str] | None = None,
    ) -> None:
        """
        Initialize the incremental updater.

        Args:
            root: Root directory of the codebase.
            index_data: The existing index data to update.
            exclude: Patterns to exclude from scanning.
            exclude_extensions: File extensions to exclude.
        """
        self.root = root
        self.index_data = index_data
        self.exclude = exclude
        self.exclude_extensions = exclude_extensions or set()

        # Build lookup of existing files by path
        self._existing_files: dict[str, dict[str, Any]] = {}
        for file_info in index_data.get("files", []):
            path = file_info.get("path", "")
            self._existing_files[path] = file_info

    def update(self, scanner: Any) -> dict[str, Any]:
        """
        Perform incremental update.

        Args:
            scanner: CodebaseScanner instance to use for re-scanning files.

        Returns:
            Dictionary with update results and statistics.
        """
        start_time = time.time()

        result = {
            "added": [],
            "updated": [],
            "deleted": [],
            "unchanged": 0,
            "errors": [],
            "duration_ms": 0,
        }

        # Get current files in codebase
        current_files = self._get_current_files()

        # Track which existing files we've seen
        seen_paths = set()

        # Check each current file
        for file_path in current_files:
            rel_path = str(file_path.relative_to(self.root))
            seen_paths.add(rel_path)

            existing = self._existing_files.get(rel_path)

            if existing is None:
                # New file - needs scanning
                result["added"].append(rel_path)
            else:
                # Existing file - check if changed
                current_hash = self._compute_hash(file_path)
                existing_hash = existing.get("hash")

                if current_hash != existing_hash:
                    result["updated"].append(rel_path)
                else:
                    result["unchanged"] += 1

        # Find deleted files
        for rel_path in self._existing_files:
            if rel_path not in seen_paths:
                result["deleted"].append(rel_path)

        # Now perform the actual updates
        updated_index = self._apply_updates(scanner, result)

        result["duration_ms"] = int((time.time() - start_time) * 1000)

        return {
            "status": "updated",
            "changes": result,
            "index": updated_index,
        }

    def _get_current_files(self) -> list[Path]:
        """Get list of current files in codebase (respecting exclusions and supported parsers)."""
        from codebase_index.parsers.base import ParserRegistry

        # Get supported extensions from ParserRegistry
        supported_extensions = set(ParserRegistry._extension_map.keys())

        files = []

        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue

            # Check exclusions
            rel_path = str(file_path.relative_to(self.root))

            # Check directory exclusions
            if any(excl in rel_path for excl in self.exclude):
                continue

            # Check extension exclusions
            suffix = file_path.suffix.lower()
            if suffix in self.exclude_extensions:
                continue

            # Only include files with supported parsers
            # This prevents marking unsupported files (like .md, .txt) as "added"
            if suffix not in supported_extensions:
                # But keep files that were in the original index
                # (in case they were added with a custom parser)
                if rel_path not in self._existing_files:
                    continue

            files.append(file_path)

        return files

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except (OSError, IOError) as e:
            logger.warning("Could not hash %s: %s", file_path, e)
            return ""

    def _apply_updates(
        self,
        scanner: Any,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply the detected changes to create updated index.

        Args:
            scanner: CodebaseScanner to use for re-scanning.
            changes: Dictionary with added/updated/deleted file lists.

        Returns:
            Updated index data.
        """
        # Keys that contain per-file data and need to be rebuilt during update
        REBUILD_KEYS = {"files", "api_endpoints", "schemas", "router_prefixes"}

        # Start by copying all analysis data from existing index
        # This preserves semantic embeddings, summaries, and other analysis results
        updated = {}
        for key, value in self.index_data.items():
            if key in REBUILD_KEYS:
                continue  # Will be rebuilt below
            # Deep copy mutable structures to avoid modifying original
            if isinstance(value, dict):
                updated[key] = copy.deepcopy(value)
            elif isinstance(value, list):
                updated[key] = copy.deepcopy(value)
            else:
                updated[key] = value

        # Initialize the keys that need rebuilding
        updated["files"] = []
        updated["api_endpoints"] = []
        updated["schemas"] = []
        updated["router_prefixes"] = {}

        # Files to re-scan
        files_to_scan = set(changes["added"]) | set(changes["updated"])

        # Copy unchanged files
        for file_info in self.index_data.get("files", []):
            rel_path = file_info.get("path", "")

            # Skip deleted files
            if rel_path in changes["deleted"]:
                continue

            # Skip files that need re-scanning
            if rel_path in files_to_scan:
                continue

            # Keep unchanged file
            updated["files"].append(file_info)

        # Copy endpoints from unchanged files
        unchanged_files = {
            f.get("path") for f in updated["files"]
        }
        for endpoint in self.index_data.get("api_endpoints", []):
            if endpoint.get("file") in unchanged_files:
                updated["api_endpoints"].append(endpoint)

        # Copy schemas from unchanged files
        for schema in self.index_data.get("schemas", []):
            if schema.get("file") in unchanged_files:
                updated["schemas"].append(schema)

        # Copy router prefixes from unchanged files
        for file_path, prefix in self.index_data.get("router_prefixes", {}).items():
            if file_path in unchanged_files:
                updated["router_prefixes"][file_path] = prefix

        # Re-scan changed/added files
        if files_to_scan:
            self._scan_files(scanner, files_to_scan, updated)

        # Remove deleted files from call graph
        for deleted_path in changes["deleted"]:
            keys_to_remove = [
                k for k in updated["call_graph"]
                if k.startswith(deleted_path + ":")
            ]
            for key in keys_to_remove:
                del updated["call_graph"][key]

        # Update metadata
        from datetime import datetime, timezone
        updated["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
        updated["meta"]["incremental_update"] = True
        updated["meta"]["changes"] = {
            "added": len(changes["added"]),
            "updated": len(changes["updated"]),
            "deleted": len(changes["deleted"]),
        }

        # Update summary counts
        updated["summary"]["total_files"] = len(updated["files"])
        updated["summary"]["api_endpoints_count"] = len(updated["api_endpoints"])
        updated["summary"]["schemas_count"] = len(updated["schemas"])

        return updated

    def _scan_files(
        self,
        scanner: Any,
        file_paths: set[str],
        updated: dict[str, Any],
    ) -> None:
        """
        Scan specific files and add results to updated index.

        Args:
            scanner: CodebaseScanner instance.
            file_paths: Set of relative file paths to scan.
            updated: Index dictionary to update.
        """
        from codebase_index.parsers.base import ParserRegistry

        for rel_path in file_paths:
            file_path = self.root / rel_path

            if not file_path.exists():
                continue

            try:
                # Determine language and get parser
                suffix = file_path.suffix.lower()
                language = self._detect_language(suffix)

                # Build basic file info
                stat = file_path.stat()
                file_info = {
                    "path": rel_path,
                    "size": stat.st_size,
                    "language": language,
                    "hash": self._compute_hash(file_path),
                    "exports": {},
                }

                # Try to parse the file
                parser, _ = ParserRegistry.get_parser(file_path, scanner.config)
                if parser:
                    try:
                        exports = parser.scan(file_path)
                        file_info["exports"] = exports

                        # Extract endpoints
                        if exports.get("fastapi_routes"):
                            # Get router prefix if available
                            router_name = file_path.stem
                            # Try to get prefix from existing data
                            prefix = ""
                            for fp, pfx in self.index_data.get("router_prefixes", {}).items():
                                if Path(fp).stem == router_name:
                                    prefix = pfx
                                    updated["router_prefixes"][rel_path] = prefix
                                    break

                            for route in exports["fastapi_routes"]:
                                full_path = prefix + (route.get("path") or "")
                                updated["api_endpoints"].append({
                                    **route,
                                    "full_path": full_path,
                                    "file": rel_path,
                                })

                        # Extract schemas
                        if exports.get("schemas"):
                            for schema in exports["schemas"]:
                                updated["schemas"].append({
                                    **schema,
                                    "file": rel_path,
                                })

                        # Update call graph
                        if exports.get("functions"):
                            for func in exports["functions"]:
                                func_key = f"{rel_path}:{func.get('name')}"
                                updated["call_graph"][func_key] = {
                                    "file": rel_path,
                                    "line": func.get("line"),
                                    "calls": func.get("calls", []),
                                }

                    except Exception as e:
                        logger.debug("Error parsing %s: %s", rel_path, e)

                updated["files"].append(file_info)

            except Exception as e:
                logger.warning("Error scanning %s: %s", rel_path, e)

    def _detect_language(self, suffix: str) -> str:
        """Detect language from file extension."""
        lang_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".sql": "sql",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
        }
        return lang_map.get(suffix, "unknown")


def incremental_update(
    root: Path,
    index_data: dict[str, Any],
    exclude: list[str],
    exclude_extensions: set[str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convenience function to perform incremental update.

    Args:
        root: Root directory of the codebase.
        index_data: Existing index data.
        exclude: Patterns to exclude.
        exclude_extensions: File extensions to exclude.
        config: Configuration dictionary.

    Returns:
        Update result with changes and new index.
    """
    from codebase_index.scanner import CodebaseScanner

    # Create scanner for re-scanning files
    scanner = CodebaseScanner(
        root=root,
        exclude=exclude,
        exclude_extensions=exclude_extensions or set(),
        include_hash=True,
        config=config or {},
    )

    # Create updater and run
    updater = IncrementalUpdater(
        root=root,
        index_data=index_data,
        exclude=exclude,
        exclude_extensions=exclude_extensions,
    )

    return updater.update(scanner)
