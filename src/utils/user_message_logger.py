"""Lightweight user-message logger for the dream memory system.

Appends one JSONL line per user message, one file per day.
Always on by default — no toggle needed.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory for daily message logs
CONVERSATIONS_DIR = Path.home() / ".bone" / "conversations"
RETENTION_DAYS = 7


class UserMessageLogger:
    """Logs user messages to daily JSONL files for later dream processing."""

    def __init__(self, conversations_dir: Path | None = None):
        self._dir = conversations_dir or CONVERSATIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def log_user_message(self, content: str) -> None:
        """Append a single user message to today's JSONL file.

        Opens in append mode and flushes immediately for crash safety.
        Each message is one self-contained JSON line.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = self._dir / f"{today}.jsonl"
        entry = {"ts": datetime.now().isoformat(), "msg": content}
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def cleanup_old_files(directory: Path | None = None, retention_days: int = RETENTION_DAYS) -> int:
        """Delete JSONL files older than retention_days. Returns count of files removed."""
        target_dir = directory or CONVERSATIONS_DIR
        if not target_dir.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=retention_days)
        removed = 0
        for f in target_dir.glob("*.jsonl"):
            if f.stat().st_mtime < cutoff.timestamp():
                f.unlink()
                removed += 1
                logger.debug("Removed old conversation log: %s", f.name)
        return removed
