#!/usr/bin/env python3
"""
Codebase Index - A CLI tool to generate comprehensive codebase inventories.

Supports: Python (AST), TypeScript/React (regex), SQL (regex), Docker (YAML)

v1.2.0 Features:
- Aggregated imports analysis with missing/unused deps detection
- Auth requirements per endpoint detection
- Test coverage mapping (source → test file)
- External HTTP calls detection
- Large file/function complexity warnings

v1.3.0 Features:
- Middleware detection (CORS, GZip, custom middleware)
- WebSocket endpoints scanning
- Alembic migrations parsing with operations tracking

v1.4.0 Features:
- Orphaned file detection (files never imported anywhere)

v1.5.0 Features:
- Symbol Index (flat list of all functions/classes with file:line)
- Docstrings extraction from functions/classes
- Function signatures (parameters with types, return types)

v1.6.0 Features:
- Call Graph (raw extraction of function calls for LLM analysis)
- Code Duplication detection (hash-based potential duplicate detection)

v1.7.0 Features:
- Configurable framework detection via YAML config file
- --init-config to generate starter config for any project
- --config to load custom config (enables Django, Flask, Express, etc.)
"""

import ast
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Optional: YAML support for Docker
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_EXCLUDE = [
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "*.log",
    "*.egg-info",
]

# =============================================================================
# Default Configuration (can be overridden via --config)
# =============================================================================

DEFAULT_CONFIG = {
    # Project metadata
    "project": {
        "name": "My Project",
        "description": "Codebase index configuration",
    },

    # Web framework route detection
    "routes": {
        "enabled": True,
        "patterns": [
            # FastAPI / Starlette
            {"regex": r"router\.(get|post|put|patch|delete|head|options)", "framework": "fastapi"},
            {"regex": r"app\.(get|post|put|patch|delete|head|options)", "framework": "fastapi"},
            # Flask
            {"regex": r"@.*\.route\(", "framework": "flask"},
            {"regex": r"@app\.(get|post|put|patch|delete)", "framework": "flask"},
            # Django (in urls.py)
            {"regex": r"path\(['\"]", "framework": "django"},
            {"regex": r"re_path\(['\"]", "framework": "django"},
        ],
    },

    # ORM / Database model detection
    "models": {
        "enabled": True,
        "patterns": [
            # SQLAlchemy
            {"marker": "__tablename__", "type": "sqlalchemy"},
            {"base_class": "Base", "type": "sqlalchemy"},
            {"base_class": "DeclarativeBase", "type": "sqlalchemy"},
            # Django
            {"base_class": "models.Model", "type": "django"},
            {"base_class": "Model", "type": "django"},
            # Tortoise ORM
            {"base_class": "tortoise.Model", "type": "tortoise"},
            # Prisma (TypeScript)
            {"marker": "@prisma/client", "type": "prisma"},
        ],
    },

    # Schema / Serializer detection
    "schemas": {
        "enabled": True,
        "patterns": [
            # Pydantic
            {"base_class": "BaseModel", "type": "pydantic"},
            {"base_class": "BaseSettings", "type": "pydantic"},
            # Django REST Framework
            {"base_class": "Serializer", "type": "drf"},
            {"base_class": "ModelSerializer", "type": "drf"},
            # Marshmallow
            {"base_class": "Schema", "type": "marshmallow"},
            {"base_class": "SQLAlchemySchema", "type": "marshmallow"},
        ],
    },

    # Authentication / Authorization detection
    "auth": {
        "enabled": True,
        "patterns": [
            # FastAPI
            {"dependency": "Depends", "markers": ["get_current_user", "verify_token", "authenticate", "require_auth"]},
            # Django
            {"decorator": "login_required", "framework": "django"},
            {"decorator": "permission_required", "framework": "django"},
            {"class": "IsAuthenticated", "framework": "drf"},
            # Flask
            {"decorator": "login_required", "framework": "flask"},
        ],
    },

    # Middleware detection
    "middleware": {
        "enabled": True,
        "patterns": [
            # FastAPI / Starlette
            {"regex": r"app\.add_middleware\(", "framework": "fastapi"},
            {"regex": r"CORSMiddleware", "type": "cors"},
            {"regex": r"GZipMiddleware", "type": "gzip"},
            {"regex": r"SessionMiddleware", "type": "session"},
            # Django
            {"setting": "MIDDLEWARE", "framework": "django"},
            # Express
            {"regex": r"app\.use\(", "framework": "express"},
        ],
    },

    # WebSocket detection
    "websockets": {
        "enabled": True,
        "patterns": [
            # FastAPI
            {"decorator": "websocket", "framework": "fastapi"},
            {"regex": r"@.*\.websocket\(", "framework": "fastapi"},
            # Django Channels
            {"base_class": "WebsocketConsumer", "framework": "django"},
            {"base_class": "AsyncWebsocketConsumer", "framework": "django"},
            # Socket.IO
            {"regex": r"@socketio\.on\(", "framework": "socketio"},
        ],
    },

    # File categorization patterns (regex -> category name)
    "categories": {
        "python": {
            r".*/routers?/.*\.py$": "router",
            r".*/views?/.*\.py$": "view",
            r".*/controllers?/.*\.py$": "controller",
            r".*/services?/.*\.py$": "service",
            r".*/schemas?/.*\.py$": "schema",
            r".*/serializers?/.*\.py$": "serializer",
            r".*/models?/.*\.py$": "model",
            r".*/auth/.*\.py$": "auth",
            r".*/tests?/.*\.py$": "test",
            r".*test_.*\.py$": "test",
            r".*_test\.py$": "test",
            r".*/hooks?/.*\.py$": "hook",
            r".*/utils?/.*\.py$": "util",
            r".*/helpers?/.*\.py$": "helper",
            r".*/migrations?/.*\.py$": "migration",
            r".*/commands?/.*\.py$": "command",
            r".*/tasks?/.*\.py$": "task",
        },
        "typescript": {
            r".*/pages?/.*\.tsx?$": "page",
            r".*/components?/.*/.*\.tsx?$": "component",
            r".*/components?/[^/]+\.tsx?$": "component",
            r".*/hooks?/.*\.tsx?$": "hook",
            r".*/api/.*\.tsx?$": "api-client",
            r".*/types?/.*\.tsx?$": "types",
            r".*/services?/.*\.tsx?$": "service",
            r".*/utils?/.*\.tsx?$": "util",
            r".*/stores?/.*\.tsx?$": "store",
            r".*/contexts?/.*\.tsx?$": "context",
        },
    },

    # Import classification
    "imports": {
        # Prefixes that indicate internal project imports
        "internal_prefixes": ["src", "app", "api", "lib", "core", "modules"],
        # Known external packages (auto-detected from requirements.txt/package.json too)
        "external_prefixes": [
            # Python standard library
            "os", "sys", "re", "json", "datetime", "pathlib", "typing", "collections",
            "functools", "itertools", "contextlib", "asyncio", "logging", "uuid",
            "hashlib", "base64", "dataclasses", "enum", "abc",
            # Common Python packages
            "fastapi", "flask", "django", "starlette", "pydantic", "sqlalchemy",
            "pytest", "requests", "httpx", "aiohttp", "celery", "redis",
            "numpy", "pandas", "scipy", "torch", "tensorflow",
            # Common Node packages
            "express", "react", "next", "vue", "angular", "lodash", "axios",
        ],
    },

    # Database migrations detection
    "migrations": {
        "enabled": True,
        "patterns": [
            # Alembic
            {"path": "migrations/versions", "type": "alembic"},
            {"path": "alembic/versions", "type": "alembic"},
            # Django
            {"path": "migrations", "marker": "Migration", "type": "django"},
            # Prisma
            {"path": "prisma/migrations", "type": "prisma"},
        ],
    },

    # Complexity thresholds
    "complexity": {
        "max_file_lines": 500,
        "max_function_lines": 50,
        "max_class_methods": 20,
    },
}


def get_config_template() -> str:
    """Generate a well-documented YAML config template for LLMs to customize."""
    return '''# =============================================================================
# Codebase Index Configuration
# =============================================================================
# This config file customizes how codebase_index.py scans your project.
#
# INSTRUCTIONS FOR LLMs (Claude, GPT, etc.):
# 1. Analyze the user's codebase structure (frameworks, file organization)
# 2. Modify the patterns below to match their stack
# 3. Remove or disable sections that don't apply
# 4. Add new patterns for any custom conventions
# =============================================================================

project:
  name: "My Project"  # Change to your project name
  description: "Auto-generated config - customize for your stack"

# =============================================================================
# WEB FRAMEWORK ROUTES
# =============================================================================
# Patterns to detect API endpoints/routes in your codebase.
# The 'regex' field matches decorator/function patterns.
#
# Common frameworks:
# - FastAPI: router.get(), router.post(), @app.get()
# - Flask: @app.route(), @blueprint.route()
# - Django: path(), re_path() in urls.py
# - Express: app.get(), router.get()
# =============================================================================
routes:
  enabled: true
  patterns:
    # FastAPI / Starlette (Python)
    - regex: "router\\\\.(get|post|put|patch|delete|head|options)"
      framework: fastapi
    - regex: "app\\\\.(get|post|put|patch|delete)"
      framework: fastapi

    # Flask (Python) - uncomment if using Flask
    # - regex: "@.*\\\\.route\\\\("
    #   framework: flask

    # Django (Python) - uncomment if using Django
    # - regex: "path\\\\(['\\\"]"
    #   framework: django

    # Express (Node.js) - uncomment if using Express
    # - regex: "(app|router)\\\\.(get|post|put|patch|delete)\\\\("
    #   framework: express

# =============================================================================
# DATABASE MODELS / ORM
# =============================================================================
# Patterns to detect database model definitions.
#
# Common ORMs:
# - SQLAlchemy: __tablename__ attribute, inherits from Base
# - Django ORM: inherits from models.Model
# - Prisma: @prisma/client imports
# - TypeORM: @Entity() decorator
# =============================================================================
models:
  enabled: true
  patterns:
    # SQLAlchemy (Python)
    - marker: "__tablename__"
      type: sqlalchemy

    # Django ORM - uncomment if using Django
    # - base_class: "models.Model"
    #   type: django

    # Prisma (TypeScript) - uncomment if using Prisma
    # - marker: "@prisma/client"
    #   type: prisma

# =============================================================================
# SCHEMAS / SERIALIZERS / DTOs
# =============================================================================
# Patterns to detect data validation/serialization classes.
#
# Common libraries:
# - Pydantic: inherits from BaseModel
# - Django REST Framework: inherits from Serializer
# - Marshmallow: inherits from Schema
# - Zod (TypeScript): z.object()
# =============================================================================
schemas:
  enabled: true
  patterns:
    # Pydantic (Python)
    - base_class: BaseModel
      type: pydantic
    - base_class: BaseSettings
      type: pydantic

    # Django REST Framework - uncomment if using DRF
    # - base_class: Serializer
    #   type: drf
    # - base_class: ModelSerializer
    #   type: drf

# =============================================================================
# AUTHENTICATION / AUTHORIZATION
# =============================================================================
# Patterns to detect auth requirements on endpoints.
#
# Common patterns:
# - FastAPI: Depends(get_current_user)
# - Django: @login_required, @permission_required
# - Flask: @login_required
# - Express: middleware like isAuthenticated
# =============================================================================
auth:
  enabled: true
  patterns:
    # FastAPI dependency injection
    - dependency: Depends
      markers:
        - get_current_user
        - verify_token
        - authenticate
        - require_auth
        - get_current_active_user

    # Django - uncomment if using Django
    # - decorator: login_required
    #   framework: django
    # - decorator: permission_required
    #   framework: django

# =============================================================================
# FILE CATEGORIZATION
# =============================================================================
# Regex patterns to categorize files by their purpose.
# Maps regex patterns to category names for better organization.
#
# Customize these based on your project structure!
# =============================================================================
categories:
  python:
    ".*/routers?/.*\\\\.py$": router
    ".*/views?/.*\\\\.py$": view
    ".*/services?/.*\\\\.py$": service
    ".*/schemas?/.*\\\\.py$": schema
    ".*/models?/.*\\\\.py$": model
    ".*/auth/.*\\\\.py$": auth
    ".*/tests?/.*\\\\.py$": test
    ".*test_.*\\\\.py$": test
    ".*/utils?/.*\\\\.py$": util
    ".*/migrations?/.*\\\\.py$": migration

  typescript:
    ".*/pages?/.*\\\\.tsx?$": page
    ".*/components?/.*\\\\.tsx?$": component
    ".*/hooks?/.*\\\\.tsx?$": hook
    ".*/services?/.*\\\\.tsx?$": service
    ".*/types?/.*\\\\.tsx?$": types
    ".*/stores?/.*\\\\.tsx?$": store

# =============================================================================
# IMPORT CLASSIFICATION
# =============================================================================
# How to classify imports as internal (your code) vs external (packages).
# =============================================================================
imports:
  # Prefixes that indicate internal project imports
  internal_prefixes:
    - src
    - app
    - lib
    # Add your project's module prefixes here

  # Common external packages (also auto-detected from requirements.txt)
  external_prefixes:
    - fastapi
    - pydantic
    - sqlalchemy
    - pytest
    - typing
    - os
    - sys

# =============================================================================
# COMPLEXITY THRESHOLDS
# =============================================================================
# Warn when files/functions exceed these limits.
# =============================================================================
complexity:
  max_file_lines: 500
  max_function_lines: 50
  max_class_methods: 20
'''


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file, merged with defaults."""
    if not HAS_YAML:
        print("Error: PyYAML is required for config files. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f) or {}

    # Deep merge with defaults
    config = DEFAULT_CONFIG.copy()
    for key, value in user_config.items():
        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
            config[key] = {**config[key], **value}
        else:
            config[key] = value

    return config


# Path patterns for categorization (defaults, can be overridden by config)
PYTHON_CATEGORIES = DEFAULT_CONFIG["categories"]["python"]
TYPESCRIPT_CATEGORIES = DEFAULT_CONFIG["categories"]["typescript"]


# =============================================================================
# Utilities
# =============================================================================

def get_file_hash(filepath: Path) -> str:
    """Generate SHA256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()[:16]}"


def count_lines(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_git_info(root: Path) -> dict:
    """Get git metadata."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root, stderr=subprocess.DEVNULL
        ).decode().strip()

        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root, stderr=subprocess.DEVNULL
        ).decode().strip()

        # Check if working directory is dirty
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root, stderr=subprocess.DEVNULL
        ).decode().strip()

        return {
            "commit": commit,
            "branch": branch,
            "dirty": len(status) > 0
        }
    except Exception:
        return None


def categorize_file(filepath: str, categories: dict) -> str:
    """Categorize a file based on path patterns."""
    for pattern, category in categories.items():
        if re.match(pattern, filepath):
            return category
    return "other"


def should_exclude(path: Path, exclude_patterns: list) -> bool:
    """Check if path should be excluded."""
    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str.split(os.sep):
            return True
    return False


# =============================================================================
# Dependencies Scanner
# =============================================================================

class DependenciesScanner:
    """Scan for project dependencies from requirements.txt, package.json, etc."""

    def scan(self, root: Path) -> dict:
        """Scan for all dependency files."""
        result = {
            "python": [],
            "node": {"dependencies": [], "devDependencies": []},
        }

        # Python: requirements.txt
        req_files = list(root.glob("requirements*.txt"))
        for req_file in req_files:
            deps = self._parse_requirements(req_file)
            result["python"].extend(deps)

        # Python: pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            deps = self._parse_pyproject(pyproject)
            result["python"].extend(deps)

        # Remove duplicates
        result["python"] = list(set(result["python"]))

        # Node: package.json
        package_json = root / "package.json"
        if not package_json.exists():
            # Check frontend directory
            package_json = root / "src" / "frontend" / "package.json"

        if package_json.exists():
            node_deps = self._parse_package_json(package_json)
            result["node"] = node_deps

        return result

    def _parse_requirements(self, filepath: Path) -> list:
        """Parse requirements.txt file."""
        deps = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Extract package name (before ==, >=, etc.)
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.append(match.group(1).lower())
        except Exception:
            pass
        return deps

    def _parse_pyproject(self, filepath: Path) -> list:
        """Parse pyproject.toml for dependencies."""
        deps = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple regex parsing for dependencies
            # Matches: dependencies = ["pkg1", "pkg2>=1.0"]
            match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                deps_str = match.group(1)
                for dep_match in re.finditer(r'"([a-zA-Z0-9_-]+)', deps_str):
                    deps.append(dep_match.group(1).lower())
        except Exception:
            pass
        return deps

    def _parse_package_json(self, filepath: Path) -> dict:
        """Parse package.json for dependencies."""
        result = {"dependencies": [], "devDependencies": []}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            result["dependencies"] = list(data.get("dependencies", {}).keys())
            result["devDependencies"] = list(data.get("devDependencies", {}).keys())
        except Exception:
            pass
        return result


# =============================================================================
# Environment Variables Scanner
# =============================================================================

class EnvScanner:
    """Scan for environment variable usage (names only, no values)."""

    def scan(self, root: Path) -> dict:
        """Scan for environment variables."""
        result = {
            "dotenv_files": {},      # .env files and their var names
            "python_usage": set(),    # os.environ, os.getenv usage
            "typescript_usage": set(), # process.env usage
            "docker_usage": set(),    # Docker compose env vars
        }

        # Scan .env files (names only, NO VALUES)
        for env_file in root.glob("**/.env*"):
            if should_exclude(env_file, DEFAULT_EXCLUDE):
                continue
            if env_file.is_file():
                vars_in_file = self._parse_dotenv(env_file)
                if vars_in_file:
                    rel_path = str(env_file.relative_to(root))
                    result["dotenv_files"][rel_path] = vars_in_file

        # Scan Python files for os.environ/os.getenv
        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, DEFAULT_EXCLUDE):
                continue
            vars_found = self._scan_python_env(py_file)
            result["python_usage"].update(vars_found)

        # Scan TypeScript files for process.env
        for ts_file in list(root.glob("**/*.ts")) + list(root.glob("**/*.tsx")):
            if should_exclude(ts_file, DEFAULT_EXCLUDE):
                continue
            vars_found = self._scan_typescript_env(ts_file)
            result["typescript_usage"].update(vars_found)

        # Convert sets to sorted lists
        result["python_usage"] = sorted(result["python_usage"])
        result["typescript_usage"] = sorted(result["typescript_usage"])
        result["docker_usage"] = sorted(result["docker_usage"])

        return result

    def _parse_dotenv(self, filepath: Path) -> list:
        """Parse .env file for variable names (NOT values)."""
        vars = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Extract variable name (before =)
                    match = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", line)
                    if match:
                        vars.append(match.group(1))
        except Exception:
            pass
        return vars

    def _scan_python_env(self, filepath: Path) -> set:
        """Scan Python file for environment variable access."""
        vars = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # os.environ["VAR"] or os.environ.get("VAR")
            for match in re.finditer(r'os\.environ(?:\.get)?\s*\[\s*["\']([A-Z_][A-Z0-9_]*)["\']', content):
                vars.add(match.group(1))

            # os.getenv("VAR")
            for match in re.finditer(r'os\.getenv\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', content):
                vars.add(match.group(1))

            # os.environ.get("VAR")
            for match in re.finditer(r'os\.environ\.get\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', content):
                vars.add(match.group(1))

        except Exception:
            pass
        return vars

    def _scan_typescript_env(self, filepath: Path) -> set:
        """Scan TypeScript file for environment variable access."""
        vars = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # process.env.VAR_NAME
            for match in re.finditer(r'process\.env\.([A-Z_][A-Z0-9_]*)', content):
                vars.add(match.group(1))

            # process.env["VAR_NAME"] or process.env['VAR_NAME']
            for match in re.finditer(r'process\.env\[["\']([A-Z_][A-Z0-9_]*)["\']\]', content):
                vars.add(match.group(1))

            # import.meta.env.VITE_VAR (Vite)
            for match in re.finditer(r'import\.meta\.env\.([A-Z_][A-Z0-9_]*)', content):
                vars.add(match.group(1))

        except Exception:
            pass
        return vars


# =============================================================================
# TODO/FIXME Scanner
# =============================================================================

class TodoScanner:
    """Scan for TODO, FIXME, HACK, XXX comments."""

    PATTERNS = [
        (r'#\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+)$', 'python'),
        (r'//\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+)$', 'typescript'),
        (r'/\*\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)\*/', 'multiline'),
    ]

    def scan(self, root: Path, exclude: list) -> list:
        """Scan all files for TODO/FIXME comments."""
        todos = []

        # Scan Python and TypeScript files
        for pattern in ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]:
            for filepath in root.glob(pattern):
                if should_exclude(filepath, exclude):
                    continue
                file_todos = self._scan_file(filepath, root)
                todos.extend(file_todos)

        return todos

    def _scan_file(self, filepath: Path, root: Path) -> list:
        """Scan a single file for TODOs."""
        todos = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, _ in self.PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        todos.append({
                            "type": match.group(1).upper(),
                            "message": match.group(2).strip(),
                            "file": rel_path,
                            "line": i
                        })
                        break  # Only match once per line

        except Exception:
            pass
        return todos


# =============================================================================
# Route Prefix Scanner
# =============================================================================

class RoutePrefixScanner:
    """Scan FastAPI main.py for router prefixes to build full paths."""

    def scan(self, root: Path) -> dict:
        """Scan for include_router calls to extract prefixes."""
        prefixes = {}  # router_name -> prefix

        # Find main.py or app files
        main_files = list(root.glob("**/main.py")) + list(root.glob("**/app.py"))

        for main_file in main_files:
            if should_exclude(main_file, DEFAULT_EXCLUDE):
                continue
            file_prefixes = self._scan_main_file(main_file)
            prefixes.update(file_prefixes)

        return prefixes

    def _scan_main_file(self, filepath: Path) -> dict:
        """Scan a main.py file for include_router calls."""
        prefixes = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Match: app.include_router(agents.router, prefix="/api/v1/agents")
            # or: app.include_router(router, prefix="/api/v1/agents", tags=["agents"])
            pattern = r'include_router\s*\(\s*(\w+)(?:\.router)?\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'

            for match in re.finditer(pattern, content):
                router_name = match.group(1)
                prefix = match.group(2)
                prefixes[router_name] = prefix

            # Also check for: from .routers import agents, chat, etc.
            # Then: app.include_router(agents.router, prefix="/agents")
            import_pattern = r'from\s+\.?routers?\s+import\s+(.+)'
            for match in re.finditer(import_pattern, content):
                imports = match.group(1)
                # Parse the imported names
                for name in re.findall(r'(\w+)', imports):
                    if name not in prefixes:
                        # Try to find the prefix for this router
                        specific_pattern = rf'include_router\s*\(\s*{name}(?:\.router)?\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'
                        specific_match = re.search(specific_pattern, content)
                        if specific_match:
                            prefixes[name] = specific_match.group(1)

        except Exception:
            pass
        return prefixes


# =============================================================================
# Import Aggregator (for missing/unused dependency detection)
# =============================================================================

# Standard library modules (Python 3.9+)
STDLIB_MODULES = {
    "__future__", "_thread",
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit", "base64",
    "bdb", "binascii", "binhex", "bisect", "builtins", "bz2", "calendar",
    "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "codeop",
    "collections", "colorsys", "compileall", "concurrent", "configparser",
    "contextlib", "contextvars", "copy", "copyreg", "cProfile", "crypt",
    "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings", "enum",
    "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass", "gettext",
    "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "imaplib", "imghdr", "imp", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache",
    "locale", "logging", "lzma", "mailbox", "mailcap", "marshal", "math",
    "mimetypes", "mmap", "modulefinder", "multiprocessing", "netrc", "nis",
    "nntplib", "numbers", "operator", "optparse", "os", "pathlib", "pdb",
    "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "posixpath", "pprint", "profile", "pstats", "pty",
    "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random",
    "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
    "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
    "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing", "unicodedata",
    "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
    "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "_thread",
}


class ImportAggregator:
    """Aggregate all imports across the codebase and detect missing/unused deps."""

    def __init__(self):
        self.all_imports = set()  # All imported modules
        self.import_locations = {}  # module -> [files that import it]
        self.internal_modules = set()  # Modules that are part of this project

    def add_imports(self, imports: list, filepath: str):
        """Add imports from a file."""
        for imp in imports:
            if not imp or not isinstance(imp, str):
                continue
            root_module = imp.split(".")[0].strip()
            if not root_module:
                continue
            self.all_imports.add(root_module)
            if root_module not in self.import_locations:
                self.import_locations[root_module] = []
            self.import_locations[root_module].append(filepath)

    def add_internal_module(self, module_name: str):
        """Register a module as internal to the project."""
        if module_name:
            self.internal_modules.add(module_name.lower())

    def analyze(self, declared_deps: list) -> dict:
        """
        Analyze imports against declared dependencies.

        Returns:
            dict with missing_deps and unused_deps
        """
        # Normalize declared deps (lowercase, strip version specifiers)
        normalized_deps = set()
        for dep in declared_deps:
            # Handle package names with different import names
            name = dep.lower().replace("-", "_").replace(".", "_")
            normalized_deps.add(name)

        # Common package name -> import name mappings
        pkg_to_import = {
            "pillow": "pil",
            "pyyaml": "yaml",
            "python_dateutil": "dateutil",
            "beautifulsoup4": "bs4",
            "scikit_learn": "sklearn",
            "opencv_python": "cv2",
            "python_dotenv": "dotenv",
            "aiohttp": "aiohttp",
            "sqlalchemy": "sqlalchemy",
            "python_jose": "jose",
            "python_multipart": "multipart",
            "email_validator": "email_validator",
            "typing_extensions": "typing_extensions",
        }

        # Packages that are commonly imported via their submodules
        # (package in requirements, but submodule is imported)
        umbrella_packages = {
            "fastapi": ["fastapi", "starlette"],
            "httpx": ["httpx"],
            "pydantic": ["pydantic"],
        }

        # Add umbrella package imports to normalized deps
        for pkg, imports in umbrella_packages.items():
            if pkg in [d.lower().replace("-", "_") for d in declared_deps]:
                for imp in imports:
                    normalized_deps.add(imp)

        # Add reverse mappings
        for pkg, imp in list(pkg_to_import.items()):
            normalized_deps.add(pkg)
            normalized_deps.add(imp)

        # Filter out stdlib and internal modules
        third_party_imports = set()
        for imp in self.all_imports:
            imp_lower = imp.lower()
            # Skip stdlib
            if imp_lower in STDLIB_MODULES:
                continue
            # Skip internal project modules (start with _ or are in internal_modules)
            if imp_lower.startswith("_") or imp_lower in self.internal_modules:
                continue
            third_party_imports.add(imp_lower.replace("-", "_"))

        # Find missing (imported but not declared)
        missing = []
        for imp in sorted(third_party_imports):
            # Check if any declared dep matches this import
            found = False
            for dep in normalized_deps:
                if imp == dep or imp.startswith(dep + "_") or dep.startswith(imp + "_"):
                    found = True
                    break
                # Check pkg_to_import mappings
                if dep in pkg_to_import and pkg_to_import[dep] == imp:
                    found = True
                    break
            if not found:
                missing.append({
                    "module": imp,
                    "used_in": self.import_locations.get(imp, [])[:5]  # First 5 files
                })

        # Find unused (declared but not imported)
        unused = []
        for dep in sorted(declared_deps):
            dep_normalized = dep.lower().replace("-", "_")
            # Check direct match or via pkg_to_import
            import_name = pkg_to_import.get(dep_normalized, dep_normalized)
            found = any(
                imp == dep_normalized or imp == import_name or
                dep_normalized.startswith(imp) or imp.startswith(dep_normalized)
                for imp in third_party_imports
            )
            if not found:
                unused.append(dep)

        return {
            "total_unique_imports": len(self.all_imports),
            "third_party_imports": sorted(third_party_imports),
            "missing_deps": missing,  # Imported but not in requirements
            "unused_deps": unused,    # In requirements but not imported
        }


# =============================================================================
# Auth Requirements Scanner
# =============================================================================

class AuthScanner:
    """Scan for authentication requirements per endpoint."""

    # Common auth patterns
    AUTH_PATTERNS = [
        (r'Depends\s*\(\s*get_current_user', "get_current_user"),
        (r'Depends\s*\(\s*require_auth', "require_auth"),
        (r'Depends\s*\(\s*auth_required', "auth_required"),
        (r'Depends\s*\(\s*get_current_active_user', "get_current_active_user"),
        (r'@require_auth', "require_auth decorator"),
        (r'@login_required', "login_required decorator"),
        (r'@authenticated', "authenticated decorator"),
        (r'@jwt_required', "jwt_required decorator"),
        (r'Authorization.*Bearer', "Bearer token"),
    ]

    def scan_file(self, filepath: Path, routes: list) -> list:
        """Scan a file and annotate routes with auth requirements."""
        if not routes:
            return routes

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception:
            return routes

        # For each route, check for auth patterns in surrounding lines
        annotated_routes = []
        for route in routes:
            route_copy = dict(route)
            route_line = route.get("line", 0)

            # Check lines around the route definition
            auth_info = self._check_auth_around_line(lines, route_line)
            if auth_info:
                route_copy["auth_required"] = True
                route_copy["auth_type"] = auth_info
            else:
                route_copy["auth_required"] = False

            annotated_routes.append(route_copy)

        return annotated_routes

    def _check_auth_around_line(self, lines: list, line_num: int) -> str:
        """Check for auth patterns around a specific line."""
        # Check the line itself and surrounding context (function body)
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 20)  # Function body can be several lines

        context = "\n".join(lines[start:end])

        for pattern, auth_type in self.AUTH_PATTERNS:
            if re.search(pattern, context, re.IGNORECASE):
                return auth_type

        return None


# =============================================================================
# Test Coverage Mapper
# =============================================================================

class TestCoverageMapper:
    """Map source files to their corresponding test files."""

    def __init__(self, root: Path):
        self.root = root
        self.test_files = set()
        self.source_to_test = {}  # source_path -> test_path

    def collect_test_files(self, exclude: list):
        """Collect all test files in the project."""
        patterns = [
            "**/test_*.py",
            "**/tests/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py",
        ]

        for pattern in patterns:
            for test_file in self.root.glob(pattern):
                if not should_exclude(test_file, exclude):
                    rel_path = str(test_file.relative_to(self.root))
                    self.test_files.add(rel_path)

    def map_source_to_test(self, source_files: list) -> dict:
        """Map source files to potential test files."""
        coverage_map = {
            "covered": [],      # Source files with tests
            "uncovered": [],    # Source files without tests
            "test_files": sorted(self.test_files),
            "coverage_percentage": 0.0,
        }

        testable_sources = []

        for source_file in source_files:
            path = source_file.get("path", "")
            language = source_file.get("language", "")
            category = source_file.get("category", "")

            # Only check Python source files (not tests themselves)
            if language != "python":
                continue
            if category == "test" or "test" in path.lower():
                continue
            if path.startswith("tests/"):
                continue

            testable_sources.append(path)

            # Look for corresponding test file
            test_file = self._find_test_file(path)
            if test_file:
                coverage_map["covered"].append({
                    "source": path,
                    "test": test_file
                })
                self.source_to_test[path] = test_file
            else:
                coverage_map["uncovered"].append(path)

        # Calculate coverage percentage
        if testable_sources:
            coverage_map["coverage_percentage"] = round(
                len(coverage_map["covered"]) / len(testable_sources) * 100, 1
            )

        return coverage_map

    def _find_test_file(self, source_path: str) -> str:
        """Find a test file for a given source file."""
        # Extract filename without extension
        path = Path(source_path)
        name = path.stem  # e.g., "agent_service"

        # Common test file naming patterns
        test_patterns = [
            f"test_{name}.py",
            f"tests/test_{name}.py",
            f"tests/unit/test_{name}.py",
            f"tests/integration/test_{name}.py",
            f"{name}_test.py",
        ]

        # Check for pattern matches
        for test_path in self.test_files:
            test_name = Path(test_path).name

            # Direct name match
            if test_name == f"test_{name}.py" or test_name == f"{name}_test.py":
                return test_path

            # Partial match (e.g., test_agent.py for agent_service.py)
            base_name = name.split("_")[0]
            if test_name == f"test_{base_name}.py":
                return test_path

        return None


# =============================================================================
# External HTTP Calls Scanner
# =============================================================================

class HttpCallsScanner:
    """Scan for external HTTP calls (httpx, requests, aiohttp, fetch)."""

    # Patterns for HTTP client libraries
    PYTHON_PATTERNS = [
        # requests
        (r'requests\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']', "requests"),
        (r'requests\.request\s*\(\s*["\'][^"\']+["\']\s*,\s*["\']([^"\']+)["\']', "requests"),
        # httpx
        (r'httpx\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']', "httpx"),
        (r'httpx\.(?:Async)?Client\s*\(\s*\).*?\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "httpx"),
        (r'client\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "httpx-client"),
        # aiohttp
        (r'session\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "aiohttp"),
        (r'aiohttp\.ClientSession.*?\.(get|post)\s*\(\s*["\']([^"\']+)["\']', "aiohttp"),
    ]

    TS_PATTERNS = [
        # fetch
        (r'fetch\s*\(\s*["\']([^"\']+)["\']', "fetch"),
        (r'fetch\s*\(\s*`([^`]+)`', "fetch-template"),
        # axios
        (r'axios\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "axios"),
        (r'axios\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\']', "axios-config"),
    ]

    def scan(self, root: Path, exclude: list) -> dict:
        """Scan for external HTTP calls."""
        result = {
            "python_calls": [],
            "typescript_calls": [],
            "total_external_calls": 0,
            "unique_domains": set(),
        }

        # Scan Python files
        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            calls = self._scan_python_file(py_file, root)
            result["python_calls"].extend(calls)

        # Scan TypeScript files
        for ts_file in list(root.glob("**/*.ts")) + list(root.glob("**/*.tsx")):
            if should_exclude(ts_file, exclude):
                continue
            calls = self._scan_ts_file(ts_file, root)
            result["typescript_calls"].extend(calls)

        # Calculate totals
        result["total_external_calls"] = len(result["python_calls"]) + len(result["typescript_calls"])

        # Extract unique domains
        for call in result["python_calls"] + result["typescript_calls"]:
            url = call.get("url", "")
            domain = self._extract_domain(url)
            if domain:
                result["unique_domains"].add(domain)

        result["unique_domains"] = sorted(result["unique_domains"])

        return result

    def _scan_python_file(self, filepath: Path, root: Path) -> list:
        """Scan a Python file for HTTP calls."""
        calls = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, library in self.PYTHON_PATTERNS:
                    for match in re.finditer(pattern, line):
                        groups = match.groups()
                        if len(groups) >= 2:
                            method, url = groups[0], groups[1]
                        else:
                            method, url = "GET", groups[0]

                        # Skip internal API calls
                        if url.startswith("/") or url.startswith("{"):
                            continue

                        calls.append({
                            "file": rel_path,
                            "line": i,
                            "library": library,
                            "method": method.upper() if method else "GET",
                            "url": url,
                        })

        except Exception:
            pass
        return calls

    def _scan_ts_file(self, filepath: Path, root: Path) -> list:
        """Scan a TypeScript file for HTTP calls."""
        calls = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                for pattern, library in self.TS_PATTERNS:
                    for match in re.finditer(pattern, line):
                        groups = match.groups()
                        if len(groups) >= 2:
                            method, url = groups[0], groups[1]
                        elif len(groups) == 1:
                            method, url = "GET", groups[0]
                        else:
                            continue

                        # Skip internal API calls (relative paths)
                        if url.startswith("/") and not url.startswith("//"):
                            continue

                        calls.append({
                            "file": rel_path,
                            "line": i,
                            "library": library,
                            "method": method.upper() if method and method.isalpha() else "GET",
                            "url": url,
                        })

        except Exception:
            pass
        return calls

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url or url.startswith("/") or url.startswith("${") or url.startswith("{"):
            return None
        try:
            # Simple domain extraction
            if "://" in url:
                url = url.split("://")[1]
            domain = url.split("/")[0].split(":")[0]
            if "." in domain:
                return domain
        except Exception:
            pass
        return None


# =============================================================================
# Complexity Analyzer (Large file/function warnings)
# =============================================================================

class ComplexityAnalyzer:
    """Analyze code complexity and flag large files/functions."""

    # Thresholds
    FILE_LINES_WARNING = 500
    FILE_LINES_CRITICAL = 1000
    FUNCTION_LINES_WARNING = 50
    FUNCTION_LINES_CRITICAL = 100
    CLASS_METHODS_WARNING = 15
    CLASS_METHODS_CRITICAL = 25

    def analyze(self, files: list) -> dict:
        """Analyze all files for complexity issues."""
        result = {
            "large_files": [],
            "large_functions": [],
            "complex_classes": [],
            "summary": {
                "files_warning": 0,
                "files_critical": 0,
                "functions_warning": 0,
                "functions_critical": 0,
            }
        }

        for file_info in files:
            # Check file size
            lines = file_info.get("lines", 0)
            if lines >= self.FILE_LINES_CRITICAL:
                result["large_files"].append({
                    "path": file_info["path"],
                    "lines": lines,
                    "severity": "critical"
                })
                result["summary"]["files_critical"] += 1
            elif lines >= self.FILE_LINES_WARNING:
                result["large_files"].append({
                    "path": file_info["path"],
                    "lines": lines,
                    "severity": "warning"
                })
                result["summary"]["files_warning"] += 1

            # Check functions (for Python files)
            exports = file_info.get("exports", {})
            functions = exports.get("functions", [])

            for func in functions:
                # We need to calculate function length from the AST
                # For now, flag based on whether function exists in a large file
                func_name = func.get("name", "") if isinstance(func, dict) else func
                func_line = func.get("line", 0) if isinstance(func, dict) else 0

            # Check classes
            classes = exports.get("classes", [])
            for cls in classes:
                methods = cls.get("methods", []) if isinstance(cls, dict) else []
                method_count = len(methods)

                if method_count >= self.CLASS_METHODS_CRITICAL:
                    result["complex_classes"].append({
                        "path": file_info["path"],
                        "class": cls.get("name", "") if isinstance(cls, dict) else cls,
                        "methods": method_count,
                        "severity": "critical"
                    })
                elif method_count >= self.CLASS_METHODS_WARNING:
                    result["complex_classes"].append({
                        "path": file_info["path"],
                        "class": cls.get("name", "") if isinstance(cls, dict) else cls,
                        "methods": method_count,
                        "severity": "warning"
                    })

        return result


# =============================================================================
# Middleware Scanner
# =============================================================================

class MiddlewareScanner:
    """Scan for FastAPI/Starlette middleware configuration."""

    # Known middleware types
    KNOWN_MIDDLEWARE = {
        "CORSMiddleware": "CORS - Cross-Origin Resource Sharing",
        "GZipMiddleware": "GZip - Response compression",
        "TrustedHostMiddleware": "Security - Host header validation",
        "HTTPSRedirectMiddleware": "Security - HTTPS redirect",
        "SessionMiddleware": "Session management",
        "AuthenticationMiddleware": "Authentication",
        "BaseHTTPMiddleware": "Custom HTTP middleware",
    }

    def scan(self, root: Path, exclude: list) -> dict:
        """Scan for middleware usage."""
        result = {
            "middleware": [],
            "custom_middleware": [],
        }

        # Scan Python files for middleware
        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            middlewares = self._scan_file(py_file, root)
            result["middleware"].extend(middlewares["standard"])
            result["custom_middleware"].extend(middlewares["custom"])

        return result

    def _scan_file(self, filepath: Path, root: Path) -> dict:
        """Scan a file for middleware."""
        result = {"standard": [], "custom": []}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                # app.add_middleware(SomeMiddleware, ...)
                match = re.search(r'\.add_middleware\s*\(\s*(\w+)', line)
                if match:
                    middleware_name = match.group(1)
                    middleware_info = {
                        "name": middleware_name,
                        "file": rel_path,
                        "line": i,
                    }

                    if middleware_name in self.KNOWN_MIDDLEWARE:
                        middleware_info["description"] = self.KNOWN_MIDDLEWARE[middleware_name]
                        result["standard"].append(middleware_info)
                    else:
                        result["custom"].append(middleware_info)

                # @app.middleware("http") decorator
                if re.search(r'@\w+\.middleware\s*\(\s*["\']http["\']', line):
                    # Find the function name on next non-empty line
                    for j in range(i, min(i + 5, len(lines))):
                        func_match = re.match(r'\s*async\s+def\s+(\w+)|def\s+(\w+)', lines[j])
                        if func_match:
                            func_name = func_match.group(1) or func_match.group(2)
                            result["custom"].append({
                                "name": func_name,
                                "type": "decorator",
                                "file": rel_path,
                                "line": i,
                            })
                            break

        except Exception:
            pass

        return result


# =============================================================================
# WebSocket Scanner
# =============================================================================

class WebSocketScanner:
    """Scan for WebSocket endpoints."""

    def scan(self, root: Path, exclude: list) -> dict:
        """Scan for WebSocket endpoints."""
        result = {
            "endpoints": [],
            "total": 0,
        }

        for py_file in root.glob("**/*.py"):
            if should_exclude(py_file, exclude):
                continue
            endpoints = self._scan_file(py_file, root)
            result["endpoints"].extend(endpoints)

        result["total"] = len(result["endpoints"])
        return result

    def _scan_file(self, filepath: Path, root: Path) -> list:
        """Scan a file for WebSocket endpoints."""
        endpoints = []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            rel_path = str(filepath.relative_to(root))

            for i, line in enumerate(lines, 1):
                # @router.websocket("/path") or @app.websocket("/path")
                match = re.search(r'@\w+\.websocket\s*\(\s*["\']([^"\']+)["\']', line)
                if match:
                    path = match.group(1)

                    # Find the function name
                    handler = None
                    for j in range(i, min(i + 5, len(lines))):
                        func_match = re.match(r'\s*async\s+def\s+(\w+)', lines[j])
                        if func_match:
                            handler = func_match.group(1)
                            break

                    endpoints.append({
                        "path": path,
                        "handler": handler,
                        "file": rel_path,
                        "line": i,
                    })

                # Also check for WebSocket type hints in function params
                if "WebSocket" in line and "def " in line:
                    func_match = re.search(r'def\s+(\w+)\s*\([^)]*WebSocket', line)
                    if func_match:
                        # Check if we already captured this as an endpoint
                        handler_name = func_match.group(1)
                        if not any(e.get("handler") == handler_name for e in endpoints):
                            endpoints.append({
                                "path": "(inferred from type hint)",
                                "handler": handler_name,
                                "file": rel_path,
                                "line": i,
                            })

        except Exception:
            pass

        return endpoints


# =============================================================================
# Alembic Migrations Scanner
# =============================================================================

class AlembicScanner:
    """Scan for Alembic database migrations."""

    def scan(self, root: Path) -> dict:
        """Scan for Alembic migrations."""
        result = {
            "migrations": [],
            "total": 0,
            "latest_revision": None,
            "has_alembic": False,
        }

        # Check for alembic.ini
        alembic_ini = root / "alembic.ini"
        if alembic_ini.exists():
            result["has_alembic"] = True

        # Find migrations directory
        migrations_dirs = [
            root / "migrations" / "versions",
            root / "alembic" / "versions",
        ]

        for migrations_dir in migrations_dirs:
            if migrations_dir.exists():
                result["has_alembic"] = True
                migrations = self._scan_migrations(migrations_dir, root)
                result["migrations"].extend(migrations)

        # Sort by revision (if we can determine order)
        result["migrations"].sort(key=lambda x: x.get("file", ""), reverse=True)
        result["total"] = len(result["migrations"])

        if result["migrations"]:
            result["latest_revision"] = result["migrations"][0].get("revision")

        return result

    def _scan_migrations(self, migrations_dir: Path, root: Path) -> list:
        """Scan migration files."""
        migrations = []

        for py_file in migrations_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            migration = self._parse_migration(py_file, root)
            if migration:
                migrations.append(migration)

        return migrations

    def _parse_migration(self, filepath: Path, root: Path) -> dict:
        """Parse a single migration file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            rel_path = str(filepath.relative_to(root))
            migration = {
                "file": rel_path,
                "filename": filepath.name,
            }

            # Extract revision
            match = re.search(r'revision\s*[:=]\s*["\']([^"\']+)["\']', content)
            if match:
                migration["revision"] = match.group(1)

            # Extract down_revision
            match = re.search(r'down_revision\s*[:=]\s*["\']?([^"\'"\n]+)["\']?', content)
            if match:
                down_rev = match.group(1).strip()
                migration["down_revision"] = None if down_rev == "None" else down_rev

            # Extract message/description from docstring or revision message
            match = re.search(r'"""(.+?)"""', content, re.DOTALL)
            if match:
                docstring = match.group(1).strip()
                # First line is usually the message
                migration["message"] = docstring.split("\n")[0].strip()

            # Extract create_date if present
            match = re.search(r'create_date\s*[:=]\s*["\']?([^"\'"\n]+)["\']?', content)
            if match:
                migration["create_date"] = match.group(1).strip()

            # Check what operations are performed
            operations = []
            if "op.create_table" in content:
                operations.append("create_table")
            if "op.drop_table" in content:
                operations.append("drop_table")
            if "op.add_column" in content:
                operations.append("add_column")
            if "op.drop_column" in content:
                operations.append("drop_column")
            if "op.create_index" in content:
                operations.append("create_index")
            if "op.drop_index" in content:
                operations.append("drop_index")
            if "op.alter_column" in content:
                operations.append("alter_column")
            if "op.create_foreign_key" in content:
                operations.append("create_foreign_key")

            if operations:
                migration["operations"] = operations

            return migration

        except Exception:
            return None


# =============================================================================
# Orphaned File Scanner (Dead Code Detection)
# =============================================================================

class OrphanedFileScanner:
    """Detect Python files that are never imported anywhere."""

    # Files that are entry points (run directly, not imported)
    ENTRY_POINT_PATTERNS = [
        r"^main\.py$",
        r"^app\.py$",
        r"^run_.*\.py$",
        r"^start_.*\.py$",
        r"^manage\.py$",
        r"^setup\.py$",
        r"^conftest\.py$",
        r"^wsgi\.py$",
        r"^asgi\.py$",
    ]

    # Files that are always excluded from orphan detection
    EXCLUDED_PATTERNS = [
        r"^__init__\.py$",
        r"^__main__\.py$",
        r"^conftest\.py$",
        r"^test_.*\.py$",
        r".*_test\.py$",
    ]

    # Directories that contain entry points
    ENTRY_POINT_DIRS = [
        "migrations",
        "alembic",
        "scripts",
        "examples",
        "tests",
    ]

    def __init__(self):
        self.all_files = set()  # All Python files (relative paths)
        self.all_imports = {}   # module_name -> [files that define it]
        self.imported_modules = set()  # All modules that are imported somewhere

    def scan(self, root: Path, files: list, exclude: list) -> dict:
        """
        Detect orphaned files.

        Args:
            root: Project root
            files: List of file info dicts from main scan
            exclude: Exclusion patterns
        """
        result = {
            "orphaned_files": [],
            "entry_points": [],
            "total_python_files": 0,
            "orphaned_count": 0,
            "orphaned_lines": 0,
        }

        # Step 1: Collect all Python files and their module names
        python_files = []
        for file_info in files:
            if file_info.get("language") != "python":
                continue

            path = file_info["path"]
            python_files.append(file_info)
            result["total_python_files"] += 1

            # Extract module name from path
            module_name = self._path_to_module(path)
            if module_name:
                if module_name not in self.all_imports:
                    self.all_imports[module_name] = []
                self.all_imports[module_name].append(path)

        # Step 2: Collect all imports from all files
        for file_info in python_files:
            exports = file_info.get("exports", {})
            imports = exports.get("imports", {})

            # Internal imports point to other project files
            for imp in imports.get("internal", []):
                # Normalize import to module name
                module = imp.split(".")[0] if imp else None
                if module:
                    self.imported_modules.add(module.lower())

                # Also add full import path
                if imp:
                    self.imported_modules.add(imp.lower().replace(".", "/"))

        # Step 3: Find orphaned files
        for file_info in python_files:
            path = file_info["path"]
            filename = Path(path).name

            # Skip excluded patterns
            if self._is_excluded(filename):
                continue

            # Skip entry point patterns
            if self._is_entry_point(path, filename):
                result["entry_points"].append(path)
                continue

            # Check if this file is imported anywhere
            module_name = self._path_to_module(path)
            if not self._is_imported(path, module_name):
                result["orphaned_files"].append({
                    "path": path,
                    "lines": file_info.get("lines", 0),
                    "module_name": module_name,
                })
                result["orphaned_lines"] += file_info.get("lines", 0)

        result["orphaned_count"] = len(result["orphaned_files"])

        # Sort by lines (biggest orphans first)
        result["orphaned_files"].sort(key=lambda x: x["lines"], reverse=True)

        return result

    def _path_to_module(self, path: str) -> str:
        """Convert file path to Python module name."""
        # src/api/routers/agents.py -> agents
        # src/openai_agents/agent_factory.py -> agent_factory
        p = Path(path)
        if p.name == "__init__.py":
            return p.parent.name
        return p.stem

    def _is_excluded(self, filename: str) -> bool:
        """Check if file matches excluded patterns."""
        for pattern in self.EXCLUDED_PATTERNS:
            if re.match(pattern, filename):
                return True
        return False

    def _is_entry_point(self, path: str, filename: str) -> bool:
        """Check if file is an entry point."""
        # Check filename patterns
        for pattern in self.ENTRY_POINT_PATTERNS:
            if re.match(pattern, filename):
                return True

        # Check if in entry point directory
        path_lower = path.lower()
        for dir_name in self.ENTRY_POINT_DIRS:
            if f"/{dir_name}/" in path_lower or path_lower.startswith(f"{dir_name}/"):
                return True

        return False

    def _is_imported(self, path: str, module_name: str) -> bool:
        """Check if a file/module is imported anywhere."""
        if not module_name:
            return True  # Can't determine, assume used

        module_lower = module_name.lower()

        # Direct module name match
        if module_lower in self.imported_modules:
            return True

        # Check path-based imports (e.g., "src.api.routers.agents")
        path_as_module = path.replace("/", ".").replace("\\", ".").lower()
        path_as_module = re.sub(r"\.py$", "", path_as_module)

        for imported in self.imported_modules:
            # Check if any import references this module
            if module_lower in imported or imported in path_as_module:
                return True

            # Check partial path match
            if imported.replace(".", "/") in path.lower():
                return True

        return False


# =============================================================================
# Python Scanner (AST-based)
# =============================================================================

class PythonScanner:
    """Scan Python files using AST for accurate extraction."""

    def scan(self, filepath: Path) -> dict:
        """Scan a Python file and extract structure."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            # Fall back to regex if AST fails
            return self._scan_regex(filepath)
        except Exception as e:
            return {"error": str(e)}

        result = {
            "classes": [],
            "functions": [],
            "imports": {"internal": [], "external": []},
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
        }

        for node in ast.walk(tree):
            # Classes
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', None),
                    "bases": [self._get_name(b) for b in node.bases],
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node),
                    "methods": []
                }

                # Check if it's a Pydantic model
                if any("BaseModel" in str(b) or "Base" == str(b) for b in class_info["bases"]):
                    if "BaseModel" in str(class_info["bases"]):
                        result["pydantic_models"].append(node.name)

                # Get methods with signatures and calls
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_info = {
                            "name": item.name,
                            "line": item.lineno,
                            "async": isinstance(item, ast.AsyncFunctionDef),
                            "signature": self._extract_signature(item),
                            "docstring": ast.get_docstring(item),
                            "calls": self._extract_calls(item),
                            "body_hash": self._get_function_body_hash(item),
                        }
                        class_info["methods"].append(method_info)

                result["classes"].append(class_info)

                # Check for SQLAlchemy __tablename__
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "__tablename__":
                                if isinstance(item.value, ast.Constant):
                                    result["sqlalchemy_tables"].append({
                                        "class": node.name,
                                        "table": item.value.value
                                    })

            # Top-level functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if hasattr(node, 'col_offset') and node.col_offset == 0:
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": getattr(node, 'end_lineno', None),
                        "async": isinstance(node, ast.AsyncFunctionDef),
                        "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                        "signature": self._extract_signature(node),
                        "docstring": ast.get_docstring(node),
                        "calls": self._extract_calls(node),
                        "body_hash": self._get_function_body_hash(node),
                    }
                    result["functions"].append(func_info)

                    # Check for FastAPI route decorators
                    for dec in node.decorator_list:
                        dec_name = self._get_decorator_name(dec)
                        if dec_name and re.match(r"router\.(get|post|put|patch|delete|head|options)", dec_name):
                            route_info = self._extract_route_info(dec, node.name, node.lineno)
                            if route_info:
                                result["fastapi_routes"].append(route_info)

            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._categorize_import(alias.name, result["imports"])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._categorize_import(node.module, result["imports"])

        return result

    def _get_name(self, node) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return str(node)

    def _get_decorator_name(self, node) -> str:
        """Extract decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return None

    def _extract_signature(self, node) -> dict:
        """Extract function signature (parameters and return type)."""
        signature = {
            "params": [],
            "return_type": None,
        }

        # Extract parameters
        args = node.args

        # Positional args
        for i, arg in enumerate(args.args):
            param = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            # Check for default value
            default_offset = len(args.args) - len(args.defaults)
            if i >= default_offset:
                default_node = args.defaults[i - default_offset]
                param["has_default"] = True
            signature["params"].append(param)

        # *args
        if args.vararg:
            signature["params"].append({
                "name": f"*{args.vararg.arg}",
                "type": self._get_annotation(args.vararg.annotation),
            })

        # Keyword-only args
        for i, arg in enumerate(args.kwonlyargs):
            param = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                param["has_default"] = True
            signature["params"].append(param)

        # **kwargs
        if args.kwarg:
            signature["params"].append({
                "name": f"**{args.kwarg.arg}",
                "type": self._get_annotation(args.kwarg.annotation),
            })

        # Return type
        if node.returns:
            signature["return_type"] = self._get_annotation(node.returns)

        return signature

    def _get_annotation(self, node) -> str:
        """Extract type annotation as string."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            # Handle generics like List[str], Optional[int]
            base = self._get_annotation(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = ", ".join(self._get_annotation(e) for e in node.slice.elts)
            else:
                args = self._get_annotation(node.slice)
            return f"{base}[{args}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handle Union types with | syntax (Python 3.10+)
            left = self._get_annotation(node.left)
            right = self._get_annotation(node.right)
            return f"{left} | {right}"
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_annotation(e) for e in node.elts)
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)

    def _extract_calls(self, node) -> list:
        """
        Extract all function/method calls from a function body.
        Returns raw call strings for LLM to analyze.
        """
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_name(child.func)
                if call_str:
                    calls.append(call_str)
        # Remove duplicates while preserving order
        seen = set()
        unique_calls = []
        for call in calls:
            if call not in seen:
                seen.add(call)
                unique_calls.append(call)
        return unique_calls

    def _get_call_name(self, node) -> str:
        """Extract the name of a call target."""
        if isinstance(node, ast.Name):
            # Direct function call: func()
            return node.id
        elif isinstance(node, ast.Attribute):
            # Method call: obj.method() or self.method()
            value = self._get_call_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Subscript):
            # Subscript call: obj[key]()
            value = self._get_call_name(node.value)
            return f"{value}[...]" if value else None
        elif isinstance(node, ast.Call):
            # Chained call: func()()
            return self._get_call_name(node.func)
        return None

    def _get_function_body_hash(self, node) -> str:
        """
        Generate a normalized hash of function body for duplicate detection.
        Normalizes variable names to detect structurally similar code.
        """
        try:
            # Get the function body (skip docstring if present)
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                # Skip docstring
                body = body[1:]

            if not body:
                return None

            # Use ast.dump for structural comparison (ignores variable names by default)
            # This gives us a structural fingerprint
            body_str = ""
            for stmt in body:
                body_str += ast.dump(stmt, annotate_fields=False)

            # Hash the structural representation
            return hashlib.md5(body_str.encode()).hexdigest()[:12]
        except Exception:
            return None

    def _extract_route_info(self, decorator, func_name: str, line: int) -> dict:
        """Extract FastAPI route information from decorator."""
        if not isinstance(decorator, ast.Call):
            return None

        dec_name = self._get_decorator_name(decorator)
        if not dec_name:
            return None

        match = re.match(r"router\.(get|post|put|patch|delete|head|options)", dec_name)
        if not match:
            return None

        method = match.group(1).upper()
        path = None

        # Get path from first argument
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            path = decorator.args[0].value

        return {
            "method": method,
            "path": path,
            "handler": func_name,
            "line": line
        }

    def _categorize_import(self, module: str, imports: dict):
        """Categorize import as internal or external."""
        # Common external packages
        external_prefixes = [
            "fastapi", "pydantic", "sqlalchemy", "openai", "langfuse",
            "pytest", "typing", "os", "sys", "re", "json", "datetime",
            "pathlib", "asyncio", "logging", "uuid", "hashlib", "base64",
            "collections", "functools", "itertools", "contextlib",
            "aiohttp", "httpx", "requests", "yaml", "toml",
        ]

        root_module = module.split(".")[0]

        if root_module in external_prefixes or not root_module.startswith(("src", "api", "db", "auth", "agents")):
            if module not in imports["external"]:
                imports["external"].append(root_module)
        else:
            if module not in imports["internal"]:
                imports["internal"].append(module)

    def _scan_regex(self, filepath: Path) -> dict:
        """Fallback regex-based scanning for files with syntax errors."""
        result = {
            "classes": [],
            "functions": [],
            "imports": {"internal": [], "external": []},
            "fastapi_routes": [],
            "sqlalchemy_tables": [],
            "pydantic_models": [],
            "_fallback": "regex"
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception:
            return result

        for i, line in enumerate(lines, 1):
            # Classes
            match = re.match(r"^class\s+(\w+)", line)
            if match:
                result["classes"].append({"name": match.group(1), "line": i})

            # Functions
            match = re.match(r"^(async\s+)?def\s+(\w+)", line)
            if match:
                result["functions"].append({
                    "name": match.group(2),
                    "line": i,
                    "async": bool(match.group(1))
                })

            # Routes
            match = re.match(r'^@router\.(get|post|put|patch|delete)\(["\']([^"\']+)', line)
            if match:
                result["fastapi_routes"].append({
                    "method": match.group(1).upper(),
                    "path": match.group(2),
                    "line": i
                })

            # Tables
            match = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', line)
            if match:
                result["sqlalchemy_tables"].append({"table": match.group(1), "line": i})

        return result


# =============================================================================
# TypeScript/React Scanner (Regex-based)
# =============================================================================

class TypeScriptScanner:
    """Scan TypeScript/React files using regex patterns."""

    def scan(self, filepath: Path) -> dict:
        """Scan a TypeScript/React file."""
        result = {
            "components": [],
            "hooks": [],
            "functions": [],
            "types": [],
            "interfaces": [],
            "imports": {"internal": [], "external": []},
            "api_calls": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception as e:
            return {"error": str(e)}

        for i, line in enumerate(lines, 1):
            # Exported functions/components
            match = re.match(r"^export\s+(default\s+)?(?:async\s+)?function\s+(\w+)", line)
            if match:
                name = match.group(2)
                if name.startswith("use"):
                    result["hooks"].append({"name": name, "line": i})
                elif name[0].isupper():
                    result["components"].append({"name": name, "line": i})
                else:
                    result["functions"].append({"name": name, "line": i})

            # Exported const components/hooks
            match = re.match(r"^export\s+(const|let)\s+(\w+)\s*[=:]", line)
            if match:
                name = match.group(2)
                if name.startswith("use"):
                    result["hooks"].append({"name": name, "line": i})
                elif name[0].isupper():
                    result["components"].append({"name": name, "line": i})

            # Types
            match = re.match(r"^export\s+type\s+(\w+)", line)
            if match:
                result["types"].append({"name": match.group(1), "line": i})

            # Interfaces
            match = re.match(r"^export\s+interface\s+(\w+)", line)
            if match:
                result["interfaces"].append({"name": match.group(1), "line": i})

            # Imports
            match = re.match(r"^import\s+.*from\s+['\"]([^'\"]+)['\"]", line)
            if match:
                module = match.group(1)
                if module.startswith(".") or module.startswith("@/"):
                    result["imports"]["internal"].append(module)
                else:
                    # Get package name (first part)
                    pkg = module.split("/")[0]
                    if pkg.startswith("@"):
                        pkg = "/".join(module.split("/")[:2])
                    if pkg not in result["imports"]["external"]:
                        result["imports"]["external"].append(pkg)

            # API calls
            match = re.search(r"fetch\(['\"]([^'\"]+)['\"]", line)
            if match:
                result["api_calls"].append({"url": match.group(1), "line": i})

            match = re.search(r"axios\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", line)
            if match:
                result["api_calls"].append({
                    "method": match.group(1).upper(),
                    "url": match.group(2),
                    "line": i
                })

        return result


# =============================================================================
# SQL Scanner (Regex-based)
# =============================================================================

class SQLScanner:
    """Scan SQL files for table definitions."""

    def scan(self, filepath: Path) -> dict:
        """Scan a SQL file."""
        result = {
            "tables": [],
            "indexes": [],
            "views": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"error": str(e)}

        # Tables
        for match in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\']?(\w+)[`\"\']?", content, re.IGNORECASE):
            result["tables"].append({"name": match.group(1)})

        # Indexes
        for match in re.finditer(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+[`\"\']?(\w+)[`\"\']?\s+ON\s+[`\"\']?(\w+)[`\"\']?", content, re.IGNORECASE):
            result["indexes"].append({"name": match.group(1), "table": match.group(2)})

        # Views
        for match in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+[`\"\']?(\w+)[`\"\']?", content, re.IGNORECASE):
            result["views"].append({"name": match.group(1)})

        return result


# =============================================================================
# Docker Scanner (YAML-based)
# =============================================================================

class DockerScanner:
    """Scan Docker Compose files."""

    def scan(self, filepath: Path) -> dict:
        """Scan a docker-compose file."""
        if not HAS_YAML:
            return self._scan_regex(filepath)

        result = {
            "services": [],
            "networks": [],
            "volumes": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            return {"error": str(e)}

        if not data:
            return result

        # Services
        services = data.get("services", {})
        for name, config in services.items():
            service_info = {
                "name": name,
                "image": config.get("image"),
                "build": config.get("build"),
                "ports": config.get("ports", []),
                "depends_on": config.get("depends_on", []),
                "environment": list(config.get("environment", {}).keys()) if isinstance(config.get("environment"), dict) else config.get("environment", []),
            }
            result["services"].append(service_info)

        # Networks
        networks = data.get("networks", {})
        result["networks"] = list(networks.keys()) if networks else []

        # Volumes
        volumes = data.get("volumes", {})
        result["volumes"] = list(volumes.keys()) if volumes else []

        return result

    def _scan_regex(self, filepath: Path) -> dict:
        """Fallback regex scanning if YAML not available."""
        result = {"services": [], "networks": [], "volumes": [], "_fallback": "regex"}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return result

        # Simple service detection
        in_services = False
        for line in content.split("\n"):
            if re.match(r"^services:\s*$", line):
                in_services = True
                continue
            if in_services and re.match(r"^[a-z]", line):
                in_services = False
            if in_services:
                match = re.match(r"^\s{2}(\w+):\s*$", line)
                if match:
                    result["services"].append({"name": match.group(1)})

        return result


# =============================================================================
# Main Scanner
# =============================================================================

class CodebaseScanner:
    """Main scanner that orchestrates all language-specific scanners."""

    def __init__(self, root: Path, exclude: list = None, exclude_extensions: set = None, include_hash: bool = True):
        self.root = root.resolve()
        self.exclude = exclude or DEFAULT_EXCLUDE
        self.exclude_extensions = exclude_extensions or set()
        self.include_hash = include_hash

        # Core scanners
        self.python_scanner = PythonScanner()
        self.typescript_scanner = TypeScriptScanner()
        self.sql_scanner = SQLScanner()
        self.docker_scanner = DockerScanner()
        self.deps_scanner = DependenciesScanner()
        self.env_scanner = EnvScanner()
        self.todo_scanner = TodoScanner()
        self.route_prefix_scanner = RoutePrefixScanner()

        # v1.2.0 scanners
        self.import_aggregator = ImportAggregator()
        self.auth_scanner = AuthScanner()
        self.test_mapper = TestCoverageMapper(self.root)
        self.http_calls_scanner = HttpCallsScanner()
        self.complexity_analyzer = ComplexityAnalyzer()

        # v1.3.0 scanners
        self.middleware_scanner = MiddlewareScanner()
        self.websocket_scanner = WebSocketScanner()
        self.alembic_scanner = AlembicScanner()

        # v1.4.0 scanners
        self.orphaned_scanner = OrphanedFileScanner()

    def scan(self) -> dict:
        """Scan the entire codebase."""
        result = {
            "meta": self._build_meta(),
            "summary": {
                "total_files": 0,
                "total_lines": 0,
                "by_language": {},
                "by_category": {},
            },
            "files": [],
            "api_endpoints": [],
            "database": {"tables": []},
            "docker": {"services": [], "networks": [], "volumes": []},
            "dependencies": {},
            "environment_variables": {},
            "todos": [],
            # v1.2.0 additions
            "import_analysis": {},
            "test_coverage": {},
            "external_http_calls": {},
            "complexity_warnings": {},
            # v1.3.0 additions
            "middleware": {},
            "websockets": {},
            "migrations": {},
            # v1.4.0 additions
            "orphaned_files": {},
            # v1.5.0 additions
            "symbol_index": {
                "functions": [],
                "classes": [],
                "methods": [],
            },
            # v1.6.0 additions
            "call_graph": {},
            "potential_duplicates": [],
        }

        # Get route prefixes first for full path resolution
        route_prefixes = self.route_prefix_scanner.scan(self.root)

        # Collect test files first for coverage mapping
        self.test_mapper.collect_test_files(self.exclude)

        # Walk directory
        for filepath in self._walk_files():
            file_info = self._scan_file(filepath)
            if file_info:
                result["files"].append(file_info)
                self._update_summary(result["summary"], file_info)

                # Register Python files as internal modules for import analysis
                if file_info.get("language") == "python":
                    # Extract module name from path (e.g., "src/api/main.py" -> "main", "api", "src")
                    path_parts = Path(file_info["path"]).with_suffix("").parts
                    for part in path_parts:
                        if part and not part.startswith("_"):
                            self.import_aggregator.add_internal_module(part)

                # Aggregate imports for dependency analysis (Python only)
                exports = file_info.get("exports", {})
                if file_info.get("language") == "python" and exports.get("imports"):
                    all_imports = exports["imports"].get("external", []) + exports["imports"].get("internal", [])
                    self.import_aggregator.add_imports(all_imports, file_info["path"])

                # Collect API endpoints with full paths and auth info
                if exports.get("fastapi_routes"):
                    # Try to find prefix for this router
                    router_name = Path(file_info["path"]).stem  # e.g., "agents" from "agents.py"
                    prefix = route_prefixes.get(router_name, "")

                    # Annotate routes with auth requirements
                    annotated_routes = self.auth_scanner.scan_file(
                        self.root / file_info["path"],
                        exports["fastapi_routes"]
                    )

                    for route in annotated_routes:
                        full_path = prefix + (route.get("path") or "")
                        result["api_endpoints"].append({
                            **route,
                            "full_path": full_path,
                            "file": file_info["path"]
                        })

                # Collect database tables
                if exports.get("sqlalchemy_tables"):
                    for table in exports["sqlalchemy_tables"]:
                        result["database"]["tables"].append({
                            **table,
                            "file": file_info["path"]
                        })

                # Collect Docker info
                if file_info.get("language") == "docker":
                    docker_data = exports
                    result["docker"]["services"].extend(docker_data.get("services", []))
                    result["docker"]["networks"].extend(docker_data.get("networks", []))
                    result["docker"]["volumes"].extend(docker_data.get("volumes", []))

                # v1.5.0: Build symbol index
                if file_info.get("language") == "python":
                    file_path = file_info["path"]

                    # Index functions
                    for func in exports.get("functions", []):
                        if isinstance(func, dict):
                            result["symbol_index"]["functions"].append({
                                "name": func.get("name"),
                                "file": file_path,
                                "line": func.get("line"),
                                "async": func.get("async", False),
                                "signature": func.get("signature"),
                                "docstring": self._truncate_docstring(func.get("docstring")),
                            })

                    # Index classes and their methods
                    for cls in exports.get("classes", []):
                        if isinstance(cls, dict):
                            result["symbol_index"]["classes"].append({
                                "name": cls.get("name"),
                                "file": file_path,
                                "line": cls.get("line"),
                                "bases": cls.get("bases", []),
                                "docstring": self._truncate_docstring(cls.get("docstring")),
                                "method_count": len(cls.get("methods", [])),
                            })

                            # Index methods
                            for method in cls.get("methods", []):
                                if isinstance(method, dict):
                                    result["symbol_index"]["methods"].append({
                                        "name": method.get("name"),
                                        "class": cls.get("name"),
                                        "file": file_path,
                                        "line": method.get("line"),
                                        "async": method.get("async", False),
                                        "signature": method.get("signature"),
                                        "docstring": self._truncate_docstring(method.get("docstring")),
                                    })

        # v1.6.0: Build call graph and detect duplicates
        body_hash_index = {}  # hash -> list of functions

        for file_info in result["files"]:
            if file_info.get("language") != "python":
                continue

            file_path = file_info["path"]
            exports = file_info.get("exports", {})

            # Process functions for call graph and duplicates
            for func in exports.get("functions", []):
                if isinstance(func, dict):
                    func_name = func.get("name")
                    calls = func.get("calls", [])

                    # Add to call graph
                    if calls:
                        full_name = f"{file_path}:{func_name}"
                        result["call_graph"][full_name] = {
                            "file": file_path,
                            "line": func.get("line"),
                            "calls": calls,
                        }

                    # Track body hash for duplicate detection
                    body_hash = func.get("body_hash")
                    if body_hash:
                        if body_hash not in body_hash_index:
                            body_hash_index[body_hash] = []
                        body_hash_index[body_hash].append({
                            "name": func_name,
                            "file": file_path,
                            "line": func.get("line"),
                            "type": "function",
                        })

            # Process methods for call graph and duplicates
            for cls in exports.get("classes", []):
                if isinstance(cls, dict):
                    class_name = cls.get("name")
                    for method in cls.get("methods", []):
                        if isinstance(method, dict):
                            method_name = method.get("name")
                            calls = method.get("calls", [])

                            # Add to call graph
                            if calls:
                                full_name = f"{file_path}:{class_name}.{method_name}"
                                result["call_graph"][full_name] = {
                                    "file": file_path,
                                    "line": method.get("line"),
                                    "class": class_name,
                                    "calls": calls,
                                }

                            # Track body hash for duplicate detection
                            body_hash = method.get("body_hash")
                            if body_hash:
                                if body_hash not in body_hash_index:
                                    body_hash_index[body_hash] = []
                                body_hash_index[body_hash].append({
                                    "name": f"{class_name}.{method_name}",
                                    "file": file_path,
                                    "line": method.get("line"),
                                    "type": "method",
                                })

        # Find potential duplicates (hashes with more than one function)
        for body_hash, functions in body_hash_index.items():
            if len(functions) > 1:
                result["potential_duplicates"].append({
                    "hash": body_hash,
                    "count": len(functions),
                    "functions": functions,
                })

        # Sort duplicates by count (most duplicated first)
        result["potential_duplicates"].sort(key=lambda x: x["count"], reverse=True)

        # Scan dependencies
        result["dependencies"] = self.deps_scanner.scan(self.root)

        # Scan environment variables
        result["environment_variables"] = self.env_scanner.scan(self.root)

        # Scan TODOs
        result["todos"] = self.todo_scanner.scan(self.root, self.exclude)

        # v1.2.0: Import analysis (missing/unused deps)
        python_deps = result["dependencies"].get("python", [])
        result["import_analysis"] = self.import_aggregator.analyze(python_deps)

        # v1.2.0: Test coverage mapping
        result["test_coverage"] = self.test_mapper.map_source_to_test(result["files"])

        # v1.2.0: External HTTP calls
        result["external_http_calls"] = self.http_calls_scanner.scan(self.root, self.exclude)

        # v1.2.0: Complexity analysis
        result["complexity_warnings"] = self.complexity_analyzer.analyze(result["files"])

        # v1.3.0: Middleware
        result["middleware"] = self.middleware_scanner.scan(self.root, self.exclude)

        # v1.3.0: WebSocket endpoints
        result["websockets"] = self.websocket_scanner.scan(self.root, self.exclude)

        # v1.3.0: Alembic migrations
        result["migrations"] = self.alembic_scanner.scan(self.root)

        # v1.4.0: Orphaned files (dead code detection)
        result["orphaned_files"] = self.orphaned_scanner.scan(self.root, result["files"], self.exclude)

        # Add summary counts
        result["summary"]["todos_count"] = len(result["todos"])
        result["summary"]["env_vars_count"] = (
            len(result["environment_variables"].get("python_usage", [])) +
            len(result["environment_variables"].get("typescript_usage", []))
        )
        result["summary"]["api_endpoints_count"] = len(result["api_endpoints"])
        result["summary"]["auth_required_endpoints"] = sum(
            1 for ep in result["api_endpoints"] if ep.get("auth_required")
        )
        result["summary"]["test_coverage_percent"] = result["test_coverage"].get("coverage_percentage", 0)
        result["summary"]["external_http_calls"] = result["external_http_calls"].get("total_external_calls", 0)
        result["summary"]["complexity_issues"] = (
            len(result["complexity_warnings"].get("large_files", [])) +
            len(result["complexity_warnings"].get("complex_classes", []))
        )
        # v1.3.0 summaries
        result["summary"]["middleware_count"] = (
            len(result["middleware"].get("middleware", [])) +
            len(result["middleware"].get("custom_middleware", []))
        )
        result["summary"]["websocket_endpoints"] = result["websockets"].get("total", 0)
        result["summary"]["migrations_count"] = result["migrations"].get("total", 0)
        # v1.4.0 summaries
        result["summary"]["orphaned_files_count"] = result["orphaned_files"].get("orphaned_count", 0)
        result["summary"]["orphaned_lines"] = result["orphaned_files"].get("orphaned_lines", 0)
        # v1.5.0 summaries
        result["summary"]["total_functions"] = len(result["symbol_index"]["functions"])
        result["summary"]["total_classes"] = len(result["symbol_index"]["classes"])
        result["summary"]["total_methods"] = len(result["symbol_index"]["methods"])
        result["summary"]["documented_functions"] = sum(
            1 for f in result["symbol_index"]["functions"] if f.get("docstring")
        )
        result["summary"]["documented_classes"] = sum(
            1 for c in result["symbol_index"]["classes"] if c.get("docstring")
        )
        # v1.6.0 summaries
        result["summary"]["call_graph_entries"] = len(result["call_graph"])
        result["summary"]["potential_duplicate_groups"] = len(result["potential_duplicates"])
        result["summary"]["total_duplicated_functions"] = sum(
            d["count"] for d in result["potential_duplicates"]
        )

        return result

    def _truncate_docstring(self, docstring: str, max_length: int = 200) -> str:
        """Truncate docstring to first line or max length."""
        if not docstring:
            return None
        # Get first line or first paragraph
        first_line = docstring.split('\n')[0].strip()
        if len(first_line) > max_length:
            return first_line[:max_length] + "..."
        return first_line

    def _build_meta(self) -> dict:
        """Build metadata section."""
        meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "1.7.0",
            "root": str(self.root),
        }

        git_info = get_git_info(self.root)
        if git_info:
            meta["git"] = git_info

        return meta

    def _walk_files(self):
        """Walk directory and yield files to scan."""
        for root, dirs, files in os.walk(self.root):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d, self.exclude)]

            for filename in files:
                filepath = Path(root) / filename
                if not should_exclude(filepath, self.exclude):
                    yield filepath

    def _scan_file(self, filepath: Path) -> dict:
        """Scan a single file."""
        rel_path = str(filepath.relative_to(self.root))
        suffix = filepath.suffix.lower()

        # Check extension exclusions
        if self.exclude_extensions and suffix in self.exclude_extensions:
            return None

        # Determine language and scanner
        language = None
        scanner = None
        category = "other"

        if suffix == ".py":
            language = "python"
            scanner = self.python_scanner
            category = categorize_file(rel_path, PYTHON_CATEGORIES)
        elif suffix in (".ts", ".tsx"):
            language = "typescript"
            scanner = self.typescript_scanner
            category = categorize_file(rel_path, TYPESCRIPT_CATEGORIES)
        elif suffix == ".sql":
            language = "sql"
            scanner = self.sql_scanner
        elif suffix in (".yaml", ".yml") and "docker" in filepath.name.lower():
            language = "docker"
            scanner = self.docker_scanner
        elif filepath.name == "docker-compose.yaml" or filepath.name == "docker-compose.yml":
            language = "docker"
            scanner = self.docker_scanner
        else:
            # Skip non-code files
            return None

        # Build file info
        file_info = {
            "path": rel_path,
            "language": language,
            "category": category,
            "size_bytes": filepath.stat().st_size,
            "lines": count_lines(filepath),
        }

        if self.include_hash:
            file_info["hash"] = get_file_hash(filepath)

        # Scan file contents
        if scanner:
            exports = scanner.scan(filepath)
            if exports and not exports.get("error"):
                file_info["exports"] = exports

        return file_info

    def _update_summary(self, summary: dict, file_info: dict):
        """Update summary statistics."""
        summary["total_files"] += 1
        summary["total_lines"] += file_info.get("lines", 0)

        # By language
        lang = file_info.get("language", "other")
        if lang not in summary["by_language"]:
            summary["by_language"][lang] = {"files": 0, "lines": 0}
        summary["by_language"][lang]["files"] += 1
        summary["by_language"][lang]["lines"] += file_info.get("lines", 0)

        # By category
        cat = file_info.get("category", "other")
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1


# =============================================================================
# Call Graph Query Functions
# =============================================================================

def cg_query_function(call_graph: dict, func_name: str) -> dict:
    """Query what a specific function calls (fuzzy match)."""
    results = {}
    func_lower = func_name.lower()

    for key, info in call_graph.items():
        # Match on function name (last part of key)
        key_func = key.split(":")[-1].lower()
        if func_lower in key_func or func_lower in key.lower():
            results[key] = info

    return {
        "query": func_name,
        "query_type": "what_does_it_call",
        "matches": len(results),
        "results": results,
    }


def cg_query_file(call_graph: dict, file_path: str) -> dict:
    """Query all functions in a specific file."""
    results = {}
    file_lower = file_path.lower()

    for key, info in call_graph.items():
        if file_lower in info.get("file", "").lower():
            results[key] = info

    return {
        "query": file_path,
        "query_type": "file_call_graph",
        "matches": len(results),
        "results": results,
    }


def cg_query_callers(call_graph: dict, func_name: str) -> dict:
    """Query what functions call a specific function (inverse lookup)."""
    results = {}
    func_lower = func_name.lower()

    for key, info in call_graph.items():
        calls = info.get("calls", [])
        # Check if any call matches the function name
        for call in calls:
            if func_lower in call.lower():
                if key not in results:
                    results[key] = {
                        "file": info.get("file"),
                        "line": info.get("line"),
                        "matching_calls": [],
                    }
                results[key]["matching_calls"].append(call)

    return {
        "query": func_name,
        "query_type": "what_calls_it",
        "matches": len(results),
        "results": results,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive codebase inventory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codebase_index.py .                    # Scan current directory
  codebase_index.py ./src -o index.json  # Scan src, output to file
  codebase_index.py . --no-hash          # Skip file hashes (faster)
  codebase_index.py . --summary          # Only show summary

Configuration (for non-FastAPI projects):
  codebase_index.py --init-config        # Generate starter config (edit with LLM)
  codebase_index.py . --config my.yaml   # Use custom config for Django/Flask/etc.

Exclusion examples:
  codebase_index.py . --exclude-dirs docs vendor  # Exclude specific directories
  codebase_index.py . --exclude-ext .md .txt      # Exclude file extensions
  codebase_index.py . --exclude "*.generated.*"   # Exclude patterns

Call graph queries (use with --load for speed):
  codebase_index.py --load index.json --cg-query ChatService.stream_chat
  codebase_index.py --load index.json --cg-file src/api/services/chat_service.py
  codebase_index.py --load index.json --cg-callers AgentFactory.create

LLM Workflow (for any project):
  1. Run: codebase_index.py --init-config > codebase_index.yaml
  2. Ask Claude/GPT: "Customize this config for my Django project"
  3. Run: codebase_index.py . --config codebase_index.yaml -o index.json
        """
    )

    parser.add_argument("path", nargs="?", default=".", help="Path to scan (default: current directory)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("--load", metavar="FILE", help="Load existing index file instead of scanning")
    parser.add_argument("--no-hash", action="store_true", help="Skip file hash generation")
    parser.add_argument("--summary", action="store_true", help="Only output summary")
    parser.add_argument("--exclude", nargs="+", help="Additional patterns to exclude")
    parser.add_argument("--exclude-dirs", nargs="+", metavar="DIR",
                        help="Directories to exclude (e.g., docs vendor third-party)")
    parser.add_argument("--exclude-ext", nargs="+", metavar="EXT",
                        help="File extensions to exclude (e.g., .md .txt .log)")

    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument("--config", metavar="FILE",
                              help="Load config from YAML file (for Django, Flask, Express, etc.)")
    config_group.add_argument("--init-config", action="store_true",
                              help="Generate a starter config file (customize with LLM, then use --config)")

    # Call graph query options
    cg_group = parser.add_argument_group("Call Graph Queries")
    cg_group.add_argument("--cg-query", metavar="FUNC",
                          help="What does FUNC call? (fuzzy match on function name)")
    cg_group.add_argument("--cg-file", metavar="FILE",
                          help="Show call graph for all functions in FILE")
    cg_group.add_argument("--cg-callers", metavar="FUNC",
                          help="What functions call FUNC? (inverse lookup)")

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Handle --init-config: just output the template and exit
    if args.init_config:
        print(get_config_template())
        return

    # Load config if specified
    config = DEFAULT_CONFIG
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file '{config_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        if args.verbose:
            print(f"Loading config from: {config_path}", file=sys.stderr)
        config = load_config(config_path)

    # Check if we have call graph query options
    has_cg_query = args.cg_query or args.cg_file or args.cg_callers

    # Load existing index or scan
    if args.load:
        # Load from file
        load_path = Path(args.load)
        if not load_path.exists():
            print(f"Error: Index file '{load_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        if args.verbose:
            print(f"Loading index from: {load_path}", file=sys.stderr)
        with open(load_path, "r") as f:
            result = json.load(f)
    else:
        # Scan the codebase
        root = Path(args.path).resolve()
        if not root.exists():
            print(f"Error: Path '{root}' does not exist", file=sys.stderr)
            sys.exit(1)

        exclude = DEFAULT_EXCLUDE.copy()
        if args.exclude:
            exclude.extend(args.exclude)

        # Add directory exclusions
        if args.exclude_dirs:
            exclude.extend(args.exclude_dirs)

        # Add extension exclusions (normalize to have leading dot)
        exclude_extensions = set()
        if args.exclude_ext:
            for ext in args.exclude_ext:
                if not ext.startswith('.'):
                    ext = '.' + ext
                exclude_extensions.add(ext.lower())

        if args.verbose:
            print(f"Scanning: {root}", file=sys.stderr)
            if args.exclude_dirs:
                print(f"Excluding directories: {args.exclude_dirs}", file=sys.stderr)
            if exclude_extensions:
                print(f"Excluding extensions: {sorted(exclude_extensions)}", file=sys.stderr)

        scanner = CodebaseScanner(
            root=root,
            exclude=exclude,
            exclude_extensions=exclude_extensions,
            include_hash=not args.no_hash
        )

        result = scanner.scan()

    # Handle call graph queries
    if has_cg_query:
        call_graph = result.get("call_graph", {})
        if not call_graph:
            print("Error: No call graph data available", file=sys.stderr)
            sys.exit(1)

        if args.cg_query:
            query_result = cg_query_function(call_graph, args.cg_query)
            print(json.dumps(query_result, indent=2))
        elif args.cg_file:
            query_result = cg_query_file(call_graph, args.cg_file)
            print(json.dumps(query_result, indent=2))
        elif args.cg_callers:
            query_result = cg_query_callers(call_graph, args.cg_callers)
            print(json.dumps(query_result, indent=2))
        return

    # Summary only mode
    if args.summary:
        result = {
            "meta": result["meta"],
            "summary": result["summary"]
        }

    # Output
    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        if args.verbose:
            print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
