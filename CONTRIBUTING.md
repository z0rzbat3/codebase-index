# Contributing to Codebase Index

This guide explains how to extend codebase-index with support for new languages, frameworks, and analysis features.

## Project Structure

```
codebase_index/
├── parsers/           # Language-specific parsers (plugin system)
│   ├── base.py        # BaseParser ABC + ParserRegistry
│   ├── python.py      # AST-based Python parser
│   ├── typescript.py  # Regex-based TypeScript/React parser
│   ├── sql.py         # SQL schema parser
│   └── docker.py      # Docker Compose YAML parser
├── scanners/          # Domain-specific scanners
├── analyzers/         # Code analysis tools
├── config.py          # Configuration and defaults
├── scanner.py         # Main orchestrator
└── cli.py             # Command-line interface
```

## Adding a New Language Parser

The easiest way to extend codebase-index is by adding a new language parser.

### Step 1: Create the Parser File

Create a new file in `codebase_index/parsers/`, e.g., `rust.py`:

```python
"""
Rust parser for codebase_index.
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


@ParserRegistry.register("rust", [".rs"])
class RustParser(BaseParser):
    """
    Rust parser using regex patterns.

    For better accuracy, consider using tree-sitter-rust.
    """

    def __init__(self) -> None:
        super().__init__()
        # Parser-specific config defaults
        self.internal_crate_prefixes: list[str] = ["crate", "super", "self"]

    def configure(self, config: dict[str, Any]) -> None:
        """Configure parser from user config."""
        super().configure(config)

        # Extract Rust-specific config if provided
        rust_config = config.get("rust", {})
        if rust_config.get("internal_prefixes"):
            self.internal_crate_prefixes = rust_config["internal_prefixes"]

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a Rust file and extract structure.

        Returns:
            Dictionary with functions, structs, enums, traits, imports.
        """
        result: dict[str, Any] = {
            "functions": [],
            "structs": [],
            "enums": [],
            "traits": [],
            "impls": [],
            "imports": {"internal": [], "external": []},
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return {"error": str(e)}

        for i, line in enumerate(lines, 1):
            self._process_line(line, i, result)

        return result

    def _process_line(self, line: str, line_num: int, result: dict[str, Any]) -> None:
        """Process a single line of Rust code."""
        stripped = line.strip()

        # Functions: pub fn name(...) or fn name(...)
        match = re.match(r"^(pub\s+)?(async\s+)?fn\s+(\w+)", stripped)
        if match:
            result["functions"].append({
                "name": match.group(3),
                "line": line_num,
                "public": bool(match.group(1)),
                "async": bool(match.group(2)),
            })
            return

        # Structs: pub struct Name
        match = re.match(r"^(pub\s+)?struct\s+(\w+)", stripped)
        if match:
            result["structs"].append({
                "name": match.group(2),
                "line": line_num,
                "public": bool(match.group(1)),
            })
            return

        # Enums: pub enum Name
        match = re.match(r"^(pub\s+)?enum\s+(\w+)", stripped)
        if match:
            result["enums"].append({
                "name": match.group(2),
                "line": line_num,
                "public": bool(match.group(1)),
            })
            return

        # Traits: pub trait Name
        match = re.match(r"^(pub\s+)?trait\s+(\w+)", stripped)
        if match:
            result["traits"].append({
                "name": match.group(2),
                "line": line_num,
                "public": bool(match.group(1)),
            })
            return

        # Use statements: use crate::foo or use std::collections
        match = re.match(r"^use\s+([^;]+)", stripped)
        if match:
            module = match.group(1).split("::")[0]
            if module in self.internal_crate_prefixes:
                result["imports"]["internal"].append(match.group(1))
            else:
                if module not in result["imports"]["external"]:
                    result["imports"]["external"].append(module)
```

### Step 2: Register the Parser

The `@ParserRegistry.register` decorator automatically registers your parser. Just import it in `codebase_index/parsers/__init__.py`:

```python
from codebase_index.parsers.rust import RustParser
```

### Step 3: Add to Scanner (if needed)

If your language needs special handling in the main scanner (like Python's route/model detection), update `codebase_index/scanner.py`:

```python
def _process_file_data(self, file_info, result, route_prefixes):
    # ... existing code ...
    elif language == "rust":
        self._process_rust_file(file_info, result)

def _process_rust_file(self, file_info, result):
    """Process Rust-specific exports."""
    exports = file_info.get("exports", {})
    # Add structs to symbol index, etc.
```

## Adding Framework Support via Config

For frameworks within existing languages (e.g., Django for Python, NestJS for TypeScript), you can add support through config patterns without writing new code.

### Route Detection Patterns

In `codebase_index/config.py`, add patterns to `DEFAULT_CONFIG["routes"]["patterns"]`:

```python
# Django
{"regex": r"path\(['\"]", "framework": "django"},
{"regex": r"re_path\(['\"]", "framework": "django"},

# NestJS
{"regex": r"@(Get|Post|Put|Patch|Delete)\(['\"]", "framework": "nestjs"},

# Express
{"regex": r"(app|router)\.(get|post|put|patch|delete)\(", "framework": "express"},
```

### Model Detection Patterns

Add to `DEFAULT_CONFIG["models"]["patterns"]`:

```python
# Django ORM
{"base_class": "models.Model", "type": "django"},

# TypeORM
{"decorator": "Entity", "type": "typeorm"},

# Prisma
{"marker": "@prisma/client", "type": "prisma"},
```

### Auth Detection Patterns

Add to `DEFAULT_CONFIG["auth"]["patterns"]`:

```python
# Django
{"regex": r"@login_required", "type": "login_required decorator"},
{"regex": r"@permission_required", "type": "permission_required decorator"},

# NestJS Guards
{"regex": r"@UseGuards\(.*Auth", "type": "auth guard"},

# Express middleware
{"regex": r"isAuthenticated", "type": "auth middleware"},
```

## Adding a New Scanner

Scanners extract domain-specific information across the codebase.

### Step 1: Create Scanner File

Create `codebase_index/scanners/graphql.py`:

```python
"""
GraphQL schema scanner for codebase_index.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class GraphQLScanner:
    """Scan for GraphQL schemas and resolvers."""

    def scan(
        self,
        root: Path,
        exclude: list[str],
    ) -> dict[str, Any]:
        """
        Scan codebase for GraphQL definitions.

        Args:
            root: Root directory to scan.
            exclude: Patterns to exclude.

        Returns:
            Dictionary with types, queries, mutations, subscriptions.
        """
        result = {
            "types": [],
            "queries": [],
            "mutations": [],
            "subscriptions": [],
            "total": 0,
        }

        # Scan .graphql files
        for filepath in root.rglob("*.graphql"):
            if self._should_exclude(filepath, exclude):
                continue
            self._scan_graphql_file(filepath, root, result)

        # Scan Python files for Strawberry/Ariadne decorators
        for filepath in root.rglob("*.py"):
            if self._should_exclude(filepath, exclude):
                continue
            self._scan_python_graphql(filepath, root, result)

        result["total"] = (
            len(result["types"]) +
            len(result["queries"]) +
            len(result["mutations"])
        )
        return result

    def _should_exclude(self, filepath: Path, exclude: list[str]) -> bool:
        """Check if file should be excluded."""
        path_str = str(filepath)
        return any(pattern in path_str for pattern in exclude)

    def _scan_graphql_file(
        self,
        filepath: Path,
        root: Path,
        result: dict[str, Any],
    ) -> None:
        """Scan a .graphql schema file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, IOError):
            return

        rel_path = str(filepath.relative_to(root))

        # Type definitions
        for match in re.finditer(r"type\s+(\w+)", content):
            result["types"].append({
                "name": match.group(1),
                "file": rel_path,
            })

    def _scan_python_graphql(
        self,
        filepath: Path,
        root: Path,
        result: dict[str, Any],
    ) -> None:
        """Scan Python file for GraphQL resolvers (Strawberry, Ariadne)."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, IOError):
            return

        rel_path = str(filepath.relative_to(root))

        # Strawberry type decorator
        for match in re.finditer(r"@strawberry\.type[^\n]*\nclass\s+(\w+)", content):
            result["types"].append({
                "name": match.group(1),
                "file": rel_path,
                "framework": "strawberry",
            })
```

### Step 2: Register in Scanner

Add to `codebase_index/scanner.py`:

```python
from codebase_index.scanners.graphql import GraphQLScanner

class CodebaseScanner:
    def __init__(self, ...):
        # ... existing scanners ...
        self.graphql_scanner = GraphQLScanner()

    def scan(self):
        # ... existing code ...
        result["graphql"] = self.graphql_scanner.scan(self.root, self.exclude)
```

### Step 3: Export in `__init__.py`

```python
from codebase_index.scanners.graphql import GraphQLScanner
```

## Adding a New Analyzer

Analyzers process the scanned data to produce insights.

### Example: Security Analyzer

Create `codebase_index/analyzers/security.py`:

```python
"""
Security pattern analyzer for codebase_index.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class SecurityAnalyzer:
    """Detect potential security issues in code."""

    PATTERNS = [
        {
            "name": "hardcoded_secret",
            "regex": r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
            "severity": "high",
        },
        {
            "name": "sql_injection",
            "regex": r"execute\([^)]*%s|execute\([^)]*\+|execute\([^)]*\.format",
            "severity": "high",
        },
        {
            "name": "eval_usage",
            "regex": r"\beval\s*\(",
            "severity": "medium",
        },
    ]

    def analyze(
        self,
        root: Path,
        files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze files for security issues.

        Args:
            root: Root directory.
            files: List of file info dictionaries.

        Returns:
            Dictionary with findings grouped by severity.
        """
        findings = {"high": [], "medium": [], "low": []}

        for file_info in files:
            if file_info.get("language") not in ("python", "typescript"):
                continue

            filepath = root / file_info["path"]
            try:
                content = filepath.read_text(encoding="utf-8")
            except (OSError, IOError):
                continue

            for pattern in self.PATTERNS:
                for match in re.finditer(pattern["regex"], content, re.IGNORECASE):
                    findings[pattern["severity"]].append({
                        "type": pattern["name"],
                        "file": file_info["path"],
                        "match": match.group(0)[:50],
                    })

        return {
            "findings": findings,
            "total_issues": sum(len(v) for v in findings.values()),
        }
```

## Testing Your Changes

### Run the Scanner

```bash
# Test on a sample project
python -m codebase_index /path/to/project --summary

# Test with custom config
python -m codebase_index /path/to/project --config myconfig.yaml -o output.json

# Verbose mode for debugging
python -m codebase_index /path/to/project -v
```

### Unit Tests

Add tests in `tests/` directory:

```python
# tests/test_rust_parser.py
import pytest
from pathlib import Path
from codebase_index.parsers.rust import RustParser


def test_rust_function_detection(tmp_path):
    # Create test file
    test_file = tmp_path / "test.rs"
    test_file.write_text("""
pub async fn process_data(input: &str) -> Result<(), Error> {
    Ok(())
}

fn helper() {}
""")

    parser = RustParser()
    result = parser.scan(test_file)

    assert len(result["functions"]) == 2
    assert result["functions"][0]["name"] == "process_data"
    assert result["functions"][0]["public"] is True
    assert result["functions"][0]["async"] is True
```

Run tests:

```bash
pytest tests/ -v
```

## Code Style

- Use type hints for all function signatures
- Add docstrings with Args/Returns sections
- Use `logging` instead of print statements
- Handle file I/O errors gracefully with try/except
- Follow existing patterns in the codebase

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/rust-parser`
3. Make your changes with tests
4. Run the test suite: `pytest tests/ -v`
5. Run type checking: `mypy codebase_index/`
6. Run linting: `ruff check codebase_index/`
7. Submit a pull request

## Questions?

Open an issue on GitHub for questions about contributing.
