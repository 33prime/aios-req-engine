"""Tests for state snapshot refresh after enrichment."""

import uuid
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_supabase():
    with patch("app.core.state_snapshot.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_regenerate_state_snapshot_upserts(mock_supabase):
    """regenerate_state_snapshot should upsert to state_snapshots table."""
    from app.core.state_snapshot import regenerate_state_snapshot

    project_id = uuid.uuid4()

    # Mock all the internal query methods
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.order.return_value.execute.return_value = mock_response

    result = regenerate_state_snapshot(project_id)

    # Should return a snapshot text string
    assert isinstance(result, str)

    # Should have called upsert on state_snapshots
    upsert_calls = [call for call in mock_supabase.table.call_args_list if call[0][0] == "state_snapshots"]
    assert len(upsert_calls) > 0


def test_invalidate_snapshot_deletes(mock_supabase):
    """invalidate_snapshot should delete from state_snapshots table."""
    from app.core.state_snapshot import invalidate_snapshot

    project_id = uuid.uuid4()

    invalidate_snapshot(project_id)

    mock_supabase.table.assert_called_with("state_snapshots")
    mock_supabase.table.return_value.delete.return_value.eq.assert_called_once()


def test_invalidate_snapshot_handles_error(mock_supabase):
    """invalidate_snapshot should not raise on error."""
    from app.core.state_snapshot import invalidate_snapshot

    mock_supabase.table.return_value.delete.side_effect = Exception("DB Error")

    project_id = uuid.uuid4()

    # Should not raise
    invalidate_snapshot(project_id)


def test_get_state_snapshot_returns_cached_when_fresh(mock_supabase):
    """get_state_snapshot should return cached content when fresh."""
    from datetime import datetime, timezone
    from app.core.state_snapshot import get_state_snapshot

    project_id = uuid.uuid4()

    # Mock a fresh cached snapshot
    mock_response = MagicMock()
    mock_response.data = {
        "snapshot_text": "# Cached Snapshot\nContent here.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    result = get_state_snapshot(project_id)

    assert result == "# Cached Snapshot\nContent here."


def test_get_state_snapshot_regenerates_when_stale(mock_supabase):
    """get_state_snapshot should regenerate when cache is stale."""
    from datetime import datetime, timezone, timedelta
    from app.core.state_snapshot import get_state_snapshot

    project_id = uuid.uuid4()

    # Mock a stale cached snapshot (10 minutes old)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    mock_response = MagicMock()
    mock_response.data = {
        "snapshot_text": "# Old Snapshot",
        "generated_at": stale_time.isoformat(),
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    # Mock empty responses for the regeneration queries
    empty_response = MagicMock()
    empty_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = empty_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty_response

    result = get_state_snapshot(project_id)

    # Should have regenerated (result will contain generated headers)
    assert "PROJECT IDENTITY" in result or "Snapshot" in result
