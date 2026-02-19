"""Pydantic models for the Intelligence Briefing system.

The briefing transforms flat action cards into a narrative intelligence brief:
- Situation: narrative summary of project state
- What Changed: temporal diff since last session
- Tensions: contradicting beliefs/positions
- Hypotheses: testable beliefs in mid-confidence range
- Heartbeat: project health metrics
- Actions: terse next-best-actions (reuses TerseAction from schemas_actions)
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.core.schemas_actions import ContextPhase, TerseAction


# =============================================================================
# Conversation Starter (signal-informed)
# =============================================================================


class EvidenceAnchor(BaseModel):
    """A specific reference from a signal that grounds the conversation starter."""

    excerpt: str  # Verbatim quote, max ~280 chars
    signal_label: str = ""  # e.g., "Kickoff Meeting Notes"
    signal_type: str = ""  # e.g., "transcript", "file_text"
    entity_name: str | None = None  # Entity this excerpt relates to


class ConversationStarter(BaseModel):
    """ONE rich conversation proposal based on actual signal content."""

    starter_id: str  # MD5 hash for cache key
    hook: str  # "I noticed..." opener (1-2 sentences)
    body: str  # Why this matters (2-4 sentences)
    question: str  # Conversational question to explore
    anchors: list[EvidenceAnchor] = Field(default_factory=list)  # 1-3 signal references
    chat_context: str = ""  # Injected into chat system prompt
    topic_domain: str = ""  # workflow, persona, process, data, etc.
    is_fallback: bool = False  # True when no signal content available
    generated_at: datetime | None = None


# =============================================================================
# Enums
# =============================================================================


class ChangeType(str, Enum):
    """Types of temporal changes tracked between sessions."""

    BELIEF_STRENGTHENED = "belief_strengthened"
    BELIEF_WEAKENED = "belief_weakened"
    BELIEF_CREATED = "belief_created"
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    SIGNAL_PROCESSED = "signal_processed"
    FACT_ADDED = "fact_added"
    INSIGHT_ADDED = "insight_added"


class HypothesisStatus(str, Enum):
    """Lifecycle states for hypotheses."""

    PROPOSED = "proposed"
    TESTING = "testing"
    GRADUATED = "graduated"
    REJECTED = "rejected"


# =============================================================================
# Briefing sections
# =============================================================================


class BriefingSituation(BaseModel):
    """Narrative situation summary — the 'here's where we are' section."""

    narrative: str = ""  # 2-3 sentences from Sonnet, conversational
    project_name: str = ""
    phase: ContextPhase = ContextPhase.EMPTY
    phase_progress: float = 0.0
    key_stakeholders: list[str] = Field(default_factory=list)
    entity_summary: dict = Field(default_factory=dict)  # {workflows: 3, personas: 2, ...}


class TemporalChange(BaseModel):
    """A single change that happened since the last session."""

    change_type: ChangeType
    summary: str  # one sentence
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    confidence_delta: float | None = None  # e.g. +0.15 for belief strengthened
    timestamp: datetime | None = None


class BriefingWhatChanged(BaseModel):
    """Temporal diff section — what happened since you were last here."""

    since_timestamp: datetime | None = None
    since_label: str = "your last session"  # "2 days ago", "your last session"
    changes: list[TemporalChange] = Field(default_factory=list)
    change_summary: str = ""  # Haiku-generated 1-sentence summary (optional)
    counts: dict = Field(default_factory=dict)  # {beliefs_changed: 3, signals: 2, ...}


class ActiveTension(BaseModel):
    """A tension between contradicting positions in the project."""

    tension_id: str
    summary: str  # one sentence describing the tension
    side_a: str  # position A
    side_b: str  # position B
    involved_entities: list[dict] = Field(default_factory=list)  # [{type, id, name}]
    confidence: float = 0.5  # how confident we are this is a real tension


class Hypothesis(BaseModel):
    """A testable belief that needs validation."""

    hypothesis_id: str  # memory node ID
    statement: str  # the belief text
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    evidence_for: int = 0
    evidence_against: int = 0
    test_suggestion: str | None = None  # Haiku-generated suggestion
    domain: str | None = None  # belief_domain


class ProjectHeartbeat(BaseModel):
    """Instant project health snapshot — no LLM needed."""

    completeness_pct: float = 0.0  # 0-100, structural field fill rate
    confirmation_pct: float = 0.0  # 0-100, % confirmed by consultant/client
    days_since_last_signal: int | None = None
    memory_depth: int = 0  # total memory nodes
    stale_entity_count: int = 0
    scope_alerts: list[str] = Field(default_factory=list)
    entity_counts: dict = Field(default_factory=dict)


class WhatYouShouldKnow(BaseModel):
    """Key insights the consultant should know — Sonnet-generated."""

    narrative: str = ""  # 1-2 sentences of what matters most right now
    bullets: list[str] = Field(default_factory=list)  # 2-4 key points


# =============================================================================
# Top-level briefing model
# =============================================================================


class IntelligenceBriefing(BaseModel):
    """Complete intelligence briefing — the main response model.

    Assembled from parallel deterministic + LLM computations.
    Cached in synthesized_memory_cache.briefing_sections.
    """

    # Narrative sections
    situation: BriefingSituation = Field(default_factory=BriefingSituation)
    what_changed: BriefingWhatChanged = Field(default_factory=BriefingWhatChanged)
    what_you_should_know: WhatYouShouldKnow = Field(default_factory=WhatYouShouldKnow)

    # Deterministic sections
    tensions: list[ActiveTension] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    heartbeat: ProjectHeartbeat = Field(default_factory=ProjectHeartbeat)

    # Actions (reuse existing v3 TerseAction)
    actions: list[TerseAction] = Field(default_factory=list)

    # Conversation starter (signal-informed)
    conversation_starter: ConversationStarter | None = None

    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    narrative_cached: bool = False  # True if Sonnet was skipped (cache hit)
    phase: ContextPhase = ContextPhase.EMPTY
