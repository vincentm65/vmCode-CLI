## Targeted Searching

**Avoid spam searches** - every rg call has latency:
1. **Reuse existing results** - before searching again, check if previous results already contain your answer
2. **Use files_with_matches first** - get file list, then read specific files  
3. **One search often enough** - combine patterns with `|` before making multiple calls
4. **Specific > Generic** - search "def authenticate_user" not "auth" or "handle"

Good: single rg for pattern + read_file(file1) + read_file(file2)
Bad: rg → read → rg → read → rg → read (chaining sequential searches)