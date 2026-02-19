"""Tests for EntityPatch schema validation."""

import pytest
from pydantic import ValidationError

from app.core.schemas_entity_patch import (
    BeliefImpact,
    EntityPatch,
    EntityPatchList,
    EvidenceRef,
    PatchApplicationResult,
)


class TestEvidenceRef:
    def test_minimal(self):
        ref = EvidenceRef(chunk_id="abc123", quote="The system must support SSO")
        assert ref.chunk_id == "abc123"
        assert ref.page_or_section is None

    def test_full(self):
        ref = EvidenceRef(
            chunk_id="abc123",
            quote="The system must support SSO",
            page_or_section="Section 4.2",
        )
        assert ref.page_or_section == "Section 4.2"


class TestBeliefImpact:
    def test_supports(self):
        bi = BeliefImpact(
            belief_summary="Client prioritizes real-time features",
            impact="supports",
            new_evidence="Document explicitly requests real-time collaboration",
        )
        assert bi.impact == "supports"

    def test_contradicts(self):
        bi = BeliefImpact(
            belief_summary="CTO prefers async architecture",
            impact="contradicts",
            new_evidence="Section 3 requires synchronous data sync",
        )
        assert bi.impact == "contradicts"

    def test_refines(self):
        bi = BeliefImpact(
            belief_summary="Budget constraint ~$200K",
            impact="refines",
            new_evidence="Budget revised to $250K for phase 1",
        )
        assert bi.impact == "refines"

    def test_invalid_impact(self):
        with pytest.raises(ValidationError):
            BeliefImpact(
                belief_summary="test",
                impact="destroys",
                new_evidence="test",
            )


class TestEntityPatch:
    def test_create_feature(self):
        patch = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "SSO Integration", "priority_group": "must_have"},
            evidence=[EvidenceRef(chunk_id="c1", quote="SSO is required")],
            confidence="high",
            confidence_reasoning="Explicit requirement with deadline",
            source_authority="client",
            mention_count=3,
        )
        assert patch.operation == "create"
        assert patch.entity_type == "feature"
        assert patch.target_entity_id is None

    def test_merge_persona(self):
        patch = EntityPatch(
            operation="merge",
            entity_type="persona",
            target_entity_id="uuid-123",
            payload={"goals": ["Reduce manual data entry"]},
            evidence=[EvidenceRef(chunk_id="c2", quote="users hate entering data twice")],
            confidence="medium",
            source_authority="consultant",
        )
        assert patch.operation == "merge"
        assert patch.target_entity_id == "uuid-123"

    def test_update_workflow_step(self):
        patch = EntityPatch(
            operation="update",
            entity_type="workflow_step",
            target_entity_id="uuid-456",
            payload={"time_minutes": 15, "pain_description": "Manual verification takes too long"},
            confidence="very_high",
            confidence_reasoning="Direct client statement with number",
            source_authority="client",
        )
        assert patch.confidence == "very_high"

    def test_stale_data_entity(self):
        patch = EntityPatch(
            operation="stale",
            entity_type="data_entity",
            target_entity_id="uuid-789",
            payload={"stale_reason": "New data model replaces this entity"},
            confidence="high",
            source_authority="consultant",
        )
        assert patch.operation == "stale"

    def test_delete_competitor(self):
        patch = EntityPatch(
            operation="delete",
            entity_type="competitor",
            target_entity_id="uuid-comp",
            confidence="medium",
            source_authority="research",
        )
        assert patch.operation == "delete"

    def test_all_entity_types(self):
        """All 10 entity types are valid."""
        types = [
            "feature", "persona", "stakeholder", "workflow",
            "workflow_step", "data_entity", "business_driver",
            "constraint", "competitor", "vision",
        ]
        for entity_type in types:
            patch = EntityPatch(
                operation="create",
                entity_type=entity_type,
                payload={"name": f"Test {entity_type}"},
                confidence="medium",
                source_authority="research",
            )
            assert patch.entity_type == entity_type

    def test_all_operations(self):
        """All 5 operations are valid."""
        for op in ["create", "merge", "update", "stale", "delete"]:
            patch = EntityPatch(
                operation=op,
                entity_type="feature",
                target_entity_id="id" if op != "create" else None,
                payload={},
                confidence="medium",
                source_authority="research",
            )
            assert patch.operation == op

    def test_all_confidence_tiers(self):
        """All 5 confidence tiers are valid."""
        for tier in ["very_high", "high", "medium", "low", "conflict"]:
            patch = EntityPatch(
                operation="create",
                entity_type="feature",
                payload={},
                confidence=tier,
                source_authority="research",
            )
            assert patch.confidence == tier

    def test_all_source_authorities(self):
        """All 4 source authorities are valid."""
        for auth in ["client", "consultant", "research", "prototype"]:
            patch = EntityPatch(
                operation="create",
                entity_type="feature",
                payload={},
                confidence="medium",
                source_authority=auth,
            )
            assert patch.source_authority == auth

    def test_invalid_entity_type(self):
        with pytest.raises(ValidationError):
            EntityPatch(
                operation="create",
                entity_type="invalid_type",
                payload={},
                confidence="medium",
                source_authority="research",
            )

    def test_invalid_operation(self):
        with pytest.raises(ValidationError):
            EntityPatch(
                operation="purge",
                entity_type="feature",
                payload={},
                confidence="medium",
                source_authority="research",
            )

    def test_belief_impact_nesting(self):
        patch = EntityPatch(
            operation="update",
            entity_type="feature",
            target_entity_id="uuid-feat",
            payload={"overview": "Updated overview"},
            evidence=[EvidenceRef(chunk_id="c1", quote="Real-time sync required")],
            confidence="high",
            confidence_reasoning="Supports existing belief",
            belief_impact=[
                BeliefImpact(
                    belief_summary="Client wants real-time features",
                    impact="supports",
                    new_evidence="Explicit real-time requirement",
                ),
                BeliefImpact(
                    belief_summary="CTO prefers async",
                    impact="contradicts",
                    new_evidence="This requires sync",
                ),
            ],
            answers_question="q-auth-method",
            source_authority="client",
            mention_count=4,
        )
        assert len(patch.belief_impact) == 2
        assert patch.answers_question == "q-auth-method"

    def test_defaults(self):
        patch = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "test"},
        )
        assert patch.confidence == "medium"
        assert patch.source_authority == "research"
        assert patch.mention_count == 1
        assert patch.belief_impact == []
        assert patch.evidence == []
        assert patch.answers_question is None

    def test_vision_patch(self):
        """Vision is a special entity type (project-level, not per-entity)."""
        patch = EntityPatch(
            operation="update",
            entity_type="vision",
            payload={"statement": "Build the best project management tool"},
            confidence="high",
            source_authority="client",
        )
        assert patch.entity_type == "vision"


class TestEntityPatchList:
    def test_empty(self):
        pl = EntityPatchList()
        assert pl.patches == []
        assert pl.signal_id is None

    def test_with_patches(self):
        patches = [
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "Feature A"},
                confidence="high",
                source_authority="client",
            ),
            EntityPatch(
                operation="merge",
                entity_type="persona",
                target_entity_id="p1",
                payload={"goals": ["goal"]},
                confidence="medium",
                source_authority="consultant",
            ),
        ]
        pl = EntityPatchList(
            patches=patches,
            signal_id="sig-1",
            run_id="run-1",
            extraction_model="claude-sonnet-4-6",
            extraction_duration_ms=1500,
        )
        assert len(pl.patches) == 2
        assert pl.extraction_model == "claude-sonnet-4-6"


class TestPatchApplicationResult:
    def test_empty(self):
        result = PatchApplicationResult()
        assert result.total_applied == 0
        assert result.total_escalated == 0

    def test_with_counts(self):
        result = PatchApplicationResult(
            applied=[
                {"entity_type": "feature", "entity_id": "f1", "operation": "create", "name": "SSO"},
                {"entity_type": "persona", "entity_id": "p1", "operation": "merge", "name": "Admin"},
            ],
            skipped=[
                {"entity_type": "feature", "reason": "duplicate", "patch_summary": "SSO v2"},
            ],
            escalated=[
                {"entity_type": "feature", "reason": "low confidence", "patch": {}},
            ],
            entity_ids_modified=["f1", "p1"],
            created_count=1,
            merged_count=1,
            updated_count=0,
            staled_count=0,
            deleted_count=0,
        )
        assert result.total_applied == 2
        assert result.total_escalated == 1
        assert len(result.entity_ids_modified) == 2
