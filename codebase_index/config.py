"""
Configuration constants and loading utilities for codebase_index.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore
    HAS_YAML = False


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


# Standard library modules (Python 3.9+)
# Used for distinguishing stdlib from third-party imports
STDLIB_MODULES = frozenset({
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
    "zipapp", "zipfile", "zipimport", "zlib",
})


DEFAULT_CONFIG: dict[str, Any] = {
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
            # SQLAlchemy (marker-based is most reliable)
            {"marker": "__tablename__", "type": "sqlalchemy"},
            {"base_class": "DeclarativeBase", "type": "sqlalchemy"},
            # Django (must be models.Model, not just Model which is too generic)
            {"base_class": "models.Model", "type": "django"},
            # Tortoise ORM
            {"base_class": "tortoise.Model", "type": "tortoise"},
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
    # NEW FORMAT: Separate parameter patterns (checked in function signature)
    # from decorator patterns (checked above function definition)
    # This prevents false positives from broad context matching
    "auth": {
        "enabled": True,
        # Patterns checked against function PARAMETERS/SIGNATURE only
        "parameters": [
            # FastAPI Depends() patterns
            r"Depends\s*\(\s*get_current_user",
            r"Depends\s*\(\s*get_current_active_user",
            r"Depends\s*\(\s*require_auth",
            r"Depends\s*\(\s*auth_required",
            r"Depends\s*\(\s*verify_token",
            r"Depends\s*\(\s*oauth2_scheme",
            r"Depends\s*\(\s*get_api_key",
            # Type hint patterns
            r"current_user\s*:\s*\w+",
            r"authenticated_user",
        ],
        # Patterns checked against DECORATORS only (lines starting with @)
        "decorators": [
            r"@login_required",
            r"@require_auth",
            r"@authenticated",
            r"@jwt_required",
            r"@permission_required",
            r"@auth_required",
            r"@token_required",
            r"@api_key_required",
            r"@permission_classes",
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
            # Python standard library (subset, full list is in STDLIB_MODULES)
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

    # Exclusion patterns (applied in addition to CLI exclusions)
    "exclude": {
        "directories": [],  # e.g., [".archive", "docs", "vendor"]
        "extensions": [],   # e.g., [".md", ".txt", ".log"]
        "patterns": [],     # e.g., ["*.generated.*", "*.min.js"]
    },
}


def load_config(config_path: Path) -> dict[str, Any]:
    """
    Load configuration from YAML file, merged with defaults.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Configuration dictionary with user values merged over defaults.

    Raises:
        SystemExit: If PyYAML is not installed.
        FileNotFoundError: If config file doesn't exist.
    """
    if not HAS_YAML:
        print("Error: PyYAML is required for config files. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}

    # Deep merge with defaults
    config = DEFAULT_CONFIG.copy()
    for key, value in user_config.items():
        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
            config[key] = {**config[key], **value}
        else:
            config[key] = value

    return config


def get_config_template() -> str:
    """Generate a well-documented YAML config template for LLMs to customize."""
    return '''# =============================================================================
# Codebase Index Configuration
# =============================================================================
# This config file customizes how codebase_index scans your project.
#
# =============================================================================
# INSTRUCTIONS FOR LLM AGENTS (Claude Code, Cursor, etc.)
# =============================================================================
#
# BEFORE creating/editing this config:
#   1. Run: codebase-index . --summary --no-hash
#   2. Analyze the output to understand the project structure
#   3. Identify the framework (FastAPI, Django, Flask, Express, etc.)
#   4. Note any unusual patterns or conventions
#
# WHEN customizing this config:
#   - Only modify sections relevant to the detected framework
#   - Use regex patterns (escape backslashes: \\\\ in YAML)
#   - Test incrementally: change one thing, re-run, verify
#   - Use --verbose to see which patterns are matching
#
# AFTER creating the config:
#   codebase-index . --config this_file.yaml -o index.json -v
#
# =============================================================================
# DISCLAIMER: LIMITATIONS OF STATIC ANALYSIS
# =============================================================================
# This tool uses AST parsing and regex patterns. It MAY:
#
#   MISS: Dynamic routes, metaprogramming, runtime code generation,
#         decorators from unusual libraries, complex inheritance
#
#   FALSE POSITIVE: Patterns that look like routes/models but aren't,
#                   test fixtures that mimic production patterns
#
# Always verify critical findings. Customize patterns for your codebase.
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
# IMPORTANT: Auth detection is PRECISE - it only checks:
# 1. Function SIGNATURE (parameters) - for dependency injection patterns
# 2. Function DECORATORS - for decorator-based auth
#
# This prevents false positives from imports or nearby code.
#
# Format:
#   parameters: List of regex patterns checked against function signature
#   decorators: List of regex patterns checked against @ decorators
# =============================================================================
auth:
  enabled: true

  # Patterns matched against function PARAMETERS only
  # Example: def endpoint(current_user: User = Depends(get_current_user))
  parameters:
    # FastAPI dependency injection
    - "Depends\\\\s*\\\\(\\\\s*get_current_user"
    - "Depends\\\\s*\\\\(\\\\s*get_current_active_user"
    - "Depends\\\\s*\\\\(\\\\s*verify_token"
    - "Depends\\\\s*\\\\(\\\\s*require_auth"
    - "Depends\\\\s*\\\\(\\\\s*oauth2_scheme"
    # Type hint patterns
    - "current_user\\\\s*:\\\\s*\\\\w+"
    # Add your custom auth dependency patterns here
    # - "Depends\\\\s*\\\\(\\\\s*my_custom_auth"

  # Patterns matched against DECORATORS only (lines starting with @)
  # Example: @login_required
  decorators:
    - "@login_required"
    - "@require_auth"
    - "@authenticated"
    - "@jwt_required"
    - "@permission_required"
    - "@token_required"
    # Django REST Framework
    # - "@permission_classes"
    # Add your custom auth decorator patterns here

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

# =============================================================================
# EXCLUSIONS
# =============================================================================
# Directories and files to exclude from scanning.
# These are applied IN ADDITION to CLI --exclude-dirs and --exclude-ext flags.
# =============================================================================
exclude:
  # Directories to skip (relative to root)
  directories:
    # - .archive
    # - docs
    # - vendor
    # - third-party

  # File extensions to skip
  extensions:
    # - .md
    # - .txt
    # - .log

  # Glob patterns to skip
  patterns:
    # - "*.generated.*"
    # - "*.min.js"
'''
