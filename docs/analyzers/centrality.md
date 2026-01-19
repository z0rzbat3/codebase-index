# CentralityAnalyzer

> Auto-generated from `codebase_index/analyzers/centrality.py`

## Overview

Computes graph centrality metrics on the call graph to identify which functions/classes are central to the codebase (core) vs peripheral (helpers/utilities).

## Classes

### `CentralityAnalyzer`

Analyzes call graph centrality to classify functions as core, hub, utility, or isolated based on their position in the call graph.

#### Methods

- `__init__(index_data: dict[str, Any]) -> None`: Initialize with loaded codebase index.
- `analyze() -> dict[str, Any]`: Analyze centrality and classify components. Returns core, hub, utility, isolated components with summary.
- `_build_metrics() -> None`: Build centrality metrics (in-degree, out-degree) from call graph.
- `_classify_components(scores) -> dict[str, str]`: Classify each component by its role.
- `_is_core(score) -> bool`: Check if component is core (highly called by others, top 5% in-degree).
- `_is_hub(score) -> bool`: Check if component is a hub (calls many others, top 5% out-degree).
- `_is_utility(score) -> bool`: Check if component is a utility (called often, calls little).
- `_is_isolated(score) -> bool`: Check if component is isolated (no callers, few calls).
- `get_component_role(key: str) -> str`: Get role classification for a specific component.
- `get_importance_score(key: str) -> float`: Get importance score (0-1) for a component.

## Functions

### `analyze_centrality(index_data)`

Convenience function to analyze centrality.

**Parameters:**
- `index_data: dict[str, Any]` - The codebase index

**Returns:** `dict[str, Any]` - Centrality analysis results

## Classification Criteria

| Role | Description | Criteria |
|------|-------------|----------|
| **core** | Central to system functionality | Top 5% in-degree (min 3) |
| **hub** | Orchestrators/entry points | Top 5% out-degree, below-avg in-degree |
| **utility** | Helper functions | Above-avg in-degree, below-avg out-degree |
| **isolated** | Dead code or entry points | 0 callers, <=2 calls |
| **standard** | Everything else | Default classification |

## Usage

```python
from codebase_index.analyzers.centrality import CentralityAnalyzer, analyze_centrality

# Quick analysis
results = analyze_centrality(index_data)
print(results["summary"])
# {"total_functions": 150, "core_count": 8, "hub_count": 5, ...}

# Detailed analysis
analyzer = CentralityAnalyzer(index_data)
role = analyzer.get_component_role("myfile.py:my_function")
score = analyzer.get_importance_score("myfile.py:my_function")
```

---
*Source: codebase_index/analyzers/centrality.py | Lines: 295*
