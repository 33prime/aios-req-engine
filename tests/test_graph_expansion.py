"""Tests for graph expansion in app.core.retrieval._expand_via_graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

# Valid UUID-format test IDs (required by UUID() conversion in _expand_via_graph)
E1 = "00000000-0000-0000-0000-000000000001"
E2 = "00000000-0000-0000-0000-000000000002"
E3 = "00000000-0000-0000-0000-000000000003"
E4 = "00000000-0000-0000-0000-000000000004"
PROJECT = "10000000-0000-0000-0000-000000000000"


@dataclass
class RetrievalResult:
    """Minimal stub matching app.core.retrieval.RetrievalResult."""

    chunks: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    beliefs: list[dict] = field(default_factory=list)
    source_queries: list[str] = field(default_factory=list)


def _neighborhood(entity_id: str, n_related: int = 2, n_chunks: int = 1) -> dict:
    """Build a mock neighborhood response."""
    return {
        "entity": {"id": entity_id},
        "evidence_chunks": [
            {"id": f"graph-chunk-{entity_id[:8]}-{i}", "content": "Evidence"}
            for i in range(n_chunks)
        ],
        "related": [
            {
                "entity_id": f"a{i}000000-0000-0000-0000-{entity_id[:12]}",
                "entity_type": "feature",
                "entity_name": f"Related Feature {i}",
                "shared_chunks": 3 - i,
            }
            for i in range(n_related)
        ],
    }


@pytest.mark.asyncio
async def test_expands_top_entities():
    """Graph expansion queries top 3 entities by similarity."""
    result = RetrievalResult(
        entities=[
            {"entity_id": E1, "entity_type": "feature", "similarity": 0.95},
            {"entity_id": E2, "entity_type": "persona", "similarity": 0.90},
            {"entity_id": E3, "entity_type": "workflow", "similarity": 0.85},
            {"entity_id": E4, "entity_type": "feature", "similarity": 0.50},
        ],
        chunks=[{"id": "c1", "content": "test"}],
    )

    calls = []

    def mock_neighborhood(entity_id, entity_type, project_id, max_related=5, **kwargs):
        calls.append(str(entity_id))
        return _neighborhood(str(entity_id))

    with patch("app.db.graph_queries.get_entity_neighborhood", mock_neighborhood):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    # Should query top 3 seeds (E1, E2, E3), not E4
    assert len(calls) == 3
    assert E1 in calls
    assert E2 in calls
    assert E3 in calls
    assert E4 not in calls
    # Original entities preserved + new related added
    assert len(out.entities) > 4


@pytest.mark.asyncio
async def test_deduplicates_entities():
    """No duplicate entity_ids in result after expansion."""
    result = RetrievalResult(
        entities=[
            {"entity_id": E1, "entity_type": "feature", "similarity": 0.9},
        ],
        chunks=[],
    )

    def mock_neighborhood(entity_id, entity_type, project_id, max_related=5, **kwargs):
        return {
            "entity": {"id": str(entity_id)},
            "evidence_chunks": [],
            "related": [
                {"entity_id": E1, "entity_type": "feature", "entity_name": "Dup"},
                {"entity_id": E2, "entity_type": "persona", "entity_name": "New"},
            ],
        }

    with patch("app.db.graph_queries.get_entity_neighborhood", mock_neighborhood):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    entity_ids = [e.get("entity_id", e.get("id", "")) for e in out.entities]
    assert len(entity_ids) == len(set(entity_ids))
    # E1 (original) + E2 (new) = 2
    assert len(entity_ids) == 2


@pytest.mark.asyncio
async def test_deduplicates_chunks():
    """No duplicate chunk_ids in result after expansion."""
    result = RetrievalResult(
        entities=[
            {"entity_id": E1, "entity_type": "feature", "similarity": 0.9},
        ],
        chunks=[{"id": "existing-chunk", "content": "existing"}],
    )

    def mock_neighborhood(entity_id, entity_type, project_id, max_related=5, **kwargs):
        return {
            "entity": {"id": str(entity_id)},
            "evidence_chunks": [
                {"id": "existing-chunk", "content": "dup"},
                {"id": "new-chunk", "content": "new evidence"},
            ],
            "related": [],
        }

    with patch("app.db.graph_queries.get_entity_neighborhood", mock_neighborhood):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    chunk_ids = [c.get("id", c.get("chunk_id", "")) for c in out.chunks]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert "new-chunk" in chunk_ids


@pytest.mark.asyncio
async def test_caps_at_max_total():
    """Respects _GRAPH_MAX_TOTAL=15 entity additions."""
    seeds = [
        {
            "entity_id": f"a000000{i}-0000-0000-0000-000000000000",
            "entity_type": "feature",
            "similarity": 0.9 - i * 0.01,
        }
        for i in range(3)
    ]
    result = RetrievalResult(entities=seeds, chunks=[])

    def mock_neighborhood(entity_id, entity_type, project_id, max_related=5, **kwargs):
        # Each seed returns 10 related — total would be 30 without cap
        return {
            "entity": {"id": str(entity_id)},
            "evidence_chunks": [],
            "related": [
                {
                    "entity_id": f"b{i}00000{entity_id.split('-')[0][-1]}"
                    f"-0000-0000-0000-000000000000",
                    "entity_type": "feature",
                    "entity_name": f"Related {i}",
                }
                for i in range(10)
            ],
        }

    with patch("app.db.graph_queries.get_entity_neighborhood", mock_neighborhood):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    graph_added = [e for e in out.entities if e.get("source") == "graph_expansion"]
    assert len(graph_added) <= 15


@pytest.mark.asyncio
async def test_empty_entities_noop():
    """No entities = no expansion, result unchanged."""
    result = RetrievalResult(
        entities=[],
        chunks=[{"id": "c1", "content": "test"}],
    )

    from app.core.retrieval import _expand_via_graph

    out = await _expand_via_graph(result, PROJECT)

    assert len(out.chunks) == 1
    assert len(out.entities) == 0


@pytest.mark.asyncio
async def test_graph_failure_graceful():
    """Exception in graph queries → original result returned unchanged."""
    result = RetrievalResult(
        entities=[
            {"entity_id": E1, "entity_type": "feature", "similarity": 0.9},
        ],
        chunks=[{"id": "c1", "content": "test"}],
    )

    with patch(
        "app.db.graph_queries.get_entity_neighborhood",
        side_effect=RuntimeError("DB down"),
    ):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    # Graceful degradation — originals preserved
    assert len(out.entities) >= 1
    assert len(out.chunks) >= 1


@pytest.mark.asyncio
async def test_marks_source():
    """Graph-expanded items have source='graph_expansion'."""
    result = RetrievalResult(
        entities=[
            {"entity_id": E1, "entity_type": "feature", "similarity": 0.9},
        ],
        chunks=[],
    )

    def mock_neighborhood(entity_id, entity_type, project_id, max_related=5, **kwargs):
        return {
            "entity": {"id": str(entity_id)},
            "evidence_chunks": [{"id": "graph-chunk-1", "content": "evidence"}],
            "related": [
                {"entity_id": E2, "entity_type": "persona", "entity_name": "User"},
            ],
        }

    with patch("app.db.graph_queries.get_entity_neighborhood", mock_neighborhood):
        from app.core.retrieval import _expand_via_graph

        out = await _expand_via_graph(result, PROJECT)

    graph_entities = [e for e in out.entities if e.get("source") == "graph_expansion"]
    graph_chunks = [c for c in out.chunks if c.get("source") == "graph_expansion"]

    assert len(graph_entities) == 1
    assert graph_chunks[0]["id"] == "graph-chunk-1"
