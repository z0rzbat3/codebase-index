# Codebase-Index Documentation

> Auto-generated using `codebase-index` on itself

## Documentation Files

| File | Description | Lines |
|------|-------------|-------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | High-level architecture, diagrams, module overview | 152 |
| [API.md](API.md) | API documentation with all classes and methods | 1,370 |
| [FULL_REFERENCE.md](FULL_REFERENCE.md) | Complete reference with method signatures and call graph | 3,213 |

## Quick Links

### Architecture
- [Module Dependency Graph](ARCHITECTURE.md#architecture)
- [Data Flow](ARCHITECTURE.md#data-flow)
- [Output Schema](ARCHITECTURE.md#output-schema)

### API Reference
- [Core Classes](FULL_REFERENCE.md#core-classes)
- [Parsers](FULL_REFERENCE.md#parsers)
- [Scanners](FULL_REFERENCE.md#scanners)
- [Analyzers](FULL_REFERENCE.md#analyzers)
- [Call Graph](FULL_REFERENCE.md#call-graph)

## Regenerating Documentation

```bash
# Generate fresh index
codebase-index . --exclude-dirs .git __pycache__ outputs -o /tmp/self_index.json

# The documentation was generated using Python scripts that parse this index
# See the main README for usage instructions
```

## Coverage

| Metric | Count |
|--------|-------|
| Files Documented | 37 |
| Classes | 46 |
| Methods | 244 |
| Functions | 41 |
| Documentation Coverage | 97% |
