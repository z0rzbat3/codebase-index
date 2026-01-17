"""
TypeScript/React regex-based parser for codebase_index.

Supports configurable internal import aliases via config.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.parsers.base import BaseParser, ParserRegistry

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


@ParserRegistry.register("typescript", [".ts", ".tsx", ".js", ".jsx"])
class TypeScriptParser(BaseParser):
    """
    TypeScript/React parser using regex patterns.

    Extracts components, hooks, functions, types, interfaces, and imports.
    Supports configurable internal import aliases.
    """

    def __init__(self) -> None:
        """Initialize with default config."""
        super().__init__()
        # Internal import patterns (relative imports, aliases)
        self.internal_patterns: list[str] = [".", "@/", "~/"]

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the parser.

        Args:
            config: Configuration dictionary.
        """
        super().configure(config)

        # Check for custom internal import prefixes
        imports_config = config.get("imports", {})
        if imports_config.get("internal_prefixes"):
            # Add TypeScript-specific prefixes
            prefixes = imports_config["internal_prefixes"]
            self.internal_patterns = [".", "@/", "~/"]
            # Add any custom prefixes that look like aliases
            for prefix in prefixes:
                if prefix.startswith("@") or prefix.startswith("~"):
                    self.internal_patterns.append(prefix)

        logger.debug("TypeScriptParser configured: internal patterns = %s", self.internal_patterns)

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a TypeScript/React file.

        Args:
            filepath: Path to the TypeScript file.

        Returns:
            Dictionary with components, hooks, functions, types, interfaces, imports.
        """
        result: dict[str, Any] = {
            "components": [],
            "hooks": [],
            "functions": [],
            "types": [],
            "interfaces": [],
            "imports": {"internal": [], "external": []},
            "api_calls": [],
            "routes": [],  # Express/Next.js routes if detected
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return {"error": str(e)}

        for i, line in enumerate(lines, 1):
            self._process_line(line, i, result)

        return result

    def _process_line(self, line: str, line_num: int, result: dict[str, Any]) -> None:
        """Process a single line of code."""
        # Exported functions/components
        match = re.match(
            r"^export\s+(default\s+)?(?:async\s+)?function\s+(\w+)",
            line,
        )
        if match:
            name = match.group(2)
            if name.startswith("use"):
                result["hooks"].append({"name": name, "line": line_num})
            elif name[0].isupper():
                result["components"].append({"name": name, "line": line_num})
            else:
                result["functions"].append({"name": name, "line": line_num})
            return

        # Exported const components/hooks (arrow functions)
        match = re.match(r"^export\s+(const|let)\s+(\w+)\s*[=:]", line)
        if match:
            name = match.group(2)
            if name.startswith("use"):
                result["hooks"].append({"name": name, "line": line_num})
            elif name[0].isupper():
                result["components"].append({"name": name, "line": line_num})
            return

        # Types
        match = re.match(r"^export\s+type\s+(\w+)", line)
        if match:
            result["types"].append({"name": match.group(1), "line": line_num})
            return

        # Interfaces
        match = re.match(r"^export\s+interface\s+(\w+)", line)
        if match:
            result["interfaces"].append({"name": match.group(1), "line": line_num})
            return

        # Imports
        match = re.match(r"^import\s+.*from\s+['\"]([^'\"]+)['\"]", line)
        if match:
            module = match.group(1)
            self._categorize_import(module, result["imports"])
            return

        # Express routes: app.get('/path', ...) or router.get('/path', ...)
        match = re.search(
            r"(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]",
            line,
        )
        if match:
            result["routes"].append({
                "method": match.group(1).upper(),
                "path": match.group(2),
                "line": line_num,
                "framework": "express",
            })
            return

        # API calls - fetch
        match = re.search(r"fetch\(['\"]([^'\"]+)['\"]", line)
        if match:
            result["api_calls"].append({"url": match.group(1), "line": line_num})
            return

        # API calls - axios
        match = re.search(
            r"axios\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]",
            line,
        )
        if match:
            result["api_calls"].append({
                "method": match.group(1).upper(),
                "url": match.group(2),
                "line": line_num,
            })

    def _categorize_import(
        self,
        module: str,
        imports: dict[str, list[str]],
    ) -> None:
        """Categorize import as internal or external."""
        # Check if it matches any internal pattern
        is_internal = any(
            module.startswith(pattern) for pattern in self.internal_patterns
        )

        if is_internal:
            if module not in imports["internal"]:
                imports["internal"].append(module)
        else:
            # Get package name (first part, or @scope/package)
            pkg = module.split("/")[0]
            if pkg.startswith("@"):
                pkg = "/".join(module.split("/")[:2])
            if pkg not in imports["external"]:
                imports["external"].append(pkg)
