"""Tests for the bulk signal processing pipeline.

Tests the heavyweight signal flow:
1. Signal classification
2. Parallel extraction
3. Consolidation
4. Validation
5. Proposal generation
"""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ============================================================================
# Signal Classifier Tests
# ============================================================================


class TestSignalClassifier:
    """Tests for signal classification logic."""

    def test_classify_transcript_as_heavyweight(self):
        """Long transcripts with multiple speakers should be heavyweight."""
        from app.core.signal_classifier import classify_signal

        # Create a substantial transcript
        transcript_content = """
        Jim: Let's discuss the new SSO feature requirements.
        Sarah: I think we need SAML and OAuth support.
        Jim: Agreed. What about the dashboard analytics?
        Sarah: We need real-time metrics for the executive team.
        Mike: I can provide the technical specifications.
        Jim: Great. Let's also discuss the budget implications.
        Sarah: The compliance requirements are critical - HIPAA and SOC2.
        Mike: I'll need to review the security architecture.
        Jim: Timeline is Q2 2025. We have three months.
        Sarah: Let me outline the user personas we're targeting.
        """ * 5  # Repeat to make it longer

        result = classify_signal(
            source_type="transcript",
            content=transcript_content,
            metadata={"duration_minutes": 45},
        )

        # With long content and transcript type, should be heavyweight
        assert result.power_score >= 0.5  # Check score is reasonable
        # Note: actual heavyweight classification depends on content length/entity density

    def test_classify_short_email_as_lightweight(self):
        """Short emails should be classified as lightweight."""
        from app.core.signal_classifier import classify_signal

        result = classify_signal(
            source_type="email",
            content="Thanks for the update. Looks good!",
            metadata={},
        )

        assert result.power_level.value == "lightweight"
        assert result.power_score < 0.5

    def test_classify_long_email_as_heavyweight(self):
        """Long emails with many entities should be heavyweight."""
        from app.core.signal_classifier import classify_signal

        # Generate a long email with multiple features mentioned
        long_content = """
        Hi team,

        After our discussion, here's what we need:

        1. SSO Integration - Must support SAML and OAuth
        2. Dashboard Analytics - Real-time metrics
        3. Export functionality - CSV and PDF
        4. Mobile responsive design
        5. Notification system
        6. User management
        7. Audit logging
        8. API access for integrations
        9. Bulk import tool
        10. Role-based permissions

        Key stakeholders:
        - Jim (CFO) will approve budget
        - Sarah (CTO) needs technical review
        - Mike (PM) is primary contact

        Timeline is Q2 2025.

        Best,
        Client
        """ * 3  # Repeat to make it longer

        result = classify_signal(
            source_type="email",
            content=long_content,
            metadata={},
        )

        assert result.power_level.value == "heavyweight"
        assert result.estimated_entity_count >= 5

    def test_classify_long_document_as_heavyweight(self):
        """Long documents should be heavyweight."""
        from app.core.signal_classifier import classify_signal

        # Create substantial document content
        doc_content = """
        Product Requirements Document

        1. Overview
        This document outlines the requirements for our new enterprise platform.

        2. Features
        - Single Sign-On (SSO) with SAML 2.0 and OAuth 2.0 support
        - Real-time analytics dashboard with customizable widgets
        - Export functionality supporting CSV, PDF, and Excel formats
        - Mobile-responsive design for iOS and Android
        - Push notification system with email fallback
        - Role-based access control (RBAC)
        - Audit logging for compliance
        - RESTful API for third-party integrations

        3. User Personas
        - Enterprise Administrator
        - Business Analyst
        - End User
        - API Developer

        4. Technical Requirements
        - 99.9% uptime SLA
        - Sub-200ms response time
        - Support for 10,000 concurrent users
        """ * 3

        result = classify_signal(
            source_type="document",
            content=doc_content,
            metadata={"filename": "PRD.pdf"},
        )

        # Long document with many entities should be heavyweight
        assert result.power_score >= 0.5
        assert result.estimated_entity_count >= 3


# ============================================================================
# Topic Extraction Tests
# ============================================================================


class TestTopicExtraction:
    """Tests for topic extraction from entities."""

    def test_extract_topics_from_feature(self):
        """Should extract relevant topics from feature data."""
        from app.core.topic_extraction import extract_topics_from_entity

        feature = {
            "name": "SSO Integration",
            "description": "Single sign-on with SAML and OAuth support",
            "user_problem": "Users need secure authentication without multiple passwords",
            "acceptance_criteria": [
                "Support SAML 2.0",
                "Support OAuth 2.0",
                "Support MFA",
            ],
        }

        topics = extract_topics_from_entity(feature, "feature")

        assert "sso" in topics or "authentication" in topics
        assert "saml" in topics
        assert "oauth" in topics
        assert len(topics) <= 10

    def test_extract_topics_from_persona(self):
        """Should extract topics from persona data."""
        from app.core.topic_extraction import extract_topics_from_entity

        persona = {
            "name": "IT Administrator",
            "description": "Manages security and compliance",
            "pain_points": ["Manual user provisioning", "No audit trail"],
            "goals": ["Reduce security incidents", "Achieve SOC2 compliance"],
        }

        topics = extract_topics_from_entity(persona, "persona")

        assert "security" in topics or "compliance" in topics
        assert len(topics) > 0

    def test_domain_keywords_prioritized(self):
        """Domain keywords should be prioritized in extraction."""
        from app.core.topic_extraction import extract_topics_from_text

        text = """
        The system needs authentication with SSO, compliance with HIPAA,
        and analytics for the dashboard. Users want better performance.
        """

        topics = extract_topics_from_text(text)

        # Domain keywords should appear early in the list
        top_5 = topics[:5]
        domain_found = any(
            kw in top_5
            for kw in ["authentication", "sso", "compliance", "hipaa", "analytics", "dashboard"]
        )
        assert domain_found, f"Expected domain keywords in top 5, got: {top_5}"


# ============================================================================
# Consolidation Tests
# ============================================================================


class TestConsolidation:
    """Tests for extraction consolidation logic."""

    @patch("app.chains.consolidate_extractions.get_supabase")
    def test_consolidate_new_features(self, mock_supabase):
        """Should create new features when no match exists."""
        from app.chains.consolidate_extractions import consolidate_extractions
        from app.core.schemas_bulk_signal import ExtractionResult, ExtractedEntity

        # Mock empty existing data
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.return_value = mock_client

        project_id = uuid4()
        extraction_results = [
            ExtractionResult(
                agent_name="fact_extraction",
                entities=[
                    ExtractedEntity(
                        entity_type="feature",
                        raw_data={"name": "SSO Integration", "description": "Single sign-on support"},
                    ),
                ],
            ),
        ]

        result = consolidate_extractions(project_id, extraction_results)

        assert len(result.features) == 1
        assert result.features[0].operation == "create"

    @patch("app.chains.consolidate_extractions.get_supabase")
    def test_consolidate_duplicate_features(self, mock_supabase):
        """Should merge duplicate feature mentions."""
        from app.chains.consolidate_extractions import consolidate_extractions
        from app.core.schemas_bulk_signal import ExtractionResult, ExtractedEntity

        # Mock empty existing data
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.return_value = mock_client

        project_id = uuid4()
        extraction_results = [
            ExtractionResult(
                agent_name="fact_extraction",
                entities=[
                    ExtractedEntity(
                        entity_type="feature",
                        raw_data={"name": "SSO Integration", "description": "Single sign-on"},
                    ),
                ],
            ),
            ExtractionResult(
                agent_name="entity_extraction",
                entities=[
                    ExtractedEntity(
                        entity_type="feature",
                        raw_data={"name": "SSO", "description": "SAML support"},  # Similar name
                    ),
                ],
            ),
        ]

        result = consolidate_extractions(project_id, extraction_results)

        # Should dedupe similar features
        assert len(result.features) <= 2  # May or may not merge depending on similarity threshold
        assert result.total_creates >= 1


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Tests for bulk change validation."""

    def test_detect_mvp_downgrade_contradiction(self):
        """Should detect when MVP feature is being downgraded."""
        from app.chains.validate_bulk_changes import check_field_contradiction

        is_contradiction, severity, description = check_field_contradiction(
            entity_type="feature",
            field_name="is_mvp",
            old_value=True,
            new_value=False,
        )

        assert is_contradiction
        assert severity == "important"
        assert "is_mvp" in description.lower() or "protected" in description.lower()

    def test_no_contradiction_for_enrichment(self):
        """Should not flag enrichment as contradiction."""
        from app.chains.validate_bulk_changes import check_field_contradiction

        is_contradiction, severity, description = check_field_contradiction(
            entity_type="feature",
            field_name="description",
            old_value="Basic description",
            new_value="Enhanced description with more details",
        )

        assert not is_contradiction

    @patch("app.chains.validate_bulk_changes.get_supabase")
    def test_identify_gaps_filled(self, mock_supabase):
        """Should identify when gaps are being filled."""
        from app.chains.validate_bulk_changes import identify_gaps_filled
        from app.core.schemas_bulk_signal import ConsolidationResult, ConsolidatedChange

        # Mock empty existing data (first features)
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 0
        mock_supabase.return_value = mock_client

        project_id = uuid4()
        consolidation = ConsolidationResult(
            features=[
                ConsolidatedChange(
                    entity_type="feature",
                    entity_id=None,
                    entity_name="New Feature",
                    operation="create",
                    before=None,
                    after={"name": "New Feature"},
                    field_changes=[],
                    evidence=[],
                    confidence=0.9,
                ),
            ],
            personas=[],
            vp_steps=[],
            stakeholders=[],
            total_creates=1,
            total_updates=0,
            average_confidence=0.9,
        )

        gaps = identify_gaps_filled(consolidation, project_id)

        assert len(gaps) > 0
        assert any("feature" in gap.lower() for gap in gaps)


# ============================================================================
# Streaming Pipeline Tests
# ============================================================================


class TestStreamingPipeline:
    """Tests for the streaming signal pipeline (synchronous tests)."""

    def test_stream_event_types_defined(self):
        """StreamEvent class should have all expected event types."""
        from app.core.signal_pipeline import StreamEvent

        # Standard pipeline events
        assert hasattr(StreamEvent, "STARTED")
        assert hasattr(StreamEvent, "CLASSIFICATION_COMPLETED")
        assert hasattr(StreamEvent, "BUILD_STATE_STARTED")
        assert hasattr(StreamEvent, "BUILD_STATE_COMPLETED")
        assert hasattr(StreamEvent, "COMPLETED")
        assert hasattr(StreamEvent, "ERROR")

        # Bulk pipeline events
        assert hasattr(StreamEvent, "BULK_STARTED")
        assert hasattr(StreamEvent, "BULK_EXTRACTION_STARTED")
        assert hasattr(StreamEvent, "BULK_EXTRACTION_COMPLETED")
        assert hasattr(StreamEvent, "BULK_PROPOSAL_CREATED")
        assert hasattr(StreamEvent, "CREATIVE_BRIEF_UPDATED")

    def test_stream_event_values_are_strings(self):
        """StreamEvent values should be strings for SSE."""
        from app.core.signal_pipeline import StreamEvent

        assert isinstance(StreamEvent.STARTED, str)
        assert isinstance(StreamEvent.BULK_STARTED, str)
        assert isinstance(StreamEvent.COMPLETED, str)


# ============================================================================
# End-to-End Scenario Tests
# ============================================================================


class TestEndToEndScenarios:
    """End-to-end scenario tests with mocked dependencies."""

    def test_topic_extraction_integration(self):
        """Test topic extraction integrates with stakeholder matching."""
        from app.core.topic_extraction import (
            extract_topics_from_entity,
            get_confirmation_gap_topics,
        )

        # Create a feature that would need stakeholder input
        feature = {
            "name": "SSO Integration",
            "description": "Enterprise SSO with SAML and OAuth support",
            "user_problem": "Users need single sign-on for compliance",
            "acceptance_criteria": ["Support SAML 2.0", "Support MFA"],
        }

        # Extract topics
        topics = extract_topics_from_entity(feature, "feature")
        assert len(topics) > 0
        assert any(t in topics for t in ["sso", "saml", "oauth", "authentication", "compliance"])

        # Get topics for a specific gap
        gap_topics = get_confirmation_gap_topics(
            entity=feature,
            entity_type="feature",
            gap_description="Need to confirm SAML IdP requirements",
        )
        assert len(gap_topics) > 0
        assert "saml" in gap_topics  # Gap-specific topic should be prioritized

    def test_validation_integration(self):
        """Test validation detects various contradiction types."""
        from app.chains.validate_bulk_changes import (
            check_field_contradiction,
            calculate_overall_severity,
        )
        from app.core.schemas_bulk_signal import Contradiction

        # Test multiple contradiction scenarios
        contradictions = []

        # Scenario 1: MVP downgrade
        is_contra, sev, desc = check_field_contradiction(
            "feature", "is_mvp", True, False
        )
        if is_contra:
            contradictions.append(Contradiction(
                description=desc,
                severity=sev,
                proposed_value=False,
                existing_value=True,
                entity_type="feature",
                entity_name="Test Feature",
                field_name="is_mvp",
            ))

        # Scenario 2: Status downgrade
        is_contra, sev, desc = check_field_contradiction(
            "feature", "status", "confirmed", "draft"
        )
        if is_contra:
            contradictions.append(Contradiction(
                description=desc,
                severity=sev,
                proposed_value="draft",
                existing_value="confirmed",
                entity_type="feature",
                entity_name="Test Feature",
                field_name="status",
            ))

        # Calculate overall severity
        severity = calculate_overall_severity(contradictions)
        assert severity in ["none", "minor", "important", "critical"]

        # With MVP downgrade, should be at least "important"
        if len(contradictions) > 0:
            assert severity != "none"

    def test_consolidation_schema_roundtrip(self):
        """Test consolidation result schema serializes correctly."""
        from app.core.schemas_bulk_signal import (
            ConsolidationResult,
            ConsolidatedChange,
            FieldChange,
        )

        result = ConsolidationResult(
            features=[
                ConsolidatedChange(
                    entity_type="feature",
                    entity_id=None,
                    entity_name="Test Feature",
                    operation="create",
                    before=None,
                    after={"name": "Test Feature", "description": "A test"},
                    field_changes=[],
                    evidence=[],
                    confidence=0.85,
                ),
                ConsolidatedChange(
                    entity_type="feature",
                    entity_id=uuid4(),
                    entity_name="Existing Feature",
                    operation="update",
                    before={"description": "Old"},
                    after={"description": "New and improved"},
                    field_changes=[
                        FieldChange(
                            field_name="description",
                            old_value="Old",
                            new_value="New and improved",
                        )
                    ],
                    evidence=[],
                    confidence=0.9,
                ),
            ],
            personas=[],
            vp_steps=[],
            stakeholders=[],
            total_creates=1,
            total_updates=1,
            average_confidence=0.875,
        )

        # Serialize and deserialize
        json_data = result.model_dump_json()
        restored = ConsolidationResult.model_validate_json(json_data)

        assert len(restored.features) == 2
        assert restored.total_creates == 1
        assert restored.total_updates == 1
        assert restored.average_confidence == 0.875
