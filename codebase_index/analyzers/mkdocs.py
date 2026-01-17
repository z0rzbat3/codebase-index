"""
MkDocs configuration generator for codebase_index.

Generates mkdocs.yml from existing documentation structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_mkdocs_config(
    docs_dir: Path,
    site_name: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Generate mkdocs.yml configuration from documentation directory.

    Args:
        docs_dir: Directory containing generated documentation.
        site_name: Name for the documentation site.
        output_path: Where to write mkdocs.yml (default: current directory).

    Returns:
        Path to the generated mkdocs.yml file.
    """
    docs_dir = Path(docs_dir)
    output_path = output_path or Path("mkdocs.yml")

    # Infer site name from directory or parent
    if not site_name:
        site_name = _infer_site_name(docs_dir)

    # Build navigation structure
    nav = _build_nav(docs_dir)

    # Generate config
    config = _generate_config(site_name, docs_dir, nav)

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config)

    return output_path


def _infer_site_name(docs_dir: Path) -> str:
    """Infer site name from directory structure."""
    # Try parent directory name
    parent = docs_dir.parent.name
    if parent and parent not in (".", "docs", "documentation"):
        return f"{parent.replace('_', ' ').replace('-', ' ').title()} Documentation"

    # Try grandparent
    grandparent = docs_dir.parent.parent.name
    if grandparent and grandparent != ".":
        return f"{grandparent.replace('_', ' ').replace('-', ' ').title()} Documentation"

    return "Project Documentation"


def _build_nav(docs_dir: Path) -> list[dict[str, Any]]:
    """Build navigation structure from directory contents."""
    nav = []

    # Known section order and titles
    sections = [
        ("api", "API Reference"),
        ("modules", "Modules"),
        ("reference", "Reference"),
        ("architecture", "Architecture"),
    ]

    for dir_name, title in sections:
        section_dir = docs_dir / dir_name
        if section_dir.exists() and section_dir.is_dir():
            section_nav = _build_section_nav(section_dir, dir_name)
            if section_nav:
                nav.append({title: section_nav})

    # Check for README at root
    root_readme = docs_dir / "README.md"
    if root_readme.exists():
        nav.insert(0, {"Home": "README.md"})

    # Check for any other markdown files at root
    for md_file in sorted(docs_dir.glob("*.md")):
        if md_file.name.lower() != "readme.md":
            title = md_file.stem.replace("_", " ").replace("-", " ").title()
            nav.append({title: md_file.name})

    return nav


def _build_section_nav(section_dir: Path, section_name: str) -> list[str | dict[str, str]]:
    """Build navigation for a section directory."""
    nav = []

    # Add README/index first if exists
    for index_name in ("README.md", "index.md"):
        index_file = section_dir / index_name
        if index_file.exists():
            nav.append(f"{section_name}/{index_name}")
            break

    # Add other markdown files
    for md_file in sorted(section_dir.glob("*.md")):
        if md_file.name.lower() not in ("readme.md", "index.md"):
            nav.append(f"{section_name}/{md_file.name}")

    return nav


def _generate_config(site_name: str, docs_dir: Path, nav: list[dict[str, Any]]) -> str:
    """Generate mkdocs.yml content."""
    lines = [
        f"site_name: \"{site_name}\"",
        f"docs_dir: {docs_dir}",
        "",
        "theme:",
        "  name: material",
        "  features:",
        "    - navigation.sections",
        "    - navigation.expand",
        "    - search.highlight",
        "    - content.code.copy",
        "  palette:",
        "    - scheme: default",
        "      primary: indigo",
        "      accent: indigo",
        "      toggle:",
        "        icon: material/brightness-7",
        "        name: Switch to dark mode",
        "    - scheme: slate",
        "      primary: indigo",
        "      accent: indigo",
        "      toggle:",
        "        icon: material/brightness-4",
        "        name: Switch to light mode",
        "",
        "plugins:",
        "  - search",
        "",
        "markdown_extensions:",
        "  - pymdownx.highlight:",
        "      anchor_linenums: true",
        "  - pymdownx.superfences",
        "  - pymdownx.tabbed:",
        "      alternate_style: true",
        "  - admonition",
        "  - toc:",
        "      permalink: true",
        "",
    ]

    # Add navigation
    if nav:
        lines.append("nav:")
        for item in nav:
            _append_nav_item(lines, item, indent=2)

    return "\n".join(lines)


def _append_nav_item(lines: list[str], item: dict | str, indent: int = 2) -> None:
    """Append a navigation item to lines."""
    prefix = " " * indent

    if isinstance(item, str):
        lines.append(f"{prefix}- {item}")
    elif isinstance(item, dict):
        for title, value in item.items():
            if isinstance(value, str):
                lines.append(f"{prefix}- \"{title}\": {value}")
            elif isinstance(value, list):
                lines.append(f"{prefix}- \"{title}\":")
                for sub_item in value:
                    _append_nav_item(lines, sub_item, indent + 4)
