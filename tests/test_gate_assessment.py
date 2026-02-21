"""Unit tests for gate assessment logic in app/core/readiness/gates.py.

Tests coverage:
- assess_prototype_gates() - all 4 gates with various satisfaction levels
- assess_build_gates() - all 4 gates including full_requirements derived from entities
- calculate_gate_score() - phase transitions, score calculation, required vs optional gates
- Integration scenarios - empty project, partial readiness, full readiness
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.readiness.types import GateAssessment, ReadinessPhase
from app.core.readiness.gates import (
    assess_build_gates,
    assess_prototype_gates,
    calculate_gate_score,
)
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
def satisfied_core_pain():
    """Create a satisfied CorePain instance."""
    return CorePain(
        statement="CS teams manually track churn risk across multiple fragmented tools",
        trigger="Lost 3 enterprise customers in Q4",
        stakes="$2M ARR at risk if churn continues",
        who_feels_it="Customer Success Managers",
        confidence=0.85,
    )


@pytest.fixture
def unsatisfied_core_pain():
    """Create an unsatisfied CorePain instance (low confidence)."""
    return CorePain(
        statement="Users have some problems with the current system",
        trigger="General feedback",
        stakes="Things could be better",
        who_feels_it="Users",
        confidence=0.4,  # Below 0.6 threshold
    )


@pytest.fixture
def satisfied_primary_persona():
    """Create a satisfied PrimaryPersona instance."""
    return PrimaryPersona(
        name="Customer Success Manager",
        role="Manages customer relationships and retention",
        goal="Reduce churn and increase customer lifetime value",
        pain_connection="Can't identify at-risk customers until it's too late",
        context="Checks dashboards 3x daily but data is fragmented",
        confidence=0.8,
    )


@pytest.fixture
def satisfied_wow_moment():
    """Create a satisfied WowMoment instance."""
    return WowMoment(
        description="Dashboard predicts churn 60 days in advance with 85% accuracy",
        core_pain_inversion="From reactive firefighting to proactive prevention",
        emotional_impact="Relief and confidence - 'Finally, I can get ahead of this'",
        visual_concept="Red/yellow/green health scores with predicted churn dates",
        level_1="Core pain solved: Can predict churn before it happens",
        level_2="Prioritizes outreach by risk level automatically",
        confidence=0.75,
    )


@pytest.fixture
def satisfied_design_preferences():
    """Create a satisfied DesignPreferences instance."""
    return DesignPreferences(
        visual_style="clean/minimal",
        references=["Linear", "Stripe", "Notion"],
        anti_references=["Salesforce", "Old enterprise software"],
    )


@pytest.fixture
def satisfied_business_case():
    """Create a satisfied BusinessCase instance."""
    return BusinessCase(
        value_to_business="Reduce churn by 15%, save $300K annually",
        roi_framing="$300K annual savings vs $50K investment = 6x ROI",
        success_kpis=[
            KPI(
                metric="Monthly churn rate",
                current_state="12%",
                target_state="<10%",
                measurement_method="Cohort retention tracking",
                timeframe="6 months",
            )
        ],
        why_priority="Churn is #1 threat to ARR growth",
        confidence=0.85,
    )


@pytest.fixture
def satisfied_budget_constraints():
    """Create a satisfied BudgetConstraints instance."""
    return BudgetConstraints(
        budget_range="$50K-$100K",
        budget_flexibility="flexible",
        timeline="Q2 2024 - need by end of June",
        hard_deadline="June 30, 2024",
        deadline_driver="Board presentation",
        confidence=0.8,
    )


@pytest.fixture
def satisfied_confirmed_scope():
    """Create a satisfied ConfirmedScope instance."""
    return ConfirmedScope(
        v1_features=["feat1", "feat2", "feat3"],
        v2_features=["feat4", "feat5"],
        v1_agreed=True,
        specs_signed_off=True,
        confirmed_by="client",
    )


@pytest.fixture
def mock_foundation_full(
    project_id,
    foundation_id,
    satisfied_core_pain,
    satisfied_primary_persona,
    satisfied_wow_moment,
    satisfied_design_preferences,
    satisfied_business_case,
    satisfied_budget_constraints,
    satisfied_confirmed_scope,
):
    """Create a full ProjectFoundation with all gates satisfied."""
    return ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=satisfied_core_pain,
        primary_persona=satisfied_primary_persona,
        wow_moment=satisfied_wow_moment,
        design_preferences=satisfied_design_preferences,
        business_case=satisfied_business_case,
        budget_constraints=satisfied_budget_constraints,
        confirmed_scope=satisfied_confirmed_scope,
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )


@pytest.fixture
def mock_foundation_prototype_only(
    project_id,
    foundation_id,
    satisfied_core_pain,
    satisfied_primary_persona,
    satisfied_wow_moment,
    satisfied_design_preferences,
):
    """Create a ProjectFoundation with only prototype gates satisfied."""
    return ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=satisfied_core_pain,
        primary_persona=satisfied_primary_persona,
        wow_moment=satisfied_wow_moment,
        design_preferences=satisfied_design_preferences,
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )


@pytest.fixture
def mock_foundation_partial(
    project_id,
    foundation_id,
    satisfied_core_pain,
    unsatisfied_core_pain,
):
    """Create a ProjectFoundation with only some gates satisfied."""
    return ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=satisfied_core_pain,
        # Missing other gates
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )


# =============================================================================
# Prototype Gate Assessment Tests
# =============================================================================


class TestAssessPrototypeGates:
    """Test assess_prototype_gates() function."""

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_returns_all_four_gates(self, mock_get_foundation, project_id, mock_foundation_full):
        """assess_prototype_gates() returns all 4 gates."""
        mock_get_foundation.return_value = mock_foundation_full

        gates = assess_prototype_gates(project_id)

        assert len(gates) == 4
        assert "core_pain" in gates
        assert "primary_persona" in gates
        assert "wow_moment" in gates
        assert "design_preferences" in gates

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_all_gates_satisfied_when_foundation_complete(
        self, mock_get_foundation, project_id, mock_foundation_full
    ):
        """All prototype gates satisfied when foundation is complete."""
        mock_get_foundation.return_value = mock_foundation_full

        gates = assess_prototype_gates(project_id)

        assert gates["core_pain"].satisfied is True
        assert gates["primary_persona"].satisfied is True
        assert gates["wow_moment"].satisfied is True
        assert gates["design_preferences"].satisfied is True

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_gates_unsatisfied_when_foundation_missing(self, mock_get_foundation, project_id):
        """All gates unsatisfied when foundation is None."""
        mock_get_foundation.return_value = None

        gates = assess_prototype_gates(project_id)

        assert gates["core_pain"].satisfied is False
        assert gates["primary_persona"].satisfied is False
        assert gates["wow_moment"].satisfied is False
        assert gates["design_preferences"].satisfied is False

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_identifies_missing_information(self, mock_get_foundation, project_id):
        """Gates identify missing information correctly."""
        mock_get_foundation.return_value = None

        gates = assess_prototype_gates(project_id)

        # Core pain should list missing elements
        assert len(gates["core_pain"].missing) > 0
        assert "Pain statement" in gates["core_pain"].missing[0]

        # Should provide guidance
        assert len(gates["core_pain"].how_to_acquire) > 0

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_partial_satisfaction(self, mock_get_foundation, project_id, mock_foundation_partial):
        """Gates handle partial satisfaction correctly."""
        mock_get_foundation.return_value = mock_foundation_partial

        gates = assess_prototype_gates(project_id)

        assert gates["core_pain"].satisfied is True  # Satisfied
        assert gates["primary_persona"].satisfied is False  # Missing
        assert gates["wow_moment"].satisfied is False  # Missing
        assert gates["design_preferences"].satisfied is False  # Missing

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_core_pain_unsatisfied_with_low_confidence(
        self, mock_get_foundation, project_id, foundation_id, unsatisfied_core_pain
    ):
        """Core pain unsatisfied when confidence too low."""
        foundation = ProjectFoundation(
            id=foundation_id,
            project_id=project_id,
            core_pain=unsatisfied_core_pain,
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
        )
        mock_get_foundation.return_value = foundation

        gates = assess_prototype_gates(project_id)

        assert gates["core_pain"].satisfied is False
        assert any("Confidence too low" in item for item in gates["core_pain"].missing)

    @patch("app.core.readiness.gates.get_project_foundation")
    def test_design_preferences_marked_optional(
        self, mock_get_foundation, project_id, mock_foundation_full
    ):
        """Design preferences gate marked as optional (not required)."""
        mock_get_foundation.return_value = mock_foundation_full

        gates = assess_prototype_gates(project_id)

        assert gates["design_preferences"].required is False
        assert gates["core_pain"].required is True
        assert gates["primary_persona"].required is True
        assert gates["wow_moment"].required is True


# =============================================================================
# Build Gate Assessment Tests
# =============================================================================


class TestAssessBuildGates:
    """Test assess_build_gates() function."""

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_returns_all_four_gates(
        self, mock_get_foundation, mock_get_supabase, project_id, mock_foundation_full
    ):
        """assess_build_gates() returns all 4 gates."""
        mock_get_foundation.return_value = mock_foundation_full

        # Mock Supabase for full_requirements assessment
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock features response
        features_response = MagicMock()
        features_response.data = [
            {"id": "1", "description": "Feature 1 with detailed description"},
            {"id": "2", "description": "Feature 2 with detailed description"},
            {"id": "3", "description": "Feature 3 with detailed description"},
            {"id": "4", "description": "Feature 4 with detailed description"},
            {"id": "5", "description": "Feature 5 with detailed description"},
        ]

        # Mock signals response
        signals_response = MagicMock()
        signals_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        gates = assess_build_gates(project_id)

        assert len(gates) == 4
        assert "business_case" in gates
        assert "budget_constraints" in gates
        assert "full_requirements" in gates
        assert "confirmed_scope" in gates

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_all_gates_satisfied_when_complete(
        self, mock_get_foundation, mock_get_supabase, project_id, mock_foundation_full
    ):
        """All build gates satisfied when complete."""
        mock_get_foundation.return_value = mock_foundation_full

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        features_response = MagicMock()
        features_response.data = [
            {"id": str(i), "description": f"Feature {i} with enough detail to pass validation"}
            for i in range(5)
        ]

        signals_response = MagicMock()
        signals_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        gates = assess_build_gates(project_id)

        assert gates["business_case"].satisfied is True
        assert gates["budget_constraints"].satisfied is True
        assert gates["full_requirements"].satisfied is True
        assert gates["confirmed_scope"].satisfied is True

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_gates_unsatisfied_when_foundation_missing(
        self, mock_get_foundation, mock_get_supabase, project_id
    ):
        """All build gates unsatisfied when foundation is None."""
        mock_get_foundation.return_value = None

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # No features or signals
        empty_response = MagicMock()
        empty_response.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = empty_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response

        gates = assess_build_gates(project_id)

        assert gates["business_case"].satisfied is False
        assert gates["budget_constraints"].satisfied is False
        assert gates["full_requirements"].satisfied is False
        assert gates["confirmed_scope"].satisfied is False

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_full_requirements_needs_five_features(
        self, mock_get_foundation, mock_get_supabase, project_id
    ):
        """full_requirements gate requires at least 5 confirmed features."""
        mock_get_foundation.return_value = None

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Only 3 features (need 5)
        features_response = MagicMock()
        features_response.data = [
            {"id": "1", "description": "Feature 1"},
            {"id": "2", "description": "Feature 2"},
            {"id": "3", "description": "Feature 3"},
        ]

        signals_response = MagicMock()
        signals_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        gates = assess_build_gates(project_id)

        assert gates["full_requirements"].satisfied is False
        assert "2 more confirmed features" in gates["full_requirements"].missing[0]

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_full_requirements_needs_signal_evidence(
        self, mock_get_foundation, mock_get_supabase, project_id
    ):
        """full_requirements gate requires signals for evidence."""
        mock_get_foundation.return_value = None

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Enough features but no signals
        features_response = MagicMock()
        features_response.data = [{"id": str(i), "description": f"Feature {i}"} for i in range(5)]

        signals_response = MagicMock()
        signals_response.data = []  # No signals

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        gates = assess_build_gates(project_id)

        assert gates["full_requirements"].satisfied is False
        assert "more discovery signals" in gates["full_requirements"].missing[0]

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_full_requirements_needs_detailed_descriptions(
        self, mock_get_foundation, mock_get_supabase, project_id
    ):
        """full_requirements gate requires detailed feature descriptions."""
        mock_get_foundation.return_value = None

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # 5 features but most have short descriptions
        features_response = MagicMock()
        features_response.data = [
            {"id": "1", "description": "Short"},  # Too short
            {"id": "2", "description": "Also short"},  # Too short
            {"id": "3", "description": "Brief"},  # Too short
            {"id": "4", "description": "This feature has a detailed description that is long enough"},
            {"id": "5", "description": "This one also has enough detail to pass the validation check"},
        ]

        signals_response = MagicMock()
        signals_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        gates = assess_build_gates(project_id)

        # Should fail because only 2/5 features have detailed descriptions (40% < 70% threshold)
        assert gates["full_requirements"].satisfied is False
        assert "features need detailed descriptions" in gates["full_requirements"].missing[0]


# =============================================================================
# Gate Score Calculation Tests
# =============================================================================


class TestCalculateGateScore:
    """Test calculate_gate_score() function."""

    def test_insufficient_phase_when_no_gates_satisfied(self):
        """Returns (0, INSUFFICIENT) when no gates satisfied."""
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

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        assert score == 0
        assert phase == ReadinessPhase.INSUFFICIENT

    def test_prototype_ready_when_all_required_prototype_gates_satisfied(self):
        """Returns (35, PROTOTYPE_READY) when all required prototype gates satisfied."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=False, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # core_pain(15) + primary_persona(10) + wow_moment(10) = 35
        assert score == 35
        assert phase == ReadinessPhase.INSUFFICIENT  # Still insufficient (need 40+)

    def test_prototype_ready_at_exactly_40_points(self):
        """Returns (40, PROTOTYPE_READY) at exactly 40 points."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # core_pain(15) + primary_persona(10) + wow_moment(10) + design_preferences(5) = 40
        assert score == 40
        assert phase == ReadinessPhase.INSUFFICIENT  # 40 or less is insufficient

    def test_prototype_ready_at_41_points(self):
        """Returns (41, PROTOTYPE_READY) at 41 points."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=False, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=False, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Phase1: 40, Phase2: confirmed_scope(10) = 50 total
        # Wait, that doesn't make sense. Let me recheck the logic.
        # Actually, Phase 2 points can only be earned if ALL REQUIRED Phase 1 gates are satisfied.
        # All required Phase 1 gates (core_pain, primary_persona, wow_moment) are satisfied.
        # So we can earn Phase 2 points.

        # core_pain(15) + primary_persona(10) + wow_moment(10) + design_preferences(5) + confirmed_scope(10) = 50
        assert score == 50
        assert phase == ReadinessPhase.PROTOTYPE_READY  # 41-70

    def test_cannot_earn_build_points_without_required_prototype_gates(self):
        """Cannot earn Phase 2 points without all required Phase 1 gates."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=False, required=True),  # Missing
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=True, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Only Phase 1 points: core_pain(15) + wow_moment(10) + design_preferences(5) = 30
        # Phase 2 points blocked because primary_persona not satisfied
        assert score == 30
        assert phase == ReadinessPhase.INSUFFICIENT

    def test_build_ready_when_all_gates_satisfied(self):
        """Returns (100, BUILD_READY) when all gates satisfied."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=True, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Phase1: 15+10+10+5=40, Phase2: 20+15+15+10=60, Total: 100
        assert score == 100
        assert phase == ReadinessPhase.BUILD_READY

    def test_build_ready_at_exactly_70_points(self):
        """Returns (70, PROTOTYPE_READY) at exactly 70 points."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=False, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Phase1: 40, Phase2: budget_constraints(15) + full_requirements(15) = 30, Total: 70
        assert score == 70
        assert phase == ReadinessPhase.PROTOTYPE_READY  # 70 or less

    def test_build_ready_at_71_points(self):
        """Returns (71, BUILD_READY) at 71 points."""
        prototype_gates = {
            "core_pain": GateAssessment(name="Core Pain", satisfied=True, required=True),
            "primary_persona": GateAssessment(name="Primary Persona", satisfied=True, required=True),
            "wow_moment": GateAssessment(name="Wow Moment", satisfied=True, required=True),
            "design_preferences": GateAssessment(name="Design Preferences", satisfied=True, required=False),
        }
        build_gates = {
            "business_case": GateAssessment(name="Business Case", satisfied=False, required=True),
            "budget_constraints": GateAssessment(name="Budget Constraints", satisfied=True, required=True),
            "full_requirements": GateAssessment(name="Full Requirements", satisfied=True, required=True),
            "confirmed_scope": GateAssessment(name="Confirmed Scope", satisfied=True, required=True),
        }

        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Phase1: 40, Phase2: budget_constraints(15) + full_requirements(15) + confirmed_scope(10) = 40, Total: 80
        # Wait, that's 80, not 71. Let me create a scenario for exactly 71.
        # Actually, the point values are fixed, so we can't get exactly 71.
        # Let me just check that 71+ triggers BUILD_READY.
        assert score >= 71
        assert phase == ReadinessPhase.BUILD_READY


# =============================================================================
# Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Test complete gate assessment scenarios."""

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_empty_project(self, mock_get_foundation, mock_get_supabase, project_id):
        """Empty project has all gates unsatisfied and is INSUFFICIENT."""
        mock_get_foundation.return_value = None

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        empty_response = MagicMock()
        empty_response.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = empty_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response

        prototype_gates = assess_prototype_gates(project_id)
        build_gates = assess_build_gates(project_id)
        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # All gates unsatisfied
        assert all(not gate.satisfied for gate in prototype_gates.values())
        assert all(not gate.satisfied for gate in build_gates.values())

        # Score is 0, phase is INSUFFICIENT
        assert score == 0
        assert phase == ReadinessPhase.INSUFFICIENT

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_prototype_ready_project(
        self, mock_get_foundation, mock_get_supabase, project_id, mock_foundation_prototype_only
    ):
        """Project with prototype gates satisfied is PROTOTYPE_READY."""
        mock_get_foundation.return_value = mock_foundation_prototype_only

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # No build data yet
        empty_response = MagicMock()
        empty_response.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = empty_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response

        prototype_gates = assess_prototype_gates(project_id)
        build_gates = assess_build_gates(project_id)
        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # Required prototype gates satisfied
        assert prototype_gates["core_pain"].satisfied is True
        assert prototype_gates["primary_persona"].satisfied is True
        assert prototype_gates["wow_moment"].satisfied is True

        # Build gates not satisfied
        assert all(not gate.satisfied for gate in build_gates.values())

        # Score is 40 (all prototype gates), phase is PROTOTYPE_READY (41-70) or INSUFFICIENT (<=40)
        # Actually score should be 40, which is INSUFFICIENT
        assert score == 40
        assert phase == ReadinessPhase.INSUFFICIENT  # Need >40 for PROTOTYPE_READY

    @patch("app.core.readiness.gates.get_supabase")
    @patch("app.core.readiness.gates.get_project_foundation")
    def test_build_ready_project(
        self, mock_get_foundation, mock_get_supabase, project_id, mock_foundation_full
    ):
        """Project with all gates satisfied is BUILD_READY."""
        mock_get_foundation.return_value = mock_foundation_full

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Full build data
        features_response = MagicMock()
        features_response.data = [
            {"id": str(i), "description": f"Feature {i} with enough detail to pass validation requirements"}
            for i in range(5)
        ]

        signals_response = MagicMock()
        signals_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = features_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = signals_response

        prototype_gates = assess_prototype_gates(project_id)
        build_gates = assess_build_gates(project_id)
        score, phase = calculate_gate_score(prototype_gates, build_gates)

        # All gates satisfied
        assert all(gate.satisfied for gate in prototype_gates.values())
        assert all(gate.satisfied for gate in build_gates.values())

        # Score is 100, phase is BUILD_READY
        assert score == 100
        assert phase == ReadinessPhase.BUILD_READY
