"""Tests for signal triage layer."""

import pytest

from app.chains.triage_signal import (
    SOURCE_STRATEGY_MAP,
    TriageResult,
    _compute_priority,
    _detect_source_type,
    _estimate_entities,
    triage_signal,
)


class TestSourceStrategyMap:
    def test_all_expected_source_types_mapped(self):
        """Major source types have strategy mappings."""
        expected = [
            "document", "pdf", "transcript", "meeting_transcript",
            "meeting_notes", "note", "email", "chat", "research",
            "prototype_review", "presentation",
        ]
        for source in expected:
            assert source in SOURCE_STRATEGY_MAP, f"Missing mapping: {source}"

    def test_strategies_are_valid(self):
        """All strategies map to known extraction strategy blocks."""
        valid_strategies = {
            "requirements_doc", "meeting_transcript", "meeting_notes",
            "chat_messages", "email", "prototype_review", "research",
            "presentation", "default",
        }
        for source, strategy in SOURCE_STRATEGY_MAP.items():
            assert strategy in valid_strategies, f"Invalid strategy for {source}: {strategy}"


class TestDetectSourceType:
    def test_metadata_source_type_takes_precedence(self):
        result = _detect_source_type("some text", "note", {"source_type": "meeting_transcript"})
        assert result == "meeting_transcript"

    def test_pdf_extension_detected(self):
        result = _detect_source_type("some text", "document", {"filename": "requirements.pdf"})
        assert result == "document"

    def test_pptx_extension_detected(self):
        result = _detect_source_type("some text", "document", {"filename": "deck.pptx"})
        assert result == "presentation"

    def test_transcript_content_detected(self):
        text = "Speaker: John\n[00:01] So let's discuss the requirements..."
        result = _detect_source_type(text, "document", {})
        assert result == "meeting_transcript"

    def test_email_content_detected(self):
        text = "From: john@example.com\nTo: jane@example.com\nSubject: Requirements\n\nHi Jane..."
        result = _detect_source_type(text, "note", {})
        assert result == "email"

    def test_meeting_notes_detected(self):
        text = "Meeting Notes\n\nAttendees: John, Jane\nAgenda:\n1. Review requirements\n\nKey Decisions:\n- SSO approved"
        result = _detect_source_type(text, "note", {})
        assert result == "meeting_notes"

    def test_prototype_review_detected(self):
        text = "Prototype review session. Feature: SSO. Verdict: aligned. Client said needs adjustment."
        result = _detect_source_type(text, "note", {})
        assert result == "prototype_review"

    def test_long_text_defaults_to_document(self):
        text = "a " * 2000  # 4000 chars, no strong signals
        result = _detect_source_type(text, "unknown", {})
        assert result == "document"

    def test_fallback_to_signal_type(self):
        result = _detect_source_type("short text", "chat", {})
        assert result == "chat"


class TestEstimateEntities:
    def test_feature_keywords_detected(self):
        text = "The system must support SSO. The feature should enable data export. Users need ability to filter reports."
        count = _estimate_entities(text)
        assert count >= 2

    def test_persona_keywords_detected(self):
        text = "As a sales manager, I need to view reports. The admin can manage users."
        count = _estimate_entities(text)
        assert count >= 1

    def test_workflow_keywords_detected(self):
        text = "Step 1: User logs in. Step 2: User selects report. The current process involves manual data entry."
        count = _estimate_entities(text)
        assert count >= 2

    def test_empty_text(self):
        assert _estimate_entities("") == 0

    def test_capped_at_50(self):
        # Generate text with many keywords
        text = "feature " * 200 + "requirement " * 200
        count = _estimate_entities(text)
        assert count <= 50


class TestComputePriority:
    def test_client_authority_boosts_priority(self):
        p1 = _compute_priority("document", 100, 2, "client")
        p2 = _compute_priority("document", 100, 2, "research")
        assert p1 > p2

    def test_high_word_count_boosts_priority(self):
        p1 = _compute_priority("document", 5000, 2, "research")
        p2 = _compute_priority("document", 100, 2, "research")
        assert p1 > p2

    def test_high_entity_count_boosts_priority(self):
        p1 = _compute_priority("document", 100, 15, "research")
        p2 = _compute_priority("document", 100, 1, "research")
        assert p1 > p2

    def test_capped_at_1(self):
        p = _compute_priority("requirements_doc", 10000, 50, "client")
        assert p <= 1.0


class TestTriageSignal:
    def test_requirements_doc_triage(self):
        text = "Requirements Document v3\n\nThe system must support SSO. " * 100
        result = triage_signal("document", text, {"authority": "client"})

        assert isinstance(result, TriageResult)
        assert result.strategy == "requirements_doc"
        assert result.source_authority == "client"
        assert result.priority_score > 0

    def test_meeting_notes_triage(self):
        text = "Meeting Notes\nAttendees: John, Jane\nAgenda: Review requirements\nKey Decisions: SSO approved"
        result = triage_signal("note", text)

        assert result.strategy == "meeting_notes"
        assert result.source_authority == "consultant"

    def test_chat_triage(self):
        result = triage_signal("chat", "quick question about the feature", {})
        assert result.strategy == "chat_messages"

    def test_research_triage(self):
        result = triage_signal("research", "Market analysis shows competitors offer SSO.", {})
        assert result.strategy == "research"
        assert result.source_authority == "research"

    def test_metadata_authority_overrides(self):
        result = triage_signal("document", "some text", {"authority": "consultant"})
        assert result.source_authority == "consultant"

    def test_word_count_populated(self):
        text = "word " * 500
        result = triage_signal("note", text)
        assert result.word_count == 500

    def test_entity_count_populated(self):
        text = "The system must support SSO. Feature: data export. Requirement: user roles."
        result = triage_signal("document", text)
        assert result.estimated_entity_count >= 1

    def test_unknown_type_gets_default_strategy(self):
        result = triage_signal("something_weird", "text", {})
        assert result.strategy == "default"
