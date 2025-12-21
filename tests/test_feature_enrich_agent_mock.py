"""Mocked tests for feature enrichment agent."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.schemas_feature_enrich import EnrichFeaturesOutput
from app.graphs.enrich_features_graph import run_enrich_features_agent


@pytest.fixture
def mock_enrich_chain_output():
    """Mock LLM output for enrichment."""
    evidence = {
        "chunk_id": str(uuid.uuid4()),
        "excerpt": "Sample evidence for enrichment",
        "rationale": "Supports the enrichment",
    }

    return {
        "project_id": str(uuid.uuid4()),
        "feature_id": str(uuid.uuid4()),
        "feature_slug": "Test Feature",
        "schema_version": "feature_details_v1",
        "details": {
            "summary": "Test feature provides user authentication",
            "data_requirements": [
                {
                    "entity": "User",
                    "fields": ["id", "email", "password_hash"],
                    "notes": "User data required for authentication",
                    "evidence": [evidence],
                }
            ],
            "business_rules": [
                {
                    "title": "Password Security",
                    "rule": "Passwords must be at least 8 characters",
                    "verification": "Frontend validation + backend checks",
                    "evidence": [evidence],
                }
            ],
            "acceptance_criteria": [
                {
                    "criterion": "User can successfully log in",
                    "evidence": [evidence],
                }
            ],
            "dependencies": [
                {
                    "dependency_type": "external_system",
                    "name": "Auth Service",
                    "why": "Handles authentication logic",
                    "evidence": [evidence],
                }
            ],
            "integrations": [
                {
                    "system": "User Database",
                    "direction": "bidirectional",
                    "data_exchanged": "user credentials",
                    "evidence": [evidence],
                }
            ],
            "telemetry_events": [
                {
                    "event_name": "user_login",
                    "when_fired": "On successful login",
                    "properties": ["user_id", "timestamp"],
                    "success_metric": "Login success rate",
                    "evidence": [evidence],
                }
            ],
            "risks": [
                {
                    "title": "Security Breach",
                    "risk": "Unauthorized access to user data",
                    "mitigation": "Use encrypted storage and access controls",
                    "severity": "high",
                    "evidence": [evidence],
                }
            ],
        },
        "open_questions": [],
    }


@pytest.fixture
def mock_feature():
    """Mock feature for testing."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "name": "User Authentication",
        "category": "Security",
        "is_mvp": True,
        "confidence": "high",
        "status": "draft",
        "description": "Allow users to log in securely",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_context():
    """Mock enrichment context."""
    return {
        "facts": [
            {
                "id": str(uuid.uuid4()),
                "summary": "Users need secure authentication",
                "created_at": "2024-01-01T00:00:00Z",
            }
        ],
        "insights": [],
        "confirmations": [],
        "chunks": [
            {
                "chunk_id": str(uuid.uuid4()),
                "snippet": "Users must authenticate securely",
                "signal_type": "client_email",
                "authority": "client",
                "created_at": "2024-01-01",
            }
        ],
        "include_research": False,
    }


class TestFeatureEnrichAgentMock:
    """Test feature enrichment agent with mocked dependencies."""

    @patch("app.core.feature_enrich_inputs.get_feature_enrich_context")
    @patch("app.chains.enrich_features.enrich_feature")
    @patch("app.db.features.patch_feature_details")
    def test_successful_enrichment_single_feature(
        self, mock_patch_details, mock_enrich_feature, mock_get_context, mock_enrich_chain_output, mock_feature, mock_context
    ):
        """Test successful enrichment of a single feature."""
        # Setup mocks
        project_id = uuid.uuid4()
        feature_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_feature["id"] = str(feature_id)
        mock_feature["project_id"] = str(project_id)

        mock_context["features"] = [mock_feature]
        mock_get_context.return_value = mock_context

        # Mock the enrich_feature chain to return validated output
        mock_output = EnrichFeaturesOutput.model_validate(mock_enrich_chain_output)
        mock_enrich_feature.return_value = mock_output

        # Mock patch_feature_details
        mock_patch_details.return_value = {**mock_feature, "details": mock_output.details.model_dump(mode='json')}

        # Run the agent
        features_processed, features_updated, summary = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id,
            feature_ids=[feature_id],
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert features_processed == 1
        assert features_updated == 1
        assert "Processed 1 features" in summary
        assert "Successfully updated 1 features" in summary

        # Verify mocks were called correctly
        mock_get_context.assert_called_once_with(
            project_id=project_id,
            feature_ids=[feature_id],
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        mock_enrich_feature.assert_called_once()
        call_args = mock_enrich_feature.call_args
        assert call_args[1]["project_id"] == project_id
        assert call_args[1]["feature"] == mock_feature

        mock_patch_details.assert_called_once()
        patch_call_args = mock_patch_details.call_args
        assert patch_call_args[0][0] == feature_id  # feature_id
        assert isinstance(patch_call_args[0][1], dict)  # details dict
        assert "summary" in patch_call_args[0][1]

    @patch("app.core.feature_enrich_inputs.get_feature_enrich_context")
    @patch("app.chains.enrich_features.enrich_feature")
    @patch("app.db.features.patch_feature_details")
    def test_enrichment_failure_handling(
        self, mock_patch_details, mock_enrich_feature, mock_get_context, mock_feature, mock_context
    ):
        """Test handling of enrichment failures."""
        # Setup mocks
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_context["features"] = [mock_feature]
        mock_get_context.return_value = mock_context

        # Mock enrich_feature to raise an exception
        mock_enrich_feature.side_effect = ValueError("LLM parsing failed")

        # Mock patch_feature_details (should not be called)
        mock_patch_details.return_value = mock_feature

        # Run the agent
        features_processed, features_updated, summary = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id,
            feature_ids=None,
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert features_processed == 1
        assert features_updated == 0  # No successful updates
        assert "Processed 1 features" in summary
        assert "Failed to update 1 features" in summary

        # Verify patch_details was not called due to failure
        mock_patch_details.assert_not_called()

    @patch("app.core.feature_enrich_inputs.get_feature_enrich_context")
    @patch("app.chains.enrich_features.enrich_feature")
    @patch("app.db.features.patch_feature_details")
    def test_mvp_filtering(
        self, mock_patch_details, mock_enrich_feature, mock_get_context, mock_enrich_chain_output, mock_feature
    ):
        """Test MVP-only filtering."""
        # Setup mocks
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()

        # Create one MVP and one non-MVP feature
        mvp_feature = {**mock_feature, "is_mvp": True, "id": str(uuid.uuid4())}
        non_mvp_feature = {**mock_feature, "is_mvp": False, "id": str(uuid.uuid4())}

        mock_get_context.return_value = {
            "features": [mvp_feature, non_mvp_feature],
            "facts": [],
            "insights": [],
            "confirmations": [],
            "chunks": [],
            "include_research": False,
        }

        # Mock successful enrichment
        mock_output = EnrichFeaturesOutput.model_validate(mock_enrich_chain_output)
        mock_enrich_feature.return_value = mock_output
        mock_patch_details.return_value = mvp_feature

        # Run agent with only_mvp=True
        features_processed, features_updated, summary = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id,
            feature_ids=None,
            only_mvp=True,  # Only MVP features
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert features_processed == 1  # Only MVP feature processed
        assert features_updated == 1

        # Verify get_context was called with only_mvp=True
        mock_get_context.assert_called_once()
        call_kwargs = mock_get_context.call_args[1]
        assert call_kwargs["only_mvp"] is True

    @patch("app.core.feature_enrich_inputs.get_feature_enrich_context")
    @patch("app.chains.enrich_features.enrich_feature")
    @patch("app.db.features.patch_feature_details")
    def test_no_features_to_process(
        self, mock_patch_details, mock_enrich_feature, mock_get_context
    ):
        """Test when no features match the criteria."""
        # Setup mocks
        project_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_get_context.return_value = {
            "features": [],  # No features
            "facts": [],
            "insights": [],
            "confirmations": [],
            "chunks": [],
            "include_research": False,
        }

        # Run the agent
        features_processed, features_updated, summary = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id,
            feature_ids=None,
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        # Assertions
        assert features_processed == 0
        assert features_updated == 0
        assert "Processed 0 features" in summary

        # Verify enrichment chain was not called
        mock_enrich_feature.assert_not_called()
        mock_patch_details.assert_not_called()
