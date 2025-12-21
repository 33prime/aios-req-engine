"""Pydantic schemas for project-level operations."""

from typing import Literal

from pydantic import BaseModel, Field


class BaselineStatus(BaseModel):
    """Response schema for baseline status."""

    baseline_ready: bool = Field(..., description="Whether research features are enabled")


class BaselinePatchRequest(BaseModel):
    """Request body for updating baseline configuration."""

    baseline_ready: bool = Field(..., description="Whether to enable research features")
