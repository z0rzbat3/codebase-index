# ExecutionFlowAnalyzer

> Auto-generated from `codebase_index/analyzers/execution_flow.py`

## Overview

Traces code paths from entry points through the call graph. Analyzes how code flows from entry points (main, CLI handlers, routes) through the system.

## Classes

### `ExecutionFlowAnalyzer`

Analyzes execution flow from entry points through the call graph.

#### Methods

- `__init__(index_data: dict[str, Any])`: Initialize with loaded codebase index.
- `analyze(max_depth: int = 6) -> dict[str, Any]`: Analyze execution flow from all detected entry points.
- `find_entry_points() -> list[dict[str, Any]]`: Find entry point functions in the codebase.
- `trace_flow(start_key, max_depth, visited) -> dict[str, Any]`: Trace execution flow from a starting function with cycle detection.
- `format_flow_tree(flow, indent) -> str`: Format a flow tree as a readable ASCII tree.

## Entry Point Detection

Entry points are detected by:

**Name patterns:**
- `main`, `cli`, `run`, `start`, `app`, `execute`
- Names starting with `main` or `setup_`

**Decorators:**
- `@click.command`, `@click.group`, `@typer.command`
- `@app.route`, `@app.get`, `@app.post`, `@router.get`, etc.

**File patterns:**
- `__main__.py` files

## Return Structure

```python
{
    "entry_points": [
        {"name": "main", "file": "cli.py", "line": 10, "key": "cli.py:main", "reason": "name matches 'main'"}
    ],
    "flows": [
        {
            "entry_point": {...},
            "flow": {"name": "main", "file": "...", "calls": [...]},
            "depth": 4,
            "total_calls": 12
        }
    ],
    "summary": {
        "total_entry_points": 5,
        "max_depth": 6,
        "total_unique_functions": 45
    }
}
```

## Functions

### `analyze_execution_flow(index_data, max_depth)`

Convenience function to analyze execution flow.

**Parameters:**
- `index_data: dict[str, Any]` - The codebase index
- `max_depth: int` - Maximum depth to trace (default: 6)

**Returns:** `dict[str, Any]` - Execution flow analysis results

## Usage

```python
from codebase_index.analyzers.execution_flow import ExecutionFlowAnalyzer

analyzer = ExecutionFlowAnalyzer(index_data)
results = analyzer.analyze(max_depth=5)

# Print flow tree
for flow_info in results["flows"]:
    print(analyzer.format_flow_tree(flow_info["flow"]))
```

---
*Source: codebase_index/analyzers/execution_flow.py | Lines: 368*
