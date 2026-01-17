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
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    Registry for language parsers.

    Manages parser instances and their file extension mappings.
    Supports dynamic registration of custom parsers.
    """

    _parsers: ClassVar[dict[str, "BaseParser"]] = {}
    _extension_map: ClassVar[dict[str, str]] = {}  # .ext -> language name

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
            parser_class: Parser class (will be instantiated).
        """
        parser_instance = parser_class()
        cls._parsers[language] = parser_instance

        for ext in extensions:
            ext_lower = ext.lower()
            if not ext_lower.startswith("."):
                ext_lower = "." + ext_lower
            cls._extension_map[ext_lower] = language

        logger.debug("Registered parser for %s: %s", language, extensions)

    @classmethod
    def get_parser(cls, filepath: Path) -> tuple["BaseParser" | None, str | None]:
        """
        Get the appropriate parser for a file.

        Args:
            filepath: Path to the file.

        Returns:
            Tuple of (parser instance, language name), or (None, None) if no parser.
        """
        suffix = filepath.suffix.lower()
        language = cls._extension_map.get(suffix)

        if language:
            return cls._parsers.get(language), language

        return None, None

    @classmethod
    def get_parser_for_language(cls, language: str) -> "BaseParser" | None:
        """
        Get parser by language name.

        Args:
            language: Language name.

        Returns:
            Parser instance or None.
        """
        return cls._parsers.get(language)

    @classmethod
    def list_languages(cls) -> list[str]:
        """Get list of registered languages."""
        return list(cls._parsers.keys())

    @classmethod
    def list_extensions(cls) -> dict[str, str]:
        """Get mapping of extensions to languages."""
        return dict(cls._extension_map)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered parsers. Useful for testing."""
        cls._parsers.clear()
        cls._extension_map.clear()


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
