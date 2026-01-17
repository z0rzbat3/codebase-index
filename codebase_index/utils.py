"""
Utility functions for codebase_index.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


def get_file_hash(filepath: Path) -> str:
    """
    Generate SHA256 hash of file contents.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Hash string in format "sha256:<first 16 chars of hex>".

    Raises:
        FileNotFoundError: If the file doesn't exist.
        PermissionError: If the file can't be read.
    """
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()[:16]}"


def count_lines(filepath: Path) -> int:
    """
    Count lines in a file.

    Args:
        filepath: Path to the file.

    Returns:
        Number of lines in the file, or 0 if the file can't be read.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError) as e:
        logger.debug("Could not count lines in %s: %s", filepath, e)
        return 0


def get_git_info(root: Path) -> dict[str, Any] | None:
    """
    Get git metadata for a repository.

    Args:
        root: Root directory of the git repository.

    Returns:
        Dictionary with 'commit', 'branch', and 'dirty' keys,
        or None if not a git repository or git is unavailable.
    """
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()

        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()

        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode().strip()

        return {
            "commit": commit,
            "branch": branch,
            "dirty": len(status) > 0,
        }
    except subprocess.TimeoutExpired:
        logger.warning("Git command timed out in %s", root)
        return None
    except subprocess.CalledProcessError:
        logger.debug("Not a git repository: %s", root)
        return None
    except FileNotFoundError:
        logger.debug("Git not available")
        return None


def categorize_file(filepath: str, categories: dict[str, str]) -> str:
    """
    Categorize a file based on path patterns.

    Args:
        filepath: Relative path to the file.
        categories: Dict mapping regex patterns to category names.

    Returns:
        Category name, or "other" if no pattern matches.
    """
    for pattern, category in categories.items():
        if re.match(pattern, filepath):
            return category
    return "other"


def should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """
    Check if path should be excluded based on patterns.

    Args:
        path: Path to check.
        exclude_patterns: List of patterns. Patterns starting with '*'
            match suffixes, others match directory names.

    Returns:
        True if the path should be excluded.
    """
    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern.startswith("*"):
            # Suffix match (e.g., "*.pyc")
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str.split(os.sep):
            # Directory name match
            return True
    return False


def normalize_module_name(name: str) -> str:
    """
    Normalize a module/package name for comparison.

    Converts hyphens to underscores and lowercases.

    Args:
        name: Module or package name.

    Returns:
        Normalized name.
    """
    return name.lower().replace("-", "_").replace(".", "_")


def extract_domain(url: str) -> str | None:
    """
    Extract domain from a URL.

    Args:
        url: URL string.

    Returns:
        Domain name, or None if extraction fails.
    """
    if not url or url.startswith("/") or url.startswith("${") or url.startswith("{"):
        return None
    try:
        if "://" in url:
            url = url.split("://")[1]
        domain = url.split("/")[0].split(":")[0]
        if "." in domain:
            return domain
    except (IndexError, ValueError):
        pass
    return None


def truncate_string(text: str | None, max_length: int = 200) -> str | None:
    """
    Truncate a string to a maximum length.

    Args:
        text: String to truncate.
        max_length: Maximum length.

    Returns:
        Truncated string with "..." suffix if needed, or None if input is None.
    """
    if not text:
        return None
    first_line = text.split('\n')[0].strip()
    if len(first_line) > max_length:
        return first_line[:max_length] + "..."
    return first_line
