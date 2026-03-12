# Plan Review System - Building Plan

## Overview
Multi-agent system that reviews generated plans through discussion and simple majority voting using 3 distinct reviewer personas.

---

## System Architecture

```
┌─────────────────┐
│  Plan Generator │ (creates initial plan)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Review Coordinator │ (orchestrates review process)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Reviewer│ │Reviewer│ ─┐
│ Agent 1│ │ Agent 2│  │ 3 reviewer agents
└────────┘ └────────┘  │ (distinct personas)
    ┌────────┐
    │Reviewer│
    │ Agent 3│
    └────────┘
         │
         ▼ (discussion rounds)
┌─────────────────┐
│  Simple Voting  │ (majority wins)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Final Decision │ (approved/rejected)
└─────────────────┘
```

---

## Modular Architecture

### Directory Structure
```
src/
├── core/                          # Core system (unchanged)
│   ├── plan_generator.py         # Existing plan generation
│   ├── plan_executor.py           # Existing plan execution
│   └── ...
│
└── plan_review/                   # DELETE THIS FOLDER TO REMOVE ENTIRELY
    ├── __init__.py                # Main interface
    ├── review_system.py           # Main coordinator
    ├── config.json                # Review system config
    │
    ├── reviewers/                 # DELETE TO REMOVE PERSONALITIES
    │   ├── __init__.py
    │   ├── base.py                # Base reviewer interface
    │   ├── pragmatic.py           # Pragmatic Engineer
    │   ├── security.py            # Security Analyst
    │   └── ux.py                  # UX Advocate
    │
    ├── discussion.py              # Discussion orchestration
    ├── voting.py                  # Simple majority voting
    └── prompts/                   # DELETE TO REMOVE PROMPTS
        ├── pragmatic.txt
        ├── security.txt
        └── ux.txt
```

### Modular Design Principles

**1. Single Folder Removal**
- Delete `src/plan_review/` → entire feature removed
- Core system continues without any changes

**2. Single Integration Point**
- Only one function in core code touches the review system
- `src/core/plan_generator.py:_maybe_review_plan()`
- Uses try/except for graceful degradation

**3. Dynamic Reviewer Loading**
- Reviewers discovered at runtime from `reviewers/` folder
- Delete `security.py` → No Security Analyst (others work)
- Delete all reviewers → Review system disabled, passes plan through

**4. Graceful Degradation Layers**

| What you delete | What happens |
|-----------------|--------------|
| `src/plan_review/` | Core system works, no reviews |
| `reviewers/security.py` | Reviews with 2 reviewers |
| `reviewers/` | Review system loads 0 reviewers, passes plan through |
| `prompts/` | Falls back to generic prompts |
| `discussion.py` | Skip discussion, go directly to voting |

**5. Clear Interfaces**
- `Reviewer` abstract base class (all personas inherit)
- `ReviewResult` dataclass (immutable result)
- `Outcome` enum (APPROVED, REJECTED)

### Activation Methods

Once implemented, users can activate review via:

1. **Chat Command**: "Generate a plan to refactor auth module and review it"
2. **Mode Flag**: "Create a plan for X in review mode"
3. **Configuration**: Set `enabled: true` in config.json
4. **Follow-up Prompt**: Auto-ask "Should I have this plan reviewed?" after plan generation

**Recommended**: Auto-prompt after plan generation, with chat command shortcut for explicit activation.

---

## Reviewer Personas

1. **Pragmatic Engineer**
   - Focus: Implementation feasibility, timelines, complexity
   - Asks: "Can this actually be built?" "What's the risk?"
   - Prefers: Simple, proven solutions
   - Dislikes: Over-engineering, experimental approaches

2. **Security Analyst**
   - Focus: Security vulnerabilities, data protection, access control
   - Asks: "What if this is exploited?" "Where's the attack surface?"
   - Prefers: Defense-in-depth, least privilege
   - Dislikes: Hardcoded secrets, insecure defaults

3. **UX Advocate**
   - Focus: User experience, accessibility, clarity
   - Asks: "How does this feel to use?" "Is this confusing?"
   - Prefers: Intuitive flows, clear error messages
   - Dislikes: Hidden features, complex workflows

---

## Review Process Flow

### Phase 1: Initial Review (Parallel)
1. Each reviewer receives:
   - The generated plan
   - Relevant code/context (via sub_agent research)
   - Their persona-specific review criteria

2. Each reviewer outputs:
   - Vote: approve/reject
   - Key concerns (1-3 bullet points)
   - Strengths (1-2 bullet points)

### Phase 2: Discussion (Structured Rounds)
**Round 1: Concern Sharing**
- Each reviewer shares their top 2 concerns
- Others can ask 1-2 clarifying questions

**Round 2: Rebuttal/Defense**
- Reviewers defend their positions
- Propose compromises or alternatives

**Discussion Rules:**
- Max 2 rounds
- Each response limited to 150 words
- Must cite specific plan sections or code

### Phase 3: Voting
Each reviewer casts a vote: approve or reject

**Aggregation:**
- Simple majority (2+ approve = APPROVED)
- No weights, no vetos, no confidence scores

### Phase 4: Final Decision
**Outcomes:**
- **APPROVED**: Plan moves forward as-is
- **REJECTED**: Plan fails; user can modify or generate new plan

**Decision Report includes:**
- Final outcome
- Voting breakdown
- Key discussion points
- Reviewer signatures (which agents participated)

---

## User Experience During Review

### What the User Sees

**Step 1: Trigger Review**
```
User: "Generate a plan to refactor the auth module and review it"
```

**System response:**
```
✓ Plan generated (47 tasks)
→ Starting plan review session...

Reviewers: Pragmatic Engineer, Security Analyst, UX Advocate
Estimated time: ~30-60 seconds
```

---

**Step 2: Initial Reviews (Parallel)**

**Behind the scenes:**
- 3 reviewer agents receive the plan + context
- Each uses `sub_agent` to research relevant code
- Each analyzes through their persona's lens

**What you see:**
```
⏳ Reviewing plan...
   Pragmatic Engineer: researching code...
   Security Analyst: analyzing attack surface...
   UX Advocate: evaluating workflows...
```

---

**Step 3: Discussion Rounds (If needed)**

**Round 1 - Concern Sharing:**
```
🔍 Discussion Round 1/2

Pragmatic Engineer: "This refactor touches 12 files. Risk is high.
Can we break into 2 phases?"

Security Analyst: "Agreed. Also, the password reset flow removes
rate limiting - that's a red flag."

UX Advocate: "The new flow adds 2 clicks. Users will be frustrated.
Can we streamline?"

[Each reviewer asks 1-2 clarifying questions]
```

**Round 2 - Rebuttal/Defense (if disagreements persist):**
```
💬 Discussion Round 2/2

Pragmatic Engineer: "2 phases is safer. Phase 1: core auth only.
Phase 2: peripheral features."

Security Analyst: "If we split phases, rate limiting must be in
Phase 1. Non-negotiable."

UX Advocate: "I can accept 2 phases if Phase 1 improves the login
error messages. That's the biggest pain point."
```



---

**Step 4: Voting**

**What you see:**
```
📊 Voting Results

Reviewer                Vote
─────────────────────────────────────
Pragmatic Engineer      APPROVE
Security Analyst        REJECT
UX Advocate             APPROVE

Result: APPROVED (2/3 majority)
```

---

**Step 5: Final Decision**

**Outcome 1: APPROVED**
```
✅ PLAN APPROVED

Summary: The plan is approved to proceed as-is.

Key strengths:
• Incremental approach reduces risk
• Clear task breakdown
• Rollback strategy included

Discussion highlights:
• Split into 2 phases recommended
• Rate limiting in Phase 1 is critical

Next: Execute plan? [Y/n]
```

---

**Outcome 2: REJECTED**
```
❌ PLAN REJECTED

Reasons:
• Security concern: Password reset flow removes rate limiting
• UX concern: Too many steps in new workflow
• Risk: Touches 12 files simultaneously

Recommendations:
• Redesign with security-first approach
• Reduce scope to 5-6 files max
• Simplify user flow

Generate new plan? [Y/n]
```

---

### Full Transcript

Users can request the complete discussion at any time:
```
User: "Show me the full review transcript"
[System outputs complete discussion log with all reviewer comments,
citations, and decision rationale]
```

---

### Time Breakdown

| Phase | Time |
|-------|------|
| Initial reviews | 15-25s |
| Discussion (if needed) | 15-30s |
| Voting | 2-5s |
| **Total** | **17-60s** |

Simple plans may skip discussion entirely (unanimous approval).

---

### User Controls

Users can interrupt at any point:
```
User: "Skip discussion, just vote now"
→ Skips to voting immediately

User: "Show me the transcript"
→ Displays full discussion log
```

---

## Integration Points

### Single Hook into Core System

**File:** `src/core/plan_generator.py` (existing file - minimal modification)

```python
def generate_plan(task: str, review: bool = False) -> Plan:
    """Generate a plan, optionally review it"""
    plan = _create_plan(task)

    if review:
        plan = _maybe_review_plan(plan)

    return plan

def _maybe_review_plan(plan: Plan) -> Plan:
    """Optional review - gracefully degrades if review system removed"""
    try:
        from plan_review.review_system import review_plan
        result = review_plan(plan)
        return result.approved_plan if result.is_approved() else plan
    except ImportError:
        # Review system not installed, return plan as-is
        return plan
```

**That's the only change needed in core code.** One function, one try/except block.

---

### Review System Interface

**File:** `src/plan_review/__init__.py`

```python
"""
Plan Review System

This module is optional. If this folder is deleted, all functionality
gracefully degrades without breaking core systems.
"""

__all__ = ["review_plan", "ReviewResult"]

def review_plan(plan: Plan, context: dict = None) -> ReviewResult:
    """
    Review a plan using multi-agent system.

    Args:
        plan: The plan to review
        context: Optional code context (for sub_agent research)

    Returns:
        ReviewResult with outcome, voting breakdown
    """
    from .review_system import ReviewSystem
    system = ReviewSystem()
    return system.review(plan, context)
```

---

### Sub-Agent Integration
- Use existing `sub_agent` tool for code/context research
- Each reviewer can call sub_agent independently
- Cache results to avoid duplicate research

---

### Task List Integration
- Track review phases as tasks
- Use `create_task_list`, `complete_task` for progress

---

### Configuration

**File:** `src/plan_review/config.json`

```json
{
  "enabled": true,
  "discussion": {
    "max_rounds": 2,
    "max_response_words": 150,
    "require_citations": true
  },
  "voting": {
    "type": "majority"
  }
}
```

---

## Implementation Phases

### Phase 1: MVP (2-3 days)
- [ ] Create 3 reviewer persona prompt templates
- [ ] Build review coordinator (parallel reviews only)
- [ ] Implement simple majority voting
- [ ] Generate basic decision report

**Deliverable:** Working review system with parallel reviews → vote → decision

### Phase 2: Discussion (2 days)
- [ ] Add structured discussion rounds (2 rounds max)
- [ ] Implement turn-taking logic
- [ ] Add response length limits (150 words)
- [ ] Build discussion transcript

**Deliverable:** Agents can discuss concerns before voting

### Phase 3: Polish (1-2 days)
- [ ] Add detailed decision reports
- [ ] Implement caching for sub_agent calls
- [ ] Add review transcript export

**Deliverable:** Production-ready system

---

## Technical Considerations

### Token Usage Optimization
- Share context between reviewers (don't re-send same code)
- Cache sub_agent research results
- Limit discussion length (150 words per response)

### Performance
- Parallel initial reviews (can run simultaneously)
- Sequential discussion (enforced turn-taking)
- Early exit if unanimous approval

### Error Handling
- Timeout per reviewer (e.g., 60s per response)
- Fallback if reviewer fails (continue with remaining)

### Persona Prompt Engineering
Each reviewer needs:
- Role definition
- Focus areas
- Output format (approve/reject + concerns)

---

## Success Metrics

1. **Coverage**: % of issues caught vs single reviewer
2. **Consensus**: % of reviews that reach majority agreement
3. **Efficiency**: Average review time (tokens + latency)
4. **Quality**: Human eval of approved plans
5. **Convergence**: % of reviews that need 2 discussion rounds vs 1

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Endless debate | Max 2 rounds, forced vote |
| Groupthink | 3 distinct personas with different focus areas |
| Token bloat | 150-word response limits, caching |
| Slow decision | Timeout per phase, early exit on consensus |
| Reviewers sound the same | Careful prompt engineering with specific focus areas |

---

## Modular Removal & Testing

### Testing Modular Removal

```bash
# Test 1: Remove entire review system
rm -rf src/plan_review/
# Result: Core system still works, no review functionality

# Test 2: Remove specific reviewer
rm src/plan_review/reviewers/security.py
# Result: Review system works, just without Security Analyst

# Test 3: Remove all reviewers
rm -rf src/plan_review/reviewers/
# Result: Review system loads with 0 reviewers, returns plan as-is

# Test 4: Remove prompts
rm -rf src/plan_review/prompts/
# Result: Reviewers fall back to generic prompts
```

### Graceful Degradation Summary

| Removal | System Behavior |
|---------|-----------------|
| Entire `plan_review/` folder | Core works, no reviews |
| Single reviewer file | Reviews with remaining personas |
| All reviewer files | Review disabled, plan passes through |
| Discussion module | Skip to voting directly |
| Prompts folder | Generic prompts used |

### Key Design Guarantees

1. **Zero coupling** - Core code doesn't depend on review system internals
2. **Single entry point** - One function to enable/disable entire feature
3. **Dynamic loading** - Reviewers discovered at runtime, not hardcoded
4. **Graceful fallbacks** - Every missing component has a safe default

---

## Next Steps

1. Create modular directory structure (`src/plan_review/`)
2. Implement base `Reviewer` interface and `ReviewResult` dataclass
3. Create 3 reviewer persona prompt templates
4. Implement `ReviewSystem` coordinator with dynamic reviewer loading
5. Build MVP with 3 reviewers (parallel reviews → vote)
6. Add single integration point in `src/core/plan_generator.py`
7. Test modular removal (delete folders, verify graceful degradation)
8. Test with sample plans
9. Add discussion rounds module (2 rounds max)
10. Polish and optimize

---

**Estimated Total Time:** 5-7 days
**Complexity:** Low-Medium
**Risk:** Low (well-contained, modular feature)

---
