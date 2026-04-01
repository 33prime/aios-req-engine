"""Tests for Phase 2: Outcomes System.

Covers:
- Outcomes DB layer CRUD
- Outcome generation chain tool schema
- Outcome strength scoring dimensions
- Outcome-entity linking
- Coverage analysis
- API endpoint registration
- Outcome cascades and auto-confirmation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest


# =============================================================================
# Helpers
# =============================================================================


def _mock_execute(data=None, count=None):
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


def _make_outcome(
    project_id: UUID | None = None,
    title: str = "Error rate drops to near-zero",
    strength: int = 75,
    horizon: str = "h1",
) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(project_id or uuid4()),
        "title": title,
        "description": "Test outcome",
        "strength_score": strength,
        "strength_dimensions": {"specificity": 20, "scenario": 20, "cost_of_failure": 20, "observable": 15},
        "horizon": horizon,
        "status": "candidate",
        "confirmation_status": "ai_generated",
        "what_helps": ["Better data", "Faster process"],
        "evidence": [],
        "source_type": "system_generated",
        "enrichment_intel": {},
        "display_order": 0,
    }


def _make_actor(
    outcome_id: UUID | None = None,
    persona_name: str = "Sarah",
    strength: int = 80,
) -> dict:
    return {
        "id": str(uuid4()),
        "outcome_id": str(outcome_id or uuid4()),
        "persona_name": persona_name,
        "title": f"{persona_name} can process items in 4 minutes",
        "before_state": "Manual process takes 3 hours",
        "after_state": "AI-assisted takes 4 minutes",
        "metric": "Processing time < 5 minutes",
        "strength_score": strength,
        "status": "emerging",
        "sharpen_prompt": None,
        "evidence": [],
        "display_order": 0,
    }


# =============================================================================
# Outcome Generation Chain Tests
# =============================================================================


class TestOutcomeGenerationChain:
    """Test outcome generation tool schema and trigger logic."""

    def test_outcome_tool_schema_valid(self):
        from app.chains.generate_outcomes import OUTCOME_TOOL

        assert OUTCOME_TOOL["name"] == "submit_outcomes"
        schema = OUTCOME_TOOL["input_schema"]
        assert "outcomes" in schema["properties"]
        items = schema["properties"]["outcomes"]["items"]
        required = items["required"]
        assert "title" in required
        assert "actor_outcomes" in required
        assert "horizon" in required

    def test_trigger_conditions_bootstrap(self):
        from app.chains.generate_outcomes import should_trigger_outcome_generation

        # Signals 1-3: always trigger
        assert should_trigger_outcome_generation(uuid4(), signal_count=1) is True
        assert should_trigger_outcome_generation(uuid4(), signal_count=2) is True
        assert should_trigger_outcome_generation(uuid4(), signal_count=3) is True

    def test_trigger_conditions_after_bootstrap(self):
        from app.chains.generate_outcomes import should_trigger_outcome_generation

        # Signal 4+: only trigger on specific conditions
        assert should_trigger_outcome_generation(uuid4(), signal_count=4) is False
        assert should_trigger_outcome_generation(uuid4(), signal_count=4, has_driver_change=True) is True
        assert should_trigger_outcome_generation(uuid4(), signal_count=4, created_count=3) is True
        assert should_trigger_outcome_generation(uuid4(), signal_count=4, new_entity_types={"constraint"}) is True

    def test_trigger_no_conditions(self):
        from app.chains.generate_outcomes import should_trigger_outcome_generation

        assert should_trigger_outcome_generation(
            uuid4(), signal_count=10, created_count=1, has_driver_change=False
        ) is False


# =============================================================================
# Outcome Strength Scoring Tests
# =============================================================================


class TestOutcomeStrengthScoring:
    """Test strength scoring tool schema and scoring logic."""

    def test_scoring_tool_schema_valid(self):
        from app.chains.score_outcomes import SCORING_TOOL

        assert SCORING_TOOL["name"] == "submit_strength_scoring"
        schema = SCORING_TOOL["input_schema"]
        props = schema["properties"]
        assert "specificity" in props
        assert "scenario" in props
        assert "cost_of_failure" in props
        assert "observable" in props
        assert props["specificity"]["maximum"] == 25
        assert props["observable"]["minimum"] == 0

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    @patch("app.core.config.Settings")
    async def test_score_outcome_returns_dimensions(self, mock_settings, mock_anthropic_cls):
        from app.chains.score_outcomes import score_outcome_strength

        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client
        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = {
            "specificity": 22,
            "scenario": 24,
            "cost_of_failure": 18,
            "observable": 20,
            "actor_scores": [
                {"actor_index": 0, "strength": 85, "sharpen_prompt": None},
            ],
        }
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        outcome = _make_outcome()
        actors = [_make_actor()]

        score, dims, actor_results = await score_outcome_strength(outcome, actors)

        assert score == 84  # 22 + 24 + 18 + 20
        assert dims["specificity"] == 22
        assert dims["scenario"] == 24
        assert len(actor_results) == 1
        assert actor_results[0]["strength"] == 85


# =============================================================================
# Outcomes DB Layer Tests
# =============================================================================


class TestOutcomesDB:
    """Test outcomes CRUD operations."""

    @patch("app.db.outcomes.get_supabase")
    def test_list_outcomes(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        outcomes = [_make_outcome(), _make_outcome(title="Second outcome")]
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute(outcomes)
        sb.table.return_value = query

        from app.db.outcomes import list_outcomes
        result = list_outcomes(uuid4())
        assert len(result) == 2

    @patch("app.db.outcomes.get_supabase")
    def test_create_outcome(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        pid = uuid4()
        new_outcome = _make_outcome(project_id=pid, title="New outcome")

        # Mock display_order query
        order_query = MagicMock()
        order_query.select.return_value = order_query
        order_query.eq.return_value = order_query
        order_query.order.return_value = order_query
        order_query.limit.return_value = order_query
        order_query.execute.return_value = _mock_execute([])

        insert_mock = MagicMock()
        insert_mock.execute.return_value = _mock_execute([new_outcome])

        sb.table.return_value = order_query
        sb.table.return_value.insert.return_value = insert_mock

        from app.db.outcomes import create_outcome
        result = create_outcome(pid, "New outcome", description="Test")
        assert result["title"] == "New outcome"

    @patch("app.db.outcomes.get_supabase")
    def test_create_outcome_actor(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        oid = uuid4()
        actor = _make_actor(outcome_id=oid, persona_name="David")

        order_query = MagicMock()
        order_query.select.return_value = order_query
        order_query.eq.return_value = order_query
        order_query.order.return_value = order_query
        order_query.limit.return_value = order_query
        order_query.execute.return_value = _mock_execute([])

        insert_mock = MagicMock()
        insert_mock.execute.return_value = _mock_execute([actor])

        sb.table.return_value = order_query
        sb.table.return_value.insert.return_value = insert_mock

        from app.db.outcomes import create_outcome_actor
        result = create_outcome_actor(oid, "David", "David can access docs in 90s")
        assert result["persona_name"] == "David"

    @patch("app.db.outcomes.get_supabase")
    def test_get_outcome_coverage_empty(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        # No outcomes
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute([])
        sb.table.return_value = query

        from app.db.outcomes import get_outcome_coverage
        result = get_outcome_coverage(uuid4())
        assert result == {}

    def test_merge_string_lists_in_outcomes_context(self):
        """Verify deduplication works for hypothetical_questions merging."""
        from app.db.patch_applicator import _merge_string_lists

        existing = ["How to track inventory?", "What reduces errors?"]
        new = ["how to track inventory?", "What improves speed?"]
        result = _merge_string_lists(existing, new)
        assert len(result) == 3  # deduped "how to track inventory?"


# =============================================================================
# Outcome Auto-Confirm Tests
# =============================================================================


class TestOutcomeAutoConfirm:
    """Test bottom-up auto-confirmation of core outcomes."""

    @patch("app.db.outcomes.get_supabase")
    @patch("app.db.outcomes.get_outcome")
    @patch("app.db.outcomes.list_outcome_actors")
    def test_auto_confirm_when_all_actors_confirmed(self, mock_actors, mock_outcome, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        oid = uuid4()
        mock_outcome.return_value = {"id": str(oid), "status": "candidate"}
        mock_actors.return_value = [
            {"id": str(uuid4()), "status": "confirmed"},
            {"id": str(uuid4()), "status": "validated"},
        ]

        update_mock = MagicMock()
        update_mock.eq.return_value.execute.return_value = _mock_execute([{"id": str(oid), "status": "confirmed"}])
        sb.table.return_value.update.return_value = update_mock

        from app.db.outcomes import check_auto_confirm_core_outcome
        result = check_auto_confirm_core_outcome(oid)
        assert result is True

    @patch("app.db.outcomes.list_outcome_actors")
    def test_no_auto_confirm_when_actors_incomplete(self, mock_actors):
        mock_actors.return_value = [
            {"id": str(uuid4()), "status": "confirmed"},
            {"id": str(uuid4()), "status": "not_started"},
        ]

        from app.db.outcomes import check_auto_confirm_core_outcome
        result = check_auto_confirm_core_outcome(uuid4())
        assert result is False


# =============================================================================
# API Router Tests
# =============================================================================


class TestOutcomesAPIRegistration:
    """Test that the outcomes router is properly registered."""

    def test_router_prefix(self):
        from app.api.workspace_outcomes import router
        assert router.prefix == "/projects/{project_id}/workspace/outcomes"

    def test_router_has_endpoints(self):
        from app.api.workspace_outcomes import router
        routes = [r.path for r in router.routes]
        prefix = "/projects/{project_id}/workspace/outcomes"
        assert prefix in routes  # GET/POST outcomes
        assert f"{prefix}/{{outcome_id}}" in routes
        assert f"{prefix}/{{outcome_id}}/actors" in routes
        assert f"{prefix}/{{outcome_id}}/links" in routes
        assert f"{prefix}/{{outcome_id}}/capabilities" in routes
        assert f"{prefix}/{{outcome_id}}/score" in routes
        assert f"{prefix}/{{outcome_id}}/confirm" in routes


# =============================================================================
# Context Snapshot Layer 6 Tests
# =============================================================================


class TestContextSnapshotOutcomes:
    """Test outcomes layer in context snapshot."""

    def test_context_snapshot_has_outcomes_fields(self):
        from app.core.context_snapshot import ContextSnapshot
        snap = ContextSnapshot()
        assert snap.outcomes_prompt == ""
        assert snap.outcomes_raw == []

    @patch("app.db.outcomes.get_supabase")
    def test_build_outcomes_layer_empty(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute([])
        sb.table.return_value = query

        from app.core.context_snapshot import _build_outcomes_layer
        prompt, raw = _build_outcomes_layer(uuid4())
        assert prompt == ""
        assert raw == []

    @patch("app.db.outcomes.get_supabase")
    def test_build_outcomes_layer_with_data(self, mock_sb):
        sb = MagicMock()
        mock_sb.return_value = sb

        outcomes = [
            _make_outcome(strength=85, title="Strong outcome"),
            _make_outcome(strength=55, title="Weak outcome"),
        ]
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute(outcomes)
        sb.table.return_value = query

        from app.core.context_snapshot import _build_outcomes_layer
        prompt, raw = _build_outcomes_layer(uuid4())

        assert "## Outcomes" in prompt
        assert "Strong outcome" in prompt
        assert "Weak outcome" in prompt
        assert "needs sharpening" in prompt
        assert len(raw) == 2


# =============================================================================
# Pulse Engine Outcome Health Tests
# =============================================================================


class TestPulseOutcomeHealth:
    """Test outcome health in Pulse Engine schema."""

    def test_outcome_health_model_defaults(self):
        from app.core.schemas_pulse import OutcomeHealth
        oh = OutcomeHealth()
        assert oh.total_outcomes == 0
        assert oh.confirmed_outcomes == 0
        assert oh.avg_strength == 0.0
        assert oh.weak_outcomes == []
        assert oh.unserved_outcomes == []
        assert oh.uncovered_outcomes == []

    def test_project_pulse_has_outcome_health(self):
        from app.core.schemas_pulse import ProjectPulse, OutcomeHealth
        pulse = ProjectPulse()
        assert isinstance(pulse.outcome_health, OutcomeHealth)

    def test_outcome_health_populated(self):
        from app.core.schemas_pulse import OutcomeHealth
        oh = OutcomeHealth(
            total_outcomes=5,
            confirmed_outcomes=3,
            avg_strength=72.5,
            weak_outcomes=[{"id": "x", "title": "Weak", "strength": 55}],
        )
        assert oh.total_outcomes == 5
        assert oh.avg_strength == 72.5
        assert len(oh.weak_outcomes) == 1
