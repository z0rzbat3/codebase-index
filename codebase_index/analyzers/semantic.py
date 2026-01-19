"""
Semantic search for codebase_index.

Uses code-specific embeddings to find code by concept/description,
not just keyword matching. Embeds actual code bodies for better results.

Requires: pip install codebase-index[semantic]
  - sentence-transformers
  - numpy
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False
    np = None  # type: ignore
    SentenceTransformer = None  # type: ignore


# Available models - code-specific models work better for code search
MODELS = {
    # Code-specific models (recommended)
    "unixcoder": {
        "name": "microsoft/unixcoder-base",
        "max_tokens": 512,
        "description": "Code-specific model, good for code search",
    },
    "codebert": {
        "name": "microsoft/codebert-base",
        "max_tokens": 512,
        "description": "Code-specific model trained on code+comments",
    },
    "codet5": {
        "name": "Salesforce/codet5-base",
        "max_tokens": 512,
        "description": "Code understanding model",
    },
    # General-purpose (faster but less code-aware)
    "minilm": {
        "name": "all-MiniLM-L6-v2",
        "max_tokens": 256,
        "description": "Fast general-purpose model",
    },
}

DEFAULT_MODEL = "unixcoder"


class SemanticSearcher:
    """
    Semantic search over code using embeddings.

    Embeds actual code bodies (not just names) using code-specific models
    for better semantic matching.
    """

    def __init__(
        self,
        model_key: str = DEFAULT_MODEL,
        cache_dir: Path | None = None,
    ) -> None:
        """
        Initialize semantic searcher.

        Args:
            model_key: Model key from MODELS dict, or a HuggingFace model name.
            cache_dir: Directory to cache the model.
        """
        if not HAS_SEMANTIC:
            raise ImportError(
                "Semantic search requires sentence-transformers. "
                "Install with: pip install codebase-index[semantic]"
            )

        # Resolve model name
        if model_key in MODELS:
            model_info = MODELS[model_key]
            self.model_name = model_info["name"]
            self.max_tokens = model_info["max_tokens"]
        else:
            # Assume it's a direct HuggingFace model name
            self.model_name = model_key
            self.max_tokens = 512

        self.model_key = model_key
        self.cache_dir = cache_dir
        self._model: Any = None
        self._embeddings: Any = None
        self._symbols: list[dict[str, Any]] = []

    @property
    def model(self) -> Any:
        """Lazy-load the embedding model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(self.cache_dir) if self.cache_dir else None,
            )
            # Set max_seq_length to avoid position embedding overflow
            # (RoBERTa-based models like UniXcoder have position offset issues)
            self._model.max_seq_length = self.max_tokens
        return self._model

    def _encode_with_fallback(self, texts: list[str]) -> Any:
        """
        Encode texts with CUDA fallback to CPU on error.

        Some models (e.g., unixcoder) can have CUDA index errors on certain GPUs.
        This method catches those errors and retries on CPU.
        """
        try:
            return self.model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
        except (RuntimeError, Exception) as e:
            error_msg = str(e).lower()
            # Check for CUDA-related errors
            if "cuda" in error_msg or "device-side assert" in error_msg or "accelerator" in error_msg:
                logger.warning(
                    "CUDA error during embedding generation, falling back to CPU: %s",
                    str(e)[:100]
                )
                # Force CPU by moving model
                try:
                    self._model = self._model.to("cpu")
                    return self.model.encode(
                        texts,
                        show_progress_bar=True,
                        convert_to_numpy=True,
                    )
                except Exception as cpu_error:
                    logger.error("CPU fallback also failed: %s", cpu_error)
                    raise
            else:
                # Non-CUDA error, re-raise
                raise

    def build_embeddings(
        self,
        index_data: dict[str, Any],
        root: Path | None = None,
    ) -> dict[str, Any]:
        """
        Build embeddings for all symbols in the index.

        Args:
            index_data: The codebase index data.
            root: Root directory to read source files from.

        Returns:
            Dictionary with embeddings that can be stored in the index.
        """
        self._symbols = []
        texts = []

        # Build file content cache for code extraction
        file_contents: dict[str, list[str]] = {}
        if root:
            for file_info in index_data.get("files", []):
                file_path = root / file_info.get("path", "")
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            file_contents[file_info["path"]] = f.readlines()
                    except (OSError, IOError):
                        pass

        # Extract symbols from files
        for file_info in index_data.get("files", []):
            file_path = file_info.get("path", "")
            exports = file_info.get("exports", {})
            source_lines = file_contents.get(file_path, [])

            # File-level summary (if available)
            if file_info.get("summary"):
                file_symbol = self._create_file_symbol_info(file_info, source_lines)
                self._symbols.append(file_symbol)
                texts.append(file_symbol["text"])

            # Functions
            for func in exports.get("functions", []):
                symbol_info = self._create_symbol_info(
                    func, file_path, "function", source_lines
                )
                self._symbols.append(symbol_info)
                texts.append(symbol_info["text"])

            # Classes and methods
            for cls in exports.get("classes", []):
                symbol_info = self._create_symbol_info(
                    cls, file_path, "class", source_lines
                )
                self._symbols.append(symbol_info)
                texts.append(symbol_info["text"])

                # Class methods
                for method in cls.get("methods", []):
                    method_info = self._create_symbol_info(
                        method, file_path, "method", source_lines,
                        class_name=cls.get("name")
                    )
                    self._symbols.append(method_info)
                    texts.append(method_info["text"])

        if not texts:
            return {
                "embeddings": [],
                "symbols": [],
                "model": self.model_name,
                "model_key": self.model_key,
            }

        # Generate embeddings
        logger.info("Generating embeddings for %d symbols...", len(texts))
        embeddings = self._encode_with_fallback(texts)

        # Store as list for JSON serialization
        self._embeddings = embeddings

        return {
            "embeddings": embeddings.tolist(),
            "symbols": self._symbols,
            "model": self.model_name,
            "model_key": self.model_key,
            "count": len(self._symbols),
        }

    def _create_file_symbol_info(
        self,
        file_info: dict[str, Any],
        source_lines: list[str],
    ) -> dict[str, Any]:
        """Create file-level symbol info for embedding."""
        file_path = file_info.get("path", "")
        summary = file_info.get("summary", "")

        # Build text for embedding: file path + summary + first lines of file
        text_parts = [file_path]

        if summary:
            text_parts.append(summary)

        # Add first N lines of file for context
        if source_lines:
            preview = "".join(source_lines[:30]).strip()
            if preview:
                text_parts.append(preview)

        full_text = " ".join(text_parts)

        # Truncate to model's max length
        max_chars = self.max_tokens * 4
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars]

        return {
            "name": file_path,
            "type": "file",
            "file": file_path,
            "line": 1,
            "text": full_text,
            "summary": summary,
            "docstring": "",
            "code_preview": "".join(source_lines[:10])[:200] if source_lines else "",
        }

    def _create_symbol_info(
        self,
        symbol: dict[str, Any],
        file_path: str,
        symbol_type: str,
        source_lines: list[str],
        class_name: str | None = None,
    ) -> dict[str, Any]:
        """Create symbol info with code body for embedding."""
        name = symbol.get("name", "")
        line = symbol.get("line", 0)

        if class_name:
            full_name = f"{class_name}.{name}"
        else:
            full_name = name

        # Extract actual code body
        code_body = self._extract_code_body(source_lines, line)

        # Build text for embedding: name + summary + docstring + code body
        text_parts = [full_name]

        # Add LLM-generated summary (high value for conceptual queries)
        summary = symbol.get("summary", "")
        if summary:
            text_parts.append(summary)

        # Add docstring
        docstring = symbol.get("docstring", "")
        if docstring:
            text_parts.append(docstring[:500])  # Limit docstring length

        # Add signature info for context
        signature = symbol.get("signature", {})
        if signature:
            params = signature.get("params", [])
            param_str = ", ".join(
                f"{p.get('name', '')}: {p.get('type', '')}"
                for p in params if p.get("name")
            )
            if param_str:
                text_parts.append(f"({param_str})")

            return_type = signature.get("return_type", "")
            if return_type:
                text_parts.append(f"-> {return_type}")

        # Add actual code body (the key improvement)
        if code_body:
            text_parts.append(code_body)

        # Combine and truncate to model's max length
        full_text = " ".join(text_parts)

        # Rough token estimate: ~4 chars per token
        max_chars = self.max_tokens * 4
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars]

        return {
            "name": full_name,
            "type": symbol_type,
            "file": file_path,
            "line": line,
            "text": full_text,
            "summary": summary,  # LLM-generated summary for conceptual matching
            "docstring": docstring[:200] if docstring else "",
            "code_preview": code_body[:200] if code_body else "",
        }

    def _extract_code_body(
        self,
        lines: list[str],
        start_line: int,
        max_lines: int = 50,
    ) -> str:
        """Extract function/class body from source lines."""
        if not lines or start_line < 1:
            return ""

        start_idx = start_line - 1
        if start_idx >= len(lines):
            return ""

        # Get lines starting from definition
        end_idx = min(start_idx + max_lines, len(lines))
        code_lines = lines[start_idx:end_idx]

        if not code_lines:
            return ""

        # Find end of function (detect dedent to base level or new def/class)
        first_line = code_lines[0]
        base_indent = len(first_line) - len(first_line.lstrip())
        result_lines = [first_line]

        for line in code_lines[1:]:
            stripped = line.strip()

            # Include empty lines
            if not stripped:
                result_lines.append(line)
                continue

            current_indent = len(line) - len(line.lstrip())

            # Stop at same or lower indent with new definition
            if current_indent <= base_indent and stripped:
                if stripped.startswith(("def ", "class ", "async def ", "@")):
                    break

            result_lines.append(line)

        return "".join(result_lines).strip()

    def load_embeddings(self, embedding_data: dict[str, Any]) -> None:
        """
        Load pre-computed embeddings.

        Args:
            embedding_data: Embedding data from index.
        """
        if not HAS_SEMANTIC:
            raise ImportError(
                "Semantic search requires sentence-transformers. "
                "Install with: pip install codebase-index[semantic]"
            )

        self._symbols = embedding_data.get("symbols", [])
        embeddings_list = embedding_data.get("embeddings", [])

        if embeddings_list:
            self._embeddings = np.array(embeddings_list)
        else:
            self._embeddings = None

        # Check model compatibility
        stored_model = embedding_data.get("model", "")
        if stored_model and stored_model != self.model_name:
            logger.warning(
                "Embedding model mismatch: stored=%s, current=%s. "
                "Results may be inaccurate. Re-run --build-embeddings to fix.",
                stored_model, self.model_name
            )

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> dict[str, Any]:
        """
        Search for code matching the query.

        Args:
            query: Natural language or code query
                   (e.g., "retry logic with backoff" or "def retry")
            top_k: Number of results to return.
            min_score: Minimum similarity score (0-1).

        Returns:
            Dictionary with search results.
        """
        if self._embeddings is None or len(self._symbols) == 0:
            return {
                "query": query,
                "results": [],
                "error": "No embeddings loaded. Run with --build-embeddings first.",
            }

        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

        # Compute cosine similarities
        similarities = self._cosine_similarity(query_embedding, self._embeddings)

        # Get top results
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < min_score:
                break

            symbol = self._symbols[idx]
            # Prefer summary > docstring > code_preview for snippet
            snippet = (
                symbol.get("summary")
                or symbol.get("docstring", "")[:100]
                or symbol.get("code_preview", "")
            )
            results.append({
                "symbol": symbol["name"],
                "type": symbol["type"],
                "file": symbol["file"],
                "line": symbol["line"],
                "score": round(score, 3),
                "snippet": snippet,
            })

        return {
            "query": query,
            "results": results,
            "total_symbols": len(self._symbols),
            "model": self.model_name,
        }

    def _cosine_similarity(self, query: Any, embeddings: Any) -> Any:
        """Compute cosine similarity between query and all embeddings."""
        # Normalize
        query_norm = query / (np.linalg.norm(query) + 1e-9)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9
        embeddings_norm = embeddings / norms

        # Dot product gives cosine similarity for normalized vectors
        return np.dot(embeddings_norm, query_norm)


def build_embeddings(
    index_data: dict[str, Any],
    root: Path | None = None,
    model: str = DEFAULT_MODEL,
    changed_files: set[str] | None = None,
) -> dict[str, Any]:
    """
    Build embeddings for symbols in the index.

    Args:
        index_data: The codebase index.
        root: Root directory for reading source files.
        model: Model key or HuggingFace model name.
        changed_files: If provided, only rebuild embeddings for symbols in these files.
                       Existing embeddings for unchanged files are preserved.

    Returns:
        Updated index with embeddings.
    """
    if changed_files is not None:
        # Incremental update mode
        return _incremental_build_embeddings(index_data, root, model, changed_files)

    # Full rebuild
    searcher = SemanticSearcher(model_key=model)
    embedding_data = searcher.build_embeddings(index_data, root=root)

    # Add to index
    index_data["semantic"] = embedding_data

    return index_data


def _incremental_build_embeddings(
    index_data: dict[str, Any],
    root: Path | None,
    model: str,
    changed_files: set[str],
) -> dict[str, Any]:
    """
    Incrementally update embeddings for changed files only.

    Args:
        index_data: The codebase index.
        root: Root directory for reading source files.
        model: Model key or HuggingFace model name.
        changed_files: Set of file paths that changed (added, updated, or deleted).

    Returns:
        Updated index with embeddings.
    """
    existing_semantic = index_data.get("semantic", {})
    existing_symbols = existing_semantic.get("symbols", [])
    existing_embeddings = existing_semantic.get("embeddings", [])

    # Check model compatibility
    stored_model_key = existing_semantic.get("model_key", DEFAULT_MODEL)
    if stored_model_key != model:
        logger.warning(
            "Model changed from %s to %s. Doing full rebuild.",
            stored_model_key, model
        )
        searcher = SemanticSearcher(model_key=model)
        embedding_data = searcher.build_embeddings(index_data, root=root)
        index_data["semantic"] = embedding_data
        return index_data

    # Separate unchanged symbols from changed ones
    unchanged_symbols = []
    unchanged_embeddings = []

    for i, symbol in enumerate(existing_symbols):
        symbol_file = symbol.get("file", "")
        if symbol_file not in changed_files and i < len(existing_embeddings):
            unchanged_symbols.append(symbol)
            unchanged_embeddings.append(existing_embeddings[i])

    logger.info(
        "Incremental embedding update: keeping %d unchanged, rebuilding for %d changed files",
        len(unchanged_symbols), len(changed_files)
    )

    # Build embeddings only for symbols in changed files
    searcher = SemanticSearcher(model_key=model)

    # Create a filtered index with only changed files
    changed_files_data = {
        "files": [
            f for f in index_data.get("files", [])
            if f.get("path", "") in changed_files
        ]
    }

    if changed_files_data["files"]:
        new_embedding_data = searcher.build_embeddings(changed_files_data, root=root)
        new_symbols = new_embedding_data.get("symbols", [])
        new_embeddings = new_embedding_data.get("embeddings", [])
    else:
        new_symbols = []
        new_embeddings = []

    # Merge unchanged + new
    all_symbols = unchanged_symbols + new_symbols
    all_embeddings = unchanged_embeddings + new_embeddings

    embedding_data = {
        "embeddings": all_embeddings,
        "symbols": all_symbols,
        "model": searcher.model_name,
        "model_key": model,
        "count": len(all_symbols),
    }

    index_data["semantic"] = embedding_data

    logger.info(
        "Embedding update complete: %d total symbols (%d unchanged + %d new/updated)",
        len(all_symbols), len(unchanged_symbols), len(new_symbols)
    )

    return index_data


def semantic_search(
    index_data: dict[str, Any],
    query: str,
    top_k: int = 10,
    model: str | None = None,
    min_score: float = 0.3,
) -> dict[str, Any]:
    """
    Convenience function for semantic search.

    Args:
        index_data: Index with embeddings.
        query: Search query.
        top_k: Number of results.
        model: Model to use (should match what was used for embeddings).
        min_score: Minimum similarity score threshold (0.0-1.0). Lower = more results.

    Returns:
        Search results.
    """
    embedding_data = index_data.get("semantic", {})

    if not embedding_data:
        return {
            "query": query,
            "results": [],
            "error": "No embeddings in index. Run with --build-embeddings first.",
        }

    # Use stored model if not specified
    model_key = model or embedding_data.get("model_key", DEFAULT_MODEL)

    searcher = SemanticSearcher(model_key=model_key)
    searcher.load_embeddings(embedding_data)

    return searcher.search(query, top_k=top_k, min_score=min_score)


def check_semantic_available() -> bool:
    """Check if semantic search dependencies are available."""
    return HAS_SEMANTIC


def list_models() -> dict[str, Any]:
    """List available embedding models."""
    return MODELS
