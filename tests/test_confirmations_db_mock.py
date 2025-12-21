"""Tests for confirmation items database operations with mocked Supabase."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.db.confirmations import (
    get_confirmation_item,
    list_confirmation_items,
    set_confirmation_status,
    upsert_confirmation_item,
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("app.db.confirmations.get_supabase") as mock:
        yield mock.return_value


class TestUpsertConfirmationItem:
    def test_upsert_new_item(self, mock_supabase):
        """Test upserting a new confirmation item."""
        project_id = uuid4()
        key = "prd:constraints:ai_boundary"
        payload = {
            "kind": "prd",
            "title": "AI boundary clarification",
            "why": "Need to understand scope",
            "ask": "What AI features are in scope?",
            "priority": "high",
            "suggested_method": "meeting",
            "evidence": [],
            "created_from": {},
        }

        expected_item = {
            "id": str(uuid4()),
            "project_id": str(project_id),
            "key": key,
            **payload,
        }

        mock_response = MagicMock()
        mock_response.data = [expected_item]
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

        result = upsert_confirmation_item(project_id, key, payload)

        assert result == expected_item
        mock_supabase.table.assert_called_once_with("confirmation_items")

    def test_upsert_existing_item(self, mock_supabase):
        """Test upserting an existing confirmation item (update)."""
        project_id = uuid4()
        key = "prd:constraints:ai_boundary"
        existing_id = uuid4()
        payload = {
            "kind": "prd",
            "title": "Updated title",
            "why": "Updated reason",
            "ask": "Updated ask",
            "priority": "medium",
            "suggested_method": "email",
            "evidence": [],
            "created_from": {},
        }

        expected_item = {
            "id": str(existing_id),
            "project_id": str(project_id),
            "key": key,
            **payload,
        }

        mock_response = MagicMock()
        mock_response.data = [expected_item]
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

        result = upsert_confirmation_item(project_id, key, payload)

        assert result["id"] == str(existing_id)
        assert result["title"] == "Updated title"


class TestListConfirmationItems:
    def test_list_all_items(self, mock_supabase):
        """Test listing all confirmation items."""
        project_id = uuid4()
        items = [
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "key": "prd:constraints:1",
                "status": "open",
            },
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "key": "prd:constraints:2",
                "status": "queued",
            },
        ]

        mock_response = MagicMock()
        mock_response.data = items
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_response
        )

        result = list_confirmation_items(project_id)

        assert len(result) == 2
        assert result == items

    def test_list_items_by_status(self, mock_supabase):
        """Test listing confirmation items filtered by status."""
        project_id = uuid4()
        items = [
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "key": "prd:constraints:1",
                "status": "open",
            },
        ]

        mock_response = MagicMock()
        mock_response.data = items
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_response
        )

        result = list_confirmation_items(project_id, status="open")

        assert len(result) == 1
        assert result[0]["status"] == "open"


class TestSetConfirmationStatus:
    def test_set_status_to_resolved(self, mock_supabase):
        """Test setting confirmation status to resolved."""
        confirmation_id = uuid4()
        resolution_evidence = {
            "type": "email",
            "ref": "Email from client on 2024-01-01",
            "note": "Client confirmed via email",
        }

        expected_item = {
            "id": str(confirmation_id),
            "status": "resolved",
            "resolution_evidence": resolution_evidence,
        }

        mock_response = MagicMock()
        mock_response.data = [expected_item]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = set_confirmation_status(confirmation_id, "resolved", resolution_evidence)

        assert result["status"] == "resolved"
        assert result["resolution_evidence"] == resolution_evidence

    def test_set_status_to_dismissed(self, mock_supabase):
        """Test setting confirmation status to dismissed."""
        confirmation_id = uuid4()

        expected_item = {
            "id": str(confirmation_id),
            "status": "dismissed",
        }

        mock_response = MagicMock()
        mock_response.data = [expected_item]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = set_confirmation_status(confirmation_id, "dismissed")

        assert result["status"] == "dismissed"


class TestGetConfirmationItem:
    def test_get_existing_item(self, mock_supabase):
        """Test getting an existing confirmation item."""
        confirmation_id = uuid4()
        expected_item = {
            "id": str(confirmation_id),
            "key": "prd:constraints:1",
            "status": "open",
        }

        mock_response = MagicMock()
        mock_response.data = [expected_item]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = get_confirmation_item(confirmation_id)

        assert result == expected_item

    def test_get_nonexistent_item(self, mock_supabase):
        """Test getting a nonexistent confirmation item."""
        confirmation_id = uuid4()

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = get_confirmation_item(confirmation_id)

        assert result is None

