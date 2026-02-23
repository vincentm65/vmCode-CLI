"""Tool execution utilities.

This package provides command execution, file editing, and result formatting
capabilities for the vmCode AI assistant.
"""

# Command execution
from .command_executor import (
    confirm_tool,
    run_shell_command,
)
# File editing
from .file_editor import (
    _resolve_repo_path,
    preview_edit_file,
    run_edit_file,
)

# Result formatting
from .formatters import (
    format_tool_result,
    format_file_result,
    _build_diff,
    _detect_newline,
)

# File operations
from .directory import list_directory
from .create_file import create_file
from .file_reader import read_file

# Tool definitions
from .definitions import TOOLS, _tools_for_mode

__all__ = [
    # Command execution
    'confirm_tool',
    'run_shell_command',
    # File editing
    '_resolve_repo_path',
    'preview_edit_file',
    'run_edit_file',
    # Formatters
    'format_tool_result',
    'format_file_result',
    '_build_diff',
    '_detect_newline',
    # File operations
    'read_file',
    'list_directory',
    'create_file',
    # Tool definitions
    'TOOLS',
    '_tools_for_mode',
]
