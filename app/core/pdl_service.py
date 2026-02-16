"""People Data Labs service for company and person enrichment."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PDL_BASE_URL = "https://api.peopledatalabs.com/v5"


def _names_match(input_name: str, returned_name: str) -> bool:
    """Check if a PDL-returned company name plausibly matches the input name.

    Compares significant words (ignoring common suffixes like Inc, LLC, etc.).
    At least one significant word from the input must appear in the returned name.
    """
    skip_words = {
        "the", "inc", "llc", "ltd", "co", "corp", "company", "corporation",
        "group", "and", "of", "for", "international", "global",
    }
    input_words = {w for w in input_name.lower().split() if len(w) > 2 and w not in skip_words}
    returned_words = {w for w in returned_name.lower().split() if len(w) > 2 and w not in skip_words}
    if not input_words:
        return True
    return bool(input_words & returned_words)


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

        # Validate: PDL returned name should resemble the input name
        pdl_name = (data.get("name") or "").lower()
        input_name = (name or "").lower()
        if name and pdl_name and not _names_match(input_name, pdl_name):
            logger.warning(
                f"PDL returned '{data.get('name')}' but we asked for '{name}' — "
                f"possible wrong company match. Discarding PDL result."
            )
            return {}

        # Validate: if we provided a website, PDL website should match domain
        if website:
            pdl_website = (data.get("website") or "").lower()
            input_domain = website.lower().replace("https://", "").replace("http://", "").split("/")[0]
            pdl_domain = pdl_website.replace("https://", "").replace("http://", "").split("/")[0]
            if pdl_domain and input_domain and pdl_domain != input_domain:
                logger.warning(
                    f"PDL returned website '{pdl_website}' but we asked for '{website}' — "
                    f"possible wrong company match. Discarding PDL result."
                )
                return {}

        logger.info(
            f"PDL enriched '{name or website}': "
            f"{result['employee_count'] or '?'} employees, "
            f"industry: {result['industries'] or 'unknown'}"
        )

        return result


# ---------------------------------------------------------------------------
# Person Enrichment (adapted from Forge stakeholder_enrichment module)
# ---------------------------------------------------------------------------


async def enrich_person(
    linkedin_url: str | None = None,
    email: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    Enrich a person using People Data Labs /v5/person/enrich.

    Accepts a LinkedIn URL or email. LinkedIn URL takes priority.

    Args:
        linkedin_url: LinkedIn profile URL
        email: Person's email address
        timeout: Request timeout in seconds

    Returns:
        Dict with job_title, company, industry, skills, experience, education, etc.

    Raises:
        ValueError: If PDL_API_KEY not configured or no identifier provided
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.PDL_API_KEY:
        raise ValueError("PDL_API_KEY not configured")

    if not linkedin_url and not email:
        raise ValueError("Either linkedin_url or email must be provided")

    payload: dict[str, Any] = {}
    if linkedin_url:
        payload["profile"] = linkedin_url
    if email:
        payload["email"] = email

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{PDL_BASE_URL}/person/enrich",
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": settings.PDL_API_KEY,
            },
            json=payload,
        )
        if response.status_code == 404:
            logger.info(f"PDL person not found: {linkedin_url or email}")
            return {}
        response.raise_for_status()

        data = response.json()

        result = {
            "full_name": data.get("full_name"),
            "job_title": data.get("job_title"),
            "job_title_levels": data.get("job_title_levels"),
            "company_name": data.get("job_company_name"),
            "company_industry": data.get("job_company_industry"),
            "company_size": data.get("job_company_size"),
            "location": data.get("location_metro"),
            "skills": (data.get("skills") or [])[:20],
            "experience": (data.get("experience") or [])[:5],
            "education": (data.get("education") or [])[:3],
            "linkedin_url": data.get("linkedin_url"),
            "emails": (data.get("emails") or [])[:3],
            "phone_numbers": (data.get("phone_numbers") or [])[:2],
        }

        identifier = linkedin_url or email
        logger.info(
            f"PDL person enriched '{identifier}': "
            f"{result['job_title'] or '?'} at {result['company_name'] or '?'}"
        )

        return result


async def enrich_person_safe(
    linkedin_url: str | None = None,
    email: str | None = None,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """Enrich a person with error handling — returns None on failure."""
    try:
        result = await enrich_person(linkedin_url, email, timeout)
        return result if result else None
    except ValueError as e:
        logger.warning(f"PDL person not configured or bad input: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"PDL person HTTP error: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"PDL person timeout for '{linkedin_url or email}'")
        return None
    except Exception as e:
        logger.warning(f"PDL person error: {e}")
        return None


# ---------------------------------------------------------------------------
# Company Enrichment (existing)
# ---------------------------------------------------------------------------


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
