# SemanticSearcher

> Auto-generated from `codebase_index/analyzers/semantic.py`

## Overview

Uses code-specific embeddings to find code by concept/description, not just keyword matching. Embeds actual code bodies for better results.

**Requires:** `pip install codebase-index[semantic]` (sentence-transformers, numpy)

## Classes

### `SemanticSearcher`

Semantic search over code using embeddings.

#### Methods

- `__init__(model_key: str = "unixcoder", cache_dir: Path | None = None)`: Initialize with model key or HuggingFace model name.
- `build_embeddings(index_data, root) -> dict[str, Any]`: Build embeddings for all symbols in the index.
- `load_embeddings(embedding_data) -> None`: Load pre-computed embeddings.
- `search(query: str, top_k: int = 10, min_score: float = 0.3) -> dict[str, Any]`: Search for code matching the query.

## Available Models

| Key | Model | Max Tokens | Description |
|-----|-------|------------|-------------|
| `unixcoder` | microsoft/unixcoder-base | 512 | Code-specific, recommended |
| `codebert` | microsoft/codebert-base | 512 | Code + comments |
| `codet5` | Salesforce/codet5-base | 512 | Code understanding |
| `minilm` | all-MiniLM-L6-v2 | 256 | Fast general-purpose |

## Semantic Tags

Code is automatically tagged with semantic patterns for better conceptual search:

- `[error-handling]`, `[exception-catch]`, `[exception-raise]`
- `[async]`, `[awaits]`
- `[caching]`, `[retry-logic]`
- `[file-io]`, `[http-client]`, `[database]`
- `[authentication]`, `[crypto]`
- `[testing]`, `[logging]`

## Functions

### `build_embeddings(index_data, root, model, changed_files)`

Build or incrementally update embeddings.

### `semantic_search(index_data, query, top_k, model, min_score)`

Convenience function for semantic search.

### `check_semantic_available() -> bool`

Check if semantic search dependencies are available.

### `list_models() -> dict[str, Any]`

List available embedding models.

## Usage

```python
from codebase_index.analyzers.semantic import semantic_search, build_embeddings

# Build embeddings (one-time)
index_data = build_embeddings(index_data, root=Path("."), model="unixcoder")

# Search by concept
results = semantic_search(
    index_data,
    query="retry logic with exponential backoff",
    top_k=5,
    min_score=0.4
)

for r in results["results"]:
    print(f"{r['symbol']} ({r['score']:.2f}): {r['snippet'][:50]}...")
```

---
*Source: codebase_index/analyzers/semantic.py | Lines: 807*
