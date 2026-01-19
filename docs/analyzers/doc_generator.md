# DocumentationGenerator

> Auto-generated from `codebase_index/analyzers/doc_generator.py`

## Overview

Generates rich documentation for symbols by combining symbol info, LLM summaries, call graph data, related tests, and code snippets. Output is formatted as Markdown.

## Classes

### `DocumentationGenerator`

Generates comprehensive documentation for code symbols.

#### Methods

- `__init__(index_data: dict[str, Any], root: Path | None = None)`: Initialize with codebase index and optional root directory.
- `generate_for_symbol(symbol_name: str) -> dict[str, Any]`: Generate documentation for a symbol. Supports partial matching and `Class.method` format.
- `_find_symbols(name: str) -> list[dict[str, Any]]`: Find symbols matching the given name.
- `_generate_symbol_doc(symbol) -> dict[str, Any]`: Generate documentation for a single symbol.
- `_get_callers(name, file_path) -> list[dict[str, Any]]`: Get functions that call this symbol.
- `_get_calls(name, file_path) -> list[str]`: Get functions that this symbol calls.
- `_get_tests(name) -> list[dict[str, Any]]`: Get tests for this symbol via TestMapper.
- `_get_code_snippet(file_path, line, context) -> str`: Get code snippet from source file.
- `_format_markdown(...) -> str`: Format documentation as Markdown.

## Functions

### `generate_doc_for_symbol(index_data, symbol_name, root)`

Convenience function to generate documentation for a symbol.

**Parameters:**
- `index_data: dict[str, Any]` - The codebase index
- `symbol_name: str` - Symbol to document
- `root: Path | None` - Root directory for reading source files

**Returns:** `dict[str, Any]` - Documentation data with markdown output

## Generated Markdown Structure

```markdown
# SymbolName
**Type:** function|class|method
**File:** `path/to/file.py:42`

## Summary
LLM-generated summary...

## Description
Docstring content...

## Signature
```python
def func(param: Type) -> ReturnType
```

## Parameters
| Name | Type | Default |
|------|------|---------|

## Calls
- `called_function`

## Called By
- `caller_function` in `file.py:10`

## Tests
**test_file.py:**
- `test_func`

## Source Code
```python
# Code snippet
```
```

## Usage

```python
from codebase_index.analyzers.doc_generator import generate_doc_for_symbol

result = generate_doc_for_symbol(index_data, "CodebaseScanner", root=Path("."))
print(result["markdown"])
```

---
*Source: codebase_index/analyzers/doc_generator.py | Lines: 429*
