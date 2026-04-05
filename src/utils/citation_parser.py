"""Citation parser for sub-agent results.

Parses bracketed citation patterns from sub-agent output and injects
the actual file contents. This module is the single source of truth
for the citation format contract between sub-agent and main agent.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Citation:
    """A parsed file citation from sub-agent output."""
    rel_path: str
    start_line: int
    end_line: Optional[int] = None  # None means full file


# Regex to find explicit citation patterns (bracketed notation only for safety)
CITATION_PATTERN = re.compile(
    r"(?:-\s+\[(.*?)\]\s+\((?:lines\s+)?(\d+)-(\d+)(?:\s*lines)?|full)\)|"
    r"(?:lines\s+(\d+)-(\d+)\s+in\s+\[(.*?)\])|"
    r"(?:\[(.*?)\]:(\d+)-(\d+))|"
    r"(?:\[(.*?)\]:(\d+))|"
    r"(?:\[([^\]]*?/[^\]]*?)\](?![:(]))"
)


def parse_citations(text: str) -> List[Citation]:
    """Parse bracketed citation patterns from sub-agent output.

    Supports these formats:
        - [path/to/file] (lines N-M)    or (full)
        - lines N-M in [path/to/file]
        - [path/to/file]:N-M
        - [path/to/file]:N
        - [path/to/file]                 (full file)

    Args:
        text: Sub-agent result text to parse

    Returns:
        List of Citation instances found in the text
    """
    citations = []

    for line in text.split('\n'):
        match = CITATION_PATTERN.search(line)
        if not match:
            continue

        if match.group(1):
            # Pattern 1: - [file] (N-M) or (full)
            rel_path = match.group(1).strip()
            if match.group(2) and match.group(3):
                start_line = int(match.group(2))
                end_line = int(match.group(3))
            else:
                start_line = 1
                end_line = None
        elif match.group(4) and match.group(5) and match.group(6):
            # Pattern 2: lines N-M in [file]
            start_line = int(match.group(4))
            end_line = int(match.group(5))
            rel_path = match.group(6).strip()
        elif match.group(7) and match.group(8) and match.group(9):
            # Pattern 3: [file]:N-M
            rel_path = match.group(7).strip()
            start_line = int(match.group(8))
            end_line = int(match.group(9))
        elif match.group(10) and match.group(11):
            # Pattern 4: [file]:N (single line)
            rel_path = match.group(10).strip()
            start_line = int(match.group(11))
            end_line = start_line
        elif match.group(12):
            # Pattern 5: [file] (full file)
            rel_path = match.group(12).strip()
            start_line = 1
            end_line = None
        else:
            continue

        citations.append(Citation(
            rel_path=rel_path,
            start_line=start_line,
            end_line=end_line,
        ))

    return citations


def _format_header(citation: Citation, lines_read: Optional[int], actual_start_line: Optional[int]) -> str:
    """Format a citation header string for injected content.

    Args:
        citation: The Citation being formatted
        lines_read: Actual number of lines read (from metadata)
        actual_start_line: Actual start line (from metadata)

    Returns:
        Formatted header string like "lines 45-78 (34 lines)"
    """
    if lines_read is not None:
        actual_start = actual_start_line or citation.start_line
        if actual_start > 1:
            end = actual_start + lines_read - 1
        else:
            end = lines_read
        line_label = "line" if lines_read == 1 else "lines"
        return f"lines {actual_start}-{end} ({lines_read} {line_label})"
    return "full"


def inject_file_contents(
    raw_result: str,
    repo_root: Path,
    gitignore_spec=None,
    console=None,
) -> str:
    """Parse sub-agent result and inject actual file contents.

    Extracts citations from the sub-agent output, reads the referenced
    files, and appends the content in a structured format that the main
    agent can use directly.

    Args:
        raw_result: Sub-agent result text containing citations
        repo_root: Repository root directory
        gitignore_spec: PathSpec for .gitignore filtering
        console: Rich console for output (unused, kept for API compat)

    Returns:
        Combined string with original result + injected file contents,
        or just the original result if no citations were found
    """
    from tools.file_reader import read_file as read_file_with_bypass
    from utils.result_parsers import extract_multiple_metadata

    citations = parse_citations(raw_result)
    if not citations:
        return raw_result

    injected_files_content = []

    for citation in citations:
        max_lines = None
        if citation.end_line is not None:
            max_lines = citation.end_line - citation.start_line + 1

        try:
            tool_result = read_file_with_bypass(
                citation.rel_path,
                repo_root,
                max_lines=max_lines,
                start_line=citation.start_line,
                gitignore_spec=gitignore_spec,
            )

            # Check for exit code
            first_line = tool_result.split('\n')[0] if tool_result else ""
            if first_line.startswith("exit_code="):
                exit_code = first_line.split("=")[1].split()[0]
                if exit_code != "0":
                    injected_files_content.append(
                        f"### {citation.rel_path} (Blocked or unavailable)"
                    )
                    injected_files_content.append(tool_result.strip())
                    injected_files_content.append("")
                    continue

            # Strip metadata line and extract content
            content_lines = tool_result.splitlines()[1:] if isinstance(tool_result, str) else []
            content = "\n".join(content_lines).rstrip()

            # Parse actual lines_read and start_line from metadata
            metadata = extract_multiple_metadata(tool_result, 'lines_read', 'start_line')
            lines_read = metadata.get('lines_read')
            actual_start = metadata.get('start_line')

            header_info = _format_header(citation, lines_read, actual_start)

            injected_files_content.append(f"### {citation.rel_path} ({header_info})")
            injected_files_content.append("```")
            injected_files_content.append(content)
            injected_files_content.append("```\n")

        except Exception as e:
            injected_files_content.append(
                f"### {citation.rel_path} (Error reading file: {e})"
            )

    if not injected_files_content:
        return raw_result

    return raw_result + "\n\n## Injected File Contents\n\n" + "\n".join(injected_files_content)
