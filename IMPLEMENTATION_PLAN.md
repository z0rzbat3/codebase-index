# Advanced Features Implementation Plan

## Overview

Four advanced features to make codebase-index more powerful for LLM assistants:

1. **Coupling Analysis** - "You might also need to change X"
2. **Incremental Updates** - Only re-scan changed files
3. **Semantic Search** - Find code by concept, not keywords
4. **Code Summaries** - LLM-generated function descriptions

---

## Feature 1: Coupling Analysis (`--coupled-with`)

### Goal
When editing a file, show other files that are tightly coupled and likely need changes too.

### Implementation

**File:** `codebase_index/analyzers/coupling.py`

**Algorithm:**
```
coupling_score(A, B) = weighted sum of:
  - call_frequency: How often A calls functions in B (and vice versa)
  - import_dependency: Does A import from B?
  - shared_imports: Do A and B import the same modules?
  - naming_similarity: Similar file/function names (e.g., user_service.py ↔ user_router.py)
  - co-change_history: (future) Git history of files changed together
```

**CLI:**
```bash
codebase-index --load index.json --coupled-with src/services/auth.py
```

**Output:**
```json
{
  "file": "src/services/auth.py",
  "coupled_files": [
    {"file": "src/routers/auth.py", "score": 0.85, "reasons": ["imports", "calls"]},
    {"file": "src/schemas/auth.py", "score": 0.72, "reasons": ["naming", "imports"]},
    {"file": "tests/test_auth.py", "score": 0.65, "reasons": ["imports", "calls"]}
  ],
  "summary": "3 tightly coupled files; consider reviewing when making changes"
}
```

**Effort:** ~100 lines, no new dependencies

---

## Feature 2: Incremental Updates (`--update`)

### Goal
Re-scan only files that changed since last index generation, for fast updates.

### Implementation

**File:** `codebase_index/incremental.py`

**Algorithm:**
```
1. Load existing index
2. For each file in codebase:
   - If file not in index → scan and add
   - If file hash changed → re-scan and update
   - If file in index but deleted → remove from index
3. Update metadata (timestamp, file counts)
4. Rebuild affected call graph edges
```

**CLI:**
```bash
# Update existing index
codebase-index --load index.json --update -o index.json

# Watch mode (optional, requires watchdog)
codebase-index --watch . -o index.json
```

**Output:**
```json
{
  "updated": ["src/services/auth.py", "src/routers/users.py"],
  "added": ["src/new_feature.py"],
  "deleted": ["src/old_code.py"],
  "unchanged": 245,
  "duration_ms": 150
}
```

**Effort:** ~150 lines, watchdog optional

---

## Feature 3: Semantic Search (`--search`)

### Goal
Find code by describing what it does, not exact keywords.

### Implementation

**File:** `codebase_index/analyzers/semantic.py`

**Dependencies:** `sentence-transformers` (optional install)

**Algorithm:**
```
At index time (--build-embeddings):
1. For each function/class, create text: "{name} {docstring} {signature}"
2. Generate embedding using sentence-transformers
3. Store embeddings in index (or separate .npy file)

At query time (--search "query"):
1. Generate embedding for query
2. Cosine similarity against all stored embeddings
3. Return top-k matches with scores
```

**CLI:**
```bash
# Build embeddings (one-time, ~30s for 500 files)
codebase-index . --build-embeddings -o index.json

# Search
codebase-index --load index.json --search "retry logic with backoff"
codebase-index --load index.json --search "handle authentication errors"
```

**Output:**
```json
{
  "query": "retry logic with backoff",
  "results": [
    {
      "symbol": "retry_with_exponential_backoff",
      "file": "src/utils/http.py",
      "line": 45,
      "score": 0.89,
      "snippet": "def retry_with_exponential_backoff(func, max_retries=3):"
    },
    {
      "symbol": "HttpClient._retry_request",
      "file": "src/clients/base.py",
      "line": 112,
      "score": 0.76,
      "snippet": "async def _retry_request(self, request, attempts=3):"
    }
  ]
}
```

**Effort:** ~200 lines + optional dependency

**Install:** `pip install codebase-index[semantic]`

---

## Feature 4: Code Summaries (`--generate-summaries`)

### Goal
Generate one-line descriptions of what each function does using an LLM.

### Implementation

**File:** `codebase_index/analyzers/summaries.py`

**Dependencies:** `anthropic` or `openai` SDK (optional)

**Algorithm:**
```
1. For each function without a docstring (or all if --force):
   - Extract function signature + first 50 lines of body
   - Call LLM: "Summarize in one line what this function does: {code}"
   - Cache result keyed by function hash
2. Store summaries in index under each function
3. Incremental: only generate for new/changed functions
```

**CLI:**
```bash
# Generate summaries (requires API key)
export ANTHROPIC_API_KEY=...
codebase-index . --generate-summaries -o index.json

# Use cached summaries, only generate for new functions
codebase-index . --generate-summaries --incremental -o index.json

# Search summaries (combines with semantic search)
codebase-index --load index.json --search "validates user input"
```

**Output in index:**
```json
{
  "functions": [
    {
      "name": "validate_email",
      "line": 23,
      "summary": "Validates email format using regex and checks for disposable domains",
      "summary_generated": true
    }
  ]
}
```

**Cost estimate:** ~$0.01 per 100 functions using Claude Haiku

**Effort:** ~150 lines + optional dependency

**Install:** `pip install codebase-index[summaries]`

---

## Implementation Order

| Order | Feature | Why |
|-------|---------|-----|
| 1 | Coupling Analysis | No deps, extends existing --impact |
| 2 | Incremental Updates | No deps, major performance win |
| 3 | Semantic Search | Adds optional dep, high value |
| 4 | Code Summaries | Needs API key, most complex |

---

## File Changes Summary

### New Files
- `codebase_index/analyzers/coupling.py` - Coupling score calculation
- `codebase_index/incremental.py` - Incremental update logic
- `codebase_index/analyzers/semantic.py` - Embedding + vector search
- `codebase_index/analyzers/summaries.py` - LLM summary generation

### Modified Files
- `codebase_index/cli.py` - Add new CLI flags
- `pyproject.toml` - Add optional dependencies
- `README.md` - Document new features

### New CLI Flags
```
--coupled-with FILE    Show files tightly coupled to FILE
--update               Incrementally update loaded index
--watch                Watch for file changes (requires watchdog)
--build-embeddings     Generate embeddings for semantic search
--search QUERY         Semantic search for code
--generate-summaries   Generate LLM summaries for functions
```

---

## Optional Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
semantic = ["sentence-transformers>=2.2.0", "numpy>=1.20.0"]
summaries = ["anthropic>=0.18.0"]
watch = ["watchdog>=3.0.0"]
all = ["codebase-index[semantic,summaries,watch]"]
```

---

## Timeline

- Feature 1 (Coupling): ~30 min
- Feature 2 (Incremental): ~45 min
- Feature 3 (Semantic): ~60 min
- Feature 4 (Summaries): ~45 min

Total: ~3 hours

---

## Success Criteria

1. **Coupling:** `--coupled-with` returns ranked list of related files
2. **Incremental:** `--update` is 10x faster than full scan on large codebases
3. **Semantic:** `--search "error handling"` finds relevant code even without keyword match
4. **Summaries:** Functions have human-readable one-line descriptions
