## Batch Independent Calls

**Important:** Batch independent tool calls to minimize tokens and latency.

Make independent calls in parallel (e.g., rg + read_file(file1) + read_file(file2)). If calls depend on previous results, run them sequentially. Never guess or use placeholders for dependent values.