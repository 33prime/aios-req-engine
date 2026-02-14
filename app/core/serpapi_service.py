"""SerpAPI service for Google search queries."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SERPAPI_BASE_URL = "https://serpapi.com/search"


async def search_google(
    query: str,
    num_results: int = 10,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    """
    Search Google via SerpAPI.

    Args:
        query: Search query string
        num_results: Number of results to return
        timeout: Request timeout in seconds

    Returns:
        List of result dicts with url, title, snippet

    Raises:
        ValueError: If SERPAPI_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.SERPAPI_API_KEY:
        raise ValueError("SERPAPI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            SERPAPI_BASE_URL,
            params={
                "api_key": settings.SERPAPI_API_KEY,
                "q": query,
                "num": num_results,
                "engine": "google",
            },
        )
        response.raise_for_status()

        data = response.json()
        organic = data.get("organic_results", [])

        results = []
        for item in organic[:num_results]:
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0),
            })

        logger.info(f"SerpAPI search '{query[:50]}': {len(results)} results")
        return results


async def search_google_safe(
    query: str,
    num_results: int = 10,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    """Search Google with error handling — returns empty list on failure."""
    try:
        return await search_google(query, num_results, timeout)
    except ValueError as e:
        logger.warning(f"SerpAPI not configured: {e}")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"SerpAPI HTTP error for '{query[:50]}': {e.response.status_code}")
        return []
    except httpx.TimeoutException:
        logger.warning(f"SerpAPI timeout for '{query[:50]}'")
        return []
    except Exception as e:
        logger.warning(f"SerpAPI error for '{query[:50]}': {e}")
        return []
