"""Tests for EntityPatch applicator."""

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pytest

from app.core.schemas_entity_patch import EntityPatch, EvidenceRef
from app.db.patch_applicator import (
    AUTHORITY_TO_STATUS,
    CONFIRMATION_HIERARCHY,
    apply_entity_patches,
    _summarize_patch,
)


@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def run_id():
    return uuid4()


@pytest.fixture
def signal_id():
    return uuid4()


def _mock_supabase():
    """Create a mock supabase client with chainable methods."""
    mock_sb = MagicMock()
    mock_table = MagicMock()

    # Make chainable: table().select().eq().single().execute()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table

    mock_sb.table.return_value = mock_table
    return mock_sb, mock_table


class TestConfirmationHierarchy:
    def test_hierarchy_order(self):
        assert CONFIRMATION_HIERARCHY["ai_generated"] < CONFIRMATION_HIERARCHY["confirmed_consultant"]
        assert CONFIRMATION_HIERARCHY["confirmed_consultant"] < CONFIRMATION_HIERARCHY["confirmed_client"]

    def test_authority_mapping(self):
        assert AUTHORITY_TO_STATUS["client"] == "confirmed_client"
        assert AUTHORITY_TO_STATUS["consultant"] == "confirmed_consultant"
        assert AUTHORITY_TO_STATUS["research"] == "ai_generated"
        assert AUTHORITY_TO_STATUS["prototype"] == "ai_generated"


class TestApplyEntityPatches:
    @pytest.mark.asyncio
    async def test_create_feature(self, project_id, run_id, signal_id):
        """CREATE operation inserts new entity."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": "new-feat-id", "name": "SSO"}])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "SSO Integration", "priority_group": "must_have"},
                evidence=[EvidenceRef(chunk_id="c1", quote="SSO is required")],
                confidence="high",
                source_authority="client",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id, signal_id)

        assert result.created_count == 1
        assert result.total_applied == 1
        assert len(result.entity_ids_modified) == 1

        # Verify insert was called with correct data
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["name"] == "SSO Integration"
        assert insert_call["confirmation_status"] == "confirmed_client"
        assert insert_call["project_id"] == str(project_id)

    @pytest.mark.asyncio
    async def test_merge_appends_evidence(self, project_id, run_id, signal_id):
        """MERGE operation appends evidence and merges fields."""
        mock_sb, mock_table = _mock_supabase()

        # Existing entity for the load
        mock_table.execute.side_effect = [
            # First call: select existing entity
            MagicMock(data={
                "id": "feat-1",
                "name": "Dashboard",
                "confirmation_status": "ai_generated",
                "evidence": [{"chunk_id": "old", "quote": "old evidence"}],
                "source_signal_ids": [],
            }),
            # Second call: update
            MagicMock(data=[{"id": "feat-1"}]),
        ]

        patches = [
            EntityPatch(
                operation="merge",
                entity_type="feature",
                target_entity_id="feat-1",
                payload={"overview": "New overview text"},
                evidence=[EvidenceRef(chunk_id="c2", quote="Dashboard should show metrics")],
                confidence="high",
                source_authority="consultant",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id, signal_id)

        assert result.merged_count == 1
        assert result.total_applied == 1

        # Verify update was called with merged evidence
        update_call = mock_table.update.call_args[0][0]
        assert len(update_call["evidence"]) == 2  # old + new

    @pytest.mark.asyncio
    async def test_update_respects_hierarchy(self, project_id, run_id):
        """UPDATE should not downgrade confirmed entities from weaker authority."""
        mock_sb, mock_table = _mock_supabase()

        # Entity confirmed by client
        mock_table.execute.return_value = MagicMock(data={
            "confirmation_status": "confirmed_client",
            "name": "Protected Feature",
        })

        patches = [
            EntityPatch(
                operation="update",
                entity_type="feature",
                target_entity_id="feat-protected",
                payload={"name": "Changed Name"},
                confidence="high",
                source_authority="research",  # Weaker than confirmed_client
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        # Update should be skipped — research can't override confirmed_client
        assert result.updated_count == 0
        assert len(result.skipped) == 1

    @pytest.mark.asyncio
    async def test_stale_marks_entity(self, project_id, run_id):
        """STALE operation sets is_stale on the entity."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": "de-1"}])

        patches = [
            EntityPatch(
                operation="stale",
                entity_type="data_entity",
                target_entity_id="de-1",
                payload={"stale_reason": "New data model replaces this"},
                confidence="high",
                source_authority="consultant",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        assert result.staled_count == 1

        # Verify update was called with stale fields
        update_call = mock_table.update.call_args[0][0]
        assert update_call["is_stale"] is True
        assert "New data model" in update_call["stale_reason"]

    @pytest.mark.asyncio
    async def test_delete_ai_generated(self, project_id, run_id):
        """DELETE on ai_generated entity actually deletes it."""
        mock_sb, mock_table = _mock_supabase()

        # First call: select returns ai_generated
        # Second call: delete
        mock_table.execute.side_effect = [
            MagicMock(data={"confirmation_status": "ai_generated", "name": "Draft Feature"}),
            MagicMock(data=[]),
        ]

        patches = [
            EntityPatch(
                operation="delete",
                entity_type="feature",
                target_entity_id="feat-draft",
                confidence="high",
                source_authority="consultant",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        assert result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_delete_confirmed_marks_stale(self, project_id, run_id):
        """DELETE on confirmed entity marks stale instead of deleting."""
        mock_sb, mock_table = _mock_supabase()

        # First call: select returns confirmed
        # Second call: update (stale)
        mock_table.execute.side_effect = [
            MagicMock(data={"confirmation_status": "confirmed_client", "name": "Confirmed Feature"}),
            MagicMock(data=[]),
        ]

        patches = [
            EntityPatch(
                operation="delete",
                entity_type="feature",
                target_entity_id="feat-confirmed",
                confidence="high",
                source_authority="consultant",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        # Should stale, not delete
        assert result.staled_count == 1
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_confidence_filtering(self, project_id, run_id):
        """Low/conflict confidence patches are escalated, not applied."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": "new-id", "name": "High"}])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "High confidence"},
                confidence="high",
                source_authority="client",
            ),
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "Low confidence"},
                confidence="low",
                source_authority="research",
            ),
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "Conflict"},
                confidence="conflict",
                confidence_reasoning="Contradicts existing belief",
                source_authority="research",
            ),
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        assert result.created_count == 1  # Only high confidence applied
        assert result.total_escalated == 2  # Low + conflict escalated

    @pytest.mark.asyncio
    async def test_state_revision_created(self, project_id, run_id, signal_id):
        """State revision should be recorded after successful application."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": "new-id", "name": "Test"}])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "Test Feature"},
                confidence="high",
                source_authority="client",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision") as mock_revision,
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id, signal_id)

        mock_revision.assert_called_once()

    @pytest.mark.asyncio
    async def test_vision_patch(self, project_id, run_id):
        """Vision patches update the project record."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": str(project_id)}])

        patches = [
            EntityPatch(
                operation="update",
                entity_type="vision",
                payload={"statement": "Build the best education platform"},
                confidence="high",
                source_authority="client",
            )
        ]

        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.patch_applicator._record_evidence_links"),
        ):
            result = await apply_entity_patches(project_id, patches, run_id)

        assert result.total_applied == 1

        # Verify it updated the projects table
        mock_sb.table.assert_any_call("projects")
        update_call = mock_table.update.call_args[0][0]
        assert "vision" in update_call


class TestSummarizePatch:
    def test_create(self):
        patch = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "SSO"},
            confidence="high",
            source_authority="client",
        )
        assert "create feature: SSO" in _summarize_patch(patch)

    def test_truncation(self):
        patch = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "A" * 200},
            confidence="high",
            source_authority="client",
        )
        assert len(_summarize_patch(patch)) <= 100
