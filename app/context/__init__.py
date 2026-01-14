"""Context management module for intelligent chat context assembly.

This module provides:
- Token budget management for context window optimization
- Project phase detection (Discovery -> Definition -> Validation -> Build-Ready)
- State frame generation for goal-based context
- Conversation compression via summarization
- Tool result truncation
- Semantic intent classification
- Dynamic system prompt building
"""

from app.context.models import (
    Blocker,
    ChatMessage,
    CompressedHistory,
    IntentClassification,
    NextAction,
    PhaseCriteria,
    ProjectPhase,
    ProjectStateFrame,
    TokenAllocation,
    TokenBudgetResult,
)

__all__ = [
    # Models
    "Blocker",
    "ChatMessage",
    "CompressedHistory",
    "IntentClassification",
    "NextAction",
    "PhaseCriteria",
    "ProjectPhase",
    "ProjectStateFrame",
    "TokenAllocation",
    "TokenBudgetResult",
]
