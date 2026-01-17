"""
Middleware scanner for codebase_index.

Scans for FastAPI/Starlette middleware configuration.
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


class MiddlewareScanner:
    """Scan for FastAPI/Starlette middleware configuration."""

    # Known middleware types
    KNOWN_MIDDLEWARE = {
        "CORSMiddleware": "CORS - Cross-Origin Resource Sharing",
        "GZipMiddleware": "GZip - Response compression",
        "TrustedHostMiddleware": "Security - Host header validation",
        "HTTPSRedirectMiddleware": "Security - HTTPS redirect",
        "SessionMiddleware": "Session management",
        "AuthenticationMiddleware": "Authentication",
        "BaseHTTPMiddleware": "Custom HTTP middleware",
    }

    def scan(self, root: Path, exclude: list[str]) -> dict[str, Any]:
        """
        Scan for middleware usage.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            Dictionary with standard and custom middleware lists.
        """
        result: dict[str, Any] = {
            "middleware": [],
            "custom_middleware": [],
        }

        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            middlewares = self._scan_file(py_file, root)
            result["middleware"].extend(middlewares["standard"])
            result["custom_middleware"].extend(middlewares["custom"])

        return result

    def _scan_file(self, filepath: Path, root: Path) -> dict[str, list[dict[str, Any]]]:
        """Scan a file for middleware."""
        result: dict[str, list[dict[str, Any]]] = {"standard": [], "custom": []}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                # app.add_middleware(SomeMiddleware, ...)
                match = re.search(r'\.add_middleware\s*\(\s*(\w+)', line)
                if match:
                    middleware_name = match.group(1)
                    middleware_info: dict[str, Any] = {
                        "name": middleware_name,
                        "file": rel_path,
                        "line": i,
                    }

                    if middleware_name in self.KNOWN_MIDDLEWARE:
                        middleware_info["description"] = self.KNOWN_MIDDLEWARE[middleware_name]
                        result["standard"].append(middleware_info)
                    else:
                        result["custom"].append(middleware_info)

                # @app.middleware("http") decorator
                if re.search(r'@\w+\.middleware\s*\(\s*["\']http["\']', line):
                    # Find the function name on next non-empty line
                    for j in range(i, min(i + 5, len(lines))):
                        func_match = re.match(
                            r'\s*async\s+def\s+(\w+)|def\s+(\w+)',
                            lines[j],
                        )
                        if func_match:
                            func_name = func_match.group(1) or func_match.group(2)
                            result["custom"].append({
                                "name": func_name,
                                "type": "decorator",
                                "file": rel_path,
                                "line": i,
                            })
                            break

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)

        return result
