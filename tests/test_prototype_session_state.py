"""Tests for prototype session state transitions and scoring logic."""

import pytest

from app.chains.audit_v0_output import should_retry
from app.core.schemas_prototypes import (
    PromptAuditResult,
    PromptGap,
    SessionContext,
    SubmitFeedbackRequest,
)


class TestPromptAuditDecisionLogic:
    """Tests for the prompt audit retry decision logic."""

    def test_accept_when_score_above_threshold(self):
        """Scores >= 0.8 should be accepted."""
        audit = PromptAuditResult(
            feature_coverage_score=0.9,
            structure_score=0.85,
            mock_data_score=0.8,
            flow_score=0.82,
            feature_id_score=0.78,
            overall_score=0.85,
        )
        assert should_retry(audit) == "accept"

    def test_accept_at_exact_threshold(self):
        """Score of exactly 0.8 should be accepted."""
        audit = PromptAuditResult(overall_score=0.8)
        assert should_retry(audit) == "accept"

    def test_retry_when_score_moderate(self):
        """Scores between 0.5 and 0.8 should trigger retry."""
        audit = PromptAuditResult(overall_score=0.65)
        assert should_retry(audit) == "retry"

    def test_retry_at_lower_bound(self):
        """Score of exactly 0.5 should trigger retry."""
        audit = PromptAuditResult(overall_score=0.5)
        assert should_retry(audit) == "retry"

    def test_notify_when_score_low(self):
        """Scores below 0.5 should notify consultant."""
        audit = PromptAuditResult(overall_score=0.3)
        assert should_retry(audit) == "notify"

    def test_notify_at_zero(self):
        """Score of 0 should notify."""
        audit = PromptAuditResult(overall_score=0.0)
        assert should_retry(audit) == "notify"

    def test_accept_perfect_score(self):
        """Perfect score of 1.0 should be accepted."""
        audit = PromptAuditResult(overall_score=1.0)
        assert should_retry(audit) == "accept"


class TestPromptAuditResult:
    """Tests for PromptAuditResult schema validation."""

    def test_default_scores_are_zero(self):
        """All scores default to 0."""
        audit = PromptAuditResult()
        assert audit.feature_coverage_score == 0
        assert audit.structure_score == 0
        assert audit.overall_score == 0

    def test_gaps_list_is_populated(self):
        """Gaps can be populated with PromptGap objects."""
        audit = PromptAuditResult(
            overall_score=0.6,
            gaps=[
                PromptGap(
                    dimension="feature_coverage",
                    description="Login feature missing",
                    severity="high",
                    feature_ids=["abc-123"],
                )
            ],
            recommendations=["Add login form component"],
        )
        assert len(audit.gaps) == 1
        assert audit.gaps[0].severity == "high"
        assert len(audit.recommendations) == 1

    def test_empty_gaps_and_recommendations(self):
        """Empty lists are valid."""
        audit = PromptAuditResult(overall_score=1.0, gaps=[], recommendations=[])
        assert audit.gaps == []
        assert audit.recommendations == []


class TestSessionContext:
    """Tests for SessionContext schema."""

    def test_minimal_context(self):
        """Minimal context with defaults."""
        ctx = SessionContext()
        assert ctx.current_page == ""
        assert ctx.active_feature_id is None
        assert ctx.visible_features == []
        assert ctx.page_history == []
        assert ctx.features_reviewed == []

    def test_full_context(self):
        """Full context with all fields populated."""
        ctx = SessionContext(
            current_page="/dashboard",
            current_route="/dashboard",
            active_feature_id="feat-123",
            active_feature_name="Dashboard",
            active_component="StatsPanel",
            visible_features=["feat-123", "feat-456"],
            page_history=[],
            features_reviewed=["feat-123"],
        )
        assert ctx.current_page == "/dashboard"
        assert ctx.active_feature_id == "feat-123"
        assert len(ctx.visible_features) == 2


class TestSubmitFeedbackRequest:
    """Tests for SubmitFeedbackRequest schema validation."""

    def test_minimal_feedback(self):
        """Minimal feedback with just content."""
        fb = SubmitFeedbackRequest(content="Looks good")
        assert fb.content == "Looks good"
        assert fb.feedback_type == "observation"
        assert fb.priority == "medium"

    def test_feedback_with_context(self):
        """Feedback with full context."""
        fb = SubmitFeedbackRequest(
            content="Login should require MFA",
            feedback_type="requirement",
            feature_id="feat-123",
            page_path="/login",
            priority="high",
            context=SessionContext(
                current_page="/login",
                active_feature_id="feat-123",
            ),
        )
        assert fb.feedback_type == "requirement"
        assert fb.priority == "high"
        assert fb.context is not None
        assert fb.context.active_feature_id == "feat-123"

    def test_empty_content_rejected(self):
        """Empty content should be rejected."""
        with pytest.raises(Exception):
            SubmitFeedbackRequest(content="")

    def test_invalid_feedback_type_rejected(self):
        """Invalid feedback_type should be rejected."""
        with pytest.raises(Exception):
            SubmitFeedbackRequest(content="test", feedback_type="invalid_type")
