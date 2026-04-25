"""Plugin manifest for on-demand tool discovery.

Plugin-tier tools are registered here instead of ToolRegistry at import time.
This keeps plugin schemas out of the LLM context window until explicitly
activated via the search_plugins core tool.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from core.skills import SearchCandidate, SearchMatch, search_candidates, search_skill_matches

from .base import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class CapabilityMatch:
    kind: str
    name: str
    description: str
    category: str | None = None
    tags: list[str] | None = None
    tool_def: ToolDefinition | None = None
    preview: str | None = None
    activated: bool = False
    already_active: bool = False


class PluginManifest:
    """Index of plugin-tier tools available for on-demand activation.

    Tools are registered here when modules with @tool(tier="plugin") are
    imported. The search_plugins core tool queries this index to find and
    activate matching plugins.
    """

    def __init__(self):
        self._plugins: Dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """Register a plugin tool definition.

        Args:
            tool_def: ToolDefinition with tier="plugin"
        """
        if tool_def.name in self._plugins:
            logger.warning(
                f"Plugin '{tool_def.name}' is being overwritten. "
                f"Previous: {self._plugins[tool_def.name].handler}, "
                f"New: {tool_def.handler}"
            )
        self._plugins[tool_def.name] = tool_def
        logger.debug(f"Plugin registered in manifest: {tool_def.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a plugin tool definition by name.

        Args:
            name: Plugin tool name

        Returns:
            ToolDefinition or None if not found
        """
        return self._plugins.get(name)

    def get_all(self) -> List[ToolDefinition]:
        """Get all registered plugin definitions.

        Returns:
            List of all ToolDefinitions in the manifest
        """
        return list(self._plugins.values())

    def search(self, query: str, category: str = None, max_results: int = 5) -> List[ToolDefinition]:
        """Search the manifest for plugins matching a query."""
        return [match.item for match in self.search_plugin_matches(query, category=category, max_results=max_results)]

    def search_plugin_matches(
        self,
        query: str,
        category: str = None,
        max_results: int = 5,
    ) -> List[SearchMatch[ToolDefinition]]:
        """Return scored plugin matches using the shared discovery helper."""
        candidates: list[SearchCandidate[ToolDefinition]] = []

        for tool_def in self._plugins.values():
            if category and tool_def.category != category:
                continue
            text = " ".join(
                part
                for part in [
                    tool_def.name,
                    tool_def.description,
                    tool_def.category or "",
                    " ".join(tool_def.tags or []),
                ]
                if part
            )
            candidates.append(
                SearchCandidate(
                    item=tool_def,
                    text=text,
                    compact_text="",
                    exact_text=tool_def.name,
                )
            )

        return search_candidates(
            query,
            candidates,
            max_results=max_results,
            item_key=lambda tool_def: tool_def.name,
        )

    def search_capabilities(
        self,
        query: str,
        category: str = None,
        max_results: int = 5,
    ) -> List[CapabilityMatch]:
        """Search plugins and skills through one shared discovery path."""
        capabilities: list[CapabilityMatch] = []
        include_plugins = category in (None, "plugin")
        include_skills = category in (None, "skill")

        if include_plugins:
            for tool_def in self._plugins.values():
                if category == "plugin":
                    pass
                elif category and tool_def.category != category:
                    continue
                capabilities.append(
                    CapabilityMatch(
                        kind="plugin",
                        name=tool_def.name,
                        description=tool_def.description,
                        category=tool_def.category,
                        tags=list(tool_def.tags or []),
                        tool_def=tool_def,
                    )
                )

        if include_skills:
            capabilities.extend(
                CapabilityMatch(
                    kind="skill",
                    name=match.item.name,
                    description=match.item.preview,
                    category="skill",
                    tags=["skill"],
                    preview=match.item.preview,
                )
                for match in search_skill_matches(query, max_results=1000)
            )

        combined_candidates = [
            SearchCandidate(
                item=capability,
                text=" ".join(
                    part
                    for part in [
                        capability.name,
                        capability.description,
                        capability.category or "",
                        " ".join(capability.tags or []),
                    ]
                    if part
                ),
                compact_text="",
                exact_text=capability.name,
            )
            for capability in capabilities
        ]
        combined_matches = search_candidates(
            query,
            combined_candidates,
            max_results=max_results,
            item_key=lambda capability: f"{capability.kind}:{capability.name}",
        )
        return [match.item for match in combined_matches]

    def get_categories(self) -> List[str]:
        """Get all unique categories in the manifest.

        Returns:
            Sorted list of category strings
        """
        categories = {td.category for td in self._plugins.values() if td.category}
        return sorted(categories)

    def plugin_count(self) -> int:
        """Get the number of registered plugins.

        Returns:
            Number of plugins in the manifest
        """
        return len(self._plugins)

    def has_plugin(self, name: str) -> bool:
        """Check if a plugin exists in the manifest.

        Args:
            name: Plugin tool name

        Returns:
            True if plugin is in the manifest
        """
        return name in self._plugins


# Singleton instance
plugin_manifest = PluginManifest()
