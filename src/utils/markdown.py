"""Markdown preprocessing utilities for vmCode."""

import re
from typing import Union

from rich.text import Text


def left_align_headings(markdown: str) -> str:
    """Convert markdown headings to bold text to avoid Rich's centering.
    
    Rich's Markdown renderer centers headings by default. This function
    converts them to bold text for consistent left alignment.
    
    Args:
        markdown: Raw markdown string
        
    Returns:
        Markdown string with headings converted to bold
    """
    # Replace headings with bold text
    # h1-h6 with optional leading whitespace
    patterns = [
        (r'^###### (.+)$', r'******\1******'),  # h6 -> bold
        (r'^##### (.+)$', r'*****\1*****'),      # h5 -> bold  
        (r'^#### (.+)$', r'****\1****'),         # h4 -> bold
        (r'^### (.+)$', r'***\1***'),            # h3 -> bold
        (r'^## (.+)$', r'**\1**'),               # h2 -> bold
        (r'^# (.+)$', r'**\1**'),                # h1 -> bold
    ]
    
    for pattern, replacement in patterns:
        markdown = re.sub(pattern, replacement, markdown, flags=re.MULTILINE)
    
    return markdown


def colorize_review_severity(rendered: Union[str, Text]) -> Text:
    """Apply Rich color styling to severity labels and verdicts.

    Operates on a *rendered* Rich object (Text or plain string) so that
    Markdown's parser doesn't strip the styling tags.

    Must be called **after** ``rich.markdown.Markdown`` has rendered the
    content to a ``Text`` instance.

    Args:
        rendered: A Rich ``Text`` object or plain string to highlight.

    Returns:
        A ``Text`` object with colored severity/verdict spans.
    """
    text = Text(rendered) if isinstance(rendered, str) else rendered.copy()

    # Severity labels (order matters: longer patterns first)
    text.highlight_regex(r'\[critical\]', 'bold red')
    text.highlight_regex(r'\[warning\]', 'bold yellow')
    text.highlight_regex(r'\[info\]', 'white')

    # Verdict labels
    text.highlight_regex(r'\bREQUEST CHANGES\b', 'bold red')
    text.highlight_regex(r'\bAPPROVE\b', 'bold green')

    return text
