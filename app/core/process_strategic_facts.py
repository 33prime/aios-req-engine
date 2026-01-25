"""Process strategic entity fact types into database entities."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.facts import list_latest_extracted_facts
from app.db.business_drivers import smart_upsert_business_driver
from app.db.competitor_refs import smart_upsert_competitor_ref
from app.db.stakeholders import smart_upsert_stakeholder

logger = get_logger(__name__)


def process_strategic_facts_for_signal(
    project_id: UUID,
    signal_id: UUID | None = None,
) -> dict[str, int]:
    """
    Process strategic entity fact types from extracted facts into database entities.

    This function extracts business drivers (pain, goal, kpi), competitors, and
    stakeholders from the most recent fact extraction and creates/updates entities
    using smart_upsert functions.

    Args:
        project_id: Project UUID
        signal_id: Optional signal UUID for attribution

    Returns:
        Dict with counts:
        - business_drivers_created
        - business_drivers_updated
        - business_drivers_merged
        - competitor_refs_created
        - competitor_refs_updated
        - competitor_refs_merged
        - stakeholders_created
        - stakeholders_updated
        - stakeholders_merged
    """
    result = {
        "business_drivers_created": 0,
        "business_drivers_updated": 0,
        "business_drivers_merged": 0,
        "competitor_refs_created": 0,
        "competitor_refs_updated": 0,
        "competitor_refs_merged": 0,
        "stakeholders_created": 0,
        "stakeholders_updated": 0,
        "stakeholders_merged": 0,
    }

    # Get most recent extracted facts for this project
    facts_rows = list_latest_extracted_facts(project_id, limit=1)

    if not facts_rows:
        logger.info(f"No extracted facts found for project {project_id}")
        return result

    latest_extraction = facts_rows[0]
    facts_json = latest_extraction.get("facts", {})
    facts_list = facts_json.get("facts", [])

    if not facts_list:
        logger.info(f"No facts in latest extraction for project {project_id}")
        return result

    logger.info(
        f"Processing {len(facts_list)} facts for strategic entities",
        extra={"project_id": str(project_id)},
    )

    # Process each fact
    for fact in facts_list:
        fact_type = fact.get("fact_type", "").lower()
        title = fact.get("title", "")
        detail = fact.get("detail", "")
        confidence = fact.get("confidence", "medium")

        # Skip if no meaningful content
        if not title and not detail:
            continue

        description = title or detail[:100]

        # Build evidence object from this fact
        evidence_items = fact.get("evidence", [])
        new_evidence = []

        for ev in evidence_items:
            new_evidence.append({
                "signal_id": str(signal_id) if signal_id else None,
                "chunk_id": ev.get("chunk_id"),
                "text": ev.get("excerpt", ""),
                "confidence": 0.8 if confidence == "high" else 0.6 if confidence == "medium" else 0.4,
            })

        # Handle business driver types (pain, goal, kpi)
        if fact_type in ("pain", "goal", "kpi", "metric", "objective"):
            driver_type = "kpi" if fact_type in ("kpi", "metric") else fact_type
            if driver_type == "objective":
                driver_type = "goal"

            try:
                _, action = smart_upsert_business_driver(
                    project_id=project_id,
                    driver_type=driver_type,
                    description=description,
                    new_evidence=new_evidence if new_evidence else None,
                    source_signal_id=signal_id,
                    created_by="system",
                    similarity_threshold=0.75,
                    measurement=detail if fact_type in ("kpi", "metric") else None,
                    priority=3,
                )

                # Track action type
                if action == "created":
                    result["business_drivers_created"] += 1
                elif action == "updated":
                    result["business_drivers_updated"] += 1
                elif action == "merged":
                    result["business_drivers_merged"] += 1

                logger.debug(f"{action.capitalize()} {driver_type} driver: {description[:50]}")

            except Exception as e:
                logger.warning(f"Failed to upsert business driver: {e}")

        # Handle competitor types (competitor, design_inspiration, feature_inspiration)
        elif fact_type in ("competitor", "design_inspiration", "feature_inspiration"):
            name = title or detail[:50]

            try:
                ref_type = fact_type

                _, action = smart_upsert_competitor_ref(
                    project_id=project_id,
                    reference_type=ref_type,
                    name=name,
                    new_evidence=new_evidence if new_evidence else None,
                    source_signal_id=signal_id,
                    created_by="system",
                    similarity_threshold=0.75,
                    research_notes=detail,
                )

                # Track action type
                if action == "created":
                    result["competitor_refs_created"] += 1
                elif action == "updated":
                    result["competitor_refs_updated"] += 1
                elif action == "merged":
                    result["competitor_refs_merged"] += 1

                logger.debug(f"{action.capitalize()} {ref_type}: {name}")

            except Exception as e:
                logger.warning(f"Failed to upsert competitor ref: {e}")

        # Handle stakeholder types
        elif fact_type == "stakeholder":
            name = title or detail[:50]

            try:
                _, action = smart_upsert_stakeholder(
                    project_id=project_id,
                    name=name,
                    role=None,  # Extract from detail if needed
                    email=None,
                    stakeholder_type=None,
                    influence_level=None,
                    engagement_status=None,
                    notes=detail,
                    new_evidence=new_evidence if new_evidence else None,
                    source_signal_id=signal_id,
                    created_by="system",
                    similarity_threshold=0.75,
                )

                # Track action type
                if action == "created":
                    result["stakeholders_created"] += 1
                elif action == "updated":
                    result["stakeholders_updated"] += 1
                elif action == "merged":
                    result["stakeholders_merged"] += 1

                logger.debug(f"{action.capitalize()} stakeholder: {name}")

            except Exception as e:
                logger.warning(f"Failed to upsert stakeholder: {e}")

    # Log summary
    total_drivers = (
        result["business_drivers_created"] +
        result["business_drivers_updated"] +
        result["business_drivers_merged"]
    )
    total_competitors = (
        result["competitor_refs_created"] +
        result["competitor_refs_updated"] +
        result["competitor_refs_merged"]
    )
    total_stakeholders = (
        result["stakeholders_created"] +
        result["stakeholders_updated"] +
        result["stakeholders_merged"]
    )

    logger.info(
        f"Processed strategic facts for project {project_id}: "
        f"drivers={total_drivers}, competitors={total_competitors}, stakeholders={total_stakeholders}",
        extra={"project_id": str(project_id), "result": result},
    )

    return result
