"""Basic tests for VP enrichment schema and functionality."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.schemas_vp_enrich import EnrichVPStepOutput
from app.graphs.enrich_vp_graph import run_enrich_vp_agent


@pytest.fixture
def mock_vp_step():
    """Mock VP step for testing."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "step_index": 1,
        "label": "User Registration",
        "status": "draft",
        "description": "Allow users to create accounts",
        "user_benefit_pain": "Easy account creation",
        "ui_overview": "Simple registration form",
        "value_created": "User can access the system",
        "kpi_impact": "Increase user registrations",
        "needed": [],
        "sources": [],
        "evidence": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_vp_enrichment_output():
    """Mock VP enrichment output."""
    evidence = {
        "chunk_id": str(uuid.uuid4()),
        "excerpt": "Sample evidence for VP enrichment",
        "rationale": "Supports the enrichment",
    }

    return {
        "step_id": str(uuid.uuid4()),
        "step_index": 1,
        "enhanced_fields": {
            "description": "Enhanced step description with more implementation details",
            "ui_overview": "Detailed UI overview with wireframe descriptions",
            "value_created": "Expanded explanation of value created for users",
            "kpi_impact": "Detailed KPI impact analysis",
            "experiments": "Suggested A/B tests for optimization",
        },
        "proposed_needs": [
            {
                "key": "ui_validation",
                "title": "Validate UI Design",
                "why": "Need to ensure UI meets user needs",
                "ask": "Can you validate this UI approach?",
                "priority": "medium",
                "suggested_method": "meeting",
                "evidence": [evidence],
            }
        ],
        "evidence": [evidence],
        "summary": "Enhanced VP step with detailed implementation guidance",
        "schema_version": "vp_enrichment_v1",
    }


class TestVPEnrichmentBasic:
    """Basic tests for VP enrichment."""

    def test_enrich_vp_output_schema(self, mock_vp_enrichment_output):
        """Test VP enrichment output schema validation."""
        output = EnrichVPStepOutput.model_validate(mock_vp_enrichment_output)

        assert output.step_id
        assert output.step_index == 1
        assert len(output.enhanced_fields) > 0
        assert output.summary == "Enhanced VP step with detailed implementation guidance"
        assert output.schema_version == "vp_enrichment_v1"

    @patch("app.core.vp_enrich_inputs.get_vp_enrich_context")
    @patch("app.chains.enrich_vp.enrich_vp_step")
    @patch("app.db.vp.patch_vp_step_enrichment")
    def test_vp_enrichment_agent_basic(
        self, mock_patch_enrichment, mock_enrich_step, mock_get_context, mock_vp_step, mock_vp_enrichment_output
    ):
        """Test basic VP enrichment agent functionality."""
        # Setup mocks
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_vp_step["project_id"] = str(project_id)
        mock_get_context.return_value = {
            "steps": [mock_vp_step],
            "canonical_vp": [mock_vp_step],
            "facts": [],
            "insights": [],
            "confirmations": [],
            "chunks": [],
            "include_research": False,
        }

        # Mock enrichment output
        mock_output = EnrichVPStepOutput.model_validate(mock_vp_enrichment_output)
        mock_enrich_step.return_value = mock_output

        # Mock patch function
        mock_patch_enrichment.return_value = mock_vp_step

        # Run the agent
        steps_processed, steps_updated, summary = run_enrich_vp_agent(
            project_id=project_id,
            run_id=run_id,
            step_ids=[uuid.UUID(mock_vp_step["id"])],
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert steps_processed == 1
        assert steps_updated == 1
        assert "Processed 1 VP steps" in summary
        assert "Successfully updated 1 steps" in summary

        # Verify mocks were called
        mock_get_context.assert_called_once()
        mock_enrich_step.assert_called_once()
        mock_patch_enrichment.assert_called_once()
