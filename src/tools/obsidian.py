"""Obsidian vault integration utilities.

Provides wiki-link resolution, backlink discovery, frontmatter parsing,
and vault session management for project note routing.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from .helpers.base import ToolDefinition, ToolRegistry
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VaultSession:
    """Immutable snapshot of vault pairing state.

    Built once when the vault is activated (register()) and shared everywhere.
    Eliminates scattered derivation of vault_root, project_folder, and path prefixes.

    Attributes:
        vault_root: Absolute validated vault root Path.
        project_folder: Absolute project folder (vault_root / project_base / repo_name).
        project_folder_relative: Vault-relative project folder string (e.g. "Dev/myrepo").
    """
    vault_root: Path
    project_folder: Path
    project_folder_relative: str


# Module-level session — set by register(), cleared by unregister()
_session: Optional[VaultSession] = None


def get_vault_session() -> Optional[VaultSession]:
    """Return the active VaultSession, or None if vault is not paired."""
    return _session


def build_vault_session(repo_root: Path = None) -> Optional[VaultSession]:
    """Build a VaultSession from current settings.

    Args:
        repo_root: Repository root used to derive project folder name.
                   Falls back to os.getcwd() if not provided.

    Returns:
        VaultSession if vault is configured and valid, None otherwise.
    """
    from utils.settings import obsidian_settings

    if not obsidian_settings.is_active():
        return None

    root = obsidian_settings.vault_path  # Already validated by is_active()
    # Re-resolve to absolute (is_active checks existence but returns raw string)
    root = Path(root).resolve()

    project_base = obsidian_settings.project_base or "Dev"
    repo_name = repo_root.name if repo_root else os.path.basename(os.getcwd())
    if not repo_name:
        return None

    project_folder = root / project_base / repo_name
    pf_relative = str(project_base) + "/" + repo_name

    return VaultSession(
        vault_root=root,
        project_folder=project_folder,
        project_folder_relative=pf_relative,
    )


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
        from utils.settings import obsidian_settings

        self._stem_map.clear()
        self._vault_root = vault_root
        exclude = obsidian_settings.exclude_folders_list
        for md_file in vault_root.rglob("*.md"):
            if any(excl == part for part in md_file.parts for excl in exclude):
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

def invalidate_vault_cache():
    """Invalidate vault index cache. Call when vault settings change."""
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
        # Ensure the resolved path is within the vault (exact boundary check)
        resolved.relative_to(vault_root)
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
        from utils.settings import obsidian_settings

        # Build glob exclusions from settings
        exclude = obsidian_settings.exclude_folders_list
        rg_args = [
            rg_bin,
            "--files-with-matches",
            "--glob=*.md",
        ]
        for excl in exclude:
            rg_args.append(f"--glob=!{excl}")

        # Search for [[NoteName]] pattern across .md files
        result = subprocess.run(
            rg_args + [
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


def init_session(repo_root: Path = None) -> Optional[VaultSession]:
    """Build and cache the VaultSession.

    Should be called once with the actual repo_root when available.
    Falls back to os.getcwd() if repo_root is None (acceptable for prompt
    building before the orchestrator starts).

    Returns:
        The active VaultSession, or None if vault is not configured.
    """
    global _session
    session = build_vault_session(repo_root=repo_root)
    if session:
        # Only cache if we have a real repo_root — otherwise the orchestrator
        # will call us again with the correct path and that should win.
        if repo_root is not None or _session is None:
            _session = session
            logger.info(f"Vault session initialized: {session.project_folder_relative}")
    return _session



