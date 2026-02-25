"""Centralized .gitignore filtering using pathspec library."""

from pathlib import Path
from typing import Optional, Tuple

# Always allow .gitignore itself to be read/edited
ALWAYS_ALLOWED_FILES = {".gitignore"}


def load_gitignore_spec(repo_root: Path):
    """Load .gitignore patterns into a PathSpec object.

    Args:
        repo_root: Repository root directory

    Returns:
        pathspec.PathSpec or None if .gitignore doesn't exist
    """
    gitignore_path = repo_root / ".gitignore"

    if not gitignore_path.exists():
        return None

    try:
        import pathspec

        # Read .gitignore patterns
        patterns = gitignore_path.read_text(encoding="utf-8").splitlines()

        # Create PathSpec with gitwildmatch (git's pattern matching)
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        return spec

    except Exception as e:
        return None


def is_path_ignored(
    path: Path, repo_root: Path, gitignore_spec
) -> Tuple[bool, Optional[str]]:
    """Check if a path is ignored by .gitignore.

    Args:
        path: Absolute path to check
        repo_root: Repository root directory
        gitignore_spec: pathspec.PathSpec object (or None)

    Returns:
        Tuple of (is_ignored, matched_pattern)
        - is_ignored: True if path should be blocked
        - matched_pattern: The pattern that matched (or None)
    """
    # No filtering if no .gitignore
    if gitignore_spec is None:
        return False, None

    # Always allow .gitignore itself
    if path.name in ALWAYS_ALLOWED_FILES:
        return False, None

    # Get relative path from repo root (gitignore only applies within repo)
    try:
        rel_path = path.relative_to(repo_root)
    except ValueError:
        # Path is outside repo - gitignore doesn't apply
        return False, None

    # Convert to forward slashes (git convention)
    rel_path_str = str(rel_path).replace("\\", "/")

    # Check if path matches any .gitignore pattern
    # pathspec.match_file() returns True if the file should be ignored
    if gitignore_spec.match_file(rel_path_str):
        # Find which pattern matched (for better error messages)
        matched_pattern = _find_matching_pattern(rel_path_str, gitignore_spec)
        return True, matched_pattern

    return False, None


def _find_matching_pattern(path_str: str, gitignore_spec) -> Optional[str]:
    """Find which .gitignore pattern matched a path.

    This is for better error messages.

    Args:
        path_str: Relative path string (with forward slashes)
        gitignore_spec: pathspec.PathSpec object

    Returns:
        The matching pattern string, or None
    """
    try:
        # PathSpec stores patterns internally
        for pattern in gitignore_spec.patterns:
            if pattern.match_file(path_str):
                # Return the original pattern string
                return pattern.pattern
    except Exception:
        pass

    return None


def format_gitignore_error(
    path: Path, repo_root: Path, matched_pattern: Optional[str]
) -> str:
    """Format a user-friendly error message for .gitignore blocked files.

    Args:
        path: The blocked file path
        repo_root: Repository root
        matched_pattern: The .gitignore pattern that matched

    Returns:
        Formatted error message
    """
    try:
        rel_path = path.relative_to(repo_root)
    except ValueError:
        rel_path = path

    error_msg = (
        f"exit_code=ERROR_GITIGNORE_BLOCKED\n"
        f"File blocked by .gitignore: {rel_path}\n\n"
    )
    error_msg += "This file matches patterns in .gitignore and cannot be accessed.\n"

    if matched_pattern:
        error_msg += f"Matched pattern: {matched_pattern}\n"

    error_msg += "\nTo access this file:\n"
    error_msg += "1. Remove it from .gitignore, or\n"
    error_msg += "2. Use git commands directly (git show, git diff)\n"

    return error_msg


def filter_paths_list(paths: list, repo_root: Path, gitignore_spec) -> list:
    """Filter a list of paths, removing ignored ones.

    Used for file scanning operations.

    Args:
        paths: List of Path objects
        repo_root: Repository root
        gitignore_spec: pathspec.PathSpec object (or None)

    Returns:
        Filtered list of Path objects
    """
    if gitignore_spec is None:
        return paths

    filtered = []
    for path in paths:
        is_ignored, _ = is_path_ignored(path, repo_root, gitignore_spec)
        if not is_ignored:
            filtered.append(path)

    return filtered
