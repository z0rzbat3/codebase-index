"""
Auth requirements scanner for codebase_index.

Scans for authentication requirements per endpoint.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class AuthScanner:
    """Scan for authentication requirements per endpoint."""

    # Common auth patterns
    AUTH_PATTERNS = [
        (r'Depends\s*\(\s*get_current_user', "get_current_user"),
        (r'Depends\s*\(\s*require_auth', "require_auth"),
        (r'Depends\s*\(\s*auth_required', "auth_required"),
        (r'Depends\s*\(\s*get_current_active_user', "get_current_active_user"),
        (r'@require_auth', "require_auth decorator"),
        (r'@login_required', "login_required decorator"),
        (r'@authenticated', "authenticated decorator"),
        (r'@jwt_required', "jwt_required decorator"),
        (r'Authorization.*Bearer', "Bearer token"),
    ]

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

        for pattern, auth_type in self.AUTH_PATTERNS:
            if re.search(pattern, context, re.IGNORECASE):
                return auth_type

        return None
