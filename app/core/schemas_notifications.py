"""Pydantic schemas for notifications."""

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str | None = None
    project_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    read: bool = False
    created_at: str
    metadata: dict = {}


class UnreadCountResponse(BaseModel):
    count: int
