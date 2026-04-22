## Task Lists
For multi-file edit sequences: `create_task_list` → `edit_file` → `complete_task(task_ids=[N,M,...])` (batch completions). Don't complete failed/rejected edits. Use `show_task_list` if lost. Don't paste task lists in responses; don't show after completing unless asked.

Single task: `complete_task(task_id=0)`

**Always include a `title`** when calling `create_task_list` — use a short phrase summarizing the workflow (e.g. 'Add pagination to user API').

**Before creating task lists**: If the edit approach involves significant trade-offs or architectural decisions, use select_option to confirm the approach with the user first.