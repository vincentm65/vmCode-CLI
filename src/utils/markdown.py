"""Markdown preprocessing utilities for vmCode."""

import re


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
