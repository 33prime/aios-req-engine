"""
Data backfill script for Strategic Foundation entity tracking fields.

This script backfills the new tracking fields added in migrations 0070-0077:
- source_signal_ids (from source_signal_id)
- version (set to 1)
- created_by (set to 'system')
- enrichment_status (set to 'none')

Run this after applying migrations 0070-0077.

Usage:
    uv run python scripts/backfill_strategic_entity_tracking.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def backfill_business_drivers(dry_run: bool = False) -> dict[str, int]:
    """
    Backfill tracking fields for business_drivers table.

    Returns:
        Dict with counts of updated records
    """
    supabase = get_supabase()

    logger.info("Starting business_drivers backfill...")

    # Get all business drivers that need backfilling
    response = supabase.table("business_drivers").select("*").execute()
    drivers = response.data or []

    logger.info(f"Found {len(drivers)} business drivers to check")

    updated_count = 0
    skipped_count = 0

    for driver in drivers:
        driver_id = driver["id"]
        needs_update = False
        updates = {}

        # Backfill source_signal_ids from source_signal_id
        source_signal_id = driver.get("source_signal_id")
        source_signal_ids = driver.get("source_signal_ids", []) or []

        if source_signal_id and not source_signal_ids:
            updates["source_signal_ids"] = [source_signal_id]
            needs_update = True

        # Set version = 1 if not set
        if driver.get("version") is None:
            updates["version"] = 1
            needs_update = True

        # Set created_by = 'system' if not set
        if driver.get("created_by") is None:
            updates["created_by"] = "system"
            needs_update = True

        # Set enrichment_status = 'none' if not set
        if driver.get("enrichment_status") is None:
            updates["enrichment_status"] = "none"
            needs_update = True

        if needs_update:
            if not dry_run:
                supabase.table("business_drivers").update(updates).eq("id", driver_id).execute()
                logger.debug(f"Updated business_driver {driver_id}: {list(updates.keys())}")
            else:
                logger.debug(f"[DRY RUN] Would update business_driver {driver_id}: {list(updates.keys())}")
            updated_count += 1
        else:
            skipped_count += 1

    logger.info(
        f"Business drivers backfill complete: {updated_count} updated, {skipped_count} skipped"
    )

    return {"updated": updated_count, "skipped": skipped_count}


def backfill_competitor_references(dry_run: bool = False) -> dict[str, int]:
    """
    Backfill tracking fields for competitor_references table.

    Returns:
        Dict with counts of updated records
    """
    supabase = get_supabase()

    logger.info("Starting competitor_references backfill...")

    response = supabase.table("competitor_references").select("*").execute()
    refs = response.data or []

    logger.info(f"Found {len(refs)} competitor references to check")

    updated_count = 0
    skipped_count = 0

    for ref in refs:
        ref_id = ref["id"]
        needs_update = False
        updates = {}

        # Backfill source_signal_ids from source_signal_id
        source_signal_id = ref.get("source_signal_id")
        source_signal_ids = ref.get("source_signal_ids", []) or []

        if source_signal_id and not source_signal_ids:
            updates["source_signal_ids"] = [source_signal_id]
            needs_update = True

        # Set version = 1 if not set
        if ref.get("version") is None:
            updates["version"] = 1
            needs_update = True

        # Set created_by = 'system' if not set
        if ref.get("created_by") is None:
            updates["created_by"] = "system"
            needs_update = True

        # Set enrichment_status = 'none' if not set
        if ref.get("enrichment_status") is None:
            updates["enrichment_status"] = "none"
            needs_update = True

        if needs_update:
            if not dry_run:
                supabase.table("competitor_references").update(updates).eq("id", ref_id).execute()
                logger.debug(f"Updated competitor_reference {ref_id}: {list(updates.keys())}")
            else:
                logger.debug(f"[DRY RUN] Would update competitor_reference {ref_id}: {list(updates.keys())}")
            updated_count += 1
        else:
            skipped_count += 1

    logger.info(
        f"Competitor references backfill complete: {updated_count} updated, {skipped_count} skipped"
    )

    return {"updated": updated_count, "skipped": skipped_count}


def backfill_stakeholders(dry_run: bool = False) -> dict[str, int]:
    """
    Backfill tracking fields for stakeholders table.

    Note: stakeholders table doesn't have source_signal_id, so we only backfill
    version, created_by, and enrichment_status.

    Returns:
        Dict with counts of updated records
    """
    supabase = get_supabase()

    logger.info("Starting stakeholders backfill...")

    response = supabase.table("stakeholders").select("*").execute()
    stakeholders = response.data or []

    logger.info(f"Found {len(stakeholders)} stakeholders to check")

    updated_count = 0
    skipped_count = 0

    for stakeholder in stakeholders:
        stakeholder_id = stakeholder["id"]
        needs_update = False
        updates = {}

        # Set version = 1 if not set
        if stakeholder.get("version") is None:
            updates["version"] = 1
            needs_update = True

        # Set created_by = 'system' if not set
        if stakeholder.get("created_by") is None:
            updates["created_by"] = "system"
            needs_update = True

        # Set enrichment_status = 'none' if not set
        if stakeholder.get("enrichment_status") is None:
            updates["enrichment_status"] = "none"
            needs_update = True

        # Initialize source_signal_ids as empty array if not set
        if stakeholder.get("source_signal_ids") is None:
            updates["source_signal_ids"] = []
            needs_update = True

        if needs_update:
            if not dry_run:
                supabase.table("stakeholders").update(updates).eq("id", stakeholder_id).execute()
                logger.debug(f"Updated stakeholder {stakeholder_id}: {list(updates.keys())}")
            else:
                logger.debug(f"[DRY RUN] Would update stakeholder {stakeholder_id}: {list(updates.keys())}")
            updated_count += 1
        else:
            skipped_count += 1

    logger.info(
        f"Stakeholders backfill complete: {updated_count} updated, {skipped_count} skipped"
    )

    return {"updated": updated_count, "skipped": skipped_count}


def main():
    """Main backfill execution."""
    parser = argparse.ArgumentParser(
        description="Backfill strategic entity tracking fields"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without making changes",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Strategic Entity Tracking Backfill Script")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    else:
        logger.info("✅ LIVE MODE - Database will be updated")

    logger.info("")

    try:
        # Backfill each table
        results = {
            "business_drivers": backfill_business_drivers(args.dry_run),
            "competitor_references": backfill_competitor_references(args.dry_run),
            "stakeholders": backfill_stakeholders(args.dry_run),
        }

        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("Backfill Summary")
        logger.info("=" * 60)

        total_updated = 0
        total_skipped = 0

        for table, counts in results.items():
            logger.info(f"{table}:")
            logger.info(f"  Updated: {counts['updated']}")
            logger.info(f"  Skipped: {counts['skipped']}")
            total_updated += counts["updated"]
            total_skipped += counts["skipped"]

        logger.info("")
        logger.info(f"Total updated: {total_updated}")
        logger.info(f"Total skipped: {total_skipped}")
        logger.info("")

        if args.dry_run:
            logger.info("🔍 This was a dry run. Run without --dry-run to apply changes.")
        else:
            logger.info("✅ Backfill complete!")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
