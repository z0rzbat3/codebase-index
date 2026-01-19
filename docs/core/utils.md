# utils

> Auto-generated from `codebase_index/utils.py`

## Overview

Utility functions for codebase_index. Provides common operations for file hashing, line counting, git metadata, path categorization, and string manipulation.

## Functions

### `get_file_hash(filepath) -> str`

Generate SHA256 hash of file contents.

**Parameters:**
- `filepath`: Path to the file to hash

**Returns:** Hash string in format "sha256:<first 16 chars of hex>"

**Raises:**
- `FileNotFoundError`: If the file doesn't exist
- `PermissionError`: If the file can't be read

### `count_lines(filepath) -> int`

Count lines in a file.

**Parameters:**
- `filepath`: Path to the file

**Returns:** Number of lines in the file, or 0 if the file can't be read

### `get_git_info(root) -> dict[str, Any] | None`

Get git metadata for a repository.

**Parameters:**
- `root`: Root directory of the git repository

**Returns:** Dictionary with keys:
- `commit`: Short commit hash
- `branch`: Current branch name
- `dirty`: Boolean indicating uncommitted changes

Returns `None` if not a git repository or git is unavailable.

### `categorize_file(filepath, categories) -> str`

Categorize a file based on path patterns.

**Parameters:**
- `filepath`: Relative path to the file
- `categories`: Dict mapping regex patterns to category names

**Returns:** Category name, or "other" if no pattern matches

### `should_exclude(path, exclude_patterns) -> bool`

Check if path should be excluded based on patterns.

**Parameters:**
- `path`: Path to check
- `exclude_patterns`: List of patterns. Patterns starting with '*' match suffixes, others match directory names.

**Returns:** True if the path should be excluded

### `normalize_module_name(name) -> str`

Normalize a module/package name for comparison. Converts hyphens to underscores and lowercases.

**Parameters:**
- `name`: Module or package name

**Returns:** Normalized name

### `extract_domain(url) -> str | None`

Extract domain from a URL.

**Parameters:**
- `url`: URL string

**Returns:** Domain name, or None if extraction fails

### `truncate_string(text, max_length) -> str | None`

Truncate a string to a maximum length.

**Parameters:**
- `text`: String to truncate
- `max_length`: Maximum length (default: 200)

**Returns:** Truncated string with "..." suffix if needed, or None if input is None

## Usage

```python
from pathlib import Path
from codebase_index.utils import (
    get_file_hash,
    count_lines,
    get_git_info,
    categorize_file,
    should_exclude
)

# Hash a file
hash_str = get_file_hash(Path('main.py'))

# Count lines
lines = count_lines(Path('main.py'))

# Get git info
git = get_git_info(Path('.'))
if git:
    print(f"Branch: {git['branch']}, Commit: {git['commit']}")

# Categorize file
categories = {r'.*/tests?/.*\.py$': 'test', r'.*/models?/.*\.py$': 'model'}
cat = categorize_file('app/models/user.py', categories)  # Returns 'model'

# Check exclusions
if should_exclude(Path('node_modules/pkg'), ['node_modules']):
    print("Excluded")
```

---
*Source: codebase_index/utils.py | Lines: 205*
