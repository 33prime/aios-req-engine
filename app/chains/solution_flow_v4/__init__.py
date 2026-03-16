"""Solution Flow v4 — Multi-phase intelligence pipeline.

Architecture (modeled after prototype builder):
  Phase 0: Intelligence Assembly         (deterministic + retrieval, ~3s, ~$0.02)
  Phase 1: Insight Synthesis             (Sonnet, 1 call, ~5s, ~$0.08)  ← "magic"
  Phase 2: Flow Architecture             (Sonnet, 1 call, cached, ~5s, ~$0.08)
  Phase 3: Step Detail Builders          (Haiku ×N, parallel, ~3s, ~$0.06)
  Phase 4: Coherence QA + Insight Weave  (Sonnet, 1 call, ~4s, ~$0.06)
  Phase 5: Enrichment + Persistence      (deterministic, ~2s, $0)

Total: ~22s, ~$0.30. Graceful degradation: if insights fail, continues without.

Key differences from v3:
- Loads 13+ intelligence sources (v3 loads 7)
- Separate planning from detail generation
- Parallel per-step builders (focused context, not 30K monolith)
- Cross-step coherence validation
- Intelligence-driven insights woven into flow
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def generate_solution_flow_v4(
    project_id: UUID,
    flow_id: UUID,
) -> dict[str, Any]:
    """Generate solution flow using the v4 multi-phase pipeline.

    Returns dict with steps, summary, metadata, insights.
    """
    from app.db.solution_flow import update_flow

    t_start = time.monotonic()

    # ── Phase 0: Intelligence Assembly ──────────────────────────────────────
    from app.chains.solution_flow_v4.intelligence import (
        assemble_intelligence,
        format_brd_for_architecture,
        format_intelligence_for_insights,
    )

    logger.info(f"v4 Phase 0: Assembling intelligence for {project_id}")
    t0 = time.monotonic()
    ctx = await assemble_intelligence(project_id)
    phase0_s = time.monotonic() - t0
    logger.info(f"v4 Phase 0 done in {phase0_s:.1f}s")

    # Snapshot existing steps
    confirmed_steps, needs_review_steps, ai_steps = await asyncio.to_thread(
        _snapshot_existing_steps, flow_id
    )
    all_existing = confirmed_steps + needs_review_steps + ai_steps

    current_version = max((s.get("generation_version", 1) for s in all_existing), default=0)
    new_version = current_version + 1

    logger.info(
        f"Snapshot: {len(confirmed_steps)} confirmed, {len(needs_review_steps)} needs_review, "
        f"{len(ai_steps)} ai_generated. Version {current_version}→{new_version}"
    )

    # ── Phase 1: Insight Synthesis ──────────────────────────────────────────
    from app.chains.solution_flow_v4.insights import synthesize_insights

    logger.info("v4 Phase 1: Synthesizing insights")
    t0 = time.monotonic()

    intelligence_text = format_intelligence_for_insights(ctx)
    brd_text = format_brd_for_architecture(ctx)

    insights = await synthesize_insights(
        intelligence_text=intelligence_text,
        brd_text=brd_text,
        project_id=project_id,
    )
    phase1_s = time.monotonic() - t0
    logger.info(
        f"v4 Phase 1 done in {phase1_s:.1f}s: "
        f"{len(insights.get('hidden_connections', []))} connections, "
        f"{len(insights.get('tension_points', []))} tensions"
    )

    # ── Phase 2: Flow Architecture ──────────────────────────────────────────
    from app.chains.solution_flow_v4.architecture import plan_architecture

    logger.info("v4 Phase 2: Planning architecture")
    t0 = time.monotonic()

    architecture = await plan_architecture(
        brd_text=brd_text,
        insights=insights,
        confirmed_steps=confirmed_steps,
        metadata=ctx.metadata,
        project_id=project_id,
    )
    phase2_s = time.monotonic() - t0

    skeletons = architecture.get("step_skeletons", [])
    flow_thesis = architecture.get("flow_thesis", "")
    logger.info(f"v4 Phase 2 done in {phase2_s:.1f}s: {len(skeletons)} steps planned")

    if not skeletons and not confirmed_steps:
        return {"error": "No steps planned", "steps": []}

    # ── Phase 3: Parallel Step Builders ─────────────────────────────────────
    from app.chains.solution_flow_v4.builders import build_step_details

    logger.info(f"v4 Phase 3: Building {len(skeletons)} step details in parallel")
    t0 = time.monotonic()

    detailed_steps = await build_step_details(
        skeletons=skeletons,
        ctx=ctx,
        insights=insights,
        project_id=project_id,
    )
    phase3_s = time.monotonic() - t0
    logger.info(f"v4 Phase 3 done in {phase3_s:.1f}s: {len(detailed_steps)} steps built")

    # ── Phase 4: Coherence QA ───────────────────────────────────────────────
    from app.chains.solution_flow_v4.coherence import apply_qa_patches, run_coherence_qa

    logger.info("v4 Phase 4: Coherence QA")
    t0 = time.monotonic()

    workflow_names = [w.get("name", "") for w in ctx.future_workflows]
    persona_names = [p.get("name", "") for p in ctx.personas]

    qa_result = await run_coherence_qa(
        steps=detailed_steps,
        flow_thesis=flow_thesis,
        insights=insights,
        workflow_names=workflow_names,
        persona_names=persona_names,
        project_id=project_id,
    )
    phase4_s = time.monotonic() - t0

    quality_score = qa_result.get("quality_score", 0)
    logger.info(
        f"v4 Phase 4 done in {phase4_s:.1f}s: score={quality_score}, "
        f"{len(qa_result.get('patches', []))} patches"
    )

    # Apply QA patches
    detailed_steps = apply_qa_patches(detailed_steps, qa_result)

    # Update summary if QA improved it
    summary_patch = qa_result.get("summary_patch", "")
    if summary_patch:
        flow_thesis = summary_patch

    # ── Phase 5: Persistence ────────────────────────────────────────────────
    logger.info("v4 Phase 5: Persisting steps")
    t0 = time.monotonic()

    # Normalize step data for persistence
    for step in detailed_steps:
        # Ensure goal field (builders may use goal_sentence)
        if "goal" not in step and "goal_sentence" in step:
            step["goal"] = step.pop("goal_sentence")
        # Ensure open_questions have status
        for q in step.get("open_questions", []):
            if isinstance(q, dict):
                q.setdefault("status", "open")

    saved_steps = _persist_steps(
        flow_id=flow_id,
        project_id=project_id,
        new_steps=detailed_steps,
        confirmed_steps=confirmed_steps,
        generation_version=new_version,
    )

    phase5_s = time.monotonic() - t0
    total_s = time.monotonic() - t_start

    # Update flow metadata
    generation_metadata = {
        "version": new_version,
        "pipeline": "v4",
        "steps_generated": len(detailed_steps),
        "steps_preserved": len(confirmed_steps),
        "quality_score": quality_score,
        "intelligence_sources": ctx.metadata.get("intelligence_sources", 0),
        "insights": {
            "hidden_connections": len(insights.get("hidden_connections", [])),
            "tension_points": len(insights.get("tension_points", [])),
            "missing_capabilities": len(insights.get("missing_capabilities", [])),
        },
        "timing": {
            "phase0_intelligence_s": round(phase0_s, 1),
            "phase1_insights_s": round(phase1_s, 1),
            "phase2_architecture_s": round(phase2_s, 1),
            "phase3_builders_s": round(phase3_s, 1),
            "phase4_qa_s": round(phase4_s, 1),
            "phase5_persistence_s": round(phase5_s, 1),
            "total_s": round(total_s, 1),
        },
        "data_flow_notes": architecture.get("data_thread", ""),
        "model": "claude-sonnet-4-6 + claude-haiku-4-5",
    }

    try:
        update_flow(
            flow_id,
            {
                "summary": flow_thesis,
                "generation_metadata": json.dumps(generation_metadata),
            },
        )
        from app.db.supabase_client import get_supabase

        get_supabase().table("solution_flows").update(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ).eq("id", str(flow_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to update flow metadata: {e}")

    # Build background narratives (fire-and-forget)
    try:
        import threading

        threading.Thread(
            target=_build_narratives_for_steps,
            args=(saved_steps, project_id),
            daemon=True,
        ).start()
    except Exception:
        pass

    # Crystallize horizons (fire-and-forget)
    try:
        from app.core.horizon_crystallization import crystallize_horizons

        threading.Thread(
            target=lambda: asyncio.run(crystallize_horizons(project_id)),
            daemon=True,
        ).start()
    except Exception:
        pass

    logger.info(
        f"v4 COMPLETE: {len(saved_steps)} steps, quality={quality_score}, "
        f"{total_s:.1f}s total, {ctx.metadata.get('intelligence_sources', 0)}/9 intel sources"
    )

    return {
        "steps": saved_steps,
        "summary": flow_thesis,
        "metadata": generation_metadata,
        "insights": {
            "hidden_connections": insights.get("hidden_connections", []),
            "tension_points": insights.get("tension_points", []),
            "missing_capabilities": insights.get("missing_capabilities", []),
            "narrative_themes": insights.get("narrative_themes", []),
            "persona_blind_spots": insights.get("persona_blind_spots", []),
            "value_unlock_chain": insights.get("value_unlock_chain", ""),
        },
    }


# =============================================================================
# Snapshot + Persistence — reused from v3 with minor adaptations
# =============================================================================


def _snapshot_existing_steps(
    flow_id: UUID,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Snapshot existing steps into confirmed, needs_review, and ai_generated buckets."""
    from app.db.solution_flow import list_flow_steps

    steps = list_flow_steps(flow_id)

    confirmed = []
    needs_review = []
    ai_generated = []

    for step in steps:
        status = step.get("confirmation_status", "ai_generated")
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed.append(step)
        elif status == "needs_review":
            needs_review.append(step)
        else:
            ai_generated.append(step)

    return confirmed, needs_review, ai_generated


def _collect_resolved_qa(steps: list[dict]) -> str:
    """Collect resolved Q&A from existing steps as project knowledge."""
    qa_pairs: list[str] = []
    for step in steps:
        for q in step.get("open_questions") or []:
            if isinstance(q, dict) and q.get("status") == "resolved":
                question = q.get("question", "")
                answer = q.get("resolved_answer", "")
                if question and answer:
                    qa_pairs.append(f"Q: {question}\nA: {answer}")
    return "\n\n".join(qa_pairs[:20]) if qa_pairs else ""


def _persist_steps(
    flow_id: UUID,
    project_id: UUID,
    new_steps: list[dict],
    confirmed_steps: list[dict],
    generation_version: int,
) -> list[dict]:
    """Persist generated steps alongside confirmed steps. Non-destructive."""
    from app.db.entity_embeddings import embed_entity
    from app.db.solution_flow import create_flow_step, update_flow_step
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    # Delete only ai_generated + needs_review steps
    supabase.table("solution_flow_steps").delete().eq("flow_id", str(flow_id)).in_(
        "confirmation_status", ["ai_generated", "needs_review"]
    ).execute()

    # Mark confirmed steps as preserved
    for step in confirmed_steps:
        try:
            update_flow_step(
                UUID(step["id"]),
                {
                    "preserved_from_version": generation_version - 1,
                    "generation_version": generation_version,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to mark preserved step {step['id']}: {e}")

    # UUID regex for sanitizing linked IDs (LLM sometimes generates names)
    import re
    _UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    # Build combined list
    all_entries: list[tuple[int, dict, bool]] = []

    for step in confirmed_steps:
        all_entries.append((step.get("step_index", 0), step, False))

    max_confirmed_idx = max((s.get("step_index", 0) for s in confirmed_steps), default=-1)
    for i, step in enumerate(new_steps):
        all_entries.append((max_confirmed_idx + 1 + i, step, True))

    all_entries.sort(key=lambda x: x[0])

    # Reindex and persist
    saved_steps: list[dict] = []
    for i, (_, step, is_new) in enumerate(all_entries):
        if is_new:
            step["step_index"] = i
            step["generation_version"] = generation_version

            # Clean architecture-only fields before persistence
            step.pop("goal_sentence", None)
            step.pop("data_inputs", None)
            step.pop("data_outputs", None)
            step.pop("complexity", None)
            step.pop("tension_notes", None)
            step.pop("insight_notes", None)
            step.pop("ai_role", None)

            # Sanitize linked_*_ids — LLM sometimes generates names instead of UUIDs
            for id_field in ("linked_workflow_ids", "linked_feature_ids", "linked_data_entity_ids"):
                if id_field in step and isinstance(step[id_field], list):
                    step[id_field] = [v for v in step[id_field] if isinstance(v, str) and _UUID_RE.match(v)]

            try:
                saved = create_flow_step(flow_id, project_id, step)
                saved_steps.append(saved)

                try:
                    embed_entity("solution_flow_step", UUID(saved["id"]), saved)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to save step {i} '{step.get('title')}': {e}")
        else:
            try:
                update_flow_step(UUID(step["id"]), {"step_index": i})
                saved_steps.append(step)
            except Exception as e:
                logger.warning(f"Failed to reindex confirmed step {step['id']}: {e}")

    return saved_steps


def _build_narratives_for_steps(saved_steps: list[dict], project_id: UUID) -> None:
    """Build background narratives for newly generated steps. Fire-and-forget."""
    try:
        from app.core.solution_flow_narrative import build_step_narrative
        from app.db.solution_flow import update_flow_step

        for step in saved_steps:
            if step.get("confirmation_status") in ("confirmed_consultant", "confirmed_client"):
                continue
            try:
                narrative = build_step_narrative(step, project_id)
                if narrative:
                    update_flow_step(UUID(step["id"]), {"background_narrative": narrative})
            except Exception as e:
                logger.debug(f"Narrative build failed for step {step.get('id')}: {e}")
    except Exception as e:
        logger.warning(f"Narrative building failed: {e}")
