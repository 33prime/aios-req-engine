"""Pydantic schemas for evidence references."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvidenceRef(BaseModel):
    """Reference to evidence from a signal chunk."""

    chunk_id: UUID = Field(..., description="Chunk UUID from which evidence was extracted")
    excerpt: str = Field(..., max_length=280, description="Verbatim excerpt from chunk (max 280)")
    rationale: str = Field(..., description="Why this excerpt supports the change")

    def __init__(self, **data):
        super().__init__(**data)
        # Validate excerpt length
        if len(self.excerpt.strip()) == 0:
            raise ValueError("excerpt must be non-empty")
        if len(self.excerpt) > 280:
            raise ValueError("excerpt must be 280 characters or less")


# ============================================================================
# Extended Evidence Tracking for Red Team, A-Team, and Research
# ============================================================================


class SourceType(str, Enum):
    """Types of evidence sources"""
    SIGNAL = "signal"
    RESEARCH = "research"
    COMPETITIVE = "competitive"
    PERSONA = "persona"
    FEATURE = "feature"
    VP_STEP = "vp_step"
    USER_INPUT = "user_input"


class Evidence(BaseModel):
    """
    A piece of evidence supporting a finding or recommendation.

    Links back to the source (signal, research, etc.) with context
    about why this evidence is relevant.
    """
    source_type: SourceType
    source_id: str
    source_name: str = Field(..., description="Human-readable source name")

    excerpt: str = Field(..., description="Relevant quote or excerpt from source")
    relevance: str = Field(..., description="Why this evidence matters for this finding")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    url: Optional[str] = Field(None, description="External URL if applicable")
    view_url: Optional[str] = Field(None, description="Internal frontend URL to view source")

    # Optional metadata
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)


class ResearchTrigger(str, Enum):
    """Reasons to trigger research"""
    NEW_DOMAIN = "new_domain"
    MISSING_CONTEXT = "missing_context"
    COMPETITIVE_GAP = "competitive_gap"
    USER_REQUESTED = "user_requested"
    STALE_DATA = "stale_data"
    RED_TEAM_GAP = "red_team_gap"


class ResearchRecommendation(BaseModel):
    """
    Recommendation to run research based on signal analysis.
    """
    should_run: bool
    triggers: List[dict] = Field(
        default_factory=list,
        description="List of {trigger, description, priority} dicts"
    )
    suggested_queries: List[str] = Field(default_factory=list)
    estimated_duration: Optional[str] = Field(None, description="e.g., '2-3 minutes'")

    # Context for decision
    new_domains: List[str] = Field(default_factory=list)
    missing_topics: List[str] = Field(default_factory=list)
    stale_topics: List[str] = Field(default_factory=list)


class Alternative(BaseModel):
    """
    An alternative solution considered by A-Team.
    """
    option: str
    description: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[Evidence] = Field(default_factory=list)

    @field_validator('pros', 'cons', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Convert string to list if LLM returns a string instead of list."""
        if v is None:
            return []
        if isinstance(v, str):
            # Split by common delimiters or wrap as single item
            if ';' in v:
                return [item.strip() for item in v.split(';') if item.strip()]
            elif '\n' in v:
                return [item.strip() for item in v.split('\n') if item.strip()]
            else:
                return [v] if v.strip() else []
        return v
