"""Tests for fact extraction parsing and validation."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_facts import (
    Contradiction,
    EvidenceRef,
    ExtractFactsOutput,
    FactItem,
    OpenQuestion,
)


class TestEvidenceRef:
    """Tests for EvidenceRef model."""

    def test_valid_evidence_ref(self) -> None:
        """Should accept valid evidence ref."""
        ref = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="This is a short excerpt.",
            rationale="Because it directly states the fact.",
        )
        assert len(ref.excerpt) <= 280

    def test_excerpt_max_length(self) -> None:
        """Should enforce max length on excerpt."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceRef(
                chunk_id=uuid4(),
                excerpt="A" * 281,  # Over limit
                rationale="test",
            )
        assert "excerpt" in str(exc_info.value)


class TestFactItem:
    """Tests for FactItem model."""

    def test_valid_fact_item(self) -> None:
        """Should accept valid fact item."""
        fact = FactItem(
            fact_type="feature",
            title="User login",
            detail="Users must be able to log in with email and password.",
            confidence="high",
            evidence=[
                EvidenceRef(
                    chunk_id=uuid4(),
                    excerpt="Users log in with email",
                    rationale="Direct statement",
                )
            ],
        )
        assert fact.fact_type == "feature"

    def test_requires_at_least_one_evidence(self) -> None:
        """Should require at least one evidence ref."""
        with pytest.raises(ValidationError) as exc_info:
            FactItem(
                fact_type="feature",
                title="Test",
                detail="Test detail",
                confidence="low",
                evidence=[],  # Empty - should fail
            )
        assert "evidence" in str(exc_info.value)

    def test_invalid_fact_type(self) -> None:
        """Should reject invalid fact types."""
        with pytest.raises(ValidationError):
            FactItem(
                fact_type="invalid_type",  # type: ignore
                title="Test",
                detail="Test",
                confidence="low",
                evidence=[EvidenceRef(chunk_id=uuid4(), excerpt="test", rationale="test")],
            )


class TestOpenQuestion:
    """Tests for OpenQuestion model."""

    def test_valid_open_question(self) -> None:
        """Should accept valid open question with no evidence."""
        question = OpenQuestion(
            question="What is the expected user volume?",
            why_it_matters="Impacts architecture decisions.",
            suggested_owner="client",
        )
        assert question.evidence == []

    def test_optional_evidence(self) -> None:
        """Should accept evidence when provided."""
        question = OpenQuestion(
            question="What timezone?",
            why_it_matters="Affects scheduling",
            suggested_owner="client",
            evidence=[
                EvidenceRef(
                    chunk_id=uuid4(),
                    excerpt="timezone unclear",
                    rationale="Mentioned but not specified",
                )
            ],
        )
        assert len(question.evidence) == 1


class TestContradiction:
    """Tests for Contradiction model."""

    def test_valid_contradiction(self) -> None:
        """Should accept valid contradiction."""
        contradiction = Contradiction(
            description="Conflicting views on deadline",
            sides=["Q1 2024", "Q2 2024"],
            severity="important",
            evidence=[
                EvidenceRef(
                    chunk_id=uuid4(),
                    excerpt="Launch in Q1",
                    rationale="First position",
                )
            ],
        )
        assert len(contradiction.sides) == 2

    def test_requires_at_least_two_sides(self) -> None:
        """Should require at least two sides."""
        with pytest.raises(ValidationError) as exc_info:
            Contradiction(
                description="Test",
                sides=["Only one"],  # Should fail
                severity="minor",
                evidence=[EvidenceRef(chunk_id=uuid4(), excerpt="test", rationale="test")],
            )
        assert "sides" in str(exc_info.value)

    def test_requires_at_least_one_evidence(self) -> None:
        """Should require at least one evidence ref."""
        with pytest.raises(ValidationError) as exc_info:
            Contradiction(
                description="Test",
                sides=["A", "B"],
                severity="minor",
                evidence=[],  # Should fail
            )
        assert "evidence" in str(exc_info.value)


class TestExtractFactsOutput:
    """Tests for ExtractFactsOutput model."""

    def test_valid_full_output(self) -> None:
        """Should accept complete valid output."""
        chunk_id = uuid4()
        output = ExtractFactsOutput(
            summary="Extracted 2 facts from client email.",
            facts=[
                FactItem(
                    fact_type="feature",
                    title="Login feature",
                    detail="Users need to log in.",
                    confidence="high",
                    evidence=[
                        EvidenceRef(
                            chunk_id=chunk_id,
                            excerpt="must log in",
                            rationale="Direct statement",
                        )
                    ],
                )
            ],
            open_questions=[
                OpenQuestion(
                    question="What is the deadline?",
                    why_it_matters="Planning",
                    suggested_owner="client",
                )
            ],
            contradictions=[],
        )
        assert len(output.facts) == 1
        assert len(output.open_questions) == 1
        assert len(output.contradictions) == 0

    def test_parse_from_json(self) -> None:
        """Should parse from valid JSON string."""
        chunk_id = str(uuid4())
        json_str = json.dumps(
            {
                "summary": "Test summary",
                "facts": [
                    {
                        "fact_type": "constraint",
                        "title": "Budget limit",
                        "detail": "Budget is $100k",
                        "confidence": "medium",
                        "evidence": [
                            {
                                "chunk_id": chunk_id,
                                "excerpt": "budget of 100k",
                                "rationale": "Stated in email",
                            }
                        ],
                    }
                ],
                "open_questions": [],
                "contradictions": [],
            }
        )

        parsed = json.loads(json_str)
        output = ExtractFactsOutput.model_validate(parsed)

        assert output.summary == "Test summary"
        assert len(output.facts) == 1
        assert output.facts[0].title == "Budget limit"

    def test_empty_lists_valid(self) -> None:
        """Should accept empty facts/questions/contradictions."""
        output = ExtractFactsOutput(
            summary="Nothing to extract.",
            facts=[],
            open_questions=[],
            contradictions=[],
        )
        assert output.summary == "Nothing to extract."

    def test_model_dump_serialization(self) -> None:
        """Should serialize to dict properly."""
        chunk_id = uuid4()
        output = ExtractFactsOutput(
            summary="Test",
            facts=[
                FactItem(
                    fact_type="risk",
                    title="Security risk",
                    detail="No encryption specified",
                    confidence="low",
                    evidence=[
                        EvidenceRef(
                            chunk_id=chunk_id,
                            excerpt="data storage",
                            rationale="Implied",
                        )
                    ],
                )
            ],
            open_questions=[],
            contradictions=[],
        )

        # Use mode="json" for JSON-compatible serialization (UUIDs as strings)
        dumped = output.model_dump(mode="json")

        assert isinstance(dumped, dict)
        assert dumped["summary"] == "Test"
        assert len(dumped["facts"]) == 1
        assert dumped["facts"][0]["fact_type"] == "risk"
        # UUIDs should serialize to strings in JSON mode
        assert isinstance(dumped["facts"][0]["evidence"][0]["chunk_id"], str)
