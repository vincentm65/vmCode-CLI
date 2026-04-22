"""Multi-layer memory system for the agent.

Two-layer persistent memory:
- User memory (global): ~/.bone/user_memory.md
- Project memory (per-repo): {repo_root}/.bone/agents.md

Memory files are read-only during conversations — loaded into the system prompt
for context but never written inline. All writes happen through the dream cron job,
which consolidates user messages into focused memories nightly.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Capacity constants (prompt-enforced, no code enforcement)
CHAR_LIMIT = 1500  # suggested chars per layer (~500 tokens)


class MemoryManager:
    """Manages two-layer memory: user-level (global) and project-level (per-repo).

    Uses a lazy singleton pattern — first call with repo_root bootstraps the
    instance, subsequent calls reuse it. Call reset() when switching repos.
    """

    _instance: Optional["MemoryManager"] = None

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.user_memory_path = Path.home() / ".bone" / "user_memory.md"
        self.project_memory_path = repo_root / ".bone" / "agents.md"

    @classmethod
    def get_instance(cls, repo_root: Path = None) -> Optional["MemoryManager"]:
        """Lazy singleton. First call sets repo_root, subsequent calls reuse instance.

        Args:
            repo_root: Path to repository root. Required on first call,
                       ignored on subsequent calls (until reset()).

        Returns:
            MemoryManager instance, or None if no repo_root provided and
            no instance has been initialized yet.
        """
        if cls._instance is not None:
            return cls._instance
        if repo_root is None:
            return None
        cls._instance = cls(repo_root)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear singleton. Called when switching repos via /cd."""
        cls._instance = None

    def ensure_exists(self) -> None:
        """Create user-level directory and memory file only.

        Project-level .bone/agents.md is created lazily on first write,
        not at startup. This prevents creating .bone/ directories in
        non-project locations (e.g. when running from ~/.bone/ itself).
        """
        self._ensure_dir_and_file(
            self.user_memory_path,
            "# User Memory\n\n",
        )
        # Add .bone/ to .gitignore if repo_root has a git repo
        self._ensure_gitignore()

    def load_user_memory(self) -> str:
        """Read and return user memory file content. Returns empty string if missing."""
        return self._read_file(self.user_memory_path)

    def load_project_memory(self) -> str:
        """Read and return project memory file content. Returns empty string if missing."""
        return self._read_file(self.project_memory_path)

    def get_user_usage(self) -> dict:
        """Return {chars_used, chars_limit} for user memory."""
        content = self.load_user_memory()
        return {"chars_used": len(content), "chars_limit": CHAR_LIMIT}

    def get_project_usage(self) -> dict:
        """Return {chars_used, chars_limit} for project memory."""
        content = self.load_project_memory()
        return {"chars_used": len(content), "chars_limit": CHAR_LIMIT}

    # ---- Private helpers ----

    @staticmethod
    def _has_entries(content: str) -> bool:
        """Check if memory file has entries beyond just the header.

        A file with only "# User Memory\\n\\n" is considered empty.
        """
        stripped = content.strip()
        # Remove the H1 header line and blank lines
        for line in stripped.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Found a non-header, non-blank line — has entries
            return True
        return False

    @staticmethod
    def _ensure_dir_and_file(path: Path, default_content: str) -> None:
        """Create parent directory and file with default content if missing."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(default_content, encoding="utf-8")
                logger.debug("Created memory file: %s", path)
        except Exception as e:
            logger.warning("Failed to create memory file %s: %s", path, e)

    @staticmethod
    def _read_file(path: Path) -> str:
        """Read file content, return empty string on any error."""
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read memory file %s: %s", path, e)
        return ""

    def _ensure_gitignore(self) -> None:
        """Add .bone/ to .gitignore if not already present."""
        gitignore = self.repo_root / ".gitignore"
        if not self.repo_root.is_dir() or not (self.repo_root / ".git").is_dir():
            return  # Not a git repo
        try:
            if not gitignore.exists():
                gitignore.write_text(".bone/\n", encoding="utf-8")
                return
            content = gitignore.read_text(encoding="utf-8")
            if ".bone" not in content:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n.bone/\n")
        except Exception as e:
            logger.warning("Failed to update .gitignore: %s", e)
