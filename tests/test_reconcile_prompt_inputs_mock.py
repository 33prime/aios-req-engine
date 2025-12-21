"""Tests for reconcile input preparation with mocked dependencies."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.reconcile_inputs import (
    build_reconcile_prompt,
    get_canonical_snapshot,
    get_delta_inputs,
)


@pytest.fixture
def mock_db_calls():
    """Mock all database calls."""
    with (
        patch("app.core.reconcile_inputs.list_prd_sections") as mock_prd,
        patch("app.core.reconcile_inputs.list_vp_steps") as mock_vp,
        patch("app.core.reconcile_inputs.list_features") as mock_features,
        patch("app.core.reconcile_inputs.list_latest_extracted_facts") as mock_facts,
        patch("app.core.reconcile_inputs.list_latest_insights") as mock_insights,
    ):
        yield {
            "list_prd_sections": mock_prd,
            "list_vp_steps": mock_vp,
            "list_features": mock_features,
            "list_latest_extracted_facts": mock_facts,
            "list_latest_insights": mock_insights,
        }


class TestGetCanonicalSnapshot:
    def test_get_snapshot_with_data(self, mock_db_calls):
        """Test getting canonical snapshot with data."""
        project_id = uuid4()

        mock_db_calls["list_prd_sections"].return_value = [
            {
                "slug": "personas",
                "label": "Personas",
                "status": "draft",
                "fields": {"content": "User personas"},
                "client_needs": [],
            }
        ]
        mock_db_calls["list_vp_steps"].return_value = [
            {
                "step_index": 1,
                "label": "Login",
                "status": "draft",
                "description": "User logs in",
            }
        ]
        mock_db_calls["list_features"].return_value = [
            {
                "name": "Authentication",
                "category": "Security",
                "is_mvp": True,
                "confidence": "high",
                "status": "draft",
            }
        ]

        result = get_canonical_snapshot(project_id)

        assert len(result["prd_sections"]) == 1
        assert len(result["vp_steps"]) == 1
        assert len(result["features"]) == 1

    def test_get_snapshot_empty(self, mock_db_calls):
        """Test getting canonical snapshot with no data."""
        project_id = uuid4()

        mock_db_calls["list_prd_sections"].return_value = []
        mock_db_calls["list_vp_steps"].return_value = []
        mock_db_calls["list_features"].return_value = []

        result = get_canonical_snapshot(project_id)

        assert len(result["prd_sections"]) == 0
        assert len(result["vp_steps"]) == 0
        assert len(result["features"]) == 0


class TestGetDeltaInputs:
    def test_get_delta_with_new_facts(self, mock_db_calls):
        """Test getting delta inputs with new facts."""
        project_id = uuid4()
        project_state = {
            "last_extracted_facts_id": None,
            "last_insight_id": None,
        }

        fact_id = uuid4()
        signal_id = uuid4()
        mock_db_calls["list_latest_extracted_facts"].return_value = [
            {
                "id": str(fact_id),
                "signal_id": str(signal_id),
                "summary": "New requirements extracted",
                "facts": {"facts": [{"title": "Feature A", "detail": "Details"}]},
            }
        ]
        mock_db_calls["list_latest_insights"].return_value = []

        result = get_delta_inputs(project_id, project_state)

        assert result["facts_count"] == 1
        assert result["insights_count"] == 0
        assert len(result["extracted_facts_ids"]) == 1
        assert str(signal_id) in result["source_signal_ids"]

    def test_get_delta_with_checkpoint(self, mock_db_calls):
        """Test getting delta inputs with checkpoint (no new data)."""
        project_id = uuid4()
        last_fact_id = uuid4()
        project_state = {
            "last_extracted_facts_id": str(last_fact_id),
            "last_insight_id": None,
        }

        mock_db_calls["list_latest_extracted_facts"].return_value = [
            {
                "id": str(last_fact_id),
                "signal_id": str(uuid4()),
                "summary": "Old fact",
                "facts": {"facts": []},
            }
        ]
        mock_db_calls["list_latest_insights"].return_value = []

        result = get_delta_inputs(project_id, project_state)

        # Should stop at checkpoint
        assert result["facts_count"] == 0
        assert result["insights_count"] == 0

    def test_get_delta_with_insights(self, mock_db_calls):
        """Test getting delta inputs with new insights."""
        project_id = uuid4()
        project_state = {
            "last_extracted_facts_id": None,
            "last_insight_id": None,
        }

        insight_id = uuid4()
        mock_db_calls["list_latest_extracted_facts"].return_value = []
        mock_db_calls["list_latest_insights"].return_value = [
            {
                "id": str(insight_id),
                "title": "Missing validation",
                "finding": "Input validation is missing",
                "status": "open",
            }
        ]

        result = get_delta_inputs(project_id, project_state)

        assert result["facts_count"] == 0
        assert result["insights_count"] == 1
        assert len(result["insight_ids"]) == 1


class TestBuildReconcilePrompt:
    def test_build_prompt_with_data(self):
        """Test building reconcile prompt with data."""
        canonical_snapshot = {
            "prd_sections": [
                {
                    "slug": "personas",
                    "label": "Personas",
                    "status": "draft",
                    "fields": {"content": "User personas"},
                    "client_needs": [],
                }
            ],
            "vp_steps": [
                {
                    "step_index": 1,
                    "label": "Login",
                    "status": "draft",
                    "description": "User logs in",
                }
            ],
            "features": [
                {
                    "name": "Authentication",
                    "category": "Security",
                    "is_mvp": True,
                    "confidence": "high",
                    "status": "draft",
                }
            ],
        }

        delta_digest = {
            "extracted_facts": [
                {
                    "id": str(uuid4()),
                    "summary": "New requirements",
                    "facts": {"facts": [{"title": "Feature A", "detail": "Details"}]},
                }
            ],
            "insights": [],
            "facts_count": 1,
            "insights_count": 0,
        }

        retrieved_chunks = [
            {
                "chunk_id": str(uuid4()),
                "content": "User should be able to login with email",
                "signal_metadata": {"signal_type": "email"},
            }
        ]

        prompt = build_reconcile_prompt(canonical_snapshot, delta_digest, retrieved_chunks)

        assert "RECONCILIATION TASK" in prompt
        assert "CURRENT CANONICAL STATE" in prompt
        assert "NEW INPUTS (DELTA)" in prompt
        assert "SUPPORTING CONTEXT" in prompt
        assert "personas" in prompt
        assert "Login" in prompt
        assert "Authentication" in prompt

    def test_build_prompt_empty_state(self):
        """Test building prompt with empty canonical state."""
        canonical_snapshot = {
            "prd_sections": [],
            "vp_steps": [],
            "features": [],
        }

        delta_digest = {
            "extracted_facts": [],
            "insights": [],
            "facts_count": 0,
            "insights_count": 0,
        }

        retrieved_chunks = []

        prompt = build_reconcile_prompt(canonical_snapshot, delta_digest, retrieved_chunks)

        assert "RECONCILIATION TASK" in prompt
        assert "PRD Sections (0)" in prompt
        assert "Value Path Steps (0)" in prompt
        assert "Features (0)" in prompt

