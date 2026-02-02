"""Tests for prototype database access layer."""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    return mock


@pytest.fixture
def sample_prototype():
    """Sample prototype record."""
    return {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "repo_url": "https://github.com/test/proto",
        "deploy_url": "https://proto.vercel.app",
        "local_path": "/tmp/aios-prototypes/test",
        "handoff_parsed": {"features": []},
        "status": "pending",
        "prompt_text": "Generate a prototype...",
        "prompt_audit": None,
        "prompt_version": 1,
        "session_count": 0,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


class TestCreatePrototype:
    """Tests for create_prototype."""

    def test_creates_prototype_with_required_fields(self, mock_supabase, sample_prototype):
        """Test that a prototype is created with project_id."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            sample_prototype
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import create_prototype

            result = create_prototype(project_id=UUID(sample_prototype["project_id"]))

            assert result["id"] == sample_prototype["id"]
            mock_supabase.table.assert_called_with("prototypes")

    def test_creates_prototype_with_optional_fields(self, mock_supabase, sample_prototype):
        """Test prototype creation with repo_url and deploy_url."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            sample_prototype
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import create_prototype

            result = create_prototype(
                project_id=UUID(sample_prototype["project_id"]),
                repo_url="https://github.com/test/proto",
                deploy_url="https://proto.vercel.app",
                prompt_text="Generate...",
            )

            assert result["id"] == sample_prototype["id"]
            call_args = mock_supabase.table.return_value.insert.call_args[0][0]
            assert call_args["repo_url"] == "https://github.com/test/proto"
            assert call_args["deploy_url"] == "https://proto.vercel.app"
            assert call_args["prompt_text"] == "Generate..."

    def test_raises_on_empty_response(self, mock_supabase):
        """Test that ValueError is raised when no data is returned."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import create_prototype

            with pytest.raises(ValueError, match="Failed to create prototype"):
                create_prototype(project_id=uuid4())


class TestGetPrototype:
    """Tests for get_prototype."""

    def test_returns_prototype_when_found(self, mock_supabase, sample_prototype):
        """Test fetching a prototype by ID."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            sample_prototype
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import get_prototype

            result = get_prototype(UUID(sample_prototype["id"]))

            assert result is not None
            assert result["id"] == sample_prototype["id"]

    def test_returns_none_when_not_found(self, mock_supabase):
        """Test that None is returned for non-existent prototype."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import get_prototype

            result = get_prototype(uuid4())
            assert result is None


class TestListOverlays:
    """Tests for list_overlays."""

    def test_returns_overlays_for_prototype(self, mock_supabase):
        """Test listing overlays for a prototype."""
        overlays = [
            {"id": str(uuid4()), "status": "understood", "confidence": 0.9},
            {"id": str(uuid4()), "status": "partial", "confidence": 0.6},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
            overlays
        )
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import list_overlays

            result = list_overlays(uuid4())
            assert len(result) == 2
            assert result[0]["status"] == "understood"

    def test_returns_empty_list_when_no_overlays(self, mock_supabase):
        """Test empty list when no overlays exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = None
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import list_overlays

            result = list_overlays(uuid4())
            assert result == []


class TestUpsertOverlay:
    """Tests for upsert_overlay."""

    def test_creates_new_overlay(self, mock_supabase):
        """Test creating a new overlay when none exists."""
        overlay_id = str(uuid4())
        # get_overlay_for_feature returns empty list (no existing)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        # insert succeeds
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": overlay_id, "status": "partial"}
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import upsert_overlay

            result = upsert_overlay(
                prototype_id=uuid4(),
                feature_id=uuid4(),
                analysis={"triggers": []},
                overlay_content={"feature_name": "Login"},
                status="partial",
                confidence=0.6,
            )
            assert result["id"] == overlay_id


class TestCreateQuestion:
    """Tests for create_question."""

    def test_creates_question(self, mock_supabase):
        """Test creating a question for an overlay."""
        question_id = str(uuid4())
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": question_id, "question": "What is the password policy?"}
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import create_question

            result = create_question(
                overlay_id=uuid4(),
                question="What is the password policy?",
                category="business_rules",
                priority="high",
            )
            assert result["id"] == question_id


class TestAnswerQuestion:
    """Tests for answer_question."""

    def test_records_answer(self, mock_supabase):
        """Test recording an answer to a question."""
        question_id = uuid4()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(question_id), "answer": "8+ chars", "answered_by": "consultant"}
        ]
        with patch("app.db.prototypes.get_supabase", return_value=mock_supabase):
            from app.db.prototypes import answer_question

            result = answer_question(
                question_id=question_id,
                answer="8+ chars",
                session_number=1,
                answered_by="consultant",
            )
            assert result["answer"] == "8+ chars"
            assert result["answered_by"] == "consultant"
