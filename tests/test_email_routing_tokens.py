"""Tests for email routing token validation logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4


class TestValidateToken:
    """Tests for token validation logic."""

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_invalid_token_returns_false(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        mock_get.return_value = None
        is_valid, reason, record = validate_token("nonexistent", "user@example.com")
        assert is_valid is False
        assert "not found" in reason.lower()

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_expired_token_returns_false(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        expired_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": expired_time,
            "is_active": True,
            "emails_received": 0,
            "max_emails": 100,
            "allowed_sender_domain": None,
            "allowed_sender_emails": [],
        }

        is_valid, reason, record = validate_token("test-token", "user@example.com")
        assert is_valid is False
        assert "expired" in reason.lower()

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_rate_limited_token_returns_false(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": future,
            "is_active": True,
            "emails_received": 100,
            "max_emails": 100,
            "allowed_sender_domain": None,
            "allowed_sender_emails": [],
        }

        is_valid, reason, record = validate_token("test-token", "user@example.com")
        assert is_valid is False
        assert "rate limit" in reason.lower()

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_wrong_sender_domain_returns_false(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": future,
            "is_active": True,
            "emails_received": 5,
            "max_emails": 100,
            "allowed_sender_domain": "acme.com",
            "allowed_sender_emails": [],
        }

        is_valid, reason, record = validate_token("test-token", "user@evil.com")
        assert is_valid is False
        assert "domain" in reason.lower()

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_wrong_sender_email_returns_false(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": future,
            "is_active": True,
            "emails_received": 5,
            "max_emails": 100,
            "allowed_sender_domain": None,
            "allowed_sender_emails": ["allowed@example.com"],
        }

        is_valid, reason, record = validate_token("test-token", "other@example.com")
        assert is_valid is False
        assert "allowlist" in reason.lower()

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_valid_token_returns_true(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": future,
            "is_active": True,
            "emails_received": 5,
            "max_emails": 100,
            "allowed_sender_domain": None,
            "allowed_sender_emails": [],
        }

        is_valid, reason, record = validate_token("test-token", "user@example.com")
        assert is_valid is True
        assert reason == "Valid"
        assert record is not None

    @patch("app.db.email_routing_tokens.get_token_by_value")
    def test_valid_with_matching_domain(self, mock_get):
        from app.db.email_routing_tokens import validate_token

        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_get.return_value = {
            "id": str(uuid4()),
            "token": "test-token",
            "expires_at": future,
            "is_active": True,
            "emails_received": 0,
            "max_emails": 100,
            "allowed_sender_domain": "acme.com",
            "allowed_sender_emails": [],
        }

        is_valid, reason, record = validate_token("test-token", "ceo@acme.com")
        assert is_valid is True
