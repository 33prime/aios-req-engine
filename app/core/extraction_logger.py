"""Accumulates extraction audit data across pipeline stages.

Lightweight class that pipeline nodes append to. Serializes to dict for
JSONB storage on the signals.extraction_log column.

Usage:
    log = ExtractionLog(run_id="abc", model="claude-haiku-4-5-20251001")
    log.log_context(snapshot)
    log.log_chunk_result(chunk_id, 0, "Introduction", 1200, raw_patches)
    log.log_chunk_merge(before_count=12, patches=merged, merge_decisions=[...])
    log.log_entity_dedup(patches=deduped, decisions=[...])
    log.log_scoring(patches=scored)
    log.log_application(result)
    data = log.to_dict()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ExtractionLog:
    """Accumulates extraction audit data across pipeline stages."""

    def __init__(self, run_id: str, model: str) -> None:
        self.run_id = run_id
        self.model = model
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.context_snapshot: dict[str, Any] = {}
        self.chunk_results: list[dict[str, Any]] = []
        self.post_chunk_merge: dict[str, Any] = {}
        self.post_consolidation: dict[str, Any] = {}
        self.post_entity_dedup: dict[str, Any] = {}
        self.post_scoring: dict[str, Any] = {}
        self.application: dict[str, Any] = {}

    def log_context(self, snapshot: Any) -> None:
        """Store the 4-layer context prompts the LLM sees."""
        self.context_snapshot = {
            "entity_inventory_prompt": getattr(snapshot, "entity_inventory_prompt", ""),
            "memory_prompt": getattr(snapshot, "memory_prompt", ""),
            "gaps_prompt": getattr(snapshot, "gaps_prompt", ""),
            "extraction_briefing_prompt": getattr(snapshot, "extraction_briefing_prompt", ""),
        }
        # Attach pulse snapshot if available
        pulse = getattr(snapshot, "pulse", None)
        if pulse is not None:
            try:
                self.context_snapshot["pulse_snapshot"] = {
                    "stage": pulse.stage.current.value,
                    "stage_progress": pulse.stage.progress,
                    "config_version": pulse.config_version,
                    "health_scores": {
                        et: {"score": h.health_score, "directive": h.directive.value}
                        for et, h in pulse.health.items()
                    },
                    "risk_score": pulse.risks.risk_score,
                    "rules_fired": pulse.rules_fired,
                }
            except Exception:
                pass

    def log_chunk_result(
        self,
        chunk_id: str,
        chunk_index: int,
        section_title: str | None,
        char_count: int,
        raw_patches: list[dict],
    ) -> None:
        """Record raw patches from a single chunk extraction."""
        self.chunk_results.append({
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "section_title": section_title,
            "char_count": char_count,
            "patch_count": len(raw_patches),
            "patches": raw_patches,
        })

    def log_chunk_merge(
        self,
        before_count: int,
        patches: list[Any],
        merge_decisions: list[dict],
    ) -> None:
        """Record cross-chunk merge results."""
        self.post_chunk_merge = {
            "before_count": before_count,
            "after_count": len(patches),
            "merge_decisions": merge_decisions,
            "patches": [p.model_dump() if hasattr(p, "model_dump") else p for p in patches],
        }

    def log_consolidation(
        self,
        before_count: int,
        patches: list[Any],
        consolidation_decisions: list[dict],
    ) -> None:
        """Record cross-chunk semantic consolidation results."""
        self.post_consolidation = {
            "before_count": before_count,
            "after_count": len(patches),
            "merge_groups": consolidation_decisions,
            "patches": [p.model_dump() if hasattr(p, "model_dump") else p for p in patches],
        }

    def log_entity_dedup(
        self,
        patches: list[Any],
        decisions: list[dict],
    ) -> None:
        """Record entity dedup results."""
        self.post_entity_dedup = {
            "patch_count": len(patches),
            "dedup_decisions": decisions,
            "patches": [p.model_dump() if hasattr(p, "model_dump") else p for p in patches],
        }

    def log_scoring(self, patches: list[Any]) -> None:
        """Record scored patches."""
        self.post_scoring = {
            "patch_count": len(patches),
            "patches": [p.model_dump() if hasattr(p, "model_dump") else p for p in patches],
        }

    def log_application(self, result: Any) -> None:
        """Record application results."""
        self.application = result.model_dump() if result and hasattr(result, "model_dump") else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model": self.model,
            "timestamp": self.timestamp,
            "context_snapshot": self.context_snapshot,
            "chunk_results": self.chunk_results,
            "post_chunk_merge": self.post_chunk_merge,
            "post_consolidation": self.post_consolidation,
            "post_entity_dedup": self.post_entity_dedup,
            "post_scoring": self.post_scoring,
            "application": self.application,
        }
