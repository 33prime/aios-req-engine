"""Tests for baseline endpoints auto-creation."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for the app."""
    return TestClient(app)


def test_get_baseline_auto_creates(client):
    """Test GET baseline auto-creates default gate."""
    project_id = uuid4()

    with patch("app.db.project_gates.get_or_create_project_gate") as mock_get_or_create:
        mock_get_or_create.return_value = {"project_id": str(project_id), "baseline_ready": False}

        response = client.get(f"/v1/projects/{project_id}/baseline")

        assert response.status_code == 200
        data = response.json()
        assert data["baseline_ready"] is False

        mock_get_or_create.assert_called_once_with(project_id)


def test_patch_baseline_upserts(client):
    """Test PATCH baseline uses upsert."""
    project_id = uuid4()

    with patch("app.db.project_gates.upsert_project_gate") as mock_upsert:
        mock_upsert.return_value = {"project_id": str(project_id), "baseline_ready": True}

        response = client.patch(
            f"/v1/projects/{project_id}/baseline",
            json={"baseline_ready": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["baseline_ready"] is True

        mock_upsert.assert_called_once_with(project_id, {"baseline_ready": True})
