"""Phase 3: Competitor Intelligence — PDL + Firecrawl + Haiku per competitor.

Profiles up to N competitors with real firmographic and scraped data.
"""

import asyncio
import json
import logging
import re
from typing import Any

from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_safe
from app.core.pdl_service import enrich_company_safe

logger = logging.getLogger(__name__)


def _parse_json_response(text: str, context: str = "") -> dict[str, Any]:
    """Robustly parse JSON from an LLM response."""
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.warning(f"Failed to parse JSON from LLM response ({context})")
    return {}

COMPETITOR_EXTRACTION_PROMPT = """You are extracting competitor information from scraped web pages.
Extract ONLY facts that appear in the provided text. Never fabricate information.

Return a JSON object:
{{
    "name": "Competitor name",
    "tagline": "Their value prop",
    "key_features": ["feature1", "feature2", "feature3"],
    "pricing_tiers": ["Free: ...", "Pro: $X/mo", "Enterprise: custom"],
    "target_market": "Who they sell to",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1 (from reviews or comparisons)"],
    "evidence": [
        {{"source_url": "...", "quote": "exact quote", "source_type": "firecrawl"}}
    ]
}}

COMPETITOR NAME: {competitor_name}
SCRAPED CONTENT:
{scraped_content}
"""


def _extract_competitor_names(source_registry: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Extract competitor names from search result titles/snippets."""
    competitor_sources = source_registry.get("competitor", [])
    names: list[str] = []
    seen: set[str] = set()

    for src in competitor_sources:
        title = src.get("title", "")
        snippet = src.get("snippet", "")

        # Look for "vs" patterns: "CompanyA vs CompanyB"
        for text in [title, snippet]:
            if " vs " in text.lower():
                parts = text.lower().split(" vs ")
                for part in parts:
                    # Clean up the name
                    name = part.strip().split(":")[0].split("-")[0].split("(")[0].strip()
                    name = " ".join(w.capitalize() for w in name.split()[:3])
                    if name and len(name) > 2 and name.lower() not in seen:
                        seen.add(name.lower())
                        names.append(name)

        # Look for "alternatives" or "competitors" lists in snippets
        for keyword in ["alternative", "competitor"]:
            if keyword in snippet.lower():
                # Simple extraction of capitalized words after the keyword
                words = snippet.split()
                for i, w in enumerate(words):
                    if keyword in w.lower() and i + 1 < len(words):
                        for j in range(i + 1, min(i + 8, len(words))):
                            candidate = words[j].strip(".,;:()")
                            if candidate and candidate[0].isupper() and len(candidate) > 2:
                                if candidate.lower() not in seen:
                                    seen.add(candidate.lower())
                                    names.append(candidate)

    return names[:10]  # Return up to 10 candidates


async def _profile_one_competitor(
    name: str,
    source_registry: dict[str, list[dict[str, Any]]],
    cost_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Profile a single competitor with PDL + Firecrawl + Haiku."""
    settings = get_settings()
    profile: dict[str, Any] = {"name": name}

    # 1. PDL enrichment
    pdl = await enrich_company_safe(name=name)
    if pdl:
        profile.update({
            "website": pdl.get("website"),
            "employee_count": pdl.get("employee_count"),
            "revenue_range": pdl.get("revenue_range"),
            "funding": pdl.get("funding_total"),
        })
        cost_entries.append({
            "phase": "competitor_intel",
            "service": "pdl",
            "competitor": name,
            "cost_usd": 0.03,
        })

    # 2. Firecrawl scrape (homepage + any matching URLs from registry)
    scrape_urls: list[str] = []
    if pdl and pdl.get("website"):
        scrape_urls.append(pdl["website"])

    # Find matching URLs in source_registry
    name_lower = name.lower()
    for cat in ["competitor", "company", "review"]:
        for src in source_registry.get(cat, []):
            if name_lower in src.get("title", "").lower() or name_lower in src.get("url", "").lower():
                if src["url"] not in scrape_urls:
                    scrape_urls.append(src["url"])
                    if len(scrape_urls) >= 2:
                        break

    scraped_parts = []
    if scrape_urls:
        tasks = [scrape_website_safe(url) for url in scrape_urls[:2]]
        results = await asyncio.gather(*tasks)
        for url, result in zip(scrape_urls, results):
            if result and result.get("markdown"):
                scraped_parts.append(f"--- Source: {url} ---\n{result['markdown'][:4000]}")
                cost_entries.append({
                    "phase": "competitor_intel",
                    "service": "firecrawl",
                    "competitor": name,
                    "url": url,
                    "cost_usd": 0.01,
                })

    # 3. Haiku extraction
    if scraped_parts and settings.ANTHROPIC_API_KEY:
        from anthropic import AsyncAnthropic

        combined = "\n\n".join(scraped_parts)[:12000]
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        try:
            response = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": COMPETITOR_EXTRACTION_PROMPT.format(
                        competitor_name=name,
                        scraped_content=combined,
                    ),
                }],
            )
            cost_entries.append({
                "phase": "competitor_intel",
                "service": "anthropic_haiku",
                "competitor": name,
                "cost_usd": 0.015,
            })

            text = response.content[0].text if response.content else "{}"
            extracted = _parse_json_response(text, f"competitor {name}")
            profile.update({
                "key_features": extracted.get("key_features", []),
                "pricing_tiers": extracted.get("pricing_tiers", []),
                "target_market": extracted.get("target_market"),
                "strengths": extracted.get("strengths", []),
                "weaknesses": extracted.get("weaknesses", []),
                "evidence": extracted.get("evidence", []),
            })
        except Exception as e:
            logger.warning(f"Haiku extraction failed for competitor {name}: {e}")

    # Only return if we got meaningful data
    if profile.get("employee_count") or profile.get("key_features"):
        return profile
    return None


async def run_competitor_intelligence(
    company_name: str,
    source_registry: dict[str, list[dict[str, Any]]],
    max_competitors: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute Phase 3: Competitor Intelligence.

    Returns:
        Tuple of (competitors, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []

    # Extract competitor names from search results
    candidate_names = _extract_competitor_names(source_registry)

    # Filter out the company itself
    company_lower = company_name.lower()
    candidate_names = [n for n in candidate_names if company_lower not in n.lower()]
    candidate_names = candidate_names[:max_competitors]

    if not candidate_names:
        logger.warning("No competitor names found from source mapping")
        return [], cost_entries

    logger.info(f"Profiling {len(candidate_names)} competitors: {candidate_names}")

    # Profile competitors concurrently (but cap at max_competitors)
    tasks = [
        _profile_one_competitor(name, source_registry, cost_entries)
        for name in candidate_names
    ]
    results = await asyncio.gather(*tasks)

    competitors = [r for r in results if r is not None]

    logger.info(f"Competitor intelligence complete: {len(competitors)} profiled")
    return competitors, cost_entries
