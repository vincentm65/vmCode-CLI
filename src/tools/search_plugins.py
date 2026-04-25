"""search_plugins core tool for on-demand plugin discovery.

This tool lets the LLM agent search for available plugin tools and
saved skills. Matching plugins are activated automatically, while skills
must be loaded explicitly. Plugin schemas are not sent by default to
avoid context bloat — they are only included after activation.
"""

from typing import List, Optional
from pathlib import Path

from tools.helpers.base import tool, ToolRegistry, TERMINAL_NONE


@tool(
    name="search_plugins",
    description=(
        "Search for available plugin tools and saved skills that can help "
        "with your task. Plugins are NOT in your available tools by default "
        "— use this to discover and activate them. Matching skills are "
        "returned for explicit loading with load_skill. Once a plugin is "
        "activated, its full schema will be available in your next response."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing what you need (e.g., 'send email', 'query database', 'http request')"
            },
            "category": {
                "type": "string",
                "description": "Optional category filter (e.g., 'email', 'database', 'analysis')"
            }
        },
        "required": ["query"]
    },
    requires_approval=False,
    terminal_policy=TERMINAL_NONE,
    tier="core",
    tags=["plugin", "discovery", "meta"],
    category="core"
)
def search_plugins(
    query: str,
    category: str = None,
) -> str:
    """Search discoverable capabilities and activate matched plugins only."""
    from tools.helpers.plugin_manifest import plugin_manifest

    core_tools = ToolRegistry.get_all(include_plugins=False)
    query_lower = query.lower()
    core_tool_note = None
    for ct in core_tools:
        if query_lower == ct.name.lower():
            core_tool_note = (
                f"'{query}' matches a core tool that is already available: **{ct.name}**.\n"
                f"Description: {ct.description}"
            )
            break

    matches = plugin_manifest.search_capabilities(query, category=category, max_results=5)

    if not matches:
        lines = ["exit_code=0"]
        if core_tool_note:
            lines.extend([core_tool_note, ""])

        categories = plugin_manifest.get_categories()
        if categories:
            cat_list = ", ".join(f"'{c}'" for c in categories)
            lines.extend([
                f"No plugins or skills found matching '{query}'.",
                f"Available plugin categories: {cat_list}",
                f"Total plugins in manifest: {plugin_manifest.plugin_count()}",
            ])
            return "\n".join(lines)

        lines.append(
            f"No plugins or skills found matching '{query}'. "
            f"No plugins are currently registered in the manifest."
        )
        return "\n".join(lines)

    plugin_count = 0
    skill_count = 0
    for match in matches:
        if match.kind != "plugin" or not match.tool_def:
            skill_count += 1
            continue
        plugin_count += 1
        if ToolRegistry.is_plugin_active(match.tool_def.name):
            match.already_active = True
        else:
            ToolRegistry.activate_plugin(match.tool_def)
            match.activated = True

    lines = ["exit_code=0"]
    if core_tool_note:
        lines.extend([core_tool_note, ""])

    lines.append(
        f"Found {len(matches)} capability match(es) for '{query}' "
        f"({plugin_count} plugin(s), {skill_count} skill(s)):\n"
    )

    for match in matches:
        cat_part = f" [{match.category}]" if match.category else ""
        if match.kind == "plugin":
            status = "activated" if match.activated else "already active"
            lines.append(f"- **{match.name}**{cat_part} (plugin, {status}): {match.description}")
            if match.tags:
                lines.append(f"  Tags: {', '.join(match.tags)}")
            continue
        lines.append(f"- **{match.name}**{cat_part} (skill): {match.description}")
        lines.append("  Load with: load_skill")

    return "\n".join(lines)
