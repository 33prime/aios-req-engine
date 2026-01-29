"""Unit tests for memory knowledge graph operations.

Tests CRUD operations for nodes, edges, beliefs, and synthesis logging.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def project_id():
    """Sample project UUID."""
    return uuid4()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.maybe_single.return_value = mock
    mock.single.return_value = mock
    return mock


@pytest.fixture
def sample_fact():
    """Sample fact node data."""
    return {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "node_type": "fact",
        "content": "Client CTO mentioned Q2 compliance deadline in email",
        "summary": "Q2 compliance deadline mentioned",
        "confidence": 1.0,
        "is_active": True,
        "source_type": "signal",
        "source_id": str(uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_belief():
    """Sample belief node data."""
    return {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "node_type": "belief",
        "content": "The primary business driver is regulatory compliance",
        "summary": "Primary driver: compliance",
        "confidence": 0.75,
        "is_active": True,
        "source_type": "synthesis",
        "belief_domain": "client_priority",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_insight():
    """Sample insight node data."""
    return {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "node_type": "insight",
        "content": "Client's stated priorities differ from actual behavior",
        "summary": "Stated vs actual priority mismatch",
        "confidence": 0.7,
        "is_active": True,
        "source_type": "reflection",
        "insight_type": "behavioral",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_edge():
    """Sample edge data."""
    return {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "from_node_id": str(uuid4()),
        "to_node_id": str(uuid4()),
        "edge_type": "supports",
        "strength": 1.0,
        "rationale": "Fact directly supports belief",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Node CRUD Tests
# =============================================================================


class TestCreateNode:
    """Tests for create_node function."""

    def test_create_fact_node(self, project_id, mock_supabase, sample_fact):
        """Test creating a fact node."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_fact])

            from app.db.memory_graph import create_node

            result = create_node(
                project_id=project_id,
                node_type="fact",
                content="Test fact content",
                summary="Test fact",
                source_type="signal",
            )

            # Verify insert was called
            mock_supabase.table.assert_called_with("memory_nodes")
            mock_supabase.insert.assert_called_once()

            # Check the inserted data
            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["node_type"] == "fact"
            assert call_args["confidence"] == 1.0  # Facts always have confidence 1.0

    def test_create_belief_node(self, project_id, mock_supabase, sample_belief):
        """Test creating a belief node with custom confidence."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_belief])

            from app.db.memory_graph import create_node

            result = create_node(
                project_id=project_id,
                node_type="belief",
                content="Test belief content",
                summary="Test belief",
                confidence=0.75,
                belief_domain="client_priority",
            )

            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["node_type"] == "belief"
            assert call_args["confidence"] == 0.75
            assert call_args["belief_domain"] == "client_priority"

    def test_create_insight_node(self, project_id, mock_supabase, sample_insight):
        """Test creating an insight node."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_insight])

            from app.db.memory_graph import create_node

            result = create_node(
                project_id=project_id,
                node_type="insight",
                content="Test insight content",
                summary="Test insight",
                confidence=0.7,
                insight_type="behavioral",
            )

            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["node_type"] == "insight"
            assert call_args["insight_type"] == "behavioral"

    def test_create_node_with_entity_link(self, project_id, mock_supabase, sample_fact):
        """Test creating a node linked to an entity."""
        entity_id = uuid4()
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_fact])

            from app.db.memory_graph import create_node

            result = create_node(
                project_id=project_id,
                node_type="fact",
                content="Feature X was mentioned",
                summary="Feature mentioned",
                linked_entity_type="feature",
                linked_entity_id=entity_id,
            )

            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["linked_entity_type"] == "feature"
            assert call_args["linked_entity_id"] == str(entity_id)


class TestGetNodes:
    """Tests for node retrieval functions."""

    def test_get_node_by_id(self, mock_supabase, sample_fact):
        """Test getting a single node by ID."""
        node_id = uuid4()
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=sample_fact)

            from app.db.memory_graph import get_node

            result = get_node(node_id)

            mock_supabase.table.assert_called_with("memory_nodes")
            mock_supabase.eq.assert_called_with("id", str(node_id))

    def test_get_active_beliefs(self, project_id, mock_supabase, sample_belief):
        """Test getting active beliefs ordered by confidence."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_belief])

            from app.db.memory_graph import get_active_beliefs

            result = get_active_beliefs(project_id, limit=10, min_confidence=0.5)

            # Verify query includes correct filters
            mock_supabase.eq.assert_any_call("project_id", str(project_id))
            mock_supabase.eq.assert_any_call("node_type", "belief")
            mock_supabase.eq.assert_any_call("is_active", True)
            mock_supabase.gte.assert_called_with("confidence", 0.5)
            mock_supabase.order.assert_called_with("confidence", desc=True)

    def test_get_recent_facts(self, project_id, mock_supabase, sample_fact):
        """Test getting recent facts."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_fact])

            from app.db.memory_graph import get_recent_facts

            result = get_recent_facts(project_id, limit=5)

            mock_supabase.eq.assert_any_call("node_type", "fact")
            mock_supabase.order.assert_called_with("created_at", desc=True)

    def test_get_insights(self, project_id, mock_supabase, sample_insight):
        """Test getting insights."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_insight])

            from app.db.memory_graph import get_insights

            result = get_insights(project_id, insight_type="behavioral")

            mock_supabase.eq.assert_any_call("node_type", "insight")
            mock_supabase.eq.assert_any_call("insight_type", "behavioral")


class TestArchiveNode:
    """Tests for archive_node function."""

    def test_archive_node(self, mock_supabase, sample_belief):
        """Test archiving a node."""
        node_id = uuid4()
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_belief])

            from app.db.memory_graph import archive_node

            result = archive_node(node_id, "Low confidence, no recent evidence")

            # Verify update was called with correct fields
            mock_supabase.update.assert_called_once()
            call_args = mock_supabase.update.call_args[0][0]
            assert call_args["is_active"] is False
            assert call_args["archive_reason"] == "Low confidence, no recent evidence"
            assert "archived_at" in call_args


# =============================================================================
# Belief Operations Tests
# =============================================================================


class TestBeliefOperations:
    """Tests for belief-specific operations."""

    def test_update_belief_confidence_increase(self, mock_supabase, sample_belief):
        """Test increasing belief confidence."""
        node_id = uuid4()
        sample_belief["id"] = str(node_id)

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            with patch("app.db.memory_graph.get_node", return_value=sample_belief):
                mock_supabase.execute.return_value = MagicMock(data=[sample_belief])

                from app.db.memory_graph import update_belief_confidence

                result = update_belief_confidence(
                    node_id=node_id,
                    new_confidence=0.85,
                    change_reason="New supporting evidence found",
                )

                # Verify update was called
                mock_supabase.update.assert_called()
                call_args = mock_supabase.update.call_args[0][0]
                assert call_args["confidence"] == 0.85

    def test_update_belief_content(self, mock_supabase, sample_belief):
        """Test updating belief content."""
        node_id = uuid4()
        sample_belief["id"] = str(node_id)

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            with patch("app.db.memory_graph.get_node", return_value=sample_belief):
                mock_supabase.execute.return_value = MagicMock(data=[sample_belief])

                from app.db.memory_graph import update_belief_content

                result = update_belief_content(
                    node_id=node_id,
                    new_content="Updated belief content",
                    new_summary="Updated belief",
                    new_confidence=0.8,
                    change_reason="Refined understanding based on new data",
                )

                # Verify update includes all fields
                call_args = mock_supabase.update.call_args[0][0]
                assert call_args["content"] == "Updated belief content"
                assert call_args["summary"] == "Updated belief"
                assert call_args["confidence"] == 0.8

    def test_update_non_belief_raises_error(self, mock_supabase, sample_fact):
        """Test that updating confidence on non-belief raises error."""
        node_id = uuid4()
        sample_fact["id"] = str(node_id)

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            with patch("app.db.memory_graph.get_node", return_value=sample_fact):
                from app.db.memory_graph import update_belief_confidence

                with pytest.raises(ValueError, match="not a belief"):
                    update_belief_confidence(
                        node_id=node_id,
                        new_confidence=0.5,
                        change_reason="Should fail",
                    )


# =============================================================================
# Edge Operations Tests
# =============================================================================


class TestEdgeOperations:
    """Tests for edge operations."""

    def test_create_edge(self, project_id, mock_supabase, sample_edge):
        """Test creating an edge between nodes."""
        from_id = uuid4()
        to_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_edge])

            from app.db.memory_graph import create_edge

            result = create_edge(
                project_id=project_id,
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type="supports",
                rationale="Fact supports belief",
            )

            mock_supabase.table.assert_called_with("memory_edges")
            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["from_node_id"] == str(from_id)
            assert call_args["to_node_id"] == str(to_id)
            assert call_args["edge_type"] == "supports"

    def test_get_edges_from_node(self, mock_supabase, sample_edge):
        """Test getting edges originating from a node."""
        node_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_edge])

            from app.db.memory_graph import get_edges_from_node

            result = get_edges_from_node(node_id, edge_type="supports")

            mock_supabase.eq.assert_any_call("from_node_id", str(node_id))
            mock_supabase.eq.assert_any_call("edge_type", "supports")

    def test_get_edges_to_node(self, mock_supabase, sample_edge):
        """Test getting edges pointing to a node."""
        node_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_edge])

            from app.db.memory_graph import get_edges_to_node

            result = get_edges_to_node(node_id)

            mock_supabase.eq.assert_called_with("to_node_id", str(node_id))

    def test_count_edges_to_node(self, mock_supabase, sample_edge):
        """Test counting edges to a node."""
        node_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[sample_edge, sample_edge])

            from app.db.memory_graph import count_edges_to_node

            result = count_edges_to_node(node_id)
            assert result == 2


# =============================================================================
# Synthesis Logging Tests
# =============================================================================


class TestSynthesisLogging:
    """Tests for synthesis log operations."""

    def test_start_synthesis_log(self, project_id, mock_supabase):
        """Test starting a synthesis log entry."""
        log_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[{"id": str(log_id)}])

            from app.db.memory_graph import start_synthesis_log

            result = start_synthesis_log(
                project_id=project_id,
                synthesis_type="watcher",
                trigger_type="signal_processed",
                input_facts_count=5,
            )

            mock_supabase.table.assert_called_with("memory_synthesis_log")
            call_args = mock_supabase.insert.call_args[0][0]
            assert call_args["synthesis_type"] == "watcher"
            assert call_args["trigger_type"] == "signal_processed"
            assert call_args["status"] == "running"

    def test_complete_synthesis_log(self, mock_supabase):
        """Test completing a synthesis log entry."""
        log_id = uuid4()
        started_at = datetime.utcnow() - timedelta(seconds=5)

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[{"id": str(log_id)}])

            from app.db.memory_graph import complete_synthesis_log

            result = complete_synthesis_log(
                log_id=log_id,
                facts_created=3,
                beliefs_created=1,
                edges_created=4,
                tokens_input=500,
                tokens_output=200,
                model_used="claude-3-5-haiku-20241022",
                started_at=started_at,
            )

            call_args = mock_supabase.update.call_args[0][0]
            assert call_args["facts_created"] == 3
            assert call_args["beliefs_created"] == 1
            assert call_args["status"] == "completed"
            assert call_args["duration_ms"] is not None

    def test_fail_synthesis_log(self, mock_supabase):
        """Test marking a synthesis log as failed."""
        log_id = uuid4()

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[{"id": str(log_id)}])

            from app.db.memory_graph import fail_synthesis_log

            result = fail_synthesis_log(log_id, "Test error message")

            call_args = mock_supabase.update.call_args[0][0]
            assert call_args["status"] == "failed"
            assert call_args["error_message"] == "Test error message"


# =============================================================================
# Archival / Maintenance Tests
# =============================================================================


class TestArchivalOperations:
    """Tests for archival and maintenance operations."""

    def test_get_graph_stats(self, project_id, mock_supabase, sample_fact, sample_belief, sample_insight):
        """Test getting graph statistics."""
        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            # Mock get_nodes to return mixed node types
            nodes = [sample_fact, sample_belief, sample_insight]

            with patch("app.db.memory_graph.get_nodes", return_value=nodes):
                with patch("app.db.memory_graph.get_all_edges", return_value=[]):
                    from app.db.memory_graph import get_graph_stats

                    stats = get_graph_stats(project_id)

                    assert stats["total_nodes"] == 3
                    assert stats["facts_count"] == 1
                    assert stats["beliefs_count"] == 1
                    assert stats["insights_count"] == 1
