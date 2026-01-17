"""
WebSocket scanner for codebase_index.

Scans for WebSocket endpoints in FastAPI and other frameworks.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class WebSocketScanner:
    """Scan for WebSocket endpoints."""

    def scan(self, root: Path, exclude: list[str]) -> dict[str, Any]:
        """
        Scan for WebSocket endpoints.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            Dictionary with endpoint list and total count.
        """
        result: dict[str, Any] = {
            "endpoints": [],
            "total": 0,
        }

        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            endpoints = self._scan_file(py_file, root)
            result["endpoints"].extend(endpoints)

        result["total"] = len(result["endpoints"])
        return result

    def _scan_file(self, filepath: Path, root: Path) -> list[dict[str, Any]]:
        """Scan a file for WebSocket endpoints."""
        endpoints: list[dict[str, Any]] = []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                # @router.websocket("/path") or @app.websocket("/path")
                match = re.search(r'@\w+\.websocket\s*\(\s*["\']([^"\']+)["\']', line)
                if match:
                    path = match.group(1)

                    # Find the function name
                    handler = None
                    for j in range(i, min(i + 5, len(lines))):
                        func_match = re.match(r'\s*async\s+def\s+(\w+)', lines[j])
                        if func_match:
                            handler = func_match.group(1)
                            break

                    endpoints.append({
                        "path": path,
                        "handler": handler,
                        "file": rel_path,
                        "line": i,
                    })

                # Also check for WebSocket type hints in function params
                if "WebSocket" in line and "def " in line:
                    func_match = re.search(r'def\s+(\w+)\s*\([^)]*WebSocket', line)
                    if func_match:
                        # Check if we already captured this as an endpoint
                        handler_name = func_match.group(1)
                        if not any(e.get("handler") == handler_name for e in endpoints):
                            endpoints.append({
                                "path": "(inferred from type hint)",
                                "handler": handler_name,
                                "file": rel_path,
                                "line": i,
                            })

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)

        return endpoints
