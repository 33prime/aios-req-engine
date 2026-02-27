"""Tests for Phase 3-4 temporal weighting and confidence helpers in app.db.graph_queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.graph_queries import (
    _CERTAINTY_MAP,
    _classify_strength,
    _compute_recency_multiplier,
)


# ── _compute_recency_multiplier tests ──


class TestRecencyMultiplier:
    def test_within_7_days(self):
        """Chunk from 3 days ago → 1.5x multiplier."""
        recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        assert _compute_recency_multiplier(recent) == 1.5

    def test_7_to_30_days(self):
        """Chunk from 15 days ago → 1.0x multiplier."""
        mid = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        assert _compute_recency_multiplier(mid) == 1.0

    def test_over_30_days(self):
        """Chunk from 60 days ago → 0.5x multiplier."""
        old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        assert _compute_recency_multiplier(old) == 0.5

    def test_boundary_7_days(self):
        """Chunk from exactly 7 days ago → 1.5x (inclusive boundary)."""
        boundary = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        assert _compute_recency_multiplier(boundary) == 1.5

    def test_invalid_string(self):
        """Invalid date string → fallback 1.0x."""
        assert _compute_recency_multiplier("not-a-date") == 1.0

    def test_datetime_object(self):
        """Accepts datetime objects directly, not just strings."""
        dt = datetime.now(timezone.utc) - timedelta(days=2)
        assert _compute_recency_multiplier(dt) == 1.5

    def test_naive_datetime(self):
        """Naive datetime (no tzinfo) is handled gracefully."""
        dt = datetime.now() - timedelta(days=20)
        assert _compute_recency_multiplier(dt) == 1.0


# ── _classify_strength with floats ──


class TestClassifyStrengthFloat:
    def test_float_strong(self):
        """Float weight 5.2 → strong."""
        assert _classify_strength(5.2) == "strong"

    def test_float_moderate(self):
        """Float weight 3.5 → moderate."""
        assert _classify_strength(3.5) == "moderate"

    def test_float_weak(self):
        """Float weight 2.9 → weak."""
        assert _classify_strength(2.9) == "weak"

    def test_int_unchanged(self):
        """Int weights still work: backward compat."""
        assert _classify_strength(6) == "strong"
        assert _classify_strength(4) == "moderate"
        assert _classify_strength(1) == "weak"


# ── Phase 4: Certainty mapping tests ──


class TestCertaintyMap:
    def test_confirmed_client(self):
        """confirmed_client → confirmed."""
        assert _CERTAINTY_MAP["confirmed_client"] == "confirmed"

    def test_confirmed_consultant(self):
        """confirmed_consultant → confirmed."""
        assert _CERTAINTY_MAP["confirmed_consultant"] == "confirmed"

    def test_needs_client(self):
        """needs_client → review."""
        assert _CERTAINTY_MAP["needs_client"] == "review"

    def test_ai_generated(self):
        """ai_generated → inferred."""
        assert _CERTAINTY_MAP["ai_generated"] == "inferred"

    def test_unknown_defaults_inferred(self):
        """Unknown status not in map → .get() returns None, consumer defaults to inferred."""
        assert _CERTAINTY_MAP.get("some_unknown_status", "inferred") == "inferred"
