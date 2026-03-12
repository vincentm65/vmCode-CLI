"""Result parsing utilities for tool outputs."""

from typing import Optional


def extract_exit_code(tool_result: str) -> Optional[int]:
    """Parse exit_code from tool result string.

    Args:
        tool_result: Tool result content string

    Returns:
        Exit code as integer, or None if not found
    """
    if not isinstance(tool_result, str):
        return None
    first_line = tool_result.splitlines()[0] if tool_result else ""
    if first_line.startswith("exit_code="):
        try:
            value = first_line.split("=", 1)[1].strip()
            value = value.split()[0] if value else value
            return int(value)
        except ValueError:
            return None
    return None


def extract_metadata_from_result(tool_result: str, key: str) -> Optional[int]:
    """Parse metadata like matches_found, lines_read, etc. from tool result.

    Args:
        tool_result: Tool result content string
        key: Metadata key to extract (e.g., "matches_found", "lines_read")

    Returns:
        Extracted value as int, or None if not found
    """
    if not isinstance(tool_result, str):
        return None
    for line in tool_result.split('\n'):
        if line.startswith(f'{key}='):
            try:
                return int(line.split('=')[1].split()[0])
            except (ValueError, IndexError):
                return None
    return None


def extract_all_metadata(tool_result: str, line_index: int = 0) -> dict:
    """Parse entire metadata line into a dictionary.

    Parses space-separated key=value pairs from a specific line.
    Follows format defined in src/tools/helpers/formatters.py.

    Args:
        tool_result: Tool result string
        line_index: Which line to parse (default: 0, use 1 for rg results)

    Returns:
        dict with all parsed metadata (e.g., {'exit_code': 0, 'lines_read': 123, ...})
        Returns empty dict if tool_result is invalid or line_index out of range
    """
    if not isinstance(tool_result, str) or not tool_result:
        return {}

    lines = tool_result.split('\n')
    if line_index >= len(lines):
        return {}

    line = lines[line_index].strip()
    if not line:
        return {}

    metadata = {}
    # Parse: exit_code=0 path=file.py lines_read=123 start_line=1
    for pair in line.split():
        if '=' in pair:
            key, value = pair.split('=', 1)
            # Skip empty values
            if not value:
                continue
            # Try to parse as int, keep as string if fails
            try:
                value = int(value)
            except ValueError:
                # Keep as string (e.g., paths, error messages)
                pass
            metadata[key] = value

    return metadata


def extract_multiple_metadata(tool_result: str, *keys: str, line_index: int = 0) -> dict:
    """Extract specific metadata keys from a tool result line.

    Args:
        tool_result: Tool result string
        *keys: Metadata keys to extract (e.g., 'lines_read', 'start_line')
        line_index: Which line to parse (default: 0)

    Returns:
        dict mapping keys to their parsed values
        Missing keys are not included in the result
    """
    all_metadata = extract_all_metadata(tool_result, line_index=line_index)

    # Return only requested keys that exist
    return {key: all_metadata[key] for key in keys if key in all_metadata}
