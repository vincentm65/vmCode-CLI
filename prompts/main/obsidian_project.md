**Flat folder structure (CRITICAL):** Notes go directly into `Bugs/`, `Tasks/`, or `Docs/`. The ONLY allowed subfolder is `Done/` (for archiving). NEVER create nested subfolders like `Tasks/Feature Name/` or `Bugs/Component/`. Task/bug filenames must be flat: `Tasks/Enhanced web search with full page content reading.md` (correct) vs `Tasks/Enhanced Web Search/DuckDuckGo adapter.md` (wrong).

**Title format:** `title: Short description in sentence case` — no quotes, no type prefix (never `Bug: ...` or `Task N: ...`). The H1 heading must match the title exactly.

**Type field (exact values):** `type: bug | task | doc` — lowercase only.

**Note schemas:** Every note MUST follow its type template exactly.

- **Bug:** `Bugs/<title>.md`
  Required FM: title, type (bug), status, priority, date_created, date_modified, tags.
  Body sections: ## Related Files, ## Steps to Reproduce, ## Expected Behavior, ## Actual Behavior.
  Optional body: ## Root Cause, ## Fix, ## Investigation Summary.

  Example:
  ```
  ---
  title: First Letter Cut Off in Agent Response
  type: bug
  status: reported
  priority: high
  date_created: 2025-07-27
  date_modified: 2025-07-27
  tags: [bug, agent, rendering]
  ---

  # First Letter Cut Off in Agent Response

  ## Related Files
  - src/core/agentic.py:1154

  ## Steps to Reproduce
  1. Use agentic mode
  2. Get a response starting with characters in lstrip set

  ## Expected Behavior
  Full first character/word is preserved.

  ## Actual Behavior
  Leading characters are silently stripped.
  ```

- **Task:** `Tasks/<title>.md`
  Required FM: title, type (task), status, priority, date_created, date_modified, tags.
  Body sections: ## Related Files, ## Problem (or ## Scope / ## Description).

  Example:
  ```
  ---
  title: Extract retry logic to src/core/retry.py
  type: task
  status: todo
  priority: medium
  date_created: 2025-07-10
  date_modified: 2025-07-10
  tags: [refactor, agentic]
  ---

  # Extract retry logic to src/core/retry.py

  ## Related Files
  - src/core/agentic.py:522-586
  - src/core/retry.py (new)

  ## Scope
  Move retry constants and functions from agentic.py into retry.py.
  ```

- **Doc:** `Docs/<title>.md`
  Required FM: title, type (doc), date_created, date_modified, tags.
  Optional FM: priority.
  No required body sections — free-form markdown.

**Common mistakes to avoid:**
- NEVER create `Bugs/`, `Tasks/` folders in the repo root
- NEVER put vault notes in `.temp/`
- NEVER use `# Bug:`, `# Task:` prefixes in H1 headings
- NEVER use quoted strings for title values in frontmatter
- NEVER nest folders (e.g. `Tasks/Some Feature/subtask.md`)
- NEVER use uppercase or mixed-case type values