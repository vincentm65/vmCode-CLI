"""Markdown preprocessing utilities for vmCode."""

import re


_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def left_align_headings(markdown: str) -> str:
    """Strip markdown heading markers to avoid Rich's centering.

    Rich's Markdown renderer centers headings by default. This function
    removes the ``#`` markers and uppercases the heading text instead.

    Args:
        markdown: Raw markdown string

    Returns:
        Markdown string with headings converted to plain uppercase text.
    """
    return _HEADING_RE.sub(lambda m: m.group(2).upper(), markdown)



