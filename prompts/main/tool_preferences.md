## Tool Preferences

**Prefer native tools over execute_command:**
- Use `rg` tool (not `execute_command rg`) for code searches
- Use `read_file` (not `Get-Content`) for reading files
- Use `list_directory` (not `Get-ChildItem`) for listing directories
- Use `create_file` (not `New-Item`) for creating files
- Use `edit_file` (not `Set-Content`/`Add-Content`) for editing files

**Use execute_command for:**
- Git operations: `git clone`, `git pull`, `git push`, `git status`, etc.
- File operations: `rm`, `mv`, `cp`, `mkdir`, `rmdir`, `chmod`, etc.
- System tasks: package management (`pacman`, `pip`, `npm`), process management (`ps`, `kill`), service management (`systemctl`)
- Network tools: `ping`, `curl`, `wget`, `ssh`, `scp`
- Development: `make`, `cmake`, building projects, running tests
- Any other shell commands that don't overlap with native tools

**Do not use execute_command for:**
- Code search: use `rg` tool
- Reading files: use `read_file` tool
- Listing directories: use `list_directory` tool
- Creating files: use `create_file` tool
- Editing files: use `edit_file` tool
- python/python3 commands to edit/modify files (use native tools: create_file, edit_file)