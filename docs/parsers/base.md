# Base Parser Module

> Auto-generated from `codebase_index/parsers/base.py`

## Overview

Base parser class and registry for language parsers. This module provides the foundation for all language-specific parsers in codebase-index.

To add support for a new language:
1. Create a new parser class inheriting from `BaseParser`
2. Implement the `scan` method
3. Register using the `@ParserRegistry.register` decorator

## Classes

### `ParserRegistry`

Registry for language parsers. Manages parser classes and their file extension mappings. Supports dynamic registration of custom parsers and config injection.

**Class Variables:**
- `_parser_classes`: Maps language names to parser classes
- `_extension_map`: Maps file extensions to language names
- `_cached_parsers`: Caches configured parser instances

#### Methods

- `register(language: str, extensions: list[str]) -> Callable`: Decorator to register a parser class for a language and its file extensions.

- `register_parser(language: str, extensions: list[str], parser_class: Type[BaseParser]) -> None`: Programmatically register a parser class.

- `get_parser(filepath: Path, config: dict | None) -> tuple[BaseParser | None, str | None]`: Get the appropriate parser for a file based on its extension.

- `get_parser_for_language(language: str, config: dict | None) -> BaseParser | None`: Get a parser by language name directly.

- `list_languages() -> list[str]`: Get list of all registered language names.

- `list_extensions() -> dict[str, str]`: Get mapping of extensions to languages.

- `clear() -> None`: Clear all registered parsers (useful for testing).

### `BaseParser`

Abstract base class for language parsers. Subclasses must implement the `scan` method to extract structural information from source files.

**Attributes:**
- `supports_fallback: bool = False`: Set to True if parser supports regex fallback
- `config: dict`: Configuration dictionary

#### Methods

- `configure(config: dict[str, Any]) -> None`: Configure the parser. Subclasses can override to extract specific config values.

- `scan(filepath: Path) -> dict[str, Any]`: Abstract method. Scan a source file and return extracted information.

- `scan_with_fallback(filepath: Path) -> dict[str, Any]`: Scan with fallback to regex if AST parsing fails.

- `get_empty_result() -> dict[str, Any]`: Get an empty result structure for this parser.

- `_match_patterns(text: str, patterns: list[dict], pattern_key: str) -> list[dict]`: Helper to match text against config-driven patterns.

## Usage

```python
from codebase_index.parsers.base import BaseParser, ParserRegistry

# Register a new parser using decorator
@ParserRegistry.register("rust", [".rs"])
class RustParser(BaseParser):
    def scan(self, filepath: Path) -> dict:
        # Parse .rs files and return structured data
        return {"functions": [], "structs": []}

# Get a parser for a file
parser, language = ParserRegistry.get_parser(Path("main.rs"))
if parser:
    result = parser.scan(Path("main.rs"))
```

---
*Source: codebase_index/parsers/base.py | Lines: 285*
