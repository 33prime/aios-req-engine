"""Bright Data service for anti-bot web scraping.

Requires a Web Unlocker zone to be created in the Bright Data dashboard.
Set BRIGHTDATA_ZONE in .env to match the zone name (default: web_unlocker1).
If BRIGHTDATA_API_KEY or BRIGHTDATA_ZONE is empty, scrape_url_safe() returns None
and the discovery pipeline falls back to Firecrawl.
"""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BRIGHTDATA_BASE_URL = "https://api.brightdata.com"

# Log once per process to avoid spam
_zone_warning_logged = False


def _is_configured() -> bool:
    """Check if Bright Data is fully configured (API key + zone)."""
    settings = get_settings()
    return bool(settings.BRIGHTDATA_API_KEY and settings.BRIGHTDATA_ZONE)


async def scrape_url(
    url: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Scrape a URL using Bright Data Web Unlocker API.

    Best for anti-bot protected sites (G2, Capterra, Reddit).

    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds

    Returns:
        Dict with html content and status

    Raises:
        ValueError: If Bright Data is not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.BRIGHTDATA_API_KEY:
        raise ValueError("BRIGHTDATA_API_KEY not configured")
    if not settings.BRIGHTDATA_ZONE:
        raise ValueError(
            "BRIGHTDATA_ZONE not configured — create a Web Unlocker zone "
            "at https://brightdata.com/cp/start and set BRIGHTDATA_ZONE in .env"
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{BRIGHTDATA_BASE_URL}/request",
            headers={
                "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "zone": settings.BRIGHTDATA_ZONE,
                "url": url,
                "format": "raw",
            },
        )
        # Log response body on error for debugging
        if response.status_code >= 400:
            body = response.text[:200]
            if "not found" in body.lower():
                raise ValueError(
                    f"Bright Data zone '{settings.BRIGHTDATA_ZONE}' not found — "
                    "create it at https://brightdata.com/cp/start"
                )
            response.raise_for_status()

        result = {
            "html": response.text,
            "status_code": response.status_code,
            "url": url,
        }

        logger.info(f"Bright Data scraped {url}: {len(result['html'])} chars")
        return result


async def scrape_url_safe(
    url: str,
    timeout: int = 30,
) -> dict[str, Any] | None:
    """Scrape URL with error handling — returns None on failure.

    Returns None immediately if Bright Data is not configured (no API key or zone).
    """
    global _zone_warning_logged

    if not _is_configured():
        if not _zone_warning_logged:
            logger.info(
                "Bright Data not configured (missing API key or zone) — "
                "skipping, will use Firecrawl fallback"
            )
            _zone_warning_logged = True
        return None

    try:
        return await scrape_url(url, timeout)
    except ValueError as e:
        if not _zone_warning_logged:
            logger.warning(f"Bright Data config issue: {e}")
            _zone_warning_logged = True
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Bright Data HTTP error for {url}: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"Bright Data timeout for {url}")
        return None
    except Exception as e:
        logger.warning(f"Bright Data error for {url}: {e}")
        return None
