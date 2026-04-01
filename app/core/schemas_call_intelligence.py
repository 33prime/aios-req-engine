"""Schemas for call intelligence pipeline.

Recording metadata, transcription results, analysis outputs, and API models.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Type aliases
# ============================================================================

CallRecordingStatus = Literal[
    "pending",
    "bot_scheduled",
    "recording",
    "transcribing",
    "analyzing",
    "complete",
    "skipped",
    "failed",
]

CallSignalType = Literal[
    "pain_point",
    "goal",
    "budget_indicator",
    "timeline",
    "decision_criteria",
    "risk_factor",
]

NuggetType = Literal[
    "testimonial",
    "soundbite",
    "statistic",
    "use_case",
    "objection",
    "vision_statement",
    "pain_point",
]

ReactionType = Literal[
    "excited",
    "interested",
    "neutral",
    "confused",
    "resistant",
]

SentimentType = Literal["positive", "neutral", "negative"]


# ============================================================================
# Data models (internal pipeline)
# ============================================================================


class TranscriptSegment(BaseModel):
    """A single speaker turn in the transcript."""

    speaker: str = Field(..., description="Speaker identifier (e.g., 'Speaker 0')")
    text: str = Field(..., description="Spoken text for this segment")
    start: float = Field(0.0, description="Start time in seconds")
    end: float = Field(0.0, description="End time in seconds")
    confidence: float = Field(0.0, description="Transcription confidence 0-1")


class TranscriptResult(BaseModel):
    """Result from Deepgram transcription."""

    full_text: str = Field("", description="Full concatenated transcript")
    segments: list[TranscriptSegment] = Field(default_factory=list)
    speaker_map: dict[str, str] = Field(
        default_factory=dict, description="Speaker ID -> label mapping"
    )
    word_count: int = Field(0, description="Total word count")
    language: str = Field("en", description="Detected language")
    provider: str = Field("deepgram", description="Transcription provider")
    model: str = Field("nova-2", description="Transcription model")


class FeatureInsight(BaseModel):
    """A feature reaction extracted from call analysis."""

    feature_name: str
    reaction: ReactionType = "neutral"
    quote: str | None = None
    context: str | None = None
    timestamp_seconds: int | None = None
    is_aha_moment: bool = False


class CallSignalInsight(BaseModel):
    """An ICP/market signal extracted from call analysis."""

    signal_type: CallSignalType
    title: str
    description: str | None = None
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    quote: str | None = None


class ContentNugget(BaseModel):
    """A reusable content extract from the call."""

    nugget_type: NuggetType
    content: str
    speaker: str | None = None
    reuse_score: float = Field(0.5, ge=0.0, le=1.0)


class CompetitiveMention(BaseModel):
    """A competitor mentioned during the call."""

    competitor_name: str
    sentiment: SentimentType = "neutral"
    context: str | None = None
    quote: str | None = None
    feature_comparison: str | None = None


class ConsultantPerformance(BaseModel):
    """Consultant performance dimensions from call analysis."""

    question_quality: dict = Field(default_factory=dict)
    active_listening: dict = Field(default_factory=dict)
    discovery_depth: dict = Field(default_factory=dict)
    objection_handling: dict = Field(default_factory=dict)
    next_steps_clarity: dict = Field(default_factory=dict)
    consultant_talk_ratio: dict = Field(default_factory=dict)
    consultant_summary: str | None = None


class AnalysisResult(BaseModel):
    """Full result from Claude call analysis."""

    engagement_score: float | None = Field(None, ge=0.0, le=1.0)
    talk_ratio: dict[str, float] = Field(default_factory=dict)
    engagement_timeline: list[dict] = Field(default_factory=list)
    executive_summary: str | None = None
    feature_insights: list[FeatureInsight] = Field(default_factory=list)
    call_signals: list[CallSignalInsight] = Field(default_factory=list)
    content_nuggets: list[ContentNugget] = Field(default_factory=list)
    competitive_mentions: list[CompetitiveMention] = Field(default_factory=list)
    custom_dimensions: dict = Field(default_factory=dict)
    dimension_packs_used: list[str] = Field(default_factory=list)
    model: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0


# ============================================================================
# API models
# ============================================================================


class ScheduleRecordingRequest(BaseModel):
    """Request to schedule a recording bot for a meeting."""

    meeting_id: UUID
    project_id: UUID
    bot_name: str = Field("AIOS Recorder", max_length=100)


class AnalyzeRequest(BaseModel):
    """Request to trigger (re-)analysis of a recording."""

    dimension_packs: str | None = Field(
        None, description="Comma-separated pack names (default: use config)"
    )


class CreateSignalRequest(BaseModel):
    """Request to manually create an AIOS signal from a recording."""

    authority: str = Field("client", description="Signal authority level")


class RecordingResponse(BaseModel):
    """API response for a call recording."""

    id: UUID
    project_id: UUID
    meeting_id: UUID | None = None
    recall_bot_id: str | None = None
    meeting_bot_id: UUID | None = None
    title: str | None = None
    status: CallRecordingStatus = "pending"
    audio_url: str | None = None
    video_url: str | None = None
    recording_url: str | None = None
    duration_seconds: int | None = None
    signal_id: UUID | None = None
    error_message: str | None = None
    error_step: str | None = None
    created_at: str
    updated_at: str


class TranscriptResponse(BaseModel):
    """API response for a call transcript."""

    id: UUID
    recording_id: UUID
    full_text: str = ""
    segments: list[dict] = Field(default_factory=list)
    speaker_map: dict = Field(default_factory=dict)
    word_count: int = 0
    language: str = "en"
    provider: str = "deepgram"
    model: str = "nova-2"


class AnalysisResponse(BaseModel):
    """API response for call analysis."""

    id: UUID
    recording_id: UUID
    engagement_score: float | None = None
    talk_ratio: dict = Field(default_factory=dict)
    engagement_timeline: list[dict] = Field(default_factory=list)
    executive_summary: str | None = None
    custom_dimensions: dict = Field(default_factory=dict)
    dimension_packs_used: list[str] = Field(default_factory=list)
    model: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0


class CallDetails(BaseModel):
    """Full details for a call recording (aggregated response)."""

    recording: RecordingResponse
    transcript: TranscriptResponse | None = None
    analysis: AnalysisResponse | None = None
    feature_insights: list[dict] = Field(default_factory=list)
    call_signals: list[dict] = Field(default_factory=list)
    content_nuggets: list[dict] = Field(default_factory=list)
    competitive_mentions: list[dict] = Field(default_factory=list)
    consultant_performance: ConsultantPerformance | None = None
    strategy_brief: dict | None = None
