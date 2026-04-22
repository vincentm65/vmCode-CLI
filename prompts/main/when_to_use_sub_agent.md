## When to Use sub_agent

Use for broad multi-file exploration when the answer is not already available from visible context. This includes tracing flows, architecture questions, and pattern analysis requiring multiple search+read cycles.

Do not call sub_agent when one direct read_file or one targeted rg is sufficient for the answer.

**Alternative: Use select_option** when you need user input on decisions, preferences, or clarifications - it's faster and more direct than exploration for trade-off questions.