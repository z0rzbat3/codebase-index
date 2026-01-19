#!/bin/bash
# ============================================================================
# Setup Documentation Maintenance System
# ============================================================================
#
# This script sets up the automated documentation maintenance system:
#   1. Creates .doc-config.json with source-to-doc mappings
#   2. Initializes .doc-manifest.json
#   3. Installs pre-commit hook for staleness checking
#   4. Copies GitHub Action workflow
#
# Usage:
#   ./scripts/setup-doc-maintenance.sh
#
# ============================================================================

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           Documentation Maintenance Setup                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# Step 1: Check prerequisites
# ============================================================================

echo "Checking prerequisites..."

if ! command -v jq &> /dev/null; then
    echo "❌ jq is required but not installed. Install with: sudo apt install jq"
    exit 1
fi
echo "  ✅ jq installed"

if ! command -v codebase-index &> /dev/null; then
    echo "❌ codebase-index is required. Install with: pip install codebase-index[semantic]"
    exit 1
fi
echo "  ✅ codebase-index installed"

if [ ! -d ".git" ]; then
    echo "❌ Not a git repository. Run this from the repository root."
    exit 1
fi
echo "  ✅ Git repository detected"

echo ""

# ============================================================================
# Step 2: Create .doc-config.json (source-to-doc mappings)
# ============================================================================

if [ -f ".doc-config.json" ]; then
    echo "⚠️  .doc-config.json already exists, skipping..."
else
    echo "Creating .doc-config.json..."

    cat > .doc-config.json << 'EOF'
{
  "version": "2.0",
  "strategy": "mirror",
  "description": "Documentation mapping configuration for /generate-docs skill",

  "source_root": "src",
  "docs_root": "docs",
  "index_files": true,

  "mappings": [
    {
      "source": "src/api/routers",
      "docs": "docs/api/routers",
      "template": "api-endpoint",
      "extensions": [".py"]
    },
    {
      "source": "src/db/models",
      "docs": "docs/db/models",
      "template": "db-model",
      "extensions": [".py"]
    },
    {
      "source": "src/services",
      "docs": "docs/services",
      "template": "module",
      "extensions": [".py"]
    }
  ],

  "exclude": [
    "**/__pycache__/**",
    "**/__init__.py",
    "**/__main__.py",
    "**/test_*.py",
    "**/*_test.py",
    "**/node_modules/**",
    "**/dist/**",
    "**/.venv/**"
  ],

  "validation": {
    "check_references": true,
    "check_symbols": true,
    "forbidden_terms": [],
    "required_sections": ["Overview"]
  }
}
EOF
    echo ""
    echo "  ⚠️  Default config created with placeholder mappings."
    echo "  📝 Edit .doc-config.json to match YOUR project structure:"
    echo "     - Update source_root to your source directory"
    echo "     - Add mappings for each source → docs directory pair"

    echo "  ✅ Created .doc-config.json"
    echo "  📝 Edit this file to customize source-to-doc mappings"
fi

echo ""

# ============================================================================
# Step 3: Initialize .doc-manifest.json
# ============================================================================

if [ -f ".doc-manifest.json" ]; then
    echo "⚠️  .doc-manifest.json already exists, skipping..."
else
    echo "Initializing .doc-manifest.json..."

    cat > .doc-manifest.json << 'EOF'
{
  "version": "2.0",
  "strategy": "mirror",
  "last_updated": null,
  "files": {},
  "indexes": {}
}
EOF

    echo "  ✅ Created .doc-manifest.json"
    echo "  📝 Run '/generate-docs' to populate with actual hashes"
fi

echo ""

# ============================================================================
# Step 4: Install pre-commit hook
# ============================================================================

echo "Setting up pre-commit hook..."

mkdir -p .git/hooks

# Check if pre-commit hook exists
if [ -f ".git/hooks/pre-commit" ]; then
    # Check if it already has doc staleness check
    if grep -q "check_doc_staleness" .git/hooks/pre-commit; then
        echo "  ✅ Pre-commit hook already has doc staleness check"
    else
        echo "  Adding doc staleness check to existing pre-commit hook..."

        # Append the doc check to existing hook
        cat >> .git/hooks/pre-commit << 'EOF'

# ============================================================================
# Documentation Staleness Check (added by setup-doc-maintenance.sh)
# ============================================================================

check_doc_staleness() {
    if [ ! -f ".doc-manifest.json" ]; then return 0; fi
    if [ ! -f ".doc-config.json" ]; then return 0; fi
    if ! command -v jq &> /dev/null; then return 0; fi

    local STALE_COUNT=0
    local STALE_DOCS=""

    # Get source_root from config (default to "src" if not set)
    local SOURCE_ROOT=$(jq -r '.source_root // "src"' .doc-config.json)

    # Get staged source files matching the source_root
    local STAGED_SRC=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^${SOURCE_ROOT}/" || true)
    if [ -z "$STAGED_SRC" ]; then return 0; fi

    # Get tracked source files from manifest
    local TRACKED_FILES=$(jq -r '.files | keys[]' .doc-manifest.json 2>/dev/null || true)

    for src_file in $TRACKED_FILES; do
        if echo "$STAGED_SRC" | grep -q "^${src_file}$"; then
            local DOC_PATH=$(jq -r --arg src "$src_file" '.files[$src].doc_path' .doc-manifest.json)
            if [ -n "$DOC_PATH" ] && [ "$DOC_PATH" != "null" ]; then
                STALE_COUNT=$((STALE_COUNT + 1))
                STALE_DOCS="$STALE_DOCS\n  - $src_file -> $DOC_PATH"
            fi
        fi
    done

    if [ $STALE_COUNT -gt 0 ]; then
        echo ""
        echo "⚠️  DOCUMENTATION MAY BE STALE ($STALE_COUNT files affected)"
        echo -e "$STALE_DOCS"
        echo "Run: /generate-docs --incremental"
        echo ""
    fi
}

check_doc_staleness || true
EOF

        echo "  ✅ Added doc staleness check to pre-commit hook"
    fi
else
    echo "  Creating new pre-commit hook..."

    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

# ============================================================================
# Pre-commit Hook: Index Update + Doc Staleness Check
# ============================================================================

EXCLUDE_DIRS=".archive node_modules dist .git __pycache__ .pytest_cache .venv venv logs backups third-party versions"

# Update codebase index
if [ ! -f "index.json" ]; then
    echo "Building codebase index..."
    codebase-index . -o index.json --build-embeddings --exclude-dirs $EXCLUDE_DIRS 2>/dev/null || true
    git add index.json 2>/dev/null || true
else
    STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|pyw|ts|tsx|js|jsx|sql)$|docker-compose\.ya?ml$' || true)
    if [ -n "$STAGED_FILES" ]; then
        echo "Updating codebase index..."
        codebase-index --load index.json --update --build-embeddings -o index.json 2>/dev/null || true
        git add index.json 2>/dev/null || true
    fi
fi

# Doc staleness check (v2.0 mirror strategy)
check_doc_staleness() {
    if [ ! -f ".doc-manifest.json" ]; then return 0; fi
    if [ ! -f ".doc-config.json" ]; then return 0; fi
    if ! command -v jq &> /dev/null; then return 0; fi

    local STALE_COUNT=0
    local STALE_DOCS=""

    # Get source_root from config (default to "src" if not set)
    local SOURCE_ROOT=$(jq -r '.source_root // "src"' .doc-config.json)

    # Get staged source files matching the source_root
    local STAGED_SRC=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^${SOURCE_ROOT}/" || true)
    if [ -z "$STAGED_SRC" ]; then return 0; fi

    # Get tracked source files from manifest
    local TRACKED_FILES=$(jq -r '.files | keys[]' .doc-manifest.json 2>/dev/null || true)

    for src_file in $TRACKED_FILES; do
        if echo "$STAGED_SRC" | grep -q "^${src_file}$"; then
            local DOC_PATH=$(jq -r --arg src "$src_file" '.files[$src].doc_path' .doc-manifest.json)
            if [ -n "$DOC_PATH" ] && [ "$DOC_PATH" != "null" ]; then
                STALE_COUNT=$((STALE_COUNT + 1))
                STALE_DOCS="$STALE_DOCS\n  - $src_file -> $DOC_PATH"
            fi
        fi
    done

    if [ $STALE_COUNT -gt 0 ]; then
        echo ""
        echo "⚠️  DOCUMENTATION MAY BE STALE ($STALE_COUNT files affected)"
        echo -e "$STALE_DOCS"
        echo "Run: /generate-docs --incremental"
        echo ""
    fi
}

check_doc_staleness || true

exit 0
EOF

    chmod +x .git/hooks/pre-commit
    echo "  ✅ Created pre-commit hook"
fi

echo ""

# ============================================================================
# Step 5: Copy GitHub Action workflow (if not exists)
# ============================================================================

echo "Setting up GitHub Action..."

mkdir -p .github/workflows

if [ -f ".github/workflows/docs-maintenance.yml" ]; then
    echo "  ✅ docs-maintenance.yml already exists"
else
    echo "  ⚠️  Please copy docs-maintenance.yml from a template repository"
    echo "     or create it manually at .github/workflows/docs-maintenance.yml"
fi

echo ""

# ============================================================================
# Step 6: Update .gitignore
# ============================================================================

echo "Checking .gitignore..."

if [ -f ".gitignore" ]; then
    if ! grep -q ".doc-stale-flag" .gitignore; then
        echo "" >> .gitignore
        echo "# Documentation maintenance" >> .gitignore
        echo ".doc-stale-flag" >> .gitignore
        echo "  ✅ Added .doc-stale-flag to .gitignore"
    else
        echo "  ✅ .gitignore already configured"
    fi
else
    echo ".doc-stale-flag" > .gitignore
    echo "  ✅ Created .gitignore with .doc-stale-flag"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                             ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Created/Updated:                                              ║"
echo "║    - .doc-config.json (edit to customize mappings)             ║"
echo "║    - .doc-manifest.json (tracks doc state)                     ║"
echo "║    - .git/hooks/pre-commit (staleness warnings)                ║"
echo "║    - .github/workflows/docs-maintenance.yml (CI/CD)            ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Next Steps:                                                   ║"
echo "║    1. Edit .doc-config.json for your project structure         ║"
echo "║    2. Run '/generate-docs' to create initial documentation     ║"
echo "║    3. Commit the config files                                  ║"
echo "║    4. Add ANTHROPIC_API_KEY to GitHub Secrets                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
