# Parsers Module

> Language-specific parsers for codebase-index

## Overview

The parsers module provides language-specific file parsers that extract structural information from source code. Each parser is registered with the `ParserRegistry` and automatically selected based on file extensions.

## Architecture

```
parsers/
├── base.py        # BaseParser ABC and ParserRegistry
├── python.py      # AST-based Python parser
├── typescript.py  # Regex-based TypeScript/React parser
├── sql.py         # Regex-based SQL DDL parser
└── docker.py      # YAML/regex Docker Compose parser
```

## Available Parsers

| Parser | Languages | Extensions | Approach |
|--------|-----------|------------|----------|
| [PythonParser](python.md) | Python | `.py`, `.pyw` | AST + regex fallback |
| [TypeScriptParser](typescript.md) | TypeScript, JavaScript, React | `.ts`, `.tsx`, `.js`, `.jsx` | Regex |
| [SQLParser](sql.md) | SQL | `.sql` | Regex |
| [DockerParser](docker.md) | Docker Compose | `docker-compose.yaml`, `docker-compose.yml` | YAML + regex fallback |

## Quick Reference

### Get Parser for File
```python
from codebase_index.parsers.base import ParserRegistry

parser, language = ParserRegistry.get_parser(Path("main.py"))
result = parser.scan(Path("main.py"))
```

### Register Custom Parser
```python
from codebase_index.parsers.base import BaseParser, ParserRegistry

@ParserRegistry.register("rust", [".rs"])
class RustParser(BaseParser):
    def scan(self, filepath: Path) -> dict:
        return {"functions": [], "structs": []}
```

### Configure Parser
```python
parser, _ = ParserRegistry.get_parser(
    Path("main.py"),
    config={
        "imports": {"internal_prefixes": ["myapp"]},
        "routes": {"enabled": True}
    }
)
```

## Common Output Keys

All parsers return dictionaries. Common keys include:

| Key | Description |
|-----|-------------|
| `classes` | Class definitions (Python) |
| `functions` | Function definitions |
| `imports` | Import statements (internal/external) |
| `error` | Error message if parsing failed |

## Adding a New Parser

1. Create a new file in `codebase_index/parsers/`
2. Inherit from `BaseParser`
3. Implement the `scan(filepath: Path) -> dict` method
4. Register with `@ParserRegistry.register("language", [".ext"])`

See [base.md](base.md) for the full API reference.

---
*Auto-generated documentation for codebase_index/parsers/*
