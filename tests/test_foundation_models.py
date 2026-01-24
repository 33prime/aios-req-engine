"""Unit tests for foundation Pydantic models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_foundation import (
    BusinessCase,
    BudgetConstraints,
    ConfirmedScope,
    CorePain,
    DesignPreferences,
    FoundationUpdateRequest,
    KPI,
    PrimaryPersona,
    ProjectFoundation,
    WowMoment,
)


# =============================================================================
# CorePain Tests
# =============================================================================


def test_core_pain_is_satisfied_when_valid():
    """CorePain.is_satisfied() returns True when all requirements met."""
    pain = CorePain(
        statement="Can't see which customers are churning until they've already left",
        trigger="Lost 3 enterprise customers in Q4",
        stakes="$2M ARR at risk if we can't predict churn",
        who_feels_it="Customer Success Manager",
        confidence=0.85,
        evidence=["signal_123", "signal_456"],
    )

    assert pain.is_satisfied() is True


def test_core_pain_not_satisfied_when_low_confidence():
    """CorePain.is_satisfied() returns False when confidence < 0.6."""
    pain = CorePain(
        statement="Can't see which customers are churning until they've already left",
        trigger="Lost 3 enterprise customers in Q4",
        stakes="$2M ARR at risk",
        who_feels_it="Customer Success Manager",
        confidence=0.4,  # Too low
    )

    assert pain.is_satisfied() is False


def test_core_pain_not_satisfied_when_statement_too_short():
    """CorePain raises ValidationError when statement < 20 chars."""
    with pytest.raises(ValidationError) as exc_info:
        CorePain(
            statement="Short problem",  # Only 13 chars
            trigger="Lost customers",
            stakes="Revenue at risk",
            who_feels_it="CSM",
            confidence=0.85,
        )

    assert "at least 20 characters" in str(exc_info.value)


def test_core_pain_validates_empty_statement():
    """CorePain raises ValidationError for empty statement."""
    with pytest.raises(ValidationError) as exc_info:
        CorePain(
            statement="   ",  # Empty/whitespace
            trigger="Lost customers",
            stakes="Revenue at risk",
            who_feels_it="CSM",
            confidence=0.85,
        )

    # Empty whitespace triggers the min_length validator
    assert "at least 20 characters" in str(exc_info.value)


def test_core_pain_trims_whitespace():
    """CorePain trims whitespace from statement."""
    pain = CorePain(
        statement="  Problem with whitespace  ",
        trigger="Trigger",
        stakes="Stakes",
        who_feels_it="Person",
        confidence=0.8,
    )

    assert pain.statement == "Problem with whitespace"


def test_core_pain_serialization():
    """CorePain can serialize to and from dict."""
    pain = CorePain(
        statement="Can't predict churn risk accurately",  # At least 20 chars
        trigger="Lost customers",
        stakes="Revenue risk",
        who_feels_it="CSM",
        confidence=0.8,
        confirmed_by="consultant",
        evidence=["sig1"],
    )

    # To dict
    data = pain.model_dump()
    assert data["statement"] == "Can't predict churn risk accurately"
    assert data["confidence"] == 0.8
    assert data["confirmed_by"] == "consultant"

    # From dict
    pain2 = CorePain(**data)
    assert pain2.statement == pain.statement
    assert pain2.confidence == pain.confidence


# =============================================================================
# PrimaryPersona Tests
# =============================================================================


def test_primary_persona_is_satisfied_when_valid():
    """PrimaryPersona.is_satisfied() returns True when requirements met."""
    persona = PrimaryPersona(
        name="Customer Success Manager",
        role="Manages customer relationships and retention",
        goal="Keep customers happy and reduce churn",
        pain_connection="Can't identify at-risk customers until too late",
        context="Reviews accounts daily, reactive not proactive",
        confidence=0.75,
    )

    assert persona.is_satisfied() is True


def test_primary_persona_not_satisfied_when_low_confidence_v2():
    """PrimaryPersona.is_satisfied() returns False at confidence boundary."""
    persona = PrimaryPersona(
        name="CSM",
        role="Manager",
        goal="Reduce churn",
        pain_connection="Can't see churn risk",
        context="Daily work",
        confidence=0.59,  # Just below threshold
    )

    assert persona.is_satisfied() is False


def test_primary_persona_not_satisfied_when_low_confidence():
    """PrimaryPersona.is_satisfied() returns False when confidence < 0.6."""
    persona = PrimaryPersona(
        name="CSM",
        role="Manager",
        goal="Reduce churn",
        pain_connection="Can't see churn risk",
        context="Daily work",
        confidence=0.5,  # Too low
    )

    assert persona.is_satisfied() is False


# =============================================================================
# WowMoment Tests
# =============================================================================


def test_wow_moment_is_satisfied_when_valid():
    """WowMoment.is_satisfied() returns True when requirements met."""
    wow = WowMoment(
        description="Dashboard shows at-risk customers 60 days before churn",
        core_pain_inversion="From reactive to proactive - seeing the future not the past",
        emotional_impact="Relief and confidence - 'Finally, I can get ahead of this'",
        visual_concept="Red/yellow/green health scores with predicted churn dates",
        level_1="Core pain solved: Can predict churn before it happens",
        level_2="Adjacent pain: Prioritizes outreach by risk level",
        level_3="Unstated need: Identifies upsell opportunities in healthy accounts",
        confidence=0.7,
    )

    assert wow.is_satisfied() is True


def test_wow_moment_satisfied_with_lower_confidence():
    """WowMoment.is_satisfied() accepts confidence >= 0.5 (hypothesis stage)."""
    wow = WowMoment(
        description="Dashboard with predictions",
        core_pain_inversion="Proactive not reactive",
        emotional_impact="Relief",
        visual_concept="Health scores",
        level_1="Predict churn",
        confidence=0.5,  # Minimum for hypothesis
    )

    assert wow.is_satisfied() is True


def test_wow_moment_not_satisfied_when_too_low_confidence():
    """WowMoment.is_satisfied() returns False when confidence < 0.5."""
    wow = WowMoment(
        description="Dashboard",
        core_pain_inversion="Proactive",
        emotional_impact="Relief",
        visual_concept="Scores",
        level_1="Predict",
        confidence=0.4,  # Too low
    )

    assert wow.is_satisfied() is False


# =============================================================================
# DesignPreferences Tests
# =============================================================================


def test_design_preferences_satisfied_with_visual_style():
    """DesignPreferences.is_satisfied() returns True with visual_style."""
    prefs = DesignPreferences(
        visual_style="clean/minimal",
    )

    assert prefs.is_satisfied() is True


def test_design_preferences_satisfied_with_references():
    """DesignPreferences.is_satisfied() returns True with references."""
    prefs = DesignPreferences(
        references=["Linear", "Notion"],
    )

    assert prefs.is_satisfied() is True


def test_design_preferences_not_satisfied_when_empty():
    """DesignPreferences.is_satisfied() returns False when no data."""
    prefs = DesignPreferences()

    assert prefs.is_satisfied() is False


# =============================================================================
# BusinessCase Tests
# =============================================================================


def test_business_case_is_satisfied_when_valid():
    """BusinessCase.is_satisfied() returns True when requirements met."""
    case = BusinessCase(
        value_to_business="Reduce churn by 15%, save $300K/year",
        roi_framing="$300K annual savings vs $50K investment = 6x ROI",
        success_kpis=[
            KPI(
                metric="Churn rate",
                current_state="12% monthly",
                target_state="<10% monthly",
                measurement_method="Track monthly cohort retention",
                timeframe="6 months",
            )
        ],
        why_priority="Churn is #1 threat to ARR growth",
        confidence=0.8,
    )

    assert case.is_satisfied() is True


def test_business_case_not_satisfied_without_kpis():
    """BusinessCase.is_satisfied() returns False without KPIs."""
    case = BusinessCase(
        value_to_business="Reduce churn",
        roi_framing="High ROI",
        success_kpis=[],  # No KPIs
        why_priority="Important",
        confidence=0.8,
    )

    assert case.is_satisfied() is False


def test_business_case_not_satisfied_when_low_confidence():
    """BusinessCase.is_satisfied() returns False when confidence < 0.7."""
    case = BusinessCase(
        value_to_business="Reduce churn",
        roi_framing="High ROI",
        success_kpis=[
            KPI(
                metric="Churn",
                current_state="High",
                target_state="Low",
                measurement_method="Track",
                timeframe="6mo",
            )
        ],
        why_priority="Important",
        confidence=0.6,  # Too low
    )

    assert case.is_satisfied() is False


# =============================================================================
# BudgetConstraints Tests
# =============================================================================


def test_budget_constraints_is_satisfied_when_valid():
    """BudgetConstraints.is_satisfied() returns True when requirements met."""
    constraints = BudgetConstraints(
        budget_range="$5K-10K one-time",
        budget_flexibility="flexible",
        timeline="Need by end of Q2",
        technical_constraints=["Must integrate with Salesforce"],
        confidence=0.8,
    )

    assert constraints.is_satisfied() is True


def test_budget_constraints_not_satisfied_when_low_confidence():
    """BudgetConstraints.is_satisfied() returns False when confidence < 0.7."""
    constraints = BudgetConstraints(
        budget_range="$5K-10K",
        budget_flexibility="unknown",
        timeline="ASAP",
        confidence=0.5,  # Too low
    )

    assert constraints.is_satisfied() is False


# =============================================================================
# ConfirmedScope Tests
# =============================================================================


def test_confirmed_scope_is_satisfied_when_valid():
    """ConfirmedScope.is_satisfied() returns True when requirements met."""
    scope = ConfirmedScope(
        v1_features=["feat1", "feat2", "feat3"],
        v2_features=["feat4", "feat5"],
        v1_agreed=True,
        specs_signed_off=True,
        confirmed_by="client",
    )

    assert scope.is_satisfied() is True


def test_confirmed_scope_not_satisfied_without_client_confirmation():
    """ConfirmedScope.is_satisfied() returns False without client confirmation."""
    scope = ConfirmedScope(
        v1_features=["feat1", "feat2"],
        v1_agreed=True,
        confirmed_by="consultant",  # Must be client
    )

    assert scope.is_satisfied() is False


def test_confirmed_scope_not_satisfied_without_v1_agreement():
    """ConfirmedScope.is_satisfied() returns False without v1_agreed."""
    scope = ConfirmedScope(
        v1_features=["feat1", "feat2"],
        v1_agreed=False,  # Not agreed
        confirmed_by="client",
    )

    assert scope.is_satisfied() is False


def test_confirmed_scope_not_satisfied_without_features():
    """ConfirmedScope.is_satisfied() returns False without v1_features."""
    scope = ConfirmedScope(
        v1_features=[],  # No features
        v1_agreed=True,
        confirmed_by="client",
    )

    assert scope.is_satisfied() is False


# =============================================================================
# KPI Tests
# =============================================================================


def test_kpi_creation():
    """KPI can be created with all required fields."""
    kpi = KPI(
        metric="Churn rate",
        current_state="12% monthly",
        target_state="<10% monthly",
        measurement_method="Track monthly cohort retention",
        timeframe="6 months",
    )

    assert kpi.metric == "Churn rate"
    assert kpi.current_state == "12% monthly"
    assert kpi.target_state == "<10% monthly"
    assert kpi.measurement_method == "Track monthly cohort retention"
    assert kpi.timeframe == "6 months"


def test_kpi_serialization():
    """KPI can serialize to and from dict."""
    original = KPI(
        metric="ARR",
        current_state="$2M",
        target_state="$5M",
        measurement_method="Financial reports",
        timeframe="12 months",
    )

    data = original.model_dump()
    restored = KPI(**data)

    assert restored.metric == original.metric
    assert restored.current_state == original.current_state
    assert restored.target_state == original.target_state


# =============================================================================
# Additional Serialization Tests
# =============================================================================


def test_primary_persona_serialization():
    """PrimaryPersona can serialize to and from dict."""
    original = PrimaryPersona(
        name="Development Director",
        role="Fundraising and donor relations",
        goal="Increase major donor retention",
        pain_connection="Can't identify at-risk major donors before they lapse",
        context="Reviews donor data monthly, too late to act",
        confidence=0.85,
        confirmed_by="client",
    )

    data = original.model_dump()
    restored = PrimaryPersona(**data)

    assert restored.name == original.name
    assert restored.role == original.role
    assert restored.goal == original.goal
    assert restored.pain_connection == original.pain_connection
    assert restored.confidence == original.confidence


def test_wow_moment_serialization():
    """WowMoment can serialize to and from dict."""
    original = WowMoment(
        description="Dashboard predicts churn 60 days in advance",
        core_pain_inversion="From reactive to proactive",
        emotional_impact="Relief and confidence",
        visual_concept="Red/yellow/green health scores",
        level_1="Core pain solved",
        level_2="Prioritizes outreach",
        level_3="Identifies upsell opportunities",
        confidence=0.75,
    )

    data = original.model_dump()
    restored = WowMoment(**data)

    assert restored.description == original.description
    assert restored.core_pain_inversion == original.core_pain_inversion
    assert restored.level_1 == original.level_1
    assert restored.level_2 == original.level_2
    assert restored.level_3 == original.level_3


def test_business_case_serialization():
    """BusinessCase can serialize to and from dict."""
    original = BusinessCase(
        value_to_business="Reduce churn by 15%",
        roi_framing="$300K annual savings",
        success_kpis=[
            KPI(
                metric="Churn",
                current_state="12%",
                target_state="<10%",
                measurement_method="Monthly tracking",
                timeframe="6 months",
            )
        ],
        why_priority="Churn threatens growth",
        confidence=0.8,
        confirmed_by="consultant",
    )

    data = original.model_dump()
    restored = BusinessCase(**data)

    assert restored.value_to_business == original.value_to_business
    assert restored.roi_framing == original.roi_framing
    assert len(restored.success_kpis) == len(original.success_kpis)
    assert restored.success_kpis[0].metric == original.success_kpis[0].metric


def test_budget_constraints_serialization():
    """BudgetConstraints can serialize to and from dict."""
    original = BudgetConstraints(
        budget_range="$50K-$100K",
        budget_flexibility="flexible",
        timeline="Q2 2024",
        hard_deadline="June 30, 2024",
        deadline_driver="Board presentation",
        technical_constraints=["Must integrate with Salesforce"],
        organizational_constraints=["Board approval required"],
        confidence=0.75,
        confirmed_by="client",
    )

    data = original.model_dump()
    restored = BudgetConstraints(**data)

    assert restored.budget_range == original.budget_range
    assert restored.budget_flexibility == original.budget_flexibility
    assert restored.timeline == original.timeline
    assert restored.hard_deadline == original.hard_deadline


def test_confirmed_scope_serialization():
    """ConfirmedScope can serialize to and from dict."""
    original = ConfirmedScope(
        v1_features=["feat1", "feat2", "feat3"],
        v2_features=["feat4", "feat5"],
        v1_agreed=True,
        specs_signed_off=True,
        confirmed_by="client",
    )

    data = original.model_dump()
    restored = ConfirmedScope(**data)

    assert restored.v1_features == original.v1_features
    assert restored.v2_features == original.v2_features
    assert restored.v1_agreed == original.v1_agreed
    assert restored.specs_signed_off == original.specs_signed_off


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_confidence_boundary_values():
    """Test confidence at exact boundaries (0.0 and 1.0)."""
    # Minimum confidence
    pain_min = CorePain(
        statement="This is a valid problem statement with enough characters",
        trigger="Trigger",
        stakes="Stakes",
        who_feels_it="User",
        confidence=0.0,
    )
    assert pain_min.confidence == 0.0
    assert pain_min.is_satisfied() is False  # Below 0.6 threshold

    # Maximum confidence
    pain_max = CorePain(
        statement="This is a valid problem statement with enough characters",
        trigger="Trigger",
        stakes="Stakes",
        who_feels_it="User",
        confidence=1.0,
    )
    assert pain_max.confidence == 1.0
    assert pain_max.is_satisfied() is True


def test_confidence_out_of_range():
    """Test that confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CorePain(
            statement="This is a valid problem statement with enough characters",
            trigger="Trigger",
            stakes="Stakes",
            who_feels_it="User",
            confidence=1.5,  # Too high
        )

    assert "less than or equal to 1" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        CorePain(
            statement="This is a valid problem statement with enough characters",
            trigger="Trigger",
            stakes="Stakes",
            who_feels_it="User",
            confidence=-0.1,  # Too low
        )

    assert "greater than or equal to 0" in str(exc_info.value)


def test_wow_moment_optional_levels():
    """Test WowMoment with optional level_2 and level_3."""
    # Only level_1
    wow_minimal = WowMoment(
        description="Dashboard shows predictions",
        core_pain_inversion="Proactive not reactive",
        emotional_impact="Relief",
        visual_concept="Health scores",
        level_1="Core pain solved",
        confidence=0.6,
    )
    assert wow_minimal.level_2 is None
    assert wow_minimal.level_3 is None
    assert wow_minimal.is_satisfied() is True

    # With level_2
    wow_with_2 = WowMoment(
        description="Dashboard shows predictions",
        core_pain_inversion="Proactive not reactive",
        emotional_impact="Relief",
        visual_concept="Health scores",
        level_1="Core pain solved",
        level_2="Adjacent pain addressed",
        confidence=0.6,
    )
    assert wow_with_2.level_2 is not None
    assert wow_with_2.level_3 is None

    # With all levels
    wow_full = WowMoment(
        description="Dashboard shows predictions",
        core_pain_inversion="Proactive not reactive",
        emotional_impact="Relief",
        visual_concept="Health scores",
        level_1="Core pain solved",
        level_2="Adjacent pain addressed",
        level_3="Unstated need met",
        confidence=0.6,
    )
    assert wow_full.level_2 is not None
    assert wow_full.level_3 is not None


def test_design_preferences_multiple_references():
    """Test DesignPreferences with multiple references."""
    prefs = DesignPreferences(
        visual_style="clean/minimal",
        references=["Linear", "Notion", "Stripe"],
        anti_references=["Old enterprise software", "Cluttered dashboards"],
        specific_requirements=["WCAG AA", "Mobile first", "Dark mode"],
    )

    assert len(prefs.references) == 3
    assert len(prefs.anti_references) == 2
    assert len(prefs.specific_requirements) == 3
    assert prefs.is_satisfied() is True


def test_business_case_multiple_kpis():
    """Test BusinessCase with multiple KPIs."""
    case = BusinessCase(
        value_to_business="Reduce churn and increase revenue",
        roi_framing="$500K annual impact",
        success_kpis=[
            KPI(
                metric="Churn rate",
                current_state="12%",
                target_state="<10%",
                measurement_method="Monthly cohort tracking",
                timeframe="6 months",
            ),
            KPI(
                metric="ARR",
                current_state="$2M",
                target_state="$3M",
                measurement_method="Financial reports",
                timeframe="12 months",
            ),
            KPI(
                metric="NPS",
                current_state="45",
                target_state="60+",
                measurement_method="Quarterly surveys",
                timeframe="6 months",
            ),
        ],
        why_priority="Critical for growth",
        confidence=0.85,
    )

    assert len(case.success_kpis) == 3
    assert case.is_satisfied() is True


def test_budget_constraints_flexibility_options():
    """Test BudgetConstraints with all flexibility options."""
    # Firm budget
    firm = BudgetConstraints(
        budget_range="$50K",
        budget_flexibility="firm",
        timeline="Q2",
        confidence=0.8,
    )
    assert firm.budget_flexibility == "firm"

    # Flexible budget
    flexible = BudgetConstraints(
        budget_range="$50K-$100K",
        budget_flexibility="flexible",
        timeline="Q2",
        confidence=0.8,
    )
    assert flexible.budget_flexibility == "flexible"

    # Unknown budget
    unknown = BudgetConstraints(
        budget_range="TBD",
        budget_flexibility="unknown",
        timeline="ASAP",
        confidence=0.8,
    )
    assert unknown.budget_flexibility == "unknown"


def test_confirmed_scope_specs_signed_off():
    """Test ConfirmedScope with specs_signed_off flag."""
    # Without specs signed off
    scope_unsigned = ConfirmedScope(
        v1_features=["feat1", "feat2"],
        v1_agreed=True,
        specs_signed_off=False,
        confirmed_by="client",
    )
    assert scope_unsigned.specs_signed_off is False
    assert scope_unsigned.is_satisfied() is True  # Not required for satisfaction

    # With specs signed off
    scope_signed = ConfirmedScope(
        v1_features=["feat1", "feat2"],
        v1_agreed=True,
        specs_signed_off=True,
        confirmed_by="client",
    )
    assert scope_signed.specs_signed_off is True
    assert scope_signed.is_satisfied() is True


# =============================================================================
# ProjectFoundation Tests
# =============================================================================


def test_project_foundation_with_all_gates():
    """ProjectFoundation can contain all gates populated."""
    project_id = uuid4()
    foundation_id = uuid4()

    foundation = ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=CorePain(
            statement="CS teams manually track churn risk across multiple tools",
            trigger="Lost 3 enterprise customers in Q4",
            stakes="$2M ARR at risk",
            who_feels_it="Customer Success Managers",
            confidence=0.85,
        ),
        primary_persona=PrimaryPersona(
            name="Customer Success Manager",
            role="Manages customer retention",
            goal="Reduce churn",
            pain_connection="Can't identify at-risk customers early enough",
            context="Checks dashboards daily but data is fragmented",
            confidence=0.8,
        ),
        wow_moment=WowMoment(
            description="Dashboard predicts churn 60 days in advance",
            core_pain_inversion="From reactive to proactive",
            emotional_impact="Relief and confidence",
            visual_concept="Health scores with predicted churn dates",
            level_1="Core pain solved: Can predict churn",
            level_2="Prioritizes outreach by risk level",
            confidence=0.75,
        ),
        design_preferences=DesignPreferences(
            visual_style="clean/minimal",
            references=["Linear", "Stripe"],
        ),
        business_case=BusinessCase(
            value_to_business="Reduce churn by 15%, save $300K/year",
            roi_framing="$300K annual savings vs $50K investment",
            success_kpis=[
                KPI(
                    metric="Churn rate",
                    current_state="12% monthly",
                    target_state="<10% monthly",
                    measurement_method="Monthly cohort tracking",
                    timeframe="6 months",
                )
            ],
            why_priority="Churn is #1 threat to ARR growth",
            confidence=0.8,
        ),
        budget_constraints=BudgetConstraints(
            budget_range="$50K-$100K",
            budget_flexibility="flexible",
            timeline="Q2 2024",
            confidence=0.75,
        ),
        confirmed_scope=ConfirmedScope(
            v1_features=["feat1", "feat2", "feat3"],
            v2_features=["feat4"],
            v1_agreed=True,
            specs_signed_off=True,
            confirmed_by="client",
        ),
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )

    assert foundation.id == foundation_id
    assert foundation.project_id == project_id
    assert foundation.core_pain is not None
    assert foundation.primary_persona is not None
    assert foundation.wow_moment is not None
    assert foundation.design_preferences is not None
    assert foundation.business_case is not None
    assert foundation.budget_constraints is not None
    assert foundation.confirmed_scope is not None


def test_project_foundation_with_minimal_gates():
    """ProjectFoundation can be created with only required gates."""
    project_id = uuid4()
    foundation_id = uuid4()

    foundation = ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=CorePain(
            statement="Users can't track their metrics effectively across systems",
            trigger="New compliance requirements",
            stakes="Risk of audit failures",
            who_feels_it="Compliance team",
            confidence=0.7,
        ),
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )

    assert foundation.core_pain is not None
    assert foundation.primary_persona is None
    assert foundation.wow_moment is None
    assert foundation.design_preferences is None
    assert foundation.business_case is None
    assert foundation.budget_constraints is None
    assert foundation.confirmed_scope is None


def test_project_foundation_serialization():
    """ProjectFoundation can serialize to and from dict."""
    project_id = uuid4()
    foundation_id = uuid4()

    original = ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=CorePain(
            statement="Manual data entry is time-consuming and error-prone for operations team",
            trigger="Errors in quarterly reports",
            stakes="Board loses confidence in data",
            who_feels_it="Operations team",
            confidence=0.8,
        ),
        primary_persona=PrimaryPersona(
            name="Operations Manager",
            role="Manages data and reporting",
            goal="Accurate and timely reports",
            pain_connection="Spends 4 hours daily on manual data entry",
            context="Works with multiple spreadsheets",
            confidence=0.75,
        ),
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )

    data = original.model_dump()
    restored = ProjectFoundation(**data)

    assert restored.id == original.id
    assert restored.project_id == original.project_id
    assert restored.core_pain.statement == original.core_pain.statement
    assert restored.primary_persona.name == original.primary_persona.name
    assert restored.created_at == original.created_at


def test_project_foundation_optional_gates_as_none():
    """ProjectFoundation handles None values for optional gates."""
    project_id = uuid4()
    foundation_id = uuid4()

    foundation = ProjectFoundation(
        id=foundation_id,
        project_id=project_id,
        core_pain=CorePain(
            statement="System crashes frequently during peak usage affecting customers",
            trigger="Customer complaints increased 300%",
            stakes="Losing customers to competitors",
            who_feels_it="Support team and customers",
            confidence=0.85,
        ),
        primary_persona=None,
        wow_moment=None,
        design_preferences=None,
        business_case=None,
        budget_constraints=None,
        confirmed_scope=None,
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )

    assert foundation.core_pain is not None
    assert foundation.primary_persona is None
    assert foundation.wow_moment is None
    assert foundation.design_preferences is None
    assert foundation.business_case is None
    assert foundation.budget_constraints is None
    assert foundation.confirmed_scope is None


# =============================================================================
# FoundationUpdateRequest Tests
# =============================================================================


def test_foundation_update_request_partial_update():
    """FoundationUpdateRequest can specify partial updates."""
    update = FoundationUpdateRequest(
        core_pain=CorePain(
            statement="Updated core pain statement with at least 20 characters",
            trigger="New trigger",
            stakes="Higher stakes",
            who_feels_it="Updated persona",
            confidence=0.9,
        ),
    )

    assert update.core_pain is not None
    assert update.primary_persona is None
    assert update.wow_moment is None


def test_foundation_update_request_multiple_gates():
    """FoundationUpdateRequest can update multiple gates at once."""
    update = FoundationUpdateRequest(
        core_pain=CorePain(
            statement="Updated core pain statement that is long enough to pass validation",
            trigger="Trigger",
            stakes="Stakes",
            who_feels_it="User",
            confidence=0.85,
        ),
        primary_persona=PrimaryPersona(
            name="Updated Persona",
            role="New role",
            goal="New goal",
            pain_connection="New pain connection",
            context="New context",
            confidence=0.8,
        ),
        business_case=BusinessCase(
            value_to_business="New value proposition",
            roi_framing="Updated ROI",
            success_kpis=[
                KPI(
                    metric="New metric",
                    current_state="Current",
                    target_state="Target",
                    measurement_method="Method",
                    timeframe="Timeline",
                )
            ],
            why_priority="New priority",
            confidence=0.85,
        ),
    )

    assert update.core_pain is not None
    assert update.primary_persona is not None
    assert update.wow_moment is None  # Not included in update
    assert update.business_case is not None


def test_foundation_update_request_empty():
    """FoundationUpdateRequest can be created with no updates."""
    update = FoundationUpdateRequest()

    assert update.core_pain is None
    assert update.primary_persona is None
    assert update.wow_moment is None
    assert update.design_preferences is None
    assert update.business_case is None
    assert update.budget_constraints is None
    assert update.confirmed_scope is None
