"""External editor integration for bone-agent."""
import os
import platform
import shlex
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional


def get_editor() -> str:
    """Get editor command with OS-specific defaults.

    Priority:
    1. Windows: notepad.exe
    2. Linux: nvim, then EDITOR, then nano/vi/vim
    3. Other Unix: EDITOR, then nano/vi/vim

    Returns:
        str: Editor command or path
    """
    system = platform.system()

    if system == "Windows":
        return "notepad.exe"

    if system == "Linux" and shutil.which("nvim"):
        return "nvim"

    editor = os.environ.get("EDITOR")
    if editor and editor.strip():
        return editor.strip()

    for cmd in ["nano", "vi", "vim"]:
        if shutil.which(cmd):
            return cmd

    return "nano"


def _create_temp_file() -> Tuple[Path, object]:
    """Create temporary file for editing.

    Returns:
        tuple: (Path object, file handle)
    """
    # Create with .md extension for better syntax highlighting
    temp_fd = tempfile.NamedTemporaryFile(
        mode='w+',
        suffix='.md',
        prefix='bone_agent_edit_',
        delete=False,
        encoding='utf-8'
    )

    temp_fd.flush()

    return Path(temp_fd.name), temp_fd


def _strip_comment_lines(content: str) -> str:
    """Remove comment lines (starting with #) from content.

    Args:
        content: Raw content from editor

    Returns:
        str: Content with comment lines removed
    """
    lines = []
    for line in content.split('\n'):
        stripped = line.strip()
        # Keep empty lines and non-comment lines
        if not stripped.startswith('#'):
            lines.append(line)

    return '\n'.join(lines).strip()


def _build_editor_command(editor_cmd: str, temp_path: Path) -> Tuple[bool, str | list[str]]:
    """Build a subprocess command for launching the configured editor."""
    use_shell = platform.system() == "Windows"
    if use_shell:
        return use_shell, f'{editor_cmd} "{temp_path}"'

    try:
        command_parts = shlex.split(editor_cmd)
    except ValueError as e:
        raise ValueError(f"Invalid EDITOR command: {e}") from e

    if not command_parts:
        raise FileNotFoundError(editor_cmd)

    return use_shell, [*command_parts, str(temp_path)]


def _open_editor_with_temp_file(
    console,
    editor_cmd: str,
    debug_mode: bool = False,
    initial_content: str = "",
    post_process=None,
) -> Tuple[bool, Optional[str]]:
    """Open the configured editor for a temporary file and return the saved content."""
    temp_path = None

    try:
        temp_path, temp_fd = _create_temp_file()
        if initial_content:
            temp_fd.write(initial_content)
            temp_fd.flush()
        temp_fd.close()

        if debug_mode:
            console.print(f"[dim]Temp file: {temp_path}[/dim]")
            console.print(f"[dim]Editor: {editor_cmd}[/dim]")

        console.print("[#5F9EA0]Opening editor...[/#5F9EA0]")
        console.print("[dim]Save and close the editor when done[/dim]")

        use_shell, command = _build_editor_command(editor_cmd, temp_path)
        result = subprocess.run(
            command,
            shell=use_shell,
            check=False,
        )

        if result.returncode != 0 and debug_mode:
            console.print(f"[yellow]Editor exited with code {result.returncode}[/yellow]")

        content = temp_path.read_text(encoding="utf-8")
        if post_process is not None:
            content = post_process(content)

        if debug_mode:
            console.print(f"[dim]Read {len(content)} characters[/dim]")

        return (True, content)

    except FileNotFoundError:
        console.print(f"[red]Editor '{editor_cmd}' not found[/red]", markup=False)
        console.print("[dim]Set EDITOR as environment variable[/dim]")
        if debug_mode:
            console.print(f"[dim]Tried to run: {editor_cmd}[/dim]")
        return (False, None)

    except PermissionError as e:
        console.print(f"[red]Permission denied: {e}[/red]", markup=False)
        console.print("[dim]Check permissions on temporary directory[/dim]")
        return (False, None)

    except Exception as e:
        console.print(f"[red]Failed to open editor: {e}[/red]", markup=False)
        if debug_mode:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return (False, None)

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
                if debug_mode:
                    console.print("[dim]Cleaned up temp file[/dim]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to delete temp file: {e}[/yellow]")
                if debug_mode:
                    console.print(f"[dim]Temp file may remain at: {temp_path}[/dim]")


def open_editor_for_input(console, debug_mode: bool = False) -> Tuple[bool, Optional[str]]:
    """Open external editor and return user input.

    Args:
        console: Rich console for output
        debug_mode: Whether to show debug information

    Returns:
        tuple: (success: bool, content: str or None)
            - (True, content) if successful
            - (False, None) if failed or cancelled
    """
    return _open_editor_with_temp_file(
        console,
        editor_cmd=get_editor(),
        debug_mode=debug_mode,
        post_process=_strip_comment_lines,
    )


def open_editor_for_content(
    console,
    initial_content: str = "",
    debug_mode: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Open external editor with initial content and return the saved file.

    Unlike open_editor_for_input, this preserves markdown comment lines so it can
    edit existing markdown files without dropping headings or notes.
    """
    return _open_editor_with_temp_file(
        console,
        editor_cmd=get_editor(),
        debug_mode=debug_mode,
        initial_content=initial_content or "",
    )
