"""People Data Labs service for company enrichment."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PDL_BASE_URL = "https://api.peopledatalabs.com/v5"


async def enrich_company(
    name: str | None = None,
    website: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    Enrich a company using People Data Labs.

    Args:
        name: Company name
        website: Company website URL
        timeout: Request timeout in seconds

    Returns:
        Dict with employee_count, revenue_range, funding, tech_stack, industries, etc.

    Raises:
        ValueError: If PDL_API_KEY not configured or no identifier provided
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.PDL_API_KEY:
        raise ValueError("PDL_API_KEY not configured")

    if not name and not website:
        raise ValueError("Either name or website must be provided")

    params: dict[str, str] = {}
    if name:
        params["name"] = name
    if website:
        params["website"] = website

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{PDL_BASE_URL}/company/enrich",
            headers={"X-Api-Key": settings.PDL_API_KEY},
            params=params,
        )
        response.raise_for_status()

        data = response.json()

        result = {
            "name": data.get("name", name),
            "website": data.get("website", website),
            "employee_count": data.get("employee_count"),
            "employee_count_range": data.get("employee_count_range"),
            "revenue_range": data.get("inferred_revenue"),
            "funding_total": data.get("total_funding_raised"),
            "funding_last_round": data.get("latest_funding_stage"),
            "founded_year": data.get("founded"),
            "industries": data.get("industry"),
            "tags": data.get("tags", []),
            "tech_stack": data.get("tech", []),
            "location": data.get("location", {}),
            "linkedin_url": data.get("linkedin_url"),
            "summary": data.get("summary"),
        }

        logger.info(
            f"PDL enriched '{name or website}': "
            f"{result['employee_count'] or '?'} employees, "
            f"industry: {result['industries'] or 'unknown'}"
        )

        return result


async def enrich_company_safe(
    name: str | None = None,
    website: str | None = None,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """Enrich company with error handling — returns None on failure."""
    try:
        return await enrich_company(name, website, timeout)
    except ValueError as e:
        logger.warning(f"PDL not configured or bad input: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"PDL HTTP error for '{name or website}': {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"PDL timeout for '{name or website}'")
        return None
    except Exception as e:
        logger.warning(f"PDL error for '{name or website}': {e}")
        return None
