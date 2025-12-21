"""Tests for project gates auto-creation functionality."""

from unittest.mock import patch

import pytest
from uuid import uuid4

from app.db.project_gates import get_or_create_project_gate


def test_get_or_create_creates_default_when_none():
    """Test that get_or_create_project_gate creates default when no gate exists."""
    project_id = uuid4()

    with patch("app.db.project_gates.get_project_gate", return_value=None) as mock_get, \
         patch("app.db.project_gates.create_default_project_gate") as mock_create:

        mock_create.return_value = {"project_id": str(project_id), "baseline_ready": False}

        result = get_or_create_project_gate(project_id)

        mock_get.assert_called_once_with(project_id)
        mock_create.assert_called_once_with(project_id)
        assert result["baseline_ready"] is False


def test_get_or_create_returns_existing():
    """Test that get_or_create_project_gate returns existing gate."""
    project_id = uuid4()
    existing_gate = {"project_id": str(project_id), "baseline_ready": True}

    with patch("app.db.project_gates.get_project_gate", return_value=existing_gate) as mock_get, \
         patch("app.db.project_gates.create_default_project_gate") as mock_create:

        result = get_or_create_project_gate(project_id)

        mock_get.assert_called_once_with(project_id)
        mock_create.assert_not_called()
        assert result["baseline_ready"] is True
