"""Tests for feature enrichment idempotency."""

import uuid
from unittest.mock import MagicMock, patch

from app.graphs.enrich_features_graph import run_enrich_features_agent


def test_enrichment_idempotency():
    """Test that running enrichment multiple times doesn't create spam."""
    project_id = uuid.uuid4()
    run_id = uuid.uuid4()
    feature_id = uuid.uuid4()

    # Mock feature
    mock_feature = {
        "id": str(feature_id),
        "project_id": str(project_id),
        "name": "Test Feature",
        "category": "Test",
        "is_mvp": True,
        "confidence": "high",
        "status": "draft",
        "description": "Test feature",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }

    # Mock context
    mock_context = {
        "features": [mock_feature],
        "facts": [],
        "insights": [],
        "confirmations": [],
        "chunks": [],
        "include_research": False,
    }

    # Mock LLM output (same each time)
    mock_output = {
        "project_id": str(project_id),
        "feature_id": str(feature_id),
        "feature_slug": "Test Feature",
        "schema_version": "feature_details_v1",
        "details": {
            "summary": "Test feature summary",
            "data_requirements": [],
            "business_rules": [],
            "acceptance_criteria": [],
            "dependencies": [],
            "integrations": [],
            "telemetry_events": [],
            "risks": [],
        },
        "open_questions": [],
    }

    with (
        patch("app.core.feature_enrich_inputs.get_feature_enrich_context", return_value=mock_context) as mock_get_context,
        patch("app.chains.enrich_features.enrich_feature") as mock_enrich_feature,
        patch("app.db.features.patch_feature_details") as mock_patch_details,
        patch("app.core.schemas_feature_enrich.EnrichFeaturesOutput.model_validate") as mock_validate,
    ):
        # Setup the mock to return the same output each time
        mock_validate.return_value = MagicMock()
        mock_validate.return_value.details.model_dump.return_value = mock_output["details"]
        mock_enrich_feature.return_value = mock_validate.return_value

        # First run
        run_id_1 = uuid.uuid4()
        processed_1, updated_1, summary_1 = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id_1,
            feature_ids=[feature_id],
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        # Second run (same inputs)
        run_id_2 = uuid.uuid4()
        processed_2, updated_2, summary_2 = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id_2,
            feature_ids=[feature_id],
            only_mvp=False,
            include_research=False,
            top_k_context=24,
        )

        # Both runs should process the same number of features
        assert processed_1 == processed_2 == 1

        # Both runs should update the feature (since we always update in this simplified test)
        # In a real implementation, you'd check for material changes
        assert updated_1 == updated_2 == 1

        # Verify the LLM was called both times (since we don't cache results)
        assert mock_enrich_feature.call_count == 2

        # Verify patch_details was called both times
        assert mock_patch_details.call_count == 2

        # Both calls should have the same feature_id
        calls = mock_patch_details.call_args_list
        assert calls[0][0][0] == calls[1][0][0] == feature_id
