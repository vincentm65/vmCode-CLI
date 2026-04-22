## Trust Subagent Results

**Important:** When sub_agent returns results with '## INJECTED FILE CONTENTS', the files have already been read.

**You must:**
- Use the injected file contents directly
- Do not call `read_file()` for any file that appears in '## Injected File Contents'
- Do not re-read the same file with different line ranges
- Do not read "full file" when subagent already injected it

The injected code blocks contain the actual file content — not summaries.

Example:
- Subagent injects: '### src/auth.py (lines 45-78)'
- Use the injected content directly
- Do not call `read_file("src/auth.py", 45, 78)`
- Do not call `read_file("src/auth.py")` — don't read full file either

Only call `read_file()` for files not mentioned in the injected section.

Violating this instruction wastes tokens and shows you didn't read the subagent's work.