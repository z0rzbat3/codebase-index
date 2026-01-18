"""
Consolidated documentation generator.

Generates a simplified, elegant documentation structure:
- index.md          - Dashboard with stats and quick links
- architecture.md   - Patterns, data flow, component diagram
- api-endpoints.md  - All REST endpoints in one searchable page
- health.md         - Dependencies, quality metrics, tech debt
- code/             - One page per top-level module with all symbols inline
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class ModuleLinker:
    """
    Build cross-links between symbols within consolidated docs.

    All symbols live in code/{module}.md with anchors.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        self.index_data = index_data
        self.symbol_index = index_data.get("symbol_index", {})
        self._symbol_map: dict[str, dict[str, str]] = {}
        self._build_symbol_map()

    def _get_top_level_module(self, file_path: str) -> str:
        """Get the top-level module name from a file path."""
        parts = Path(file_path).parts
        if not parts:
            return "root"

        # Single file in root directory goes to "root" module
        if len(parts) == 1:
            return "root"

        # Skip common prefixes like 'src'
        first = parts[0]
        if first in ("src", "lib", "app") and len(parts) > 1:
            # Check if next part is a file (like __init__.py) vs a directory
            next_part = parts[1]
            # If it's a file (has extension), treat as "root"
            if "." in next_part:
                return "root"
            return next_part
        return first

    def _build_symbol_map(self) -> None:
        """Build the symbol location map."""
        # Map functions
        for func in self.symbol_index.get("functions", []):
            name = func.get("name", "")
            file_path = func.get("file", "")
            if name and file_path:
                module = self._get_top_level_module(file_path)
                anchor = self._make_anchor(name)
                self._symbol_map[name] = {
                    "file": file_path,
                    "module": module,
                    "doc_file": f"code/{module}.md",
                    "anchor": anchor,
                    "type": "function",
                }

        # Map classes
        for cls in self.symbol_index.get("classes", []):
            name = cls.get("name", "")
            file_path = cls.get("file", "")
            if name and file_path:
                module = self._get_top_level_module(file_path)
                anchor = self._make_anchor(name)
                self._symbol_map[name] = {
                    "file": file_path,
                    "module": module,
                    "doc_file": f"code/{module}.md",
                    "anchor": anchor,
                    "type": "class",
                }

        # Map methods
        for method in self.symbol_index.get("methods", []):
            name = method.get("name", "")
            class_name = method.get("class", "")
            file_path = method.get("file", "")
            if name and file_path:
                module = self._get_top_level_module(file_path)
                anchor = self._make_anchor(name)
                self._symbol_map[name] = {
                    "file": file_path,
                    "module": module,
                    "doc_file": f"code/{module}.md",
                    "anchor": anchor,
                    "type": "method",
                }
                if class_name:
                    full_name = f"{class_name}.{name}"
                    self._symbol_map[full_name] = {
                        "file": file_path,
                        "module": module,
                        "doc_file": f"code/{module}.md",
                        "anchor": self._make_anchor(full_name),
                        "type": "method",
                    }

    def _make_anchor(self, name: str) -> str:
        """Create a markdown anchor ID."""
        return name.lower().replace(".", "-").replace("_", "-")

    def get_symbol_info(self, name: str) -> dict[str, str] | None:
        """Get documentation info for a symbol."""
        if name in self._symbol_map:
            return self._symbol_map[name]

        # Try case-insensitive
        name_lower = name.lower()
        for sym_name, info in self._symbol_map.items():
            if sym_name.lower() == name_lower:
                return info

        # Try base name
        base_name = name.split(".")[-1] if "." in name else name
        if base_name != name and base_name in self._symbol_map:
            return self._symbol_map[base_name]

        return None

    def link_symbol(self, name: str, from_file: str = "") -> str:
        """Generate a markdown link for a symbol."""
        info = self.get_symbol_info(name)
        if not info:
            return f"`{name}`"

        doc_file = info["doc_file"]
        anchor = info["anchor"]

        # Calculate relative path
        if from_file.startswith("code/"):
            # From another code file
            current_module = Path(from_file).stem
            target_module = info["module"]
            if current_module == target_module:
                return f"[`{name}`](#{anchor})"
            else:
                return f"[`{name}`]({target_module}.md#{anchor})"
        else:
            # From index/architecture/etc
            return f"[`{name}`]({doc_file}#{anchor})"

    def make_anchor_tag(self, name: str) -> str:
        """Generate an HTML anchor tag."""
        anchor = self._make_anchor(name)
        return f'<a id="{anchor}"></a>'


class ConsolidatedCodeGenerator:
    """
    Generate consolidated code documentation.

    Creates one page per top-level module containing all
    classes, functions, and methods with inline documentation.
    """

    def __init__(self, index_data: dict[str, Any], root: Path | None = None) -> None:
        self.index_data = index_data
        self.root = root
        self.symbol_index = index_data.get("symbol_index", {})
        self.call_graph = index_data.get("call_graph", {})
        self.files = index_data.get("files", [])
        self.linker = ModuleLinker(index_data)

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate consolidated code documentation."""
        code_dir = output_dir / "code"
        code_dir.mkdir(parents=True, exist_ok=True)

        # Group files by top-level module
        modules = self._group_by_module()

        generated_files = []
        total_symbols = 0

        for module_name, module_data in sorted(modules.items()):
            filepath = code_dir / f"{module_name}.md"
            content = self._generate_module_page(module_name, module_data)

            symbols_count = sum(
                len(f.get("classes", [])) + len(f.get("functions", []))
                for f in module_data["files"]
            )
            total_symbols += symbols_count

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(str(filepath))

        # Generate code index
        index_path = code_dir / "README.md"
        index_content = self._generate_code_index(modules)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        generated_files.append(str(index_path))

        return {
            "layer": "code",
            "files": generated_files,
            "modules": len(modules),
            "symbols": total_symbols,
        }

    def _get_top_level_module(self, file_path: str) -> str:
        """Get the top-level module name from a file path."""
        parts = Path(file_path).parts
        if not parts:
            return "root"

        # Single file in root directory goes to "root" module
        if len(parts) == 1:
            return "root"

        # Skip common prefixes like 'src'
        first = parts[0]
        if first in ("src", "lib", "app") and len(parts) > 1:
            # Check if next part is a file (like __init__.py) vs a directory
            next_part = parts[1]
            # If it's a file (has extension), treat as "root"
            if "." in next_part:
                return "root"
            return next_part
        return first

    def _group_by_module(self) -> dict[str, dict[str, Any]]:
        """Group all files and symbols by top-level module."""
        modules: dict[str, dict[str, Any]] = {}

        # Group files
        for file_info in self.files:
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            module = self._get_top_level_module(file_path)
            if module not in modules:
                modules[module] = {
                    "files": [],
                    "classes": [],
                    "functions": [],
                    "methods": [],
                    "total_lines": 0,
                }

            modules[module]["files"].append(file_info)
            modules[module]["total_lines"] += file_info.get("lines", 0)

        # Group classes
        for cls in self.symbol_index.get("classes", []):
            file_path = cls.get("file", "")
            if not file_path:
                continue
            module = self._get_top_level_module(file_path)
            if module in modules:
                modules[module]["classes"].append(cls)

        # Group functions
        for func in self.symbol_index.get("functions", []):
            file_path = func.get("file", "")
            if not file_path:
                continue
            module = self._get_top_level_module(file_path)
            if module in modules:
                modules[module]["functions"].append(func)

        # Group methods
        for method in self.symbol_index.get("methods", []):
            file_path = method.get("file", "")
            if not file_path:
                continue
            module = self._get_top_level_module(file_path)
            if module in modules:
                modules[module]["methods"].append(method)

        return modules

    def _generate_module_page(self, module_name: str, module_data: dict[str, Any]) -> str:
        """Generate a consolidated module page."""
        lines = []

        files = module_data["files"]
        classes = module_data["classes"]
        functions = module_data["functions"]
        methods = module_data["methods"]
        total_lines = module_data["total_lines"]

        # Header
        lines.append(f"# {module_name}")
        lines.append("")

        # Stats
        lines.append(f"**{len(files)} files** | **{total_lines:,} lines** | "
                     f"**{len(classes)} classes** | **{len(functions)} functions**")
        lines.append("")

        # Table of contents
        lines.append("## Contents")
        lines.append("")
        lines.append("- [Files](#files)")
        if classes:
            lines.append("- [Classes](#classes)")
        if functions:
            lines.append("- [Functions](#functions)")
        lines.append("")

        # Files table
        lines.append("---")
        lines.append("")
        lines.append("## Files")
        lines.append("")
        lines.append("| File | Lines | Purpose |")
        lines.append("|------|-------|---------|")

        for f in sorted(files, key=lambda x: x.get("path", "")):
            path = f.get("path", "")
            file_lines = f.get("lines", 0)
            purpose = f.get("summary", "")
            if not purpose:
                # Fall back to first function's docstring
                for func in functions:
                    if func.get("file") == path:
                        purpose = func.get("docstring") or ""
                        if purpose:
                            purpose = purpose[:80]
                        break
            purpose = (purpose or "").replace("|", "\\|").replace("\n", " ")[:100]
            if len(purpose) == 100:
                purpose += "..."

            filename = Path(path).name
            lines.append(f"| `{filename}` | {file_lines} | {purpose} |")

        lines.append("")

        # Classes section
        if classes:
            lines.append("---")
            lines.append("")
            lines.append("## Classes")
            lines.append("")

            # Detect duplicate class names for disambiguation
            from collections import Counter
            name_counts = Counter(c.get("name", "") for c in classes)
            duplicates = {n for n, count in name_counts.items() if count > 1}

            for cls in sorted(classes, key=lambda x: x.get("name", "")):
                needs_file_qualifier = cls.get("name", "") in duplicates
                lines.extend(self._format_class(cls, methods, module_name, needs_file_qualifier))
                lines.append("")

        # Functions section
        if functions:
            lines.append("---")
            lines.append("")
            lines.append("## Functions")
            lines.append("")

            for func in sorted(functions, key=lambda x: x.get("name", "")):
                lines.extend(self._format_function(func, module_name))
                lines.append("")

        return "\n".join(lines)

    def _format_class(
        self, cls: dict[str, Any], all_methods: list[dict[str, Any]], module_name: str,
        needs_file_qualifier: bool = False
    ) -> list[str]:
        """Format a class with its methods."""
        lines = []

        name = cls.get("name", "")
        file_path = cls.get("file", "")
        line_num = cls.get("line", 0)
        docstring = cls.get("docstring", "")
        summary = cls.get("summary", "")
        bases = cls.get("bases", [])
        filename = Path(file_path).stem

        # Anchor and header - use file-qualified anchor if duplicate name
        if needs_file_qualifier:
            anchor_name = f"{filename}-{name}"
            lines.append(self.linker.make_anchor_tag(anchor_name))
            lines.append(self.linker.make_anchor_tag(name))  # Also add simple anchor for backwards compat
            lines.append(f"### {name} ({filename})")
        else:
            lines.append(self.linker.make_anchor_tag(name))
            lines.append(f"### {name}")
        lines.append("")

        # Location
        filename = Path(file_path).name
        lines.append(f"`{filename}:{line_num}`")

        # Inheritance
        if bases:
            linked_bases = []
            for b in bases:
                info = self.linker.get_symbol_info(b)
                if info:
                    linked_bases.append(self.linker.link_symbol(b, f"code/{module_name}.md"))
                else:
                    linked_bases.append(f"`{b}`")
            lines.append(f" \u2190 {', '.join(linked_bases)}")
        lines.append("")

        # Description
        desc = summary or docstring
        if desc:
            lines.append(desc.split("\n")[0])
            lines.append("")

        # Methods
        class_methods = [m for m in all_methods if m.get("class") == name]
        if class_methods:
            lines.append("**Methods:**")
            lines.append("")
            for method in class_methods:
                m_name = method.get("name", "")
                m_summary = method.get("summary", method.get("docstring", ""))
                m_sig = method.get("signature", {})
                params = m_sig.get("params", [])
                param_str = ", ".join(p.get("name", "") for p in params if p.get("name") != "self")

                # Anchor for method
                lines.append(self.linker.make_anchor_tag(f"{name}.{m_name}"))
                lines.append(self.linker.make_anchor_tag(m_name))

                desc_short = m_summary.split("\n")[0] if m_summary else ""
                if len(desc_short) > 80:
                    desc_short = desc_short[:77] + "..."
                lines.append(f"- `{m_name}({param_str})` - {desc_short}")
            lines.append("")

        # Callers
        callers = self._get_callers(name)
        if callers:
            lines.append("**Used by:** " + ", ".join(
                self.linker.link_symbol(c, f"code/{module_name}.md")
                for c in callers[:5]
            ))
            lines.append("")

        return lines

    def _format_function(self, func: dict[str, Any], module_name: str) -> list[str]:
        """Format a function."""
        lines = []

        name = func.get("name", "")
        file_path = func.get("file", "")
        line_num = func.get("line", 0)
        signature = func.get("signature", {})
        docstring = func.get("docstring", "")
        summary = func.get("summary", "")

        # Anchor and header
        lines.append(self.linker.make_anchor_tag(name))
        lines.append(f"### {name}")
        lines.append("")

        # Location
        filename = Path(file_path).name
        lines.append(f"`{filename}:{line_num}`")
        lines.append("")

        # Signature
        params = signature.get("params", [])
        returns = signature.get("returns", "")

        param_parts = []
        for p in params:
            p_name = p.get("name", "")
            p_type = p.get("type", "")
            p_default = p.get("default", "")
            if p_type and p_default:
                param_parts.append(f"{p_name}: {p_type} = {p_default}")
            elif p_type:
                param_parts.append(f"{p_name}: {p_type}")
            elif p_default:
                param_parts.append(f"{p_name} = {p_default}")
            else:
                param_parts.append(p_name)

        sig_str = f"def {name}({', '.join(param_parts)})"
        if returns:
            sig_str += f" -> {returns}"

        lines.append("```python")
        lines.append(sig_str)
        lines.append("```")
        lines.append("")

        # Description
        desc = summary or docstring
        if desc:
            lines.append(desc.split("\n\n")[0])
            lines.append("")

        # Parameters table (if any)
        if params:
            lines.append("| Parameter | Type | Default |")
            lines.append("|-----------|------|---------|")
            for p in params:
                p_name = p.get("name", "")
                p_type = p.get("type", "-")
                p_default = p.get("default", "-")
                lines.append(f"| `{p_name}` | `{p_type}` | {p_default} |")
            lines.append("")

        # Calls and callers
        calls = self._get_calls(name, file_path)
        callers = self._get_callers(name)

        if calls:
            internal_calls = [c for c in calls if self.linker.get_symbol_info(c)]
            if internal_calls:
                lines.append("**Calls:** " + ", ".join(
                    self.linker.link_symbol(c, f"code/{module_name}.md")
                    for c in internal_calls[:5]
                ))
                lines.append("")

        if callers:
            lines.append("**Called by:** " + ", ".join(
                self.linker.link_symbol(c, f"code/{module_name}.md")
                for c in callers[:5]
            ))
            lines.append("")

        return lines

    def _get_callers(self, name: str) -> list[str]:
        """Get functions that call this symbol."""
        callers = []
        base_name = name.split(".")[-1].lower() if "." in name else name.lower()

        for func_key, func_data in self.call_graph.items():
            calls_list = func_data.get("calls", [])
            for call in calls_list:
                call_base = call.split(".")[-1].lower() if "." in call else call.lower()
                if call_base == base_name or call.lower() == name.lower():
                    if ":" in func_key:
                        _, caller_name = func_key.split(":", 1)
                    else:
                        caller_name = func_key
                    if caller_name not in callers:
                        callers.append(caller_name)
                    break

        return callers[:10]

    def _get_calls(self, name: str, file_path: str) -> list[str]:
        """Get functions that this symbol calls."""
        # Build the key format used in call graph
        key = f"{file_path}:{name}"
        if key in self.call_graph:
            return self.call_graph[key].get("calls", [])[:10]

        # Try just the name
        for func_key, func_data in self.call_graph.items():
            if name in func_key:
                return func_data.get("calls", [])[:10]

        return []

    def _generate_code_index(self, modules: dict[str, dict[str, Any]]) -> str:
        """Generate the code index page."""
        lines = []
        lines.append("# Code Reference")
        lines.append("")
        lines.append("Documentation for all modules in the codebase.")
        lines.append("")
        lines.append("| Module | Files | Lines | Classes | Functions |")
        lines.append("|--------|-------|-------|---------|-----------|")

        for name, data in sorted(modules.items()):
            files_count = len(data["files"])
            lines_count = data["total_lines"]
            classes_count = len(data["classes"])
            funcs_count = len(data["functions"])
            lines.append(
                f"| [{name}]({name}.md) | {files_count} | {lines_count:,} | "
                f"{classes_count} | {funcs_count} |"
            )

        lines.append("")
        return "\n".join(lines)


class ConsolidatedAPIGenerator:
    """Generate a single API endpoints page."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        self.index_data = index_data
        self.endpoints = index_data.get("api_endpoints", [])
        self.linker = ModuleLinker(index_data)

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate consolidated API documentation."""
        filepath = output_dir / "api-endpoints.md"
        content = self._generate_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "layer": "api",
            "files": [str(filepath)],
            "endpoints": len(self.endpoints),
        }

    def _generate_content(self) -> str:
        """Generate the API endpoints page."""
        lines = []
        lines.append("# API Endpoints")
        lines.append("")
        lines.append(f"**{len(self.endpoints)} endpoints**")
        lines.append("")

        if not self.endpoints:
            lines.append("*No API endpoints detected.*")
            return "\n".join(lines)

        # Group by router/tag
        by_router: dict[str, list[dict[str, Any]]] = {}
        for ep in self.endpoints:
            router = ep.get("router", ep.get("file", "default"))
            router = Path(router).stem if "/" in router else router
            if router not in by_router:
                by_router[router] = []
            by_router[router].append(ep)

        # TOC
        lines.append("## Contents")
        lines.append("")
        for router in sorted(by_router.keys()):
            count = len(by_router[router])
            lines.append(f"- [{router}](#{router.lower().replace('_', '-')}) ({count})")
        lines.append("")

        # Endpoints by router
        for router in sorted(by_router.keys()):
            endpoints = by_router[router]
            lines.append("---")
            lines.append("")
            lines.append(f"## {router}")
            lines.append("")

            # Table
            lines.append("| Method | Path | Function | Auth |")
            lines.append("|--------|------|----------|------|")

            for ep in sorted(endpoints, key=lambda e: (e.get("method", ""), e.get("path", ""))):
                method = ep.get("method", "GET").upper()
                path = ep.get("full_path", ep.get("path", "/"))
                func = ep.get("function", "")
                auth = "\u2705" if ep.get("auth_required") else ""

                func_link = self.linker.link_symbol(func, "")
                lines.append(f"| `{method}` | `{path}` | {func_link} | {auth} |")

            lines.append("")

        return "\n".join(lines)


class ConsolidatedArchitectureGenerator:
    """Generate a single architecture page."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        self.index_data = index_data
        self.files = index_data.get("files", [])
        self.symbol_index = index_data.get("symbol_index", {})
        self.execution_flow = index_data.get("execution_flow", {})
        self.centrality = index_data.get("centrality", {})

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate consolidated architecture documentation."""
        filepath = output_dir / "architecture.md"
        content = self._generate_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "layer": "architecture",
            "files": [str(filepath)],
        }

    def _generate_content(self) -> str:
        """Generate the architecture page."""
        lines = []
        lines.append("# Architecture")
        lines.append("")

        # Summary stats
        total_files = len(self.files)
        total_lines = sum(f.get("lines", 0) for f in self.files)
        total_classes = len(self.symbol_index.get("classes", []))
        total_functions = len(self.symbol_index.get("functions", []))

        lines.append("## Overview")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Files | {total_files} |")
        lines.append(f"| Lines | {total_lines:,} |")
        lines.append(f"| Classes | {total_classes} |")
        lines.append(f"| Functions | {total_functions} |")
        lines.append("")

        # Components
        components = self._analyze_components()
        if components:
            lines.append("## Components")
            lines.append("")
            lines.append("| Component | Files | Lines | Classes | Functions |")
            lines.append("|-----------|-------|-------|---------|-----------|")

            for comp in sorted(components, key=lambda c: -c["lines"]):
                lines.append(
                    f"| `{comp['name']}` | {comp['files']} | {comp['lines']:,} | "
                    f"{comp['classes']} | {comp['functions']} |"
                )
            lines.append("")

        # Entry points
        entry_points = self.execution_flow.get("entry_points", [])
        if entry_points:
            lines.append("## Entry Points")
            lines.append("")
            for ep in entry_points[:10]:
                name = ep.get("name", "")
                file_path = ep.get("file", "")
                reason = ep.get("reason", "")
                filename = Path(file_path).name
                lines.append(f"- `{name}` in `{filename}` - {reason}")
            lines.append("")

        # Core functions (from centrality)
        core = self.centrality.get("core", [])
        if core:
            lines.append("## Core Functions")
            lines.append("")
            lines.append("Functions with the highest in-degree (most called):")
            lines.append("")
            for func in core[:10]:
                name = func.get("name", "")
                in_deg = func.get("in_degree", 0)
                lines.append(f"- `{name}` (called by {in_deg} functions)")
            lines.append("")

        # Hub functions
        hubs = self.centrality.get("hubs", [])
        if hubs:
            lines.append("## Hub Functions")
            lines.append("")
            lines.append("Functions with high out-degree (orchestrators):")
            lines.append("")
            for func in hubs[:10]:
                name = func.get("name", "")
                out_deg = func.get("out_degree", 0)
                lines.append(f"- `{name}` (calls {out_deg} functions)")
            lines.append("")

        return "\n".join(lines)

    def _analyze_components(self) -> list[dict[str, Any]]:
        """Analyze components by grouping files."""
        components: dict[str, dict[str, Any]] = {}

        for f in self.files:
            path = f.get("path", "")
            if not path:
                continue

            parts = Path(path).parts
            if not parts:
                continue

            # Get top-level component
            first = parts[0]
            if first in ("src", "lib", "app") and len(parts) > 1:
                comp_name = parts[1]
            else:
                comp_name = first

            if comp_name not in components:
                components[comp_name] = {
                    "name": comp_name,
                    "files": 0,
                    "lines": 0,
                    "classes": 0,
                    "functions": 0,
                }

            components[comp_name]["files"] += 1
            components[comp_name]["lines"] += f.get("lines", 0)

        # Count classes/functions per component
        for cls in self.symbol_index.get("classes", []):
            path = cls.get("file", "")
            if path:
                parts = Path(path).parts
                if parts:
                    first = parts[0]
                    if first in ("src", "lib", "app") and len(parts) > 1:
                        comp = parts[1]
                    else:
                        comp = first
                    if comp in components:
                        components[comp]["classes"] += 1

        for func in self.symbol_index.get("functions", []):
            path = func.get("file", "")
            if path:
                parts = Path(path).parts
                if parts:
                    first = parts[0]
                    if first in ("src", "lib", "app") and len(parts) > 1:
                        comp = parts[1]
                    else:
                        comp = first
                    if comp in components:
                        components[comp]["functions"] += 1

        return list(components.values())


class ConsolidatedHealthGenerator:
    """Generate a single health/dependencies page."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        self.index_data = index_data
        self.dependencies = index_data.get("dependencies", {})
        self.complexity = index_data.get("complexity", {})
        self.env_vars = index_data.get("env_vars", [])

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate consolidated health documentation."""
        filepath = output_dir / "health.md"
        content = self._generate_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "layer": "health",
            "files": [str(filepath)],
        }

    def _generate_content(self) -> str:
        """Generate the health page."""
        lines = []
        lines.append("# Project Health")
        lines.append("")

        # Dependencies
        python_deps = self.dependencies.get("python", {})
        node_deps = self.dependencies.get("node", {})

        if python_deps or node_deps:
            lines.append("## Dependencies")
            lines.append("")

        if python_deps:
            # Handle both list format and dict with production/development keys
            if isinstance(python_deps, list):
                all_deps = python_deps
                lines.append(f"### Python ({len(all_deps)} packages)")
                lines.append("")
                if all_deps:
                    lines.append("| Package |")
                    lines.append("|---------|")
                    for dep in sorted(all_deps):
                        lines.append(f"| `{dep}` |")
                    lines.append("")
            else:
                prod = python_deps.get("production") or []
                dev = python_deps.get("development") or []
                lines.append(f"### Python ({len(prod)} production, {len(dev)} dev)")
                lines.append("")
                if prod:
                    lines.append("| Package | Version |")
                    lines.append("|---------|---------|")
                    for dep in sorted(prod, key=lambda d: d.get("name", "") if isinstance(d, dict) else d):
                        if isinstance(dep, dict):
                            name = dep.get("name", "")
                            version = dep.get("version", "")
                        else:
                            name = dep
                            version = ""
                        lines.append(f"| `{name}` | {version} |")
                    lines.append("")

        if node_deps:
            # Handle both list format and dict format
            if isinstance(node_deps, list):
                lines.append(f"### Node.js ({len(node_deps)} packages)")
                lines.append("")
                if node_deps:
                    lines.append("| Package |")
                    lines.append("|---------|")
                    for dep in sorted(node_deps):
                        lines.append(f"| `{dep}` |")
                    lines.append("")
            else:
                prod = node_deps.get("production") or {}
                dev = node_deps.get("development") or {}
                prod_count = len(prod) if isinstance(prod, (dict, list)) else 0
                dev_count = len(dev) if isinstance(dev, (dict, list)) else 0
                lines.append(f"### Node.js ({prod_count} production, {dev_count} dev)")
                lines.append("")
                if prod:
                    lines.append("| Package | Version |")
                    lines.append("|---------|---------|")
                    if isinstance(prod, dict):
                        for name, version in sorted(prod.items()):
                            lines.append(f"| `{name}` | {version} |")
                    else:
                        for name in sorted(prod):
                            lines.append(f"| `{name}` | |")
                    lines.append("")

        # Complexity metrics
        if self.complexity:
            lines.append("## Code Complexity")
            lines.append("")

            high_complexity = self.complexity.get("high_complexity", [])
            if high_complexity:
                lines.append("### High Complexity Functions")
                lines.append("")
                lines.append("| Function | File | Complexity |")
                lines.append("|----------|------|------------|")
                for func in high_complexity[:20]:
                    name = func.get("name", "")
                    file_path = func.get("file", "")
                    complexity = func.get("complexity", 0)
                    filename = Path(file_path).name
                    lines.append(f"| `{name}` | `{filename}` | {complexity} |")
                lines.append("")

        # Environment variables
        if self.env_vars:
            lines.append("## Environment Variables")
            lines.append("")
            lines.append("| Variable | Used In |")
            lines.append("|----------|---------|")
            for var in sorted(self.env_vars, key=lambda v: v.get("name", "")):
                name = var.get("name", "")
                files = var.get("files", [])
                file_list = ", ".join(Path(f).name for f in files[:3])
                if len(files) > 3:
                    file_list += f" (+{len(files) - 3})"
                lines.append(f"| `{name}` | {file_list} |")
            lines.append("")

        return "\n".join(lines)


class ConsolidatedIndexGenerator:
    """Generate the main index page."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        self.index_data = index_data
        self.meta = index_data.get("meta", {})
        self.summary = index_data.get("summary", {})
        self.files = index_data.get("files", [])
        self.symbol_index = index_data.get("symbol_index", {})
        self.endpoints = index_data.get("api_endpoints", [])
        self.linker = ModuleLinker(index_data)

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Generate the main index page."""
        filepath = output_dir / "index.md"
        content = self._generate_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "layer": "index",
            "files": [str(filepath)],
        }

    def _generate_content(self) -> str:
        """Generate the index page content."""
        lines = []

        # Header
        lines.append("# Codebase Documentation")
        lines.append("")

        generated_at = self.meta.get("generated_at", "")
        version = self.meta.get("tool_version", "")
        if generated_at or version:
            lines.append(f"*Generated: {generated_at} | Tool version: {version}*")
            lines.append("")

        # Stats
        total_files = self.summary.get("total_files", len(self.files))
        total_lines = self.summary.get("total_lines", 0)
        total_classes = len(self.symbol_index.get("classes", []))
        total_functions = len(self.symbol_index.get("functions", []))
        total_endpoints = len(self.endpoints)

        by_lang = self.summary.get("by_language", {})
        languages = ", ".join(by_lang.keys()) if by_lang else "unknown"

        lines.append("## Overview")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| **Files** | {total_files} |")
        lines.append(f"| **Lines** | {total_lines:,} |")
        lines.append(f"| **Classes** | {total_classes} |")
        lines.append(f"| **Functions** | {total_functions} |")
        if total_endpoints:
            lines.append(f"| **API Endpoints** | {total_endpoints} |")
        lines.append(f"| **Languages** | {languages} |")
        lines.append("")

        # Navigation
        lines.append("## Documentation")
        lines.append("")
        lines.append("| Section | Description |")
        lines.append("|---------|-------------|")
        lines.append("| [Code](code/README.md) | All modules, classes, and functions |")
        if total_endpoints:
            lines.append("| [API](api-endpoints.md) | REST endpoints reference |")
        lines.append("| [Architecture](architecture.md) | Components, patterns, core functions |")
        lines.append("| [Health](health.md) | Dependencies, complexity, environment |")
        lines.append("")

        # Quick links to key classes/functions
        key_classes = self._find_key_classes()
        if key_classes:
            lines.append("## Key Classes")
            lines.append("")
            for cls in key_classes[:5]:
                name = cls.get("name", "")
                desc = cls.get("summary", cls.get("docstring", ""))
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                link = self.linker.link_symbol(name, "")
                lines.append(f"- {link} - {desc}")
            lines.append("")

        return "\n".join(lines)

    def _find_key_classes(self) -> list[dict[str, Any]]:
        """Find key classes by naming patterns."""
        key_patterns = {"service", "controller", "manager", "handler", "repository"}
        key_classes = []

        for cls in self.symbol_index.get("classes", []):
            name = cls.get("name", "").lower()
            if any(p in name for p in key_patterns):
                key_classes.append(cls)

        return sorted(key_classes, key=lambda c: -len(c.get("methods", [])))[:10]


def generate_consolidated_docs(
    index_data: dict[str, Any],
    output_dir: Path,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Generate consolidated documentation.

    Args:
        index_data: The codebase index.
        output_dir: Directory to write documentation.
        root: Root directory for reading source files.

    Returns:
        Summary of generated documentation.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # Generate code pages
    code_gen = ConsolidatedCodeGenerator(index_data, root)
    results.append(code_gen.generate(output_dir))

    # Generate API endpoints (if any)
    if index_data.get("api_endpoints"):
        api_gen = ConsolidatedAPIGenerator(index_data)
        results.append(api_gen.generate(output_dir))

    # Generate architecture page
    arch_gen = ConsolidatedArchitectureGenerator(index_data)
    results.append(arch_gen.generate(output_dir))

    # Generate health page
    health_gen = ConsolidatedHealthGenerator(index_data)
    results.append(health_gen.generate(output_dir))

    # Generate index page
    index_gen = ConsolidatedIndexGenerator(index_data)
    results.append(index_gen.generate(output_dir))

    # Collect all generated files
    all_files = []
    for r in results:
        all_files.extend(r.get("files", []))

    return {
        "output_dir": str(output_dir),
        "files": all_files,
        "layers": results,
    }
