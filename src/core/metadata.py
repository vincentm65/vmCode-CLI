"""AI-powered metadata generation for skills and plugins.

Generates description and tags from content when not provided manually.
Shared between skill frontmatter and plugin registration.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You generate concise metadata for code tools and prompts.

Given the content below, return a JSON object with exactly two fields:
- "description": a one-sentence summary (max 120 chars) of what this does
- "tags": a list of 3-7 lowercase single-word tags for discovery

Return ONLY the JSON object, no other text."""

_MAX_CONTENT_CHARS = 3000


def generate_metadata(content: str, name: str = "") -> dict:
    """Generate description and tags from content using the LLM.

    Args:
        content: The skill prompt or plugin source to describe.
        name: Optional name for context.

    Returns:
        Dict with 'description' (str) and 'tags' (list[str]).
        Returns defaults on failure.
    """
    truncated = content[:_MAX_CONTENT_CHARS]
    if len(content) > _MAX_CONTENT_CHARS:
        truncated += "\n..."

    user_msg = f"Name: {name}\n\n{truncated}" if name else truncated

    try:
        from llm.client import LLMClient

        client = LLMClient()
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            stream=False,
            tools=None,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        parsed = json.loads(raw)

        description = str(parsed.get("description", ""))[:120]
        tags = [str(t).lower() for t in parsed.get("tags", []) if t]

        return {"description": description, "tags": tags}

    except Exception:
        logger.debug("Metadata generation failed for '%s'", name, exc_info=True)
        return _fallback_metadata(content, name)


def _fallback_metadata(content: str, name: str) -> dict:
    """Simple heuristic metadata when LLM is unavailable."""
    # Use first line or first ~100 chars as description
    first_line = content.strip().split("\n", 1)[0].strip()
    desc = first_line[:120] if first_line else name
    return {"description": desc, "tags": [name] if name else []}
