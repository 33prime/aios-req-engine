"""Pydantic schemas for Phase 0 API endpoints."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request schema for signal ingestion."""

    project_id: UUID = Field(..., description="Project UUID")
    signal_type: str = Field(
        ...,
        description="Type of signal: email, transcript, note, file, or file_text",
        pattern="^(email|transcript|note|file|file_text)$",
    )
    source: str = Field(..., description="Source identifier (e.g., email address, file name)")
    raw_text: str = Field(..., description="Raw text content of the signal")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata as key-value pairs"
    )


class IngestResponse(BaseModel):
    """Response schema for signal ingestion."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    signal_id: UUID = Field(..., description="Created signal UUID")
    chunks_inserted: int = Field(..., description="Number of chunks inserted")


class SearchRequest(BaseModel):
    """Request schema for vector search."""

    project_id: UUID | None = Field(
        default=None, description="Optional project UUID to filter results"
    )
    query: str = Field(..., description="Search query text", min_length=1)
    top_k: int = Field(default=10, description="Number of results to return", ge=1, le=100)


class SearchResult(BaseModel):
    """Individual search result."""

    signal_id: UUID = Field(..., description="Signal UUID")
    chunk_id: UUID = Field(..., description="Chunk UUID")
    chunk_index: int = Field(..., description="Chunk index within signal")
    content: str = Field(..., description="Chunk text content")
    similarity: float = Field(..., description="Cosine similarity score (0-1)")
    start_char: int = Field(..., description="Start character position in original text")
    end_char: int = Field(..., description="End character position in original text")
    metadata: dict[str, Any] = Field(..., description="Signal metadata")
    chunk_metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk-level metadata")


class SearchResponse(BaseModel):
    """Response schema for vector search."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    results: list[SearchResult] = Field(..., description="List of matching chunks")
