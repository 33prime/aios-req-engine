"""Pydantic models for the action engine.

Architecture:
  v2 (legacy): ActionSkeleton → UnifiedAction (still used by answer cascade)
  v3 (current): ProjectContextFrame — universal context engine powering actions + chat.

v3 produces terse, stage-aware actions with three gap types:
  - Structural gaps: deterministic graph walk (field is null)
  - Signal gaps: Haiku-reasoned domain artifacts (implied by workflow context)
  - Knowledge gaps: Haiku-reasoned insufficient context (what we don't know)
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ActionCategory(str, Enum):
    """What kind of action this is."""

    GAP = "gap"  # Structural hole in workflows/drivers/personas
    INTELLIGENCE = "intelligence"  # Similar company results, discovery data
    OPPORTUNITY = "opportunity"  # Cross-entity insight (conservative)


class GapDomain(str, Enum):
    """Which domain the gap lives in (walk order = priority order)."""

    WORKFLOW = "workflow"  # Step-level gaps (actor, pain, benefit, driver, time)
    DRIVER = "driver"  # Orphan pains, goals without features, KPIs without numbers
    PERSONA = "persona"  # Primary persona owns 0 workflows, unaddressed goals
    CROSS_REF = "cross_ref"  # Open questions linked to gaps, low-confidence beliefs


class QuestionTarget(str, Enum):
    """Who is most likely able to answer this question."""

    CONSULTANT = "consultant"  # Consultant can answer inline
    CLIENT = "client"  # Needs client stakeholder (flows to collab engine)
    EITHER = "either"  # Could go either way


class ContextPhase(str, Enum):
    """Four-tier project maturity phase for the context engine."""

    EMPTY = "empty"  # 0-3 entities, no workflows
    SEEDING = "seeding"  # 3-15 entities OR <2 workflows
    BUILDING = "building"  # 15+ entities, 2+ workflows
    REFINING = "refining"  # >70% completeness


class CTAType(str, Enum):
    """Call-to-action type for terse action cards."""

    INLINE_ANSWER = "inline_answer"  # Structural gap — show text input
    UPLOAD_DOC = "upload_doc"  # Signal gap — open file upload
    DISCUSS = "discuss"  # Knowledge/signal gap — switch to chat tab


# =============================================================================
# Layer 1: Skeleton (pure logic, no LLM)
# =============================================================================


class SkeletonRelationship(BaseModel):
    """A single relationship edge relevant to this skeleton."""

    entity_type: str  # workflow, vp_step, business_driver, persona, etc.
    entity_id: str
    entity_name: str
    relationship: str  # actor_of, targets, uses, derived_from


class ActionSkeleton(BaseModel):
    """Rich relationship context produced by the graph-walking engine.

    This is the input to Haiku — contains everything needed to generate
    a narrative without the LLM needing to query anything.
    """

    # Identity
    skeleton_id: str  # deterministic hash for caching
    category: ActionCategory
    gap_domain: GapDomain | None = None  # only for GAP category

    # What's missing
    gap_type: str  # e.g. "step_missing_actor", "driver_orphan_pain", "kpi_no_baseline"
    gap_description: str  # human-readable summary of the structural gap

    # Entity context — the specific entities involved
    primary_entity_type: str  # the entity with the gap
    primary_entity_id: str
    primary_entity_name: str

    # Relationship context — what connects to this gap
    related_entities: list[SkeletonRelationship] = Field(default_factory=list)

    # What we know
    known_contacts: list[str] = Field(default_factory=list)  # stakeholder names
    existing_evidence_count: int = 0  # how many signals reference this entity

    # Impact context
    downstream_entity_count: int = 0  # entities that depend on this
    gates_affected: list[str] = Field(default_factory=list)  # "canvas_ready", etc.

    # Scoring (deterministic)
    base_score: float = 0.0  # raw priority before phase multiplier
    phase_multiplier: float = 1.0
    temporal_modifier: float = 1.0  # boost for staleness, recency
    final_score: float = 0.0  # base × phase × temporal

    # Suggested question routing (engine's best guess, Haiku refines)
    suggested_question_target: QuestionTarget = QuestionTarget.CONSULTANT
    suggested_contact_name: str | None = None  # specific person if known


# =============================================================================
# Layer 2: Narrative (Haiku 4.5 output)
# =============================================================================


class ActionQuestion(BaseModel):
    """A question attached to an action — personal, minimal, non-technical."""

    question: str  # 1 sentence, as you'd text a colleague
    target: QuestionTarget  # who should answer
    suggested_contact: str | None = None  # "Sarah Chen" or "someone from Finance"
    unlocks: str  # what answering this enables: "Confirms 3 workflow steps + 2 KPIs"


class UnifiedAction(BaseModel):
    """A fully-rendered action ready for the frontend.

    Combines the deterministic skeleton with Haiku-generated narrative.
    """

    # Identity
    action_id: str  # matches skeleton_id
    category: ActionCategory
    gap_domain: GapDomain | None = None

    # Narrative (Haiku-generated)
    narrative: str  # 2-3 sentences, conversational, explains WHY
    unlocks: str  # 1 sentence: what resolving this enables downstream

    # Questions (Haiku-generated, 1 per action, max 2)
    questions: list[ActionQuestion] = Field(default_factory=list, max_length=2)

    # Scoring
    impact_score: float = Field(ge=0, le=100)
    urgency: str = "normal"  # low/normal/high/critical

    # Entity targeting
    primary_entity_type: str
    primary_entity_id: str
    primary_entity_name: str

    # Relationship hints for UI (hover highlights, navigation)
    related_entity_ids: list[str] = Field(default_factory=list)
    gates_affected: list[str] = Field(default_factory=list)

    # Metadata
    gap_type: str  # for frontend icon/color mapping
    known_contacts: list[str] = Field(default_factory=list)
    evidence_count: int = 0

    def to_legacy_dict(self) -> dict:
        """Convert to legacy NextAction shape for backward compat."""
        return {
            "action_type": self.gap_type,
            "title": self.narrative[:80] if self.narrative else "",
            "description": self.narrative,
            "impact_score": self.impact_score,
            "target_entity_type": self.primary_entity_type,
            "target_entity_id": self.primary_entity_id,
            "suggested_stakeholder_role": (
                self.known_contacts[0] if self.known_contacts else None
            ),
            "suggested_artifact": None,
            "category": self.category.value,
            "rationale": self.unlocks,
            "urgency": self.urgency,
        }


# =============================================================================
# Engine result
# =============================================================================


class ActionEngineResult(BaseModel):
    """Full result from the two-layer action engine."""

    # Rendered actions (show 3 to user, buffer 5 total)
    actions: list[UnifiedAction]
    skeleton_count: int = 0  # total skeletons before filtering to top 5

    # Open questions (surfaced alongside actions)
    open_questions: list[dict] = Field(default_factory=list)

    # Phase context
    phase: str = "discovery"
    phase_progress: float = 0.0

    # Cache metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    narrative_cached: bool = False  # true if Haiku was skipped (cache hit)
    state_snapshot_tokens: int = 0  # size of cached context block


# =============================================================================
# v3: ProjectContextFrame — universal context engine
# =============================================================================


class StructuralGap(BaseModel):
    """A deterministic gap from graph walking (field is null)."""

    gap_id: str  # deterministic hash
    gap_type: str  # step_no_actor, step_no_pain, step_no_time, etc.
    sentence: str  # ONE sentence describing the gap
    entity_type: str
    entity_id: str
    entity_name: str
    workflow_name: str | None = None  # parent workflow if applicable
    score: float = 0.0  # priority score (0-100)
    question_placeholder: str | None = None  # hint for inline input


class SignalGap(BaseModel):
    """A Haiku-reasoned domain artifact gap (implied by workflow context)."""

    gap_id: str
    sentence: str  # ONE sentence: "Get the assessment rubric from the clinical team"
    suggested_artifact: str  # what to upload: "question bank", "rubric", "flowchart"
    reasoning: str  # why this is needed (terse)
    related_workflow: str | None = None  # which workflow implies this
    cta_type: CTAType = CTAType.UPLOAD_DOC  # upload or discuss


class KnowledgeGap(BaseModel):
    """A Haiku-reasoned insufficient context gap (what we don't know)."""

    gap_id: str
    sentence: str  # ONE sentence: "What regulations govern this certification?"
    reasoning: str  # why we need this (terse)
    related_context: str | None = None  # what triggered this gap


class TerseAction(BaseModel):
    """A single terse action card for the frontend.

    One sentence + one CTA. No paragraphs. No narrative.
    """

    action_id: str
    sentence: str  # ONE sentence
    cta_type: CTAType
    cta_label: str  # "Answer", "Upload document", "Discuss in chat"

    # Source
    gap_source: str  # "structural", "signal", "knowledge"
    gap_type: str  # for icon mapping

    # Entity targeting
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None

    # For inline answers
    question_placeholder: str | None = None

    # Scoring
    priority: int = 0  # 1-based rank
    impact_score: float = 0.0


class ProjectContextFrame(BaseModel):
    """Universal context output powering actions + chat.

    Replaces ActionEngineResult for the v3 action system.
    Computed on: data change, signal processed, periodic refresh.
    """

    # Phase
    phase: ContextPhase = ContextPhase.EMPTY
    phase_progress: float = 0.0  # 0-1

    # Three gap types
    structural_gaps: list[StructuralGap] = Field(default_factory=list)
    signal_gaps: list[SignalGap] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)

    # Terse actions (merged + ranked from all 3 gap types)
    actions: list[TerseAction] = Field(default_factory=list)

    # Context for chat injection
    state_snapshot: str = ""  # ~500 tokens, project summary
    workflow_context: str = ""  # ~300 tokens, workflow names + step summaries

    # Memory
    memory_hints: list[str] = Field(default_factory=list)  # low-confidence beliefs

    # Stats
    entity_counts: dict = Field(default_factory=dict)
    entity_inventory: dict[str, list[dict]] = Field(default_factory=dict)  # {type: [{id, name, status, is_stale}]}
    total_gap_count: int = 0
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    # Open questions (surfaced alongside actions)
    open_questions: list[dict] = Field(default_factory=list)


# =============================================================================
# Answer cascade models
# =============================================================================


class AnswerInput(BaseModel):
    """Consultant's answer to an action question."""

    action_id: str
    question_index: int = 0  # which question was answered (usually 0)
    answer_text: str
    answered_by: str | None = None  # user_id or stakeholder name


class ExtractedEntity(BaseModel):
    """A single entity extraction from an answer (Haiku parse output)."""

    operation: str  # "create", "update", "link"
    entity_type: str  # business_driver, vp_step, persona, workflow, etc.
    entity_id: str | None = None  # for updates/links
    data: dict = Field(default_factory=dict)  # fields to set/merge


class AnswerParseResult(BaseModel):
    """Result of parsing an answer into structured entity operations."""

    extractions: list[ExtractedEntity]
    entities_affected: int = 0
    cascade_triggered: bool = False
    summary: str = ""  # human-readable: "Created 1 KPI, updated 2 workflow steps"
