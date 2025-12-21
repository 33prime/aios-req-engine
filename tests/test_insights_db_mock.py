"""Tests for insights database operations with mocked Supabase."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.db.insights.get_supabase") as mock_get_supabase:
        mock_client = MagicMock()
        mock_get_supabase.return_value = mock_client
        yield mock_client


class TestInsertInsights:
    def test_insert_single_insight(self, mock_supabase):
        from app.db.insights import insert_insights

        project_id = uuid4()
        run_id = uuid4()
        job_id = uuid4()

        insights = [
            {
                "severity": "important",
                "category": "security",
                "title": "Test insight",
                "finding": "Something is wrong",
                "why": "It could cause problems",
                "suggested_action": "needs_confirmation",
                "targets": [],
                "evidence": [{"chunk_id": str(uuid4()), "excerpt": "quote", "rationale": "reason"}],
            }
        ]

        source = {
            "agent": "red_team",
            "model": "gpt-4o-mini",
            "prompt_version": "redteam_v1",
            "schema_version": "redteam_v1",
        }

        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        count = insert_insights(project_id, run_id, job_id, insights, source)

        assert count == 1
        mock_supabase.table.assert_called_with("insights")
        mock_supabase.table.return_value.insert.assert_called_once()

        # Verify the inserted data structure
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_rows = call_args[0][0]
        assert len(inserted_rows) == 1
        assert inserted_rows[0]["status"] == "open"
        assert inserted_rows[0]["source"] == source

    def test_insert_multiple_insights(self, mock_supabase):
        from app.db.insights import insert_insights

        project_id = uuid4()
        run_id = uuid4()
        job_id = uuid4()

        insights = [
            {
                "severity": "minor",
                "category": "ux",
                "title": "Insight 1",
                "finding": "F1",
                "why": "W1",
                "suggested_action": "apply_internally",
                "targets": [],
                "evidence": [{"chunk_id": str(uuid4()), "excerpt": "q1", "rationale": "r1"}],
            },
            {
                "severity": "critical",
                "category": "data",
                "title": "Insight 2",
                "finding": "F2",
                "why": "W2",
                "suggested_action": "needs_confirmation",
                "targets": [],
                "evidence": [{"chunk_id": str(uuid4()), "excerpt": "q2", "rationale": "r2"}],
            },
        ]

        source = {"agent": "red_team"}

        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}, {"id": str(uuid4())}]
        )

        count = insert_insights(project_id, run_id, job_id, insights, source)

        assert count == 2

    def test_insert_empty_insights(self, mock_supabase):
        from app.db.insights import insert_insights

        project_id = uuid4()
        run_id = uuid4()
        job_id = uuid4()

        count = insert_insights(project_id, run_id, job_id, [], {})

        assert count == 0
        mock_supabase.table.return_value.insert.assert_not_called()


class TestUpdateInsightStatus:
    def test_update_status_success(self, mock_supabase):
        from app.db.insights import update_insight_status

        insight_id = uuid4()
        mock_update = mock_supabase.table.return_value.update.return_value
        mock_update.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": str(insight_id), "status": "applied"}]
        )

        update_insight_status(insight_id, "applied")

        mock_supabase.table.assert_called_with("insights")
        mock_supabase.table.return_value.update.assert_called_once_with({"status": "applied"})

    def test_update_status_not_found(self, mock_supabase):
        from app.db.insights import update_insight_status

        insight_id = uuid4()
        mock_update = mock_supabase.table.return_value.update.return_value
        mock_update.eq.return_value.execute.return_value = MagicMock(data=[])

        with pytest.raises(ValueError, match="Insight not found"):
            update_insight_status(insight_id, "dismissed")

    def test_update_status_invalid(self, mock_supabase):
        from app.db.insights import update_insight_status

        insight_id = uuid4()

        with pytest.raises(ValueError, match="Invalid status"):
            update_insight_status(insight_id, "invalid_status")


class TestListInsights:
    def test_list_insights_all(self, mock_supabase):
        from app.db.insights import list_insights

        project_id = uuid4()

        mock_insights = [
            {"id": str(uuid4()), "status": "open", "title": "Insight 1"},
            {"id": str(uuid4()), "status": "applied", "title": "Insight 2"},
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (  # noqa: E501
            MagicMock(data=mock_insights)
        )

        results = list_insights(project_id)

        assert len(results) == 2
        mock_supabase.table.assert_called_with("insights")

    def test_list_insights_with_status_filter(self, mock_supabase):
        from app.db.insights import list_insights

        project_id = uuid4()

        mock_insights = [
            {"id": str(uuid4()), "status": "open", "title": "Open Insight"},
        ]

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=mock_insights)

        mock_supabase.table.return_value.select.return_value = mock_query

        results = list_insights(project_id, status="open")

        assert len(results) == 1

    def test_list_insights_with_limit(self, mock_supabase):
        from app.db.insights import list_insights

        project_id = uuid4()

        mock_insights = [{"id": str(uuid4()), "status": "open", "title": "Single"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (  # noqa: E501
            MagicMock(data=mock_insights)
        )

        results = list_insights(project_id, limit=1)

        assert len(results) == 1
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.assert_called_with(  # noqa: E501
            1
        )

    def test_list_insights_empty(self, mock_supabase):
        from app.db.insights import list_insights

        project_id = uuid4()

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (  # noqa: E501
            MagicMock(data=[])
        )

        results = list_insights(project_id)

        assert results == []
