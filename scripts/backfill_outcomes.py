#!/usr/bin/env python3
"""
Backfill script for outcomes on existing projects.

For projects with existing entity data, runs outcome generation,
scores strength, and links outcomes to entities.

Depends on Phase 1 enrichment backfill being complete (enriched entities
produce better outcomes).

Usage:
    python scripts/backfill_outcomes.py
    python scripts/backfill_outcomes.py --project-id <uuid>
    python scripts/backfill_outcomes.py --dry-run
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

CHECKPOINT_FILE = Path(__file__).parent / ".backfill_outcomes_checkpoint"


def load_checkpoint() -> set[str]:
    """Load set of completed project IDs."""
    if CHECKPOINT_FILE.exists():
        try:
            return set(json.loads(CHECKPOINT_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_checkpoint(completed: set[str]) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(sorted(completed)))


async def backfill_project(project_id: str, dry_run: bool = False) -> dict:
    """Run outcome generation for a single project."""
    from app.chains.generate_outcomes import generate_outcomes, persist_generated_outcomes
    from app.chains.score_outcomes import score_and_persist_outcome
    from app.db.outcomes import list_outcomes

    sb = get_supabase()

    # Load entity graph
    entity_graph = {}
    entity_count = 0
    for etype, table in [
        ("personas", "personas"),
        ("business_drivers", "business_drivers"),
        ("features", "features"),
        ("workflows", "workflows"),
        ("constraints", "constraints"),
    ]:
        try:
            resp = sb.table(table).select("*").eq("project_id", project_id).execute()
            entities = resp.data or []
            entity_graph[etype] = entities
            entity_count += len(entities)
        except Exception:
            entity_graph[etype] = []

    if entity_count < 3:
        return {"skipped": True, "reason": "Not enough entities", "entity_count": entity_count}

    if dry_run:
        return {"dry_run": True, "entity_count": entity_count}

    # Check existing outcomes
    existing = list_outcomes(UUID(project_id))

    # Generate outcomes
    result = await generate_outcomes(
        project_id=UUID(project_id),
        entity_graph=entity_graph,
        existing_outcomes=existing,
    )

    # Persist
    created = await persist_generated_outcomes(
        project_id=UUID(project_id),
        generation_result=result,
        entity_graph=entity_graph,
    )

    # Score each
    scored = 0
    for outcome in created:
        try:
            await score_and_persist_outcome(outcome_id=str(outcome["id"]))
            scored += 1
        except Exception as e:
            logger.warning(f"Failed to score outcome {outcome['id']}: {e}")

    return {
        "outcomes_created": len(created),
        "outcomes_scored": scored,
        "macro_outcome": result.get("macro_outcome"),
        "entity_count": entity_count,
        "existing_outcomes": len(existing),
    }


async def main():
    parser = argparse.ArgumentParser(description="Backfill outcomes for existing projects")
    parser.add_argument("--project-id", type=str, help="Process only this project")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    start_time = time.monotonic()
    sb = get_supabase()

    if args.project_id:
        project_ids = [args.project_id]
    else:
        resp = sb.table("projects").select("id").execute()
        project_ids = [p["id"] for p in (resp.data or [])]

    completed = load_checkpoint()
    total_created = 0
    total_projects = 0

    for pid in project_ids:
        if pid in completed and not args.project_id:
            logger.info(f"Skipping {pid} (already completed)")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing project: {pid}")

        try:
            result = await backfill_project(pid, dry_run=args.dry_run)

            if result.get("skipped"):
                logger.info(f"  Skipped: {result.get('reason')}")
            elif result.get("dry_run"):
                logger.info(f"  [DRY RUN] {result.get('entity_count')} entities")
            else:
                total_created += result.get("outcomes_created", 0)
                total_projects += 1
                logger.info(
                    f"  Created: {result.get('outcomes_created')} outcomes "
                    f"(scored: {result.get('outcomes_scored')}, "
                    f"existing: {result.get('existing_outcomes')})"
                )
                if result.get("macro_outcome"):
                    logger.info(f"  Macro: {result['macro_outcome'][:80]}")

            completed.add(pid)
            save_checkpoint(completed)

        except Exception as e:
            logger.error(f"  Failed: {e}", exc_info=True)

        await asyncio.sleep(1.0)  # Rate limit between projects

    elapsed = time.monotonic() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"BACKFILL COMPLETE")
    logger.info(f"  Projects processed: {total_projects}")
    logger.info(f"  Outcomes created: {total_created}")
    logger.info(f"  Duration: {elapsed:.1f}s")

    if not args.dry_run and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


if __name__ == "__main__":
    asyncio.run(main())
