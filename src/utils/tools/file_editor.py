"""File editing operations with preview and diff generation."""

import os
import re
from pathlib import Path
from exceptions import PathValidationError, FileEditError

from .formatters import _build_diff, _detect_newline, _normalize_search_replace_for_newlines

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_line_for_match(line, *, collapse_whitespace):
    line = line.rstrip("\r\n")
    if collapse_whitespace:
        return _WHITESPACE_RE.sub(" ", line).strip()
    return line.rstrip(" \t")


def _find_spans_by_line_normalization(content, search_text, *, collapse_whitespace):
    file_lines = content.splitlines(keepends=True)
    search_lines = search_text.splitlines(keepends=False)
    if not search_lines:
        return []

    normalized_search = [
        _normalize_line_for_match(line, collapse_whitespace=collapse_whitespace)
        for line in search_lines
    ]
    normalized_file = [
        _normalize_line_for_match(line, collapse_whitespace=collapse_whitespace)
        for line in file_lines
    ]

    offsets = [0]
    for line in file_lines:
        offsets.append(offsets[-1] + len(line))

    first = normalized_search[0]
    n = len(normalized_search)
    spans = []
    for i, file_line in enumerate(normalized_file):
        if file_line != first:
            continue
        if normalized_file[i:i + n] == normalized_search:
            spans.append((offsets[i], offsets[i + n]))
    return spans


def _build_whitespace_insensitive_pattern(search_text):
    parts = []
    i = 0
    while i < len(search_text):
        ch = search_text[i]
        if ch.isspace():
            while i < len(search_text) and search_text[i].isspace():
                i += 1
            parts.append(r"\s+")
            continue
        parts.append(re.escape(ch))
        i += 1
    return re.compile("".join(parts))


def _build_fully_whitespace_agnostic_pattern(search_text):
    parts = []
    for i, ch in enumerate(search_text):
        if ch.isspace():
            continue
        parts.append(re.escape(ch))
        if i != len(search_text) - 1:
            parts.append(r"\s*")
    return re.compile("".join(parts))


def _find_unique_span_with_fallbacks(content, search_text):
    count = content.count(search_text)
    if count == 1:
        start = content.index(search_text)
        return (start, start + len(search_text))
    if count > 1:
        raise FileEditError(
            f"Search text appears {count} times in file (must be unique)",
            details={"count": count, "hint": "Add more surrounding context to make it unique"}
        )

    if "\n" in search_text or "\r" in search_text:
        spans = _find_spans_by_line_normalization(
            content, search_text, collapse_whitespace=False
        )
        if len(spans) == 1:
            return spans[0]
        if len(spans) > 1:
            raise FileEditError(
                f"Search text appears {len(spans)} times in file (must be unique)",
                details={"count": len(spans), "hint": "Add more surrounding context to make it unique"}
            )

        spans = _find_spans_by_line_normalization(
            content, search_text, collapse_whitespace=True
        )
        if len(spans) == 1:
            return spans[0]
        if len(spans) > 1:
            raise FileEditError(
                f"Search text appears {len(spans)} times in file (must be unique)",
                details={"count": len(spans), "hint": "Add more surrounding context to make it unique"}
            )

    pattern = _build_whitespace_insensitive_pattern(search_text)
    matches = list(pattern.finditer(content))
    if len(matches) == 1:
        return matches[0].span()
    if len(matches) > 1:
        raise FileEditError(
            f"Search text appears {len(matches)} times in file (must be unique)",
            details={"count": len(matches), "hint": "Add more surrounding context to make it unique"}
        )

    if not any(ch.isspace() for ch in search_text):
        pattern = _build_fully_whitespace_agnostic_pattern(search_text)
        matches = list(pattern.finditer(content))
        if len(matches) == 1:
            return matches[0].span()
        if len(matches) > 1:
            raise FileEditError(
                f"Search text appears {len(matches)} times in file (must be unique)",
                details={"count": len(matches), "hint": "Add more surrounding context to make it unique"}
            )
    return None


def _resolve_repo_path(path_str, repo_root, gitignore_spec=None):
    """Resolve and validate a path within the repo.

    Args:
        path_str: Path string to resolve
        repo_root: Repository root directory
        gitignore_spec: Optional pathspec.PathSpec for .gitignore filtering

    Returns:
        Resolved Path object

    Raises:
        PathValidationError: If path is invalid, outside repo, or blocked by .gitignore
    """
    raw_path = Path(path_str)
    if not raw_path.is_absolute():
        raw_path = repo_root / raw_path
    resolved = raw_path.resolve()
    if resolved != repo_root and not resolved.is_relative_to(repo_root):
        raise PathValidationError(
            "Path is outside allowed root",
            details={"path": str(resolved), "repo_root": str(repo_root)}
        )

    # Check .gitignore (if spec provided)
    if gitignore_spec is not None:
        from utils.gitignore_filter import is_path_ignored, format_gitignore_error

        is_ignored, matched_pattern = is_path_ignored(
            resolved, repo_root, gitignore_spec
        )
        if is_ignored:
            # Create descriptive error
            error_msg = format_gitignore_error(resolved, repo_root, matched_pattern)
            raise PathValidationError(
                f"Path blocked by .gitignore: {error_msg}",
                details={"path": str(resolved), "pattern": matched_pattern}
            )

    return resolved


def _prepare_edit(arguments, repo_root, gitignore_spec=None):
    """Prepare edit operation with validation.

    Args:
        arguments: Edit arguments dict
        repo_root: Repository root
        gitignore_spec: Optional PathSpec for .gitignore filtering

    Returns:
        Tuple of (status_string, payload_dict or None)

    Raises:
        PathValidationError: If path is invalid or blocked by .gitignore
        FileEditError: If file cannot be read or edit is invalid
    """
    path = arguments.get("path")
    if not path or not isinstance(path, str) or not path.strip():
        raise FileEditError("Missing or invalid 'path' parameter")

    # Use updated _resolve_repo_path with gitignore checking
    try:
        file_path = _resolve_repo_path(path, repo_root, gitignore_spec)
    except PathValidationError as e:
        # Re-raise with additional context
        raise FileEditError(str(e), details=e.details)

    if not file_path.exists():
        raise FileEditError(
            f"File not found",
            details={"path": str(file_path)}
        )

    search = arguments.get("search")
    replace = arguments.get("replace")

    if search is None:
        raise FileEditError("'search' parameter is required")
    if replace is None:
        raise FileEditError("'replace' parameter is required")
    if not isinstance(search, str):
        raise FileEditError("'search' must be a string")
    if not isinstance(replace, str):
        raise FileEditError("'replace' must be a string")
    if search == "":
        raise FileEditError("'search' must be non-empty")

    try:
        with file_path.open("r", encoding="utf-8", newline="") as f:
            original_content = f.read()
    except Exception as e:
        raise FileEditError(
            f"Failed to read file",
            details={"path": str(file_path), "original_error": str(e)}
        )

    file_newline = _detect_newline(original_content)
    search, replace, _ = _normalize_search_replace_for_newlines(
        search, replace, file_newline
    )

    search_span = _find_unique_span_with_fallbacks(original_content, search)
    if search_span is None:
        search_preview = search[:200] + "..." if len(search) > 200 else search
        raise FileEditError(
            "Search text not found in file",
            details={
                "search_preview": search_preview,
                "hint": "Try adding more surrounding context (including nearby lines) to disambiguate whitespace/indentation differences."
            }
        )

    context_lines = arguments.get("context_lines", 3)
    if not isinstance(context_lines, int) or context_lines < 0:
        context_lines = 3

    color_mode = arguments.get("color", "auto")
    if color_mode not in ("auto", "on", "off"):
        color_mode = "auto"

    return "exit_code=0", {
        "file_path": file_path,
        "original_content": original_content,        "search_span": search_span,
        "replace": replace,
        "context_lines": context_lines,
        "color_mode": color_mode,
    }


def preview_edit_file(arguments, repo_root, gitignore_spec=None):
    """Build a line-numbered diff preview without writing changes.

    Returns:
        Tuple of (status_string, diff_text or None)

    Raises:
        FileEditError: If edit validation fails
    """
    status, payload = _prepare_edit(arguments, repo_root, gitignore_spec)

    start, end = payload["search_span"]
    new_content = (
        payload["original_content"][:start]
        + payload["replace"]
        + payload["original_content"][end:]
    )
    diff_text = _build_diff(
        payload["original_content"],
        new_content,
        payload["file_path"],
        payload["context_lines"],
        "on",
        show_header=True,
        repo_root=repo_root,
    )
    return "exit_code=0", diff_text


def run_edit_file(arguments, repo_root, console, debug_mode, gitignore_spec=None):
    """Apply search/replace edit to a file.

    Args:
        arguments: {
            "path": "path/to/file",
            "search": "exact text to find (required)",
            "replace": "replacement text (required)",
            "context_lines": 3  # optional, for diff display
        }
        repo_root: Repository root
        console: Rich console for output
        debug_mode: Whether to show debug output
        gitignore_spec: Optional PathSpec for .gitignore filtering

    Returns:
        str: Formatted result with exit_code=0 or exit_code=1
    """
    try:
        status, payload = _prepare_edit(arguments, repo_root, gitignore_spec)

        start, end = payload["search_span"]
        new_content = (
            payload["original_content"][:start]
            + payload["replace"]
            + payload["original_content"][end:]
        )

        # Generate diff for preview
        diff_text = _build_diff(
            payload["original_content"],
            new_content,
            payload["file_path"],
            payload["context_lines"],
            payload["color_mode"],
        )

        # Write to file
        try:
            with payload["file_path"].open("w", encoding="utf-8", newline="") as f:
                f.write(new_content)
        except Exception as e:
            raise FileEditError(
                f"Failed to write file",
                details={"path": str(payload["file_path"]), "original_error": str(e)}
            )

        # Success
        return f"exit_code=0\n\nDiff:\n{diff_text}\n\n"

    except FileEditError as e:
        # Return formatted error string for backward compatibility
        error_msg = str(e)
        if e.details:
            details_str = "\n".join(f"  {k}: {v}" for k, v in e.details.items())
            return f"exit_code=1\n{error_msg}\n{details_str}\n\n"
        return f"exit_code=1\n{error_msg}\n\n"
    except Exception as exc:
        return f"exit_code=1\n{exc}\n\n"
