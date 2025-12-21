"""Pydantic schemas for evidence references."""

from uuid import UUID

from pydantic import BaseModel, Field


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
