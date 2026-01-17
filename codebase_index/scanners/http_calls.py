"""
External HTTP calls scanner for codebase_index.

Scans for external HTTP calls using requests, httpx, aiohttp, fetch, axios.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude, extract_domain

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class HttpCallsScanner:
    """Scan for external HTTP calls (httpx, requests, aiohttp, fetch)."""

    # Patterns for HTTP client libraries
    PYTHON_PATTERNS = [
        # requests
        (r'requests\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']', "requests"),
        (r'requests\.request\s*\(\s*["\'][^"\']+["\']\s*,\s*["\']([^"\']+)["\']', "requests"),
        # httpx
        (r'httpx\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']', "httpx"),
        (r'httpx\.(?:Async)?Client\s*\(\s*\).*?\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "httpx"),
        (r'client\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "httpx-client"),
        # aiohttp
        (r'session\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "aiohttp"),
        (r'aiohttp\.ClientSession.*?\.(get|post)\s*\(\s*["\']([^"\']+)["\']', "aiohttp"),
    ]

    TS_PATTERNS = [
        # fetch
        (r'fetch\s*\(\s*["\']([^"\']+)["\']', "fetch"),
        (r'fetch\s*\(\s*`([^`]+)`', "fetch-template"),
        # axios
        (r'axios\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "axios"),
        (r'axios\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\']', "axios-config"),
    ]

    def scan(self, root: Path, exclude: list[str]) -> dict[str, Any]:
        """
        Scan for external HTTP calls.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            Dictionary with Python and TypeScript calls, totals, and unique domains.
        """
        result: dict[str, Any] = {
            "python_calls": [],
            "typescript_calls": [],
            "total_external_calls": 0,
            "unique_domains": set(),
        }

        # Scan Python files
        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            calls = self._scan_python_file(py_file, root)
            result["python_calls"].extend(calls)

        # Scan TypeScript files
        for pattern in ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]:
            for ts_file in root.glob(pattern):
                if should_exclude(ts_file, exclude):
                    continue
                calls = self._scan_ts_file(ts_file, root)
                result["typescript_calls"].extend(calls)

        # Calculate totals
        result["total_external_calls"] = (
            len(result["python_calls"]) + len(result["typescript_calls"])
        )

        # Extract unique domains
        for call in result["python_calls"] + result["typescript_calls"]:
            url = call.get("url", "")
            domain = extract_domain(url)
            if domain:
                result["unique_domains"].add(domain)

        result["unique_domains"] = sorted(result["unique_domains"])

        return result

    def _scan_python_file(self, filepath: Path, root: Path) -> list[dict[str, Any]]:
        """Scan a Python file for HTTP calls."""
        calls: list[dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, library in self.PYTHON_PATTERNS:
                    for match in re.finditer(pattern, line):
                        groups = match.groups()
                        if len(groups) >= 2:
                            method, url = groups[0], groups[1]
                        else:
                            method, url = "GET", groups[0]

                        # Skip internal API calls
                        if url.startswith("/") or url.startswith("{"):
                            continue

                        calls.append({
                            "file": rel_path,
                            "line": i,
                            "library": library,
                            "method": method.upper() if method else "GET",
                            "url": url,
                        })

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)
        return calls

    def _scan_ts_file(self, filepath: Path, root: Path) -> list[dict[str, Any]]:
        """Scan a TypeScript file for HTTP calls."""
        calls: list[dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, library in self.TS_PATTERNS:
                    for match in re.finditer(pattern, line):
                        groups = match.groups()
                        if len(groups) >= 2:
                            method, url = groups[0], groups[1]
                        elif len(groups) == 1:
                            method, url = "GET", groups[0]
                        else:
                            continue

                        # Skip internal API calls (relative paths)
                        if url.startswith("/") and not url.startswith("//"):
                            continue

                        calls.append({
                            "file": rel_path,
                            "line": i,
                            "library": library,
                            "method": method.upper() if method and method.isalpha() else "GET",
                            "url": url,
                        })

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)
        return calls
