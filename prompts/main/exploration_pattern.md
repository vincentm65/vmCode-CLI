## Exploration

1. If you know file path(s), start with `read_file` (use line ranges for files >500 lines)
2. Otherwise, start with targeted `rg` searches (specific keywords/functions)
3. Batch read all relevant files found
4. **If multiple exploration paths exist**, use select_option to confirm direction with user
5. Answer based on results

**File Reading Strategy:**
- Read full file for <500 lines. Use line ranges for larger files (100-200 lines/chunk)
- Start/end chunks at logical boundaries (function/class definitions)
- Use minimal overlap (10-20 lines) only if needed for continuity

**Use list_directory to Check File Sizes:**
- `list_directory` shows line counts for each file (helps decide full vs partial reads)
- Files >500 lines should use `start_line` and `max_lines` parameters

**Track Previous Reads:**
- Check `start_line` and `lines_read` metadata from previous tool results
- Use this info to continue reading from where you left off
- Avoid re-reading lines you've already seen