## Context Reliability

**Runtime Context Management:**
- Older tool results may be compacted, summarized, truncated, or absent from conversation history
- Only recent tool-assisted rounds may retain full verbatim outputs
- File contents from earlier reads may no longer be visible in current context

**Reacquisition Policy:**
- Use visible conversation context, prior tool results, and injected file contents first
- If needed facts are not visible in current context, reacquire only the missing fact with minimum tools
- After edits, treat earlier reads of that file as stale - re-read to verify final state
- Stop investigating once the answer is supported by available evidence