"""Bright Data service for anti-bot web scraping.

Requires a Web Unlocker zone to be created in the Bright Data dashboard.
Set BRIGHTDATA_ZONE in .env to match the zone name (default: web_unlocker1).
If BRIGHTDATA_API_KEY or BRIGHTDATA_ZONE is empty, scrape_url_safe() returns None
and the discovery pipeline falls back to Firecrawl.
"""

import asyncio
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


# ---------------------------------------------------------------------------
# LinkedIn Profile Scraper (adapted from Forge stakeholder_enrichment module)
# ---------------------------------------------------------------------------

# BrightData LinkedIn People dataset ID
_LINKEDIN_DATASET_ID = "gd_l1viktl72bvl7bjuj0"


async def scrape_linkedin_profile(
    linkedin_url: str,
    timeout: int = 120,
    poll_interval: int = 5,
) -> dict[str, Any]:
    """
    Scrape a LinkedIn profile using Bright Data's dataset API.

    Uses trigger+poll pattern: POST to start scrape, then poll snapshot.
    Gotchas from Forge module:
    - BD uses 'position' (not 'headline'), 'followers' (not 'followers_count')
    - Posts have 'title' + 'attribution' (not 'text')

    Args:
        linkedin_url: Full LinkedIn profile URL
        timeout: Max time to wait for results (seconds)
        poll_interval: Seconds between poll attempts

    Returns:
        Parsed profile dict with headline, about, posts, experience, etc.

    Raises:
        ValueError: If Bright Data not configured
        RuntimeError: If scrape fails or times out
    """
    settings = get_settings()

    if not settings.BRIGHTDATA_API_KEY:
        raise ValueError("BRIGHTDATA_API_KEY not configured")

    auth_headers = {
        "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Trigger the scrape
        trigger_res = await client.post(
            f"{BRIGHTDATA_BASE_URL}/datasets/v3/trigger",
            params={"dataset_id": _LINKEDIN_DATASET_ID, "include_errors": "true"},
            headers=auth_headers,
            json=[{"url": linkedin_url}],
        )
        if trigger_res.status_code != 200:
            raise RuntimeError(
                f"Bright Data LinkedIn trigger error {trigger_res.status_code}: {trigger_res.text}"
            )

        snapshot_id = trigger_res.json().get("snapshot_id")
        if not snapshot_id:
            raise RuntimeError(
                f"Bright Data: no snapshot_id returned: {trigger_res.text}"
            )

        logger.info(f"Bright Data LinkedIn scrape started: {snapshot_id}")

        # 2. Poll for results
        max_attempts = timeout // poll_interval
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            poll_res = await client.get(
                f"{BRIGHTDATA_BASE_URL}/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers={"Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}"},
                timeout=15,
            )
            if poll_res.status_code == 200:
                results = poll_res.json()
                if isinstance(results, list) and len(results) > 0:
                    profile = results[0]
                    if profile.get("error"):
                        raise RuntimeError(
                            f"Bright Data profile error: {profile.get('error')}"
                        )
                    logger.info(
                        f"Bright Data LinkedIn scrape complete after {(attempt + 1) * poll_interval}s"
                    )
                    return _parse_linkedin_profile(profile)
            elif poll_res.status_code != 202:
                raise RuntimeError(
                    f"Bright Data poll error {poll_res.status_code}: {poll_res.text}"
                )

        raise RuntimeError(
            f"Bright Data: timed out waiting for LinkedIn scrape ({timeout}s)"
        )


def _parse_linkedin_profile(profile: dict) -> dict[str, Any]:
    """Extract structured fields from raw Bright Data LinkedIn response."""
    headline = profile.get("position") or profile.get("headline")

    raw_posts = (profile.get("posts") or [])[:5]
    posts = []
    for p in raw_posts:
        if isinstance(p, dict):
            text = p.get("title", "")
            if p.get("attribution"):
                text += f" — {p['attribution']}"
            posts.append({
                "text": text,
                "link": p.get("link"),
                "created_at": p.get("created_at"),
                "interaction": p.get("interaction"),
            })

    return {
        "headline": headline,
        "about": profile.get("about"),
        "name": profile.get("name"),
        "posts": posts,
        "recommendations": profile.get("recommendations"),
        "certifications": profile.get("honors_and_awards"),
        "follower_count": profile.get("followers"),
        "connections": profile.get("connections"),
        "experience": profile.get("experience"),
        "education": profile.get("education"),
        "current_company": profile.get("current_company"),
        "activity": (profile.get("activity") or [])[:5],
    }


async def scrape_linkedin_profile_safe(
    linkedin_url: str,
    timeout: int = 120,
) -> dict[str, Any] | None:
    """Scrape LinkedIn profile with error handling — returns None on failure."""
    if not _is_configured():
        logger.info("Bright Data not configured — skipping LinkedIn scrape")
        return None

    try:
        return await scrape_linkedin_profile(linkedin_url, timeout)
    except ValueError as e:
        logger.warning(f"Bright Data LinkedIn config issue: {e}")
        return None
    except RuntimeError as e:
        logger.warning(f"Bright Data LinkedIn scrape failed: {e}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"Bright Data LinkedIn timeout for {linkedin_url}")
        return None
    except Exception as e:
        logger.warning(f"Bright Data LinkedIn error: {e}")
        return None
