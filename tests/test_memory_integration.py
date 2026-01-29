"""Integration tests for the Memory System.

Tests the full flow from signal processing through memory agent to rendering.
These tests mock external services but test the integration between components.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
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
def signal_id():
    """Sample signal UUID."""
    return uuid4()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for integration tests."""
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
def mock_anthropic_watcher():
    """Mock Anthropic response for watcher."""
    response = {
        "facts": [
            {
                "content": "CTO mentioned Q2 compliance deadline is critical",
                "summary": "Q2 compliance deadline critical"
            }
        ],
        "importance": 0.75,
        "contradicts_beliefs": [],
        "confirms_beliefs": [],
        "is_milestone": False,
        "rationale": "New information about deadline urgency"
    }
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(response))]
    mock.usage = MagicMock(input_tokens=200, output_tokens=100)
    return mock


@pytest.fixture
def mock_anthropic_synthesizer():
    """Mock Anthropic response for synthesizer."""
    response = [
        {
            "action": "create_belief",
            "content": "Q2 compliance deadline is driving immediate priorities",
            "summary": "Q2 compliance driving priorities",
            "confidence": 0.7,
            "domain": "client_priority",
            "supported_by": []
        }
    ]
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(response))]
    mock.usage = MagicMock(input_tokens=500, output_tokens=200)
    return mock


@pytest.fixture
def mock_anthropic_reflector():
    """Mock Anthropic response for reflector."""
    response = {
        "insights": [
            {
                "content": "Timeline pressure is consistently driving decisions over feature quality",
                "summary": "Timeline over quality pattern",
                "confidence": 0.72,
                "type": "behavioral",
                "supported_by": []
            }
        ]
    }
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(response))]
    mock.usage = MagicMock(input_tokens=1000, output_tokens=300)
    return mock


# =============================================================================
# Full Flow Integration Tests
# =============================================================================


class TestSignalToMemoryFlow:
    """Tests for the signal → watcher → synthesizer flow."""

    @pytest.mark.asyncio
    async def test_signal_triggers_watcher_and_synthesis(
        self,
        project_id,
        signal_id,
        mock_supabase,
        mock_anthropic_watcher,
        mock_anthropic_synthesizer,
    ):
        """Test that processing a high-importance signal triggers full memory flow."""
        created_node = {"id": str(uuid4()), "node_type": "fact"}
        created_belief = {"id": str(uuid4()), "node_type": "belief"}

        call_count = {"count": 0}

        def mock_anthropic_create(**kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return mock_anthropic_watcher
            return mock_anthropic_synthesizer

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            with patch("app.agents.memory_agent.get_active_beliefs", return_value=[]):
                with patch("app.agents.memory_agent.get_recent_facts", return_value=[]):
                    with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                        with patch("app.agents.memory_agent.get_edges_to_node", return_value=[]):
                            with patch("app.agents.memory_agent.create_node") as mock_create:
                                mock_create.side_effect = [created_node, created_belief]
                                with patch("app.agents.memory_agent.create_edge"):
                                    with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                                        with patch("app.agents.memory_agent.complete_synthesis_log"):
                                            with patch("app.agents.memory_agent.Anthropic") as mock_anthropic:
                                                mock_client = MagicMock()
                                                mock_client.messages.create = mock_anthropic_create
                                                mock_anthropic.return_value = mock_client

                                                from app.agents.memory_agent import process_signal_for_memory

                                                result = await process_signal_for_memory(
                                                    project_id=project_id,
                                                    signal_id=signal_id,
                                                    signal_type="email",
                                                    raw_text="The Q2 compliance deadline is absolutely critical...",
                                                    entities_extracted={"features_created": 2},
                                                )

                                                # Should trigger synthesis due to importance > 0.7
                                                assert result["triggers_synthesis"] is True
                                                assert "synthesis_result" in result
                                                assert result["synthesis_result"]["beliefs_created"] >= 1


class TestBeliefEvolutionFlow:
    """Tests for belief evolution over multiple signals."""

    @pytest.mark.asyncio
    async def test_belief_confidence_evolves(self, project_id, mock_supabase):
        """Test that belief confidence changes with new evidence."""
        initial_belief = {
            "id": str(uuid4()),
            "project_id": str(project_id),
            "node_type": "belief",
            "content": "Compliance is the main driver",
            "summary": "Compliance main driver",
            "confidence": 0.6,
            "is_active": True,
        }

        # Synthesizer response that increases confidence
        synth_response = [
            {
                "action": "update_belief_confidence",
                "belief_id": initial_belief["id"],
                "new_confidence": 0.8,
                "reason": "Second signal confirms compliance priority"
            }
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(synth_response))]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=200)

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[initial_belief])

            with patch("app.agents.memory_agent.get_active_beliefs", return_value=[initial_belief]):
                with patch("app.agents.memory_agent.get_recent_facts", return_value=[]):
                    with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                        with patch("app.agents.memory_agent.get_edges_to_node", return_value=[]):
                            with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                                with patch("app.agents.memory_agent.complete_synthesis_log"):
                                    with patch("app.agents.memory_agent.update_belief_confidence") as mock_update:
                                        with patch("app.agents.memory_agent.Anthropic") as mock_anthropic:
                                            mock_client = MagicMock()
                                            mock_client.messages.create.return_value = mock_response
                                            mock_anthropic.return_value = mock_client

                                            from app.agents.memory_agent import MemorySynthesizer

                                            synthesizer = MemorySynthesizer()
                                            result = await synthesizer.synthesize(
                                                project_id=project_id,
                                                trigger_reason="confirming_evidence",
                                            )

                                            # Verify confidence was updated
                                            assert result["beliefs_updated"] >= 1


class TestContradictionHandling:
    """Tests for handling contradictions in memory."""

    @pytest.mark.asyncio
    async def test_contradiction_lowers_confidence(self, project_id, mock_supabase):
        """Test that contradicting facts lower belief confidence."""
        existing_belief = {
            "id": str(uuid4()),
            "project_id": str(project_id),
            "node_type": "belief",
            "content": "Mobile-first is top priority",
            "summary": "Mobile-first priority",
            "confidence": 0.8,
            "is_active": True,
        }

        # Watcher detects contradiction
        watcher_response = {
            "facts": [
                {"content": "Budget for mobile cut by 60%", "summary": "Mobile budget cut 60%"}
            ],
            "importance": 0.7,
            "contradicts_beliefs": ["Mobile-first priority"],
            "confirms_beliefs": [],
            "is_milestone": False,
            "rationale": "Budget cut contradicts stated priority"
        }

        # Synthesizer lowers confidence
        synth_response = [
            {
                "action": "update_belief_confidence",
                "belief_id": existing_belief["id"],
                "new_confidence": 0.5,
                "reason": "Budget cut contradicts mobile priority claim"
            },
            {
                "action": "add_edge",
                "from_id": str(uuid4()),
                "to_id": existing_belief["id"],
                "edge_type": "contradicts",
                "rationale": "Budget reduction contradicts priority claim"
            }
        ]

        mock_watcher = MagicMock()
        mock_watcher.content = [MagicMock(text=json.dumps(watcher_response))]
        mock_watcher.usage = MagicMock(input_tokens=200, output_tokens=100)

        mock_synth = MagicMock()
        mock_synth.content = [MagicMock(text=json.dumps(synth_response))]
        mock_synth.usage = MagicMock(input_tokens=500, output_tokens=200)

        call_count = {"count": 0}

        def mock_create(**kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return mock_watcher
            return mock_synth

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])

            with patch("app.agents.memory_agent.get_active_beliefs", return_value=[existing_belief]):
                with patch("app.agents.memory_agent.get_recent_facts", return_value=[]):
                    with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                        with patch("app.agents.memory_agent.get_edges_to_node", return_value=[]):
                            with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                                with patch("app.agents.memory_agent.create_edge"):
                                    with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                                        with patch("app.agents.memory_agent.complete_synthesis_log"):
                                            with patch("app.agents.memory_agent.update_belief_confidence") as mock_update:
                                                with patch("app.agents.memory_agent.Anthropic") as mock_anthropic:
                                                    mock_client = MagicMock()
                                                    mock_client.messages.create = mock_create
                                                    mock_anthropic.return_value = mock_client

                                                    from app.agents.memory_agent import process_signal_for_memory

                                                    result = await process_signal_for_memory(
                                                        project_id=project_id,
                                                        signal_id=uuid4(),
                                                        signal_type="budget_report",
                                                        raw_text="Mobile budget cut by 60%...",
                                                        entities_extracted={},
                                                    )

                                                    # Contradiction should trigger synthesis
                                                    assert result["triggers_synthesis"] is True


class TestReflectionFlow:
    """Tests for periodic reflection and insight generation."""

    @pytest.mark.asyncio
    async def test_reflection_generates_insights(
        self,
        project_id,
        mock_supabase,
        mock_anthropic_reflector,
    ):
        """Test that reflection generates insights from accumulated data."""
        beliefs = [
            {"id": str(uuid4()), "summary": "Compliance is priority", "confidence": 0.8, "node_type": "belief"},
            {"id": str(uuid4()), "summary": "Mobile is stated priority", "confidence": 0.5, "node_type": "belief"},
        ]

        with patch("app.db.memory_graph.get_supabase", return_value=mock_supabase):
            mock_supabase.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])

            with patch("app.agents.memory_agent.get_active_beliefs", return_value=beliefs):
                with patch("app.agents.memory_agent.get_recent_facts", return_value=[]):
                    with patch("app.agents.memory_agent.get_insights", return_value=[]):
                        with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                            with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                                with patch("app.agents.memory_agent.create_edge"):
                                    with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                                        with patch("app.agents.memory_agent.complete_synthesis_log"):
                                            with patch("app.agents.memory_agent.archive_old_insights", return_value=0):
                                                with patch("app.agents.memory_agent.Anthropic") as mock_anthropic:
                                                    mock_client = MagicMock()
                                                    mock_client.messages.create.return_value = mock_anthropic_reflector
                                                    mock_anthropic.return_value = mock_client

                                                    from app.agents.memory_agent import run_periodic_reflection

                                                    result = await run_periodic_reflection(project_id)

                                                    assert result["insights_created"] >= 1


# =============================================================================
# Renderer Integration Tests
# =============================================================================


class TestMemoryRendering:
    """Tests for markdown rendering from graph."""

    @pytest.mark.asyncio
    async def test_render_memory_markdown(self, project_id, mock_supabase):
        """Test rendering markdown from knowledge graph."""
        beliefs = [
            {
                "id": str(uuid4()),
                "summary": "Compliance is main driver",
                "confidence": 0.85,
                "node_type": "belief",
                "belief_domain": "client_priority",
            },
        ]

        insights = [
            {
                "id": str(uuid4()),
                "summary": "Timeline vs quality tradeoff",
                "content": "Team consistently chooses faster delivery...",
                "confidence": 0.7,
                "insight_type": "behavioral",
            },
        ]

        facts = [
            {"id": str(uuid4()), "summary": "Q2 deadline mentioned", "created_at": "2025-01-15"},
        ]

        with patch("app.db.memory_graph.get_active_beliefs", return_value=beliefs):
            with patch("app.db.memory_graph.get_recent_facts", return_value=facts):
                with patch("app.db.memory_graph.get_insights", return_value=insights):
                    with patch("app.db.memory_graph.get_edges_to_node", return_value=[]):
                        with patch("app.db.project_memory.get_recent_decisions", return_value=[]):
                            with patch("app.db.project_memory.get_mistakes_to_avoid", return_value=[]):
                                with patch("app.core.memory_renderer._get_project_name", return_value="Test Project"):
                                    from app.core.memory_renderer import render_memory_markdown

                                    markdown = await render_memory_markdown(project_id)

                                    # Check that key sections are present
                                    assert "Project Memory: Test Project" in markdown
                                    assert "Current Understanding" in markdown
                                    assert "Compliance is main driver" in markdown
                                    assert "Strategic Insights" in markdown
                                    assert "Recent Observations" in markdown

    @pytest.mark.asyncio
    async def test_render_memory_for_di_agent(self, project_id, mock_supabase):
        """Test rendering memory in format optimized for DI Agent."""
        beliefs = [
            {
                "id": str(uuid4()),
                "summary": "Test belief",
                "confidence": 0.8,
                "node_type": "belief",
            },
        ]

        with patch("app.db.memory_graph.get_active_beliefs", return_value=beliefs):
            with patch("app.db.memory_graph.get_recent_facts", return_value=[]):
                with patch("app.db.memory_graph.get_insights", return_value=[]):
                    with patch("app.db.memory_graph.get_edges_to_node", return_value=[]):
                        with patch("app.db.project_memory.get_recent_decisions", return_value=[]):
                            with patch("app.db.project_memory.get_mistakes_to_avoid", return_value=[]):
                                with patch("app.core.memory_renderer._get_project_name", return_value="Test"):
                                    from app.core.memory_renderer import render_memory_for_di_agent

                                    result = await render_memory_for_di_agent(project_id)

                                    # Check structured output
                                    assert "markdown" in result
                                    assert "beliefs" in result
                                    assert "insights" in result
                                    assert "high_confidence_summary" in result

                                    # Beliefs should be formatted for prompt
                                    assert len(result["beliefs"]) >= 1
                                    # Check belief has required fields and reasonable confidence
                                    assert "confidence" in result["beliefs"][0]
                                    assert result["beliefs"][0]["confidence"] >= 0.7  # High confidence
