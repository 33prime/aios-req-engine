"""Tests for unified memory synthesis module.

Tests cover:
- Data gathering from both memory systems
- LLM synthesis (mocked)
- Cache storage and retrieval
- Staleness tracking and triggers
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.unified_memory_synthesis import (
    gather_unified_memory_data,
    compute_inputs_hash,
    synthesize_unified_memory,
    get_cached_synthesis,
    mark_synthesis_stale,
    get_unified_memory,
    _build_synthesis_prompt,
    _format_age,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for database operations."""
    with patch("app.core.unified_memory_synthesis.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_project_id():
    """Generate a sample project UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_memory_data():
    """Sample memory data from both systems."""
    return {
        "decisions": [
            {
                "id": str(uuid.uuid4()),
                "title": "Use FastAPI for backend",
                "decision": "We will use FastAPI as the web framework",
                "rationale": "It has good async support and auto-documentation",
                "decided_by": "consultant",
                "confidence": 0.9,
                "decision_type": "architecture",
                "created_at": "2024-01-15T10:00:00Z",
            }
        ],
        "learnings": [
            {
                "id": str(uuid.uuid4()),
                "title": "Client prefers detailed documentation",
                "context": "During review meeting",
                "learning": "The client values comprehensive docs over speed",
                "learning_type": "insight",
                "domain": "client",
                "times_applied": 2,
                "created_at": "2024-01-16T10:00:00Z",
            }
        ],
        "questions": [
            {
                "question": "What is the expected user load?",
                "resolved": False,
                "created_at": "2024-01-17T10:00:00Z",
            }
        ],
        "beliefs": [
            {
                "id": str(uuid.uuid4()),
                "summary": "Performance is a critical priority for this client",
                "content": "Based on multiple signals, the client has emphasized performance...",
                "confidence": 0.85,
                "belief_domain": "client_priority",
                "created_at": "2024-01-18T10:00:00Z",
            }
        ],
        "low_confidence_beliefs": [
            {
                "id": str(uuid.uuid4()),
                "summary": "Mobile support may be needed",
                "content": "One stakeholder mentioned mobile...",
                "confidence": 0.5,
                "belief_domain": "technical",
                "created_at": "2024-01-19T10:00:00Z",
            }
        ],
        "insights": [
            {
                "id": str(uuid.uuid4()),
                "summary": "Client says speed but actions show quality focus",
                "content": "Behavioral pattern detected...",
                "confidence": 0.75,
                "insight_type": "behavioral",
                "created_at": "2024-01-20T10:00:00Z",
            }
        ],
        "facts_count": 15,
        "sources_count": 5,
    }


# =============================================================================
# Data Gathering Tests
# =============================================================================


def test_gather_unified_memory_data_combines_both_systems(mock_supabase, sample_project_id):
    """Test that gather_unified_memory_data queries both memory systems."""
    # Setup mock responses
    decisions_response = MagicMock()
    decisions_response.data = [{"id": "1", "title": "Test Decision"}]

    learnings_response = MagicMock()
    learnings_response.data = [{"id": "1", "title": "Test Learning"}]

    memory_response = MagicMock()
    memory_response.data = {"open_questions": [{"question": "Test?"}]}

    beliefs_response = MagicMock()
    beliefs_response.data = [
        {"id": "1", "summary": "High conf", "confidence": 0.8},
        {"id": "2", "summary": "Low conf", "confidence": 0.4},
    ]

    insights_response = MagicMock()
    insights_response.data = [{"id": "1", "summary": "Test insight"}]

    facts_count_response = MagicMock()
    facts_count_response.count = 10

    sources_count_response = MagicMock()
    sources_count_response.count = 3

    # Configure mock to return appropriate responses
    def mock_table(table_name):
        table_mock = MagicMock()
        if table_name == "project_decisions":
            table_mock.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = decisions_response
        elif table_name == "project_learnings":
            table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = learnings_response
        elif table_name == "project_memory":
            table_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = memory_response
        elif table_name == "memory_nodes":
            # First call for beliefs, second for facts count
            table_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = beliefs_response
            table_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = facts_count_response
        elif table_name == "signals":
            table_mock.select.return_value.eq.return_value.execute.return_value = sources_count_response
        return table_mock

    mock_supabase.table.side_effect = mock_table

    # Execute
    result = gather_unified_memory_data(sample_project_id)

    # Verify structure
    assert "decisions" in result
    assert "learnings" in result
    assert "questions" in result
    assert "beliefs" in result
    assert "low_confidence_beliefs" in result
    assert "insights" in result
    assert "facts_count" in result
    assert "sources_count" in result


def test_compute_inputs_hash_consistent():
    """Test that hash is consistent for same input."""
    data = {
        "decisions": [{"id": "1"}, {"id": "2"}],
        "learnings": [],
        "beliefs": [{"id": "3"}],
        "insights": [],
        "facts_count": 5,
        "questions": [],
    }

    hash1 = compute_inputs_hash(data)
    hash2 = compute_inputs_hash(data)

    assert hash1 == hash2


def test_compute_inputs_hash_changes_on_different_input():
    """Test that hash changes when input changes."""
    data1 = {
        "decisions": [{"id": "1"}],
        "learnings": [],
        "beliefs": [],
        "insights": [],
        "facts_count": 5,
        "questions": [],
    }
    data2 = {
        "decisions": [{"id": "1"}, {"id": "2"}],  # Added a decision
        "learnings": [],
        "beliefs": [],
        "insights": [],
        "facts_count": 5,
        "questions": [],
    }

    hash1 = compute_inputs_hash(data1)
    hash2 = compute_inputs_hash(data2)

    assert hash1 != hash2


# =============================================================================
# Synthesis Tests
# =============================================================================


def test_build_synthesis_prompt_includes_all_sections(sample_memory_data):
    """Test that the synthesis prompt includes all memory sections."""
    prompt = _build_synthesis_prompt(sample_memory_data)

    # Should include beliefs section
    assert "High-Confidence Beliefs" in prompt
    assert "Performance is a critical priority" in prompt

    # Should include decisions section
    assert "Key Decisions" in prompt
    assert "Use FastAPI for backend" in prompt

    # Should include insights
    assert "Strategic Insights" in prompt
    assert "behavioral" in prompt

    # Should include uncertainties
    assert "Uncertainties" in prompt
    assert "Mobile support may be needed" in prompt

    # Should include questions
    assert "Open Questions" in prompt
    assert "expected user load" in prompt

    # Should include learnings
    assert "Learnings" in prompt
    assert "Client prefers detailed documentation" in prompt

    # Should include evidence stats
    assert "Facts extracted: 15" in prompt
    assert "Sources analyzed: 5" in prompt


@patch("app.core.unified_memory_synthesis.Anthropic")
@patch("app.core.unified_memory_synthesis._store_cached_synthesis")
@patch("app.core.unified_memory_synthesis.gather_unified_memory_data")
def test_synthesize_unified_memory_calls_llm(
    mock_gather, mock_store, mock_anthropic, sample_project_id, sample_memory_data
):
    """Test that synthesis calls the LLM and returns content."""
    # Setup mocks
    mock_gather.return_value = sample_memory_data

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## Current Understanding\n\nSynthesized content...")]
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=1000)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Execute
    with patch("app.core.unified_memory_synthesis.get_settings") as mock_settings:
        mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
        result = synthesize_unified_memory(sample_project_id)

    # Verify
    assert "content" in result
    assert "Synthesized content" in result["content"]
    assert result["is_stale"] is False
    assert "synthesized_at" in result
    mock_store.assert_called_once()


# =============================================================================
# Cache Tests
# =============================================================================


def test_get_cached_synthesis_returns_freshness(mock_supabase, sample_project_id):
    """Test that cached synthesis includes freshness information."""
    # Setup mock
    cache_time = datetime.utcnow() - timedelta(minutes=5)
    response = MagicMock()
    response.data = {
        "content": "Cached content",
        "synthesized_at": cache_time.isoformat() + "Z",
        "is_stale": False,
        "stale_reason": None,
        "inputs_hash": "abc123",
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = response

    # Execute
    result = get_cached_synthesis(sample_project_id)

    # Verify
    assert result is not None
    assert result["content"] == "Cached content"
    assert "freshness" in result
    assert "age_seconds" in result["freshness"]
    assert result["freshness"]["age_seconds"] >= 300  # ~5 minutes


def test_get_cached_synthesis_returns_none_when_no_cache(mock_supabase, sample_project_id):
    """Test that None is returned when no cache exists."""
    response = MagicMock()
    response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = response

    result = get_cached_synthesis(sample_project_id)

    assert result is None


# =============================================================================
# Staleness Tests
# =============================================================================


def test_mark_synthesis_stale_updates_cache(mock_supabase, sample_project_id):
    """Test that marking stale updates the cache entry."""
    response = MagicMock()
    response.data = [{"id": "1", "is_stale": True}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(sample_project_id, "signal_processed")

    assert result is True
    mock_supabase.table.return_value.update.assert_called_once()
    call_args = mock_supabase.table.return_value.update.call_args
    assert call_args[0][0]["is_stale"] is True
    assert call_args[0][0]["stale_reason"] == "signal_processed"


def test_mark_synthesis_stale_returns_false_when_no_cache(mock_supabase, sample_project_id):
    """Test that marking stale returns False when no cache exists."""
    response = MagicMock()
    response.data = []
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(sample_project_id, "signal_processed")

    assert result is False


# =============================================================================
# Unified Memory Retrieval Tests
# =============================================================================


@patch("app.core.unified_memory_synthesis.get_cached_synthesis")
@patch("app.core.unified_memory_synthesis.synthesize_unified_memory")
def test_get_unified_memory_returns_cache_when_fresh(
    mock_synthesize, mock_get_cache, sample_project_id
):
    """Test that fresh cache is returned without re-synthesis."""
    mock_get_cache.return_value = {
        "content": "Cached content",
        "synthesized_at": datetime.utcnow().isoformat(),
        "is_stale": False,
        "stale_reason": None,
        "freshness": {"age_seconds": 60, "age_human": "1m ago"},
    }

    result = get_unified_memory(sample_project_id)

    assert result["content"] == "Cached content"
    mock_synthesize.assert_not_called()


@patch("app.core.unified_memory_synthesis.get_cached_synthesis")
@patch("app.core.unified_memory_synthesis.synthesize_unified_memory")
@patch("app.core.unified_memory_synthesis.gather_unified_memory_data")
def test_get_unified_memory_regenerates_when_stale(
    mock_gather, mock_synthesize, mock_get_cache, sample_project_id, sample_memory_data
):
    """Test that stale cache triggers re-synthesis."""
    mock_get_cache.return_value = {
        "content": "Stale content",
        "synthesized_at": datetime.utcnow().isoformat(),
        "is_stale": True,  # Stale!
        "stale_reason": "signal_processed",
        "freshness": {"age_seconds": 300, "age_human": "5m ago"},
    }
    mock_gather.return_value = sample_memory_data
    mock_synthesize.return_value = {
        "content": "Fresh content",
        "synthesized_at": datetime.utcnow().isoformat(),
        "is_stale": False,
        "stale_reason": None,
    }

    result = get_unified_memory(sample_project_id)

    assert result["content"] == "Fresh content"
    mock_synthesize.assert_called_once()


@patch("app.core.unified_memory_synthesis.get_cached_synthesis")
@patch("app.core.unified_memory_synthesis.synthesize_unified_memory")
@patch("app.core.unified_memory_synthesis.gather_unified_memory_data")
def test_get_unified_memory_force_refresh_bypasses_cache(
    mock_gather, mock_synthesize, mock_get_cache, sample_project_id, sample_memory_data
):
    """Test that force_refresh=True bypasses cache."""
    mock_gather.return_value = sample_memory_data
    mock_synthesize.return_value = {
        "content": "Force refreshed content",
        "synthesized_at": datetime.utcnow().isoformat(),
        "is_stale": False,
        "stale_reason": None,
    }

    result = get_unified_memory(sample_project_id, force_refresh=True)

    assert result["content"] == "Force refreshed content"
    mock_get_cache.assert_not_called()  # Should not check cache
    mock_synthesize.assert_called_once()


# =============================================================================
# Helper Function Tests
# =============================================================================


def test_format_age_just_now():
    """Test age formatting for very recent times."""
    assert _format_age(30) == "just now"


def test_format_age_minutes():
    """Test age formatting for minutes."""
    assert _format_age(120) == "2m ago"
    assert _format_age(3599) == "59m ago"


def test_format_age_hours():
    """Test age formatting for hours."""
    assert _format_age(3600) == "1h ago"
    assert _format_age(7200) == "2h ago"


def test_format_age_days():
    """Test age formatting for days."""
    assert _format_age(86400) == "1d ago"
    assert _format_age(172800) == "2d ago"
