"""
Template system for documentation generation.

Provides Jinja2-based templating with default templates and
support for custom user templates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

# Check for optional Jinja2
try:
    from jinja2 import Environment, FileSystemLoader, BaseLoader, TemplateNotFound
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore
    BaseLoader = None  # type: ignore
    TemplateNotFound = Exception  # type: ignore


# Default templates as strings
DEFAULT_TEMPLATES = {
    # API Reference templates
    "api/router.md.j2": """# {{ router_name | title }} API

{% if base_path %}**Base path:** `{{ base_path }}`{% endif %}

{% if source_file %}**Source:** `{{ source_file }}`{% endif %}

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
{% for ep in endpoints -%}
| `{{ ep.method }}` | `{{ ep.path }}` | {{ ep.description or '-' }} |
{% endfor %}

{% for ep in endpoints %}
### {{ ep.method }} {{ ep.path }}

{% if ep.function %}**Function:** `{{ ep.function }}`{% endif %}
{% if ep.location %}**Location:** `{{ ep.location }}`{% endif %}

**Authentication:** {{ 'Required' if ep.auth_required else 'Not required' }}

{% if ep.path_params %}
**Path Parameters:**

| Name | Type | Description |
|------|------|-------------|
{% for p in ep.path_params -%}
| `{{ p.name }}` | `{{ p.type or 'string' }}` | - |
{% endfor %}
{% endif %}

{% if ep.query_params %}
**Query Parameters:**

| Name | Type | Required | Default |
|------|------|----------|---------|
{% for p in ep.query_params -%}
| `{{ p.name }}` | `{{ p.type or 'string' }}` | {{ 'Yes' if p.required else 'No' }} | {{ p.default or '-' }} |
{% endfor %}
{% endif %}

{% if ep.request_schema %}
**Request Body:** Schema: `{{ ep.request_schema }}`
{% endif %}

{% if ep.response_schema %}
**Response:** Schema: `{{ ep.response_schema }}`
{% endif %}

**Example:**

```bash
{{ ep.curl_example }}
```

---

{% endfor %}
""",

    "api/index.md.j2": """# API Reference

Auto-generated API documentation from codebase-index.

**Total Routers:** {{ routers | length }}
**Total Endpoints:** {{ total_endpoints }}

## Routers

| Router | Endpoints | File |
|--------|-----------|------|
{% for router in routers -%}
| [{{ router.name }}]({{ router.filename }}.md) | {{ router.endpoint_count }} | `{{ router.source }}` |
{% endfor %}
""",

    # Module templates
    "modules/module.md.j2": """# {{ module_name }}

**Path:** `{{ module_path }}`

{% if overview %}
## Overview

{{ overview }}
{% endif %}

## Files

| File | Category | Lines | Purpose |
|------|----------|-------|---------|
{% for f in files -%}
| `{{ f.name }}` | {{ f.category }} | {{ f.lines }} | {{ f.purpose or '-' }} |
{% endfor %}

{% if classes %}
## Classes

{% for cls in classes %}
### {{ cls.name }}

{{ cls.summary or cls.docstring or '' }}

{% if cls.methods %}
**Methods:**
{% for m in cls.methods -%}
- `{{ m.name }}()` - {{ m.summary or 'No description' }}
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}

{% if functions %}
## Functions

| Function | Description |
|----------|-------------|
{% for func in functions -%}
| `{{ func.name }}()` | {{ func.summary or '-' }} |
{% endfor %}
{% endif %}

{% if internal_deps or external_deps %}
## Dependencies

{% if internal_deps %}
**Internal:**
{% for dep in internal_deps -%}
- `{{ dep }}`
{% endfor %}
{% endif %}

{% if external_deps %}
**External:**
{% for dep in external_deps -%}
- `{{ dep }}`
{% endfor %}
{% endif %}
{% endif %}
""",

    "modules/index.md.j2": """# Modules Reference

Auto-generated module documentation from codebase-index.

**Total Modules:** {{ modules | length }}
**Total Files:** {{ total_files }}

## Modules

| Module | Files | Description |
|--------|-------|-------------|
{% for module in modules -%}
| [{{ module.path }}]({{ module.filename }}.md) | {{ module.file_count }} | {{ module.description or '-' }} |
{% endfor %}
""",

    # Reference templates
    "reference/file.md.j2": """# {{ module_name }} Reference

**File:** `{{ file_path }}`

{% if classes or functions %}
## Contents

{% if classes %}
### Classes
{% for cls in classes -%}
- [{{ cls.name }}](#{{ cls.name | lower }})
{% endfor %}
{% endif %}

{% if functions %}
### Functions
{% for func in functions -%}
- [{{ func.name }}](#{{ func.name | lower }})
{% endfor %}
{% endif %}

---
{% endif %}

{% if classes %}
## Classes

{% for cls in classes %}
### {{ cls.name }}

**Location:** `{{ file_path }}:{{ cls.line }}`
{% if cls.bases %}**Inherits:** {{ cls.bases | map('tojinja', '`{}`') | join(', ') }}{% endif %}

{{ cls.summary or cls.docstring or '' }}

{% if cls.methods %}
#### Methods

{% for method in cls.methods %}
##### `{{ method.name }}()`

{% if method.signature %}
```python
{{ method.signature }}
```
{% endif %}

{{ method.summary or method.docstring or '' }}

{% if method.params %}
**Parameters:**
{% for p in method.params -%}
- `{{ p.name }}`{% if p.type %}: `{{ p.type }}`{% endif %}
{% endfor %}
{% endif %}

{% if method.return_type %}**Returns:** `{{ method.return_type }}`{% endif %}

{% endfor %}
{% endif %}

{% if cls.callers %}
#### Used By
{% for caller in cls.callers -%}
- `{{ caller.name }}` in `{{ caller.file }}`
{% endfor %}
{% endif %}

---

{% endfor %}
{% endif %}

{% if functions %}
## Functions

{% for func in functions %}
### {{ func.name }}

**Location:** `{{ file_path }}:{{ func.line }}`

{% if func.signature %}
```python
{{ func.signature }}
```
{% endif %}

{{ func.summary or func.docstring or '' }}

{% if func.params %}
**Parameters:**

| Name | Type | Default |
|------|------|---------|
{% for p in func.params -%}
| `{{ p.name }}` | `{{ p.type or '-' }}` | {{ '...' if p.has_default else '-' }} |
{% endfor %}
{% endif %}

{% if func.return_type %}**Returns:** `{{ func.return_type }}`{% endif %}

{% if func.calls %}
**Calls:**
{% for call in func.calls -%}
- `{{ call }}`
{% endfor %}
{% endif %}

{% if func.callers %}
**Called By:**
{% for caller in func.callers -%}
- `{{ caller.name }}` in `{{ caller.file }}`
{% endfor %}
{% endif %}

{% if func.tests %}
**Tests:**
{% for test in func.tests -%}
- `{{ test.file }}`
{% endfor %}
{% endif %}

---

{% endfor %}
{% endif %}
""",

    "reference/index.md.j2": """# Function Reference

Auto-generated function and class reference from codebase-index.

**Total Files:** {{ files | length }}
**Total Classes:** {{ total_classes }}
**Total Functions:** {{ total_functions }}

## Files

| File | Classes | Functions |
|------|---------|-----------|
{% for file in files -%}
| [{{ file.path }}]({{ file.filename }}.md) | {{ file.class_count }} | {{ file.function_count }} |
{% endfor %}
""",

    # Architecture templates
    "architecture/overview.md.j2": """# Architecture Overview

## Project Summary

- **Total Files:** {{ summary.total_files }}
- **Total Lines:** {{ summary.total_lines | default(0) | int | format_number }}
- **Languages:** {{ summary.languages | join(', ') }}

## Components

| Component | Files | Classes | Functions | Coupling |
|-----------|-------|---------|-----------|----------|
{% for comp in components -%}
| `{{ comp.name }}` | {{ comp.file_count }} | {{ comp.class_count }} | {{ comp.function_count }} | {{ comp.coupling or '-' }} |
{% endfor %}

## Component Diagram

```
{{ diagram }}
```

## Architectural Patterns

{% for pattern in patterns -%}
- **{{ pattern.name }}:** {{ pattern.description }}
{% endfor %}
""",

    "architecture/component.md.j2": """# {{ component.name | title }} Component

## Overview

- **Files:** {{ component.files | length }}
- **Classes:** {{ component.classes | length }}
- **Functions:** {{ component.functions | length }}
{% if component.coupling_score %}- **Coupling Score:** {{ component.coupling_score | round(2) }}{% endif %}

{% if component.classes %}
## Key Classes

{% for cls in component.classes[:10] %}
### {{ cls.name }}

{{ cls.summary or cls.docstring or '' }}

**Location:** `{{ cls.file }}:{{ cls.line }}`

{% endfor %}
{% endif %}

{% if component.functions %}
## Key Functions

| Function | File | Description |
|----------|------|-------------|
{% for func in component.functions[:15] -%}
| `{{ func.name }}` | `{{ func.file_name }}` | {{ func.summary or '-' }} |
{% endfor %}
{% endif %}

## Files

| File | Category | Lines |
|------|----------|-------|
{% for f in component.files[:20] -%}
| `{{ f.path }}` | {{ f.category or '-' }} | {{ f.lines }} |
{% endfor %}
{% if component.files | length > 20 %}
| ... | ... | *{{ component.files | length - 20 }} more* |
{% endif %}
""",

    "architecture/data_flow.md.j2": """# Data Flow

This document describes how data flows through the system based on call graph analysis.

## Most Called Functions

These functions are central to the data flow:

| Function | Times Called |
|----------|--------------|
{% for func in top_functions -%}
| `{{ func.name }}` | {{ func.count }} |
{% endfor %}

## Call Chains

Key execution paths through the system:

{% for chain in call_chains %}
### Chain {{ loop.index }}

```
{{ chain | join(' → ') }}
```

{% endfor %}
""",

    "architecture/index.md.j2": """# Architecture Documentation

Auto-generated architecture documentation from codebase-index.

## Documents

- [Overview](overview.md) - High-level architecture overview
- [Data Flow](data_flow.md) - How data flows through the system

## Component Documentation

{% for comp in components -%}
- [{{ comp.name }}]({{ comp.filename }}.md) - {{ comp.file_count }} files
{% endfor %}
""",
}


class DictLoader(BaseLoader if HAS_JINJA2 else object):
    """Load templates from a dictionary."""

    def __init__(self, templates: dict[str, str]) -> None:
        self.templates = templates

    def get_source(self, environment: Any, template: str) -> tuple[str, str | None, Any]:
        if template in self.templates:
            source = self.templates[template]
            return source, None, lambda: True
        raise TemplateNotFound(template)


class TemplateRenderer:
    """
    Render documentation templates.

    Supports both default templates and custom user templates.
    """

    def __init__(self, custom_template_dir: Path | None = None) -> None:
        """
        Initialize the template renderer.

        Args:
            custom_template_dir: Optional directory with custom templates.
        """
        if not HAS_JINJA2:
            raise ImportError(
                "Jinja2 is required for custom templates. "
                "Install with: pip install jinja2"
            )

        self.custom_dir = custom_template_dir

        # Create loaders
        loaders = []
        if custom_template_dir and custom_template_dir.exists():
            loaders.append(FileSystemLoader(str(custom_template_dir)))
        loaders.append(DictLoader(DEFAULT_TEMPLATES))

        # Create environment with first available loader
        if loaders:
            from jinja2 import ChoiceLoader
            self.env = Environment(loader=ChoiceLoader(loaders))
        else:
            self.env = Environment(loader=DictLoader(DEFAULT_TEMPLATES))

        # Add custom filters
        self.env.filters["format_number"] = lambda x: f"{int(x):,}"

    def render(self, template_name: str, **context: Any) -> str:
        """
        Render a template with context.

        Args:
            template_name: Name of the template (e.g., "api/router.md.j2")
            **context: Template context variables.

        Returns:
            Rendered template string.
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def has_template(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False


def check_jinja2_available() -> bool:
    """Check if Jinja2 is available."""
    return HAS_JINJA2


def create_template_dir(output_dir: Path) -> None:
    """
    Create a template directory with default templates.

    Useful for users who want to customize templates.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for template_name, content in DEFAULT_TEMPLATES.items():
        template_path = output_dir / template_name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(content)
