"""Tests for confirmations PATCH endpoint."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from app.db.confirmations import set_confirmation_status


def test_set_confirmation_status():
    """Test updating confirmation status."""
    confirmation_id = uuid4()
    new_status = "resolved"
    resolution_evidence = {
        "type": "email",
        "ref": "approved",
        "note": "Consultant approved"
    }

    mock_updated_confirmation = {
        "id": str(confirmation_id),
        "status": new_status,
        "resolution_evidence": resolution_evidence
    }

    with patch("app.db.confirmations.get_supabase") as mock_supabase:
        mock_response = {"data": [mock_updated_confirmation]}
        mock_supabase.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = set_confirmation_status(confirmation_id, new_status, resolution_evidence)

        assert result == mock_updated_confirmation
        # Verify the update was called with correct data
        update_call = mock_supabase.return_value.table.return_value.update
        update_call.assert_called_once()
        call_args = update_call.call_args[0][0]
        assert call_args["status"] == new_status
        assert call_args["resolution_evidence"] == resolution_evidence
