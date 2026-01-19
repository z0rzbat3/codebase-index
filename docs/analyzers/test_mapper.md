# TestMapper

> Auto-generated from `codebase_index/analyzers/test_mapper.py`

## Overview

Maps symbols (functions, classes) to their tests by analyzing imports, call graphs, and naming conventions.

## Classes

### `TestMapper`

Maps symbols to their tests.

#### Properties

- `test_files: list[dict[str, Any]]`: All test files from the index (lazy-loaded).
- `call_graph: dict[str, Any]`: Call graph from the index (lazy-loaded).

#### Methods

- `__init__(index_data: dict[str, Any])`: Initialize with loaded index data.
- `find_tests_for(symbol: str) -> dict[str, Any]`: Find tests for a given symbol.
- `_imports_symbol(imports, symbol, class_name, method_name) -> bool`: Check if imports contain the symbol.
- `_calls_symbol(file_path, symbol, class_name, method_name) -> bool`: Check if file calls the symbol via call graph.
- `_find_matching_test_functions(exports, class_name, method_name) -> list[str]`: Find test functions matching naming conventions.
- `_find_callers_in_tests(symbol) -> list[str]`: Find test functions that call the symbol.
- `_build_summary(result) -> str`: Build human-readable summary.

## Test File Detection

Files are identified as tests if their path:
- Starts with `test_` or `tests/`
- Contains `/test_` or `/tests/`
- Ends with `_test.py`, `.test.ts`, `.test.js`, `.spec.ts`, `.spec.js`
- Contains `/__tests__/`

## Return Structure

```python
{
    "symbol": "MyClass.my_method",
    "tests": [
        {
            "file": "tests/test_myclass.py",
            "imports_symbol": True,
            "calls_symbol": True,
            "test_functions": ["test_my_method", "test_my_method_edge_case"]
        }
    ],
    "test_files": ["tests/test_myclass.py"],
    "importers": ["tests/test_myclass.py"],
    "callers": ["tests/test_myclass.py:test_my_method"],
    "summary": "Found 1 test file(s) for 'MyClass.my_method'; 2 test function(s) call this symbol"
}
```

## Naming Convention Matching

For symbol `my_function`:
- `test_my_function`, `test_my_function_*`
- `testMyFunction` (camelCase)

For `MyClass.my_method`:
- `test_MyClass_my_method`
- `TestMyClass` class with `test_my_method` method

## Usage

```python
from codebase_index.analyzers.test_mapper import TestMapper

mapper = TestMapper(index_data)

# Find tests for a function
result = mapper.find_tests_for("parse_config")
print(result["summary"])

# Find tests for a class method
result = mapper.find_tests_for("AgentFactory.create")
for test in result["tests"]:
    print(f"  {test['file']}: {test['test_functions']}")
```

---
*Source: codebase_index/analyzers/test_mapper.py | Lines: 330*
