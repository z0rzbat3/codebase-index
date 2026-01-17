"""
Staleness checker for codebase_index.

Compares an index file against the current state of the codebase
to determine if the index is out of date.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class StalenessChecker:
    """Check if an index file is stale compared to the codebase."""

    def __init__(self, root: Path, index_data: dict[str, Any]) -> None:
        """
        Initialize the staleness checker.

        Args:
            root: Root directory of the codebase.
            index_data: The loaded index data.
        """
        self.root = root
        self.index_data = index_data

    def check(self) -> dict[str, Any]:
        """
        Check if the index is stale.

        Returns:
            Dictionary with staleness information:
            - is_stale: bool
            - index_age_hours: float
            - changed_files: list of changed file paths
            - new_files: list of new file paths
            - deleted_files: list of deleted file paths
            - summary: human-readable summary
        """
        result: dict[str, Any] = {
            "is_stale": False,
            "index_age_hours": 0.0,
            "index_generated_at": None,
            "changed_files": [],
            "new_files": [],
            "deleted_files": [],
            "total_changes": 0,
            "summary": "",
        }

        # Get index generation time
        meta = self.index_data.get("meta", {})
        generated_at_str = meta.get("generated_at")

        if not generated_at_str:
            result["is_stale"] = True
            result["summary"] = "Index has no generation timestamp"
            return result

        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            result["is_stale"] = True
            result["summary"] = f"Invalid timestamp in index: {generated_at_str}"
            return result

        result["index_generated_at"] = generated_at_str

        # Calculate age
        now = datetime.now(timezone.utc)
        age = now - generated_at
        result["index_age_hours"] = round(age.total_seconds() / 3600, 1)

        # Get indexed file paths
        indexed_files = set()
        for file_info in self.index_data.get("files", []):
            indexed_files.add(file_info.get("path"))

        # Check for git changes since index generation
        git_changes = self._get_git_changes_since(generated_at)

        if git_changes:
            result["changed_files"] = git_changes.get("modified", [])
            result["new_files"] = git_changes.get("added", [])
            result["deleted_files"] = git_changes.get("deleted", [])
        else:
            # Fallback: check file modification times
            result["changed_files"] = self._get_modified_files_since(
                generated_at, indexed_files
            )

        result["total_changes"] = (
            len(result["changed_files"])
            + len(result["new_files"])
            + len(result["deleted_files"])
        )

        result["is_stale"] = result["total_changes"] > 0

        # Build summary
        result["summary"] = self._build_summary(result)

        return result

    def _get_git_changes_since(
        self, since: datetime
    ) -> dict[str, list[str]] | None:
        """
        Get files changed in git since the given time.

        Returns:
            Dict with 'modified', 'added', 'deleted' lists, or None if not a git repo.
        """
        try:
            # Format timestamp for git
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")

            # Get commits since the timestamp
            result = subprocess.run(
                ["git", "log", "--since", since_str, "--name-status", "--pretty=format:"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return None

            changes: dict[str, list[str]] = {
                "modified": [],
                "added": [],
                "deleted": [],
            }

            seen = set()
            for line in result.stdout.strip().split("\n"):
                if not line or "\t" not in line:
                    continue

                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue

                status, filepath = parts
                if filepath in seen:
                    continue
                seen.add(filepath)

                if status.startswith("M"):
                    changes["modified"].append(filepath)
                elif status.startswith("A"):
                    changes["added"].append(filepath)
                elif status.startswith("D"):
                    changes["deleted"].append(filepath)

            # Also check working directory changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line or len(line) < 4:
                        continue

                    status = line[:2]
                    filepath = line[3:]

                    if filepath in seen:
                        continue
                    seen.add(filepath)

                    if "M" in status:
                        changes["modified"].append(filepath)
                    elif "A" in status or "?" in status:
                        changes["added"].append(filepath)
                    elif "D" in status:
                        changes["deleted"].append(filepath)

            return changes

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug("Git check failed: %s", e)
            return None

    def _get_modified_files_since(
        self,
        since: datetime,
        indexed_files: set[str],
    ) -> list[str]:
        """
        Fallback: check file modification times.

        Args:
            since: Check for files modified after this time.
            indexed_files: Set of file paths in the index.

        Returns:
            List of modified file paths.
        """
        modified = []
        since_ts = since.timestamp()

        for filepath in indexed_files:
            full_path = self.root / filepath
            try:
                if full_path.exists():
                    mtime = full_path.stat().st_mtime
                    if mtime > since_ts:
                        modified.append(filepath)
            except OSError:
                pass

        return modified

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Build a human-readable summary."""
        parts = []

        age_hours = result["index_age_hours"]
        if age_hours < 1:
            age_str = f"{int(age_hours * 60)} minutes"
        elif age_hours < 24:
            age_str = f"{age_hours:.1f} hours"
        else:
            age_str = f"{age_hours / 24:.1f} days"

        parts.append(f"Index is {age_str} old")

        if result["is_stale"]:
            changes = []
            if result["changed_files"]:
                changes.append(f"{len(result['changed_files'])} modified")
            if result["new_files"]:
                changes.append(f"{len(result['new_files'])} added")
            if result["deleted_files"]:
                changes.append(f"{len(result['deleted_files'])} deleted")

            parts.append(f"{result['total_changes']} files changed ({', '.join(changes)})")
            parts.append("Recommend: regenerate index")
        else:
            parts.append("Index is up to date")

        return "; ".join(parts)
