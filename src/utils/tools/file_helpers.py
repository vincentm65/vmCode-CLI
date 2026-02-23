"""Shared utilities for file operations."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from utils.gitignore_filter import ALWAYS_ALLOWED_FILES

# Fast-path patterns that should never be checked against spec
FAST_IGNORE_DIRS = {".git", ".venv", "__pycache__", "node_modules", "venv", "env", ".env"}
# Keep this list to high-signal "noise" files only; avoid blocking common lockfiles that may be relevant.
FAST_IGNORE_FILES = {".DS_Store", "Thumbs.db"}

_GITIGNORE_SPEC_REGISTRY = {}


def _is_fast_ignored(path: Path) -> bool:
    """Quick check for common ignore patterns without spec lookup.

    Args:
        path: Path to check

    Returns:
        True if path matches fast-path ignore patterns
    """
    if path.name in ALWAYS_ALLOWED_FILES:
        return False
    if path.name in FAST_IGNORE_FILES:
        return True
    if any(part in FAST_IGNORE_DIRS for part in path.parts):
        return True
    return False


def _register_gitignore_spec(gitignore_spec) -> int:
    """Register a PathSpec for cached lookups and return its key.

    Args:
        gitignore_spec: PathSpec object to register

    Returns:
        Registry key for the PathSpec object
    """
    if gitignore_spec is None:
        return 0
    key = id(gitignore_spec)
    _GITIGNORE_SPEC_REGISTRY[key] = gitignore_spec
    return key


@lru_cache(maxsize=1000)
def _is_ignored_cached(path_str: str, repo_root_str: str, spec_key: int) -> bool:
    """Cached version of gitignore check.

    Args:
        path_str: String representation of path to check
        repo_root_str: String representation of repository root
        spec_key: Registry key for the PathSpec object

    Returns:
        True if path is ignored by gitignore spec
    """
    gitignore_spec = _GITIGNORE_SPEC_REGISTRY.get(spec_key)
    if gitignore_spec is None:
        return False

    from utils.gitignore_filter import is_path_ignored

    path = Path(path_str)
    repo_root = Path(repo_root_str)
    is_ignored, _ = is_path_ignored(path, repo_root, gitignore_spec)
    return is_ignored


def _is_reserved_windows_name(name: str) -> bool:
    """Check if filename is a reserved Windows device name.

    Args:
        name: Filename to check (without path)

    Returns:
        True if name is reserved (e.g., CON, PRN, NUL)
    """
    if not name:
        return False
    base = name.upper().split('.')[0]
    return base in {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }


def validate_path_within_repo(path: Path, repo_root: Path) -> Tuple[bool, Optional[str]]:
    """Validate that a resolved path is within the repository root.

    Args:
        path: Resolved path to validate
        repo_root: Repository root directory

    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if path != repo_root and not path.is_relative_to(repo_root):
        return False, f"Path is outside allowed root: {path}"
    return True, None
