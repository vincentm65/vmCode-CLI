"""Obsidian vault integration utilities.

Provides vault session management for project note routing.
"""

import logging
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

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



