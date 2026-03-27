# Git Review Agent — Implementation Plan

## Overview

Add a review subagent that analyzes git diffs and provides structured code review feedback. Read-only, bounded input (a diff), fits the existing subagent architecture with minimal changes.

## How It Works

1. User invokes `review_changes` tool (via main agent or direct command)
2. Tool captures diff via `execute_command` (already available to the main agent)
3. Diff is passed as context to the review subagent
4. Review subagent reads changed files for surrounding context
5. Returns structured review with cited file references
6. Existing citation injection provides file content to the main agent

## What Changes

### 1. New file: `src/tools/review_sub_agent.py`

`@tool` registration for `review_changes`:

```python
@tool(
    name="review_changes",
    description="Review current git changes. Run 'git diff' first, then pass the diff to this tool for analysis.",
    parameters={
        "diff_output": "Full git diff output to review",
        "focus": "Optional: 'security', 'logic', 'style', 'all' (default: 'all')"
    }
)
```

The tool function:
- Receives diff as a string parameter (main agent captures it via `execute_command` + `git diff`)
- Validates diff is non-empty
- Checks diff size — if over 50k tokens, truncates with a warning (keep first N files, drop the rest with a summary of what was skipped)
- Calls `run_sub_agent(task_query, sub_agent_type="review", initial_context=diff_output)`
- Returns review result directly (main agent presents it to user)

**Why the main agent captures the diff:** The review tool doesn't need `execute_command`. The main agent already has it and can choose what to diff (`git diff`, `git diff main..HEAD`, `git diff --staged`, etc.). This keeps the review tool's surface area small — it's a pure analysis tool.

### 2. Modified: `src/llm/prompts.py`

Add a review-mode prompt section and parameterize `build_sub_agent_prompt()`:

**New `SUB_AGENT_SECTIONS["review_mode"]`:**

```
# Current Mode: CODE REVIEW

You are a code review agent. Analyze the provided git diff and provide structured feedback.

## Review Checklist
- **Correctness**: Logic bugs, off-by-one errors, null/edge cases
- **Security**: Exposed secrets, unsafe inputs, injection vectors, auth bypasses
- **Error handling**: Missing try/catch, unhandled promise rejections, silent failures
- **Consistency**: Changes that conflict with patterns in related files
- **Completeness**: Partial changes (e.g., new function but no tests, new field but no migration)

## Output Format
1. **Summary** — 1-2 sentence overview of changes
2. **Issues** — numbered list, each with severity (critical/warning/info), file, line range, description
3. **Suggestions** — optional non-blocking improvements
4. **Verdict** — approve / request changes / needs discussion

Read changed files for surrounding context before commenting on them.
Use bracketed citations: [path/to/file] (lines N-M)
```

**Parameterize `build_sub_agent_prompt()`:**

```python
def build_sub_agent_prompt(sub_agent_type: str = "research") -> str:
```

- `"research"` (default) — existing behavior, unchanged
- `"review"` — replaces `SUB_AGENT_SECTIONS["mode"]` with `SUB_AGENT_SECTIONS["review_mode"]`, keeps `response_format` (citations still needed)

### 3. Modified: `src/core/sub_agent.py`

Two small additions to `run_sub_agent()`:

- **`sub_agent_type` parameter** (default `"research"`) — passed through to `build_sub_agent_prompt()`
- **`initial_context` parameter** (optional string) — injected as a user message after agents.md, before the task query

```python
def run_sub_agent(
    task_query: str,
    repo_root: Path,
    rg_exe_path: str,
    console=None,
    panel_updater=None,
    sub_agent_type: str = "research",      # new
    initial_context: str = None,            # new
) -> dict:
```

`_create_chat_manager()` gets an optional `initial_context` parameter that appends a user/assistant pair after the codebase map:

```
[user]: "Review this diff:\n\n{diff}"
[assistant]: "I'll analyze this diff, reading changed files for context as needed."
```

No settings restructuring. The review agent reuses the existing `SubAgentSettings` (allowed_tools, token limits, etc.) as-is.

### 4. No changes to settings

The review agent uses the same read-only tools and token budget as the research agent. No new config fields needed.

## Edge Cases

Handled in the tool function (`src/tools/review_sub_agent.py`):

| Case | Handling |
|------|----------|
| Empty diff | Return early: "No changes to review" |
| Diff too large (>50k tokens) | Truncate: review first N files, append note listing skipped files |
| Binary files in diff | Skip, note in output: "N binary files skipped" |
| Deleted files | Include in diff context but don't attempt to read them |

## Files Changed

| File | Change |
|------|--------|
| `src/tools/review_sub_agent.py` | **New** — `review_changes` tool |
| `src/llm/prompts.py` | Add `SUB_AGENT_SECTIONS["review_mode"]`, parameterize `build_sub_agent_prompt()` |
| `src/core/sub_agent.py` | Add `sub_agent_type` and `initial_context` params to `run_sub_agent()` and `_create_chat_manager()` |

3 files changed, 1 new. No settings changes, no architectural restructuring.
