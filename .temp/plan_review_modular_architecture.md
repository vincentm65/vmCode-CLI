# Plan Review System - Modular Architecture

## Directory Structure

```
src/
├── core/                          # Core system (unchanged)
│   ├── plan_generator.py         # Existing plan generation
│   ├── plan_executor.py           # Existing plan execution
│   └── ...
│
└── plan_review/                   # DELETE THIS FOLDER TO REMOVE ENTIRELY
    ├── __init__.py                # Optional: expose main interface
    ├── review_system.py           # Main coordinator (entry point)
    ├── config.json                # Review system config
    │
    ├── reviewers/                 # DELETE THIS TO REMOVE PERSONALITIES
    │   ├── __init__.py
    │   ├── base.py                # Base reviewer interface
    │   ├── pragmatic.py           # Pragmatic Engineer
    │   ├── security.py            # Security Analyst
    │   ├── ux.py                  # UX Advocate
    │   ├── performance.py         # Performance Optimizer
    │   ├── maintainability.py     # Maintainability Maven
    │   ├── testing.py             # Test Champion
    │   └── integration.py         # Integration Specialist
    │
    ├── discussion.py              # Discussion orchestration
    ├── voting.py                  # Voting logic
    └── prompts/                   # DELETE THIS TO REMOVE PROMPTS
        ├── pragmatic.txt
        ├── security.txt
        ├── ux.txt
        ├── performance.txt
        ├── maintainability.txt
        ├── testing.txt
        └── integration.txt
```

**Removal:**
```bash
rm -rf src/plan_review/           # Removes ALL functionality
```

---

## Integration Points (Minimal, Well-Defined)

### 1. Single Entry Point Hook

**File:** `src/core/plan_generator.py` (existing file)

**Before (no review system):**
```python
def generate_plan(task: str) -> Plan:
    plan = _create_plan(task)
    return plan
```

**After (with review system):**
```python
def generate_plan(task: str, review: bool = False) -> Plan:
    plan = _create_plan(task)

    if review:
        plan = _maybe_review_plan(plan)  # ← SINGLE HOOK

    return plan

def _maybe_review_plan(plan: Plan) -> Plan:
    """Optional review - gracefully degrades if review system removed"""
    try:
        from plan_review.review_system import review_plan
        return review_plan(plan)
    except ImportError:
        # Review system not installed, return plan as-is
        return plan
```

**That's it.** One function, one try/except block.

---

### 2. Review System Interface

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
        ReviewResult with outcome, voting breakdown, modifications

    This function can be safely imported - if reviewers/ folder is deleted,
    it will degrade gracefully.
    """
    from .review_system import ReviewSystem

    system = ReviewSystem()
    return system.review(plan, context)
```

---

## Module Contracts (Interfaces)

### Reviewer Interface

**File:** `src/plan_review/reviewers/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class Reviewer(ABC):
    """Base class for all reviewer personas"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Reviewer name (e.g., 'Pragmatic Engineer')"""
        pass

    @property
    @abstractmethod
    def focus_areas(self) -> list[str]:
        """What this reviewer focuses on"""
        pass

    @abstractmethod
    def review(self, plan: str, context: dict) -> Review:
        """
        Review a plan and return structured feedback.

        Args:
            plan: The plan to review
            context: Code/context information

        Returns:
            Review object with vote, concerns, strengths, confidence
        """
        pass
```

**All reviewers inherit from this.** Delete a reviewer file, that persona is gone.

---

### Review Result Interface

**File:** `src/plan_review/review_system.py`

```python
from dataclasses import dataclass
from enum import Enum

class Outcome(Enum):
    APPROVED = "approved"
    APPROVED_WITH_MODIFICATIONS = "approved_with_modifications"
    REJECTED = "rejected"

@dataclass
class ReviewResult:
    """Immutable result of plan review"""
    outcome: Outcome
    voting_breakdown: dict
    discussion_transcript: list
    required_modifications: list[str]
    confidence_score: float

    def is_approved(self) -> bool:
        return self.outcome in (Outcome.APPROVED, Outcome.APPROVED_WITH_MODIFICATIONS)
```

---

## Reviewer Module Structure

### Example: Security Analyst

**File:** `src/plan_review/reviewers/security.py`

```python
from .base import Reviewer
from ..prompts import load_prompt

class SecurityReviewer(Reviewer):
    """Security-focused reviewer with veto power"""

    @property
    def name(self) -> str:
        return "Security Analyst"

    @property
    def focus_areas(self) -> list[str]:
        return [
            "security vulnerabilities",
            "data protection",
            "access control",
            "attack surface"
        ]

    @property
    def weight(self) -> float:
        """Higher weight = veto power"""
        return 1.5

    def review(self, plan: str, context: dict) -> Review:
        prompt = load_prompt("security")  # Loads from prompts/security.txt

        # Use sub_agent to research code
        research = self._research_code(context)

        # Get LLM review using persona prompt
        response = self._call_llm(prompt, plan, research)

        return Review(
            vote=response.vote,
            concerns=response.concerns,
            strengths=response.strengths,
            confidence=response.confidence,
            citations=response.citations
        )
```

**Delete `security.py` → Security Analyst persona removed.**

---

## Review System Coordinator

**File:** `src/plan_review/review_system.py`

```python
import importlib
from pathlib import Path
from typing import List

class ReviewSystem:
    """Orchestrates multi-agent plan review"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.reviewers = self._load_reviewers()

    def _load_reviewers(self) -> List[Reviewer]:
        """Dynamically load all reviewers from reviewers/ folder"""
        reviewers = []

        reviewers_dir = Path(__file__).parent / "reviewers"
        for file in reviewers_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue

            module_name = f"plan_review.reviewers.{file.stem}"

            try:
                module = importlib.import_module(module_name)
                # Find Reviewer subclass in module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Reviewer) and
                        attr != Reviewer):
                        reviewers.append(attr())
            except Exception as e:
                print(f"Warning: Failed to load reviewer {file.stem}: {e}")

        return reviewers

    def review(self, plan: str, context: dict) -> ReviewResult:
        """Main review orchestration"""
        # Phase 1: Parallel reviews
        reviews = self._run_parallel_reviews(plan, context)

        # Phase 2: Discussion (if needed)
        if self._needs_discussion(reviews):
            discussion = DiscussionManager()
            discussion.run(self.reviewers, reviews)

        # Phase 3: Voting
        voting_result = VotingEngine().vote(self.reviewers, reviews)

        # Phase 4: Decision
        return self._make_decision(voting_result)
```

**Key:** Reviewers loaded **dynamically**. Delete files, they're simply not loaded.

---

## Discussion Module

**File:** `src/plan_review/discussion.py`

```python
class DiscussionManager:
    """Manages structured discussion rounds"""

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds

    def run(self, reviewers: List[Reviewer], reviews: List[Review]) -> list:
        """Run discussion rounds and return transcript"""
        transcript = []

        for round_num in range(1, self.max_rounds + 1):
            round_transcript = self._run_round(reviewers, reviews, round_num)
            transcript.extend(round_transcript)

            if self._has_consensus(reviewers):
                break

        return transcript
```

---

## Voting Module

**File:** `src/plan_review/voting.py`

```python
class VotingEngine:
    """Aggregates reviewer votes with weighted scoring"""

    def vote(self, reviewers: List[Reviewer], reviews: List[Review]) -> VoteResult:
        """Calculate weighted voting result"""
        total_weight = sum(r.weight for r in reviewers)
        approve_weight = sum(
            r.weight * reviews[i].confidence
            for i, r in enumerate(reviewers)
            if reviews[i].vote == Vote.APPROVE
        )

        score = approve_weight / total_weight
        return VoteResult(score=score, breakdown=self._build_breakdown(...))
```

---

## Configuration

**File:** `src/plan_review/config.json`

```json
{
  "enabled": true,
  "reviewers": {
    "auto_load": true,
    "exclude": []
  },
  "discussion": {
    "max_rounds": 3,
    "max_response_words": 150,
    "require_citations": true
  },
  "voting": {
    "approval_threshold": 0.67,
    "enable_veto": true
  },
  "personalities": {
    "pragmatic": {"weight": 1.0},
    "security": {"weight": 1.5},
    "ux": {"weight": 1.0},
    "performance": {"weight": 1.0},
    "maintainability": {"weight": 1.0},
    "testing": {"weight": 1.0},
    "integration": {"weight": 1.0}
  }
}
```

---

## Prompt Templates

**File:** `src/plan_review/prompts/security.txt`

```
You are a Security Analyst reviewing a technical plan.

Your focus:
- Security vulnerabilities
- Data protection
- Access control
- Attack surface

You have VETO POWER. If you see critical security issues, you must reject.

Review the following plan:
{plan}

Context from code analysis:
{context}

Provide your review in this format:
VOTE: [APPROVE/REJECT/NEEDS_CHANGES]
CONFIDENCE: [1-5]
CONCERNS:
- [concern 1]
- [concern 2]
STRENGTHS:
- [strength 1]
CITATIONS:
- [specific plan section or code reference]
```

**Delete `security.txt` → Security reviewer falls back to generic prompt or fails gracefully.**

---

## Graceful Degradation

### Scenario 1: Review System Deleted

```python
# User requests review
plan = generate_plan(task, review=True)

# _maybe_review_plan catches ImportError
# Plan returns as-is, no review performed
```

**Result:** System works normally, just no review.

---

### Scenario 2: Some Reviewers Deleted

```python
# Only 3 reviewers loaded instead of 7
# System still works, just fewer perspectives
```

**Result:** Review happens with available reviewers.

---

### Scenario 3: Prompts Deleted

```python
# Reviewer fails to load prompt
# Falls back to generic base prompt or skips that reviewer
```

**Result:** Review continues with remaining reviewers.

---

## Testing Modular Removal

```bash
# Test 1: Remove entire review system
rm -rf src/plan_review/
# Core system still works, no review functionality

# Test 2: Remove specific reviewer
rm src/plan_review/reviewers/security.py
# Review system works, just without Security Analyst

# Test 3: Remove all reviewers
rm -rf src/plan_review/reviewers/
# Review system loads with 0 reviewers, returns plan as-is

# Test 4: Remove prompts
rm -rf src/plan_review/prompts/
# Reviewers fall back to generic prompts
```

---

## Summary: Modular by Design

| Component | Delete to Remove | Impact |
|-----------|------------------|--------|
| Entire system | `src/plan_review/` | Core system unchanged, no reviews |
| Specific persona | `src/plan_review/reviewers/X.py` | That reviewer unavailable |
| All personas | `src/plan_review/reviewers/` | Review system disabled (no reviewers) |
| Prompts | `src/plan_review/prompts/` | Generic prompts used |
| Discussion | `src/plan_review/discussion.py` | Skip to voting directly |
| Voting | `src/plan_review/voting.py` | Simple majority instead |

**Single integration point:** `src/core/plan_generator.py:_maybe_review_plan()`

That's the only place you need to touch to add/remove the review system.
