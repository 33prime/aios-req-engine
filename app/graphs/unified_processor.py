"""Signal Pipeline v2 — EntityPatch-based extraction with 3-layer context.

Single unified pipeline for all signal processing:
  load_signal → triage → load_context → extract_patches →
  score_patches → apply_patches → generate_summary → trigger_memory

All signals produce EntityPatch[] that get scored against memory beliefs,
then surgically applied to BRD entities with confidence-based auto-apply.

Usage:
    from app.graphs.unified_processor import process_signal_v2

    result = await process_signal_v2(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.schemas_entity_patch import EntityPatchList, PatchApplicationResult
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# =============================================================================
# State & Result Models
# =============================================================================


@dataclass
class V2ProcessorState:
    """State for the v2 unified processor pipeline.

    Flows through 8 sequential steps. Each step reads state and returns
    a dict of field updates applied via _apply_state_updates().
    """

    # Input (required)
    signal_id: UUID
    project_id: UUID
    run_id: UUID

    # Signal data (set by v2_load_signal)
    signal: dict[str, Any] | None = None
    signal_text: str = ""
    signal_type: str = "default"
    source_authority: str = "research"

    # Triage (set by v2_triage_signal)
    triage_result: Any | None = None  # TriageResult — Any to avoid circular import

    # Context (set by v2_load_context)
    context_snapshot: Any | None = None  # ContextSnapshot — Any to avoid circular import

    # Extraction (set by v2_extract_patches)
    entity_patches: EntityPatchList | None = None

    # Application (set by v2_apply_patches)
    application_result: PatchApplicationResult | None = None

    # Summary (set by v2_generate_summary)
    chat_summary: str = ""

    # Extraction logging
    extraction_log: Any | None = None  # ExtractionLog instance

    # Signal chunks (loaded once, reused by extraction + memory steps)
    chunks: list[dict[str, Any]] = field(default_factory=list)

    # Status
    success: bool = True
    error: str | None = None


class V2ProcessingResult(BaseModel):
    """Result of v2 signal processing."""

    signal_id: str
    project_id: str
    patches_extracted: int = 0
    patches_applied: int = 0
    patches_escalated: int = 0
    created_count: int = 0
    merged_count: int = 0
    updated_count: int = 0
    staled_count: int = 0
    deleted_count: int = 0
    chat_summary: str = ""
    success: bool = True
    error: str | None = None


# =============================================================================
# DB Status Helpers (non-critical — failures are logged, never fatal)
# =============================================================================


def _update_signal_status(
    signal_id: UUID, status: str, extra: dict[str, Any] | None = None
) -> None:
    """Update signal processing_status in DB. Logs on failure, never raises."""
    try:
        sb = get_supabase()
        updates: dict[str, Any] = {"processing_status": status}
        if extra:
            updates.update(extra)
        sb.table("signals").update(updates).eq("id", str(signal_id)).execute()
    except Exception as e:
        logger.debug(f"Failed to update signal {signal_id} status to {status!r}: {e}")


async def _maybe_trigger_outcome_generation(state: V2ProcessorState) -> None:
    """Trigger outcome generation if change-detection conditions are met.

    Runs on signals 1-3 (bootstrap), or when new entity types appear,
    3+ entities created, or business_driver changed. Fire-and-forget.
    """
    if not state.application_result or state.application_result.total_applied == 0:
        return

    try:
        from app.chains.generate_outcomes import (
            generate_outcomes,
            persist_generated_outcomes,
            should_trigger_outcome_generation,
        )
        from app.db.outcomes import list_outcomes

        # Count signals for this project
        sb = get_supabase()
        sig_resp = sb.table("signals").select("id", count="exact").eq(
            "project_id", str(state.project_id)
        ).execute()
        signal_count = sig_resp.count or 0

        # Detect new entity types
        existing_types = set(state.context_snapshot.entity_inventory.keys()) if state.context_snapshot else set()
        created_types = {
            e.get("entity_type") for e in state.application_result.applied
            if e.get("operation") == "create"
        }
        new_types = created_types - existing_types if existing_types else set()

        # Detect business_driver changes
        has_driver = any(
            e.get("entity_type") == "business_driver"
            for e in state.application_result.applied
        )

        if not should_trigger_outcome_generation(
            project_id=state.project_id,
            signal_count=signal_count,
            new_entity_types=new_types or None,
            created_count=state.application_result.created_count,
            has_driver_change=has_driver,
        ):
            return

        # Load entity graph
        entity_graph: dict[str, list[dict]] = {}
        for etype, table in [
            ("personas", "personas"),
            ("business_drivers", "business_drivers"),
            ("features", "features"),
            ("workflows", "workflows"),
            ("constraints", "constraints"),
        ]:
            try:
                resp = sb.table(table).select("*").eq("project_id", str(state.project_id)).execute()
                entity_graph[etype] = resp.data or []
            except Exception:
                entity_graph[etype] = []

        total_entities = sum(len(v) for v in entity_graph.values())
        if total_entities < 3:
            return  # Not enough data yet

        existing_outcomes = list_outcomes(state.project_id)

        result = await generate_outcomes(
            project_id=state.project_id,
            entity_graph=entity_graph,
            existing_outcomes=existing_outcomes,
        )

        created = await persist_generated_outcomes(
            project_id=state.project_id,
            generation_result=result,
            entity_graph=entity_graph,
        )

        if created:
            # Score each outcome (fire-and-forget)
            from app.chains.score_outcomes import score_and_persist_outcome
            for outcome in created:
                try:
                    await score_and_persist_outcome(outcome_id=str(outcome["id"]))
                except Exception:
                    pass

            logger.info(
                f"[v2] Outcome generation triggered: {len(created)} outcomes created",
                extra={"signal_id": str(state.signal_id)},
            )

    except ImportError:
        pass  # Outcome system not yet available
    except Exception as e:
        logger.debug(f"[v2] Outcome generation trigger failed: {e}")


def _create_signal_review_task(state: V2ProcessorState) -> None:
    """Create a signal_review task for any signal that produced entity changes.

    Works for documents, meeting transcripts, chat signals, etc.
    Non-critical — failures are logged, never fatal.
    """
    try:
        from datetime import datetime, timedelta

        r = state.application_result
        if not r or r.total_applied == 0:
            return

        sb = get_supabase()
        entity_count = r.total_applied

        # Derive title from signal source
        source_label = "signal"
        uploaded_by = None

        if state.signal:
            source_label = (
                state.signal.get("source_label")
                or state.signal.get("source")
                or "signal"
            )

        # Check if document upload (for filename + uploader)
        try:
            doc_resp = (
                sb.table("document_uploads")
                .select("original_filename, uploaded_by")
                .eq("signal_id", str(state.signal_id))
                .limit(1)
                .execute()
            )
            if doc_resp.data:
                source_label = doc_resp.data[0].get("original_filename", source_label)
                uploaded_by = doc_resp.data[0].get("uploaded_by")
        except Exception:
            pass

        # Build patches snapshot from application result
        patches_snapshot = None
        if r.applied:
            patches_snapshot = {
                "total": entity_count,
                "created": r.created_count,
                "merged": r.merged_count,
                "updated": r.updated_count,
                "applied": r.applied[:50],  # Cap to avoid oversized JSONB
            }

        # Build description with entity breakdown
        created_types: dict[str, int] = {}
        updated_types: dict[str, int] = {}
        for a in r.applied:
            etype = a.get("entity_type", "entity")
            if a.get("operation") == "create":
                created_types[etype] = created_types.get(etype, 0) + 1
            else:
                updated_types[etype] = updated_types.get(etype, 0) + 1

        desc_parts = [f"Review and confirm entities extracted from {source_label}."]
        if created_types:
            breakdown = ", ".join(f"{v} {k}s" for k, v in sorted(created_types.items()))
            desc_parts.append(f"\n\n**Created ({r.created_count}):** {breakdown}")
        if updated_types:
            breakdown = ", ".join(f"{v} {k}s" for k, v in sorted(updated_types.items()))
            desc_parts.append(f"\n**Updated ({r.updated_count + r.merged_count}):** {breakdown}")

        # Resolve assignee: document uploader, or signal creator
        assignee = uploaded_by
        if not assignee and state.signal:
            assignee = state.signal.get("metadata", {}).get("created_by") if state.signal.get("metadata") else None
            if not assignee:
                assignee = state.signal.get("created_by")

        # Due date: next business day
        due = datetime.now(UTC) + timedelta(days=1)

        task_data: dict[str, Any] = {
            "project_id": str(state.project_id),
            "title": f"Review {entity_count} entities from {source_label}",
            "description": "".join(desc_parts),
            "task_type": "signal_review",
            "status": "pending",
            "source_type": "signal_processing",
            "priority": "high",
            "priority_score": 90,
            "due_date": due.isoformat(),
            "signal_id": str(state.signal_id),
            "patches_snapshot": patches_snapshot,
        }

        if assignee:
            task_data["assigned_to"] = str(assignee)

        sb.table("tasks").insert(task_data).execute()

        logger.info(
            f"[v2] Created review task for {source_label} ({entity_count} entities)",
            extra={"signal_id": str(state.signal_id)},
        )
    except Exception as e:
        logger.debug(f"[v2] Failed to create signal review task: {e}")

    # Check if we should suggest unlock generation
    _maybe_suggest_unlocks(state)


def _maybe_suggest_unlocks(state: V2ProcessorState) -> None:
    """Create a task suggesting unlock generation when 2+ signals exist and 0 unlocks.

    The idea: project creation note alone isn't enough context for meaningful unlocks.
    Once a second signal arrives (meeting transcript, doc upload, chat signal, etc.),
    the system has enough data to discover strategic capabilities.
    Non-critical — failures are logged, never fatal.
    """
    try:
        sb = get_supabase()
        pid = str(state.project_id)

        # Count signals for this project
        signal_count_resp = (
            sb.table("signals")
            .select("id", count="exact")
            .eq("project_id", pid)
            .execute()
        )
        signal_count = signal_count_resp.count or 0
        if signal_count < 2:
            return

        # Check if unlocks already exist
        unlock_resp = (
            sb.table("unlocks")
            .select("id", count="exact")
            .eq("project_id", pid)
            .execute()
        )
        if (unlock_resp.count or 0) > 0:
            return

        # Check if we already created this suggestion task
        existing_resp = (
            sb.table("tasks")
            .select("id")
            .eq("project_id", pid)
            .eq("task_type", "custom")
            .ilike("title", "%Generate strategic unlocks%")
            .limit(1)
            .execute()
        )
        if existing_resp.data:
            return

        # Create the suggestion task
        sb.table("tasks").insert({
            "project_id": pid,
            "title": "Generate strategic unlocks",
            "description": (
                "This project now has multiple signals processed. "
                "Generate unlocks to discover hidden capabilities — "
                "strategic features that become possible from the "
                "workflows, data, and pain points already captured.\n\n"
                "Open the Unlocks panel (bottom dock) and click Generate."
            ),
            "task_type": "custom",
            "status": "pending",
            "source_type": "system_generated",
            "priority": "medium",
            "priority_score": 55,
            "action_verb": "generate",
        }).execute()

        logger.info(
            f"[v2] Created unlock suggestion task for project {pid} "
            f"({signal_count} signals, 0 unlocks)",
        )
    except Exception as e:
        logger.debug(f"[v2] Failed to check/create unlock suggestion: {e}")


# =============================================================================
# Pipeline Node Functions
# =============================================================================


def v2_load_signal(state: V2ProcessorState) -> dict[str, Any]:
    """Step 1: Load signal data from database."""
    logger.info(
        f"[v2] Loading signal {state.signal_id}",
        extra={"run_id": str(state.run_id), "signal_id": str(state.signal_id)},
    )

    sb = get_supabase()
    response = sb.table("signals").select("*").eq("id", str(state.signal_id)).single().execute()

    if not response.data:
        return {"error": f"Signal {state.signal_id} not found", "success": False}

    signal = response.data
    metadata = signal.get("metadata", {}) or {}

    _update_signal_status(state.signal_id, "extracting")

    return {
        "signal": signal,
        "signal_text": signal.get("raw_text", ""),
        "signal_type": metadata.get("source_type", signal.get("signal_type", "default")),
        "source_authority": metadata.get("authority", "research"),
    }


def v2_triage_signal(state: V2ProcessorState) -> dict[str, Any]:
    """Step 2: Triage signal for source type, strategy, authority, priority."""
    if not state.signal_text:
        return {}

    logger.info(
        f"[v2] Triaging signal {state.signal_id}",
        extra={"run_id": str(state.run_id), "signal_id": str(state.signal_id)},
    )

    try:
        from app.chains.triage_signal import triage_signal

        metadata = (state.signal.get("metadata", {}) or {}) if state.signal else {}
        result = triage_signal(
            signal_type=state.signal_type,
            raw_text=state.signal_text,
            metadata=metadata,
        )

        updates: dict[str, Any] = {
            "triage_result": result,
            "signal_type": result.strategy,
            "source_authority": result.source_authority,
        }

        # Store triage metadata on signal (non-critical)
        _update_signal_status(
            state.signal_id, "extracting", extra={"triage_metadata": result.model_dump()}
        )

        return updates

    except Exception as e:
        logger.warning(
            f"[v2] Triage failed (using defaults): {e}",
            extra={"signal_id": str(state.signal_id)},
        )
        return {}


async def v2_load_context(state: V2ProcessorState) -> dict[str, Any]:
    """Step 3: Build 3-layer context snapshot for extraction."""
    logger.info(
        f"[v2] Building context snapshot for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    try:
        from app.core.context_snapshot import build_context_snapshot

        snapshot = await build_context_snapshot(state.project_id)
        return {"context_snapshot": snapshot}
    except Exception as e:
        logger.warning(
            f"[v2] Context snapshot build failed: {e}",
            extra={"project_id": str(state.project_id)},
        )
        from app.core.context_snapshot import ContextSnapshot

        return {"context_snapshot": ContextSnapshot()}


async def v2_extract_patches(state: V2ProcessorState) -> dict[str, Any]:
    """Step 4: Extract EntityPatch[] from signal.

    Uses parallel per-chunk Haiku extraction when signal_chunks >= 2 (documents).
    Falls back to single Sonnet call for chunk-less signals (notes, chat, email).
    """
    if not state.signal_text:
        logger.warning("[v2] No signal text to extract from")
        return {"entity_patches": None}

    logger.info(
        f"[v2] Extracting patches from signal {state.signal_id}",
        extra={"run_id": str(state.run_id), "signal_id": str(state.signal_id)},
    )

    try:
        # Load chunks for this signal (stored on state for reuse in v2_trigger_memory)
        chunks: list[dict] = []
        try:
            from app.db.signals import list_signal_chunks

            chunks = list_signal_chunks(state.signal_id)
            state.chunks = chunks
        except Exception as e:
            logger.debug(f"[v2] Could not load signal chunks: {e}")

        if len(chunks) >= 2:
            # Parallel chunk extraction (fast path — Haiku map-reduce)
            from app.chains.extract_entity_patches import extract_patches_parallel

            logger.info(
                f"[v2] Using parallel extraction ({len(chunks)} chunks)",
                extra={"signal_id": str(state.signal_id)},
            )
            patch_list = await extract_patches_parallel(
                chunks=chunks,
                signal_type=state.signal_type,
                context_snapshot=state.context_snapshot,
                source_authority=state.source_authority,
                signal_id=str(state.signal_id),
                run_id=str(state.run_id),
                extraction_log=state.extraction_log,
            )
        else:
            # Single-call fallback for chunk-less signals
            from app.chains.extract_entity_patches import extract_entity_patches

            chunk_ids = [str(c.get("id", "")) for c in chunks]
            patch_list = await extract_entity_patches(
                signal_text=state.signal_text,
                signal_type=state.signal_type,
                context_snapshot=state.context_snapshot,
                chunk_ids=chunk_ids,
                source_authority=state.source_authority,
                signal_id=str(state.signal_id),
                run_id=str(state.run_id),
                extraction_log=state.extraction_log,
            )

        # Update extraction log with model info
        if state.extraction_log and patch_list.extraction_model:
            state.extraction_log.model = patch_list.extraction_model

        logger.info(
            f"[v2] Extracted {len(patch_list.patches)} patches",
            extra={"signal_id": str(state.signal_id)},
        )
        return {"entity_patches": patch_list}

    except Exception as e:
        logger.error(
            f"[v2] Extraction failed: {e}",
            exc_info=True,
            extra={"signal_id": str(state.signal_id)},
        )
        return {"entity_patches": None, "error": f"Extraction failed: {e}"}


async def v2_enrich_patches(state: V2ProcessorState) -> dict[str, Any]:
    """Step 4a: Enrich patches with hypothetical questions, term expansion, canonical format.

    Non-critical — pipeline continues with raw patches if enrichment fails entirely.
    """
    if not state.entity_patches or not state.entity_patches.patches:
        return {}

    try:
        from app.chains.enrich_entity_patches import enrich_entity_patches

        context = state.context_snapshot
        inventory_prompt = context.entity_inventory_prompt if context else ""

        enriched = await enrich_entity_patches(
            patches=state.entity_patches.patches,
            entity_inventory_prompt=inventory_prompt,
            project_id=state.project_id,
            signal_id=state.signal_id,
        )

        return {
            "entity_patches": EntityPatchList(
                patches=enriched,
                signal_id=state.entity_patches.signal_id,
                run_id=state.entity_patches.run_id,
                extraction_model=state.entity_patches.extraction_model,
                extraction_duration_ms=state.entity_patches.extraction_duration_ms,
            )
        }
    except Exception as e:
        logger.warning(
            f"v2_enrich_patches failed, continuing with raw patches: {e}",
            extra={"signal_id": str(state.signal_id)},
        )
        return {}


async def v2_dedup_patches(state: V2ProcessorState) -> dict[str, Any]:
    """Step 4b: Deduplicate create patches against existing entities."""
    if not state.entity_patches or not state.entity_patches.patches:
        return {}

    create_count = sum(1 for p in state.entity_patches.patches if p.operation == "create")
    if create_count == 0:
        return {}

    logger.info(
        f"[v2] Deduplicating {create_count} create patches",
        extra={"signal_id": str(state.signal_id)},
    )

    try:
        from app.core.entity_dedup import dedup_create_patches

        inventory = (
            getattr(state.context_snapshot, "entity_inventory", {})
            if state.context_snapshot
            else {}
        )

        # Pass pulse health map for dynamic dedup threshold tuning
        pulse_health = None
        try:
            pulse = getattr(state.context_snapshot, "pulse", None)
            if pulse and hasattr(pulse, "health"):
                pulse_health = pulse.health
            elif isinstance(pulse, dict):
                pulse_health = pulse.get("health")
        except Exception:
            pass

        deduped = await dedup_create_patches(
            state.entity_patches.patches,
            inventory,
            state.project_id,
            extraction_log=state.extraction_log,
            pulse_health_map=pulse_health,
        )
        return {
            "entity_patches": EntityPatchList(
                patches=deduped,
                signal_id=state.entity_patches.signal_id,
                run_id=state.entity_patches.run_id,
                extraction_model=state.entity_patches.extraction_model,
                extraction_duration_ms=state.entity_patches.extraction_duration_ms,
            )
        }
    except Exception as e:
        logger.warning(
            f"[v2] Dedup failed (continuing with original patches): {e}",
            extra={"signal_id": str(state.signal_id)},
        )
        return {}


async def v2_score_patches(state: V2ProcessorState) -> dict[str, Any]:
    """Step 5: Score patches against memory beliefs and open questions."""
    if not state.entity_patches or not state.entity_patches.patches:
        return {}

    logger.info(
        f"[v2] Scoring {len(state.entity_patches.patches)} patches against memory",
        extra={"signal_id": str(state.signal_id)},
    )

    try:
        from app.chains.score_entity_patches import score_entity_patches

        scored = await score_entity_patches(
            patches=state.entity_patches.patches,
            context_snapshot=state.context_snapshot,
        )
        # Replace patches with scored versions
        return {
            "entity_patches": EntityPatchList(
                patches=scored,
                signal_id=state.entity_patches.signal_id,
                run_id=state.entity_patches.run_id,
                extraction_model=state.entity_patches.extraction_model,
                extraction_duration_ms=state.entity_patches.extraction_duration_ms,
            )
        }

    except Exception as e:
        logger.warning(
            f"[v2] Patch scoring failed (continuing with unscored): {e}",
            extra={"signal_id": str(state.signal_id)},
        )
        return {}


async def v2_apply_patches(state: V2ProcessorState) -> dict[str, Any]:
    """Step 6: Apply extracted patches to the database."""
    if not state.entity_patches or not state.entity_patches.patches:
        return {"application_result": None}

    logger.info(
        f"[v2] Applying {len(state.entity_patches.patches)} patches",
        extra={"signal_id": str(state.signal_id)},
    )

    _update_signal_status(state.signal_id, "applying")

    try:
        from app.db.patch_applicator import apply_entity_patches

        result = await apply_entity_patches(
            project_id=state.project_id,
            patches=state.entity_patches.patches,
            run_id=state.run_id,
            signal_id=state.signal_id,
        )

        logger.info(
            f"[v2] Applied {result.total_applied} patches, escalated {result.total_escalated}",
            extra={"signal_id": str(state.signal_id)},
        )

        # Record pulse snapshot after successful patch application (debounced)
        try:
            import asyncio

            from app.core.pulse_observer import record_pulse_snapshot_debounced

            asyncio.create_task(
                record_pulse_snapshot_debounced(state.project_id, trigger="signal_processed")
            )
        except Exception as e:
            logger.debug(f"Pulse observer failed (non-fatal): {e}")

        return {"application_result": result}

    except Exception as e:
        logger.error(
            f"[v2] Patch application failed: {e}",
            exc_info=True,
            extra={"signal_id": str(state.signal_id)},
        )
        return {"application_result": None, "error": f"Patch application failed: {e}"}


async def v2_generate_summary(state: V2ProcessorState) -> dict[str, Any]:
    """Step 7: Generate chat summary of processing results."""
    if not state.application_result:
        return {"chat_summary": "No changes from this signal."}

    try:
        from app.chains.generate_chat_summary import generate_chat_summary

        patches = state.entity_patches.patches if state.entity_patches else []
        signal_name = state.signal.get("title", "signal") if state.signal else "signal"

        summary = await generate_chat_summary(
            result=state.application_result,
            patches=patches,
            signal_name=signal_name,
        )
        return {"chat_summary": summary}

    except Exception as e:
        logger.warning(
            f"[v2] Summary generation failed: {e}",
            extra={"signal_id": str(state.signal_id)},
        )
        return {"chat_summary": "Signal processed. Check the BRD for updates."}


def _build_entity_counts(result: PatchApplicationResult | None) -> dict:
    """Extract entity counts from PatchApplicationResult for memory agent."""
    if not result:
        return {}
    return {
        "created": result.created_count,
        "merged": result.merged_count,
        "updated": result.updated_count,
        "staled": result.staled_count,
        "deleted": result.deleted_count,
        "total_applied": result.total_applied,
    }


async def v2_trigger_memory(state: V2ProcessorState) -> dict[str, Any]:
    """Step 8: Fire MemoryWatcher + Stakeholder Intelligence for signal processing event."""
    # Reuse chunks loaded in v2_extract_patches (avoids duplicate DB query)
    chunks: list[dict] = state.chunks

    # Speaker resolution (non-critical)
    try:
        from app.core.speaker_resolver import resolve_speakers_for_signal

        if chunks:
            resolve_speakers_for_signal(state.project_id, state.signal_id, chunks)
    except Exception as e:
        logger.debug(f"[v2] Speaker resolution failed: {e}")

    try:
        from app.agents.memory_agent import process_signal_for_memory

        if state.signal and state.signal_text:
            entity_counts = _build_entity_counts(state.application_result)
            signal_type = state.signal.get("signal_type", "signal") if state.signal else "signal"
            await process_signal_for_memory(
                project_id=state.project_id,
                signal_id=state.signal_id,
                signal_type=signal_type,
                raw_text=state.signal_text,
                entities_extracted=entity_counts,
                chunks=chunks if chunks else None,
            )
    except ImportError:
        logger.debug("[v2] Memory processing not available")
    except Exception as e:
        logger.warning(
            f"[v2] Memory trigger failed: {e}",
            extra={"signal_id": str(state.signal_id)},
        )

    # Trigger Stakeholder Intelligence for affected stakeholders (fire-and-forget)
    await _trigger_stakeholder_intelligence(state)

    # Regenerate narrative fields if signal affected relevant entities (fire-and-forget)
    await _trigger_narrative_regeneration(state)

    # Mark signal processing complete
    patch_summary: dict[str, Any] = {}
    if state.application_result:
        r = state.application_result
        patch_summary = {
            "applied": r.total_applied,
            "escalated": r.total_escalated,
            "created": r.created_count,
            "merged": r.merged_count,
            "updated": r.updated_count,
            "chat_summary": state.chat_summary or "",
        }

    extra: dict[str, Any] = {"patch_summary": patch_summary}
    if state.extraction_log:
        extra["extraction_log"] = state.extraction_log.to_dict()

    _update_signal_status(
        state.signal_id,
        "complete",
        extra=extra,
    )

    # Create review task for any signal that produced entity changes
    _create_signal_review_task(state)

    # Trigger outcome generation if change-detection conditions met (fire-and-forget)
    await _maybe_trigger_outcome_generation(state)

    return {"success": True}


async def _trigger_stakeholder_intelligence(state: V2ProcessorState) -> None:
    """Trigger SI agent for stakeholders affected by this signal's patches.

    Fires for stakeholders that were created, merged, or updated. Non-critical —
    failures are logged, never fatal.
    """
    if not state.application_result or not state.application_result.applied:
        return

    # Find stakeholder entity IDs from applied patches
    stakeholder_ids = [
        entry["entity_id"]
        for entry in state.application_result.applied
        if entry.get("entity_type") == "stakeholder"
        and entry.get("entity_id")
        and entry.get("operation") in ("create", "merge", "update")
    ]

    if not stakeholder_ids:
        return

    logger.info(
        f"[v2] Triggering SI agent for {len(stakeholder_ids)} affected stakeholders",
        extra={"signal_id": str(state.signal_id), "stakeholder_ids": stakeholder_ids},
    )

    try:
        from app.chains.stakeholder_enrichment import analyze_stakeholder

        for sid in stakeholder_ids[:3]:  # Cap at 3 per signal
            try:
                await analyze_stakeholder(
                    stakeholder_id=UUID(sid),
                    project_id=state.project_id,
                    trigger="signal_processed",
                    trigger_context=f"Signal {state.signal_id} applied patches",
                )
            except Exception as e:
                logger.debug(f"[v2] SI agent trigger failed for stakeholder {sid}: {e}")

    except ImportError:
        logger.debug("[v2] Stakeholder intelligence agent not available")
    except Exception as e:
        logger.warning(
            f"[v2] SI agent trigger failed: {e}",
            extra={"signal_id": str(state.signal_id)},
        )


async def _trigger_narrative_regeneration(state: V2ProcessorState) -> None:
    """Regenerate vision/background/deal-pulse when signal touches relevant entities.

    Fire-and-forget: failures are logged, never fatal.
    Only auto-regenerates narratives that are still AI-generated.
    """
    if not state.application_result or state.application_result.total_applied == 0:
        return

    # Check if any applied patches touch narrative-relevant entities
    relevant_types = {"business_driver", "feature", "persona", "vp_step", "vision"}
    touched_types = {
        entry.get("entity_type")
        for entry in state.application_result.applied
        if entry.get("entity_type")
    }

    if not touched_types & relevant_types:
        return

    logger.info(
        "[v2] Triggering narrative regeneration (touched: %s)",
        touched_types & relevant_types,
        extra={"signal_id": str(state.signal_id)},
    )

    import asyncio

    try:
        from app.chains.synthesize_intelligence import invalidate_intelligence_cache
        from app.context.project_awareness import invalidate_awareness

        # Invalidate caches so next page load triggers fresh intelligence
        pid = str(state.project_id)
        invalidate_intelligence_cache(pid)
        invalidate_awareness(state.project_id)
        try:
            from app.api.workspace_intelligence import _pulse_cache

            _pulse_cache.pop(pid, None)
        except Exception:
            pass
    except Exception as e:
        logger.debug("[v2] Intelligence cache invalidation failed: %s", e)

    try:
        # Auto-rewrite background if it hasn't been manually edited
        # Only when pain points or goals are touched
        driver_touched = "business_driver" in touched_types
        if driver_touched:
            from app.db.supabase_client import get_supabase

            client = get_supabase()
            company_info = (
                client.table("company_info")
                .select("description, updated_by")
                .eq("project_id", str(state.project_id))
                .maybe_single()
                .execute()
            )

            # Only auto-rewrite if background was AI-generated (not manually edited)
            if company_info and company_info.data:
                updated_by = company_info.data.get("updated_by")
                if updated_by != "consultant":
                    asyncio.get_event_loop().create_task(
                        asyncio.to_thread(
                            _auto_rewrite_and_save_background,
                            str(state.project_id),
                        )
                    )
    except Exception as e:
        logger.debug("[v2] Narrative regeneration trigger failed: %s", e)


def _auto_rewrite_and_save_background(project_id: str) -> None:
    """Auto-rewrite background using evidence and save it."""
    try:
        from app.chains.enhance_narrative import enhance_narrative
        from app.db.supabase_client import get_supabase

        suggestion = enhance_narrative(
            project_id=project_id,
            field="background",
            mode="rewrite",
        )
        if suggestion:
            client = get_supabase()
            existing = (
                client.table("company_info")
                .select("id")
                .eq("project_id", project_id)
                .maybe_single()
                .execute()
            )

            if existing and existing.data:
                client.table("company_info").update(
                    {
                        "description": suggestion,
                    }
                ).eq("project_id", project_id).execute()
            else:
                client.table("company_info").insert(
                    {
                        "project_id": project_id,
                        "description": suggestion,
                    }
                ).execute()

            logger.info("Auto-rewrote background for project %s", project_id[:8])
    except Exception:
        logger.debug("Auto-rewrite background failed for project %s", project_id[:8])


# =============================================================================
# Pipeline Orchestrator
# =============================================================================


async def process_signal_v2(
    signal_id: UUID,
    project_id: UUID,
    run_id: UUID,
) -> V2ProcessingResult:
    """Process a signal through the v2 EntityPatch pipeline.

    Pipeline: load_signal → triage → load_context → extract_patches →
              score_patches → apply_patches → generate_summary → trigger_memory

    Each step checks for errors from previous steps and short-circuits
    to failure when critical steps (load, extract, apply) fail.

    Args:
        signal_id: Signal UUID
        project_id: Project UUID
        run_id: Run tracking UUID

    Returns:
        V2ProcessingResult with full pipeline results
    """
    logger.info(
        f"[v2] Starting signal processing for {signal_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    state = V2ProcessorState(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
    )

    # Create extraction log for audit trail
    from app.core.extraction_logger import ExtractionLog

    state.extraction_log = ExtractionLog(run_id=str(run_id), model="")

    try:
        # Step 1: Load signal (CRITICAL — abort on failure)
        updates = v2_load_signal(state)
        _apply_state_updates(state, updates)
        if not state.success or state.error:
            _update_signal_status(signal_id, "failed")
            return _make_v2_result(state)

        # Step 2: Triage signal (non-critical — defaults work)
        updates = v2_triage_signal(state)
        _apply_state_updates(state, updates)

        # Step 3: Load context (non-critical — empty context is valid)
        updates = await v2_load_context(state)
        _apply_state_updates(state, updates)

        # Log context snapshot for extraction audit
        if state.context_snapshot and state.extraction_log:
            state.extraction_log.log_context(state.context_snapshot)

        # Step 4: Extract patches (CRITICAL — abort on failure)
        updates = await v2_extract_patches(state)
        _apply_state_updates(state, updates)
        if state.error:
            _update_signal_status(signal_id, "failed")
            return _make_v2_result(state)

        # Step 4a: Enrich patches (non-critical — raw patches still work for dedup)
        updates = await v2_enrich_patches(state)
        _apply_state_updates(state, updates)

        # Step 4b: Dedup create patches (non-critical — original patches still work)
        updates = await v2_dedup_patches(state)
        _apply_state_updates(state, updates)

        # Step 5: Score patches (non-critical — unscored patches still apply)
        updates = await v2_score_patches(state)
        _apply_state_updates(state, updates)

        # Log scored patches for extraction audit
        if state.entity_patches and state.extraction_log:
            state.extraction_log.log_scoring(state.entity_patches.patches)

        # Step 6: Apply patches (CRITICAL — abort on failure)
        updates = await v2_apply_patches(state)
        _apply_state_updates(state, updates)
        if state.error:
            _update_signal_status(signal_id, "failed")
            return _make_v2_result(state)

        # Log application results for extraction audit
        if state.extraction_log:
            state.extraction_log.log_application(state.application_result)

        # Step 7: Generate summary (non-critical — fallback message used)
        updates = await v2_generate_summary(state)
        _apply_state_updates(state, updates)

        # Step 8: Trigger memory + mark complete (non-critical)
        updates = await v2_trigger_memory(state)
        _apply_state_updates(state, updates)

        # Step 9: Auto-resolve open questions from signal content (non-critical, fire-and-forget)
        try:
            if (
                state.signal_text
                and state.application_result
                and state.application_result.total_applied > 0
            ):
                from app.core.question_auto_resolver import auto_resolve_from_signal

                await auto_resolve_from_signal(
                    project_id=project_id,
                    signal_content=state.signal_text,
                    signal_id=signal_id,
                    signal_source="v2_pipeline",
                )
        except Exception as qar_err:
            logger.debug(f"[v2] Question auto-resolution failed (non-fatal): {qar_err}")

        # Step 9b: Extract action items from meeting transcripts (non-critical)
        if state.triage_result and getattr(state.triage_result, "strategy", "") in (
            "meeting_transcript",
            "meeting_notes",
        ):
            try:
                from app.chains.extract_action_items import extract_action_items
                from app.core.task_integrations import create_action_item_tasks

                items = await extract_action_items(state.signal_text, state.signal_type)
                if items:
                    await create_action_item_tasks(project_id, signal_id, items)
                    logger.info(
                        f"[v2] Created {len(items)} action item tasks from transcript",
                        extra={"signal_id": str(signal_id)},
                    )
            except Exception as ai_err:
                logger.debug(f"[v2] Action item extraction failed (non-fatal): {ai_err}")

        result = _make_v2_result(state)

        logger.info(
            f"[v2] Processing complete: {result.patches_extracted} extracted, "
            f"{result.patches_applied} applied, {result.patches_escalated} escalated",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )

        return result

    except Exception as e:
        logger.exception(
            f"[v2] Processing failed: {e}",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )

        _update_signal_status(signal_id, "failed")

        return V2ProcessingResult(
            signal_id=str(signal_id),
            project_id=str(project_id),
            success=False,
            error=str(e),
        )


# =============================================================================
# State Helpers
# =============================================================================


def _apply_state_updates(state: V2ProcessorState, updates: dict[str, Any]) -> None:
    """Apply dict updates to dataclass state."""
    for key, value in updates.items():
        if hasattr(state, key):
            setattr(state, key, value)


def _make_v2_result(state: V2ProcessorState) -> V2ProcessingResult:
    """Build V2ProcessingResult from final state."""
    patches_extracted = 0
    if state.entity_patches:
        patches_extracted = len(state.entity_patches.patches)

    r = state.application_result
    return V2ProcessingResult(
        signal_id=str(state.signal_id),
        project_id=str(state.project_id),
        patches_extracted=patches_extracted,
        patches_applied=r.total_applied if r else 0,
        patches_escalated=r.total_escalated if r else 0,
        created_count=r.created_count if r else 0,
        merged_count=r.merged_count if r else 0,
        updated_count=r.updated_count if r else 0,
        staled_count=r.staled_count if r else 0,
        deleted_count=r.deleted_count if r else 0,
        chat_summary=state.chat_summary,
        success=state.success if not state.error else False,
        error=state.error,
    )
