#!/bin/bash
# Pre-commit hook: Keep index.json fresh with incremental updates
#
# Install with: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Or run: ./scripts/setup-hooks.sh

set -e

# Check if index.json exists
if [ ! -f "index.json" ]; then
    echo "index.json not found, building fresh index..."
    codebase-index . -o index.json --build-embeddings
    git add index.json
    exit 0
fi

# Check if any Python files are staged
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$STAGED_PY" ]; then
    # No Python files changed, skip update
    exit 0
fi

echo "Updating codebase index for changed files..."

# Incremental update with embeddings
codebase-index --load index.json --update --build-embeddings -o index.json 2>/dev/null

# Stage the updated index
git add index.json

echo "Index updated successfully."
