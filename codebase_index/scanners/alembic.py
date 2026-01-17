"""
Alembic migrations scanner for codebase_index.

Scans for Alembic database migrations and extracts revision info.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class AlembicScanner:
    """Scan for Alembic database migrations."""

    def scan(self, root: Path) -> dict[str, Any]:
        """
        Scan for Alembic migrations.

        Args:
            root: Project root directory.

        Returns:
            Dictionary with migrations list, total count, and latest revision.
        """
        result: dict[str, Any] = {
            "migrations": [],
            "total": 0,
            "latest_revision": None,
            "has_alembic": False,
        }

        # Check for alembic.ini
        alembic_ini = root / "alembic.ini"
        if alembic_ini.exists():
            result["has_alembic"] = True

        # Find migrations directory
        migrations_dirs = [
            root / "migrations" / "versions",
            root / "alembic" / "versions",
        ]

        for migrations_dir in migrations_dirs:
            if migrations_dir.exists():
                result["has_alembic"] = True
                migrations = self._scan_migrations(migrations_dir, root)
                result["migrations"].extend(migrations)

        # Sort by revision (if we can determine order)
        result["migrations"].sort(key=lambda x: x.get("file", ""), reverse=True)
        result["total"] = len(result["migrations"])

        if result["migrations"]:
            result["latest_revision"] = result["migrations"][0].get("revision")

        return result

    def _scan_migrations(self, migrations_dir: Path, root: Path) -> list[dict[str, Any]]:
        """Scan migration files."""
        migrations: list[dict[str, Any]] = []

        for py_file in migrations_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            migration = self._parse_migration(py_file, root)
            if migration:
                migrations.append(migration)

        return migrations

    def _parse_migration(self, filepath: Path, root: Path) -> dict[str, Any] | None:
        """Parse a single migration file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            rel_path = str(filepath.relative_to(root))
            migration: dict[str, Any] = {
                "file": rel_path,
                "filename": filepath.name,
            }

            # Extract revision
            match = re.search(r'revision\s*[:=]\s*["\']([^"\']+)["\']', content)
            if match:
                migration["revision"] = match.group(1)

            # Extract down_revision
            match = re.search(r'down_revision\s*[:=]\s*["\']?([^"\'"\n]+)["\']?', content)
            if match:
                down_rev = match.group(1).strip()
                migration["down_revision"] = None if down_rev == "None" else down_rev

            # Extract message/description from docstring
            match = re.search(r'"""(.+?)"""', content, re.DOTALL)
            if match:
                docstring = match.group(1).strip()
                # First line is usually the message
                migration["message"] = docstring.split("\n")[0].strip()

            # Extract create_date if present
            match = re.search(r'create_date\s*[:=]\s*["\']?([^"\'"\n]+)["\']?', content)
            if match:
                migration["create_date"] = match.group(1).strip()

            # Check what operations are performed
            operations: list[str] = []
            if "op.create_table" in content:
                operations.append("create_table")
            if "op.drop_table" in content:
                operations.append("drop_table")
            if "op.add_column" in content:
                operations.append("add_column")
            if "op.drop_column" in content:
                operations.append("drop_column")
            if "op.create_index" in content:
                operations.append("create_index")
            if "op.drop_index" in content:
                operations.append("drop_index")
            if "op.alter_column" in content:
                operations.append("alter_column")
            if "op.create_foreign_key" in content:
                operations.append("create_foreign_key")

            if operations:
                migration["operations"] = operations

            return migration

        except (OSError, IOError) as e:
            logger.debug("Could not parse migration %s: %s", filepath, e)
            return None
