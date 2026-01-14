"""
Run Strategic Foundation - Background Job

Orchestrates:
1. Company enrichment (Firecrawl + LLM)
2. Stakeholder ↔ Project Member linking
3. Business driver & competitor extraction from signals
4. State snapshot invalidation

This is designed to be called as a chat slash command.
"""

import logging
from typing import Any
from uuid import UUID

from app.chains.enrich_company import enrich_company
from app.core.config import get_settings
from app.core.state_snapshot import invalidate_snapshot
from app.db.company_info import get_company_info
from app.db.stakeholders import auto_link_project_members_to_stakeholders

logger = logging.getLogger(__name__)


async def run_strategic_foundation(project_id: UUID) -> dict[str, Any]:
    """
    Main entry point for strategic foundation enrichment.

    This function:
    1. Enriches company info from website scraping + AI
    2. Links stakeholders to project members by email
    3. Extracts business drivers and competitor refs from signals
    4. Invalidates state snapshot for fresh LLM context

    Args:
        project_id: Project UUID

    Returns:
        Summary of changes made:
        - company_enriched: bool
        - enrichment_source: str (if enriched)
        - stakeholders_linked: int
        - business_drivers_created: int
        - competitor_refs_created: int
        - errors: list of error messages
    """
    results: dict[str, Any] = {
        "company_enriched": False,
        "enrichment_source": None,
        "stakeholders_linked": 0,
        "business_drivers_created": 0,
        "competitor_refs_created": 0,
        "errors": [],
    }

    # 1. Get company info
    company_info = get_company_info(project_id)

    # 2. Company enrichment (if company info exists)
    if company_info:
        logger.info(f"Starting company enrichment for project {project_id}")
        try:
            enrichment_result = await enrich_company(project_id)

            if enrichment_result.get("success"):
                results["company_enriched"] = True
                results["enrichment_source"] = enrichment_result.get("enrichment_source")
                results["enrichment_confidence"] = enrichment_result.get("enrichment_confidence")
                results["scraped_chars"] = enrichment_result.get("scraped_chars", 0)
                logger.info(
                    f"Company enrichment complete: source={results['enrichment_source']}, "
                    f"confidence={results.get('enrichment_confidence')}"
                )
            else:
                error = enrichment_result.get("error", "Unknown error")
                results["errors"].append(f"Company enrichment failed: {error}")
                logger.warning(f"Company enrichment failed: {error}")

        except Exception as e:
            error_msg = f"Company enrichment error: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)
    else:
        logger.info(f"No company info found for project {project_id}, skipping enrichment")

    # 3. Link stakeholders to project members
    logger.info(f"Linking stakeholders to project members for project {project_id}")
    try:
        linked_count = auto_link_project_members_to_stakeholders(project_id)
        results["stakeholders_linked"] = linked_count
        if linked_count > 0:
            logger.info(f"Linked {linked_count} stakeholders to project members")
    except Exception as e:
        error_msg = f"Stakeholder linking error: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg, exc_info=True)

    # 4. Extract business drivers and competitor refs from signals
    logger.info(f"Extracting business drivers and competitor refs for project {project_id}")
    try:
        extraction_result = extract_strategic_entities_from_signals(project_id)
        results["business_drivers_created"] = extraction_result.get("business_drivers_created", 0)
        results["competitor_refs_created"] = extraction_result.get("competitor_refs_created", 0)
        if extraction_result.get("errors"):
            results["errors"].extend(extraction_result["errors"])
        logger.info(
            f"Strategic entity extraction complete: "
            f"business_drivers={results['business_drivers_created']}, "
            f"competitor_refs={results['competitor_refs_created']}"
        )
    except Exception as e:
        error_msg = f"Strategic entity extraction error: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg, exc_info=True)

    # 5. Invalidate state snapshot to refresh LLM context
    invalidate_snapshot(project_id)
    logger.info(f"State snapshot invalidated for project {project_id}")

    # 6. Log summary
    logger.info(
        f"Strategic foundation complete for project {project_id}: "
        f"company_enriched={results['company_enriched']}, "
        f"stakeholders_linked={results['stakeholders_linked']}, "
        f"business_drivers={results['business_drivers_created']}, "
        f"competitor_refs={results['competitor_refs_created']}, "
        f"errors={len(results['errors'])}"
    )

    return results


def extract_strategic_entities_from_signals(project_id: UUID) -> dict[str, Any]:
    """
    Extract business drivers and competitor refs from all project signals.

    This function:
    1. Gets all signals for the project (or uses project description if none)
    2. For each signal, extracts facts using the fact extraction chain
    3. Converts relevant facts (pain, goal, competitor, design_inspiration) to entities
    4. Creates business_drivers and competitor_refs in the database

    Args:
        project_id: Project UUID

    Returns:
        Dict with:
        - business_drivers_created: int
        - competitor_refs_created: int
        - signals_processed: int
        - errors: list of error messages
    """
    from app.chains.extract_facts import extract_facts_from_chunks
    from app.db.signals import list_project_signals, list_signal_chunks
    from app.db.business_drivers import create_business_driver, find_similar_driver
    from app.db.competitor_refs import create_competitor_ref, find_similar_competitor
    from app.db.projects import get_project

    settings = get_settings()

    result = {
        "business_drivers_created": 0,
        "competitor_refs_created": 0,
        "signals_processed": 0,
        "errors": [],
    }

    # Get all signals for the project
    signal_response = list_project_signals(project_id, limit=50)
    signals = signal_response.get("signals", [])

    # If no signals, use project description as a synthetic signal
    if not signals:
        logger.info(f"No signals found for project {project_id}, using project description")
        try:
            project = get_project(project_id)
            if project and project.get("description"):
                # Create synthetic signal from project description
                signals = [{
                    "id": str(project_id),  # Use project_id as signal_id for synthetic
                    "content": f"Project: {project.get('name', 'Untitled')}\n\n{project.get('description', '')}",
                    "title": project.get("name", "Project Description"),
                    "signal_type": "project_description",
                }]
                logger.info(f"Created synthetic signal from project description ({len(project.get('description', ''))} chars)")
            else:
                logger.info(f"No project description found for project {project_id}")
                return result
        except Exception as e:
            error_msg = f"Failed to get project for synthetic signal: {e}"
            result["errors"].append(error_msg)
            logger.warning(error_msg)
            return result

    logger.info(f"Processing {len(signals)} signals for strategic entity extraction")

    # Track what we've already created to avoid duplicates
    seen_drivers: set[str] = set()
    seen_competitors: set[str] = set()

    for signal in signals:
        signal_id = signal.get("id")
        if not signal_id:
            continue

        # Check if this is a synthetic signal (from project description)
        is_synthetic = signal.get("signal_type") == "project_description"

        try:
            # Get chunks for this signal (skip DB lookup for synthetic signals)
            chunks = []
            if not is_synthetic:
                chunks = list_signal_chunks(UUID(signal_id))

            # If no chunks, create a synthetic chunk from signal content
            if not chunks and signal.get("content"):
                chunks = [{
                    "id": signal_id,
                    "signal_id": signal_id,
                    "chunk_index": 0,
                    "content": signal.get("content", "")[:8000],  # Limit content
                    "start_char": 0,
                    "end_char": len(signal.get("content", "")),
                }]

            if not chunks:
                continue

            # Extract facts from chunks using GPT-4o for better quality
            extraction = extract_facts_from_chunks(
                signal=signal,
                chunks=chunks,
                settings=settings,
                model_override="gpt-4o",  # Use stronger model for strategic foundation
            )

            result["signals_processed"] += 1

            # Process extracted facts
            for fact in extraction.facts:
                fact_type = fact.fact_type.lower()
                title = fact.title or ""
                detail = fact.detail or ""

                # Skip if no meaningful content
                if not title and not detail:
                    continue

                description = title or detail[:100]
                desc_key = description.lower().strip()[:50]

                # Handle business driver types (pain, goal, kpi)
                if fact_type in ("pain", "goal", "kpi", "metric", "objective"):
                    if desc_key in seen_drivers:
                        continue

                    # Check for existing similar driver
                    driver_type = "kpi" if fact_type in ("kpi", "metric") else fact_type
                    if driver_type == "objective":
                        driver_type = "goal"

                    existing = find_similar_driver(
                        project_id, description, driver_type=driver_type, threshold=0.7
                    )
                    if existing:
                        continue

                    try:
                        create_business_driver(
                            project_id=project_id,
                            driver_type=driver_type,
                            description=description,
                            measurement=detail if fact_type in ("kpi", "metric") else None,
                            priority=3,
                            source_signal_id=None if is_synthetic else UUID(signal_id),
                        )
                        result["business_drivers_created"] += 1
                        seen_drivers.add(desc_key)
                        logger.debug(f"Created {driver_type} driver: {description[:50]}")
                    except Exception as e:
                        result["errors"].append(f"Failed to create business driver: {e}")

                # Handle competitor types (competitor, design_inspiration, feature_inspiration)
                elif fact_type in ("competitor", "design_inspiration", "feature_inspiration"):
                    name = title or detail[:50]
                    name_key = name.lower().strip()

                    if name_key in seen_competitors:
                        continue

                    # Check for existing similar competitor
                    existing = find_similar_competitor(project_id, name, threshold=0.8)
                    if existing:
                        continue

                    try:
                        ref_type = fact_type
                        create_competitor_ref(
                            project_id=project_id,
                            reference_type=ref_type,
                            name=name,
                            research_notes=detail,
                            source_signal_id=None if is_synthetic else UUID(signal_id),
                        )
                        result["competitor_refs_created"] += 1
                        seen_competitors.add(name_key)
                        logger.debug(f"Created {ref_type}: {name}")
                    except Exception as e:
                        result["errors"].append(f"Failed to create competitor ref: {e}")

        except Exception as e:
            error_msg = f"Error processing signal {signal_id}: {str(e)}"
            result["errors"].append(error_msg)
            logger.warning(error_msg)

    logger.info(
        f"Strategic entity extraction complete: "
        f"processed={result['signals_processed']}, "
        f"drivers={result['business_drivers_created']}, "
        f"competitors={result['competitor_refs_created']}"
    )

    return result


def get_strategic_foundation_summary(project_id: UUID) -> dict[str, Any]:
    """
    Get a summary of the current strategic foundation state.

    Useful for chat assistant to report on what exists.

    Args:
        project_id: Project UUID

    Returns:
        Summary dict with counts and status
    """
    from app.db.business_drivers import list_business_drivers
    from app.db.competitor_refs import list_competitor_refs
    from app.db.stakeholders import list_stakeholders
    from app.db.constraints import list_constraints

    company_info = get_company_info(project_id)
    drivers = list_business_drivers(project_id)
    competitors = list_competitor_refs(project_id)
    stakeholders = list_stakeholders(project_id)

    # Get constraints (may not have the function yet)
    try:
        constraints = list_constraints(project_id)
    except Exception:
        constraints = []

    # Check company enrichment status
    company_status = "none"
    if company_info:
        if company_info.get("enriched_at"):
            company_status = "enriched"
        else:
            company_status = "basic"

    return {
        "company": {
            "exists": company_info is not None,
            "name": company_info.get("name") if company_info else None,
            "status": company_status,
            "has_website": bool(company_info.get("website")) if company_info else False,
            "enrichment_source": company_info.get("enrichment_source") if company_info else None,
        },
        "business_drivers": {
            "count": len(drivers),
            "by_type": {
                "kpi": len([d for d in drivers if d.get("driver_type") == "kpi"]),
                "pain": len([d for d in drivers if d.get("driver_type") == "pain"]),
                "goal": len([d for d in drivers if d.get("driver_type") == "goal"]),
            },
        },
        "competitors": {
            "count": len(competitors),
            "by_type": {
                "competitor": len([c for c in competitors if c.get("reference_type") == "competitor"]),
                "design_inspiration": len([c for c in competitors if c.get("reference_type") == "design_inspiration"]),
                "feature_inspiration": len([c for c in competitors if c.get("reference_type") == "feature_inspiration"]),
            },
        },
        "stakeholders": {
            "count": len(stakeholders),
            "linked_to_users": len([s for s in stakeholders if s.get("linked_user_id")]),
            "by_type": {
                "champion": len([s for s in stakeholders if s.get("stakeholder_type") == "champion"]),
                "sponsor": len([s for s in stakeholders if s.get("stakeholder_type") == "sponsor"]),
                "blocker": len([s for s in stakeholders if s.get("stakeholder_type") == "blocker"]),
                "influencer": len([s for s in stakeholders if s.get("stakeholder_type") == "influencer"]),
                "end_user": len([s for s in stakeholders if s.get("stakeholder_type") == "end_user"]),
            },
        },
        "constraints": {
            "count": len(constraints),
        },
    }
