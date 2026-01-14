"""Firecrawl service for website scraping."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


async def scrape_website(url: str, timeout: int | None = None) -> dict[str, Any]:
    """
    Scrape a website using Firecrawl API.

    Args:
        url: The website URL to scrape
        timeout: Optional timeout override in seconds

    Returns:
        Dict with:
            - markdown: Scraped content as markdown
            - metadata: Page metadata (title, description, etc.)

    Raises:
        ValueError: If FIRECRAWL_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY not configured")

    request_timeout = timeout or settings.FIRECRAWL_TIMEOUT

    async with httpx.AsyncClient(timeout=request_timeout) as client:
        logger.info(f"Scraping website: {url}")

        response = await client.post(
            f"{FIRECRAWL_BASE_URL}/scrape",
            headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}"},
            json={
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,
            }
        )
        response.raise_for_status()

        data = response.json()
        result = {
            "markdown": data.get("data", {}).get("markdown", ""),
            "metadata": data.get("data", {}).get("metadata", {}),
        }

        logger.info(
            f"Scraped {url}: {len(result['markdown'])} chars, "
            f"title: {result['metadata'].get('title', 'N/A')}"
        )

        return result


async def scrape_website_safe(url: str, timeout: int | None = None) -> dict[str, Any] | None:
    """
    Scrape a website with error handling - returns None on failure.

    Use this when scraping is optional and failure should not break the flow.

    Args:
        url: The website URL to scrape
        timeout: Optional timeout override in seconds

    Returns:
        Scrape result dict or None if scraping failed
    """
    try:
        return await scrape_website(url, timeout)
    except ValueError as e:
        logger.warning(f"Firecrawl not configured: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Firecrawl HTTP error for {url}: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"Firecrawl timeout for {url}")
        return None
    except Exception as e:
        logger.warning(f"Firecrawl error for {url}: {e}")
        return None
