"""Phase 2: Company Intelligence — PDL enrichment + Firecrawl scraping + Haiku extraction.

Builds a structured company profile from real data sources.
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
    """Robustly parse JSON from an LLM response, handling code blocks and raw JSON."""
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        pass

    # Fallback: find first { ... } block
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from LLM response ({context})")
    return {}

COMPANY_EXTRACTION_PROMPT = """You are extracting structured company information from scraped web pages.
Extract ONLY facts that appear in the provided text. Do NOT generate or infer information.

For each fact, note the source URL it came from.

Return a JSON object with these fields (use null for anything not found):
{{
    "tagline": "Company's tagline or value prop",
    "description": "What the company does (1-2 sentences)",
    "target_market": "Who they sell to",
    "key_products": ["product1", "product2"],
    "pricing_model": "How they charge (freemium, subscription, etc.)",
    "pricing_tiers": ["tier1: $X/mo", "tier2: $Y/mo"],
    "tech_mentions": ["technology1", "technology2"],
    "evidence": [
        {{"source_url": "...", "quote": "exact quote from text", "source_type": "firecrawl"}}
    ]
}}

SCRAPED CONTENT:
{scraped_content}
"""


async def _extract_with_haiku(scraped_content: str, cost_entries: list[dict]) -> dict[str, Any]:
    """Use Haiku to extract structured company info from scraped text."""
    from anthropic import AsyncAnthropic

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return {}

    # Truncate to fit context
    content = scraped_content[:12000]

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": COMPANY_EXTRACTION_PROMPT.format(scraped_content=content),
        }],
    )

    cost_entries.append({
        "phase": "company_intel",
        "service": "anthropic_haiku",
        "cost_usd": 0.02,
    })

    text = response.content[0].text if response.content else "{}"
    return _parse_json_response(text, "company extraction")


async def run_company_intelligence(
    company_name: str,
    company_website: str | None,
    source_registry: dict[str, list[dict[str, Any]]],
    existing_company_info: dict[str, Any] | None = None,
    skip_pdl: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute Phase 2: Company Intelligence.

    Args:
        existing_company_info: If provided, used to seed profile (skip PDL).
        skip_pdl: If True, skip $0.03 PDL call and use existing_company_info.

    Returns:
        Tuple of (company_profile, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []
    company_profile: dict[str, Any] = {"name": company_name}

    # 1. PDL enrichment (or reuse existing)
    if skip_pdl and existing_company_info:
        logger.info("Skipping PDL — using existing company info")
        company_profile.update({
            "employee_count": existing_company_info.get("employee_count"),
            "employee_count_range": existing_company_info.get("employee_count_range"),
            "revenue_range": existing_company_info.get("revenue_range"),
            "funding_total": existing_company_info.get("funding_total"),
            "funding_last_round": existing_company_info.get("funding_last_round"),
            "founded_year": existing_company_info.get("founded_year"),
            "industries": existing_company_info.get("industries"),
            "tech_stack": existing_company_info.get("tech_stack", []),
            "linkedin_url": existing_company_info.get("linkedin_url"),
        })
        if not company_website:
            company_website = existing_company_info.get("website")
    else:
        pdl_data = await enrich_company_safe(
            name=company_name,
            website=company_website,
        )
        if pdl_data:
            company_profile.update({
                "employee_count": pdl_data.get("employee_count"),
                "employee_count_range": pdl_data.get("employee_count_range"),
                "revenue_range": pdl_data.get("revenue_range"),
                "funding_total": pdl_data.get("funding_total"),
                "funding_last_round": pdl_data.get("funding_last_round"),
                "founded_year": pdl_data.get("founded_year"),
                "industries": pdl_data.get("industries"),
                "tech_stack": pdl_data.get("tech_stack", []),
                "linkedin_url": pdl_data.get("linkedin_url"),
            })
            cost_entries.append({
                "phase": "company_intel",
                "service": "pdl",
                "cost_usd": 0.03,
            })

    # 2. Firecrawl scrape (homepage + about + pricing from source_registry)
    company_urls = source_registry.get("company", [])
    scrape_urls = []

    # Always try the company website
    if company_website:
        scrape_urls.append(company_website)

    # Add top source_registry company URLs (max 3 total)
    for src in company_urls[:3]:
        if src["url"] not in scrape_urls:
            scrape_urls.append(src["url"])
            if len(scrape_urls) >= 3:
                break

    scrape_tasks = [scrape_website_safe(url) for url in scrape_urls[:3]]
    scrape_results = await asyncio.gather(*scrape_tasks)

    scraped_content_parts = []
    for url, result in zip(scrape_urls, scrape_results):
        if result and result.get("markdown"):
            scraped_content_parts.append(
                f"--- Source: {url} ---\n{result['markdown'][:4000]}"
            )
            cost_entries.append({
                "phase": "company_intel",
                "service": "firecrawl",
                "url": url,
                "cost_usd": 0.01,
            })

    # 3. Haiku extraction from scraped content
    if scraped_content_parts:
        combined = "\n\n".join(scraped_content_parts)
        extracted = await _extract_with_haiku(combined, cost_entries)
        if extracted:
            company_profile["tagline"] = extracted.get("tagline")
            company_profile["description"] = extracted.get("description")
            company_profile["target_market"] = extracted.get("target_market")
            company_profile["key_products"] = extracted.get("key_products", [])
            company_profile["pricing_model"] = extracted.get("pricing_model")
            company_profile["pricing_tiers"] = extracted.get("pricing_tiers", [])
            company_profile["evidence"] = extracted.get("evidence", [])

    # 4. Verify extracted profile matches the target company
    desc = company_profile.get("description") or ""
    if desc and not _verify_company_match(company_name, desc):
        logger.warning(
            f"Company profile description does NOT match '{company_name}': {desc[:200]}. "
            f"Clearing unreliable fields."
        )
        # Keep only PDL structural data (employee count etc.), clear narrative fields
        company_profile.pop("description", None)
        company_profile.pop("tagline", None)
        company_profile.pop("target_market", None)
        company_profile.pop("key_products", None)
        company_profile.pop("pricing_model", None)
        company_profile.pop("pricing_tiers", None)

    logger.info(
        f"Company intelligence complete for '{company_name}': "
        f"{company_profile.get('employee_count', '?')} employees"
    )

    return company_profile, cost_entries


def _verify_company_match(company_name: str, text: str) -> bool:
    """Check that extracted text plausibly describes the target company."""
    text_lower = text[:500].lower()
    skip_words = {"the", "inc", "llc", "ltd", "co", "corp", "company", "group", "and", "of", "for"}
    name_words = [
        w for w in company_name.lower().split()
        if len(w) > 2 and w not in skip_words
    ]
    if not name_words:
        return True
    return any(w in text_lower for w in name_words)
