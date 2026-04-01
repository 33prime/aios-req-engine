#!/usr/bin/env python3
"""
Backfill script for entity enrichment + multi-vector embeddings.

Iterates all existing entities across projects, runs the enrichment chain
(Haiku), stores enrichment_intel JSONB, and generates all 4 multi-vector
embeddings in the entity_vectors table.

Resumable: tracks progress in a checkpoint file so it can be restarted
after interruption.

Usage:
    python scripts/backfill_enrichment.py
    python scripts/backfill_enrichment.py --project-id <uuid>
    python scripts/backfill_enrichment.py --resume
    python scripts/backfill_enrichment.py --entity-type feature
    python scripts/backfill_enrichment.py --dry-run
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.db.entity_embeddings import (
    EMBED_TEXT_BUILDERS,
    ENTITY_TABLE_MAP,
    embed_entity_multivector,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Checkpoint file for resuming
CHECKPOINT_FILE = Path(__file__).parent / ".backfill_enrichment_checkpoint"

# Rate limiting
BATCH_SIZE = 20
ENRICHMENT_BATCH_SIZE = 4  # entities per Haiku call (matches enrichment chain)
SLEEP_BETWEEN_BATCHES = 0.5  # seconds

# Entity types to process (ordered by typical importance)
ENTITY_TYPES = [
    "feature",
    "business_driver",
    "persona",
    "workflow",
    "vp_step",
    "stakeholder",
    "data_entity",
    "constraint",
    "competitor",
    "solution_flow_step",
    "unlock",
    "prototype_feedback",
]


def load_checkpoint() -> dict:
    """Load checkpoint from file. Returns {entity_type: last_entity_id}."""
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_checkpoint(checkpoint: dict) -> None:
    """Save checkpoint to file."""
    CHECKPOINT_FILE.write_text(json.dumps(checkpoint, indent=2))


async def enrich_entity_batch(
    entities: list[dict],
    entity_type: str,
    project_id: str,
) -> list[dict]:
    """Run enrichment chain on a batch of entities.

    Returns enrichment dicts keyed by entity_id.
    """
    from app.chains.enrich_entity_patches import enrich_entity_patches
    from app.core.schemas_entity_patch import EntityPatch

    # Convert entities to minimal EntityPatch objects for the enrichment chain
    patches = []
    for entity in entities:
        name = (
            entity.get("name")
            or entity.get("title")
            or entity.get("label")
            or entity.get("description", "")[:60]
        )
        patches.append(EntityPatch(
            operation="update",
            entity_type=entity_type,
            target_entity_id=str(entity["id"]),
            payload=entity,
        ))

    enriched = await enrich_entity_patches(
        patches=patches,
        entity_inventory_prompt="",  # No inventory context for backfill
        project_id=UUID(project_id),
    )

    # Map enrichment results back to entity IDs
    results = {}
    for patch in enriched:
        if patch.canonical_text and patch.target_entity_id:
            results[patch.target_entity_id] = {
                "canonical_text": patch.canonical_text,
                "hypothetical_questions": patch.hypothetical_questions or [],
                "expanded_terms": patch.expanded_terms or [],
            }
            if patch.enrichment_data:
                results[patch.target_entity_id].update(
                    {k: v for k, v in patch.enrichment_data.items() if v}
                )

    return results


async def process_entity_type(
    entity_type: str,
    project_id: str | None = None,
    resume_after: str | None = None,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Process all entities of a given type.

    Returns (total, enriched, embedded) counts.
    """
    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        logger.warning(f"No table mapping for {entity_type}")
        return 0, 0, 0

    sb = get_supabase()

    # Build query
    query = sb.table(table).select("*").order("created_at")
    if project_id:
        query = query.eq("project_id", project_id)
    if resume_after:
        query = query.gt("id", resume_after)

    response = query.limit(1000).execute()
    entities = response.data or []

    if not entities:
        logger.info(f"No {entity_type} entities to process")
        return 0, 0, 0

    logger.info(f"Processing {len(entities)} {entity_type} entities")

    total = 0
    enriched_count = 0
    embedded_count = 0
    checkpoint = load_checkpoint()

    for i in range(0, len(entities), BATCH_SIZE):
        batch = entities[i : i + BATCH_SIZE]
        total += len(batch)

        if dry_run:
            logger.info(f"  [DRY RUN] Would process {len(batch)} {entity_type} entities")
            continue

        # Determine project_id for each entity
        for entity in batch:
            eid = str(entity["id"])
            pid = str(entity.get("project_id", project_id or ""))

            if not pid:
                continue

            # Step 1: Run enrichment
            try:
                enrichment_results = await enrich_entity_batch(
                    [entity], entity_type, pid
                )
                enrichment = enrichment_results.get(eid, {})

                if enrichment:
                    # Store enrichment_intel on entity
                    enrichment["enrichment_sources"] = [{
                        "signal_id": None,
                        "source_authority": "backfill",
                    }]
                    sb.table(table).update({
                        "enrichment_intel": enrichment,
                    }).eq("id", eid).execute()
                    enriched_count += 1
            except Exception as e:
                logger.warning(f"Enrichment failed for {entity_type}/{eid}: {e}")
                enrichment = {}

            # Step 2: Generate multi-vector embeddings
            try:
                entity_enrichment = enrichment or entity.get("enrichment_intel") or {}
                await embed_entity_multivector(
                    entity_type=entity_type,
                    entity_id=UUID(eid),
                    entity_data=entity,
                    project_id=UUID(pid),
                    enrichment=entity_enrichment,
                )
                embedded_count += 1
            except Exception as e:
                logger.warning(f"Multi-vector embedding failed for {entity_type}/{eid}: {e}")

            # Update checkpoint
            checkpoint[entity_type] = eid
            save_checkpoint(checkpoint)

        # Rate limit between batches
        await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

        logger.info(
            f"  {entity_type}: {total}/{len(entities)} processed "
            f"({enriched_count} enriched, {embedded_count} embedded)"
        )

    return total, enriched_count, embedded_count


async def main():
    parser = argparse.ArgumentParser(description="Backfill entity enrichment + multi-vectors")
    parser.add_argument("--project-id", type=str, help="Process only this project")
    parser.add_argument("--entity-type", type=str, help="Process only this entity type")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    start_time = time.monotonic()
    checkpoint = load_checkpoint() if args.resume else {}

    types_to_process = [args.entity_type] if args.entity_type else ENTITY_TYPES

    grand_total = 0
    grand_enriched = 0
    grand_embedded = 0

    for entity_type in types_to_process:
        if entity_type not in ENTITY_TABLE_MAP:
            logger.warning(f"Unknown entity type: {entity_type}")
            continue

        resume_after = checkpoint.get(entity_type) if args.resume else None

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {entity_type}")
        if resume_after:
            logger.info(f"  Resuming after: {resume_after}")
        logger.info(f"{'='*60}")

        total, enriched, embedded = await process_entity_type(
            entity_type=entity_type,
            project_id=args.project_id,
            resume_after=resume_after,
            dry_run=args.dry_run,
        )

        grand_total += total
        grand_enriched += enriched
        grand_embedded += embedded

    elapsed = time.monotonic() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"BACKFILL COMPLETE")
    logger.info(f"  Total entities: {grand_total}")
    logger.info(f"  Enriched: {grand_enriched}")
    logger.info(f"  Embedded (multi-vector): {grand_embedded}")
    logger.info(f"  Duration: {elapsed:.1f}s")
    logger.info(f"{'='*60}")

    if not args.dry_run and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        logger.info("Checkpoint file removed")


if __name__ == "__main__":
    asyncio.run(main())
