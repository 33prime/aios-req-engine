"""Unit tests for Memory Agent components.

Tests MemoryWatcher, MemorySynthesizer, and MemoryReflector.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.memory_agent import (
    MemoryWatcher,
    MemorySynthesizer,
    MemoryReflector,
    IMPORTANCE_THRESHOLD_FOR_SYNTHESIS,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def project_id():
    """Sample project UUID."""
    return uuid4()


@pytest.fixture
def sample_beliefs():
    """Sample active beliefs for testing."""
    return [
        {
            "id": str(uuid4()),
            "node_type": "belief",
            "content": "The primary business driver is regulatory compliance",
            "summary": "Primary driver: compliance",
            "confidence": 0.8,
            "belief_domain": "client_priority",
        },
        {
            "id": str(uuid4()),
            "node_type": "belief",
            "content": "Mobile-first is stated priority but not reflected in decisions",
            "summary": "Mobile priority uncertain",
            "confidence": 0.6,
            "belief_domain": "client_priority",
        },
    ]


@pytest.fixture
def sample_facts():
    """Sample facts for testing."""
    return [
        {
            "id": str(uuid4()),
            "node_type": "fact",
            "content": "CTO mentioned Q2 compliance deadline in email",
            "summary": "Q2 compliance deadline mentioned",
            "confidence": 1.0,
        },
        {
            "id": str(uuid4()),
            "node_type": "fact",
            "content": "CEO said mobile-first is top priority in kickoff meeting",
            "summary": "Mobile-first stated as priority",
            "confidence": 1.0,
        },
    ]


@pytest.fixture
def sample_insights():
    """Sample insights for testing."""
    return [
        {
            "id": str(uuid4()),
            "node_type": "insight",
            "content": "Client's stated priorities differ from actual decision patterns",
            "summary": "Stated vs actual priority mismatch",
            "confidence": 0.75,
            "insight_type": "behavioral",
        },
    ]


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"facts": [], "importance": 0.5}')]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return mock_response


# =============================================================================
# MemoryWatcher Tests
# =============================================================================


class TestMemoryWatcher:
    """Tests for MemoryWatcher component."""

    @pytest.mark.asyncio
    async def test_process_event_extracts_facts(self, project_id, sample_beliefs, sample_facts):
        """Test that watcher extracts facts from events."""
        watcher_response = {
            "facts": [
                {"content": "New compliance requirement mentioned", "summary": "New compliance req"}
            ],
            "importance": 0.6,
            "contradicts_beliefs": [],
            "confirms_beliefs": ["Primary driver: compliance"],
            "is_milestone": False,
            "rationale": "Routine signal with new information",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(watcher_response))]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=80)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                    with patch("app.agents.memory_agent.complete_synthesis_log"):
                        with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                            with patch.object(
                                MemoryWatcher,
                                "__init__",
                                lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                            ):
                                watcher = MemoryWatcher()
                                watcher.client.messages.create.return_value = mock_response

                                result = await watcher.process_event(
                                    project_id=project_id,
                                    event_type="signal_processed",
                                    event_data={
                                        "signal_id": str(uuid4()),
                                        "signal_type": "email",
                                        "raw_text_snippet": "We need to meet the Q2 compliance deadline...",
                                    },
                                )

                                assert "facts" in result
                                assert result["importance"] == 0.6
                                assert result["triggers_synthesis"] is False  # 0.6 < 0.7 threshold
                                assert "Primary driver: compliance" in result["supported_beliefs"]

    @pytest.mark.asyncio
    async def test_high_importance_triggers_synthesis(self, project_id, sample_beliefs, sample_facts):
        """Test that high importance triggers synthesis."""
        watcher_response = {
            "facts": [
                {"content": "Client announced pivot to B2B", "summary": "B2B pivot announced"}
            ],
            "importance": 0.9,
            "contradicts_beliefs": ["Mobile priority uncertain"],
            "confirms_beliefs": [],
            "is_milestone": True,
            "rationale": "Major strategic shift announced",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(watcher_response))]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=80)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                    with patch("app.agents.memory_agent.complete_synthesis_log"):
                        with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                            with patch.object(
                                MemoryWatcher,
                                "__init__",
                                lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                            ):
                                watcher = MemoryWatcher()
                                watcher.client.messages.create.return_value = mock_response

                                result = await watcher.process_event(
                                    project_id=project_id,
                                    event_type="signal_processed",
                                    event_data={"signal_type": "meeting_notes"},
                                )

                                assert result["importance"] == 0.9
                                assert result["triggers_synthesis"] is True  # High importance
                                assert result["triggers_reflection"] is True  # is_milestone

    @pytest.mark.asyncio
    async def test_contradiction_triggers_synthesis(self, project_id, sample_beliefs, sample_facts):
        """Test that contradictions trigger synthesis even with low importance."""
        watcher_response = {
            "facts": [
                {"content": "Budget for compliance cut by 50%", "summary": "Compliance budget cut"}
            ],
            "importance": 0.5,
            "contradicts_beliefs": ["Primary driver: compliance"],
            "confirms_beliefs": [],
            "is_milestone": False,
            "rationale": "Contradicts existing belief about compliance priority",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(watcher_response))]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=80)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                    with patch("app.agents.memory_agent.complete_synthesis_log"):
                        with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                            with patch.object(
                                MemoryWatcher,
                                "__init__",
                                lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                            ):
                                watcher = MemoryWatcher()
                                watcher.client.messages.create.return_value = mock_response

                                result = await watcher.process_event(
                                    project_id=project_id,
                                    event_type="signal_processed",
                                    event_data={"signal_type": "email"},
                                )

                                # Even though importance is 0.5, contradiction should trigger synthesis
                                assert result["triggers_synthesis"] is True

    def test_parse_watcher_response_valid_json(self):
        """Test parsing valid JSON response."""
        with patch.object(
            MemoryWatcher,
            "__init__",
            lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
        ):
            watcher = MemoryWatcher()

            content = '{"facts": [{"content": "test", "summary": "test"}], "importance": 0.7}'
            result = watcher._parse_watcher_response(content)

            assert result["importance"] == 0.7
            assert len(result["facts"]) == 1

    def test_parse_watcher_response_with_markdown(self):
        """Test parsing JSON embedded in markdown."""
        with patch.object(
            MemoryWatcher,
            "__init__",
            lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
        ):
            watcher = MemoryWatcher()

            content = 'Here is the result:\n```json\n{"facts": [], "importance": 0.5}\n```'
            result = watcher._parse_watcher_response(content)

            assert result["importance"] == 0.5


# =============================================================================
# MemorySynthesizer Tests
# =============================================================================


class TestMemorySynthesizer:
    """Tests for MemorySynthesizer component."""

    @pytest.mark.asyncio
    async def test_synthesize_creates_beliefs(self, project_id, sample_beliefs, sample_facts):
        """Test that synthesizer creates beliefs from facts."""
        synthesizer_response = [
            {
                "action": "create_belief",
                "content": "Compliance is driving Q2 decisions",
                "summary": "Q2 compliance focus",
                "confidence": 0.75,
                "domain": "client_priority",
                "supported_by": [sample_facts[0]["id"]],
            },
            {
                "action": "add_edge",
                "from_id": sample_facts[0]["id"],
                "to_id": sample_beliefs[0]["id"],
                "edge_type": "supports",
                "rationale": "Fact supports belief",
            },
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(synthesizer_response))]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=300)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                    with patch("app.agents.memory_agent.get_edges_to_node", return_value=[]):
                        with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                            with patch("app.agents.memory_agent.complete_synthesis_log"):
                                with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                                    with patch("app.agents.memory_agent.create_edge"):
                                        with patch.object(
                                            MemorySynthesizer,
                                            "__init__",
                                            lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                                        ):
                                            synthesizer = MemorySynthesizer()
                                            synthesizer.client.messages.create.return_value = mock_response

                                            result = await synthesizer.synthesize(
                                                project_id=project_id,
                                                trigger_reason="high_importance",
                                            )

                                            assert result["beliefs_created"] >= 1
                                            assert result["edges_created"] >= 1

    @pytest.mark.asyncio
    async def test_synthesize_updates_confidence(self, project_id, sample_beliefs, sample_facts):
        """Test that synthesizer updates belief confidence."""
        synthesizer_response = [
            {
                "action": "update_belief_confidence",
                "belief_id": sample_beliefs[0]["id"],
                "new_confidence": 0.9,
                "reason": "Multiple supporting facts found",
            },
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(synthesizer_response))]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=200)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                    with patch("app.agents.memory_agent.get_edges_to_node", return_value=[]):
                        with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                            with patch("app.agents.memory_agent.complete_synthesis_log"):
                                with patch("app.agents.memory_agent.update_belief_confidence") as mock_update:
                                    with patch.object(
                                        MemorySynthesizer,
                                        "__init__",
                                        lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                                    ):
                                        synthesizer = MemorySynthesizer()
                                        synthesizer.client.messages.create.return_value = mock_response

                                        result = await synthesizer.synthesize(
                                            project_id=project_id,
                                            trigger_reason="evidence_found",
                                        )

                                        assert result["beliefs_updated"] >= 1

    def test_parse_synthesizer_response(self):
        """Test parsing synthesizer JSON array response."""
        with patch.object(
            MemorySynthesizer,
            "__init__",
            lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
        ):
            synthesizer = MemorySynthesizer()

            content = '[{"action": "create_belief", "content": "test"}]'
            result = synthesizer._parse_synthesizer_response(content)

            assert len(result) == 1
            assert result[0]["action"] == "create_belief"


# =============================================================================
# MemoryReflector Tests
# =============================================================================


class TestMemoryReflector:
    """Tests for MemoryReflector component."""

    @pytest.mark.asyncio
    async def test_reflect_generates_insights(self, project_id, sample_beliefs, sample_facts, sample_insights):
        """Test that reflector generates insights."""
        reflector_response = {
            "insights": [
                {
                    "content": "Pattern detected: compliance consistently wins over mobile in decisions",
                    "summary": "Compliance trumps mobile priority",
                    "confidence": 0.8,
                    "type": "behavioral",
                    "supported_by": [sample_beliefs[0]["id"], sample_beliefs[1]["id"]],
                },
            ],
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(reflector_response))]
        mock_response.usage = MagicMock(input_tokens=1000, output_tokens=500)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=sample_beliefs):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=sample_facts):
                with patch("app.agents.memory_agent.get_insights", return_value=sample_insights):
                    with patch("app.agents.memory_agent.get_all_edges", return_value=[]):
                        with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                            with patch("app.agents.memory_agent.complete_synthesis_log"):
                                with patch("app.agents.memory_agent.archive_old_insights", return_value=0):
                                    with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                                        with patch("app.agents.memory_agent.create_edge"):
                                            with patch.object(
                                                MemoryReflector,
                                                "__init__",
                                                lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
                                            ):
                                                reflector = MemoryReflector()
                                                reflector.client.messages.create.return_value = mock_response

                                                result = await reflector.reflect(project_id)

                                                assert result["insights_created"] >= 1
                                                assert len(result["insights"]) >= 1
                                                assert result["insights"][0]["type"] == "behavioral"

    def test_parse_reflector_response(self):
        """Test parsing reflector JSON response."""
        with patch.object(
            MemoryReflector,
            "__init__",
            lambda self: setattr(self, "settings", MagicMock()) or setattr(self, "client", MagicMock()),
        ):
            reflector = MemoryReflector()

            content = '{"insights": [{"summary": "test insight", "type": "risk"}]}'
            result = reflector._parse_reflector_response(content)

            assert len(result["insights"]) == 1
            assert result["insights"][0]["type"] == "risk"


# =============================================================================
# Integration Helper Tests
# =============================================================================


class TestIntegrationHelpers:
    """Tests for convenience/integration functions."""

    @pytest.mark.asyncio
    async def test_process_signal_for_memory(self, project_id):
        """Test the convenience function for signal processing."""
        watcher_response = {
            "facts": [{"content": "test", "summary": "test"}],
            "importance": 0.5,
            "contradicts_beliefs": [],
            "confirms_beliefs": [],
            "is_milestone": False,
            "rationale": "test",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(watcher_response))]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        with patch("app.agents.memory_agent.get_active_beliefs", return_value=[]):
            with patch("app.agents.memory_agent.get_recent_facts", return_value=[]):
                with patch("app.agents.memory_agent.start_synthesis_log", return_value=uuid4()):
                    with patch("app.agents.memory_agent.complete_synthesis_log"):
                        with patch("app.agents.memory_agent.create_node", return_value={"id": str(uuid4())}):
                            with patch("app.agents.memory_agent.Anthropic") as mock_anthropic:
                                mock_client = MagicMock()
                                mock_client.messages.create.return_value = mock_response
                                mock_anthropic.return_value = mock_client

                                from app.agents.memory_agent import process_signal_for_memory

                                result = await process_signal_for_memory(
                                    project_id=project_id,
                                    signal_id=uuid4(),
                                    signal_type="email",
                                    raw_text="Test email content",
                                    entities_extracted={"features_created": 1},
                                )

                                assert "facts" in result
                                assert "importance" in result
