"""Tests for EntityPatch applicator."""

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.schemas_entity_patch import EntityPatch, EvidenceRef
from app.db.patch_applicator import (
    AUTHORITY_TO_STATUS,
    CONFIRMATION_HIERARCHY,
    ENTITY_TABLE_MAP,
    TABLES_WITH_SLUG,
    TABLES_WITH_SIGNAL_IDS,
    TABLE_FIELD_RENAMES,
    apply_entity_patches,
    _normalize_payload,
    _resolve_target_entity_id,
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

    def test_title_field(self):
        """Summarize patch uses title for entities without name."""
        p = EntityPatch(
            operation="create",
            entity_type="constraint",
            payload={"title": "Budget limit"},
            confidence="high",
            source_authority="client",
        )
        assert "Budget limit" in _summarize_patch(p)

    def test_description_field(self):
        """Summarize patch uses description for entities without name/label/title."""
        p = EntityPatch(
            operation="create",
            entity_type="business_driver",
            payload={"description": "Reduce cost", "driver_type": "goal"},
            confidence="high",
            source_authority="client",
        )
        assert "Reduce cost" in _summarize_patch(p)


class TestEntityTableMap:
    def test_competitor_table_name(self):
        """Competitor should map to competitor_references, not competitor_refs."""
        assert ENTITY_TABLE_MAP["competitor"] == "competitor_references"

    def test_all_entity_types_mapped(self):
        """All expected entity types have table mappings."""
        expected = {
            "feature", "persona", "stakeholder", "workflow",
            "workflow_step", "data_entity", "business_driver",
            "constraint", "competitor", "vision",
        }
        assert expected == set(ENTITY_TABLE_MAP.keys())


class TestNormalizePayload:
    def test_strips_slug_from_business_drivers(self):
        payload = {"description": "Reduce cost", "slug": "reduce-cost"}
        result = _normalize_payload("business_drivers", payload)
        assert "slug" not in result
        assert result["description"] == "Reduce cost"

    def test_strips_slug_from_vp_steps(self):
        payload = {"label": "Login Step", "slug": "login-step"}
        result = _normalize_payload("vp_steps", payload)
        assert "slug" not in result

    def test_strips_slug_from_data_entities(self):
        payload = {"name": "User Profile", "slug": "user-profile"}
        result = _normalize_payload("data_entities", payload)
        assert "slug" not in result

    def test_keeps_slug_for_personas(self):
        payload = {"name": "Admin User", "slug": "admin-user"}
        result = _normalize_payload("personas", payload)
        assert result["slug"] == "admin-user"

    def test_keeps_slug_for_prd_sections(self):
        payload = {"name": "Overview", "slug": "overview"}
        result = _normalize_payload("prd_sections", payload)
        assert result["slug"] == "overview"

    def test_renames_name_to_title_for_constraints(self):
        payload = {"name": "Budget limit", "description": "Max $50k"}
        result = _normalize_payload("constraints", payload)
        assert "name" not in result
        assert result["title"] == "Budget limit"
        assert result["description"] == "Max $50k"

    def test_no_rename_if_title_already_set_for_constraints(self):
        """If both name and title present, drop name, keep title."""
        payload = {"name": "old", "title": "Budget limit", "description": "details"}
        result = _normalize_payload("constraints", payload)
        assert result["title"] == "Budget limit"
        assert "name" not in result

    def test_noop_for_features(self):
        """Features need no normalization."""
        payload = {"name": "SSO", "priority_group": "must_have"}
        result = _normalize_payload("features", payload)
        assert result == payload

    def test_strips_source_signal_ids_from_constraints(self):
        payload = {"title": "Budget", "source_signal_ids": ["abc"]}
        result = _normalize_payload("constraints", payload)
        assert "source_signal_ids" not in result

    def test_keeps_source_signal_ids_for_features(self):
        payload = {"name": "SSO", "source_signal_ids": ["abc"]}
        result = _normalize_payload("features", payload)
        assert result["source_signal_ids"] == ["abc"]


class TestApplyCreateSchemaFixes:
    """Test that _apply_create handles schema differences correctly."""

    @pytest.mark.asyncio
    async def test_create_business_driver_no_slug(self, project_id, run_id, signal_id):
        """Creating a business_driver should NOT insert a slug field."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{
            "id": "new-bd-id", "description": "Reduce customer churn",
        }])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="business_driver",
                payload={"description": "Reduce customer churn", "driver_type": "goal"},
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
        insert_call = mock_table.insert.call_args[0][0]
        assert "slug" not in insert_call
        assert insert_call["description"] == "Reduce customer churn"

    @pytest.mark.asyncio
    async def test_create_constraint_name_becomes_title(self, project_id, run_id):
        """Creating a constraint with 'name' field should normalize to 'title'."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{
            "id": "new-c-id", "title": "Budget limit",
        }])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="constraint",
                payload={"name": "Budget limit", "constraint_type": "budget", "description": "Max $50k"},
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

        assert result.created_count == 1
        insert_call = mock_table.insert.call_args[0][0]
        assert "name" not in insert_call
        assert insert_call["title"] == "Budget limit"
        assert "slug" not in insert_call
        # constraints don't have source_signal_ids
        assert "source_signal_ids" not in insert_call

    @pytest.mark.asyncio
    async def test_create_persona_keeps_slug(self, project_id, run_id, signal_id):
        """Creating a persona should auto-generate slug."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{
            "id": "new-p-id", "name": "Admin User",
        }])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="persona",
                payload={"name": "Admin User"},
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
        insert_call = mock_table.insert.call_args[0][0]
        assert "slug" in insert_call
        assert insert_call["slug"] == "admin-user"

    @pytest.mark.asyncio
    async def test_create_vp_step_no_slug(self, project_id, run_id):
        """Creating a vp_step should NOT insert a slug field."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{
            "id": "new-vs-id", "label": "Fill out form",
        }])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="workflow_step",
                payload={"label": "Fill out form", "description": "User fills the form"},
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

        assert result.created_count == 1
        insert_call = mock_table.insert.call_args[0][0]
        assert "slug" not in insert_call
        assert insert_call["label"] == "Fill out form"


class TestRecordEvidenceLinks:
    """Test that evidence linking calls record_chunk_impacts correctly."""

    @pytest.mark.asyncio
    async def test_evidence_links_correct_signature(self, project_id, run_id, signal_id):
        """record_chunk_impacts should be called per-entity with correct args."""
        mock_sb, mock_table = _mock_supabase()

        # First call: insert (create)
        mock_table.execute.return_value = MagicMock(data=[{
            "id": "new-feat-id", "name": "SSO",
        }])

        patches = [
            EntityPatch(
                operation="create",
                entity_type="feature",
                payload={"name": "SSO Integration"},
                evidence=[EvidenceRef(chunk_id="chunk-1", quote="SSO is required")],
                confidence="high",
                source_authority="client",
            )
        ]

        mock_record = MagicMock()
        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.signals.record_chunk_impacts", mock_record),
        ):
            result = await apply_entity_patches(project_id, patches, run_id, signal_id)

        assert result.created_count == 1
        # Evidence linking should have been attempted
        # (create patches may not match by target_entity_id, but the function should not crash)

    @pytest.mark.asyncio
    async def test_evidence_links_merge_matches_target(self, project_id, run_id, signal_id):
        """Merge patches should link evidence via target_entity_id."""
        mock_sb, mock_table = _mock_supabase()

        target_id = str(uuid4())
        mock_table.execute.side_effect = [
            # select existing
            MagicMock(data={
                "id": target_id,
                "name": "Dashboard",
                "confirmation_status": "ai_generated",
                "evidence": [],
                "source_signal_ids": [],
            }),
            # update
            MagicMock(data=[{"id": target_id}]),
        ]

        patches = [
            EntityPatch(
                operation="merge",
                entity_type="feature",
                target_entity_id=target_id,
                payload={"overview": "Updated overview"},
                evidence=[EvidenceRef(chunk_id="chunk-2", quote="Dashboard metrics")],
                confidence="high",
                source_authority="consultant",
            )
        ]

        mock_record = MagicMock()
        with (
            patch("app.db.patch_applicator.get_supabase", return_value=mock_sb),
            patch("app.db.patch_applicator._record_state_revision"),
            patch("app.db.signals.record_chunk_impacts", mock_record),
        ):
            result = await apply_entity_patches(project_id, patches, run_id, signal_id)

        assert result.merged_count == 1
        # record_chunk_impacts should be called with correct per-entity signature
        mock_record.assert_called_once_with(
            chunk_ids=["chunk-2"],
            entity_type="feature",
            entity_id=UUID(target_id),
        )


class TestResolveTargetEntityId:
    """Test UUID prefix-matching fallback for truncated LLM UUIDs."""

    def test_full_uuid_passes_through(self, project_id):
        """Full 36-char UUIDs should not trigger resolution."""
        full_id = "aeb74d67-0bee-4eaa-b25c-6957a724b484"
        p = EntityPatch(
            operation="merge",
            entity_type="feature",
            target_entity_id=full_id,
            payload={"overview": "test"},
            confidence="high",
            source_authority="client",
        )
        result = _resolve_target_entity_id(project_id, p, "features")
        assert result.target_entity_id == full_id

    def test_none_target_passes_through(self, project_id):
        """None target_entity_id should pass through."""
        p = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "test"},
            confidence="high",
            source_authority="client",
        )
        result = _resolve_target_entity_id(project_id, p, "features")
        assert result.target_entity_id is None

    def test_prefix_resolves_to_full_uuid(self, project_id):
        """8-char prefix should resolve to matching full UUID."""
        full_id = "aeb74d67-0bee-4eaa-b25c-6957a724b484"
        prefix = "aeb74d67"

        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[
            {"id": full_id},
            {"id": "bbbb1111-2222-3333-4444-555566667777"},
        ])

        p = EntityPatch(
            operation="merge",
            entity_type="feature",
            target_entity_id=prefix,
            payload={"overview": "test"},
            confidence="high",
            source_authority="client",
        )

        with patch("app.db.patch_applicator.get_supabase", return_value=mock_sb):
            result = _resolve_target_entity_id(project_id, p, "features")

        assert result.target_entity_id == full_id

    def test_ambiguous_prefix_returns_unchanged(self, project_id):
        """Prefix matching multiple entities should not resolve."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[
            {"id": "aeb74d67-0bee-4eaa-b25c-6957a724b484"},
            {"id": "aeb74d67-ffff-eeee-dddd-ccccbbbbaaaa"},
        ])

        p = EntityPatch(
            operation="update",
            entity_type="feature",
            target_entity_id="aeb74d67",
            payload={"overview": "test"},
            confidence="high",
            source_authority="client",
        )

        with patch("app.db.patch_applicator.get_supabase", return_value=mock_sb):
            result = _resolve_target_entity_id(project_id, p, "features")

        # Should return unchanged — ambiguous
        assert result.target_entity_id == "aeb74d67"

    def test_no_match_returns_unchanged(self, project_id):
        """Prefix matching no entities should return unchanged."""
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[
            {"id": "bbbb1111-2222-3333-4444-555566667777"},
        ])

        p = EntityPatch(
            operation="merge",
            entity_type="feature",
            target_entity_id="aeb74d67",
            payload={"overview": "test"},
            confidence="high",
            source_authority="client",
        )

        with patch("app.db.patch_applicator.get_supabase", return_value=mock_sb):
            result = _resolve_target_entity_id(project_id, p, "features")

        assert result.target_entity_id == "aeb74d67"

    def test_preserves_all_patch_fields(self, project_id):
        """Resolved patch should preserve all original fields."""
        full_id = "aeb74d67-0bee-4eaa-b25c-6957a724b484"
        mock_sb, mock_table = _mock_supabase()
        mock_table.execute.return_value = MagicMock(data=[{"id": full_id}])

        p = EntityPatch(
            operation="merge",
            entity_type="feature",
            target_entity_id="aeb74d67",
            payload={"overview": "enriched overview"},
            evidence=[EvidenceRef(chunk_id="c1", quote="important quote")],
            confidence="high",
            confidence_reasoning="Clear statement",
            source_authority="client",
            mention_count=3,
            answers_question="q-123",
        )

        with patch("app.db.patch_applicator.get_supabase", return_value=mock_sb):
            result = _resolve_target_entity_id(project_id, p, "features")

        assert result.target_entity_id == full_id
        assert result.operation == "merge"
        assert result.entity_type == "feature"
        assert result.payload == {"overview": "enriched overview"}
        assert len(result.evidence) == 1
        assert result.confidence == "high"
        assert result.confidence_reasoning == "Clear statement"
        assert result.source_authority == "client"
        assert result.mention_count == 3
        assert result.answers_question == "q-123"

    @pytest.mark.asyncio
    async def test_end_to_end_prefix_resolution(self, project_id, run_id, signal_id):
        """Full pipeline: merge with truncated UUID should resolve and succeed."""
        full_id = "aeb74d67-0bee-4eaa-b25c-6957a724b484"
        mock_sb, mock_table = _mock_supabase()

        # Call sequence:
        # 1. _resolve: select all features in project
        # 2. _apply_merge: select entity by full ID
        # 3. _apply_merge: update entity
        mock_table.execute.side_effect = [
            # _resolve: project features
            MagicMock(data=[
                {"id": full_id},
                {"id": "cccc2222-3333-4444-5555-666677778888"},
            ]),
            # _apply_merge: select existing entity
            MagicMock(data={
                "id": full_id,
                "name": "Dashboard",
                "confirmation_status": "ai_generated",
                "evidence": [],
                "source_signal_ids": [],
            }),
            # _apply_merge: update
            MagicMock(data=[{"id": full_id}]),
        ]

        patches = [
            EntityPatch(
                operation="merge",
                entity_type="feature",
                target_entity_id="aeb74d67",  # Truncated!
                payload={"overview": "Updated from signal"},
                evidence=[EvidenceRef(chunk_id="c1", quote="Dashboard details")],
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
        assert full_id in result.entity_ids_modified
