"""Structured command safety system for auto-approval.

Replaces the flat ALLOWED_COMMANDS whitelist with a command+subcommand
granularity system that distinguishes read-only operations from mutations.

Design principles:
- No args = not safe (for commands with subcommand variants)
- Gate anything that has potential to be unsafe
- Deny-by-default: commands not in the dict require approval
- Compound flags use longest-prefix matching
"""

import os
import shlex
from utils.validation import CHAINING_OPERATORS


# ---------------------------------------------------------------------------
# SAFE_COMMAND_RULES
# ---------------------------------------------------------------------------
# Maps command names to their safety profile:
#   None  → always safe (inherently read-only, e.g., ps, pwd)
#   set() → only safe for listed subcommands/flags
#
# Platform normalization strips .exe suffix and lowercases before lookup.

SAFE_COMMAND_RULES: dict[str, frozenset | None] = {
    # --- Always safe (truly read-only, no mutating subcommands) ---
    "pwd": None,
    "which": None,
    "whereis": None,
    "uname": None,
    "hostname": None,
    "uptime": None,
    "date": None,
    "cal": None,
    "whoami": None,
    "id": None,
    "env": frozenset({"--version", "--help"}),
    "printenv": frozenset({"--version", "--help"}),
    "lscpu": None,
    "lsblk": None,
    "file": None,
    "stat": None,
    "md5sum": None,
    "sha256sum": None,
    "free": None,
    "df": None,
    "du": None,
    "dmesg": None,
    "ltrace": None,
    "ps": None,
    "pgrep": None,
    "pidof": None,
    "lsof": None,
    "ping": None,
    "nslookup": None,
    "dig": None,
    "ss": None,
    "ifconfig": None,
    "netstat": None,
    "journalctl": None,
    "apt-cache": None,
    "apt-show": None,
    "dpkg-query": None,

    # --- Subcommand-gated (safe only for specific read-only operations) ---
    "git": frozenset({
        "status", "log", "diff", "show", "branch",
        "remote", "tag",
        "rev-parse", "shortlog", "describe", "symbolic-ref",
        "reflog", "name-rev", "blame", "annotate",
        "for-each-ref", "ls-files", "ls-tree", "ls-remote",
    }),
    "pip": frozenset({"show", "list", "--version", "check", "debug", "index", "inspect"}),
    "pip3": frozenset({"show", "list", "--version", "check", "debug", "index", "inspect"}),
    "npm": frozenset({"list", "ls", "view", "version", "outdated", "pack", "info", "doctor", "audit"}),
    "node": frozenset({"--version"}),
    "python": frozenset({"--version"}),
    "python3": frozenset({"--version"}),
    "pacman": frozenset({
        "-Q", "-Qi", "-Ql", "-Qo", "-Qs", "-Qt",
        "-F", "-Si", "-Ss", "-Fl", "-G",
    }),
    "dpkg": frozenset({"-l", "-s", "-S", "-L", "-p", "--verify", "--audit"}),
    "rpm": frozenset({"-q", "-qa", "-qi", "-ql", "-qf", "--queryformat"}),
    "dnf": frozenset({"list", "info", "search", "check-update", "repoquery"}),
    "yum": frozenset({"list", "info", "search", "check-update"}),
    "systemctl": frozenset({
        "status", "list-units", "list-unit-files", "show",
        "is-active", "is-enabled", "cat", "list-timers",
        "list-sockets", "list-jobs",
    }),
    "service": frozenset({"--status-all"}),  # "service <name> status" handled by _is_safe_service_command
    "ip": frozenset({"addr", "address", "link", "route", "neigh", "maddr", "rule", "netns"}),

    # --- Windows equivalents ---
    "where": None,
    "systeminfo": None,
    "Get-Process": None,
    "Get-Service": None,
    "Get-ChildItem": None,
    "Get-Content": None,
    "Get-Location": None,
    "Test-Connection": None,
    "Get-NetIPAddress": None,
}


# Sub-subcommand deny lists for commands where the first arg passes safety
# but later args can be mutating. Checked AFTER first-arg matching.
# If any token appears in the deny list, the command is rejected.
_IP_MUTATING_VERBS = frozenset({
    "set", "add", "delete", "replace", "flush", "change",
})

# Commands that need deep token scanning mapped to their deny sets.
_DEEP_SCAN_RULES: dict[str, frozenset] = {
    "ip": _IP_MUTATING_VERBS,
}


def _tokenize(command: str) -> list[str]:
    """Tokenize a command string using platform-appropriate splitting."""
    use_posix = os.name != "nt"
    try:
        return shlex.split(command, posix=use_posix)
    except ValueError:
        return command.split()


def _normalize_command_name(name: str) -> str:
    """Normalize a command name for lookup.

    Strips .exe suffix and lowercases. Does NOT normalize PowerShell
    cmdlet casing (case-insensitive lookup handles that).
    """
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name.lower()


def _matches_safe_subcommand(arg: str, safe_set: frozenset) -> bool:
    """Check if an argument matches any entry in the safe subcommand set.

    Uses longest-prefix matching for flag-style arguments:
    e.g., if '-Qi' is safe, then '-Qil' also matches.
    For word-style subcommands (e.g., git 'status'), exact match only.

    Comparison is case-insensitive.
    """
    arg_lower = arg.lower()

    # Build lowercase version of safe_set for case-insensitive comparison
    safe_lower = {s.lower() for s in safe_set}

    # Exact match
    if arg_lower in safe_lower:
        return True

    # Longest-prefix match for flags (arguments starting with -)
    if arg_lower.startswith("-"):
        # Try progressively shorter prefixes
        for length in range(len(arg_lower) - 1, 1, -1):
            prefix = arg_lower[:length]
            if prefix in safe_lower:
                return True

    return False


def is_git_command(command: str) -> bool:
    """Check if a command is a git invocation.

    Returns True for 'git', 'git.exe', and any command starting with 'git '.
    This is used to gate git operations separately in danger mode.

    Args:
        command: Command string to check

    Returns:
        bool: True if the command is a git invocation
    """
    command = command.strip()
    if not command:
        return False
    tokens = _tokenize(command)
    if not tokens:
        return False
    return _normalize_command_name(tokens[0]) == "git"


def is_safe_command(command: str) -> bool:
    """Check if a command should be auto-approved (safe, read-only).

    A command is auto-approved when:
    1. It contains no chaining/redirection operators
    2. The command name is in SAFE_COMMAND_RULES
    3. If gated (has a set of safe subcommands), the first argument
       matches an entry in the set
    4. If always-safe (None), it's approved with or without args

    Args:
        command: Command string to validate

    Returns:
        bool: True if the command is safe to auto-approve
    """
    command = command.strip()
    if not command:
        return False

    # Strip "powershell " prefix if present (legacy support for Windows users)
    if command.lower().startswith("powershell "):
        command = command[len("powershell "):].strip()

    # Reject any command containing chaining/redirection operators
    if CHAINING_OPERATORS.search(command):
        return False

    # Tokenize and get command name
    tokens = _tokenize(command)
    if not tokens:
        return False

    cmd_name = _normalize_command_name(tokens[0])

    # Look up in rules (deny-by-default)
    if cmd_name not in SAFE_COMMAND_RULES:
        # Unknown command — require approval
        return False

    rule = SAFE_COMMAND_RULES[cmd_name]
    if rule is None:
        # Always-safe command (e.g., ps, pwd)
        return True

    if not rule:
        # Empty frozenset — no safe subcommands defined, deny
        return False

    # Gated command — need at least one subcommand arg
    if len(tokens) < 2:
        return False

    # Check first argument against safe subcommand set
    first_arg = tokens[1]

    # Special case: "service <name> status" — the safe subcommand is the LAST arg
    if cmd_name == "service" and len(tokens) >= 3 and tokens[-1].lower() == "status":
        return True

    if not _matches_safe_subcommand(first_arg, rule):
        return False

    # Deep scan: for commands with known mutating sub-subcommands,
    # reject if any remaining token matches the deny list.
    deny_set = _DEEP_SCAN_RULES.get(cmd_name)
    if deny_set and len(tokens) > 2:
        for tok in tokens[2:]:
            if tok.lower() in deny_set:
                return False

    return True
