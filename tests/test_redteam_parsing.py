"""Tests for red-team schema validation and parsing."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_redteam import (
    EvidenceRef,
    InsightTarget,
    RedTeamInsight,
    RedTeamOutput,
)


class TestEvidenceRef:
    def test_valid_evidence(self):
        evidence = EvidenceRef(
            chunk_id=uuid4(),
            excerpt="This is a direct quote from the chunk.",
            rationale="This supports the finding because...",
        )
        assert evidence.excerpt == "This is a direct quote from the chunk."

    def test_excerpt_max_length(self):
        long_excerpt = "x" * 300
        with pytest.raises(ValidationError) as exc_info:
            EvidenceRef(
                chunk_id=uuid4(),
                excerpt=long_excerpt,
                rationale="Rationale",
            )
        assert "excerpt" in str(exc_info.value).lower()


class TestInsightTarget:
    def test_valid_target(self):
        target = InsightTarget(
            kind="requirement",
            id="req-123",
            label="User authentication requirement",
        )
        assert target.kind == "requirement"

    def test_target_without_id(self):
        target = InsightTarget(
            kind="general",
            label="Overall scope issue",
        )
        assert target.id is None

    def test_invalid_kind(self):
        with pytest.raises(ValidationError):
            InsightTarget(
                kind="invalid_kind",
                label="Some label",
            )


class TestRedTeamInsight:
    def test_valid_insight(self):
        chunk_id = uuid4()
        insight = RedTeamInsight(
            severity="important",
            category="security",
            title="Missing authentication",
            finding="The API lacks proper authentication.",
            why="Unauthorized access could lead to data breaches.",
            suggested_action="needs_confirmation",
            targets=[InsightTarget(kind="general", label="API endpoints")],
            evidence=[
                EvidenceRef(
                    chunk_id=chunk_id,
                    excerpt="No auth mentioned for API",
                    rationale="Direct quote showing missing auth",
                )
            ],
        )
        assert insight.severity == "important"
        assert len(insight.evidence) == 1

    def test_insight_requires_evidence(self):
        with pytest.raises(ValidationError) as exc_info:
            RedTeamInsight(
                severity="minor",
                category="logic",
                title="Some issue",
                finding="Finding",
                why="Why it matters",
                suggested_action="apply_internally",
                targets=[],
                evidence=[],  # Empty - should fail
            )
        assert "evidence" in str(exc_info.value).lower()

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            RedTeamInsight(
                severity="extreme",  # Invalid
                category="logic",
                title="Title",
                finding="Finding",
                why="Why",
                suggested_action="apply_internally",
                evidence=[
                    EvidenceRef(
                        chunk_id=uuid4(),
                        excerpt="Quote",
                        rationale="Reason",
                    )
                ],
            )

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            RedTeamInsight(
                severity="minor",
                category="unknown_category",  # Invalid
                title="Title",
                finding="Finding",
                why="Why",
                suggested_action="apply_internally",
                evidence=[
                    EvidenceRef(
                        chunk_id=uuid4(),
                        excerpt="Quote",
                        rationale="Reason",
                    )
                ],
            )


class TestRedTeamOutput:
    def test_empty_insights(self):
        output = RedTeamOutput(insights=[])
        assert output.insights == []

    def test_output_with_insights(self):
        chunk_id = uuid4()
        output = RedTeamOutput(
            insights=[
                RedTeamInsight(
                    severity="critical",
                    category="data",
                    title="Data leak risk",
                    finding="PII could be exposed.",
                    why="Compliance violation.",
                    suggested_action="needs_confirmation",
                    evidence=[
                        EvidenceRef(
                            chunk_id=chunk_id,
                            excerpt="Store user data",
                            rationale="Shows data storage",
                        )
                    ],
                )
            ]
        )
        assert len(output.insights) == 1

    def test_parse_from_json(self):
        chunk_id = str(uuid4())
        json_str = json.dumps(
            {
                "insights": [
                    {
                        "severity": "minor",
                        "category": "ux",
                        "title": "Confusing UI",
                        "finding": "Button placement is confusing.",
                        "why": "Users might miss important actions.",
                        "suggested_action": "apply_internally",
                        "targets": [{"kind": "general", "label": "UI design"}],
                        "evidence": [
                            {
                                "chunk_id": chunk_id,
                                "excerpt": "Button should be prominent",
                                "rationale": "Shows expectation",
                            }
                        ],
                    }
                ]
            }
        )

        data = json.loads(json_str)
        output = RedTeamOutput.model_validate(data)

        assert len(output.insights) == 1
        assert output.insights[0].category == "ux"

    def test_model_dump_serialization(self):
        chunk_id = uuid4()
        output = RedTeamOutput(
            insights=[
                RedTeamInsight(
                    severity="important",
                    category="scope",
                    title="Scope creep",
                    finding="Requirements keep growing.",
                    why="Budget and timeline at risk.",
                    suggested_action="needs_confirmation",
                    evidence=[
                        EvidenceRef(
                            chunk_id=chunk_id,
                            excerpt="Add this feature too",
                            rationale="Shows additional request",
                        )
                    ],
                )
            ]
        )

        dumped = output.model_dump(mode="json")

        assert isinstance(dumped["insights"][0]["evidence"][0]["chunk_id"], str)
