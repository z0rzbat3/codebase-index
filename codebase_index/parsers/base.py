"""
Base parser class and registry for language parsers.

To add support for a new language:
1. Create a new parser class inheriting from BaseParser
2. Implement the `scan` method
3. Register using the @ParserRegistry.register decorator or ParserRegistry.register_parser()

Example:
    @ParserRegistry.register("rust", [".rs"])
    class RustParser(BaseParser):
        def scan(self, filepath: Path) -> dict:
            # Parse .rs files and return structured data
            ...
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    Registry for language parsers.

    Manages parser classes and their file extension mappings.
    Supports dynamic registration of custom parsers and config injection.
    """

    _parser_classes: ClassVar[dict[str, Type["BaseParser"]]] = {}
    _extension_map: ClassVar[dict[str, str]] = {}  # .ext -> language name
    _cached_parsers: ClassVar[dict[tuple[str, int], "BaseParser"]] = {}  # (lang, config_id) -> instance

    @classmethod
    def register(
        cls,
        language: str,
        extensions: list[str],
    ) -> Callable[[Type["BaseParser"]], Type["BaseParser"]]:
        """
        Decorator to register a parser class.

        Args:
            language: Language name (e.g., "python", "rust").
            extensions: List of file extensions (e.g., [".py", ".pyw"]).

        Returns:
            Decorator function.

        Example:
            @ParserRegistry.register("python", [".py", ".pyw"])
            class PythonParser(BaseParser):
                ...
        """
        def decorator(parser_class: Type["BaseParser"]) -> Type["BaseParser"]:
            cls.register_parser(language, extensions, parser_class)
            return parser_class
        return decorator

    @classmethod
    def register_parser(
        cls,
        language: str,
        extensions: list[str],
        parser_class: Type["BaseParser"],
    ) -> None:
        """
        Register a parser class for a language.

        Args:
            language: Language name.
            extensions: List of file extensions.
            parser_class: Parser class (stored, instantiated on demand with config).
        """
        cls._parser_classes[language] = parser_class

        for ext in extensions:
            ext_lower = ext.lower()
            if not ext_lower.startswith("."):
                ext_lower = "." + ext_lower
            cls._extension_map[ext_lower] = language

        logger.debug("Registered parser for %s: %s", language, extensions)

    @classmethod
    def get_parser(
        cls,
        filepath: Path,
        config: dict[str, Any] | None = None,
    ) -> tuple["BaseParser" | None, str | None]:
        """
        Get the appropriate parser for a file, configured with the given config.

        Args:
            filepath: Path to the file.
            config: Configuration dictionary to pass to the parser.

        Returns:
            Tuple of (parser instance, language name), or (None, None) if no parser.
        """
        suffix = filepath.suffix.lower()
        language = cls._extension_map.get(suffix)

        if language:
            parser = cls._get_configured_parser(language, config)
            return parser, language

        return None, None

    @classmethod
    def _get_configured_parser(
        cls,
        language: str,
        config: dict[str, Any] | None,
    ) -> "BaseParser" | None:
        """Get or create a parser instance with the given config."""
        parser_class = cls._parser_classes.get(language)
        if not parser_class:
            return None

        # Use config id for caching (None config = id 0)
        config_id = id(config) if config else 0
        cache_key = (language, config_id)

        if cache_key not in cls._cached_parsers:
            parser = parser_class()
            if config:
                parser.configure(config)
            cls._cached_parsers[cache_key] = parser

        return cls._cached_parsers[cache_key]

    @classmethod
    def get_parser_for_language(
        cls,
        language: str,
        config: dict[str, Any] | None = None,
    ) -> "BaseParser" | None:
        """
        Get parser by language name.

        Args:
            language: Language name.
            config: Configuration dictionary.

        Returns:
            Parser instance or None.
        """
        return cls._get_configured_parser(language, config)

    @classmethod
    def list_languages(cls) -> list[str]:
        """Get list of registered languages."""
        return list(cls._parser_classes.keys())

    @classmethod
    def list_extensions(cls) -> dict[str, str]:
        """Get mapping of extensions to languages."""
        return dict(cls._extension_map)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered parsers. Useful for testing."""
        cls._parser_classes.clear()
        cls._extension_map.clear()
        cls._cached_parsers.clear()


class BaseParser(ABC):
    """
    Abstract base class for language parsers.

    Subclasses must implement the `scan` method to extract
    structural information from source files.

    The scan method should return a dictionary with language-specific
    keys. Common keys include:
    - classes: List of class definitions
    - functions: List of function definitions
    - imports: Dict with 'internal' and 'external' lists
    - error: Error message if parsing failed
    """

    # Subclasses can set this to provide a regex fallback
    supports_fallback: bool = False

    def __init__(self) -> None:
        """Initialize the parser with empty config."""
        self.config: dict[str, Any] = {}

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the parser with the given config.

        Subclasses can override to extract specific config values.

        Args:
            config: Configuration dictionary.
        """
        self.config = config

    @abstractmethod
    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a source file and extract structural information.

        Args:
            filepath: Path to the source file.

        Returns:
            Dictionary containing extracted information.
            Should include an 'error' key if parsing failed.

        The returned dict structure varies by language but typically includes:
        - classes: List of class info dicts
        - functions: List of function info dicts
        - imports: Dict with 'internal' and 'external' import lists
        """
        ...

    def scan_with_fallback(self, filepath: Path) -> dict[str, Any]:
        """
        Scan with fallback to regex if AST parsing fails.

        Override this in subclasses that support regex fallback.

        Args:
            filepath: Path to the source file.

        Returns:
            Dictionary containing extracted information.
        """
        return self.scan(filepath)

    def get_empty_result(self) -> dict[str, Any]:
        """
        Get an empty result structure for this parser.

        Subclasses can override to provide language-specific structure.
        """
        return {
            "classes": [],
            "functions": [],
            "imports": {"internal": [], "external": []},
        }

    def _match_patterns(
        self,
        text: str,
        patterns: list[dict[str, Any]],
        pattern_key: str = "regex",
    ) -> list[dict[str, Any]]:
        """
        Match text against a list of config patterns.

        Helper method for subclasses to use config-driven pattern matching.

        Args:
            text: Text to match against.
            patterns: List of pattern dicts from config.
            pattern_key: Key in pattern dict containing the regex.

        Returns:
            List of matching pattern dicts.
        """
        matches = []
        for pattern in patterns:
            regex = pattern.get(pattern_key)
            if regex:
                try:
                    if re.search(regex, text):
                        matches.append(pattern)
                except re.error as e:
                    logger.warning("Invalid regex pattern %r: %s", regex, e)
        return matches
