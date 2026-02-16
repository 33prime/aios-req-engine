"""Tests for open questions schemas and API router validation."""

import pytest

from app.core.schemas_open_questions import (
    OpenQuestionAnswer,
    OpenQuestionConvert,
    OpenQuestionCreate,
    OpenQuestionDismiss,
    OpenQuestionResponse,
    OpenQuestionUpdate,
    QuestionCategory,
    QuestionCounts,
    QuestionPriority,
    QuestionSourceType,
    QuestionStatus,
)


class TestOpenQuestionSchemas:
    def test_create_minimal(self):
        q = OpenQuestionCreate(question="What is the auth model?")
        assert q.priority == QuestionPriority.MEDIUM
        assert q.category == QuestionCategory.GENERAL
        assert q.source_type == QuestionSourceType.MANUAL

    def test_create_full(self):
        q = OpenQuestionCreate(
            question="What regulatory requirements exist?",
            why_it_matters="Affects architecture decisions",
            context="Client is in healthcare",
            priority=QuestionPriority.CRITICAL,
            category=QuestionCategory.TECHNICAL,
            source_type=QuestionSourceType.FACT_EXTRACTION,
            source_id="abc123",
            target_entity_type="feature",
            target_entity_id="def456",
            suggested_owner="client",
        )
        assert q.priority == QuestionPriority.CRITICAL
        assert q.source_type == QuestionSourceType.FACT_EXTRACTION

    def test_create_rejects_short_question(self):
        with pytest.raises(Exception):
            OpenQuestionCreate(question="Hi")

    def test_update_partial(self):
        u = OpenQuestionUpdate(priority=QuestionPriority.HIGH)
        data = u.model_dump(exclude_none=True)
        assert "priority" in data
        assert "question" not in data

    def test_answer_model(self):
        a = OpenQuestionAnswer(answer="We use OAuth2")
        assert a.answered_by == "consultant"

    def test_answer_rejects_empty(self):
        with pytest.raises(Exception):
            OpenQuestionAnswer(answer="")

    def test_dismiss_model(self):
        d = OpenQuestionDismiss(reason="No longer relevant")
        assert d.reason == "No longer relevant"

    def test_dismiss_no_reason(self):
        d = OpenQuestionDismiss()
        assert d.reason is None

    def test_convert_model(self):
        c = OpenQuestionConvert(
            converted_to_type="feature",
            converted_to_id="abc123",
        )
        assert c.converted_to_type == "feature"

    def test_response_model(self):
        r = OpenQuestionResponse(
            id="q1",
            project_id="p1",
            question="Test?",
            priority="medium",
            status="open",
            source_type="manual",
            created_at="2026-02-01T00:00:00Z",
            updated_at="2026-02-01T00:00:00Z",
        )
        assert r.status == "open"

    def test_counts_model(self):
        c = QuestionCounts(total=10, open=5, answered=3, dismissed=1, converted=1)
        assert c.total == 10
        assert c.critical_open == 0

    def test_counts_defaults(self):
        c = QuestionCounts()
        assert c.total == 0


class TestEnumValues:
    def test_priority_values(self):
        assert QuestionPriority.CRITICAL.value == "critical"
        assert QuestionPriority.LOW.value == "low"

    def test_category_values(self):
        assert QuestionCategory.REQUIREMENTS.value == "requirements"
        assert QuestionCategory.GENERAL.value == "general"

    def test_status_values(self):
        assert QuestionStatus.OPEN.value == "open"
        assert QuestionStatus.CONVERTED.value == "converted"

    def test_source_type_values(self):
        assert QuestionSourceType.FACT_EXTRACTION.value == "fact_extraction"
        assert QuestionSourceType.MANUAL.value == "manual"
