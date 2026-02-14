"""Bright Data service for anti-bot web scraping."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BRIGHTDATA_BASE_URL = "https://api.brightdata.com"


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
        ValueError: If BRIGHTDATA_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.BRIGHTDATA_API_KEY:
        raise ValueError("BRIGHTDATA_API_KEY not configured")

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
    """Scrape URL with error handling — returns None on failure."""
    try:
        return await scrape_url(url, timeout)
    except ValueError as e:
        logger.warning(f"Bright Data not configured: {e}")
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
