"""Tests for outreach draft generation logic."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.outreach import _decide_outreach_method, _generate_email_draft, _generate_meeting_draft
from app.main import app

client = TestClient(app)


class TestDecideOutreachMethod:
    def test_meeting_for_many_items(self):
        """Test that meeting is recommended for 3+ items."""
        confirmations = [
            {"title": "Item 1", "priority": "low"},
            {"title": "Item 2", "priority": "low"},
            {"title": "Item 3", "priority": "low"},
        ]

        method, reason = _decide_outreach_method(confirmations)

        assert method == "meeting"
        assert "3+ open confirmations" in reason

    def test_meeting_for_high_priority(self):
        """Test that meeting is recommended for high priority items."""
        confirmations = [
            {"title": "Critical decision", "priority": "high", "why": "Important"},
        ]

        method, reason = _decide_outreach_method(confirmations)

        assert method == "meeting"
        assert "High-priority" in reason

    def test_meeting_for_strategic_topics(self):
        """Test that meeting is recommended for strategic topics."""
        confirmations = [
            {"title": "Budget alignment", "priority": "medium", "why": "Need budget approval"},
        ]

        method, reason = _decide_outreach_method(confirmations)

        assert method == "meeting"
        assert "Strategic" in reason

    def test_email_for_simple_items(self):
        """Test that email is recommended for simple items."""
        confirmations = [
            {"title": "Clarify field name", "priority": "low", "why": "Minor detail"},
        ]

        method, reason = _decide_outreach_method(confirmations)

        assert method == "email"
        assert "asynchronously" in reason


class TestGenerateEmailDraft:
    def test_generate_email_single_item(self):
        """Test generating email draft for single item."""
        confirmations = [
            {
                "title": "Clarify user role",
                "ask": "What user roles should we support?",
            }
        ]

        subject, message = _generate_email_draft(confirmations)

        assert "1 item" in subject
        assert "Clarify user role" in message
        assert "What user roles should we support?" in message

    def test_generate_email_multiple_items(self):
        """Test generating email draft for multiple items."""
        confirmations = [
            {"title": "Item 1", "ask": "Ask 1"},
            {"title": "Item 2", "ask": "Ask 2"},
        ]

        subject, message = _generate_email_draft(confirmations)

        assert "2 items" in subject
        assert "Item 1" in message
        assert "Item 2" in message
        assert "Ask 1" in message
        assert "Ask 2" in message


class TestGenerateMeetingDraft:
    def test_generate_meeting_single_item(self):
        """Test generating meeting draft for single item."""
        confirmations = [
            {
                "title": "Budget discussion",
                "ask": "What is the approved budget?",
            }
        ]

        title, agenda = _generate_meeting_draft(confirmations)

        assert "1 topic" in title
        assert "Budget discussion" in agenda
        assert "What is the approved budget?" in agenda
        assert "30 minutes" in agenda

    def test_generate_meeting_multiple_items(self):
        """Test generating meeting draft for multiple items."""
        confirmations = [
            {"title": "Topic 1", "ask": "Question 1"},
            {"title": "Topic 2", "ask": "Question 2"},
            {"title": "Topic 3", "ask": "Question 3"},
        ]

        title, agenda = _generate_meeting_draft(confirmations)

        assert "3 topics" in title
        assert "Topic 1" in agenda
        assert "Topic 2" in agenda
        assert "Topic 3" in agenda


@pytest.fixture
def mock_list_confirmations():
    """Mock list_confirmation_items."""
    with patch("app.api.outreach.list_confirmation_items") as mock:
        yield mock


class TestOutreachEndpoint:
    def test_draft_outreach_email(self, mock_list_confirmations):
        """Test drafting email outreach."""
        project_id = uuid4()

        mock_list_confirmations.return_value = [
            {
                "key": "prd:constraints:1",
                "title": "Clarify constraint",
                "ask": "What is the constraint?",
                "priority": "low",
            }
        ]

        response = client.post(
            "/v1/outreach/draft",
            json={"project_id": str(project_id)},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["recommended_method"] == "email"
        assert "reason" in data
        assert "goal" in data
        assert len(data["needs"]) == 1
        assert "subject" in data
        assert "message" in data

    def test_draft_outreach_meeting(self, mock_list_confirmations):
        """Test drafting meeting outreach."""
        project_id = uuid4()

        mock_list_confirmations.return_value = [
            {"key": "item1", "title": "Item 1", "ask": "Ask 1", "priority": "high"},
            {"key": "item2", "title": "Item 2", "ask": "Ask 2", "priority": "medium"},
            {"key": "item3", "title": "Item 3", "ask": "Ask 3", "priority": "medium"},
        ]

        response = client.post(
            "/v1/outreach/draft",
            json={"project_id": str(project_id)},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["recommended_method"] == "meeting"
        assert len(data["needs"]) == 3

    def test_draft_outreach_no_items(self, mock_list_confirmations):
        """Test drafting outreach with no open items."""
        project_id = uuid4()

        mock_list_confirmations.return_value = []

        response = client.post(
            "/v1/outreach/draft",
            json={"project_id": str(project_id)},
        )

        assert response.status_code == 400
        assert "No open confirmation items" in response.json()["detail"]

