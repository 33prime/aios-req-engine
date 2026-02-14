"""Phase 4: Market Evidence — Firecrawl + Haiku extraction from industry reports.

Scrapes market/industry report pages and extracts structured data points.
"""

import asyncio
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_safe

logger = logging.getLogger(__name__)

MARKET_EXTRACTION_PROMPT = """You are extracting market data and statistics from industry report pages.
Extract ONLY facts that appear in the provided text. Do NOT generate statistics.

Return a JSON object:
{{
    "data_points": [
        {{
            "data_type": "statistic|trend|forecast|regulation",
            "content": "The exact finding or data point",
            "source_url": "URL this came from",
            "source_title": "Title of the page/report",
            "confidence": 0.8
        }}
    ]
}}

SCRAPED CONTENT:
{scraped_content}
"""


async def run_market_evidence(
    source_registry: dict[str, list[dict[str, Any]]],
    max_pages: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute Phase 4: Market Evidence.

    Returns:
        Tuple of (market_data_points, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []
    industry_urls = source_registry.get("industry", [])

    if not industry_urls:
        logger.info("No industry URLs found, skipping market evidence phase")
        return [], cost_entries

    # Scrape industry report pages (max 5)
    urls_to_scrape = [src["url"] for src in industry_urls[:max_pages]]
    scrape_tasks = [scrape_website_safe(url) for url in urls_to_scrape]
    scrape_results = await asyncio.gather(*scrape_tasks)

    scraped_parts: list[str] = []
    for url, result in zip(urls_to_scrape, scrape_results):
        if result and result.get("markdown"):
            scraped_parts.append(f"--- Source: {url} ---\n{result['markdown'][:3000]}")
            cost_entries.append({
                "phase": "market_evidence",
                "service": "firecrawl",
                "url": url,
                "cost_usd": 0.01,
            })

    if not scraped_parts:
        logger.warning("No industry pages scraped successfully")
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
                "content": MARKET_EXTRACTION_PROMPT.format(scraped_content=combined),
            }],
        )
        cost_entries.append({
            "phase": "market_evidence",
            "service": "anthropic_haiku",
            "cost_usd": 0.02,
        })

        text = response.content[0].text if response.content else "{}"
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        parsed = json.loads(text.strip())
        data_points = parsed.get("data_points", [])

        logger.info(f"Market evidence complete: {len(data_points)} data points extracted")
        return data_points, cost_entries

    except Exception as e:
        logger.warning(f"Market evidence extraction failed: {e}")
        return [], cost_entries
