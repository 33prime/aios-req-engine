"""Tests for the feature analyzer chain."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.chains.analyze_prototype_feature import analyze_prototype_feature
from app.core.schemas_prototypes import FeatureAnalysis


@pytest.fixture
def sample_feature():
    """Sample AIOS feature record."""
    return {
        "id": str(uuid4()),
        "name": "Login",
        "category": "authentication",
        "overview": "User authentication via email and password",
        "user_actions": ["Enter email", "Enter password", "Click login"],
        "system_behaviors": ["Validate credentials", "Create session"],
        "ui_requirements": ["Email input", "Password input", "Submit button"],
        "rules": ["Password must be 8+ characters"],
        "integrations": ["User profile"],
    }


@pytest.fixture
def sample_code():
    """Sample prototype code for a login component."""
    return """
import React, { useState } from 'react';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    // validate and submit
    if (password.length < 8) return;
    await login(email, password);
  };

  return (
    <form onSubmit={handleSubmit} data-feature-id="feat-login">
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Login</button>
    </form>
  );
}
"""


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.PROTOTYPE_ANALYSIS_MODEL = "claude-sonnet-4-20250514"
    settings.ANTHROPIC_API_KEY = "test-key"
    return settings


class TestAnalyzePrototypeFeature:
    """Tests for the analyze_prototype_feature chain."""

    def test_returns_feature_analysis(self, sample_feature, sample_code, mock_settings):
        """Should return a FeatureAnalysis object."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "triggers": ["User enters email and password"],
                        "actions": ["Validates password length", "Calls login API"],
                        "data_requirements": ["Email (string, validated)", "Password (string, min 8 chars)"],
                        "business_rules": [
                            {"rule": "Password must be 8+ characters", "source": "confirmed", "confidence": 1.0}
                        ],
                        "integration_points": ["login() API function"],
                        "implementation_status": "functional",
                        "confidence": 0.85,
                        "notes": "Basic login form with client-side validation",
                    }
                )
            )
        ]

        with patch("app.chains.analyze_prototype_feature.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = analyze_prototype_feature(
                code_content=sample_code,
                feature=sample_feature,
                handoff_entry="Login: Email/password form with validation",
                settings=mock_settings,
            )

            assert isinstance(result, FeatureAnalysis)
            assert result.implementation_status == "functional"
            assert result.confidence == 0.85
            assert len(result.triggers) == 1
            assert len(result.business_rules) == 1
            assert result.business_rules[0]["source"] == "confirmed"

    def test_uses_configured_model(self, sample_feature, sample_code, mock_settings):
        """Should use the PROTOTYPE_ANALYSIS_MODEL setting."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "triggers": [],
                        "actions": [],
                        "data_requirements": [],
                        "business_rules": [],
                        "integration_points": [],
                        "implementation_status": "placeholder",
                        "confidence": 0.5,
                        "notes": "",
                    }
                )
            )
        ]

        with patch("app.chains.analyze_prototype_feature.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            analyze_prototype_feature(
                code_content=sample_code,
                feature=sample_feature,
                handoff_entry=None,
                settings=mock_settings,
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_respects_model_override(self, sample_feature, sample_code, mock_settings):
        """Model override should take precedence."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "triggers": [],
                        "actions": [],
                        "data_requirements": [],
                        "business_rules": [],
                        "integration_points": [],
                        "implementation_status": "placeholder",
                        "confidence": 0.5,
                        "notes": "",
                    }
                )
            )
        ]

        with patch("app.chains.analyze_prototype_feature.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            analyze_prototype_feature(
                code_content=sample_code,
                feature=sample_feature,
                handoff_entry=None,
                settings=mock_settings,
                model_override="custom-model",
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "custom-model"

    def test_handles_missing_handoff(self, sample_feature, sample_code, mock_settings):
        """None handoff_entry should include 'Not found' in user message."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "triggers": [],
                        "actions": [],
                        "data_requirements": [],
                        "business_rules": [],
                        "integration_points": [],
                        "implementation_status": "partial",
                        "confidence": 0.4,
                        "notes": "No HANDOFF.md entry found",
                    }
                )
            )
        ]

        with patch("app.chains.analyze_prototype_feature.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            result = analyze_prototype_feature(
                code_content=sample_code,
                feature=sample_feature,
                handoff_entry=None,
                settings=mock_settings,
            )

            # Verify the user message included the fallback text
            call_kwargs = mock_client.messages.create.call_args[1]
            user_msg = call_kwargs["messages"][0]["content"]
            assert "Not found in HANDOFF.md" in user_msg
            assert result.implementation_status == "partial"

    def test_truncates_long_code(self, sample_feature, mock_settings):
        """Code content over 8000 chars should be truncated."""
        long_code = "// " + "x" * 10000

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "triggers": [],
                        "actions": [],
                        "data_requirements": [],
                        "business_rules": [],
                        "integration_points": [],
                        "implementation_status": "placeholder",
                        "confidence": 0.3,
                        "notes": "",
                    }
                )
            )
        ]

        with patch("app.chains.analyze_prototype_feature.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            analyze_prototype_feature(
                code_content=long_code,
                feature=sample_feature,
                handoff_entry=None,
                settings=mock_settings,
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            user_msg = call_kwargs["messages"][0]["content"]
            # The code block should not contain the full 10000 char string
            assert len(user_msg) < len(long_code)


class TestFeatureAnalysisSchema:
    """Tests for the FeatureAnalysis Pydantic model."""

    def test_default_values(self):
        """Defaults should produce a valid minimal analysis."""
        analysis = FeatureAnalysis()
        assert analysis.triggers == []
        assert analysis.actions == []
        assert analysis.implementation_status == "placeholder"
        assert analysis.confidence == 0

    def test_full_analysis(self):
        """All fields populated should work."""
        analysis = FeatureAnalysis(
            triggers=["Button click"],
            actions=["Submit form"],
            data_requirements=["Email field"],
            business_rules=[{"rule": "Must validate", "source": "aios", "confidence": 1.0}],
            integration_points=["Auth service"],
            implementation_status="functional",
            confidence=0.9,
            notes="Well implemented",
        )
        assert len(analysis.triggers) == 1
        assert analysis.confidence == 0.9
        assert analysis.notes == "Well implemented"
