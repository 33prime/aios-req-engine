"""Tests for consent service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.consent_service import check_consent_status, handle_opt_out


class TestCheckConsentStatus:
    def test_returns_pending_when_no_bot(self):
        with patch("app.db.meeting_bots.get_bot", return_value=None):
            result = check_consent_status(uuid4())
        assert result == "pending"

    @patch("app.db.meeting_bots.get_bot")
    def test_returns_opted_out_when_participant_opted_out(self, mock_get):
        mock_get.return_value = {
            "id": str(uuid4()),
            "participants_opted_out": ["user@example.com"],
            "opt_out_deadline": None,
            "consent_status": "opted_out",
        }
        result = check_consent_status(uuid4())
        assert result == "opted_out"

    @patch("app.db.meeting_bots.get_bot")
    def test_returns_all_consented_after_deadline(self, mock_get):
        past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "participants_opted_out": [],
            "opt_out_deadline": past,
            "consent_status": "pending",
        }
        result = check_consent_status(uuid4())
        assert result == "all_consented"

    @patch("app.db.meeting_bots.get_bot")
    def test_returns_pending_before_deadline(self, mock_get):
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "participants_opted_out": [],
            "opt_out_deadline": future,
            "consent_status": "pending",
        }
        result = check_consent_status(uuid4())
        assert result == "pending"


class TestHandleOptOut:
    @pytest.mark.asyncio
    @patch("app.core.sendgrid_service.send_opt_out_confirmation", new_callable=AsyncMock)
    @patch("app.core.recall_service.remove_bot", new_callable=AsyncMock)
    @patch("app.db.meeting_bots.add_opt_out")
    @patch("app.db.meeting_bots.get_bot_by_recall_id")
    @patch("app.db.meetings.get_meeting")
    async def test_opt_out_cancels_bot(
        self, mock_meeting, mock_get_bot, mock_add_opt_out, mock_remove, mock_send
    ):
        bot_id = str(uuid4())
        meeting_id = str(uuid4())

        mock_get_bot.return_value = {
            "id": bot_id,
            "meeting_id": meeting_id,
            "recall_bot_id": "recall-123",
            "status": "joining",
            "consent_status": "pending",
        }
        mock_meeting.return_value = {"title": "Test Meeting"}
        mock_add_opt_out.return_value = {"status": "cancelled"}
        mock_remove.return_value = True
        mock_send.return_value = {"sent": True}

        result = await handle_opt_out("recall-123", "user@example.com")

        assert result is True
        mock_add_opt_out.assert_called_once()
        mock_remove.assert_called_once_with("recall-123")

    @pytest.mark.asyncio
    @patch("app.db.meeting_bots.get_bot_by_recall_id")
    async def test_opt_out_returns_false_for_unknown_bot(self, mock_get_bot):
        mock_get_bot.return_value = None

        result = await handle_opt_out("unknown-bot", "user@example.com")
        assert result is False
