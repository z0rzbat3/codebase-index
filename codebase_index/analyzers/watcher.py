"""
File watcher for auto-regenerating documentation.

Watches for changes in source files and triggers documentation
regeneration when files are modified.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

# Check for optional watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore


class DocRegenHandler(FileSystemEventHandler if HAS_WATCHDOG else object):
    """Handler for file system events that triggers doc regeneration."""

    def __init__(
        self,
        callback: Callable[[], None],
        extensions: set[str] | None = None,
        debounce_seconds: float = 2.0,
    ) -> None:
        """
        Initialize the handler.

        Args:
            callback: Function to call when files change.
            extensions: File extensions to watch (e.g., {".py", ".ts"}).
            debounce_seconds: Minimum time between regenerations.
        """
        self.callback = callback
        self.extensions = extensions or {".py", ".ts", ".js", ".tsx", ".jsx"}
        self.debounce_seconds = debounce_seconds
        self._last_trigger = 0.0
        self._pending = False

    def on_modified(self, event: Any) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check extension
        path = Path(event.src_path)
        if path.suffix.lower() not in self.extensions:
            return

        # Skip hidden files and common non-source files
        if path.name.startswith("."):
            return
        if "__pycache__" in str(path):
            return

        # Debounce
        now = time.time()
        if now - self._last_trigger < self.debounce_seconds:
            self._pending = True
            return

        self._trigger_regeneration(path)

    def _trigger_regeneration(self, path: Path) -> None:
        """Trigger documentation regeneration."""
        self._last_trigger = time.time()
        self._pending = False

        logger.info("File changed: %s", path)
        print(f"\n[watch] File changed: {path}", flush=True)
        print("[watch] Regenerating documentation...", flush=True)

        try:
            self.callback()
            print("[watch] Done. Waiting for changes...", flush=True)
        except Exception as e:
            print(f"[watch] Error: {e}", flush=True)


def watch_and_regenerate(
    source_dir: Path,
    regenerate_callback: Callable[[], None],
    extensions: set[str] | None = None,
    verbose: bool = False,
) -> None:
    """
    Watch source directory and regenerate docs on changes.

    Args:
        source_dir: Directory to watch for changes.
        regenerate_callback: Function to call to regenerate docs.
        extensions: File extensions to watch.
        verbose: Enable verbose output.
    """
    if not HAS_WATCHDOG:
        # Fall back to simple polling
        print("[watch] watchdog not installed, using polling mode", flush=True)
        print("[watch] Install watchdog for better performance: pip install watchdog", flush=True)
        _poll_and_regenerate(source_dir, regenerate_callback, extensions, verbose)
        return

    handler = DocRegenHandler(
        callback=regenerate_callback,
        extensions=extensions,
    )

    observer = Observer()
    observer.schedule(handler, str(source_dir), recursive=True)
    observer.start()

    print(f"[watch] Watching {source_dir} for changes...", flush=True)
    print("[watch] Press Ctrl+C to stop", flush=True)

    try:
        while True:
            time.sleep(1)
            # Check for pending regenerations
            if handler._pending:
                now = time.time()
                if now - handler._last_trigger >= handler.debounce_seconds:
                    handler._trigger_regeneration(Path("multiple files"))
    except KeyboardInterrupt:
        print("\n[watch] Stopping...", flush=True)
        observer.stop()

    observer.join()


def _poll_and_regenerate(
    source_dir: Path,
    regenerate_callback: Callable[[], None],
    extensions: set[str] | None = None,
    verbose: bool = False,
    poll_interval: float = 3.0,
) -> None:
    """
    Poll-based file watching (fallback when watchdog unavailable).

    Args:
        source_dir: Directory to watch.
        regenerate_callback: Function to call on changes.
        extensions: File extensions to watch.
        verbose: Enable verbose output.
        poll_interval: Seconds between polls.
    """
    extensions = extensions or {".py", ".ts", ".js", ".tsx", ".jsx"}

    # Build initial file state
    def get_file_states() -> dict[str, float]:
        states = {}
        for ext in extensions:
            for path in source_dir.rglob(f"*{ext}"):
                if "__pycache__" in str(path):
                    continue
                if path.name.startswith("."):
                    continue
                try:
                    states[str(path)] = path.stat().st_mtime
                except (OSError, IOError):
                    pass
        return states

    last_states = get_file_states()
    print(f"[watch] Polling {source_dir} every {poll_interval}s for changes...", flush=True)
    print("[watch] Press Ctrl+C to stop", flush=True)

    try:
        while True:
            time.sleep(poll_interval)

            current_states = get_file_states()
            changed = []

            # Check for modified files
            for path, mtime in current_states.items():
                if path not in last_states or last_states[path] < mtime:
                    changed.append(path)

            # Check for new files
            for path in current_states:
                if path not in last_states:
                    changed.append(path)

            if changed:
                print(f"\n[watch] {len(changed)} file(s) changed", flush=True)
                if verbose:
                    for p in changed[:5]:
                        print(f"  - {p}", flush=True)
                    if len(changed) > 5:
                        print(f"  ... and {len(changed) - 5} more", flush=True)

                print("[watch] Regenerating documentation...", flush=True)
                try:
                    regenerate_callback()
                    print("[watch] Done. Waiting for changes...", flush=True)
                except Exception as e:
                    print(f"[watch] Error: {e}", flush=True)

                last_states = current_states

    except KeyboardInterrupt:
        print("\n[watch] Stopping...", flush=True)


def check_watchdog_available() -> bool:
    """Check if watchdog is available."""
    return HAS_WATCHDOG
