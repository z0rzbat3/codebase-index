"""
Route prefix scanner for codebase_index.

Scans FastAPI main.py for router prefixes to build full API paths.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.utils import should_exclude
from codebase_index.config import DEFAULT_EXCLUDE

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RoutePrefixScanner:
    """Scan FastAPI main.py for router prefixes to build full paths."""

    def scan(self, root: Path, exclude: list[str] | None = None) -> dict[str, str]:
        """
        Scan for include_router calls to extract prefixes.

        Args:
            root: Project root directory.
            exclude: Exclusion patterns.

        Returns:
            Dictionary mapping router names to their prefixes.
        """
        exclude = exclude or DEFAULT_EXCLUDE
        prefixes: dict[str, str] = {}

        # Find main.py or app files
        main_files = list(root.glob("**/main.py")) + list(root.glob("**/app.py"))

        for main_file in main_files:
            if should_exclude(main_file, exclude):
                continue
            file_prefixes = self._scan_main_file(main_file)
            prefixes.update(file_prefixes)

        return prefixes

    def _scan_main_file(self, filepath: Path) -> dict[str, str]:
        """
        Scan a main.py file for include_router calls.

        Args:
            filepath: Path to the main.py file.

        Returns:
            Dictionary mapping router names to prefixes.
        """
        prefixes: dict[str, str] = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Match: app.include_router(agents.router, prefix="/api/v1/agents")
            # or: app.include_router(router, prefix="/api/v1/agents", tags=["agents"])
            pattern = r'include_router\s*\(\s*(\w+)(?:\.router)?\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'

            for match in re.finditer(pattern, content):
                router_name = match.group(1)
                prefix = match.group(2)
                prefixes[router_name] = prefix

            # Also check for: from .routers import agents, chat, etc.
            # Then: app.include_router(agents.router, prefix="/agents")
            import_pattern = r'from\s+\.?routers?\s+import\s+(.+)'
            for match in re.finditer(import_pattern, content):
                imports = match.group(1)
                # Parse the imported names
                for name in re.findall(r'(\w+)', imports):
                    if name not in prefixes:
                        # Try to find the prefix for this router
                        specific_pattern = (
                            rf'include_router\s*\(\s*{name}(?:\.router)?\s*,\s*'
                            rf'prefix\s*=\s*["\']([^"\']+)["\']'
                        )
                        specific_match = re.search(specific_pattern, content)
                        if specific_match:
                            prefixes[name] = specific_match.group(1)

        except (OSError, IOError) as e:
            logger.debug("Could not scan %s: %s", filepath, e)
        return prefixes
