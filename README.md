# Codebase Index

A CLI tool that generates comprehensive, LLM-friendly inventories of your codebase. **Built for AI assistants** like Claude Code, Cursor, and Copilot to understand, navigate, and analyze code.

## Why?

LLMs work better when they have structured context about your codebase. This tool extracts:
- **What exists**: Functions, classes, routes, models, schemas
- **How it connects**: Call graphs, imports, dependencies
- **Where things are**: File locations, line numbers, categories
- **What's missing**: Test coverage gaps, orphaned files, documentation

## Supported & Limitations

| ✅ Works Well | ⚠️ May Miss |
|--------------|-------------|
| Python (full AST parsing) | Dynamic/runtime routes |
| TypeScript/JavaScript | Metaprogramming |
| FastAPI, Flask, Django, Express | Unusual decorator patterns |
| SQLAlchemy, Pydantic, Django ORM | Complex inheritance |
| Standard project structures | Code generation |

**Config-driven**: Easily extend for new frameworks by adding regex patterns. See `--init-config`.

**Always verify**: Static analysis has limits. Check critical findings against source code.

## Quick Start

```bash
# Install (Python 3.9+)
pip install pyyaml  # Optional: for config file support

# Basic scan (outputs JSON to stdout)
python -m codebase_index .

# Save to file
python -m codebase_index . -o index.json

# Summary only
python -m codebase_index . --summary

# Exclude non-essential directories
python -m codebase_index . --exclude-dirs docs examples vendor -o index.json
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/codebase-index.git
cd codebase-index

# Run as a module
python -m codebase_index .

# Or use the legacy single-file script
python codebase_index.py .
```

**Requirements:**
- Python 3.9+
- PyYAML (optional, for config file support)

**Optional Features:**
```bash
# Semantic search (find code by description)
# Uses code-specific models: unixcoder, codebert, codet5
pip install codebase-index[semantic]

# LLM-generated summaries (supports multiple providers)
# Providers: OpenRouter (any model), Anthropic, OpenAI
pip install codebase-index[summaries]

# All optional features
pip install codebase-index[all]
```

**API Keys for Summaries:**
```bash
# Option 1: OpenRouter (recommended - access any model)
export OPENROUTER_API_KEY=sk-or-...

# Option 2: Anthropic direct
export ANTHROPIC_API_KEY=sk-ant-...

# Option 3: OpenAI
export OPENAI_API_KEY=sk-...

# Or pass via CLI: --api-key KEY --summary-provider PROVIDER
```

## System Requirements

### Base Tool (no optional features)
- **Python:** 3.9+
- **Memory:** Minimal (~50MB)
- **Disk:** ~5MB

### Semantic Search (`pip install codebase-index[semantic]`)

Requires PyTorch and sentence-transformers:

| Resource | Requirement |
|----------|-------------|
| **Disk** | ~3GB (PyTorch + models) |
| **Memory (CPU)** | ~2GB for embedding generation |
| **Memory (GPU)** | ~1GB VRAM (if using CUDA) |
| **Model cache** | ~/.cache/huggingface/hub (~500MB per model) |

**GPU Acceleration (optional but recommended for large codebases):**
- NVIDIA GPU with CUDA support
- CUDA 12.1+ drivers
- Works on CPU if no GPU available (slower)

**Embedding models:**
| Model | Size | Best for |
|-------|------|----------|
| `unixcoder` (default) | ~500MB | Code search (recommended) |
| `codebert` | ~500MB | Code + comments |
| `codet5` | ~900MB | Code understanding |
| `minilm` | ~90MB | Fast, general-purpose |

### LLM Summaries (`pip install codebase-index[summaries]`)
- **Disk:** ~10MB (httpx only)
- **Memory:** Minimal
- **Network:** API access to OpenRouter/Anthropic/OpenAI
- **Cost:** ~$0.01-0.05 per 100 functions (depends on model)

### Check Your Setup
```bash
# Check CUDA availability (for GPU acceleration)
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Check available memory
python -c "import torch; print('GPU Memory:', torch.cuda.get_device_properties(0).total_memory // 1e9, 'GB') if torch.cuda.is_available() else print('CPU only')"
```

### Troubleshooting

**"CUDA out of memory":**
```bash
# Use CPU instead
export CUDA_VISIBLE_DEVICES=""
codebase-index . --build-embeddings -o index.json
```

**"No module named torch":**
```bash
# Reinstall with CUDA support
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

**Slow embedding generation:**
- Use `--embedding-model minilm` for faster (but less accurate) results
- Ensure GPU is being used: check `torch.cuda.is_available()`

## Project Structure

```
codebase_index/
├── __init__.py           # Package init, exports CodebaseScanner
├── __main__.py           # Entry point for python -m
├── cli.py                # Command-line interface
├── config.py             # Configuration constants and loaders
├── utils.py              # Shared utility functions
├── scanner.py            # Main orchestrator
├── call_graph.py         # Call graph query functions
│
├── parsers/              # Language-specific parsers (plugin system)
│   ├── base.py           # BaseParser ABC + ParserRegistry
│   ├── python.py         # AST-based Python parser
│   ├── typescript.py     # Regex-based TypeScript/React parser
│   ├── sql.py            # SQL schema parser
│   └── docker.py         # Docker Compose YAML parser
│
├── scanners/             # Domain-specific scanners
│   ├── dependencies.py   # requirements.txt, package.json
│   ├── env.py            # Environment variables
│   ├── todo.py           # TODO/FIXME comments
│   ├── routes.py         # FastAPI router prefixes
│   ├── http_calls.py     # External HTTP calls
│   ├── middleware.py     # Middleware detection
│   ├── websocket.py      # WebSocket endpoints
│   └── alembic.py        # Database migrations
│
├── incremental.py        # Incremental index updates
│
└── analyzers/            # Code analysis tools
    ├── imports.py        # Missing/unused deps detection
    ├── auth.py           # Auth requirements per endpoint
    ├── complexity.py     # Large file/function warnings
    ├── coverage.py       # Test coverage mapping
    ├── orphans.py        # Dead code detection
    ├── staleness.py      # Index staleness detection
    ├── test_mapper.py    # Symbol-to-test mapping
    ├── impact.py         # Change impact radius analysis
    ├── schema_mapper.py  # Schema-to-endpoint mapping
    ├── coupling.py       # File coupling analysis
    ├── semantic.py       # Semantic search with embeddings
    └── summaries.py      # LLM-generated code summaries
```

## Adding a New Language Parser

The modular architecture makes it easy to add support for new languages:

```python
from pathlib import Path
from codebase_index.parsers.base import BaseParser, ParserRegistry

@ParserRegistry.register("rust", [".rs"])
class RustParser(BaseParser):
    """Rust parser using tree-sitter or regex."""

    def scan(self, filepath: Path) -> dict:
        # Parse the file and extract structure
        return {
            "functions": [
                {"name": "main", "line": 1, "async": False}
            ],
            "structs": [
                {"name": "Config", "line": 10}
            ],
            "imports": {
                "internal": ["crate::utils"],
                "external": ["serde", "tokio"]
            },
        }
```

The parser is automatically registered and will be used for `.rs` files.

## Features

### Core Scanning
| Feature | Description |
|---------|-------------|
| **Python AST Scanning** | Functions, classes, methods, imports via accurate AST parsing |
| **TypeScript/React** | Components, hooks, types, interfaces via regex |
| **FastAPI Routes** | Endpoints with methods, paths, auth requirements |
| **SQLAlchemy Models** | Tables with columns and relationships |
| **Pydantic Schemas** | Validation models |
| **Symbol Index** | Flat list of all symbols with `file:line` for fast lookup |
| **Docstrings** | Extracted from functions/classes |
| **Function Signatures** | Parameters with types, return types |

### Analysis
| Feature | Description |
|---------|-------------|
| **Import Analysis** | Missing/unused dependencies detection |
| **Test Coverage Mapping** | Source file → test file relationships |
| **External HTTP Calls** | URLs your code calls |
| **Complexity Warnings** | Large files, complex functions |
| **Orphaned Files** | Dead code detection (files never imported) |
| **Middleware Detection** | CORS, GZip, custom middleware |
| **WebSocket Endpoints** | Real-time endpoint scanning |
| **Alembic Migrations** | Migration history with operations |

### Call Graph & Duplicates
| Feature | Description |
|---------|-------------|
| **Call Graph** | What each function calls (for impact analysis) |
| **Code Duplication** | Hash-based duplicate detection |
| **Query Commands** | `--cg-query`, `--cg-file`, `--cg-callers` |

### Configuration
| Feature | Description |
|---------|-------------|
| **Custom Config** | YAML config for any framework (Django, Flask, Express) |
| **LLM-Friendly Template** | Generate config, customize with AI, run |

## CLI Reference

```
usage: codebase-index [-h] [-o OUTPUT] [--load FILE] [--no-hash]
                      [--summary] [--exclude EXCLUDE [EXCLUDE ...]]
                      [--exclude-dirs DIR [DIR ...]]
                      [--exclude-ext EXT [EXT ...]] [--config FILE]
                      [--init-config] [--cg-query FUNC] [--cg-file FILE]
                      [--cg-callers FUNC] [--check] [--tests-for SYMBOL]
                      [--impact FILE] [--schema NAME] [-v] [--version]
                      [path]
```

### Basic Options
| Flag | Description |
|------|-------------|
| `path` | Directory to scan (default: `.`) |
| `-o, --output FILE` | Save output to file |
| `--summary` | Only output summary statistics |
| `--no-hash` | Skip file hashing (faster) |
| `-v, --verbose` | Show progress and debug info |
| `--version` | Show version number |

### Exclusions
| Flag | Description |
|------|-------------|
| `--exclude PATTERN` | Exclude paths matching pattern |
| `--exclude-dirs DIR [DIR ...]` | Exclude specific directories |
| `--exclude-ext EXT [EXT ...]` | Exclude file extensions (e.g., `.md .txt`) |

### Configuration
| Flag | Description |
|------|-------------|
| `--config FILE` | Load custom YAML config |
| `--init-config` | Generate starter config template |

### Call Graph Queries
| Flag | Description |
|------|-------------|
| `--load FILE` | Load existing index (skip re-scanning) |
| `--cg-query FUNC` | What does FUNC call? |
| `--cg-file FILE` | Show call graph for all functions in FILE |
| `--cg-callers FUNC` | What functions call FUNC? |

### Analysis Queries
| Flag | Description |
|------|-------------|
| `--check` | Check if loaded index is stale (requires `--load`) |
| `--tests-for SYMBOL` | Find tests for a function/class (e.g., `UserService.create`) |
| `--impact FILE` | Show impact radius: callers, affected tests, affected endpoints |
| `--schema NAME` | Find endpoints using a schema (e.g., `AgentConfig`) |
| `--coupled-with FILE` | Find files tightly coupled to FILE (likely need changes together) |

### Advanced Features
| Flag | Description |
|------|-------------|
| `--update` | Incrementally update loaded index (only re-scan changed files) |
| `--build-embeddings` | Build embeddings for semantic search (requires `sentence-transformers`) |
| `--embedding-model MODEL` | Embedding model: `unixcoder` (default), `codebert`, `codet5`, `minilm` |
| `--search QUERY` | Semantic search: find code by description (requires embeddings) |
| `--generate-summaries` | Generate LLM summaries for functions (requires API key) |
| `--summary-provider PROVIDER` | Provider: `openrouter`, `anthropic`, `openai` (auto-detects from env) |
| `--summary-model MODEL` | Model name (e.g., `anthropic/claude-3-haiku`, `gpt-4o-mini`) |
| `--api-key KEY` | API key for summaries (alternative to environment variable) |

## Output Format

The tool outputs JSON with these sections:

```json
{
  "meta": {
    "generated_at": "2024-01-15T10:30:00Z",
    "tool_version": "2.0.0",
    "git": { "commit": "abc123", "branch": "main" }
  },
  "summary": {
    "total_files": 250,
    "total_lines": 45000,
    "by_language": { "python": { "files": 200, "lines": 40000 } },
    "api_endpoints_count": 45,
    "test_coverage_percent": 65
  },
  "files": [...],
  "api_endpoints": [...],
  "database": { "tables": [...] },
  "symbol_index": {
    "functions": [...],
    "classes": [...],
    "methods": [...]
  },
  "call_graph": {...},
  "potential_duplicates": [...],
  "import_analysis": {...},
  "test_coverage": {...}
}
```

### Symbol Index Format
```json
{
  "name": "create_user",
  "file": "src/api/services/user_service.py",
  "line": 45,
  "async": true,
  "signature": {
    "params": [
      { "name": "db", "type": "Session" },
      { "name": "user_data", "type": "UserCreate" }
    ],
    "return_type": "User"
  },
  "docstring": "Create a new user in the database."
}
```

### Call Graph Format
```json
{
  "src/api/services/user_service.py:create_user": {
    "file": "src/api/services/user_service.py",
    "line": 45,
    "calls": ["db.add", "db.commit", "db.refresh", "UserModel", "logger.info"]
  }
}
```

## Examples

### Basic Usage

```bash
# Scan current directory
python -m codebase_index .

# Scan with exclusions (recommended for cleaner output)
python -m codebase_index . \
  --exclude-dirs docs examples .archive node_modules \
  -o index.json

# Quick summary
python -m codebase_index . --summary --no-hash
```

### Call Graph Queries

```bash
# First, create an index
python -m codebase_index . -o index.json

# Query: What does UserService.create call?
python -m codebase_index --load index.json --cg-query UserService.create

# Query: All functions in a specific file
python -m codebase_index --load index.json --cg-file src/api/services/user_service.py

# Query: What calls the authenticate function?
python -m codebase_index --load index.json --cg-callers authenticate
```

### Analysis Queries

```bash
# Check if index is stale (detects changes since generation)
python -m codebase_index --load index.json --check
# Output: {"is_stale": true, "changed_files": [...], "summary": "48 files changed"}

# Find tests for a function/class
python -m codebase_index --load index.json --tests-for UserService.create
# Output: {"tests": [...], "test_files": ["tests/test_user_service.py"]}

# Analyze impact radius of changes to a file
python -m codebase_index --load index.json --impact src/services/auth.py
# Output: {"direct_callers": [...], "affected_tests": [...], "affected_endpoints": [...]}

# Find endpoints using a schema
python -m codebase_index --load index.json --schema UserCreate
# Output: {"endpoints": [{"method": "POST", "path": "/users"}], "usages": [...]}
```

### Using with LLMs

```bash
# Generate index for LLM context
python -m codebase_index . \
  --exclude-dirs docs tests \
  --summary \
  -o context.json

# Then share context.json with your LLM, or paste the summary
```

### Programmatic Usage

```python
from pathlib import Path
from codebase_index import CodebaseScanner

scanner = CodebaseScanner(
    root=Path("."),
    exclude=["node_modules", "__pycache__", ".git"],
    include_hash=True,
)

result = scanner.scan()
print(f"Total files: {result['summary']['total_files']}")
print(f"Total functions: {result['summary']['total_functions']}")
```

## Configuration for Other Frameworks

The default config is optimized for **FastAPI + SQLAlchemy + Pydantic**. For other stacks:

### Step 1: Generate Config Template
```bash
python -m codebase_index --init-config > codebase_index.yaml
```

### Step 2: Customize with LLM
Share the config with Claude/GPT and ask:
> "I have a Django + DRF project. Customize this config for my stack."

The config includes detailed comments explaining each section:
- Route detection patterns
- ORM model detection
- Schema/serializer detection
- Auth patterns
- File categorization rules

### Step 3: Run with Custom Config
```bash
python -m codebase_index . --config codebase_index.yaml -o index.json
```

### Example: Django Config Changes
```yaml
routes:
  patterns:
    - regex: "path\\(['\"]"
      framework: django

models:
  patterns:
    - base_class: "models.Model"
      type: django

schemas:
  patterns:
    - base_class: "Serializer"
      type: drf

auth:
  patterns:
    - decorator: login_required
      framework: django
```

## Use Cases

### 1. Onboarding / Documentation
```bash
# Generate comprehensive index
python -m codebase_index . -o index.json

# Share with new team members or documentation tools
```

### 2. Code Review Context
```bash
# Before reviewing a PR, understand what a function touches
python -m codebase_index --load index.json --cg-callers modified_function
```

### 3. Impact Analysis
```bash
# What would break if I change this file?
python -m codebase_index --load index.json --impact src/services/database.py

# Shows: direct callers, transitive callers, affected tests, affected endpoints
```

### 4. Finding Dead Code
```bash
# Check for orphaned files
python -m codebase_index . --summary | grep orphaned
```

### 5. Test Coverage Gaps
```bash
# Find tests for a specific function
python -m codebase_index --load index.json --tests-for UserService.create

# See which source files lack tests
python -m codebase_index . -o index.json
# Check test_coverage.uncovered_files in output
```

### 6. CI/CD: Stale Index Check
```bash
# Check if index needs regenerating before using cached version
python -m codebase_index --load index.json --check

# Output includes: is_stale, changed_files, new_files, deleted_files
```

### 7. Schema Usage Discovery
```bash
# Find all endpoints that use a schema
python -m codebase_index --load index.json --schema UserCreate

# Useful for: API documentation, breaking change detection
```

### 8. LLM-Assisted Development
```bash
# Give an LLM full codebase context
python -m codebase_index . \
  --exclude-dirs docs node_modules \
  -o index.json

# Then: "Based on index.json, help me add a new endpoint for..."
```

### 9. Coupling Analysis
```bash
# Find files tightly coupled to a specific file
python -m codebase_index --load index.json --coupled-with src/services/auth.py

# Output:
# {
#   "file": "src/services/auth.py",
#   "coupled_files": [
#     {"file": "src/routers/auth.py", "score": 0.85, "reasons": ["imports", "calls"]},
#     {"file": "tests/test_auth.py", "score": 0.65, "reasons": ["naming", "calls"]}
#   ],
#   "summary": "2 tightly coupled files"
# }
```

### 10. Incremental Updates
```bash
# First scan
python -m codebase_index . -o index.json

# Later: only re-scan changed files (much faster)
python -m codebase_index --load index.json --update -o index.json

# Shows: added, updated, deleted, unchanged file counts
```

### 11. Semantic Search
```bash
# Build embeddings (one-time, requires sentence-transformers)
pip install codebase-index[semantic]

# Default model: unixcoder (code-specific, recommended)
python -m codebase_index . --build-embeddings -o index.json

# Or choose a different model
python -m codebase_index . --build-embeddings --embedding-model codebert -o index.json

# Available models: unixcoder (default), codebert, codet5, minilm

# Search by concept, not keywords
python -m codebase_index --load index.json --search "retry logic with backoff"
python -m codebase_index --load index.json --search "database connection pool"

# Output:
# {
#   "query": "retry logic with backoff",
#   "results": [
#     {"symbol": "retry_with_exponential_backoff", "file": "src/utils/http.py", "score": 0.89}
#   ],
#   "model": "microsoft/unixcoder-base"
# }
```

### 12. LLM-Generated Summaries
```bash
# Install dependency
pip install codebase-index[summaries]

# Option 1: Use environment variable (auto-detects provider)
export OPENROUTER_API_KEY=sk-or-...   # Recommended: access any model
# OR export ANTHROPIC_API_KEY=sk-ant-...
# OR export OPENAI_API_KEY=sk-...
python -m codebase_index . --generate-summaries -o index.json

# Option 2: Pass API key directly (requires --summary-provider)
python -m codebase_index . --generate-summaries \
  --api-key "sk-or-..." \
  --summary-provider openrouter \
  --summary-model "anthropic/claude-3-haiku" \
  -o index.json

# Option 3: Use specific provider and model
python -m codebase_index . --generate-summaries \
  --summary-provider openai \
  --summary-model gpt-4o-mini \
  -o index.json

# Summaries are cached by code hash - subsequent runs only generate for changed code
```

## Output Size Considerations

| Codebase Size | Full Output | Summary Only |
|---------------|-------------|--------------|
| Small (<100 files) | ~500KB | ~2KB |
| Medium (~500 files) | ~3MB | ~3KB |
| Large (1000+ files) | ~10MB+ | ~5KB |

**Tips for LLM context limits:**
- Use `--summary` for overview
- Use `--cg-query` for specific lookups
- Use `--exclude-dirs` to focus on core code
- The call graph queries return focused, small results

## Version History

| Version | Features |
|---------|----------|
| 2.2 | **Advanced features**: `--coupled-with`, `--update`, `--search`, `--build-embeddings`, `--generate-summaries` |
| 2.1 | **Analysis queries**: `--check` staleness, `--tests-for`, `--impact`, `--schema` |
| 2.0 | **Modular architecture**, plugin system for parsers, proper logging |
| 1.7 | YAML config, --init-config, multi-framework support |
| 1.6 | Call graph, code duplication, query commands |
| 1.5 | Symbol index, docstrings, function signatures |
| 1.4 | Orphaned file detection |
| 1.3 | Middleware, WebSockets, Alembic migrations |
| 1.2 | Import analysis, auth detection, test mapping, complexity |
| 1.0 | Python AST, TypeScript regex, basic scanning |

## Contributing

Issues and PRs welcome. Key areas for improvement:
- Additional language parsers (Go, Rust, Java, C#)
- Framework-specific scanners (NestJS, Spring, Rails)
- Smarter duplicate detection
- Integration with IDEs
- Tree-sitter based parsing for more languages

### Adding a Language Parser

1. Create a new file in `codebase_index/parsers/`
2. Inherit from `BaseParser`
3. Use `@ParserRegistry.register()` decorator
4. Implement the `scan()` method

See `parsers/python.py` for a full example with AST parsing and regex fallback.

## License

MIT
