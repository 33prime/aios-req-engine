"""Pydantic schemas for Phase 1 fact extraction."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# =======================
# Core extraction models
# =======================


class EvidenceRef(BaseModel):
    """Reference to evidence from a signal chunk."""

    chunk_id: UUID = Field(..., description="Chunk UUID from which evidence was extracted")
    excerpt: str = Field(..., max_length=2000, description="Verbatim excerpt from chunk (max 2000)")
    rationale: str = Field(..., max_length=500, description="Why this excerpt supports the fact")


class FactItem(BaseModel):
    """A single extracted fact with provenance."""

    fact_type: str = Field(
        ...,
        description="Category of the fact (e.g., feature, constraint, persona, kpi, process, organizational_goal, etc.)"
    )
    title: str = Field(..., description="Short fact title")
    detail: str = Field(..., description="Detailed description of the fact")
    confidence: Literal["low", "medium", "high"] = Field(
        ..., description="Confidence level in extraction"
    )
    evidence: list[EvidenceRef] = Field(
        ..., min_length=1, description="Supporting evidence (at least one required)"
    )


class OpenQuestion(BaseModel):
    """An open question identified during extraction."""

    question: str = Field(..., description="The open question")
    why_it_matters: str = Field(..., description="Why this question is important")
    suggested_owner: Literal["client", "consultant", "unknown"] = Field(
        ..., description="Who should answer this question"
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Optional supporting evidence"
    )


class Contradiction(BaseModel):
    """A contradiction or conflict found in the signal."""

    description: str = Field(..., description="Description of the contradiction")
    sides: list[str] = Field(..., min_length=2, description="Conflicting positions (at least two)")
    severity: Literal["minor", "important", "critical"] = Field(
        ..., description="Severity of the contradiction"
    )
    evidence: list[EvidenceRef] = Field(
        ..., min_length=1, description="Supporting evidence (at least one required)"
    )


class ExtractedClientInfo(BaseModel):
    """Client/project context information extracted from signal."""

    client_name: str | None = Field(None, description="Name of the client company")
    industry: str | None = Field(None, description="Industry/vertical of the client")
    website: str | None = Field(None, description="Client website URL")
    competitors: list[str] = Field(default_factory=list, description="Competitor names mentioned")
    confidence: Literal["low", "medium", "high"] = Field(
        default="medium", description="Confidence in extracted info"
    )


class ExtractFactsOutput(BaseModel):
    """Complete output from fact extraction LLM."""

    summary: str = Field(..., description="Summary of extracted content")
    facts: list[FactItem] = Field(default_factory=list, description="Extracted facts")
    open_questions: list[OpenQuestion] = Field(
        default_factory=list, description="Identified open questions"
    )
    contradictions: list[Contradiction] = Field(
        default_factory=list, description="Identified contradictions"
    )
    client_info: ExtractedClientInfo | None = Field(
        default=None, description="Extracted client/project context information"
    )


# =======================
# API request/response models
# =======================


class ExtractFactsRequest(BaseModel):
    """Request body for fact extraction endpoint."""

    signal_id: UUID = Field(..., description="Signal UUID to extract facts from")
    project_id: UUID | None = Field(default=None, description="Optional project_id for validation")
    top_chunks: int | None = Field(default=None, description="Override max chunks to process")


class ExtractFactsResponse(BaseModel):
    """Response body for fact extraction endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    extracted_facts_id: UUID = Field(..., description="ID of stored extracted facts")
    summary: str = Field(..., description="Summary of extracted content")
    facts_count: int = Field(..., description="Number of facts extracted")
    open_questions_count: int = Field(..., description="Number of open questions")
    contradictions_count: int = Field(..., description="Number of contradictions")


class ReplayRequest(BaseModel):
    """Request body for replay endpoint."""

    override_model: str | None = Field(
        default=None, description="Override model for replay (e.g., gpt-4o)"
    )
    override_top_chunks: int | None = Field(
        default=None, description="Override max chunks to process"
    )
