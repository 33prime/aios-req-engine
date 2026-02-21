"""Rerun extraction on an existing signal for eval/debugging.

Re-processes a signal's extraction pipeline without applying patches to the DB.
Outputs the full extraction audit trail.

Usage:
    uv run python scripts/rerun_extraction.py <signal_id> \
        [--project-id <id>] [--dry-run] [--dump <path>]

Examples:
    # Rerun and dump to JSON
    uv run python scripts/rerun_extraction.py 5929b7e7-d036-45e2-b71f-5ff8e49e6b7e \
        --project-id 634647e8-a22a-4b6f-b42a-452659620bc4 \
        --dump docs/eval/extraction-run-001.json

    # Dry-run (don't write log back to signal)
    uv run python scripts/rerun_extraction.py 5929b7e7-d036-45e2-b71f-5ff8e49e6b7e \
        --dry-run --dump /tmp/test-run.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def run_extraction(
    signal_id: str,
    project_id: str | None,
    dry_run: bool,
    dump_path: str | None,
) -> None:
    from app.core.context_snapshot import build_context_snapshot
    from app.core.entity_dedup import dedup_create_patches
    from app.core.extraction_logger import ExtractionLog
    from app.db.signals import get_signal, list_signal_chunks

    # Step 1: Load signal
    print(f"\n{'='*60}")
    print(f"Loading signal {signal_id}...")
    signal = get_signal(uuid.UUID(signal_id))
    signal_type = (signal.get("metadata") or {}).get(
        "source_type", signal.get("signal_type", "default")
    )
    source_authority = (signal.get("metadata") or {}).get("authority", "research")

    pid = project_id or signal.get("project_id")
    if not pid:
        print("ERROR: Could not determine project_id. Pass --project-id.")
        sys.exit(1)

    project_uuid = uuid.UUID(pid)
    print(f"  Signal type: {signal_type}")
    print(f"  Project: {pid}")
    print(f"  Source authority: {source_authority}")

    # Step 2: Load chunks
    print(f"\nLoading chunks...")
    chunks = list_signal_chunks(uuid.UUID(signal_id))
    print(f"  Found {len(chunks)} chunks")

    # Step 3: Build context
    print(f"\nBuilding context snapshot...")
    context_snapshot = await build_context_snapshot(project_uuid)
    inventory = getattr(context_snapshot, "entity_inventory", {})
    entity_count = sum(len(v) for v in inventory.values())
    print(f"  Entity inventory: {entity_count} entities across {len(inventory)} types")

    # Print pulse state if available
    pulse = getattr(context_snapshot, "pulse", None)
    if pulse:
        print(f"\n--- Project Pulse ---")
        print(f"  Stage: {pulse.stage.current.value} (progress: {pulse.stage.progress:.0%})")
        if pulse.stage.next_stage:
            print(f"  Next stage: {pulse.stage.next_stage.value}")
        print(f"  Gates ({pulse.stage.gates_met}/{pulse.stage.gates_total}):")
        for gate in pulse.stage.gates:
            print(f"    {gate}")
        print(f"\n  Entity Health:")
        for et, h in sorted(pulse.health.items(), key=lambda x: -x[1].count):
            print(f"    {et}: {h.count}/{h.target} ({h.coverage.value}) "
                  f"conf={h.confirmation_rate:.0%} → {h.directive.value} [score={h.health_score:.0f}]")
        print(f"\n  Risk score: {pulse.risks.risk_score:.0f}")
        if pulse.actions:
            print(f"\n  Top Actions:")
            for a in pulse.actions[:5]:
                gate_tag = " [GATE]" if a.unblocks_gate else ""
                print(f"    [{a.impact_score:.0f}] {a.sentence}{gate_tag}")
        print(f"\n  Forecast: coverage={pulse.forecast.coverage_index:.0%} "
              f"confidence={pulse.forecast.confidence_index:.0%} "
              f"proto_ready={pulse.forecast.prototype_readiness:.0%}")
        print(f"\n  Rules fired ({len(pulse.rules_fired)}):")
        for rule in pulse.rules_fired:
            print(f"    {rule}")
        print(f"--- End Pulse ---")

    briefing = getattr(context_snapshot, "extraction_briefing_prompt", "")
    if briefing:
        print(f"\n--- Extraction Directive ---")
        print(briefing)
        print(f"--- End Directive ---")
    else:
        print(f"  (No extraction directive generated)")

    # Step 4: Create extraction log
    run_id = str(uuid.uuid4())
    extraction_log = ExtractionLog(run_id=run_id, model="")
    extraction_log.log_context(context_snapshot)

    # Step 5: Extract
    print(f"\nExtracting patches...")
    if len(chunks) >= 2:
        from app.chains.extract_entity_patches import extract_patches_parallel

        patch_list = await extract_patches_parallel(
            chunks=chunks,
            signal_type=signal_type,
            context_snapshot=context_snapshot,
            source_authority=source_authority,
            signal_id=signal_id,
            run_id=run_id,
            extraction_log=extraction_log,
        )
    else:
        from app.chains.extract_entity_patches import extract_entity_patches

        signal_text = signal.get("raw_text", "")
        chunk_ids = [str(c.get("id", "")) for c in chunks]
        patch_list = await extract_entity_patches(
            signal_text=signal_text,
            signal_type=signal_type,
            context_snapshot=context_snapshot,
            chunk_ids=chunk_ids,
            source_authority=source_authority,
            signal_id=signal_id,
            run_id=run_id,
            extraction_log=extraction_log,
        )

    extraction_log.model = patch_list.extraction_model or ""
    print(f"  Extracted {len(patch_list.patches)} patches (model: {patch_list.extraction_model})")
    print(f"  Duration: {patch_list.extraction_duration_ms}ms")

    # Step 6: Dedup
    print(f"\nDeduplicating patches...")
    create_count = sum(1 for p in patch_list.patches if p.operation == "create")
    print(f"  Create patches to dedup: {create_count}")

    deduped = await dedup_create_patches(
        patch_list.patches,
        inventory,
        project_uuid,
        extraction_log=extraction_log,
    )
    deduped_create_count = sum(1 for p in deduped if p.operation == "create")
    deduped_merge_count = sum(1 for p in deduped if p.operation == "merge")
    print(f"  After dedup: {len(deduped)} patches ({deduped_create_count} creates, {deduped_merge_count} merges)")

    # Step 7: Score
    print(f"\nScoring patches...")
    try:
        from app.chains.score_entity_patches import score_entity_patches

        scored = await score_entity_patches(
            patches=deduped,
            context_snapshot=context_snapshot,
        )
        extraction_log.log_scoring(scored)
        print(f"  Scored {len(scored)} patches")
    except Exception as e:
        print(f"  Scoring failed (non-fatal): {e}")
        scored = deduped
        extraction_log.log_scoring(scored)

    # Step 8: Skip apply (no side effects)
    print(f"\n  SKIPPING patch application (rerun mode)")

    # Summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"  Run ID: {run_id}")
    print(f"  Chunks processed: {len(extraction_log.chunk_results)}")
    raw_total = sum(cr["patch_count"] for cr in extraction_log.chunk_results)
    print(f"  Raw patches (pre-merge): {raw_total}")
    print(f"  After chunk merge: {extraction_log.post_chunk_merge.get('after_count', 'N/A')}")
    merge_decisions = extraction_log.post_chunk_merge.get("merge_decisions", [])
    if merge_decisions:
        print(f"  Chunk merges:")
        for md in merge_decisions:
            print(f"    - '{md['name']}' ({md['entity_type']}): {md['duplicates_merged']} → 1")
    # Consolidation (semantic dedup)
    if extraction_log.post_consolidation:
        cons = extraction_log.post_consolidation
        print(f"  After consolidation: {cons.get('after_count', 'N/A')} (from {cons.get('before_count', 'N/A')})")
        for cg in cons.get("merge_groups", []):
            print(f"    - Kept: '{cg.get('keep_description', '')[:60]}' ({cg.get('entity_type', '')})")
            for desc in cg.get("merged_descriptions", []):
                print(f"      Merged: '{desc}'")
            print(f"      Reason: {cg.get('reasoning', '')}")
    dedup_decisions = extraction_log.post_entity_dedup.get("dedup_decisions", [])
    converted = [d for d in dedup_decisions if d["action"] == "convert_to_merge"]
    passed = [d for d in dedup_decisions if d["action"] == "keep_as_create"]
    print(f"  Entity dedup: {len(converted)} converted to merge, {len(passed)} kept as create")
    if converted:
        for d in converted:
            print(f"    - '{d['patch_name']}' → matched '{d['matched_entity_name']}' ({d['strategy']}, score={d['score']:.2f})")
    print(f"  Final scored patches: {extraction_log.post_scoring.get('patch_count', 'N/A')}")

    # Count by entity type
    if scored:
        from collections import Counter
        type_counts = Counter(p.entity_type for p in scored)
        op_counts = Counter(p.operation for p in scored)
        print(f"\n  By type: {dict(type_counts)}")
        print(f"  By operation: {dict(op_counts)}")

    # Dump to file
    if dump_path:
        print(f"\nDumping extraction log to {dump_path}...")
        path = Path(dump_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(extraction_log.to_dict(), indent=2, default=str))
        print(f"  Written ({path.stat().st_size:,} bytes)")

    # Write back to signal
    if not dry_run:
        print(f"\nWriting extraction_log to signal...")
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        sb.table("signals").update(
            {"extraction_log": extraction_log.to_dict()}
        ).eq("id", signal_id).execute()
        print(f"  Done.")
    else:
        print(f"\n  DRY RUN — not writing to signal")

    print(f"\n{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rerun extraction on an existing signal for eval/debugging."
    )
    parser.add_argument("signal_id", help="Signal UUID to reprocess")
    parser.add_argument("--project-id", help="Project UUID (auto-detected from signal if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write log back to signal")
    parser.add_argument("--dump", metavar="PATH", help="Dump extraction log as JSON to file")

    args = parser.parse_args()

    asyncio.run(run_extraction(
        signal_id=args.signal_id,
        project_id=args.project_id,
        dry_run=args.dry_run,
        dump_path=args.dump,
    ))


if __name__ == "__main__":
    main()
