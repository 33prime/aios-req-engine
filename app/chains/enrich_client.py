"""
Client Organization Enrichment Chain

Uses Firecrawl for web scraping + Claude Sonnet 4 for enrichment.
Enriches a client entity with company intelligence.
"""

import json
import logging
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_safe
from app.db.clients import get_client, update_client_enrichment

logger = logging.getLogger(__name__)


def _verify_scraped_content(company_name: str, scraped_text: str) -> bool:
    """Check that scraped website content plausibly matches the target company.

    Returns True if ANY significant word from the company name appears in the
    first 2000 chars of scraped content. This catches cases where a scrape
    returns content about a completely different company.
    """
    text_lower = scraped_text[:2000].lower()
    # Split company name into significant words (skip short/common words)
    skip_words = {"the", "inc", "llc", "ltd", "co", "corp", "company", "group", "and", "of", "for"}
    name_words = [
        w for w in company_name.lower().split()
        if len(w) > 2 and w not in skip_words
    ]
    if not name_words:
        return True  # Can't verify, assume OK

    # At least one significant word must appear
    matches = sum(1 for w in name_words if w in text_lower)
    return matches >= 1

CLIENT_ENRICHMENT_PROMPT = '''You are a business analyst providing company intelligence for a consulting engagement.

CRITICAL: You MUST provide intelligence about the SPECIFIC company described below.
Do NOT confuse this company with similarly-named companies.

## Company Identity (GROUND TRUTH — use this to verify all data)
Name: {name}
Website: {website}
Location: {location}
Organization type: {org_type}
Industry hint: {industry}
Description: {description}

## Website Data
{scraped_data}

## Verification Rules
1. If scraped website data is available, base your analysis PRIMARILY on that data.
2. If the scraped data does NOT match the company identity above (wrong industry, wrong name, wrong location), IGNORE the scraped data and note the mismatch.
3. NEVER substitute data from a different company with a similar name.
4. If you cannot find reliable information, return null for that field — do NOT guess or use data from a different company.
5. Include a "verification_status" field: "verified" (data matches company identity), "partial" (some data unverified), "low_confidence" (mostly inferred).

Generate a JSON object with these fields:

1. "company_summary": 2-3 sentence overview of the company, its mission, and what they do.

2. "market_position": 2-3 sentences on where this company sits in the market (leader, challenger, niche player, etc.)

3. "technology_maturity": One of: "legacy", "transitioning", "modern", "cutting_edge"
   Based on their tech stack, website, and digital presence.

4. "digital_readiness": One of: "low", "medium", "high", "advanced"
   Based on how digitally mature their operations appear.

5. "revenue_range": Estimated annual revenue range string, e.g. "$1M-$10M", "$10M-$50M", "$50M-$100M", "$100M-$500M", "$500M+"
   Only if inferable from available data, otherwise null.

6. "employee_count": Estimated number of employees (integer). null if unknown.

7. "founding_year": Year founded (integer). null if unknown.

8. "headquarters": City, State/Country string. null if unknown.

9. "tech_stack": Array of technology/platform strings the company uses or mentions.
   Example: ["React", "AWS", "Salesforce", "SAP"]

10. "growth_signals": Array of objects with:
    - "signal": Description of the growth indicator
    - "type": One of "hiring", "funding", "expansion", "product_launch", "partnership", "other"

11. "competitors": Array of objects with:
    - "name": Competitor company name
    - "relationship": Brief description of competitive relationship

12. "innovation_score": Float 0.0-1.0 rating of how innovative/forward-thinking the company appears.

13. "verification_status": One of "verified", "partial", "low_confidence"

Return ONLY valid JSON. Do not include any explanation or markdown code fences.
'''


async def enrich_client(client_id: UUID) -> dict[str, Any]:
    """
    Enrich a client entity from website + AI inference.

    Args:
        client_id: Client UUID

    Returns:
        Dict with enrichment results and metadata
    """
    settings = get_settings()

    # Get existing client
    client = get_client(client_id)
    if not client:
        logger.warning(f"No client found for id {client_id}")
        return {"success": False, "error": "Client not found"}

    name = client.get("name", "Unknown")
    website = client.get("website")
    industry = client.get("industry")
    description = client.get("description")
    location = client.get("headquarters") or client.get("location") or "Not specified"
    org_type = client.get("org_type") or client.get("organization_type") or "Not specified"

    # Mark as in_progress
    update_client_enrichment(client_id, {"enrichment_status": "in_progress"})

    # 1. Scrape website if available
    scraped_data = ""
    enrichment_source = "ai_inference"

    if website:
        logger.info(f"Scraping website: {website}")
        scrape_result = await scrape_website_safe(website)
        if scrape_result:
            raw_scraped = scrape_result.get("markdown", "")[:8000]
            # Verify scraped content is about the right company
            if raw_scraped and _verify_scraped_content(name, raw_scraped):
                scraped_data = raw_scraped
                enrichment_source = "website_scrape"
                logger.info(f"Scraped {len(scraped_data)} chars from {website} (verified)")
            elif raw_scraped:
                logger.warning(
                    f"Scraped content from {website} does NOT appear to match client '{name}' — discarding"
                )
                scraped_data = ""
                enrichment_source = "ai_inference"

    # 2. Build prompt with disambiguation context
    prompt = CLIENT_ENRICHMENT_PROMPT.format(
        name=name,
        website=website or "Not provided",
        location=location,
        org_type=org_type,
        scraped_data=scraped_data or "Not available - no website provided or scraping failed. Use ONLY the company identity above. Do NOT substitute data from a similarly-named company.",
        industry=industry or "Not specified",
        description=description or "Not provided",
    )

    # 3. Get enrichment via Claude Sonnet 4
    logger.info(f"Running enrichment inference for client {name}")
    client_ai = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client_ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text if response.content else ""
    except Exception as e:
        logger.error(f"AI enrichment failed for client {client_id}: {e}")
        update_client_enrichment(client_id, {"enrichment_status": "failed"})
        return {"success": False, "error": str(e)}

    # 4. Parse JSON response
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        enrichment = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse enrichment response: {e}")
        update_client_enrichment(client_id, {"enrichment_status": "failed"})
        return {"success": False, "error": f"JSON parse error: {e}"}

    # 5. Verify enrichment matches the target company
    verification_status = enrichment.get("verification_status", "partial")
    if verification_status == "low_confidence":
        logger.warning(
            f"Enrichment returned low_confidence for client '{name}' — "
            f"summary: {enrichment.get('company_summary', '')[:100]}"
        )

    # Cross-check: if the summary mentions a completely different company, reject
    summary = enrichment.get("company_summary", "") or ""
    if summary and not _verify_scraped_content(name, summary):
        logger.error(
            f"Enrichment summary does NOT mention '{name}' — likely wrong company. "
            f"Summary: {summary[:200]}"
        )
        update_client_enrichment(client_id, {"enrichment_status": "failed"})
        return {
            "success": False,
            "error": f"Enrichment returned data for wrong company. Summary: {summary[:200]}",
        }

    # 6. Store enrichment
    enrichment_data = {
        "company_summary": enrichment.get("company_summary"),
        "market_position": enrichment.get("market_position"),
        "technology_maturity": enrichment.get("technology_maturity"),
        "digital_readiness": enrichment.get("digital_readiness"),
        "revenue_range": enrichment.get("revenue_range"),
        "employee_count": enrichment.get("employee_count"),
        "founding_year": enrichment.get("founding_year"),
        "headquarters": enrichment.get("headquarters"),
        "tech_stack": enrichment.get("tech_stack", []),
        "growth_signals": enrichment.get("growth_signals", []),
        "competitors": enrichment.get("competitors", []),
        "innovation_score": enrichment.get("innovation_score"),
        "enrichment_status": "completed",
        "enriched_at": "now()",
        "enrichment_source": enrichment_source,
    }

    update_client_enrichment(client_id, enrichment_data)

    logger.info(f"Client enrichment complete for {client_id}")

    return {
        "success": True,
        "enrichment_source": enrichment_source,
        "scraped_chars": len(scraped_data) if scraped_data else 0,
        "fields_enriched": list(enrichment.keys()),
    }
