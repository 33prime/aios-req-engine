"""Tests for the prompt audit chain."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.chains.audit_v0_output import audit_v0_output, should_retry
from app.core.schemas_prototypes import PromptAuditResult


@pytest.fixture
def sample_features():
    """Sample features for audit."""
    return [
        {"id": str(uuid4()), "name": "Login"},
        {"id": str(uuid4()), "name": "Dashboard"},
        {"id": str(uuid4()), "name": "Settings"},
    ]


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.PROTOTYPE_ANALYSIS_MODEL = "claude-sonnet-4-20250514"
    settings.ANTHROPIC_API_KEY = "test-key"
    return settings


class TestAuditV0Output:
    """Tests for audit_v0_output chain."""

    def test_audits_with_all_features_found(self, sample_features, mock_settings):
        """Full coverage should produce high scores."""
        feature_scan = {f["id"]: [f"src/{f['name']}.tsx"] for f in sample_features}

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "feature_coverage_score": 1.0,
                        "structure_score": 0.9,
                        "mock_data_score": 0.85,
                        "flow_score": 0.8,
                        "feature_id_score": 0.95,
                        "overall_score": 0.9,
                        "gaps": [],
                        "recommendations": [],
                    }
                )
            )
        ]

        with patch("app.chains.audit_v0_output.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = audit_v0_output(
                original_prompt="Generate a React app...",
                handoff_content="# HANDOFF\n## Features\n...",
                file_tree=["src/Login.tsx", "src/Dashboard.tsx", "src/Settings.tsx"],
                feature_scan=feature_scan,
                expected_features=sample_features,
                settings=mock_settings,
            )

            assert result.overall_score == 0.9
            assert result.feature_coverage_score == 1.0
            assert len(result.gaps) == 0

    def test_audits_with_missing_features(self, sample_features, mock_settings):
        """Missing features should produce lower coverage score."""
        # Only one of three features found
        feature_scan = {sample_features[0]["id"]: ["src/Login.tsx"]}

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "feature_coverage_score": 0.33,
                        "structure_score": 0.5,
                        "mock_data_score": 0.4,
                        "flow_score": 0.3,
                        "feature_id_score": 0.2,
                        "overall_score": 0.35,
                        "gaps": [
                            {
                                "dimension": "feature_coverage",
                                "description": "Dashboard and Settings features missing",
                                "severity": "high",
                                "feature_ids": [sample_features[1]["id"], sample_features[2]["id"]],
                            }
                        ],
                        "recommendations": [
                            "Add Dashboard component with stats",
                            "Add Settings page",
                        ],
                    }
                )
            )
        ]

        with patch("app.chains.audit_v0_output.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = audit_v0_output(
                original_prompt="Generate a React app...",
                handoff_content=None,
                file_tree=["src/Login.tsx"],
                feature_scan=feature_scan,
                expected_features=sample_features,
                settings=mock_settings,
            )

            assert result.overall_score == 0.35
            assert len(result.gaps) == 1
            assert result.gaps[0].severity == "high"
            assert len(result.recommendations) == 2

    def test_audits_with_missing_handoff(self, sample_features, mock_settings):
        """Missing HANDOFF.md should produce low structure score."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "feature_coverage_score": 0.8,
                        "structure_score": 0.2,
                        "mock_data_score": 0.7,
                        "flow_score": 0.6,
                        "feature_id_score": 0.5,
                        "overall_score": 0.56,
                        "gaps": [
                            {
                                "dimension": "structure",
                                "description": "HANDOFF.md is missing",
                                "severity": "high",
                                "feature_ids": [],
                            }
                        ],
                        "recommendations": ["Create HANDOFF.md with feature inventory"],
                    }
                )
            )
        ]

        with patch("app.chains.audit_v0_output.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = audit_v0_output(
                original_prompt="Generate...",
                handoff_content=None,
                file_tree=["src/App.tsx"],
                feature_scan={},
                expected_features=sample_features,
                settings=mock_settings,
            )

            assert result.structure_score == 0.2
            assert any("HANDOFF" in g.description for g in result.gaps)


class TestShouldRetry:
    """Tests for retry decision logic."""

    @pytest.mark.parametrize(
        "score,expected",
        [
            (1.0, "accept"),
            (0.9, "accept"),
            (0.8, "accept"),
            (0.79, "retry"),
            (0.65, "retry"),
            (0.5, "retry"),
            (0.49, "notify"),
            (0.3, "notify"),
            (0.0, "notify"),
        ],
    )
    def test_decision_thresholds(self, score, expected):
        """Verify all decision thresholds."""
        audit = PromptAuditResult(overall_score=score)
        assert should_retry(audit) == expected
