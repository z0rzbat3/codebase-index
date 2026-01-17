"""
Coupling analyzer for codebase_index.

Analyzes file coupling to answer: "If I change file X, what else might need to change?"
Uses call graph, imports, and naming patterns to compute coupling scores.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class CouplingAnalyzer:
    """
    Analyze coupling between files to identify tightly related code.

    Coupling score is computed from:
    - Call frequency: How often functions in A call functions in B
    - Import dependency: Direct imports between files
    - Shared imports: Common external dependencies
    - Naming similarity: Similar file/function names
    """

    # Weights for different coupling factors
    WEIGHTS = {
        "calls_to": 0.35,      # A calls B
        "calls_from": 0.25,    # B calls A
        "imports": 0.20,       # Direct import relationship
        "shared_imports": 0.10, # Common dependencies
        "naming": 0.10,        # Similar names
    }

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the coupling analyzer.

        Args:
            index_data: The loaded index data.
        """
        self.index_data = index_data
        self._files_by_path: dict[str, dict[str, Any]] | None = None
        self._call_graph: dict[str, Any] | None = None
        self._reverse_calls: dict[str, set[str]] | None = None
        self._file_imports: dict[str, set[str]] | None = None

    @property
    def files_by_path(self) -> dict[str, dict[str, Any]]:
        """Get files indexed by path."""
        if self._files_by_path is None:
            self._files_by_path = {}
            for file_info in self.index_data.get("files", []):
                path = file_info.get("path", "")
                self._files_by_path[path] = file_info
        return self._files_by_path

    @property
    def call_graph(self) -> dict[str, Any]:
        """Get the call graph from the index."""
        if self._call_graph is None:
            self._call_graph = self.index_data.get("call_graph", {})
        return self._call_graph

    @property
    def reverse_calls(self) -> dict[str, set[str]]:
        """Build reverse call mapping (callee -> caller files)."""
        if self._reverse_calls is None:
            self._reverse_calls = {}
            for func_key, func_data in self.call_graph.items():
                caller_file = func_key.split(":")[0] if ":" in func_key else ""
                for call in func_data.get("calls", []):
                    if call not in self._reverse_calls:
                        self._reverse_calls[call] = set()
                    self._reverse_calls[call].add(caller_file)
        return self._reverse_calls

    @property
    def file_imports(self) -> dict[str, set[str]]:
        """Get imports for each file."""
        if self._file_imports is None:
            self._file_imports = {}
            for path, file_info in self.files_by_path.items():
                exports = file_info.get("exports", {})
                imports = exports.get("imports", {})

                all_imports = set()
                if isinstance(imports, dict):
                    all_imports.update(imports.get("internal", []))
                    all_imports.update(imports.get("external", []))
                elif isinstance(imports, list):
                    all_imports.update(imports)

                self._file_imports[path] = all_imports
        return self._file_imports

    def analyze(self, file_path: str, top_k: int = 10) -> dict[str, Any]:
        """
        Find files most tightly coupled to the given file.

        Args:
            file_path: Path to the file to analyze.
            top_k: Number of coupled files to return.

        Returns:
            Dictionary with coupled files, scores, and reasons.
        """
        result: dict[str, Any] = {
            "file": file_path,
            "coupled_files": [],
            "summary": "",
        }

        # Normalize path
        file_path = self._normalize_path(file_path)

        if file_path not in self.files_by_path:
            result["summary"] = f"File not found in index: {file_path}"
            return result

        # Calculate coupling scores with all other files
        scores: dict[str, dict[str, Any]] = {}

        for other_path in self.files_by_path:
            if other_path == file_path:
                continue

            score_info = self._calculate_coupling(file_path, other_path)
            if score_info["total"] > 0:
                scores[other_path] = score_info

        # Sort by total score and take top_k
        sorted_files = sorted(
            scores.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:top_k]

        for other_path, score_info in sorted_files:
            result["coupled_files"].append({
                "file": other_path,
                "score": round(score_info["total"], 3),
                "reasons": score_info["reasons"],
                "details": {
                    k: round(v, 3) for k, v in score_info["components"].items() if v > 0
                },
            })

        # Build summary
        result["summary"] = self._build_summary(result)

        return result

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for matching."""
        # Remove leading ./
        file_path = file_path.lstrip("./")

        # Try exact match first
        if file_path in self.files_by_path:
            return file_path

        # Try partial match
        for path in self.files_by_path:
            if path.endswith(file_path) or file_path.endswith(path):
                return path

        return file_path

    def _calculate_coupling(
        self, file_a: str, file_b: str
    ) -> dict[str, Any]:
        """
        Calculate coupling score between two files.

        Returns:
            Dict with total score, component scores, and reasons.
        """
        components = {
            "calls_to": 0.0,
            "calls_from": 0.0,
            "imports": 0.0,
            "shared_imports": 0.0,
            "naming": 0.0,
        }
        reasons = []

        # 1. Calls from A to B
        calls_a_to_b = self._count_calls_between(file_a, file_b)
        if calls_a_to_b > 0:
            components["calls_to"] = min(1.0, calls_a_to_b / 5)  # Normalize
            reasons.append(f"calls ({calls_a_to_b}x)")

        # 2. Calls from B to A
        calls_b_to_a = self._count_calls_between(file_b, file_a)
        if calls_b_to_a > 0:
            components["calls_from"] = min(1.0, calls_b_to_a / 5)
            if "calls" not in str(reasons):
                reasons.append(f"called by ({calls_b_to_a}x)")

        # 3. Direct import relationship
        if self._has_import(file_a, file_b):
            components["imports"] = 1.0
            reasons.append("imports")
        elif self._has_import(file_b, file_a):
            components["imports"] = 0.8
            reasons.append("imported by")

        # 4. Shared imports
        shared = self._count_shared_imports(file_a, file_b)
        if shared > 0:
            components["shared_imports"] = min(1.0, shared / 10)
            if shared >= 3:
                reasons.append(f"shared deps ({shared})")

        # 5. Naming similarity
        name_sim = self._name_similarity(file_a, file_b)
        if name_sim > 0.5:
            components["naming"] = name_sim
            reasons.append("similar names")

        # Calculate weighted total
        total = sum(
            components[k] * self.WEIGHTS[k]
            for k in components
        )

        return {
            "total": total,
            "components": components,
            "reasons": reasons,
        }

    def _count_calls_between(self, from_file: str, to_file: str) -> int:
        """Count how many times functions in from_file call functions in to_file."""
        count = 0

        # Get functions defined in to_file
        to_file_info = self.files_by_path.get(to_file, {})
        to_exports = to_file_info.get("exports", {})
        to_functions = {f.get("name") for f in to_exports.get("functions", [])}
        to_classes = {c.get("name") for c in to_exports.get("classes", [])}
        to_symbols = to_functions | to_classes

        # Check call graph for calls from from_file to these symbols
        for func_key, func_data in self.call_graph.items():
            if not func_key.startswith(from_file + ":"):
                continue

            for call in func_data.get("calls", []):
                # Direct match
                if call in to_symbols:
                    count += 1
                # Method call match (e.g., ClassName.method)
                elif "." in call:
                    class_name = call.split(".")[0]
                    if class_name in to_symbols:
                        count += 1

        return count

    def _has_import(self, from_file: str, to_file: str) -> bool:
        """Check if from_file imports from to_file."""
        imports = self.file_imports.get(from_file, set())

        # Convert to_file path to module-like pattern
        to_module = to_file.replace("/", ".").replace(".py", "")
        to_module_parts = to_module.split(".")

        for imp in imports:
            if isinstance(imp, str):
                # Check if import matches the target file
                if to_module in imp or imp in to_module:
                    return True
                # Check partial match (e.g., "auth" matches "src/auth/service.py")
                for part in to_module_parts:
                    if part and part in imp:
                        return True

        return False

    def _count_shared_imports(self, file_a: str, file_b: str) -> int:
        """Count shared external imports between two files."""
        imports_a = self.file_imports.get(file_a, set())
        imports_b = self.file_imports.get(file_b, set())

        # Only count external imports (not internal modules)
        external_a = {i for i in imports_a if isinstance(i, str) and not i.startswith("src")}
        external_b = {i for i in imports_b if isinstance(i, str) and not i.startswith("src")}

        return len(external_a & external_b)

    def _name_similarity(self, file_a: str, file_b: str) -> float:
        """Calculate naming similarity between files."""
        # Extract base names without extension
        name_a = Path(file_a).stem.lower()
        name_b = Path(file_b).stem.lower()

        # Remove common prefixes/suffixes
        for prefix in ["test_", "tests_"]:
            name_a = name_a.removeprefix(prefix)
            name_b = name_b.removeprefix(prefix)

        for suffix in ["_test", "_tests", "_router", "_service", "_schema", "_model"]:
            name_a = name_a.removesuffix(suffix)
            name_b = name_b.removesuffix(suffix)

        # Exact match after normalization
        if name_a == name_b:
            return 1.0

        # One contains the other
        if name_a in name_b or name_b in name_a:
            return 0.7

        # Check for common patterns (e.g., user_service.py ↔ user_router.py)
        parts_a = set(re.split(r"[_\-]", name_a))
        parts_b = set(re.split(r"[_\-]", name_b))

        if parts_a and parts_b:
            overlap = len(parts_a & parts_b) / max(len(parts_a), len(parts_b))
            if overlap > 0.5:
                return overlap

        return 0.0

    def _build_summary(self, result: dict[str, Any]) -> str:
        """Build a human-readable summary."""
        coupled = result["coupled_files"]

        if not coupled:
            return f"No tightly coupled files found for {result['file']}"

        high_coupling = [f for f in coupled if f["score"] >= 0.3]

        if high_coupling:
            names = [Path(f["file"]).name for f in high_coupling[:3]]
            return (
                f"{len(coupled)} coupled file(s); "
                f"{len(high_coupling)} highly coupled: {', '.join(names)}"
            )
        else:
            return f"{len(coupled)} loosely coupled file(s)"
