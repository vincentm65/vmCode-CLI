## Obsidian Vault

**Vault root:** `${vault_root}`
${project_header}

**Path separation (CRITICAL):** Project folder is for **notes only**. Code files use **relative paths** from repo root (e.g. `src/core/chat_manager.py`). Never prepend vault/project paths to code paths.

**Content routing (CRITICAL):** ALL project notes (bugs, tasks, docs) MUST be created in the vault using `create_file` with absolute vault paths (e.g. `${project_folder}/Bugs/My bug title.md`). Code changes (source, configs, tests) → relative repo paths. Scratch/draft work → `.temp/` at repo root ONLY. NEVER create vault notes in `.temp/`, the repo root, or any repo subdirectory.

**Plan routing:** When asked to plan a feature or change, create a task note in `${project_folder}/Tasks/`. Do NOT create plan files in `.temp/` or the repo — task notes ARE the plan records.

**Search:** `rg` scans both repo and vault (vault results show `[vault]` prefix). Excluded: ${excluded}.

**Rules:** `[[wiki-links]]` for cross-references, YAML frontmatter in all notes, never touch `.obsidian/`, update `date_modified` on edits. Code refs in notes: plain paths (not wiki-links).

**Archiving:** Terminal status (bug: fixed/verified, task: done) → move to `Done/` folder via `execute_command mv`. User asks to sweep → `mv` each done note.