"""
Centrality analyzer - identifies core vs helper components.

Computes graph centrality metrics on the call graph to identify
which functions/classes are central to the codebase (core) vs
peripheral (helpers/utilities).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class CentralityAnalyzer:
    """
    Analyze call graph centrality to identify core components.

    Uses degree centrality and other metrics to classify functions
    as core, helper, or utility based on their position in the
    call graph.
    """

    def __init__(self, index_data: dict[str, Any]) -> None:
        """
        Initialize the centrality analyzer.

        Args:
            index_data: The loaded codebase index.
        """
        self.call_graph = index_data.get("call_graph", {})
        self.symbol_index = index_data.get("symbol_index", {})
        self.files = index_data.get("files", [])

        # Build metrics
        self._in_degree: dict[str, int] = defaultdict(int)
        self._out_degree: dict[str, int] = defaultdict(int)
        self._callers: dict[str, set[str]] = defaultdict(set)
        self._build_metrics()

    def _build_metrics(self) -> None:
        """Build centrality metrics from call graph."""
        # Build reverse lookup for function resolution
        func_to_key: dict[str, list[str]] = defaultdict(list)
        for key in self.call_graph:
            if ":" in key:
                _, func_name = key.rsplit(":", 1)
                func_to_key[func_name].append(key)

        for key, data in self.call_graph.items():
            calls = data.get("calls", [])
            self._out_degree[key] = len(calls)

            for call in calls:
                # Resolve call to full key
                call_name = call.split(".")[-1] if "." in call else call

                # Find matching keys
                if call_name in func_to_key:
                    for target_key in func_to_key[call_name]:
                        self._in_degree[target_key] += 1
                        self._callers[target_key].add(key)
                else:
                    # External call - track by name
                    self._in_degree[call] += 1
                    self._callers[call].add(key)

    def analyze(self) -> dict[str, Any]:
        """
        Analyze centrality and classify components.

        Returns:
            Centrality analysis results with classifications.
        """
        # Calculate combined scores
        scores: dict[str, dict[str, Any]] = {}

        for key in self.call_graph:
            in_deg = self._in_degree.get(key, 0)
            out_deg = self._out_degree.get(key, 0)

            # Parse key
            if ":" in key:
                file_path, func_name = key.rsplit(":", 1)
            else:
                file_path, func_name = "", key

            # Get additional info from call graph
            line = self.call_graph[key].get("line", 0)

            scores[key] = {
                "name": func_name,
                "file": file_path,
                "line": line,
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_degree": in_deg + out_deg,
                "callers": list(self._callers.get(key, set()))[:10],
            }

        # Compute statistics for relative thresholds
        if scores:
            in_degrees = [s["in_degree"] for s in scores.values()]
            out_degrees = [s["out_degree"] for s in scores.values()]
            self._avg_in = sum(in_degrees) / len(in_degrees)
            self._avg_out = sum(out_degrees) / len(out_degrees)
            # Use percentile-based thresholds
            sorted_in = sorted(in_degrees, reverse=True)
            sorted_out = sorted(out_degrees, reverse=True)
            # Top 5% for core/hub thresholds
            top_5_idx = max(1, len(sorted_in) // 20)
            self._high_in_threshold = sorted_in[top_5_idx] if top_5_idx < len(sorted_in) else 3
            self._high_out_threshold = sorted_out[top_5_idx] if top_5_idx < len(sorted_out) else 5
            # Ensure minimum thresholds
            self._high_in_threshold = max(self._high_in_threshold, 3)
            self._high_out_threshold = max(self._high_out_threshold, 5)
        else:
            self._avg_in = 0
            self._avg_out = 0
            self._high_in_threshold = 3
            self._high_out_threshold = 5

        # Classify based on metrics
        classifications = self._classify_components(scores)

        # Get top components by category
        core = sorted(
            [s for s in scores.values() if self._is_core(s)],
            key=lambda x: x["in_degree"],
            reverse=True,
        )[:15]

        hubs = sorted(
            [s for s in scores.values() if self._is_hub(s)],
            key=lambda x: x["out_degree"],
            reverse=True,
        )[:15]

        utilities = sorted(
            [s for s in scores.values() if self._is_utility(s)],
            key=lambda x: x["in_degree"],
            reverse=True,
        )[:15]

        isolated = [s for s in scores.values() if self._is_isolated(s)]

        return {
            "core_components": core,
            "hub_components": hubs,
            "utility_components": utilities,
            "isolated_components": isolated[:10],
            "classifications": classifications,
            "summary": {
                "total_functions": len(scores),
                "core_count": len([s for s in scores.values() if self._is_core(s)]),
                "hub_count": len([s for s in scores.values() if self._is_hub(s)]),
                "utility_count": len([s for s in scores.values() if self._is_utility(s)]),
                "isolated_count": len(isolated),
                "avg_in_degree": self._avg_in,
                "avg_out_degree": self._avg_out,
                "high_in_threshold": self._high_in_threshold,
                "high_out_threshold": self._high_out_threshold,
            },
        }

    def _classify_components(self, scores: dict[str, dict[str, Any]]) -> dict[str, str]:
        """Classify each component by its role."""
        classifications = {}

        for key, score in scores.items():
            if self._is_core(score):
                classifications[key] = "core"
            elif self._is_hub(score):
                classifications[key] = "hub"
            elif self._is_utility(score):
                classifications[key] = "utility"
            elif self._is_isolated(score):
                classifications[key] = "isolated"
            else:
                classifications[key] = "standard"

        return classifications

    def _is_core(self, score: dict[str, Any]) -> bool:
        """
        Check if a component is core (highly called by others).

        Core components are called by many others - they're central
        to the system's functionality. Uses relative threshold based
        on top 5% of in-degree values.
        """
        threshold = getattr(self, '_high_in_threshold', 3)
        return score["in_degree"] >= threshold

    def _is_hub(self, score: dict[str, Any]) -> bool:
        """
        Check if a component is a hub (calls many others).

        Hubs orchestrate other components - they're coordinators
        or entry points. Uses relative threshold based on top 5%
        of out-degree values.
        """
        threshold = getattr(self, '_high_out_threshold', 5)
        avg_in = getattr(self, '_avg_in', 1)
        # Hub: high out-degree and below-average in-degree
        return score["out_degree"] >= threshold and score["in_degree"] <= avg_in

    def _is_utility(self, score: dict[str, Any]) -> bool:
        """
        Check if a component is a utility (called often, calls little).

        Utilities are helper functions that many others depend on
        but don't themselves have many dependencies.
        """
        # Don't classify as utility if already core
        if self._is_core(score):
            return False
        avg_in = getattr(self, '_avg_in', 1)
        avg_out = getattr(self, '_avg_out', 1)
        # Utility: above-average in-degree, below-average out-degree
        return score["in_degree"] > avg_in and score["out_degree"] <= avg_out

    def _is_isolated(self, score: dict[str, Any]) -> bool:
        """
        Check if a component is isolated (no callers, few calls).

        Isolated components might be dead code, entry points,
        or test functions.
        """
        return score["in_degree"] == 0 and score["out_degree"] <= 2

    def get_component_role(self, key: str) -> str:
        """
        Get the role classification for a specific component.

        Args:
            key: The call graph key (file:function).

        Returns:
            Role classification string.
        """
        in_deg = self._in_degree.get(key, 0)
        out_deg = self._out_degree.get(key, 0)

        score = {"in_degree": in_deg, "out_degree": out_deg}

        if self._is_core(score):
            return "core"
        elif self._is_hub(score):
            return "hub"
        elif self._is_utility(score):
            return "utility"
        elif self._is_isolated(score):
            return "isolated"
        return "standard"

    def get_importance_score(self, key: str) -> float:
        """
        Get an importance score for a component (0-1).

        Higher scores indicate more central/important components.

        Args:
            key: The call graph key.

        Returns:
            Importance score between 0 and 1.
        """
        in_deg = self._in_degree.get(key, 0)
        out_deg = self._out_degree.get(key, 0)

        # Weighted combination: in_degree is more important
        max_in = max(self._in_degree.values()) if self._in_degree else 1
        max_out = max(self._out_degree.values()) if self._out_degree else 1

        normalized_in = in_deg / max_in if max_in > 0 else 0
        normalized_out = out_deg / max_out if max_out > 0 else 0

        # Weight in_degree higher (being called is more important)
        return 0.7 * normalized_in + 0.3 * normalized_out


def analyze_centrality(index_data: dict[str, Any]) -> dict[str, Any]:
    """
    Convenience function to analyze centrality.

    Args:
        index_data: The codebase index.

    Returns:
        Centrality analysis results.
    """
    analyzer = CentralityAnalyzer(index_data)
    return analyzer.analyze()
