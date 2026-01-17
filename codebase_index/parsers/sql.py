"""
SQL regex-based parser for codebase_index.
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


@ParserRegistry.register("sql", [".sql"])
class SQLParser(BaseParser):
    """
    SQL parser using regex patterns.

    Extracts table definitions, indexes, and views.
    """

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a SQL file.

        Args:
            filepath: Path to the SQL file.

        Returns:
            Dictionary with tables, indexes, and views.
        """
        result: dict[str, Any] = {
            "tables": [],
            "indexes": [],
            "views": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return {"error": str(e)}

        # Tables
        for match in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\']?(\w+)[`\"\']?",
            content,
            re.IGNORECASE,
        ):
            result["tables"].append({"name": match.group(1)})

        # Indexes
        for match in re.finditer(
            r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+[`\"\']?(\w+)[`\"\']?\s+ON\s+[`\"\']?(\w+)[`\"\']?",
            content,
            re.IGNORECASE,
        ):
            result["indexes"].append({
                "name": match.group(1),
                "table": match.group(2),
            })

        # Views
        for match in re.finditer(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+[`\"\']?(\w+)[`\"\']?",
            content,
            re.IGNORECASE,
        ):
            result["views"].append({"name": match.group(1)})

        return result
