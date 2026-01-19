# Analyzers

> Auto-generated documentation for `codebase_index/analyzers/`

The analyzers module provides tools for analyzing codebase structure, dependencies, complexity, and more using the indexed data.

## Module Index

| Module | Description |
|--------|-------------|
| [auth.md](auth.md) | Authentication requirements scanner - detects auth patterns in endpoint signatures and decorators |
| [centrality.md](centrality.md) | Call graph centrality analyzer - identifies core vs helper components |
| [complexity.md](complexity.md) | Code complexity analyzer - flags large files, functions, and complex classes |
| [coverage.md](coverage.md) | Test coverage mapper - maps source files to corresponding test files |
| [doc_generator.md](doc_generator.md) | Documentation generator - produces rich Markdown docs for symbols |
| [execution_flow.md](execution_flow.md) | Execution flow analyzer - traces code paths from entry points |
| [impact.md](impact.md) | Impact radius analyzer - finds callers, tests, and endpoints affected by changes |
| [imports.md](imports.md) | Import aggregator - detects missing and unused dependencies |
| [orphans.md](orphans.md) | Orphaned file scanner - detects Python files never imported (dead code) |
| [semantic.md](semantic.md) | Semantic search - finds code by concept using embeddings |
| [staleness.md](staleness.md) | Staleness checker - determines if index is out of date |
| [test_mapper.md](test_mapper.md) | Test mapper - finds tests for symbols via imports, calls, and naming |

## Quick Reference

### Analysis Categories

**Code Quality:**
- `ComplexityAnalyzer` - File/function size thresholds
- `OrphanedFileScanner` - Dead code detection

**Dependencies:**
- `ImportAggregator` - Missing/unused deps
- `ImpactAnalyzer` - Change impact radius

**Architecture:**
- `CentralityAnalyzer` - Core vs utility classification
- `ExecutionFlowAnalyzer` - Entry point tracing

**Testing:**
- `TestMapper` - Symbol to test mapping
- `TestCoverageMapper` - Source to test file mapping

**Search & Documentation:**
- `SemanticSearcher` - Concept-based code search
- `DocumentationGenerator` - Rich symbol docs

**Security:**
- `AuthScanner` - Endpoint auth detection

**Maintenance:**
- `StalenessChecker` - Index freshness

## Common Usage Patterns

```python
import json
from pathlib import Path

# Load index
with open("index.json") as f:
    index_data = json.load(f)

# Impact analysis before modifying a file
from codebase_index.analyzers.impact import ImpactAnalyzer
analyzer = ImpactAnalyzer(index_data)
impact = analyzer.analyze_file("src/core/service.py")
print(impact["summary"])

# Find code by concept
from codebase_index.analyzers.semantic import semantic_search
results = semantic_search(index_data, "error handling with retry")

# Check what calls a function
from codebase_index.analyzers.test_mapper import TestMapper
mapper = TestMapper(index_data)
tests = mapper.find_tests_for("MyClass.important_method")
```

---
*Source: codebase_index/analyzers/*
