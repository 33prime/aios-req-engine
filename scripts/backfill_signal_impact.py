#!/usr/bin/env python3
"""
Backfill script for signal_impact table.

Populates signal_impact records by scanning existing entities (PRD sections, features,
VP steps, insights) and extracting chunk_ids from their evidence arrays.

Usage:
    python scripts/backfill_signal_impact.py [--project-id PROJECT_ID] [--batch-size 100]

Options:
    --project-id: Optional project UUID to backfill only that project
    --batch-size: Number of entities to process per batch (default: 100)
"""

import argparse
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.db.signals import record_chunk_impacts
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def backfill_prd_sections(project_id: UUID | None = None, batch_size: int = 100) -> int:
    """Backfill signal_impact for PRD sections."""
    supabase = get_supabase()
    total_processed = 0

    try:
        # Build query
        query = supabase.table("prd_sections").select("id, project_id, evidence")
        if project_id:
            query = query.eq("project_id", str(project_id))

        response = query.execute()
        sections = response.data or []

        logger.info(f"Found {len(sections)} PRD sections to process")

        for section in sections:
            if not section.get("evidence"):
                continue

            chunk_ids = [e.get("chunk_id") for e in section["evidence"] if e.get("chunk_id")]
            if chunk_ids:
                record_chunk_impacts(
                    chunk_ids=chunk_ids,
                    entity_type="prd_section",
                    entity_id=UUID(section["id"]),
                    usage_context="evidence",
                )
                total_processed += 1

        logger.info(f"Processed {total_processed} PRD sections")
        return total_processed

    except Exception as e:
        logger.error(f"Failed to backfill PRD sections: {e}")
        raise


def backfill_features(project_id: UUID | None = None, batch_size: int = 100) -> int:
    """Backfill signal_impact for features."""
    supabase = get_supabase()
    total_processed = 0

    try:
        # Build query
        query = supabase.table("features").select("id, project_id, evidence")
        if project_id:
            query = query.eq("project_id", str(project_id))

        response = query.execute()
        features = response.data or []

        logger.info(f"Found {len(features)} features to process")

        for feature in features:
            if not feature.get("evidence"):
                continue

            chunk_ids = [e.get("chunk_id") for e in feature["evidence"] if e.get("chunk_id")]
            if chunk_ids:
                record_chunk_impacts(
                    chunk_ids=chunk_ids,
                    entity_type="feature",
                    entity_id=UUID(feature["id"]),
                    usage_context="evidence",
                )
                total_processed += 1

        logger.info(f"Processed {total_processed} features")
        return total_processed

    except Exception as e:
        logger.error(f"Failed to backfill features: {e}")
        raise


def backfill_vp_steps(project_id: UUID | None = None, batch_size: int = 100) -> int:
    """Backfill signal_impact for VP steps."""
    supabase = get_supabase()
    total_processed = 0

    try:
        # Build query
        query = supabase.table("vp_steps").select("id, project_id, evidence")
        if project_id:
            query = query.eq("project_id", str(project_id))

        response = query.execute()
        steps = response.data or []

        logger.info(f"Found {len(steps)} VP steps to process")

        for step in steps:
            if not step.get("evidence"):
                continue

            chunk_ids = [e.get("chunk_id") for e in step["evidence"] if e.get("chunk_id")]
            if chunk_ids:
                record_chunk_impacts(
                    chunk_ids=chunk_ids,
                    entity_type="vp_step",
                    entity_id=UUID(step["id"]),
                    usage_context="evidence",
                )
                total_processed += 1

        logger.info(f"Processed {total_processed} VP steps")
        return total_processed

    except Exception as e:
        logger.error(f"Failed to backfill VP steps: {e}")
        raise


def backfill_insights(project_id: UUID | None = None, batch_size: int = 100) -> int:
    """Backfill signal_impact for insights."""
    supabase = get_supabase()
    total_processed = 0

    try:
        # Build query
        query = supabase.table("insights").select("id, project_id, evidence")
        if project_id:
            query = query.eq("project_id", str(project_id))

        response = query.execute()
        insights = response.data or []

        logger.info(f"Found {len(insights)} insights to process")

        for insight in insights:
            if not insight.get("evidence"):
                continue

            chunk_ids = [e.get("chunk_id") for e in insight["evidence"] if e.get("chunk_id")]
            if chunk_ids:
                record_chunk_impacts(
                    chunk_ids=chunk_ids,
                    entity_type="insight",
                    entity_id=UUID(insight["id"]),
                    usage_context="evidence",
                )
                total_processed += 1

        logger.info(f"Processed {total_processed} insights")
        return total_processed

    except Exception as e:
        logger.error(f"Failed to backfill insights: {e}")
        raise


def main():
    """Main backfill function."""
    parser = argparse.ArgumentParser(description="Backfill signal_impact table from existing evidence")
    parser.add_argument(
        "--project-id",
        type=str,
        help="Optional project UUID to backfill only that project",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of entities to process per batch (default: 100)",
    )

    args = parser.parse_args()

    project_id = UUID(args.project_id) if args.project_id else None
    batch_size = args.batch_size

    logger.info("=" * 60)
    logger.info("SIGNAL IMPACT BACKFILL")
    logger.info("=" * 60)

    if project_id:
        logger.info(f"Backfilling for project: {project_id}")
    else:
        logger.info("Backfilling for ALL projects")

    logger.info(f"Batch size: {batch_size}")
    logger.info("=" * 60)

    try:
        # Backfill all entity types
        total = 0

        logger.info("\n[1/4] Backfilling PRD sections...")
        total += backfill_prd_sections(project_id, batch_size)

        logger.info("\n[2/4] Backfilling features...")
        total += backfill_features(project_id, batch_size)

        logger.info("\n[3/4] Backfilling VP steps...")
        total += backfill_vp_steps(project_id, batch_size)

        logger.info("\n[4/4] Backfilling insights...")
        total += backfill_insights(project_id, batch_size)

        logger.info("=" * 60)
        logger.info(f"BACKFILL COMPLETE - Processed {total} entities")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
