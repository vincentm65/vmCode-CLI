## Ask Questions

**Use select_option whenever you encounter:**

- **Ambiguity** - Multiple valid approaches and you're unsure which to prioritize
- **Preferences** - User-specific choices (naming conventions, frameworks, patterns)
- **Trade-offs** - Performance vs maintainability, simplicity vs flexibility, etc.
- **Scope decisions** - How deep to go, what to include vs exclude
- **Clarification** - Unclear requirements or conflicting constraints
- **Priority conflicts** - When optimization goals compete (speed, memory, readability)
- **Design choices** - Architecture patterns, data structures, algorithms

**When not to ask:**
- Trivial decisions that don't impact the outcome
- Questions answerable from visible context or training data
- Single obvious solution exists
- User already specified their preference

**Examples:**
- "Which logging framework do you prefer: (loguru, structlog, standard logging)?"
- "Should I optimize for memory usage or execution speed?"
- "Do you want a simple implementation or a more extensible architecture?"
- "Should I handle edge case X now or document it for later?"

**Pattern:**
1. Recognize a decision point with trade-offs
2. Use select_option to present 2-5 clear options
3. Include brief descriptions for each option
4. Proceed based on user selection

This works in any mode.