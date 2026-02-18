"""Tests for context snapshot builder."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.context_snapshot import (
    ContextSnapshot,
    _render_entity_inventory_prompt,
    build_context_snapshot,
)


@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def mock_project_data():
    """Realistic project data matching _load_project_data() output."""
    return {
        "phase": "definition",
        "phase_progress": 0.45,
        "workflow_pairs": [
            {
                "id": "wf-1",
                "name": "Student Assessment",
                "confirmation_status": "confirmed_consultant",
                "is_stale": False,
                "current_steps": [
                    {
                        "id": "step-1",
                        "label": "Create quiz",
                        "confirmation_status": "ai_generated",
                        "actor_persona_id": "p-1",
                        "pain_description": "Manual question entry",
                        "time_minutes": 30,
                        "is_stale": False,
                    },
                    {
                        "id": "step-2",
                        "label": "Grade responses",
                        "confirmation_status": "confirmed_consultant",
                        "actor_persona_id": None,
                        "pain_description": None,
                        "time_minutes": None,
                        "is_stale": True,
                    },
                ],
                "future_steps": [
                    {
                        "id": "step-3",
                        "label": "Auto-grade",
                        "confirmation_status": "ai_generated",
                        "benefit_description": "Instant grading",
                        "is_stale": False,
                    },
                ],
            },
        ],
        "drivers": [
            {
                "id": "bd-1",
                "driver_type": "pain",
                "description": "Manual grading takes 2 hours per class",
                "confirmation_status": "confirmed_client",
                "is_stale": False,
            },
            {
                "id": "bd-2",
                "driver_type": "goal",
                "description": "Reduce grading time by 80%",
                "confirmation_status": "ai_generated",
                "is_stale": False,
            },
        ],
        "personas": [
            {
                "id": "p-1",
                "name": "Professor Smith",
                "confirmation_status": "confirmed_consultant",
                "is_stale": False,
            },
        ],
        "features": [
            {
                "id": "f-1",
                "name": "Auto-grading Engine",
                "confirmation_status": "ai_generated",
                "is_stale": False,
            },
            {
                "id": "f-2",
                "name": "Quiz Builder",
                "confirmation_status": "confirmed_client",
                "is_stale": True,
            },
        ],
        "dep_graph": {"by_source": {}, "by_target": {}},
        "questions": [
            {
                "id": "q-1",
                "question": "Which LMS platforms to integrate with?",
                "priority": "high",
                "category": "technical",
            },
        ],
        "stakeholder_names": ["Sarah Chen", "Dr. Johnson"],
    }


@pytest.fixture
def mock_memory_data():
    """Mock return from render_memory_for_di_agent."""
    return {
        "markdown": "# Memory\nSome memory content",
        "beliefs": [
            {
                "id": "bel-1234",
                "summary": "Client prioritizes LMS integration",
                "confidence": 0.85,
                "domain": "technical",
            },
            {
                "id": "bel-5678",
                "summary": "Budget is constrained",
                "confidence": 0.5,
                "domain": "business",
            },
        ],
        "insights": [
            {
                "summary": "Scope expanding with each signal",
                "type": "risk",
                "confidence": 0.7,
            },
        ],
        "high_confidence_summary": "Client prioritizes LMS integration.",
    }


class TestRenderEntityInventoryPrompt:
    def test_empty_inventory(self):
        result = _render_entity_inventory_prompt({})
        assert "No entities exist yet" in result

    def test_with_features(self):
        inventory = {
            "feature": [
                {"id": "f-1", "name": "SSO", "confirmation_status": "confirmed_client", "is_stale": False},
                {"id": "f-2", "name": "Dashboard", "confirmation_status": "ai_generated", "is_stale": True},
            ],
        }
        result = _render_entity_inventory_prompt(inventory)
        assert "Features (2)" in result
        assert "SSO" in result
        assert "[confirmed_client]" in result
        assert "[STALE]" in result

    def test_with_workflow_steps(self):
        inventory = {
            "workflow_step": [
                {
                    "id": "s-1",
                    "name": "Create quiz",
                    "confirmation_status": "ai_generated",
                    "is_stale": False,
                    "workflow_name": "Assessment",
                },
            ],
        }
        result = _render_entity_inventory_prompt(inventory)
        assert "Workflow Steps (1)" in result
        assert "in Assessment" in result

    def test_with_business_drivers(self):
        inventory = {
            "business_driver": [
                {
                    "id": "bd-1",
                    "name": "Manual grading takes too long",
                    "driver_type": "pain",
                    "confirmation_status": "confirmed_client",
                    "is_stale": False,
                },
            ],
        }
        result = _render_entity_inventory_prompt(inventory)
        assert "(pain)" in result

    def test_caps_at_20_per_type(self):
        inventory = {
            "feature": [
                {"id": f"f-{i}", "name": f"Feature {i}", "confirmation_status": "ai_generated", "is_stale": False}
                for i in range(25)
            ],
        }
        result = _render_entity_inventory_prompt(inventory)
        assert "and 5 more" in result

    def test_total_count(self):
        inventory = {
            "feature": [{"id": "f-1", "name": "A", "confirmation_status": "ai_generated", "is_stale": False}],
            "persona": [{"id": "p-1", "name": "B", "confirmation_status": "ai_generated", "is_stale": False}],
            "workflow": [],
        }
        result = _render_entity_inventory_prompt(inventory)
        assert "Total: 2 entities across 2 types" in result


# Shared mock patches for all build_context_snapshot tests.
# The key insight: imports happen inside function bodies, so we mock at the source modules.
def _make_snapshot_mocks(mock_project_data, mock_memory_data, open_questions=None, structural_gaps=None):
    """Create patch context manager for build_context_snapshot tests."""
    if open_questions is None:
        open_questions = []
    if structural_gaps is None:
        structural_gaps = []

    mock_phase = MagicMock(value="building")

    return [
        patch("app.core.action_engine._load_project_data", new_callable=AsyncMock, return_value=mock_project_data),
        patch("app.core.memory_renderer.render_memory_for_di_agent", new_callable=AsyncMock, return_value=mock_memory_data),
        patch("app.core.memory_renderer.format_beliefs_for_prompt", return_value="- (85%) Client prioritizes LMS"),
        patch("app.core.memory_renderer.format_insights_for_prompt", return_value="- Risk: Scope expanding"),
        patch("app.db.open_questions.list_open_questions", return_value=open_questions),
        patch("app.core.action_engine._build_structural_gaps", return_value=structural_gaps),
        patch("app.core.action_engine._detect_context_phase", return_value=(mock_phase, 0.5)),
        # Mock supabase calls for extra entity types (stakeholders, data_entities, etc.)
        patch("app.db.supabase_client.get_supabase", return_value=MagicMock(
            table=MagicMock(return_value=MagicMock(
                select=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=MagicMock(data=[])),
                        limit=MagicMock(return_value=MagicMock(
                            execute=MagicMock(return_value=MagicMock(data=[]))
                        )),
                    ))
                ))
            ))
        )),
    ]


class TestBuildContextSnapshot:
    @pytest.mark.asyncio
    async def test_builds_three_layers(self, project_id, mock_project_data, mock_memory_data):
        """All 3 prompt layers should be non-empty strings."""
        mocks = _make_snapshot_mocks(
            mock_project_data,
            mock_memory_data,
            open_questions=[{"id": "q-1", "question": "Which LMS platforms?", "priority": "high", "category": "technical"}],
            structural_gaps=[MagicMock(sentence="Who performs 'Grade responses'?", score=82)],
        )
        with mocks[0], mocks[1], mocks[2], mocks[3], mocks[4], mocks[5], mocks[6], mocks[7]:
            snapshot = await build_context_snapshot(project_id)

        # Layer 1: Entity inventory
        assert isinstance(snapshot.entity_inventory_prompt, str)
        assert len(snapshot.entity_inventory_prompt) > 0
        assert "Feature" in snapshot.entity_inventory_prompt

        # Layer 2: Memory
        assert isinstance(snapshot.memory_prompt, str)
        assert len(snapshot.memory_prompt) > 0
        assert "Beliefs" in snapshot.memory_prompt or "Memory" in snapshot.memory_prompt

        # Layer 3: Gaps
        assert isinstance(snapshot.gaps_prompt, str)
        assert len(snapshot.gaps_prompt) > 0
        assert "Gap" in snapshot.gaps_prompt

    @pytest.mark.asyncio
    async def test_entity_inventory_contains_ids(self, project_id, mock_project_data, mock_memory_data):
        """Entity inventory should contain entity IDs for merge/update references."""
        mocks = _make_snapshot_mocks(mock_project_data, mock_memory_data)
        with mocks[0], mocks[1], mocks[2], mocks[3], mocks[4], mocks[5], mocks[6], mocks[7]:
            snapshot = await build_context_snapshot(project_id)

        # Check structured inventory
        assert "feature" in snapshot.entity_inventory
        assert len(snapshot.entity_inventory["feature"]) == 2
        assert snapshot.entity_inventory["feature"][0]["id"] == "f-1"
        assert snapshot.entity_inventory["feature"][0]["name"] == "Auto-grading Engine"

        assert "persona" in snapshot.entity_inventory
        assert snapshot.entity_inventory["persona"][0]["id"] == "p-1"

        assert "workflow" in snapshot.entity_inventory
        assert snapshot.entity_inventory["workflow"][0]["name"] == "Student Assessment"

        assert "workflow_step" in snapshot.entity_inventory
        assert len(snapshot.entity_inventory["workflow_step"]) == 3  # 2 current + 1 future

        assert "business_driver" in snapshot.entity_inventory
        assert len(snapshot.entity_inventory["business_driver"]) == 2

    @pytest.mark.asyncio
    async def test_beliefs_and_questions_populated(self, project_id, mock_project_data, mock_memory_data):
        """Beliefs and open questions should be populated from memory."""
        mocks = _make_snapshot_mocks(
            mock_project_data,
            mock_memory_data,
            open_questions=[{"id": "q-1", "question": "Which LMS?", "priority": "high", "category": "technical"}],
        )
        with mocks[0], mocks[1], mocks[2], mocks[3], mocks[4], mocks[5], mocks[6], mocks[7]:
            snapshot = await build_context_snapshot(project_id)

        assert len(snapshot.beliefs) == 2
        assert snapshot.beliefs[0]["summary"] == "Client prioritizes LMS integration"
        assert snapshot.beliefs[0]["confidence"] == 0.85

        assert len(snapshot.open_questions) == 1
        assert snapshot.open_questions[0]["question"] == "Which LMS?"

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, project_id):
        """Should return partial results when individual layers fail."""
        with patch("app.core.action_engine._load_project_data", new_callable=AsyncMock, side_effect=Exception("DB down")):
            snapshot = await build_context_snapshot(project_id)

        # Should still return a valid ContextSnapshot
        assert isinstance(snapshot, ContextSnapshot)
        # Inventory will be empty due to failure
        assert snapshot.entity_inventory == {}


class TestContextSnapshotModel:
    def test_defaults(self):
        cs = ContextSnapshot()
        assert cs.entity_inventory_prompt == ""
        assert cs.memory_prompt == ""
        assert cs.gaps_prompt == ""
        assert cs.entity_inventory == {}
        assert cs.beliefs == []
        assert cs.open_questions == []

    def test_with_data(self):
        cs = ContextSnapshot(
            entity_inventory_prompt="## Entities\n- Feature A",
            memory_prompt="## Memory\n- Belief 1",
            gaps_prompt="## Gaps\n- No actor",
            entity_inventory={"feature": [{"id": "f1", "name": "A"}]},
            beliefs=[{"id": "b1", "summary": "test", "confidence": 0.8}],
            open_questions=[{"id": "q1", "question": "test?"}],
        )
        assert "Feature A" in cs.entity_inventory_prompt
        assert len(cs.beliefs) == 1
