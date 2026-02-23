"""Repository scan and agents.md generation."""

from pathlib import Path
from typing import List, Tuple

from llm.client import LLMClient
from utils.settings import file_settings


EXCLUDE_DIRS = file_settings.exclude_dirs
MAX_FILE_BYTES = file_settings.max_file_bytes
MAX_TOTAL_BYTES = file_settings.max_total_bytes


def _is_excluded(path: Path, repo_root: Path) -> bool:
    rel_parts = path.relative_to(repo_root).parts
    return any(part in EXCLUDE_DIRS for part in rel_parts)


def _read_file(path: Path) -> Tuple[str, str]:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        return "skipped_large", ""

    raw = path.read_bytes()
    if b"\x00" in raw:
        return "skipped_binary", ""

    text = raw.decode("utf-8", errors="replace")
    return "ok", text


def _collect_files(repo_root: Path) -> List[Path]:
    """Collect files from repository, respecting EXCLUDE_DIRS and .gitignore.

    Args:
        repo_root: Repository root directory

    Returns:
        List of Path objects for files to include
    """
    from utils.gitignore_filter import load_gitignore_spec, is_path_ignored

    # Load .gitignore spec
    gitignore_spec = load_gitignore_spec(repo_root)

    files = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue

        # Check hard-coded exclusions
        if _is_excluded(path, repo_root):
            continue

        # Check .gitignore
        if gitignore_spec is not None:
            is_ignored, _ = is_path_ignored(path, repo_root, gitignore_spec)
            if is_ignored:
                continue

        files.append(path)

    return sorted(files, key=lambda p: str(p.relative_to(repo_root)))


def _build_prompt(repo_root: Path, files: List[Path]) -> str:
    total_bytes = 0
    file_blocks = []
    for path in files:
        rel_path = path.relative_to(repo_root)
        status, text = _read_file(path)
        size = path.stat().st_size

        if status == "ok":
            if total_bytes + len(text.encode("utf-8")) > MAX_TOTAL_BYTES:
                status = "skipped_total_limit"
                text = ""
            else:
                total_bytes += len(text.encode("utf-8"))

        if status == "ok":
            content = text
        elif status == "skipped_large":
            content = "[skipped: file too large]"
        elif status == "skipped_binary":
            content = "[skipped: binary file]"
        else:
            content = "[skipped: total content limit reached]"

        block = (
            f"FILE: {rel_path}\n"
            f"SIZE: {size}\n"
            f"CONTENT:\n{content}\n"
        )
        file_blocks.append(block)

    files_payload = "\n".join(file_blocks)
    return (
        "Generate a concise agents.md for this repository.\n\n"
        "CRITICAL: Be extremely concise. Single-line descriptions only.\n\n"
        "Requirements:\n"
        "1) '# Files' section - bullets: `path` - one-line description\n"
        "2) '# Key Classes' section - bullets: **Class** (`path`) - one-line responsibility\n"
        "3) '# Architecture' section - compact flow diagrams showing entry points, data flow, tool-calling loop\n"
        "4) '# Configuration' section - grouped bullets: `VAR_1`, `VAR_2` - purpose\n"
        "5) '# Patterns' section - bullets: **Category**: description\n"
        "6) '# Summary' section - 1-2 sentences max\n\n"
        "Style rules:\n"
        "- One line per file/class description\n"
        "- No verbose explanations or implementation details\n"
        "- Use arrows (→) for flows instead of numbered lists\n"
        "- Group related config vars on single line\n"
        "- Focus on WHAT and WHERE, not HOW\n"
        "- Return ONLY markdown, no code blocks\n\n"
        f"REPO_ROOT: {repo_root}\n\n"
        f"{files_payload}"
    )


def run_init(repo_root: Path, console) -> None:
    """Scan repo files with the LLM and write agents.md."""
    console.print("[yellow]Generating agents.md with LLM scan...[/yellow]")

    files = _collect_files(repo_root)
    if not files:
        console.print("[red]No files found to scan.[/red]")
        return

    prompt = _build_prompt(repo_root, files)
    client = LLMClient()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a documentation generator for a codebase. "
                "Follow the user's formatting requirements exactly."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = client.chat_completion(messages, stream=False)
    if isinstance(response, str):
        console.print(f"[red]{response}[/red]", markup=False)
        return

    content = None
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None

    if not content or not content.strip():
        console.print("[red]LLM returned empty content.[/red]")
        return

    output_path = Path(__file__).resolve().parents[1] / "agents.md"
    output_path.write_text(content.strip() + "\n", encoding="utf-8")
    console.print(f"[green]Generated {output_path.name} successfully![/green]")
