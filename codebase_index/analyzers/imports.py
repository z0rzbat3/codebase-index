"""
Import aggregator for codebase_index.

Aggregates imports across the codebase and detects missing/unused dependencies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from codebase_index.config import STDLIB_MODULES

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


# Common package name -> import name mappings
PKG_TO_IMPORT = {
    "pillow": "pil",
    "pyyaml": "yaml",
    "python_dateutil": "dateutil",
    "beautifulsoup4": "bs4",
    "scikit_learn": "sklearn",
    "opencv_python": "cv2",
    "python_dotenv": "dotenv",
    "python_jose": "jose",
    "python_multipart": "multipart",
    "email_validator": "email_validator",
    "typing_extensions": "typing_extensions",
}

# Packages that are commonly imported via their submodules
UMBRELLA_PACKAGES = {
    "fastapi": ["fastapi", "starlette"],
    "httpx": ["httpx"],
    "pydantic": ["pydantic"],
}


class ImportAggregator:
    """Aggregate all imports across the codebase and detect missing/unused deps."""

    def __init__(self) -> None:
        self.all_imports: set[str] = set()
        self.import_locations: dict[str, list[str]] = {}
        self.internal_modules: set[str] = set()

    def add_imports(self, imports: list[str], filepath: str) -> None:
        """
        Add imports from a file.

        Args:
            imports: List of import module names.
            filepath: Path to the file containing these imports.
        """
        for imp in imports:
            if not imp or not isinstance(imp, str):
                continue
            root_module = imp.split(".")[0].strip()
            if not root_module:
                continue
            self.all_imports.add(root_module)
            if root_module not in self.import_locations:
                self.import_locations[root_module] = []
            self.import_locations[root_module].append(filepath)

    def add_internal_module(self, module_name: str) -> None:
        """
        Register a module as internal to the project.

        Args:
            module_name: Name of the internal module.
        """
        if module_name:
            self.internal_modules.add(module_name.lower())

    def analyze(self, declared_deps: list[str]) -> dict[str, Any]:
        """
        Analyze imports against declared dependencies.

        Args:
            declared_deps: List of declared package names from requirements.txt etc.

        Returns:
            Dictionary with analysis results including missing and unused deps.
        """
        # Normalize declared deps (lowercase, strip version specifiers)
        normalized_deps: set[str] = set()
        for dep in declared_deps:
            name = dep.lower().replace("-", "_").replace(".", "_")
            normalized_deps.add(name)

        # Add umbrella package imports to normalized deps
        for pkg, imports in UMBRELLA_PACKAGES.items():
            if pkg in [d.lower().replace("-", "_") for d in declared_deps]:
                for imp in imports:
                    normalized_deps.add(imp)

        # Add reverse mappings
        for pkg, imp in PKG_TO_IMPORT.items():
            normalized_deps.add(pkg)
            normalized_deps.add(imp)

        # Filter out stdlib and internal modules
        third_party_imports: set[str] = set()
        for imp in self.all_imports:
            imp_lower = imp.lower()
            # Skip stdlib
            if imp_lower in STDLIB_MODULES:
                continue
            # Skip internal project modules
            if imp_lower.startswith("_") or imp_lower in self.internal_modules:
                continue
            third_party_imports.add(imp_lower.replace("-", "_"))

        # Find missing (imported but not declared)
        missing: list[dict[str, Any]] = []
        for imp in sorted(third_party_imports):
            found = False
            for dep in normalized_deps:
                if imp == dep or imp.startswith(dep + "_") or dep.startswith(imp + "_"):
                    found = True
                    break
                # Check pkg_to_import mappings
                if dep in PKG_TO_IMPORT and PKG_TO_IMPORT[dep] == imp:
                    found = True
                    break
            if not found:
                missing.append({
                    "module": imp,
                    "used_in": self.import_locations.get(imp, [])[:5],  # First 5 files
                })

        # Find unused (declared but not imported)
        unused: list[str] = []
        for dep in sorted(declared_deps):
            dep_normalized = dep.lower().replace("-", "_")
            # Check direct match or via pkg_to_import
            import_name = PKG_TO_IMPORT.get(dep_normalized, dep_normalized)
            found = any(
                imp == dep_normalized or imp == import_name
                or dep_normalized.startswith(imp) or imp.startswith(dep_normalized)
                for imp in third_party_imports
            )
            if not found:
                unused.append(dep)

        return {
            "total_unique_imports": len(self.all_imports),
            "third_party_imports": sorted(third_party_imports),
            "missing_deps": missing,
            "unused_deps": unused,
        }

    def clear(self) -> None:
        """Clear all collected data."""
        self.all_imports.clear()
        self.import_locations.clear()
        self.internal_modules.clear()
