"""
LLM-generated code summaries for codebase_index.

Generates one-line descriptions of what each function does,
making the index more useful for code navigation.

Supports multiple providers:
  - OpenRouter (any model): OPENROUTER_API_KEY
  - Anthropic (Claude): ANTHROPIC_API_KEY
  - OpenAI-compatible: OPENAI_API_KEY + OPENAI_BASE_URL

Requires: pip install codebase-index[summaries]
  - httpx (for API calls)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None  # type: ignore


# Provider configurations
PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "qwen/qwen3-coder-30b-a3b-instruct",
        "headers": lambda key: {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://github.com/codebase-index",
            "X-Title": "codebase-index",
        },
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-haiku-latest",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
        "headers": lambda key: {
            "Authorization": f"Bearer {key}",
        },
    },
}

# Prompt template
SUMMARY_PROMPT = """Summarize what this function does in ONE concise sentence (max 15 words). Focus on the primary purpose, not implementation details. Do not start with "This function" or "The function".

Function:
```{language}
{code}
```

Summary:"""


class SummaryGenerator:
    """
    Generate LLM summaries for code symbols.

    Supports multiple providers (OpenRouter, Anthropic, OpenAI-compatible)
    with caching based on code hash to avoid regenerating unchanged code.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """
        Initialize the summary generator.

        Args:
            provider: Provider name (openrouter, anthropic, openai) or auto-detect.
            model: Model name (provider-specific).
            api_key: API key (or use environment variable).
            base_url: Custom base URL for API.
        """
        if not HAS_HTTPX:
            raise ImportError(
                "Summary generation requires httpx. "
                "Install with: pip install codebase-index[summaries]"
            )

        # Auto-detect provider from available API keys
        self.provider = provider or self._detect_provider()
        if not self.provider:
            raise ValueError(
                "No API key found. Set one of:\n"
                "  - OPENROUTER_API_KEY (recommended - access any model)\n"
                "  - ANTHROPIC_API_KEY\n"
                "  - OPENAI_API_KEY"
            )

        provider_config = PROVIDERS.get(self.provider, {})

        # Get API key
        self.api_key = api_key or os.environ.get(provider_config.get("env_key", ""))
        if not self.api_key:
            raise ValueError(
                f"{provider_config.get('env_key', 'API_KEY')} environment variable is required."
            )

        # Set base URL (allow override)
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL") or provider_config.get("base_url", "")

        # Set model
        self.model = model or provider_config.get("default_model", "")

        # Build headers
        headers_func = provider_config.get("headers", lambda k: {"Authorization": f"Bearer {k}"})
        self.headers = headers_func(self.api_key)
        self.headers["Content-Type"] = "application/json"

        self._client: Any = None
        self._cache: dict[str, str] = {}

    def _detect_provider(self) -> str | None:
        """Detect provider from available environment variables."""
        if os.environ.get("OPENROUTER_API_KEY"):
            return "openrouter"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        return None

    @property
    def client(self) -> Any:
        """Lazy-load the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=60.0)
        return self._client

    def load_cache(self, cache_data: dict[str, str]) -> None:
        """Load existing summary cache."""
        self._cache = dict(cache_data)

    def generate_summaries(
        self,
        index_data: dict[str, Any],
        root: Path,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Generate summaries for all functions in the index.

        Args:
            index_data: The codebase index data.
            root: Root directory of the codebase.
            force: If True, regenerate all summaries (ignore cache).

        Returns:
            Dictionary with summary statistics and cache.
        """
        stats = {
            "generated": 0,
            "cached": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Process each file
        for file_info in index_data.get("files", []):
            file_path = root / file_info.get("path", "")
            language = file_info.get("language", "unknown")
            exports = file_info.get("exports", {})

            # Get source code if available
            source_lines = self._read_file(file_path)
            if not source_lines:
                continue

            # Process functions
            for func in exports.get("functions", []):
                self._generate_symbol_summary(
                    func, source_lines, language, force, stats
                )

            # Process class methods
            for cls in exports.get("classes", []):
                for method in cls.get("methods", []):
                    self._generate_symbol_summary(
                        method, source_lines, language, force, stats,
                        class_name=cls.get("name")
                    )

        return {
            "stats": stats,
            "cache": self._cache,
            "model": self.model,
            "provider": self.provider,
        }

    def _generate_symbol_summary(
        self,
        symbol: dict[str, Any],
        source_lines: list[str],
        language: str,
        force: bool,
        stats: dict[str, int],
        class_name: str | None = None,
    ) -> None:
        """Generate summary for a single symbol."""
        name = symbol.get("name", "")
        line = symbol.get("line", 0)

        # Skip dunder methods
        if name.startswith("__") and name.endswith("__"):
            stats["skipped"] += 1
            return

        # Skip if already has a good docstring
        docstring = symbol.get("docstring", "")
        if docstring and len(docstring) > 10 and not force:
            symbol["summary"] = docstring.split("\n")[0][:100]
            symbol["summary_source"] = "docstring"
            stats["skipped"] += 1
            return

        # Extract code snippet
        code = self._extract_code(source_lines, line, max_lines=30)
        if not code:
            stats["skipped"] += 1
            return

        # Check cache
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        if not force and code_hash in self._cache:
            symbol["summary"] = self._cache[code_hash]
            symbol["summary_source"] = "cached"
            stats["cached"] += 1
            return

        # Generate summary
        try:
            summary = self._call_llm(code, language)
            symbol["summary"] = summary
            symbol["summary_source"] = "generated"
            self._cache[code_hash] = summary
            stats["generated"] += 1
        except Exception as e:
            logger.warning("Error generating summary for %s: %s", name, e)
            stats["errors"] += 1

    def _read_file(self, file_path: Path) -> list[str]:
        """Read file content as lines."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()
        except (OSError, IOError):
            return []

    def _extract_code(
        self,
        lines: list[str],
        start_line: int,
        max_lines: int = 30,
    ) -> str:
        """Extract code snippet starting from a line."""
        if not lines or start_line < 1:
            return ""

        start_idx = start_line - 1
        if start_idx >= len(lines):
            return ""

        end_idx = min(start_idx + max_lines, len(lines))
        code_lines = lines[start_idx:end_idx]

        if not code_lines:
            return ""

        # Find end of function
        first_line = code_lines[0]
        base_indent = len(first_line) - len(first_line.lstrip())
        result_lines = [first_line]

        for line in code_lines[1:]:
            stripped = line.strip()

            if not stripped:
                result_lines.append(line)
                continue

            current_indent = len(line) - len(line.lstrip())

            if current_indent <= base_indent and stripped:
                if stripped.startswith(("def ", "class ", "async def ")):
                    break

            result_lines.append(line)

        return "".join(result_lines).strip()

    def _call_llm(self, code: str, language: str) -> str:
        """Call the LLM to generate a summary."""
        prompt = SUMMARY_PROMPT.format(language=language, code=code)

        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            # OpenRouter and OpenAI use same format
            return self._call_openai_compatible(prompt)

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API directly."""
        response = self.client.post(
            f"{self.base_url}/messages",
            headers=self.headers,
            json={
                "model": self.model,
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        summary = data["content"][0]["text"].strip()
        return self._clean_summary(summary)

    def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API (OpenRouter, OpenAI, etc.)."""
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        summary = data["choices"][0]["message"]["content"].strip()
        return self._clean_summary(summary)

    def _clean_summary(self, summary: str) -> str:
        """Clean up common issues in generated summaries."""
        # Remove common prefixes
        summary = re.sub(r'^(This function |The function |It |This method |The method )', '', summary, flags=re.IGNORECASE)
        summary = summary.rstrip(".")

        # Capitalize first letter
        if summary:
            summary = summary[0].upper() + summary[1:]

        return summary[:150]


def generate_summaries(
    index_data: dict[str, Any],
    root: Path,
    force: bool = False,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to generate summaries.

    Args:
        index_data: The codebase index.
        root: Root directory of the codebase.
        force: Regenerate all summaries.
        provider: API provider (openrouter, anthropic, openai).
        model: Model to use.
        api_key: API key (alternative to environment variable).

    Returns:
        Updated index with summaries and cache.
    """
    # Load existing cache if present
    existing_cache = index_data.get("summaries", {}).get("cache", {})

    generator = SummaryGenerator(provider=provider, model=model, api_key=api_key)
    generator.load_cache(existing_cache)

    result = generator.generate_summaries(index_data, root, force=force)

    # Store in index
    index_data["summaries"] = {
        "stats": result["stats"],
        "cache": result["cache"],
        "model": result["model"],
        "provider": result["provider"],
    }

    # Update symbol_index with summaries (link summaries to queryable symbols)
    _link_summaries_to_symbol_index(index_data)

    return index_data


def _link_summaries_to_symbol_index(index_data: dict[str, Any]) -> None:
    """
    Link generated summaries to symbol_index entries.

    After summaries are generated, they're stored in the exports dict.
    This function copies them to symbol_index for easy querying.
    """
    symbol_index = index_data.get("symbol_index", {})

    # Build lookup from (file, name) -> summary
    summary_lookup: dict[tuple[str, str], str] = {}

    for file_info in index_data.get("files", []):
        file_path = file_info.get("path", "")
        exports = file_info.get("exports", {})

        # Functions
        for func in exports.get("functions", []):
            name = func.get("name", "")
            summary = func.get("summary")
            if summary:
                summary_lookup[(file_path, name)] = summary

        # Methods
        for cls in exports.get("classes", []):
            class_name = cls.get("name", "")
            for method in cls.get("methods", []):
                method_name = method.get("name", "")
                summary = method.get("summary")
                if summary:
                    summary_lookup[(file_path, f"{class_name}.{method_name}")] = summary

    # Update symbol_index functions
    for func in symbol_index.get("functions", []):
        file_path = func.get("file", "")
        name = func.get("name", "")
        key = (file_path, name)
        if key in summary_lookup:
            func["summary"] = summary_lookup[key]

    # Update symbol_index methods
    for method in symbol_index.get("methods", []):
        file_path = method.get("file", "")
        class_name = method.get("class", "")
        method_name = method.get("name", "")
        key = (file_path, f"{class_name}.{method_name}")
        if key in summary_lookup:
            method["summary"] = summary_lookup[key]


def check_summaries_available() -> bool:
    """Check if summary generation dependencies are available."""
    return HAS_HTTPX


def check_api_key() -> bool:
    """Check if any API key is configured."""
    return bool(
        os.environ.get("OPENROUTER_API_KEY") or
        os.environ.get("ANTHROPIC_API_KEY") or
        os.environ.get("OPENAI_API_KEY")
    )


def get_available_provider() -> str | None:
    """Get the first available provider based on API keys."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None
