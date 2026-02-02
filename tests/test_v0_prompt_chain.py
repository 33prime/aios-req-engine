"""Tests for the v0 prompt generator chain."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.chains.generate_v0_prompt import build_user_message, generate_v0_prompt


@pytest.fixture
def sample_project():
    """Sample project record."""
    return {
        "id": str(uuid4()),
        "name": "TestApp",
        "description": "A test application for demo purposes",
    }


@pytest.fixture
def sample_features():
    """Sample feature records."""
    return [
        {
            "id": str(uuid4()),
            "name": "Login",
            "category": "authentication",
            "is_mvp": True,
            "overview": "User authentication via email and password",
            "user_actions": ["Enter email", "Enter password", "Click login"],
            "system_behaviors": ["Validate credentials", "Create session"],
            "ui_requirements": ["Email input", "Password input", "Submit button"],
            "rules": ["Password must be 8+ characters"],
        },
        {
            "id": str(uuid4()),
            "name": "Dashboard",
            "category": "core",
            "is_mvp": True,
            "overview": "Main dashboard with stats and recent activity",
            "user_actions": ["View stats", "Navigate to details"],
            "system_behaviors": ["Load aggregated data", "Refresh on interval"],
            "ui_requirements": ["Stats cards", "Activity feed"],
            "rules": [],
        },
    ]


@pytest.fixture
def sample_personas():
    """Sample persona records."""
    return [
        {
            "id": str(uuid4()),
            "name": "Sarah Chen",
            "role": "Product Manager",
            "goals": ["Track project progress", "Make data-driven decisions"],
            "pain_points": ["Information scattered across tools"],
            "key_workflows": [{"name": "Daily Review", "description": "Morning check-in"}],
        }
    ]


@pytest.fixture
def sample_vp_steps():
    """Sample VP step records."""
    return [
        {
            "step_index": 0,
            "label": "Sign Up",
            "description": "User creates account",
            "actor_persona_name": "Sarah Chen",
            "features_used": [{"feature_id": "feat-1", "feature_name": "Login"}],
            "narrative_user": "Sarah creates her account using email",
        },
        {
            "step_index": 1,
            "label": "First Dashboard View",
            "description": "User sees their dashboard",
            "actor_persona_name": "Sarah Chen",
            "features_used": [{"feature_id": "feat-2", "feature_name": "Dashboard"}],
            "narrative_user": "Sarah sees her personalized dashboard",
        },
    ]


class TestBuildUserMessage:
    """Tests for build_user_message helper."""

    def test_includes_project_name(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """Project name should appear in the message."""
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        assert "TestApp" in msg

    def test_includes_all_features(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """All features should be included."""
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        assert "Login" in msg
        assert "Dashboard" in msg
        assert f"Features ({len(sample_features)})" in msg

    def test_includes_personas(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """Personas should be included."""
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        assert "Sarah Chen" in msg

    def test_includes_vp_steps(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """VP steps should be included."""
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        assert "Sign Up" in msg
        assert "First Dashboard View" in msg

    def test_includes_learnings_when_provided(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """Cross-project learnings should be included when provided."""
        learnings = [
            {"category": "structure", "learning": "Always include a sidebar nav"},
        ]
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
            learnings=learnings,
        )
        assert "Prompt Learnings" in msg
        assert "Always include a sidebar nav" in msg

    def test_handles_empty_features(self, sample_project, sample_personas, sample_vp_steps):
        """Empty features list should not cause errors."""
        msg = build_user_message(
            project=sample_project,
            features=[],
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        assert "Features (0)" in msg

    def test_includes_feature_ids(self, sample_project, sample_features, sample_personas, sample_vp_steps):
        """Feature IDs should be present for data-feature-id mapping."""
        msg = build_user_message(
            project=sample_project,
            features=sample_features,
            personas=sample_personas,
            vp_steps=sample_vp_steps,
        )
        for feature in sample_features:
            assert feature["id"] in msg


class TestGenerateV0Prompt:
    """Tests for the generate_v0_prompt chain function."""

    def test_calls_anthropic_with_correct_model(
        self, sample_project, sample_features, sample_personas, sample_vp_steps
    ):
        """Should use the configured model."""
        mock_settings = MagicMock()
        mock_settings.PROTOTYPE_PROMPT_MODEL = "claude-opus-4-5-20251101"
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "prompt": "Build a React app...",
                        "features_included": [sample_features[0]["id"]],
                        "flows_included": ["Sign Up"],
                    }
                )
            )
        ]

        with patch("app.chains.generate_v0_prompt.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = generate_v0_prompt(
                project=sample_project,
                features=sample_features,
                personas=sample_personas,
                vp_steps=sample_vp_steps,
                settings=mock_settings,
            )

            assert result.prompt == "Build a React app..."
            assert len(result.features_included) == 1
            assert len(result.flows_included) == 1
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-opus-4-5-20251101"

    def test_supports_model_override(
        self, sample_project, sample_features, sample_personas, sample_vp_steps
    ):
        """Model override should be respected."""
        mock_settings = MagicMock()
        mock_settings.PROTOTYPE_PROMPT_MODEL = "default-model"
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {"prompt": "...", "features_included": [], "flows_included": []}
                )
            )
        ]

        with patch("app.chains.generate_v0_prompt.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            generate_v0_prompt(
                project=sample_project,
                features=sample_features,
                personas=sample_personas,
                vp_steps=sample_vp_steps,
                settings=mock_settings,
                model_override="override-model",
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "override-model"
