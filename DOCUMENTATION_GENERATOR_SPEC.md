# Documentation Generator Specification

**Author:** Claude Code (QA Tester)
**Date:** 2026-01-17
**Status:** Ready for Implementation

---

## Overview

Extend codebase-index to automatically generate and maintain code documentation using the existing index data. The index already contains all necessary information - this feature formats it as human-readable documentation.

---

## Documentation Layers

The tool should generate **4 types of documentation**, each serving different audiences:

| Layer | Output | Audience | Data Sources |
|-------|--------|----------|--------------|
| Module READMEs | `{module}/README.md` | Developers navigating codebase | `files`, `call_graph`, `summaries` |
| API Reference | `docs/api/*.md` | API consumers | `api_endpoints`, `schemas` |
| Function Reference | `docs/reference/*.md` | Developers using/extending code | `symbol_index`, `summaries`, `call_graph` |
| Architecture | `docs/architecture/*.md` | New team members | `call_graph`, `import_analysis`, `coupled_with` |

---

## Proposed CLI Interface

### 1. Generate All Documentation

```bash
codebase-index --load index.json --generate-docs --output-dir docs/generated/
```

**Flags:**
- `--generate-docs` - Enable documentation generation mode
- `--output-dir DIR` - Where to write generated docs (default: `docs/generated/`)
- `--doc-layers LAYERS` - Comma-separated: `modules,api,reference,architecture` (default: all)
- `--doc-template DIR` - Custom Jinja2 templates directory
- `--doc-format FORMAT` - Output format: `markdown`, `html`, `rst` (default: markdown)

### 2. Generate Documentation for Single Symbol

```bash
codebase-index --load index.json --doc-for "ChatService"
```

**Output:** Full markdown documentation for the symbol including:
- Summary/description
- Parameters and return types
- Code snippet
- What it calls (`--cg-query`)
- What calls it (`--cg-callers`)
- Related tests (`--tests-for`)
- Related symbols (via semantic search)
- Usage examples (if LLM enabled)

### 3. Check Documentation Freshness

```bash
codebase-index --load index.json --doc-diff --doc-dir docs/
```

**Output:**
```json
{
  "stale": [
    {
      "doc": "docs/api/chat_service.md",
      "source": "src/api/services/chat_service.py",
      "source_modified": "2026-01-17T10:00:00Z",
      "doc_modified": "2026-01-15T08:00:00Z",
      "reason": "Source newer than documentation"
    }
  ],
  "missing": [
    {
      "source": "src/api/routers/workspaces.py",
      "suggested_doc": "docs/api/workspaces.md",
      "reason": "Router has no documentation"
    }
  ],
  "ok": [
    "docs/api/agents.md",
    "docs/api/health.md"
  ],
  "summary": "2 stale, 1 missing, 2 ok"
}
```

### 4. Watch Mode (Optional)

```bash
codebase-index --load index.json --generate-docs --watch
```

Watches for file changes and regenerates affected documentation automatically.

---

## Output Formats

### Module README Template

**File:** `{module_dir}/README.md`

```markdown
# {module_name}

{module_summary - LLM generated from file summaries}

## Files

| File | Purpose | Lines |
|------|---------|-------|
| chat_service.py | {summary} | 450 |
| agent_service.py | {summary} | 320 |

## Key Classes/Functions

### ChatService
{summary}

**Methods:**
- `stream_chat()` - {summary}
- `send_message()` - {summary}

**Used by:** {callers}
**Tests:** {test_files}

## Dependencies

**Internal:**
- `src/openai_agents/agent_spawner.py`
- `src/db/repositories/chat.py`

**External:**
- `openai`
- `fastapi`

## Related Modules

- `src/api/routers/chat.py` - Routes that use this service
- `src/db/models/chat.py` - Database models
```

### API Reference Template

**File:** `docs/api/{router_name}.md`

```markdown
# {Router Name} API

Base path: `/api/v1/{base}`

## Endpoints

### POST /api/v1/agents

Create a new agent.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "string",
  "model": "string",
  "instructions": "string"
}
```
Schema: `AgentCreateRequest`

**Response:**
```json
{
  "id": "uuid",
  "name": "string",
  "created_at": "datetime"
}
```
Schema: `AgentResponse`

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "model": "gpt-4o"}'
```

---

### GET /api/v1/agents/{agent_id}

{... continue for each endpoint}
```

### Function Reference Template

**File:** `docs/reference/{module_name}.md`

```markdown
# {module_name} Reference

## Classes

### ChatService

{docstring or LLM summary}

**File:** `src/api/services/chat_service.py:45`

#### Methods

##### stream_chat

```python
async def stream_chat(
    self,
    agent_id: UUID,
    message: str,
    session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
```

{summary}

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| agent_id | UUID | The agent to chat with |
| message | str | User message |
| session_id | Optional[str] | Session for conversation history |

**Returns:** `AsyncGenerator[str, None]` - Streaming response chunks

**Raises:**
- `AgentNotFoundError` - If agent_id doesn't exist
- `AuthenticationError` - If not authenticated

**Calls:**
- `AgentSpawner.stream()`
- `SessionRepository.get_or_create()`

**Called by:**
- `src/api/routers/chat.py:stream_message`
- `tests/test_chat_service.py:test_stream_chat`

**Tests:**
- `test_chat_service.py::TestChatService::test_stream_chat_success`
- `test_chat_service.py::TestChatService::test_stream_chat_no_session`

**Example:**
```python
service = ChatService()
async for chunk in service.stream_chat(agent_id, "Hello"):
    print(chunk, end="")
```
```

### Architecture Template

**File:** `docs/architecture/{system_name}.md`

```markdown
# {System Name} Architecture

## Overview

{LLM-generated summary based on call graph and coupling analysis}

## Component Diagram

```
┌─────────────────┐     ┌─────────────────┐
│   ChatRouter    │────>│   ChatService   │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  AgentSpawner   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  OpenAI Runner  │
                        └─────────────────┘
```

## Data Flow

1. Request arrives at `ChatRouter.stream_message()`
2. Router calls `ChatService.stream_chat()`
3. Service retrieves agent via `AgentRepository`
4. Service creates `AgentSpawner` instance
5. Spawner executes via `Runner.run_streamed()`
6. Response streams back through layers

## Key Files

| File | Role | Coupling Score |
|------|------|----------------|
| chat_service.py | Orchestration | 0.85 |
| agent_spawner.py | Execution | 0.72 |
| chat.py (router) | HTTP interface | 0.65 |

## Design Decisions

### Why AgentSpawner wraps Runner

{LLM analysis based on code structure}

### Session Management Strategy

{LLM analysis based on session-related code}
```

---

## Implementation Notes

### Data Already Available in Index

```python
index = {
    "files": [...],              # File inventory with categories
    "api_endpoints": [...],      # All routes with methods, auth, schemas
    "schemas": [...],            # Pydantic models
    "call_graph": {...},         # Function → calls mapping
    "symbol_index": {...},       # All symbols by name
    "summaries": {"cache": {}},  # LLM-generated summaries
    "import_analysis": {...},    # Import relationships
    "test_coverage": {...},      # Test file mapping
}
```

### Queries to Use

| Documentation Need | Index Query |
|-------------------|-------------|
| What does function do? | `summaries.cache[hash]` or `--summary-for` |
| What calls this? | `--cg-callers SYMBOL` |
| What does this call? | `--cg-query SYMBOL` |
| What tests cover this? | `--tests-for SYMBOL` |
| Related files? | `--coupled-with FILE` |
| Endpoints using schema? | `--schema NAME` |
| Impact of changes? | `--impact FILE` |

### LLM Enhancement (Optional)

For richer documentation, use LLM to:

1. **Synthesize module summaries** from individual function summaries
2. **Generate usage examples** from test code
3. **Explain architecture** from call graph patterns
4. **Describe design decisions** from code structure

```python
def generate_module_summary(module_files, summaries):
    prompt = f"""
    Summarize this module based on its functions:

    Functions:
    {summaries}

    Write 2-3 sentences explaining what this module does and its role in the system.
    """
    return llm.generate(prompt)
```

---

## Suggested Implementation Order

### Phase 1: Core Generation (MVP)
1. `--doc-for SYMBOL` - Single symbol documentation
2. `--generate-docs --doc-layers api` - API reference only
3. Basic markdown templates

### Phase 2: Full Generation
4. `--generate-docs --doc-layers modules` - Module READMEs
5. `--generate-docs --doc-layers reference` - Full reference docs
6. `--doc-diff` - Freshness checking

### Phase 3: Advanced
7. `--generate-docs --doc-layers architecture` - Architecture docs (needs LLM)
8. `--doc-template` - Custom templates
9. `--watch` - Auto-regeneration
10. HTML/RST output formats

---

## Example Workflow

```bash
# Initial setup: Generate full index with summaries
codebase-index . --config config.yaml \
  --build-embeddings \
  --generate-summaries --summary-provider openrouter --summary-model mistralai/ministral-8b-2512 \
  -o index.json

# Generate all documentation
codebase-index --load index.json --generate-docs --output-dir docs/generated/

# Check what's stale after making changes
codebase-index --load index.json --doc-diff --doc-dir docs/generated/

# Regenerate only API docs
codebase-index --load index.json --generate-docs --doc-layers api --output-dir docs/generated/

# Get detailed docs for a specific class
codebase-index --load index.json --doc-for "AgentFactory"
```

---

## Success Criteria

1. **Accuracy:** Generated docs match actual code behavior
2. **Completeness:** All public APIs documented
3. **Freshness:** `--doc-diff` correctly identifies stale docs
4. **Usability:** Output is readable without manual editing
5. **Performance:** Full doc generation < 30 seconds for 500-file codebase

---

## Questions for Engineer

1. Should `--generate-docs` require `--generate-summaries` first, or generate on-the-fly?
2. Preferred template engine: Jinja2, Mako, or simple string formatting?
3. Should we track doc freshness in the index itself (add `docs` section)?
4. Priority: Which layer is most valuable to implement first?
