"""Test: retrieval cache is invalidated after tool execution.

Verifies that entity create/update/delete via tool execution busts
the topic-keyed retrieval cache so subsequent queries see fresh data.
"""

import pytest

from app.core.chat_context import (
    _check_retrieval_cache,
    _retrieval_cache,
    _store_retrieval_cache,
    invalidate_retrieval_cache,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure clean cache state for each test."""
    _retrieval_cache.clear()
    yield
    _retrieval_cache.clear()


class TestRetrievalCacheInvalidation:
    """Verify cache invalidation on tool execution."""

    def test_cache_stores_and_retrieves(self):
        _store_retrieval_cache("proj-1", ["feature"], "result A")
        assert _check_retrieval_cache("proj-1", ["feature"]) == "result A"

    def test_invalidation_clears_all_project_keys(self):
        """After tool execution, all cached retrievals for the
        project should be cleared."""
        _store_retrieval_cache("proj-1", ["feature"], "features result")
        _store_retrieval_cache("proj-1", ["persona"], "personas result")
        _store_retrieval_cache("proj-2", ["feature"], "other project")

        # Simulate tool execution invalidation
        invalidate_retrieval_cache("proj-1")

        # proj-1 caches are gone
        assert _check_retrieval_cache("proj-1", ["feature"]) is None
        assert _check_retrieval_cache("proj-1", ["persona"]) is None

        # proj-2 cache is untouched
        assert _check_retrieval_cache("proj-2", ["feature"]) == "other project"

    def test_create_entity_busts_cache(self):
        """Simulate: cache populated → entity created → cache busted → fresh query."""
        # 1. Cache a retrieval result
        _store_retrieval_cache("proj-1", ["feature"], "old features list")

        # 2. Verify cache hit
        assert _check_retrieval_cache("proj-1", ["feature"]) is not None

        # 3. Simulate tool execution (what chat_stream.py does after tools)
        invalidate_retrieval_cache("proj-1")

        # 4. Cache should be busted
        assert _check_retrieval_cache("proj-1", ["feature"]) is None

    def test_topic_order_independence(self):
        """Cache keys are sorted so topic order doesn't matter."""
        _store_retrieval_cache("proj-1", ["workflow", "feature"], "result")
        # Reversed order should still hit
        assert _check_retrieval_cache("proj-1", ["feature", "workflow"]) is not None

    def test_empty_topics(self):
        """Empty topic list should work without error."""
        _store_retrieval_cache("proj-1", [], "empty result")
        assert _check_retrieval_cache("proj-1", []) == "empty result"
        invalidate_retrieval_cache("proj-1")
        assert _check_retrieval_cache("proj-1", []) is None
