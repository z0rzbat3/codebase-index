# call_graph

> Auto-generated from `codebase_index/call_graph.py`

## Overview

Call graph query functions for codebase_index. Provides functions to query the call graph for impact analysis, including finding callers, callees, and file-level call relationships.

## Functions

### `cg_query_function(call_graph, func_name) -> dict[str, Any]`

Query what a specific function calls (fuzzy match).

**Parameters:**
- `call_graph`: The call graph dictionary
- `func_name`: Function name to search for

**Returns:** Dictionary with query info and matching results containing:
- `query`: The original function name
- `query_type`: "what_does_it_call"
- `matches`: Number of matching functions
- `results`: Dict of matching function entries with their call info

### `cg_query_file(call_graph, file_path) -> dict[str, Any]`

Query all functions in a specific file.

**Parameters:**
- `call_graph`: The call graph dictionary
- `file_path`: File path to search for

**Returns:** Dictionary with query info and matching results containing:
- `query`: The file path
- `query_type`: "file_call_graph"
- `matches`: Number of functions in the file
- `results`: Dict of function entries from that file

### `cg_query_callers(call_graph, func_name) -> dict[str, Any]`

Query what functions call a specific function (inverse lookup).

**Parameters:**
- `call_graph`: The call graph dictionary
- `func_name`: Function name to find callers of

**Returns:** Dictionary with query info and matching results containing:
- `query`: The function name
- `query_type`: "what_calls_it"
- `matches`: Number of callers found
- `results`: Dict of caller functions with file, line, and matching_calls

## Usage

```python
from codebase_index.call_graph import cg_query_callers, cg_query_function

# Find what calls a function
callers = cg_query_callers(call_graph, "process_data")
print(f"Found {callers['matches']} callers")

# Find what a function calls
callees = cg_query_function(call_graph, "main")
for name, info in callees['results'].items():
    print(f"{name} calls: {info.get('calls', [])}")
```

---
*Source: codebase_index/call_graph.py | Lines: 104*
