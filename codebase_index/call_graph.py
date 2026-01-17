"""
Call graph query functions for codebase_index.

Provides functions to query the call graph for impact analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def cg_query_function(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]:
    """
    Query what a specific function calls (fuzzy match).

    Args:
        call_graph: The call graph dictionary.
        func_name: Function name to search for.

    Returns:
        Dictionary with query info and matching results.
    """
    results: dict[str, Any] = {}
    func_lower = func_name.lower()

    for key, info in call_graph.items():
        # Match on function name (last part of key)
        key_func = key.split(":")[-1].lower()
        if func_lower in key_func or func_lower in key.lower():
            results[key] = info

    return {
        "query": func_name,
        "query_type": "what_does_it_call",
        "matches": len(results),
        "results": results,
    }


def cg_query_file(call_graph: dict[str, Any], file_path: str) -> dict[str, Any]:
    """
    Query all functions in a specific file.

    Args:
        call_graph: The call graph dictionary.
        file_path: File path to search for.

    Returns:
        Dictionary with query info and matching results.
    """
    results: dict[str, Any] = {}
    file_lower = file_path.lower()

    for key, info in call_graph.items():
        if file_lower in info.get("file", "").lower():
            results[key] = info

    return {
        "query": file_path,
        "query_type": "file_call_graph",
        "matches": len(results),
        "results": results,
    }


def cg_query_callers(call_graph: dict[str, Any], func_name: str) -> dict[str, Any]:
    """
    Query what functions call a specific function (inverse lookup).

    Args:
        call_graph: The call graph dictionary.
        func_name: Function name to find callers of.

    Returns:
        Dictionary with query info and matching results.
    """
    results: dict[str, Any] = {}
    func_lower = func_name.lower()

    for key, info in call_graph.items():
        calls = info.get("calls", [])
        matching_calls: list[str] = []

        for call in calls:
            if func_lower in call.lower():
                matching_calls.append(call)

        if matching_calls:
            results[key] = {
                "file": info.get("file"),
                "line": info.get("line"),
                "matching_calls": matching_calls,
            }

    return {
        "query": func_name,
        "query_type": "what_calls_it",
        "matches": len(results),
        "results": results,
    }
