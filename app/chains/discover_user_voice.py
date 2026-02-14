"""Phase 5: User Voice — Bright Data + Firecrawl fallback + Haiku extraction.

Scrapes review sites and forums, extracts pain points and quotes.
"""

import asyncio
import json
import logging
import re
from typing import Any

from app.core.brightdata_service import scrape_url_safe
from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_safe

logger = logging.getLogger(__name__)

USER_VOICE_EXTRACTION_PROMPT = """You are extracting user reviews, pain points, and opinions from web pages.
Extract ONLY real quotes and sentiments from the provided text. Never fabricate reviews.

Return a JSON object:
{{
    "items": [
        {{
            "content": "The actual review or comment text",
            "source_url": "URL this came from",
            "source_type": "g2_review|capterra|reddit|forum",
            "sentiment": "positive|negative|neutral",
            "pain_point": "Brief description of pain if negative sentiment, else null",
            "confidence": 0.8
        }}
    ]
}}

SCRAPED CONTENT:
{scraped_content}
"""


async def _scrape_with_fallback(
    url: str,
    cost_entries: list[dict[str, Any]],
) -> str | None:
    """Try Bright Data first, then Firecrawl, return markdown content."""
    # Try Bright Data for anti-bot sites
    bd_result = await scrape_url_safe(url)
    if bd_result and bd_result.get("html"):
        cost_entries.append({
            "phase": "user_voice",
            "service": "brightdata",
            "url": url,
            "cost_usd": 0.01,
        })
        # Basic HTML to text (strip tags)
        html = bd_result["html"]
        # Simple tag stripping for review extraction
        import re
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:4000] if text else None

    # Fallback: Firecrawl
    fc_result = await scrape_website_safe(url)
    if fc_result and fc_result.get("markdown"):
        cost_entries.append({
            "phase": "user_voice",
            "service": "firecrawl",
            "url": url,
            "cost_usd": 0.01,
        })
        return fc_result["markdown"][:4000]

    return None


async def run_user_voice(
    source_registry: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute Phase 5: User Voice.

    Returns:
        Tuple of (user_voice_items, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []

    # Collect review + forum URLs
    urls_to_scrape: list[tuple[str, str]] = []  # (url, source_type)

    for src in source_registry.get("review", [])[:5]:
        urls_to_scrape.append((src["url"], "review"))

    for src in source_registry.get("forum", [])[:3]:
        urls_to_scrape.append((src["url"], "forum"))

    if not urls_to_scrape:
        logger.info("No review/forum URLs found, skipping user voice phase")
        return [], cost_entries

    # Scrape all URLs concurrently
    async def scrape_one(url_type: tuple[str, str]) -> tuple[str, str | None]:
        url, stype = url_type
        content = await _scrape_with_fallback(url, cost_entries)
        if content:
            return f"--- Source: {url} (type: {stype}) ---\n{content}", url
        return "", ""

    tasks = [scrape_one(ut) for ut in urls_to_scrape]
    results = await asyncio.gather(*tasks)

    scraped_parts = [r[0] for r in results if r[0]]

    if not scraped_parts:
        logger.warning("No review/forum pages scraped successfully")
        return [], cost_entries

    # Haiku extraction
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return [], cost_entries

    from anthropic import AsyncAnthropic

    combined = "\n\n".join(scraped_parts)[:12000]
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": USER_VOICE_EXTRACTION_PROMPT.format(scraped_content=combined),
            }],
        )
        cost_entries.append({
            "phase": "user_voice",
            "service": "anthropic_haiku",
            "cost_usd": 0.02,
        })

        text = response.content[0].text if response.content else "{}"
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            parsed = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            match = re.search(r'\{[\s\S]*\}', text)
            parsed = json.loads(match.group()) if match else {}
        items = parsed.get("items", [])

        logger.info(f"User voice complete: {len(items)} items extracted")
        return items, cost_entries

    except Exception as e:
        logger.warning(f"User voice extraction failed: {e}")
        return [], cost_entries
