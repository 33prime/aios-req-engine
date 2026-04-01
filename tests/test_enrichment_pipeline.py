"""Tests for Phase 1: Enrichment + Multi-Vector Embeddings.

Covers:
- EntityPatch enrichment fields
- Enrichment chain batching and tool schema
- Multi-vector text builders (identity, intent, relationship, status)
- Dedup with enriched text (Tier 3 upgrade)
- embed_entity_multivector function
- Config USE_MULTI_VECTOR flag
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest

from app.core.schemas_entity_patch import EntityPatch, EntityPatchList


# =============================================================================
# Helpers
# =============================================================================


def _mock_execute(data=None, count=None):
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


def _make_patch(
    entity_type: str = "feature",
    operation: str = "create",
    name: str = "Test Feature",
    canonical_text: str | None = None,
    hypothetical_questions: list[str] | None = None,
    expanded_terms: list[str] | None = None,
) -> EntityPatch:
    payload = {"name": name, "overview": "Test overview"}
    if entity_type == "business_driver":
        payload = {"description": name, "driver_type": "pain"}
    return EntityPatch(
        operation=operation,
        entity_type=entity_type,
        payload=payload,
        confidence="high",
        canonical_text=canonical_text,
        hypothetical_questions=hypothetical_questions,
        expanded_terms=expanded_terms,
    )


# =============================================================================
# EntityPatch Schema Tests
# =============================================================================


class TestEntityPatchEnrichmentFields:
    """Test that enrichment fields exist and are optional."""

    def test_enrichment_fields_default_none(self):
        patch = EntityPatch(operation="create", entity_type="feature", payload={"name": "X"})
        assert patch.canonical_text is None
        assert patch.hypothetical_questions is None
        assert patch.expanded_terms is None
        assert patch.enrichment_data is None

    def test_enrichment_fields_settable(self):
        patch = EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": "X"},
            canonical_text="[ENTITY] X [TYPE] feature",
            hypothetical_questions=["What tracks inventory?", "How to classify items?"],
            expanded_terms=["SKU", "warehouse", "barcode"],
            enrichment_data={"actors": ["Sarah"], "downstream_impacts": ["reporting"]},
        )
        assert patch.canonical_text == "[ENTITY] X [TYPE] feature"
        assert len(patch.hypothetical_questions) == 2
        assert "SKU" in patch.expanded_terms
        assert patch.enrichment_data["actors"] == ["Sarah"]

    def test_enrichment_fields_serializable(self):
        patch = _make_patch(
            canonical_text="test",
            hypothetical_questions=["q1"],
            expanded_terms=["t1"],
        )
        data = patch.model_dump()
        assert data["canonical_text"] == "test"
        assert data["hypothetical_questions"] == ["q1"]

    def test_existing_fields_unchanged(self):
        patch = _make_patch()
        assert patch.operation == "create"
        assert patch.entity_type == "feature"
        assert patch.confidence == "high"
        assert patch.source_authority == "research"
        assert patch.mention_count == 1

    def test_entity_patch_list_with_enrichment(self):
        patches = [
            _make_patch(canonical_text="enriched1"),
            _make_patch(canonical_text=None),
        ]
        pl = EntityPatchList(patches=patches)
        assert len(pl.patches) == 2
        assert pl.patches[0].canonical_text == "enriched1"
        assert pl.patches[1].canonical_text is None


# =============================================================================
# Multi-Vector Text Builder Tests
# =============================================================================


class TestMultiVectorTextBuilders:
    """Test the 4 text builder functions."""

    def test_build_identity_with_canonical(self):
        from app.db.entity_embeddings import build_identity_text

        enrichment = {"canonical_text": "[ENTITY] AI Classification [TYPE] feature [STATE] proposed"}
        text = build_identity_text("feature", {"name": "AI Classification"}, enrichment)
        assert "[ENTITY] AI Classification" in text
        assert "[TYPE] feature" in text

    def test_build_identity_fallback_no_enrichment(self):
        from app.db.entity_embeddings import build_identity_text

        text = build_identity_text("feature", {"name": "AI Class", "overview": "Auto-classify items"}, {})
        assert "AI Class" in text
        assert "Auto-classify" in text

    def test_build_identity_empty_enrichment(self):
        from app.db.entity_embeddings import build_identity_text

        text = build_identity_text("feature", {"name": "Test"}, {"canonical_text": ""})
        # Empty canonical_text falls back to legacy builder
        assert "Test" in text

    def test_build_intent_with_questions_and_terms(self):
        from app.db.entity_embeddings import build_intent_text

        enrichment = {
            "hypothetical_questions": ["How to classify inventory?", "What reduces errors?"],
            "expanded_terms": ["SKU", "warehouse", "barcode"],
        }
        text = build_intent_text("feature", {}, enrichment)
        assert "Questions this answers:" in text
        assert "How to classify inventory?" in text
        assert "Related concepts:" in text
        assert "SKU" in text

    def test_build_intent_empty_enrichment(self):
        from app.db.entity_embeddings import build_intent_text

        text = build_intent_text("feature", {}, {})
        assert text == ""

    def test_build_intent_only_questions(self):
        from app.db.entity_embeddings import build_intent_text

        enrichment = {"hypothetical_questions": ["What is this?"]}
        text = build_intent_text("feature", {}, enrichment)
        assert "Questions this answers:" in text
        assert "Related concepts:" not in text

    def test_build_relationship_with_links(self):
        from app.db.entity_embeddings import build_relationship_text

        links = [
            {"target_name": "Nurse", "dependency_type": "targets"},
            {"target_name": "EHR System", "dependency_type": "uses"},
        ]
        enrichment = {"downstream_impacts": ["reporting accuracy"]}
        text = build_relationship_text("feature", {}, enrichment, links)
        assert "Nurse (targets)" in text
        assert "EHR System (uses)" in text
        assert "reporting accuracy" in text

    def test_build_relationship_no_links(self):
        from app.db.entity_embeddings import build_relationship_text

        text = build_relationship_text("feature", {}, {}, None)
        assert text == ""

    def test_build_relationship_with_before_after(self):
        from app.db.entity_embeddings import build_relationship_text

        enrichment = {"before_after": {"before": ["data entry"], "after": ["auto-import"]}}
        text = build_relationship_text("workflow", {}, enrichment)
        assert "Before: data entry" in text
        assert "After: auto-import" in text

    def test_build_status_feature(self):
        from app.db.entity_embeddings import build_status_text

        entity = {
            "confirmation_status": "confirmed_consultant",
            "version": 3,
            "priority_group": "must_have",
            "is_mvp": True,
        }
        text = build_status_text("feature", entity)
        assert "[CONFIDENCE] confirmed_consultant" in text
        assert "[VERSION] 3" in text
        assert "[PRIORITY] must_have" in text
        assert "[MVP] yes" in text

    def test_build_status_business_driver(self):
        from app.db.entity_embeddings import build_status_text

        entity = {
            "confirmation_status": "ai_generated",
            "driver_type": "pain",
            "severity": "critical",
        }
        text = build_status_text("business_driver", entity)
        assert "[DRIVER_TYPE] pain" in text
        assert "[SEVERITY] critical" in text

    def test_build_status_stale_entity(self):
        from app.db.entity_embeddings import build_status_text

        entity = {"confirmation_status": "ai_generated", "is_stale": True}
        text = build_status_text("feature", entity)
        assert "[STALE] yes" in text

    def test_build_status_minimal(self):
        from app.db.entity_embeddings import build_status_text

        text = build_status_text("constraint", {})
        assert "[CONFIDENCE] unknown" in text


# =============================================================================
# Enrichment Chain Tests
# =============================================================================


class TestEnrichmentChain:
    """Test enrichment chain batching and tool schema."""

    def test_enrichment_tool_schema_valid(self):
        from app.chains.enrich_entity_patches import ENRICHMENT_TOOL

        assert ENRICHMENT_TOOL["name"] == "submit_enrichments"
        schema = ENRICHMENT_TOOL["input_schema"]
        assert "enrichments" in schema["properties"]
        items = schema["properties"]["enrichments"]["items"]
        required = items["required"]
        assert "patch_index" in required
        assert "canonical_text" in required
        assert "hypothetical_questions" in required
        assert "expanded_terms" in required

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_enrich_empty_patches(self, mock_anthropic_cls):
        from app.chains.enrich_entity_patches import enrich_entity_patches

        result = await enrich_entity_patches([], "", uuid4())
        assert result == []

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    @patch("app.core.config.Settings")
    async def test_enrich_populates_fields(self, mock_settings, mock_anthropic_cls):
        from app.chains.enrich_entity_patches import enrich_entity_patches

        # Mock the Anthropic client
        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

        # Mock response with tool_use block
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = {
            "enrichments": [{
                "patch_index": 0,
                "canonical_text": "[ENTITY] Test [TYPE] feature",
                "hypothetical_questions": ["What tracks inventory?"],
                "expanded_terms": ["SKU", "warehouse"],
            }]
        }
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        patches = [_make_patch()]
        result = await enrich_entity_patches(patches, "", uuid4())

        assert len(result) == 1
        assert result[0].canonical_text == "[ENTITY] Test [TYPE] feature"
        assert result[0].hypothetical_questions == ["What tracks inventory?"]
        assert result[0].expanded_terms == ["SKU", "warehouse"]

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    @patch("app.core.config.Settings")
    async def test_enrich_failure_returns_raw_patches(self, mock_settings, mock_anthropic_cls):
        from app.chains.enrich_entity_patches import enrich_entity_patches

        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client
        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

        # Simulate API failure
        from anthropic import APIConnectionError
        mock_client.messages.create = AsyncMock(side_effect=APIConnectionError(request=MagicMock()))

        patches = [_make_patch()]
        result = await enrich_entity_patches(patches, "", uuid4())

        # Should return original patches without enrichment
        assert len(result) == 1
        assert result[0].canonical_text is None


# =============================================================================
# Embed Entity Multivector Tests
# =============================================================================


class TestEmbedEntityMultivector:
    """Test the multi-vector embedding function."""

    @pytest.mark.asyncio
    @patch("app.db.entity_embeddings.get_supabase")
    @patch("app.db.entity_embeddings.embed_texts_async")
    async def test_generates_multiple_vectors(self, mock_embed, mock_sb):
        from app.db.entity_embeddings import embed_entity_multivector

        mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]  # identity + status

        sb = MagicMock()
        mock_sb.return_value = sb
        upsert_mock = MagicMock()
        upsert_mock.execute.return_value = _mock_execute()
        sb.table.return_value.upsert.return_value = upsert_mock
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _mock_execute()

        await embed_entity_multivector(
            entity_type="feature",
            entity_id=uuid4(),
            entity_data={"name": "Test", "confirmation_status": "ai_generated"},
            project_id=uuid4(),
            enrichment={"canonical_text": "[ENTITY] Test [TYPE] feature"},
        )

        # Should have called embed_texts_async with texts
        mock_embed.assert_called_once()
        texts = mock_embed.call_args[0][0]
        assert len(texts) >= 2  # identity + status at minimum

    @pytest.mark.asyncio
    @patch("app.db.entity_embeddings.get_supabase")
    @patch("app.db.entity_embeddings.embed_texts_async")
    async def test_skips_empty_vectors(self, mock_embed, mock_sb):
        from app.db.entity_embeddings import embed_entity_multivector

        # No enrichment = no intent vector, no relationship vector
        mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

        sb = MagicMock()
        mock_sb.return_value = sb
        upsert_mock = MagicMock()
        upsert_mock.execute.return_value = _mock_execute()
        sb.table.return_value.upsert.return_value = upsert_mock
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _mock_execute()

        await embed_entity_multivector(
            entity_type="feature",
            entity_id=uuid4(),
            entity_data={"name": "Test Feature Name", "overview": "A longer overview text here", "confirmation_status": "ai_generated"},
            project_id=uuid4(),
            enrichment={},  # No enrichment
        )

        # Only identity + status should be generated (intent and relationship are empty)
        texts = mock_embed.call_args[0][0]
        assert len(texts) == 2

    @pytest.mark.asyncio
    @patch("app.db.entity_embeddings.get_supabase")
    @patch("app.db.entity_embeddings.embed_texts_async")
    async def test_writes_legacy_column(self, mock_embed, mock_sb):
        from app.db.entity_embeddings import embed_entity_multivector

        mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

        sb = MagicMock()
        mock_sb.return_value = sb
        upsert_mock = MagicMock()
        upsert_mock.execute.return_value = _mock_execute()
        sb.table.return_value.upsert.return_value = upsert_mock
        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value = _mock_execute()
        sb.table.return_value.update.return_value = update_chain

        await embed_entity_multivector(
            entity_type="feature",
            entity_id=uuid4(),
            entity_data={"name": "Test Feature Name", "confirmation_status": "ai_generated"},
            project_id=uuid4(),
            enrichment={"canonical_text": "[ENTITY] Test Feature Name [TYPE] feature"},
        )

        # Should write to entity_vectors AND legacy features table
        table_calls = [c[0][0] for c in sb.table.call_args_list]
        assert "entity_vectors" in table_calls
        assert "features" in table_calls


# =============================================================================
# Dedup with Enriched Text Tests
# =============================================================================


class TestDedupEnrichedText:
    """Test that dedup Tier 3 uses enriched text when available."""

    @pytest.mark.asyncio
    @patch("app.db.supabase_client.get_supabase")
    @patch("app.core.embeddings.embed_texts")
    async def test_enriched_text_used_for_embedding(self, mock_embed, mock_sb):
        from app.core.entity_dedup import _check_embedding_similarity

        mock_embed.return_value = [[0.1] * 1536]

        sb = MagicMock()
        mock_sb.return_value = sb
        # match_entity_vectors returns no matches
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = _mock_execute([])
        sb.rpc.return_value = rpc_mock

        patch = _make_patch(
            canonical_text="[ENTITY] AI Classification [TYPE] feature [CONTEXT] auto-classify",
            hypothetical_questions=["How to classify?", "What reduces errors?"],
            expanded_terms=["SKU", "barcode"],
        )

        result = await _check_embedding_similarity(patch, "feature", uuid4())

        # Verify the embedded text includes enrichment
        embedded_text = mock_embed.call_args[0][0][0]
        assert "AI Classification" in embedded_text
        assert "How to classify?" in embedded_text
        assert "SKU" in embedded_text

    @pytest.mark.asyncio
    @patch("app.db.supabase_client.get_supabase")
    @patch("app.core.embeddings.embed_texts")
    async def test_fallback_to_legacy_text(self, mock_embed, mock_sb):
        from app.core.entity_dedup import _check_embedding_similarity

        mock_embed.return_value = [[0.1] * 1536]

        sb = MagicMock()
        mock_sb.return_value = sb
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = _mock_execute([])
        sb.rpc.return_value = rpc_mock

        # No enrichment on patch
        patch = _make_patch(canonical_text=None)

        result = await _check_embedding_similarity(patch, "feature", uuid4())

        # Should use legacy text builder
        embedded_text = mock_embed.call_args[0][0][0]
        assert "Test Feature" in embedded_text


# =============================================================================
# Config Tests
# =============================================================================


class TestConfig:
    """Test USE_MULTI_VECTOR config flag."""

    def test_use_multi_vector_default_true(self):
        from app.core.config import Settings
        s = Settings()
        assert s.USE_MULTI_VECTOR is True

    def test_cosine_similarity(self):
        from app.core.embeddings import cosine_similarity

        # Identical vectors
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

        # Orthogonal vectors
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

        # Opposite vectors
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

        # Zero vector
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# =============================================================================
# Patch Applicator Enrichment Storage Tests
# =============================================================================


class TestPatchApplicatorEnrichment:
    """Test that enrichment_intel is stored during patch application."""

    def test_merge_string_lists_deduplicates(self):
        from app.db.patch_applicator import _merge_string_lists

        existing = ["Apple", "banana"]
        new = ["APPLE", "cherry", "Banana"]
        result = _merge_string_lists(existing, new)
        assert len(result) == 3
        assert "Apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_merge_string_lists_empty(self):
        from app.db.patch_applicator import _merge_string_lists

        assert _merge_string_lists([], []) == []
        assert _merge_string_lists(["a"], []) == ["a"]
        assert _merge_string_lists([], ["b"]) == ["b"]
