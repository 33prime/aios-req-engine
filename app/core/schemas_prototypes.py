"""Pydantic schemas for the prototype refinement subsystem."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# === Design token schemas ===


class DesignTokens(BaseModel):
    """Design tokens that feed into the v0 prompt."""

    primary_color: str = Field(..., description="Primary brand color hex")
    secondary_color: str = Field(..., description="Secondary color hex")
    accent_color: str = Field(..., description="Accent color hex")
    font_heading: str = Field("Inter", description="Heading font family")
    font_body: str = Field("Inter", description="Body font family")
    spacing: str = Field("balanced", description="Spacing: compact, balanced, generous")
    corners: str = Field(
        "slightly-rounded", description="Corner style: sharp, slightly-rounded, rounded, pill"
    )
    style_direction: str = Field("", description="Overall style direction description")
    logo_url: str | None = Field(None, description="Logo URL to include in header")


class GenericStyle(BaseModel):
    """A generic design style option."""

    id: str = Field(..., description="Style identifier")
    label: str = Field(..., description="Display label")
    description: str = Field(..., description="Style description")
    preview_colors: list[str] = Field(default_factory=list, description="Preview color swatches")
    tokens: DesignTokens = Field(..., description="Design tokens for this style")


class DesignSelection(BaseModel):
    """What the user selected for design direction."""

    option_id: str = Field(..., description="Selected option ID")
    tokens: DesignTokens = Field(..., description="Design tokens")
    source: str = Field("", description="Source of selection: brand, inspiration, generic")


class BrandData(BaseModel):
    """Brand data extracted from company website."""

    logo_url: str | None = Field(None, description="Logo URL")
    brand_colors: list[str] = Field(default_factory=list, description="Brand colors")
    typography: dict[str, str] | None = Field(
        None, description="Typography: {heading_font, body_font}"
    )
    design_characteristics: dict[str, str] | None = Field(
        None, description="Design characteristics: {overall_feel, spacing, corners, visual_weight}"
    )


class DesignInspiration(BaseModel):
    """A design inspiration from competitor refs or signals."""

    id: str = Field(..., description="Reference ID")
    name: str = Field(..., description="Reference name (e.g., 'Stripe')")
    url: str | None = Field(None, description="Reference URL")
    description: str = Field("", description="Why this is an inspiration")
    source: str = Field("", description="Where this came from: competitor_ref, signal")


class DesignProfileResponse(BaseModel):
    """Response for the design profile endpoint."""

    brand_available: bool = Field(False, description="Whether brand data was extracted")
    brand: BrandData | None = Field(None, description="Extracted brand data")
    design_inspirations: list[DesignInspiration] = Field(
        default_factory=list, description="Design inspirations from competitors/signals"
    )
    suggested_style: str | None = Field(None, description="AI-suggested style from signals")
    style_source: str | None = Field(None, description="Attribution for suggested style")
    generic_styles: list[GenericStyle] = Field(default_factory=list, description="Generic style options")


# === Generic style definitions ===

GENERIC_DESIGN_STYLES: list[GenericStyle] = [
    GenericStyle(
        id="minimal_clean",
        label="Minimal & Clean",
        description="Understated elegance with generous whitespace and sharp typography",
        preview_colors=["#000000", "#f5f5f5", "#e5e5e5"],
        tokens=DesignTokens(
            primary_color="#000000",
            secondary_color="#f5f5f5",
            accent_color="#e5e5e5",
            font_heading="Inter",
            font_body="Inter",
            spacing="generous",
            corners="sharp",
            style_direction="Minimal and clean: high contrast black/white, generous whitespace, "
            "sharp corners, thin borders, restrained use of color",
        ),
    ),
    GenericStyle(
        id="bold_expressive",
        label="Bold & Expressive",
        description="Strong typography and high contrast with vibrant accent colors",
        preview_colors=["#1a1a2e", "#e94560", "#f5f5f5"],
        tokens=DesignTokens(
            primary_color="#1a1a2e",
            secondary_color="#f5f5f5",
            accent_color="#e94560",
            font_heading="Sora",
            font_body="Inter",
            spacing="balanced",
            corners="slightly-rounded",
            style_direction="Bold and expressive: dark primary with vibrant red accent, "
            "strong typography hierarchy, high visual contrast, confident layout",
        ),
    ),
    GenericStyle(
        id="warm_organic",
        label="Warm & Organic",
        description="Earthy tones with rounded shapes and a friendly, approachable feel",
        preview_colors=["#2d3436", "#e17055", "#ffeaa7"],
        tokens=DesignTokens(
            primary_color="#2d3436",
            secondary_color="#ffeaa7",
            accent_color="#e17055",
            font_heading="DM Serif Display",
            font_body="DM Sans",
            spacing="balanced",
            corners="rounded",
            style_direction="Warm and organic: earthy tones, rounded corners, warm accent colors, "
            "friendly serif headings, approachable and human feel",
        ),
    ),
    GenericStyle(
        id="luxury_refined",
        label="Luxury & Refined",
        description="Elegant serif typography with gold accents and refined dark palette",
        preview_colors=["#0c0c0c", "#c9a227", "#f8f8f8"],
        tokens=DesignTokens(
            primary_color="#0c0c0c",
            secondary_color="#f8f8f8",
            accent_color="#c9a227",
            font_heading="Playfair Display",
            font_body="Lato",
            spacing="generous",
            corners="sharp",
            style_direction="Luxury and refined: near-black primary, gold accents, elegant serif headings, "
            "generous spacing, minimal ornamentation, premium feel",
        ),
    ),
    GenericStyle(
        id="tech_modern",
        label="Tech & Modern",
        description="Clean blue palette with crisp geometry and modern sans-serif type",
        preview_colors=["#0f172a", "#3b82f6", "#f1f5f9"],
        tokens=DesignTokens(
            primary_color="#0f172a",
            secondary_color="#f1f5f9",
            accent_color="#3b82f6",
            font_heading="Plus Jakarta Sans",
            font_body="Inter",
            spacing="balanced",
            corners="slightly-rounded",
            style_direction="Tech and modern: dark navy primary, blue accent, clean geometry, "
            "crisp borders, modern sans-serif type, dashboard-ready layout",
        ),
    ),
]


# === Request schemas ===


class GeneratePrototypeRequest(BaseModel):
    """Request body for generating a prototype from discovery data."""

    project_id: UUID = Field(..., description="Project UUID")
    design_selection: DesignSelection | None = Field(None, description="Design selection from modal")


class IngestPrototypeRequest(BaseModel):
    """Request body for ingesting an existing prototype repo."""

    project_id: UUID = Field(..., description="Project UUID")
    repo_url: str = Field(..., description="Git repo URL for the prototype")
    deploy_url: str | None = Field(None, description="Live deployment URL")


class RetryPrototypeRequest(BaseModel):
    """Request body for retrying prototype generation with a refined prompt."""

    prototype_id: UUID = Field(..., description="Prototype UUID")


class CreateSessionRequest(BaseModel):
    """Request body for creating a new review session."""

    prototype_id: UUID = Field(..., description="Prototype UUID")


class SubmitFeedbackRequest(BaseModel):
    """Request body for submitting feedback during a session."""

    content: str = Field(..., min_length=1, description="Feedback text")
    feedback_type: Literal[
        "observation", "requirement", "concern", "question", "answer"
    ] = Field("observation", description="Type of feedback")
    context: "SessionContext | None" = Field(None, description="Current session context snapshot")
    feature_id: str | None = Field(None, description="Feature UUID if feedback targets a specific feature")
    page_path: str | None = Field(None, description="Current page path in prototype")
    component_name: str | None = Field(None, description="Component name if known")
    answers_question_id: str | None = Field(None, description="Question UUID if this answers a question")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Feedback priority")


class SessionChatRequest(BaseModel):
    """Request body for context-aware AI chat in a session."""

    message: str = Field(..., min_length=1, description="Chat message")
    context: "SessionContext | None" = Field(None, description="Current session context snapshot")


# === Shared context models ===


class PageVisit(BaseModel):
    """A page visited during a session."""

    path: str = Field(..., description="Route path")
    timestamp: str = Field(..., description="ISO timestamp of visit")
    features_visible: list[str] = Field(default_factory=list, description="Feature IDs visible on this page")


class SessionContext(BaseModel):
    """Snapshot of current session state, sent with every feedback/chat message."""

    current_page: str = Field("", description="Current page path")
    current_route: str = Field("", description="Current route")
    active_feature_id: str | None = Field(None, description="Currently active feature ID")
    active_feature_name: str | None = Field(None, description="Currently active feature name")
    active_component: str | None = Field(None, description="Currently active component name")
    visible_features: list[str] = Field(default_factory=list, description="Feature IDs visible on current page")
    page_history: list[PageVisit] = Field(default_factory=list, description="Pages visited in this session")
    features_reviewed: list[str] = Field(default_factory=list, description="Feature IDs that have been reviewed")


# === Response schemas ===


class PromptGap(BaseModel):
    """A gap found during prompt audit."""

    dimension: str = Field(..., description="Which dimension has the gap")
    description: str = Field(..., description="What's missing")
    severity: Literal["high", "medium", "low"] = Field("medium", description="Gap severity")
    feature_ids: list[str] = Field(default_factory=list, description="Affected feature IDs")


class PromptAuditResult(BaseModel):
    """Results from auditing a v0 output against the original prompt."""

    feature_coverage_score: float = Field(0, description="Features requested vs found (0-1)")
    structure_score: float = Field(0, description="HANDOFF.md, folders, JSDoc (0-1)")
    mock_data_score: float = Field(0, description="Realistic data matching personas (0-1)")
    flow_score: float = Field(0, description="User flows navigable (0-1)")
    feature_id_score: float = Field(0, description="Elements with data-feature-id (0-1)")
    overall_score: float = Field(0, description="Weighted average (0-1)")
    gaps: list[PromptGap] = Field(default_factory=list, description="Specific gaps found")
    recommendations: list[str] = Field(default_factory=list, description="Improvement recommendations")


class PrototypeResponse(BaseModel):
    """Response schema for a prototype."""

    id: UUID = Field(..., description="Prototype UUID")
    project_id: UUID = Field(..., description="Project UUID")
    repo_url: str | None = Field(None, description="Git repo URL")
    deploy_url: str | None = Field(None, description="Deployment URL")
    status: Literal[
        "pending", "generating", "ingested", "analyzed", "active", "archived"
    ] = Field(..., description="Prototype status")
    prompt_audit: PromptAuditResult | None = Field(None, description="Audit results")
    prompt_version: int = Field(1, description="Prompt version number")
    session_count: int = Field(0, description="Number of review sessions")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class PersonaRef(BaseModel):
    """Reference to a persona that uses a feature."""

    persona_id: str = Field(..., description="Persona UUID")
    persona_name: str = Field(..., description="Persona display name")
    role: str = Field("primary", description="How this persona relates to the feature")


class Dependency(BaseModel):
    """A dependency between features."""

    feature_id: str = Field(..., description="Dependent feature UUID")
    feature_name: str = Field(..., description="Dependent feature name")
    direction: Literal["upstream", "downstream"] = Field(..., description="Dependency direction")
    relationship: str = Field("", description="Nature of the dependency")


class UploadSuggestion(BaseModel):
    """A suggested document upload to fill a knowledge gap."""

    title: str = Field(..., description="What to upload")
    description: str = Field(..., description="Why it would help")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Urgency")


class BusinessRule(BaseModel):
    """A business rule associated with a feature."""

    rule: str = Field(..., description="The business rule")
    source: Literal["aios", "inferred", "confirmed"] = Field("inferred", description="Where this rule came from")
    confidence: float = Field(0.5, description="Confidence in this rule (0-1)")


class OverlayQuestion(BaseModel):
    """A question about a feature from the overlay."""

    id: str = Field(..., description="Question UUID")
    question: str = Field(..., description="The question text")
    category: str = Field("", description="Question category")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Priority level")
    answer: str | None = Field(None, description="Answer if provided")
    answered_in_session: int | None = Field(None, description="Session number where answered")


class OverlayContent(BaseModel):
    """Full overlay card content for a feature."""

    feature_id: str | None = Field(None, description="Matched AIOS feature UUID")
    feature_name: str = Field(..., description="Feature display name")
    status: Literal["understood", "partial", "unknown"] = Field("unknown", description="Understanding status")
    confidence: float = Field(0, description="Confidence score (0-1)")
    gaps_count: int = Field(0, description="Number of remaining gaps")
    triggers: list[str] = Field(default_factory=list, description="What triggers this feature")
    actions: list[str] = Field(default_factory=list, description="What actions the feature performs")
    data_requirements: list[str] = Field(default_factory=list, description="Data needed by this feature")
    personas: list[PersonaRef] = Field(default_factory=list, description="Personas that use this feature")
    flow_position: dict[str, Any] | None = Field(None, description="Position in the value path")
    dependencies: list[Dependency] = Field(default_factory=list, description="Feature dependencies")
    questions: list[OverlayQuestion] = Field(default_factory=list, description="Outstanding questions")
    business_rules: list[BusinessRule] = Field(default_factory=list, description="Business rules")
    implementation_notes: str = Field("", description="Implementation notes from analysis")
    upload_suggestions: list[UploadSuggestion] = Field(default_factory=list, description="Suggested uploads")


class FeatureOverlayResponse(BaseModel):
    """Response schema for a feature overlay."""

    id: UUID = Field(..., description="Overlay UUID")
    prototype_id: UUID = Field(..., description="Prototype UUID")
    feature_id: str | None = Field(None, description="Matched AIOS feature UUID")
    code_file_path: str | None = Field(None, description="Code file path in prototype")
    component_name: str | None = Field(None, description="Component name")
    handoff_feature_name: str | None = Field(None, description="Name from HANDOFF.md")
    status: str = Field("unknown", description="Analysis status")
    confidence: float = Field(0, description="Confidence score")
    gaps_count: int = Field(0, description="Number of gaps")
    overlay_content: OverlayContent | None = Field(None, description="Full overlay card content")
    created_at: str = Field(..., description="Creation timestamp")


class SessionResponse(BaseModel):
    """Response schema for a review session."""

    id: UUID = Field(..., description="Session UUID")
    prototype_id: UUID = Field(..., description="Prototype UUID")
    session_number: int = Field(..., description="Session number (1-indexed)")
    status: str = Field(..., description="Session status")
    readiness_before: float | None = Field(None, description="Readiness score at session start")
    readiness_after: float | None = Field(None, description="Readiness score at session end")
    synthesis: dict[str, Any] | None = Field(None, description="Feedback synthesis result")
    code_update_plan: dict[str, Any] | None = Field(None, description="Code update plan")
    code_update_result: dict[str, Any] | None = Field(None, description="Code update result")
    started_at: str | None = Field(None, description="Session start time")
    completed_at: str | None = Field(None, description="Session completion time")
    created_at: str = Field(..., description="Creation timestamp")


class FeedbackResponse(BaseModel):
    """Response schema for a piece of feedback."""

    id: UUID = Field(..., description="Feedback UUID")
    session_id: UUID = Field(..., description="Session UUID")
    source: Literal["consultant", "client"] = Field(..., description="Who submitted")
    feature_id: str | None = Field(None, description="Target feature UUID")
    page_path: str | None = Field(None, description="Page path")
    component_name: str | None = Field(None, description="Component name")
    feedback_type: str | None = Field(None, description="Feedback type")
    content: str = Field(..., description="Feedback content")
    context: SessionContext | None = Field(None, description="Session context snapshot")
    priority: str = Field("medium", description="Priority")
    created_at: str = Field(..., description="Creation timestamp")


class ChatResponse(BaseModel):
    """Response from context-aware session chat."""

    response: str = Field(..., description="AI response text")
    extracted_feedback: list[dict[str, Any]] = Field(
        default_factory=list, description="Structured feedback extracted from conversation"
    )


# === Chain output schemas ===


class V0PromptOutput(BaseModel):
    """Output from the v0 prompt generator chain."""

    prompt: str = Field(..., description="The complete v0 prompt")
    features_included: list[str] = Field(default_factory=list, description="Feature IDs included in prompt")
    flows_included: list[str] = Field(default_factory=list, description="VP step labels included")


class FeatureAnalysis(BaseModel):
    """Analysis of a single feature's code vs AIOS metadata."""

    triggers: list[str] = Field(default_factory=list, description="What triggers this feature")
    actions: list[str] = Field(default_factory=list, description="What actions the feature performs")
    data_requirements: list[str] = Field(default_factory=list, description="Data needed")
    business_rules: list[dict[str, Any]] = Field(
        default_factory=list, description="Business rules: [{rule, source, confidence}]"
    )
    integration_points: list[str] = Field(default_factory=list, description="Integration points found")
    implementation_status: Literal["functional", "partial", "placeholder"] = Field(
        "placeholder", description="How complete the implementation is"
    )
    confidence: float = Field(0, description="Overall confidence (0-1)")
    notes: str = Field("", description="Free-form implementation notes")


class GeneratedQuestion(BaseModel):
    """A question generated about a feature."""

    question: str = Field(..., description="The question text")
    category: Literal[
        "business_rules", "edge_cases", "permissions", "integration", "data_handling"
    ] = Field("business_rules", description="Question category")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Priority")
    why_important: str = Field("", description="Why this question matters")


class FeatureSynthesis(BaseModel):
    """Synthesis of feedback for a single feature."""

    feature_id: str = Field(..., description="Feature UUID")
    confirmed_requirements: list[str] = Field(default_factory=list, description="Requirements confirmed")
    new_requirements: list[str] = Field(default_factory=list, description="New requirements discovered")
    contradictions: list[dict[str, Any]] = Field(
        default_factory=list, description="Contradictions found"
    )
    questions_resolved: list[dict[str, Any]] = Field(
        default_factory=list, description="Questions answered"
    )
    code_changes: list[dict[str, Any]] = Field(
        default_factory=list, description="Code changes needed"
    )
    recommended_status: str = Field("ai_generated", description="Updated confirmation status")


class FeedbackSynthesis(BaseModel):
    """Complete feedback synthesis for a session."""

    by_feature: dict[str, FeatureSynthesis] = Field(
        default_factory=dict, description="Per-feature synthesis"
    )
    new_features_discovered: list[dict[str, Any]] = Field(
        default_factory=list, description="New features found in feedback"
    )
    high_priority_changes: list[dict[str, Any]] = Field(
        default_factory=list, description="High-priority changes"
    )
    session_summary: str = Field("", description="Human-readable session summary")


class UpdateTask(BaseModel):
    """A single code update task."""

    file_path: str = Field(..., description="File to modify")
    change_description: str = Field(..., description="What to change")
    reason: str = Field(..., description="Why (links to feedback)")
    feature_id: str = Field("", description="Related feature UUID")
    risk: Literal["low", "medium", "high"] = Field("low", description="Risk level")
    depends_on: list[str] = Field(default_factory=list, description="File paths that must change first")


class UpdatePlan(BaseModel):
    """Plan for updating prototype code after a session."""

    tasks: list[UpdateTask] = Field(default_factory=list, description="Ordered tasks")
    execution_order: list[int] = Field(default_factory=list, description="Task execution order indices")
    estimated_files_changed: int = Field(0, description="Number of files to change")
    risk_assessment: str = Field("", description="Overall risk assessment")
