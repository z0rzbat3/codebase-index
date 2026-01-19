#!/bin/bash
# Install git hooks for codebase-index

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Installing pre-commit hook..."
cp "$SCRIPT_DIR/pre-commit-hook.sh" "$REPO_ROOT/.git/hooks/pre-commit"
chmod +x "$REPO_ROOT/.git/hooks/pre-commit"

echo "Done! The index.json will be updated automatically on each commit."
