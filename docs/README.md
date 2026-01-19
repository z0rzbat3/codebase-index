# codebase-index Documentation

> Auto-generated using mirror strategy v2.0

## Documentation Structure

```
docs/
├── README.md           ← You are here
├── core/               ← Main modules (cli, scanner, config, etc.)
│   ├── README.md
│   ├── call_graph.md
│   ├── cli.md
│   ├── config.md
│   ├── incremental.md
│   ├── scanner.md
│   └── utils.md
├── parsers/            ← Language-specific parsers
│   ├── README.md
│   ├── base.md
│   ├── docker.md
│   ├── python.md
│   ├── sql.md
│   └── typescript.md
├── analyzers/          ← Analysis tools
│   ├── README.md
│   ├── auth.md
│   ├── centrality.md
│   ├── complexity.md
│   ├── coverage.md
│   ├── doc_generator.md
│   ├── execution_flow.md
│   ├── impact.md
│   ├── imports.md
│   ├── orphans.md
│   ├── semantic.md
│   ├── staleness.md
│   └── test_mapper.md
└── scanners/           ← Domain-specific scanners
    ├── README.md
    ├── alembic.md
    ├── dependencies.md
    ├── env.md
    ├── http_calls.md
    ├── middleware.md
    ├── routes.md
    ├── todo.md
    └── websocket.md
```

## Quick Links

### Core

| Module | Description |
|--------|-------------|
| [cli](core/cli.md) | Command-line interface |
| [scanner](core/scanner.md) | Main orchestrator |
| [config](core/config.md) | Configuration system |
| [call_graph](core/call_graph.md) | Call graph queries |
| [incremental](core/incremental.md) | Incremental updates |
| [utils](core/utils.md) | Utility functions |

### Parsers

| Parser | Languages | Approach |
|--------|-----------|----------|
| [PythonParser](parsers/python.md) | Python | AST |
| [TypeScriptParser](parsers/typescript.md) | TS/JS/React | Regex |
| [SQLParser](parsers/sql.md) | SQL | Regex |
| [DockerParser](parsers/docker.md) | Docker Compose | YAML |

### Analyzers

| Analyzer | Purpose |
|----------|---------|
| [ImpactAnalyzer](analyzers/impact.md) | Change impact radius |
| [SemanticSearcher](analyzers/semantic.md) | Code search by concept |
| [TestMapper](analyzers/test_mapper.md) | Symbol to test mapping |
| [ComplexityAnalyzer](analyzers/complexity.md) | Code complexity |
| [AuthScanner](analyzers/auth.md) | Auth requirements |
| [StalenessChecker](analyzers/staleness.md) | Index freshness |

### Scanners

| Scanner | Detects |
|---------|---------|
| [DependenciesScanner](scanners/dependencies.md) | Package deps |
| [EnvScanner](scanners/env.md) | Environment vars |
| [TodoScanner](scanners/todo.md) | TODO comments |
| [HttpCallsScanner](scanners/http_calls.md) | External APIs |
| [RoutePrefixScanner](scanners/routes.md) | API prefixes |

## Regenerating Documentation

```bash
# Full regeneration
/generate-docs

# Incremental (changed files only)
/generate-docs --incremental

# Review for accuracy
/generate-docs --review

# Review and auto-fix
/generate-docs --review --fix
```

## Coverage

| Category | Files | Documented |
|----------|-------|------------|
| Core | 6 | 6 |
| Parsers | 5 | 5 |
| Analyzers | 12 | 12 |
| Scanners | 8 | 8 |
| **Total** | **31** | **31** |

---
*Generated with mirror strategy v2.0*
