"""Basic tests for PRD enrichment schema and functionality."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.schemas_prd_enrich import EnrichPRDSectionOutput
from app.graphs.enrich_prd_graph import run_enrich_prd_agent


@pytest.fixture
def mock_prd_section():
    """Mock PRD section for testing."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "slug": "personas",
        "label": "Personas",
        "required": True,
        "status": "draft",
        "fields": {"content": "Basic persona information"},
        "client_needs": [],
        "sources": [],
        "evidence": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_prd_enrichment_output():
    """Mock PRD enrichment output."""
    evidence = {
        "chunk_id": str(uuid.uuid4()),
        "excerpt": "Sample evidence for PRD enrichment",
        "rationale": "Supports the enrichment",
    }

    return {
        "section_id": str(uuid.uuid4()),
        "slug": "personas",
        "enhanced_fields": {
            "content": "Enhanced persona content with more details",
            "description": "Detailed persona descriptions",
        },
        "proposed_client_needs": [
            {
                "key": "persona_validation",
                "title": "Validate Persona Accuracy",
                "why": "Need to confirm persona details are accurate",
                "ask": "Can you confirm these persona details are accurate?",
                "priority": "medium",
                "suggested_method": "email",
                "evidence": [evidence],
            }
        ],
        "evidence": [evidence],
        "summary": "Enhanced personas section with more detailed descriptions",
        "schema_version": "prd_enrichment_v1",
    }


class TestPRDEnrichmentBasic:
    """Basic tests for PRD enrichment."""

    def test_enrich_prd_output_schema(self, mock_prd_enrichment_output):
        """Test PRD enrichment output schema validation."""
        output = EnrichPRDSectionOutput.model_validate(mock_prd_enrichment_output)

        assert output.section_id
        assert output.slug == "personas"
        assert len(output.enhanced_fields) > 0
        assert output.summary == "Enhanced personas section with more detailed descriptions"
        assert output.schema_version == "prd_enrichment_v1"

    @patch("app.core.prd_enrich_inputs.get_prd_enrich_context")
    @patch("app.chains.enrich_prd.enrich_prd_section")
    @patch("app.db.prd.patch_prd_section_enrichment")
    def test_prd_enrichment_agent_basic(
        self, mock_patch_enrichment, mock_enrich_section, mock_get_context, mock_prd_section, mock_prd_enrichment_output
    ):
        """Test basic PRD enrichment agent functionality."""
        # Setup mocks
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_prd_section["project_id"] = str(project_id)
        mock_get_context.return_value = {
            "sections": [mock_prd_section],
            "canonical_prd": [mock_prd_section],
            "facts": [],
            "insights": [],
            "confirmations": [],
            "chunks": [],
            "include_research": False,
        }

        # Mock enrichment output
        mock_output = EnrichPRDSectionOutput.model_validate(mock_prd_enrichment_output)
        mock_enrich_section.return_value = mock_output

        # Mock patch function
        mock_patch_enrichment.return_value = mock_prd_section

        # Run the agent
        sections_processed, sections_updated, summary = run_enrich_prd_agent(
            project_id=project_id,
            run_id=run_id,
            section_slugs=["personas"],
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert sections_processed == 1
        assert sections_updated == 1
        assert "Processed 1 PRD sections" in summary
        assert "Successfully updated 1 sections" in summary

        # Verify mocks were called
        mock_get_context.assert_called_once()
        mock_enrich_section.assert_called_once()
        mock_patch_enrichment.assert_called_once()
