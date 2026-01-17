"""
Auth requirements scanner for codebase_index.

Scans for authentication requirements per endpoint.
Supports configurable auth patterns via config.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


# Default auth patterns (FastAPI/general patterns)
DEFAULT_AUTH_PATTERNS = [
    {"regex": r"Depends\s*\(\s*get_current_user", "type": "get_current_user"},
    {"regex": r"Depends\s*\(\s*require_auth", "type": "require_auth"},
    {"regex": r"Depends\s*\(\s*auth_required", "type": "auth_required"},
    {"regex": r"Depends\s*\(\s*get_current_active_user", "type": "get_current_active_user"},
    {"regex": r"@require_auth", "type": "require_auth decorator"},
    {"regex": r"@login_required", "type": "login_required decorator"},
    {"regex": r"@authenticated", "type": "authenticated decorator"},
    {"regex": r"@jwt_required", "type": "jwt_required decorator"},
    {"regex": r"@permission_required", "type": "permission_required decorator"},
    {"regex": r"Authorization.*Bearer", "type": "Bearer token"},
]


class AuthScanner:
    """
    Scan for authentication requirements per endpoint.

    Supports configurable auth patterns. Falls back to FastAPI defaults.
    """

    def __init__(self) -> None:
        """Initialize with default auth patterns."""
        self.auth_patterns = DEFAULT_AUTH_PATTERNS.copy()

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the scanner with auth patterns from config.

        Args:
            config: Configuration dictionary with optional 'auth' section.
        """
        auth_config = config.get("auth", {})

        if auth_config.get("patterns"):
            # Use configured patterns
            self.auth_patterns = auth_config["patterns"]
            logger.debug("AuthScanner using %d config patterns", len(self.auth_patterns))
        else:
            # Use defaults
            self.auth_patterns = DEFAULT_AUTH_PATTERNS.copy()
            logger.debug("AuthScanner using default patterns")

    def scan_file(
        self,
        filepath: Path,
        routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Scan a file and annotate routes with auth requirements.

        Args:
            filepath: Path to the file.
            routes: List of route dictionaries to annotate.

        Returns:
            List of routes with auth_required and auth_type fields added.
        """
        if not routes:
            return routes

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
        except (OSError, IOError) as e:
            logger.debug("Could not read %s: %s", filepath, e)
            return routes

        # For each route, check for auth patterns in surrounding lines
        annotated_routes: list[dict[str, Any]] = []
        for route in routes:
            route_copy = dict(route)
            route_line = route.get("line", 0)

            # Check lines around the route definition
            auth_info = self._check_auth_around_line(lines, route_line)
            if auth_info:
                route_copy["auth_required"] = True
                route_copy["auth_type"] = auth_info
            else:
                route_copy["auth_required"] = False

            annotated_routes.append(route_copy)

        return annotated_routes

    def _check_auth_around_line(self, lines: list[str], line_num: int) -> str | None:
        """
        Check for auth patterns around a specific line.

        Args:
            lines: All lines in the file.
            line_num: Line number to check around.

        Returns:
            Auth type string if found, None otherwise.
        """
        # Check the line itself and surrounding context (function body)
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 20)

        context = "\n".join(lines[start:end])

        for pattern_info in self.auth_patterns:
            regex = pattern_info.get("regex", "")
            auth_type = pattern_info.get("type", "unknown")
            try:
                if re.search(regex, context, re.IGNORECASE):
                    return auth_type
            except re.error as e:
                logger.warning("Invalid auth regex %r: %s", regex, e)

        return None
