"""Integration tests for unified readiness system.

Tests the complete readiness scoring pipeline including:
- Dimensional scoring (value_path, problem, solution, engagement)
- Gate-based assessment
- Gate ceiling application
- Cache consistency
- Recommendations and blocking gates
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.readiness.types import GateAssessment, ReadinessPhase
from app.core.readiness import compute_readiness
from app.core.readiness.types import ReadinessScore
from app.core.schemas_foundation import (
    BusinessCase,
    BudgetConstraints,
    ConfirmedScope,
    CorePain,
    DesignPreferences,
    KPI,
    PrimaryPersona,
    ProjectFoundation,
    WowMoment,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def project_id():
    """Generate a test project ID."""
    return uuid4()


@pytest.fixture
def foundation_id():
    """Generate a test foundation ID."""
    return uuid4()


@pytest.fixture
def empty_project_data():
    """Data for an empty project with no entities."""
    return {
        "vp_steps": [],
        "features": [],
        "personas": [],
        "strategic_context": None,
        "signals": [],
        "meetings": [],
        "foundation": None,
        "client_signals": [],
        "completed_meetings": [],
        "confirmed_count": 0,
        "total_count": 0,
    }


@pytest.fixture
def prototype_ready_foundation(project_id, foundation_id):
    """Foundation with prototype gates satisfied."""
    return ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=CorePain(
            statement="CS teams manually track churn risk across multiple fragmented tools",
            trigger="Lost 3 enterprise customers in Q4",
            stakes="$2M ARR at risk if churn continues",
            who_feels_it="Customer Success Managers",
            confidence=0.85,
        ),
        primary_persona=PrimaryPersona(
            name="Customer Success Manager",
            role="Manages customer relationships",
            goal="Reduce churn",
            pain_connection="Can't identify at-risk customers early",
            context="Checks dashboards daily",
            confidence=0.8,
        ),
        wow_moment=WowMoment(
            description="Dashboard predicts churn 60 days in advance",
            core_pain_inversion="From reactive to proactive",
            emotional_impact="Relief and confidence",
            visual_concept="Red/yellow/green health scores",
            level_1="Core pain solved: Can predict churn",
            confidence=0.75,
        ),
        design_preferences=DesignPreferences(
            visual_style="clean/minimal",
            references=["Linear", "Stripe"],
        ),
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )


@pytest.fixture
def build_ready_foundation(prototype_ready_foundation):
    """Foundation with all gates satisfied."""
    foundation = prototype_ready_foundation.model_copy(deep=True)
    foundation.business_case = BusinessCase(
        value_to_business="Reduce churn by 15%, save $300K annually",
        roi_framing="$300K annual savings vs $50K investment",
        success_kpis=[
            KPI(
                metric="Churn rate",
                current_state="12%",
                target_state="<10%",
                measurement_method="Monthly cohort tracking",
                timeframe="6 months",
            )
        ],
        why_priority="Churn is #1 threat to ARR growth",
        confidence=0.85,
    )
    foundation.budget_constraints = BudgetConstraints(
        budget_range="$50K-$100K",
        budget_flexibility="flexible",
        timeline="Q2 2024",
        confidence=0.8,
    )
    foundation.confirmed_scope = ConfirmedScope(
        v1_features=["feat1", "feat2", "feat3"],
        v2_features=["feat4"],
        v1_agreed=True,
        specs_signed_off=True,
        confirmed_by="client",
    )
    return foundation


# =============================================================================
# Test Scenarios
# =============================================================================


class TestEmptyProject:
    """Test readiness scoring for an empty project."""

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_empty_project_has_low_score(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Empty project returns score < 40 and phase = insufficient."""
        mock_fetch_state.return_value = empty_project_data

        # Mock gate assessment - all gates unsatisfied
        empty_prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=False, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=False, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=False, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        empty_build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        mock_assess_gates.return_value = (
            empty_prototype_gates,
            empty_build_gates,
            0,  # gate_score
            ReadinessPhase.INSUFFICIENT,
        )

        readiness = compute_readiness(project_id)

        assert readiness.score < 40
        assert readiness.phase == "insufficient"
        assert readiness.ready is False
        assert readiness.gate_score == 0

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_empty_project_all_gates_unsatisfied(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Empty project has all gates unsatisfied."""
        mock_fetch_state.return_value = empty_project_data

        empty_prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=False, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=False, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=False, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        empty_build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        mock_assess_gates.return_value = (
            empty_prototype_gates,
            empty_build_gates,
            0,
            ReadinessPhase.INSUFFICIENT,
        )

        readiness = compute_readiness(project_id)

        # Check all gates unsatisfied
        assert all(
            not gate["satisfied"]
            for gate in readiness.gates["prototype_gates"].values()
        )
        assert all(
            not gate["satisfied"]
            for gate in readiness.gates["build_gates"].values()
        )

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_empty_project_has_blocking_gates(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Empty project has blocking gates in recommendations."""
        mock_fetch_state.return_value = empty_project_data

        empty_prototype_gates = {
            "core_pain": GateAssessment(
                name="Core Pain",
                satisfied=False,
                required=True,
                missing=["Pain statement"],
                how_to_acquire=["Ask about core problem"],
            ),
            "primary_persona": GateAssessment(
                name="Primary Persona",
                satisfied=False,
                required=True,
            ),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=False, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        empty_build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        mock_assess_gates.return_value = (
            empty_prototype_gates,
            empty_build_gates,
            0,
            ReadinessPhase.INSUFFICIENT,
        )

        readiness = compute_readiness(project_id)

        # Should have all required gates blocking
        assert "core_pain" in readiness.blocking_gates
        assert "primary_persona" in readiness.blocking_gates
        assert "wow_moment" in readiness.blocking_gates
        # design_preferences is optional, so should not block


class TestPrototypeReadyProject:
    """Test readiness scoring for a prototype-ready project."""

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_prototype_ready_phase_and_milestone(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Prototype-ready project has correct phase and milestone."""
        mock_fetch_state.return_value = empty_project_data

        # Mock prototype gates satisfied, build gates not
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True, confidence=1.0),
        }
        # Gate score: 40 (prototype) + 10 (confirmed_scope) = 50
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            50,  # gate_score
            ReadinessPhase.PROTOTYPE_READY,
        )

        readiness = compute_readiness(project_id)

        # Gate score should cap the final score at 50
        assert readiness.score <= 50
        assert readiness.gate_score == 50
        assert readiness.phase == "prototype_ready"
        assert readiness.prototype_ready is True
        assert readiness.build_ready is False

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_prototype_ready_has_build_gates_blocking(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Prototype-ready project has build gates blocking."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            50,
            ReadinessPhase.PROTOTYPE_READY,
        )

        readiness = compute_readiness(project_id)

        # Build gates should be blocking
        assert "business_case" in readiness.blocking_gates
        assert "budget_constraints" in readiness.blocking_gates
        assert "full_requirements" in readiness.blocking_gates

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_prototype_ready_next_milestone_is_build(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Prototype-ready project has next_milestone = 'build'."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            50,
            ReadinessPhase.PROTOTYPE_READY,
        )

        readiness = compute_readiness(project_id)

        assert readiness.next_milestone == "build"


class TestBuildReadyProject:
    """Test readiness scoring for a build-ready project."""

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_build_ready_phase_and_milestone(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Build-ready project has correct phase and milestone."""
        mock_fetch_state.return_value = empty_project_data

        # All gates satisfied
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=True, required=True, confidence=0.85),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True, confidence=0.8),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True, confidence=0.9),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True, confidence=1.0),
        }
        # All gates: 40 (prototype) + 60 (build) = 100
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            100,
            ReadinessPhase.BUILD_READY,
        )

        readiness = compute_readiness(project_id)

        # Gate score should cap at 100
        assert readiness.score <= 100
        assert readiness.gate_score == 100
        assert readiness.phase == "build_ready"
        assert readiness.prototype_ready is True
        assert readiness.build_ready is True

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_build_ready_no_blocking_gates(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Build-ready project has no blocking gates."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=True, required=True, confidence=0.85),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True, confidence=0.8),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True, confidence=0.9),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True, confidence=1.0),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            100,
            ReadinessPhase.BUILD_READY,
        )

        readiness = compute_readiness(project_id)

        assert len(readiness.blocking_gates) == 0

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_build_ready_next_milestone_is_complete(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Build-ready project has next_milestone = 'complete'."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=True, required=True, confidence=0.85),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True, confidence=0.8),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True, confidence=0.9),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True, confidence=1.0),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            100,
            ReadinessPhase.BUILD_READY,
        )

        readiness = compute_readiness(project_id)

        assert readiness.next_milestone == "complete"


class TestGateCeilingLogic:
    """Test gate ceiling application."""

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_gate_ceiling_exists_as_mechanism(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """Gate ceiling mechanism exists and correctly reports gate score."""
        mock_fetch_state.return_value = empty_project_data

        # Gates partially satisfied (score = 55)
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True, confidence=0.8),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        # Gate score: 40 (prototype) + 15 (budget_constraints) = 55
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            55,  # gate_score
            ReadinessPhase.PROTOTYPE_READY,
        )

        readiness = compute_readiness(project_id)

        # Gate score should be correctly reported
        assert readiness.gate_score == 55

        # Final score should never exceed gate score
        assert readiness.score <= 55


class TestCacheConsistency:
    """Test cache round-trip consistency."""

    @patch("app.core.readiness_cache.get_supabase")
    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_cache_round_trip(
        self, mock_fetch_state, mock_assess_gates, mock_supabase, project_id, empty_project_data
    ):
        """Compute fresh readiness, cache it, retrieve from cache, verify match."""
        from app.core.readiness_cache import update_project_readiness

        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True, confidence=0.85),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True, confidence=0.8),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True, confidence=0.75),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False, confidence=1.0),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            50,
            ReadinessPhase.PROTOTYPE_READY,
        )

        # Mock Supabase
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Compute fresh readiness
        fresh_readiness = compute_readiness(project_id)

        # Cache it
        cached_score = update_project_readiness(project_id)

        # Verify the update was called with correct data
        mock_supabase_instance.table.assert_called_with("projects")
        update_call = mock_supabase_instance.table.return_value.update

        # Check that cached data matches fresh computation
        assert cached_score == fresh_readiness.score / 100.0  # Stored as 0-1

        # Verify update was called
        assert update_call.called


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_readiness_score_structure(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """ReadinessScore has all expected fields for backward compatibility."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=False, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=False, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=False, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            0,
            ReadinessPhase.INSUFFICIENT,
        )

        readiness = compute_readiness(project_id)

        # Verify all expected fields exist
        assert hasattr(readiness, "score")
        assert hasattr(readiness, "ready")
        assert hasattr(readiness, "threshold")
        assert hasattr(readiness, "dimensions")
        assert hasattr(readiness, "caps_applied")
        assert hasattr(readiness, "top_recommendations")

        # Gate-based fields
        assert hasattr(readiness, "phase")
        assert hasattr(readiness, "prototype_ready")
        assert hasattr(readiness, "build_ready")
        assert hasattr(readiness, "gates")
        assert hasattr(readiness, "next_milestone")
        assert hasattr(readiness, "blocking_gates")
        assert hasattr(readiness, "gate_score")

        # Metadata fields
        assert hasattr(readiness, "computed_at")
        assert hasattr(readiness, "confirmed_entities")
        assert hasattr(readiness, "total_entities")
        assert hasattr(readiness, "client_signals_count")
        assert hasattr(readiness, "meetings_completed")

    @patch("app.core.readiness.score.assess_all_gates")
    @patch("app.core.readiness.score._fetch_project_state")
    def test_readiness_score_is_serializable(
        self, mock_fetch_state, mock_assess_gates, project_id, empty_project_data
    ):
        """ReadinessScore can be serialized to JSON."""
        mock_fetch_state.return_value = empty_project_data

        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=False, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=False, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=False, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }
        mock_assess_gates.return_value = (
            prototype_gates,
            build_gates,
            0,
            ReadinessPhase.INSUFFICIENT,
        )

        readiness = compute_readiness(project_id)

        # Should serialize to dict without errors
        serialized = readiness.model_dump(mode="json")

        assert isinstance(serialized, dict)
        assert "score" in serialized
        assert "phase" in serialized
        assert "gates" in serialized
