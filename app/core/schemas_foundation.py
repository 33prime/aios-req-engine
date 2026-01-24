"""Pydantic schemas for DI Agent Foundation system.

Foundation elements represent the "gates" that determine project readiness
for building prototypes vs final products. These models map to the JSONB
columns in the project_foundation table.
"""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Supporting Models
# =============================================================================


class KPI(BaseModel):
    """A measurable success metric for business case."""

    metric: str = Field(..., description="The metric name (e.g., 'Donor retention rate')")
    current_state: str = Field(..., description="Current state (e.g., '~45%')")
    target_state: str = Field(..., description="Target state (e.g., '60%+')")
    measurement_method: str = Field(..., description="How this will be measured")
    timeframe: str = Field(..., description="When to measure (e.g., '6 months')")


# =============================================================================
# Phase 1: Prototype Gates
# =============================================================================


class CorePain(BaseModel):
    """THE core pain - singular root problem, not symptoms.

    This is the foundation of everything. Without clear core pain,
    the prototype will solve the wrong problem.
    """

    statement: str = Field(
        ...,
        min_length=20,
        description="THE problem statement (singular, not a list)",
    )
    trigger: str = Field(..., description="Why now? What made them reach out?")
    stakes: str = Field(..., description="What happens if this remains unsolved?")
    who_feels_it: str = Field(..., description="Who experiences this pain most?")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in this assessment (0.0-1.0)"
    )
    confirmed_by: Optional[Literal["client", "consultant"]] = Field(
        None, description="Who confirmed this pain"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Signal IDs or quotes that support this pain",
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if statement is substantial and confidence >= 0.6
        """
        return (
            self.statement is not None
            and len(self.statement) > 20
            and self.confidence >= 0.6
        )

    @field_validator("statement")
    @classmethod
    def statement_not_empty(cls, v: str) -> str:
        """Ensure statement is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Core pain statement cannot be empty")
        return v.strip()


class PrimaryPersona(BaseModel):
    """The primary persona - who we're building for FIRST.

    A prototype must speak to SOMEONE specific. Generic prototypes
    feel like templates and don't create "holy shit" moments.
    """

    name: str = Field(..., description="Role name (e.g., 'Development Director')")
    role: str = Field(..., description="What they do")
    goal: str = Field(..., description="What they're trying to achieve")
    pain_connection: str = Field(
        ..., description="How the core pain affects them specifically"
    )
    context: str = Field(..., description="Their daily reality with this problem")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0.0-1.0)")
    confirmed_by: Optional[Literal["client", "consultant"]] = Field(
        None, description="Who confirmed this persona"
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if name and pain_connection exist and confidence >= 0.6
        """
        return (
            self.name is not None
            and self.pain_connection is not None
            and self.confidence >= 0.6
        )


class WowMoment(BaseModel):
    """The wow moment - peak where core pain dissolves.

    This is the emotional climax of the Value Path. The moment where
    the client sees their pain solved and says "you get me."

    Levels:
    - Level 1: Core pain solved (required)
    - Level 2: Adjacent pains addressed (better)
    - Level 3: Unstated needs met (holy shit)
    """

    description: str = Field(..., description="The peak moment description")
    core_pain_inversion: str = Field(
        ..., description="How this is the opposite of the core pain"
    )
    emotional_impact: str = Field(
        ..., description="How they'll feel at this moment"
    )
    visual_concept: str = Field(
        ..., description="What they'll SEE in the prototype"
    )
    level_1: str = Field(..., description="Core pain solved (required)")
    level_2: Optional[str] = Field(
        None, description="Adjacent pains addressed (optional but better)"
    )
    level_3: Optional[str] = Field(
        None, description="Unstated needs met (optional, 'holy shit' factor)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0.0-1.0)")

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if description and core_pain_inversion exist and confidence >= 0.5
        """
        return (
            self.description is not None
            and self.core_pain_inversion is not None
            and self.confidence >= 0.5  # Can be hypothesis, refined later
        )


class DesignPreferences(BaseModel):
    """Visual and style preferences (optional gate).

    This is optional but helps the prototype feel more "right"
    visually and reduces iteration cycles.
    """

    visual_style: Optional[str] = Field(
        None, description="Style preference (e.g., 'clean/minimal', 'playful', 'enterprise')"
    )
    references: list[str] = Field(
        default_factory=list, description="Products/designs they love"
    )
    anti_references: list[str] = Field(
        default_factory=list, description="Products/designs they've hated"
    )
    specific_requirements: list[str] = Field(
        default_factory=list,
        description="Specific requirements (e.g., 'WCAG AA', 'Mobile first')",
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if visual_style is set OR references exist
        """
        return self.visual_style is not None or len(self.references) > 0


# =============================================================================
# Phase 2: Build Gates
# =============================================================================


class BusinessCase(BaseModel):
    """Why this investment matters - ROI and value justification.

    Often unlocked AFTER prototype when client sees value and can
    articulate "Now that I see it, here's what it's worth."
    """

    value_to_business: str = Field(
        ..., description="How solving this helps the organization"
    )
    roi_framing: str = Field(
        ..., description="Value in dollars, time saved, or risk reduced"
    )
    success_kpis: list[KPI] = Field(
        default_factory=list, description="Measurable outcomes"
    )
    why_priority: str = Field(
        ..., description="Why invest in this vs other things"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0.0-1.0)")
    confirmed_by: Optional[Literal["client", "consultant"]] = Field(
        None, description="Who confirmed this business case"
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if value_to_business exists, at least 1 KPI, and confidence >= 0.7
        """
        return (
            self.value_to_business is not None
            and len(self.success_kpis) >= 1
            and self.confidence >= 0.7
        )


class BudgetConstraints(BaseModel):
    """Budget, timeline, and constraint reality check.

    Often unlocked by trust from prototype. Money conversations
    are easier when client sees you understand their problem.
    """

    budget_range: str = Field(
        ..., description="Budget range (e.g., '$200-500/month', '$5K-10K one-time')"
    )
    budget_flexibility: Literal["firm", "flexible", "unknown"] = Field(
        ..., description="How flexible is the budget"
    )
    timeline: str = Field(..., description="When they need it")
    hard_deadline: Optional[str] = Field(None, description="Immovable date if exists")
    deadline_driver: Optional[str] = Field(
        None, description="What's driving the deadline"
    )
    technical_constraints: list[str] = Field(
        default_factory=list,
        description="Technical limits (e.g., 'Must integrate with Salesforce')",
    )
    organizational_constraints: list[str] = Field(
        default_factory=list,
        description="Org limits (e.g., 'Board approval required', 'Low change tolerance')",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0.0-1.0)")
    confirmed_by: Optional[Literal["client", "consultant"]] = Field(
        None, description="Who confirmed these constraints"
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if budget_range and timeline exist and confidence >= 0.7
        """
        return (
            self.budget_range is not None
            and self.timeline is not None
            and self.confidence >= 0.7
        )


class ConfirmedScope(BaseModel):
    """V1 vs V2 agreement - what's in and what's out.

    Often unlocked by prototype making scope tangible and discussable.
    The prototype helps client see what V1 really means.
    """

    v1_features: list[str] = Field(
        default_factory=list, description="Feature IDs included in V1"
    )
    v2_features: list[str] = Field(
        default_factory=list, description="Feature IDs deferred to V2"
    )
    v1_agreed: bool = Field(False, description="Client agreed to V1 scope")
    specs_signed_off: bool = Field(False, description="Specifications approved")
    confirmed_by: Optional[Literal["client", "consultant"]] = Field(
        None, description="Who confirmed this scope"
    )

    def is_satisfied(self) -> bool:
        """Check if this gate is satisfied.

        Returns:
            True if v1_agreed, confirmed by client, and has v1_features
        """
        return (
            self.v1_agreed
            and self.confirmed_by == "client"
            and len(self.v1_features) > 0
        )


# =============================================================================
# Complete Foundation
# =============================================================================


class ProjectFoundation(BaseModel):
    """Complete project foundation - all gate data.

    This model represents the full project_foundation table row.
    """

    id: UUID = Field(..., description="Foundation record UUID")
    project_id: UUID = Field(..., description="Project UUID")

    # Phase 1: Prototype Gates
    core_pain: Optional[CorePain] = Field(None, description="THE core pain")
    primary_persona: Optional[PrimaryPersona] = Field(
        None, description="Primary persona"
    )
    wow_moment: Optional[WowMoment] = Field(None, description="Wow moment hypothesis")
    design_preferences: Optional[DesignPreferences] = Field(
        None, description="Design preferences"
    )

    # Phase 2: Build Gates
    business_case: Optional[BusinessCase] = Field(None, description="Business case")
    budget_constraints: Optional[BudgetConstraints] = Field(
        None, description="Budget and constraints"
    )
    confirmed_scope: Optional[ConfirmedScope] = Field(
        None, description="Confirmed scope"
    )

    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class FoundationUpdateRequest(BaseModel):
    """Request to update foundation elements.

    Only include fields you want to update. Null fields are ignored.
    """

    core_pain: Optional[CorePain] = None
    primary_persona: Optional[PrimaryPersona] = None
    wow_moment: Optional[WowMoment] = None
    design_preferences: Optional[DesignPreferences] = None
    business_case: Optional[BusinessCase] = None
    budget_constraints: Optional[BudgetConstraints] = None
    confirmed_scope: Optional[ConfirmedScope] = None
