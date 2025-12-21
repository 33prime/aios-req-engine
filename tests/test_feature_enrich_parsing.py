"""Tests for feature enrichment schema parsing and validation."""

import pytest
from uuid import uuid4

from app.core.schemas_evidence import EvidenceRef
from app.core.schemas_feature_enrich import (
    AcceptanceCriterion,
    BusinessRule,
    Dependency,
    EnrichFeaturesOutput,
    FeatureDetails,
    Integration,
    RiskItem,
    TelemetryEvent,
)


class TestEvidenceValidation:
    """Test EvidenceRef validation."""

    def test_valid_evidence_ref(self):
        """Test valid EvidenceRef creation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="This is a valid excerpt under 280 characters.",
            rationale="This supports the claim",
        )
        assert evidence.chunk_id
        assert len(evidence.excerpt) <= 280
        assert evidence.excerpt.strip() != ""

    def test_excerpt_too_long(self):
        """Test excerpt length validation."""
        long_excerpt = "x" * 281
        with pytest.raises(ValueError, match="excerpt must be 280 characters or less"):
            EvidenceRef(
                chunk_id=uuid4(),
                excerpt=long_excerpt,
                rationale="Too long",
            )

    def test_empty_excerpt(self):
        """Test empty excerpt validation."""
        with pytest.raises(ValueError, match="excerpt must be non-empty"):
            EvidenceRef(
                chunk_id=uuid4(),
                excerpt="   ",
                rationale="Empty excerpt",
            )


class TestFeatureEnrichmentSchemas:
    """Test feature enrichment schema validation."""

    def test_business_rule_schema(self):
        """Test BusinessRule schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Business rule excerpt",
            rationale="Supports rule",
        )

        rule = BusinessRule(
            title="User Authentication Rule",
            rule="Users must provide valid credentials to access the system",
            verification="Validated through OAuth integration",
            evidence=[evidence],
        )

        assert rule.title == "User Authentication Rule"
        assert len(rule.evidence) == 1

    def test_acceptance_criterion_schema(self):
        """Test AcceptanceCriterion schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Acceptance criterion excerpt",
            rationale="Supports criterion",
        )

        criterion = AcceptanceCriterion(
            criterion="User can log in with Google OAuth",
            evidence=[evidence],
        )

        assert criterion.criterion == "User can log in with Google OAuth"
        assert len(criterion.evidence) == 1

    def test_dependency_schema(self):
        """Test Dependency schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Dependency excerpt",
            rationale="Supports dependency",
        )

        dependency = Dependency(
            dependency_type="external_system",
            name="Google OAuth API",
            why="Required for user authentication",
            evidence=[evidence],
        )

        assert dependency.dependency_type == "external_system"
        assert dependency.name == "Google OAuth API"
        assert len(dependency.evidence) == 1

    def test_integration_schema(self):
        """Test Integration schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Integration excerpt",
            rationale="Supports integration",
        )

        integration = Integration(
            system="Auth Service",
            direction="bidirectional",
            data_exchanged="user credentials and tokens",
            evidence=[evidence],
        )

        assert integration.system == "Auth Service"
        assert integration.direction == "bidirectional"
        assert len(integration.evidence) == 1

    def test_telemetry_event_schema(self):
        """Test TelemetryEvent schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Telemetry excerpt",
            rationale="Supports telemetry",
        )

        event = TelemetryEvent(
            event_name="user_login_success",
            when_fired="After successful authentication",
            properties=["user_id", "login_method", "timestamp"],
            success_metric="User retention rate",
            evidence=[evidence],
        )

        assert event.event_name == "user_login_success"
        assert len(event.properties) == 3
        assert len(event.evidence) == 1

    def test_risk_item_schema(self):
        """Test RiskItem schema validation."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Risk excerpt",
            rationale="Supports risk assessment",
        )

        risk = RiskItem(
            title="Authentication Security Risk",
            risk="Potential OAuth token exposure",
            mitigation="Use secure token storage and rotation",
            severity="high",
            evidence=[evidence],
        )

        assert risk.title == "Authentication Security Risk"
        assert risk.severity == "high"
        assert len(risk.evidence) == 1

    def test_feature_details_schema(self):
        """Test complete FeatureDetails schema."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Sample evidence",
            rationale="Supports feature",
        )

        business_rule = BusinessRule(
            title="Sample Rule",
            rule="Sample business logic",
            evidence=[evidence],
        )

        details = FeatureDetails(
            summary="User authentication feature for secure access",
            data_requirements=[],
            business_rules=[business_rule],
            acceptance_criteria=[],
            dependencies=[],
            integrations=[],
            telemetry_events=[],
            risks=[],
        )

        assert details.summary == "User authentication feature for secure access"
        assert len(details.business_rules) == 1
        assert len(details.data_requirements) == 0

    def test_enrich_features_output_schema(self):
        """Test complete EnrichFeaturesOutput schema."""
        project_id = uuid4()
        feature_id = uuid4()

        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Output evidence",
            rationale="Supports enrichment",
        )

        details = FeatureDetails(
            summary="Test feature summary",
            data_requirements=[],
            business_rules=[],
            acceptance_criteria=[],
            dependencies=[],
            integrations=[],
            telemetry_events=[],
            risks=[],
        )

        output = EnrichFeaturesOutput(
            project_id=project_id,
            feature_id=feature_id,
            feature_slug="Test Feature",
            details=details,
            open_questions=[],
        )

        assert output.project_id == project_id
        assert output.feature_id == feature_id
        assert output.feature_slug == "Test Feature"
        assert output.schema_version == "feature_details_v1"

    def test_minimal_valid_output(self):
        """Test minimal valid enrichment output."""
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="Minimal evidence",
            rationale="Minimal rationale",
        )

        # Create output with minimal required fields
        output = EnrichFeaturesOutput(
            project_id=uuid4(),
            feature_id=uuid4(),
            feature_slug="Minimal Feature",
            details=FeatureDetails(
                summary="Minimal summary",
                data_requirements=[],
                business_rules=[],
                acceptance_criteria=[],
                dependencies=[],
                integrations=[],
                telemetry_events=[],
                risks=[],
            ),
            open_questions=[],
        )

        assert output.details.summary == "Minimal summary"
        assert output.schema_version == "feature_details_v1"
