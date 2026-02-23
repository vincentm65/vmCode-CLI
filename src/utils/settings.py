"""Centralized configuration for vmCode."""
from dataclasses import dataclass, field
from typing import Set

# Load config from llm.config
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.config import _CONFIG

# Styles and themes
from pygments.styles.monokai import MonokaiStyle


class MonokaiDarkBGStyle(MonokaiStyle):
    """Monokai style with dark background for code highlighting."""
    background_color = "#141414"


@dataclass
class ServerSettings:
    """Local llama-server configuration."""
    ngl_layers: int = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("ngl_layers", 30))
    ctx_size: int = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("ctx_size", 8192))
    n_predict: int = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("n_predict", 8192))
    rope_scale: float = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("rope_scale", 1.0))
    health_check_timeout_sec: int = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("health_check_timeout_sec", 120))
    health_check_interval_sec: float = field(default_factory=lambda: _CONFIG.get("SERVER_SETTINGS", {}).get("health_check_interval_sec", 1.0))


@dataclass
class ToolSettings:
    """Tool execution limits and defaults."""
    max_tool_calls: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("max_tool_calls", 100))
    max_output_chars: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("max_output_chars", 8000))
    command_timeout_sec: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("command_timeout_sec", 30))
    preview_lines: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("preview_lines", 50))
    max_recent_reads: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("max_recent_reads", 20))
    enable_parallel_execution: bool = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("enable_parallel_execution", True))
    max_parallel_workers: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("max_parallel_workers", 10))
    max_command_output_lines: int = field(default_factory=lambda: _CONFIG.get("TOOL_SETTINGS", {}).get("max_command_output_lines", 100))


@dataclass
class FileSettings:
    """File scanning and reading limits."""
    max_file_bytes: int = field(default_factory=lambda: _CONFIG.get("FILE_SETTINGS", {}).get("max_file_bytes", 200_000))
    max_total_bytes: int = field(default_factory=lambda: _CONFIG.get("FILE_SETTINGS", {}).get("max_total_bytes", 1_500_000))
    exclude_dirs: Set[str] = None

    def __post_init__(self):
        if self.exclude_dirs is None:
            config_exclude = _CONFIG.get("FILE_SETTINGS", {}).get("exclude_dirs")
            if config_exclude:
                self.exclude_dirs = set(config_exclude)
            else:
                self.exclude_dirs = {".git", ".venv", "llama.cpp", "bin", "__pycache__"}


@dataclass
class ToolCompactionSettings:
    """Per-message tool result compaction settings."""
    enable_per_message_compaction: bool = field(default_factory=lambda: _CONFIG.get("TOOL_COMPACTION_SETTINGS", {}).get("enable_per_message_compaction", True))
    keep_recent_tool_blocks: int = field(default_factory=lambda: _CONFIG.get("TOOL_COMPACTION_SETTINGS", {}).get("keep_recent_tool_blocks", 3))
    compact_failed_tools: bool = field(default_factory=lambda: _CONFIG.get("TOOL_COMPACTION_SETTINGS", {}).get("compact_failed_tools", True))


# Context compaction settings
@dataclass
class ContextSettings:
    """Context compaction thresholds and defaults."""
    compact_trigger_tokens: int = field(default_factory=lambda: _CONFIG.get("CONTEXT_SETTINGS", {}).get("compact_trigger_tokens", 100_000))
    log_conversations: bool = field(default_factory=lambda: _CONFIG.get("CONTEXT_SETTINGS", {}).get("log_conversations", False))
    conversations_dir: str = field(default_factory=lambda: _CONFIG.get("CONTEXT_SETTINGS", {}).get("conversations_dir", "conversations"))
    tool_compaction: ToolCompactionSettings = field(default_factory=ToolCompactionSettings)

    def get_compact_trigger_for_provider(self, provider: str) -> int:
        """Get provider-specific compaction threshold.

        Args:
            provider: Provider name (unused - same threshold for all)

        Returns:
            int: Token threshold for auto-compaction (100k for all providers)
        """
        return self.compact_trigger_tokens  # Universal threshold for all providers


# Global instances
server_settings = ServerSettings()
tool_settings = ToolSettings()
file_settings = FileSettings()
context_settings = ContextSettings()

# Tool execution constants
MAX_TOOL_OUTPUT_CHARS = tool_settings.max_output_chars
MAX_TOOL_CALLS = tool_settings.max_tool_calls
MAX_COMMAND_OUTPUT_LINES = tool_settings.max_command_output_lines
