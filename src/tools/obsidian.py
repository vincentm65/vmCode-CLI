"""Obsidian vault integration tools.

Provides wiki-link resolution, backlink discovery, and frontmatter parsing.
Uses register() pattern — tools only register when called explicitly,
NOT on import. This ensures zero cost when no vault is configured.

Usage (from __init__.py):
    from tools import obsidian
    if obsidian_settings.is_active():
        obsidian.register()
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from .helpers.base import ToolDefinition, ToolRegistry

logger = logging.getLogger(__name__)


class _VaultIndex:
    """Lazy-built cache of vault note stems to paths.

    Built once on first access, invalidated on register/unregister.
    Eliminates full rglob("*.md") scan on every wiki-link resolution.
    """
    def __init__(self):
        self._stem_map: Dict[str, List[Tuple[Path, str]]] = {}
        self._vault_root: Optional[Path] = None

    def get(self, vault_root: Path) -> Dict[str, List[Tuple[Path, str]]]:
        """Return the stem→paths map, building it if stale."""
        if vault_root != self._vault_root:
            self._build(vault_root)
        return self._stem_map

    def _build(self, vault_root: Path):
        """Scan vault and build stem→[(path, stem)] index."""
        self._stem_map.clear()
        self._vault_root = vault_root
        for md_file in vault_root.rglob("*.md"):
            if ".obsidian" in md_file.parts:
                continue
            stem = md_file.stem
            key = stem.lower()
            self._stem_map.setdefault(key, []).append((md_file, stem))

    def invalidate(self):
        """Force rebuild on next access."""
        self._vault_root = None


_vault_index = _VaultIndex()


# =============================================================================
# Internal utilities (not exposed as tools)
# =============================================================================

# Cached vault root — invalidated on register/unregister
_cached_vault_root: Optional[Path] = None


def _get_vault_root() -> Optional[Path]:
    """Resolve vault root from settings, validate .obsidian/ exists.

    Result is cached after first successful resolution. Call invalidate_vault_cache()
    when vault settings change.

    Returns:
        Path to vault root, or None if not configured/invalid
    """
    global _cached_vault_root

    if _cached_vault_root is not None:
        return _cached_vault_root

    from utils.settings import obsidian_settings

    vault_path = obsidian_settings.vault_path
    if not vault_path:
        return None

    root = Path(vault_path).resolve()
    if not root.is_dir():
        logger.warning(f"Obsidian vault path is not a directory: {root}")
        return None

    obsidian_dir = root / ".obsidian"
    if not obsidian_dir.is_dir():
        logger.warning(f"No .obsidian/ directory found in: {root}")
        return None

    _cached_vault_root = root
    return root


def invalidate_vault_cache():
    """Invalidate cached vault root and index. Call when vault settings change."""
    global _cached_vault_root
    _cached_vault_root = None
    _vault_index.invalidate()


def _resolve_path(relative_path: str, vault_root: Path) -> Optional[Path]:
    """Safely resolve a relative path within the vault.

    Prevents path traversal attacks.

    Args:
        relative_path: Path relative to vault root
        vault_root: Vault root directory

    Returns:
        Resolved absolute path, or None if it escapes the vault
    """
    try:
        resolved = (vault_root / relative_path).resolve()
        # Ensure the resolved path is within the vault
        if not str(resolved).startswith(str(vault_root)):
            logger.warning(f"Path traversal attempt: {relative_path}")
            return None
        return resolved
    except (ValueError, OSError) as e:
        logger.warning(f"Invalid path '{relative_path}': {e}")
        return None


def resolve_wiki_link(name: str, vault_root: Path) -> List[Tuple[Path, str]]:
    """Resolve a wiki-link name to filesystem path(s).

    Handles:
    - Raw names: "Auth System"
    - Wiki-link syntax: "[[Auth System]]" or "[[Auth System|Auth]]"
    - Case-insensitive matching
    - Partial matching (prefix)

    Returns:
        List of (path, display_name) tuples. Empty if no match.
        Multiple results indicate ambiguity.
    """
    # Strip wiki-link syntax and extract display name
    clean = name.strip()
    display_name = clean

    # Remove [[ ]] wrapper
    if clean.startswith("[[") and clean.endswith("]]"):
        clean = clean[2:-2].strip()

    # Extract alias: [[Target|Display]] -> Target
    if "|" in clean:
        parts = clean.split("|", 1)
        clean = parts[0].strip()
        display_name = parts[1].strip()

    # Strip .md extension if present
    clean_stem = clean.removesuffix(".md").strip()

    if not clean_stem:
        return []

    # Use cached vault index for O(1) lookup
    stem_map = _vault_index.get(vault_root)
    key = clean_stem.lower()

    # Exact case-insensitive match
    if key in stem_map:
        return stem_map[key]

    # Prefix match — scan keys for matching stems
    matches = []
    for other_key, entries in stem_map.items():
        if other_key.startswith(key):
            matches.extend(entries)

    return matches


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown content.

    Args:
        content: Raw markdown content

    Returns:
        (metadata_dict, body_text) tuple.
        metadata_dict is empty {} if no frontmatter found.
        body_text is everything after the closing ---.
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = re.search(r"^---\s*$", content[3:], re.MULTILINE)
    if not end_match:
        return {}, content

    yaml_block = content[3:end_match.start() + 3]
    body = content[end_match.start() + 3:].strip()

    # Parse simple YAML (key: value pairs, lists, and multi-line strings)
    metadata = _parse_simple_yaml(yaml_block)

    return metadata, body


def _parse_simple_yaml(yaml_text: str) -> Dict:
    """Parse YAML frontmatter into a dict.

    Uses yaml.safe_load when available, with a minimal inline fallback.
    """
    try:
        import yaml
        result = yaml.safe_load(yaml_text)
        return result if isinstance(result, dict) else {}
    except Exception:
        pass

    # Minimal fallback for environments without PyYAML
    result = {}
    for line in yaml_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_ -]*?)\s*:\s*(.*)", stripped)
        if key_match:
            key = key_match.group(1).strip()
            value = key_match.group(2).strip()
            if value:
                result[key] = value
    return result


def parse_wiki_links(content: str) -> List[str]:
    """Extract all wiki-link names from content.

    Handles [[Link]], [[Link|Alias]], and [[Link#Heading]].

    Args:
        content: Markdown content

    Returns:
        List of link names (without [[ ]] or aliases)
    """
    pattern = r"\[\[([^\]|#]+)"
    return re.findall(pattern, content)


def _find_backlinks(note_path: Path, vault_root: Path, rg_exe_path: str = None) -> List[str]:
    """Find notes in the vault that link to the given note.

    Uses rg to scan for wiki-link references.

    Args:
        note_path: Path to the target note
        vault_root: Vault root directory
        rg_exe_path: Path to rg executable (defaults to 'rg' on PATH)

    Returns:
        List of relative paths (from vault root) of notes linking to this note
    """
    note_name = note_path.stem
    if not note_name:
        return []

    rg_bin = rg_exe_path or "rg"

    try:
        import subprocess

        # Search for [[NoteName]] pattern across .md files, excluding .obsidian/
        result = subprocess.run(
            [
                rg_bin,
                "--files-with-matches",
                "--glob=*.md",
                "--glob=!.obsidian",
                f"[[{re.escape(note_name)}]]",
                str(vault_root),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            backlinks = []
            for line in result.stdout.strip().split("\n"):
                bl_path = Path(line)
                # Skip the note itself
                if bl_path != note_path:
                    try:
                        backlinks.append(str(bl_path.relative_to(vault_root)))
                    except ValueError:
                        pass
            return backlinks

        return []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning(f"Backlink search failed: {e}")
        return []


# =============================================================================
# Tool handlers
# =============================================================================

def _handle_obsidian_resolve(
    name: str,
    get_backlinks: bool = False,
    repo_root: Path = None,
    rg_exe_path: str = None,
    console=None,
    **kwargs,
) -> str:
    """Resolve a wiki-link or note name to filesystem path(s)."""
    vault_root = _get_vault_root()
    if not vault_root:
        return "exit_code=1\nObsidian vault is not configured or invalid. Use /obsidian set <path> to configure."

    if not name or not name.strip():
        return "exit_code=1\n'name' parameter is required."

    matches = resolve_wiki_link(name, vault_root)

    if not matches:
        return f"exit_code=0\nNo notes found matching '{name}' in vault."

    lines = []

    if len(matches) == 1:
        path, stem = matches[0]
        rel_path = str(path.relative_to(vault_root))
        lines.append(f"Resolved: {stem}")
        lines.append(f"Vault root: {vault_root}")
        lines.append(f"Relative path: {rel_path}")
        lines.append(f"Absolute path: {path}")
    else:
        lines.append(f"Ambiguous match for '{name}' — {len(matches)} candidates:")
        for path, stem in matches:
            rel_path = str(path.relative_to(vault_root))
            lines.append(f"  - {stem} -> {rel_path}")

    if get_backlinks and matches:
        # Use first match for backlinks
        target_path = matches[0][0]
        backlinks = _find_backlinks(target_path, vault_root, rg_exe_path=rg_exe_path)
        if backlinks:
            lines.append(f"\nBacklinks ({len(backlinks)}):")
            for bl in backlinks:
                lines.append(f"  <- {bl}")
        else:
            lines.append("\nNo backlinks found.")

    return "exit_code=0\n" + "\n".join(lines)


def _handle_obsidian_frontmatter(
    path_str: str,
    repo_root: Path = None,
    console=None,
    **kwargs,
) -> str:
    """Parse frontmatter from an Obsidian note."""
    vault_root = _get_vault_root()
    if not vault_root:
        return "exit_code=1\nObsidian vault is not configured or invalid. Use /obsidian set <path> to configure."

    if not path_str or not path_str.strip():
        return "exit_code=1\n'path_str' parameter is required."

    # Resolve path relative to vault root
    resolved = _resolve_path(path_str, vault_root)
    if not resolved:
        return "exit_code=1\nInvalid path or path traversal detected."

    if not resolved.exists():
        return f"exit_code=1\nNote not found: {path_str}"

    if not resolved.is_file():
        return f"exit_code=1\nNot a file: {path_str}"

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as e:
        return f"exit_code=1\nFailed to read file: {e}"

    metadata, body = parse_frontmatter(content)

    if not metadata:
        return f"exit_code=0\nNo frontmatter found in: {path_str}"

    lines = [f"Frontmatter for: {path_str}"]
    lines.append("")

    # Format metadata as YAML-like output
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            lines.append(f"{key}: {value}")

    # Body stats
    body_lines = body.count("\n") + 1 if body else 0
    lines.append("")
    lines.append(f"Body lines: {body_lines}")

    return "exit_code=0\n" + "\n".join(lines)


# =============================================================================
# Tool definitions (not registered until register() is called)
# =============================================================================

OBSIDIAN_RESOLVE_TOOL = ToolDefinition(
    name="obsidian_resolve",
    description=(
        "Resolve an Obsidian wiki-link or note name to a filesystem path. "
        "Optionally find backlinks (notes that link TO this note). "
        "Use before read_file to turn note names into file paths. "
        "When auto_resolve_links is enabled, resolve [[links]] automatically."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Note name or wiki-link (e.g. 'Auth System', '[[Auth System|Auth]]')"
            },
            "get_backlinks": {
                "type": "boolean",
                "description": "If true, find notes linking TO this note (vault-wide scan)",
                "default": False
            }
        },
        "required": ["name"]
    },
    allowed_modes=["edit", "plan"],
    requires_approval=False,
    handler=_handle_obsidian_resolve,
)

OBSIDIAN_FRONTMATTER_TOOL = ToolDefinition(
    name="obsidian_frontmatter",
    description=(
        "Parse YAML frontmatter from an Obsidian note. "
        "Returns structured metadata (tags, status, dates, etc.) and body line count. "
        "Use instead of read_file when you only need metadata."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path_str": {
                "type": "string",
                "description": "Path to the note, relative to vault root (e.g. 'Projects/Auth System.md')"
            }
        },
        "required": ["path_str"]
    },
    allowed_modes=["edit", "plan"],
    requires_approval=False,
    handler=_handle_obsidian_frontmatter,
)


# =============================================================================
# Registration function
# =============================================================================

def register() -> bool:
    """Register Obsidian tools with the global tool registry.

    Should only be called when obsidian_settings.is_active() is True.
    Safe to call multiple times — tools are only registered once.

    Returns:
        True if tools were registered, False if already registered
    """
    # Use ToolRegistry as source of truth (no separate _registered flag)
    if ToolRegistry.get("obsidian_resolve"):
        logger.debug("Obsidian tools already registered, skipping.")
        return False

    # Validate vault before registering
    vault_root = _get_vault_root()
    if not vault_root:
        logger.warning("Cannot register Obsidian tools: vault is not configured or invalid.")
        return False

    ToolRegistry.register(OBSIDIAN_RESOLVE_TOOL)
    ToolRegistry.register(OBSIDIAN_FRONTMATTER_TOOL)
    invalidate_vault_cache()

    logger.info(f"Obsidian tools registered. Vault: {vault_root}")
    return True


def unregister() -> bool:
    """Remove Obsidian tools from the global tool registry.

    Returns:
        True if tools were unregistered, False if not registered
    """
    if not ToolRegistry.get("obsidian_resolve"):
        return False

    for name in ("obsidian_resolve", "obsidian_frontmatter"):
        ToolRegistry.unregister(name)

    invalidate_vault_cache()
    logger.info("Obsidian tools unregistered.")
    return True
