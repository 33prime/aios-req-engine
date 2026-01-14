"""CRUD operations for company_info entity."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_company_info(project_id: UUID) -> dict[str, Any] | None:
    """
    Get company info for a project (one-to-one relationship).

    Args:
        project_id: Project UUID

    Returns:
        Company info dict or None if not set
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("company_info")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )
        return response.data if response else None
    except Exception as e:
        logger.error(f"Error getting company info for project {project_id}: {e}")
        return None


def upsert_company_info(
    project_id: UUID,
    name: str,
    industry: str | None = None,
    stage: str | None = None,
    size: str | None = None,
    website: str | None = None,
    description: str | None = None,
    key_differentiators: list[str] | None = None,
    source_signal_id: UUID | None = None,
    revision_id: UUID | None = None,
    company_type: str | None = None,
    revenue: str | None = None,
    address: str | None = None,
    location: str | None = None,
    employee_count: str | None = None,
) -> dict[str, Any]:
    """
    Create or update company info for a project.

    Args:
        project_id: Project UUID
        name: Company name
        industry: Industry category
        stage: Company stage (Startup, Growth, Enterprise)
        size: Company size range
        website: Company website URL
        description: Company description
        key_differentiators: List of differentiators
        source_signal_id: Signal this was extracted from
        revision_id: Revision tracking ID
        company_type: Company type (SMB, Enterprise, etc.)
        revenue: Revenue range
        address: Physical address
        location: City, State, Country
        employee_count: Number of employees

    Returns:
        Created/updated company info dict
    """
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "name": name,
    }

    if industry is not None:
        data["industry"] = industry
    if stage is not None:
        data["stage"] = stage
    if size is not None:
        data["size"] = size
    if website is not None:
        data["website"] = website
    if description is not None:
        data["description"] = description
    if key_differentiators is not None:
        data["key_differentiators"] = key_differentiators
    if source_signal_id is not None:
        data["source_signal_id"] = str(source_signal_id)
    if revision_id is not None:
        data["revision_id"] = str(revision_id)
    if company_type is not None:
        data["company_type"] = company_type
    if revenue is not None:
        data["revenue"] = revenue
    if address is not None:
        data["address"] = address
    if location is not None:
        data["location"] = location
    if employee_count is not None:
        data["employee_count"] = employee_count

    response = (
        supabase.table("company_info")
        .upsert(data, on_conflict="project_id")
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Upserted company info for project {project_id}")
    return response.data[0] if response.data else data


def update_company_enrichment(
    project_id: UUID,
    unique_selling_point: str | None = None,
    customers: str | None = None,
    products_services: str | None = None,
    industry_overview: str | None = None,
    industry_trends: str | None = None,
    fast_facts: str | None = None,
    company_type: str | None = None,
    industry_display: str | None = None,
    industry_naics: str | None = None,
    data_dictionary: dict[str, Any] | None = None,
    industry_use_cases: list[dict[str, Any]] | None = None,
    enrichment_source: str | None = None,
    enrichment_confidence: float | None = None,
    raw_website_content: str | None = None,
) -> dict[str, Any] | None:
    """
    Update enrichment fields for company info.

    Args:
        project_id: Project UUID
        unique_selling_point: Core value proposition
        customers: HTML describing target customers
        products_services: HTML describing offerings
        industry_overview: HTML industry context
        industry_trends: HTML current trends
        fast_facts: HTML key market facts
        company_type: Startup, SMB, Enterprise, etc.
        industry_display: Formatted industry string
        industry_naics: NAICS classification
        data_dictionary: Vocabulary context dict
        industry_use_cases: Common use cases
        enrichment_source: website_scrape, ai_inference, etc.
        enrichment_confidence: Confidence score 0-1
        raw_website_content: Cached scraped markdown

    Returns:
        Updated company info dict or None if not found
    """
    supabase = get_supabase()

    # Build update data
    data: dict[str, Any] = {"enriched_at": "now()"}

    if unique_selling_point is not None:
        data["unique_selling_point"] = unique_selling_point
    if customers is not None:
        data["customers"] = customers
    if products_services is not None:
        data["products_services"] = products_services
    if industry_overview is not None:
        data["industry_overview"] = industry_overview
    if industry_trends is not None:
        data["industry_trends"] = industry_trends
    if fast_facts is not None:
        data["fast_facts"] = fast_facts
    if company_type is not None:
        data["company_type"] = company_type
    if industry_display is not None:
        data["industry_display"] = industry_display
    if industry_naics is not None:
        data["industry_naics"] = industry_naics
    if data_dictionary is not None:
        data["data_dictionary"] = data_dictionary
    if industry_use_cases is not None:
        data["industry_use_cases"] = industry_use_cases
    if enrichment_source is not None:
        data["enrichment_source"] = enrichment_source
    if enrichment_confidence is not None:
        data["enrichment_confidence"] = enrichment_confidence
    if raw_website_content is not None:
        data["raw_website_content"] = raw_website_content

    response = (
        supabase.table("company_info")
        .update(data)
        .eq("project_id", str(project_id))
        .execute()
    )

    if not response.data:
        logger.warning(f"No company info found for project {project_id}")
        return None

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Updated company enrichment for project {project_id}")
    return response.data[0]


def delete_company_info(project_id: UUID) -> bool:
    """
    Delete company info for a project.

    Args:
        project_id: Project UUID

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("company_info")
        .delete()
        .eq("project_id", str(project_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return bool(response.data)
