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

CLIENT_ENRICHMENT_PROMPT = '''You are a business analyst providing company intelligence for a consulting engagement.

Input Data:
Name: {name}
Website: {website}
Scraped website data:
{scraped_data}

Industry hint: {industry}
Description: {description}

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

    # Mark as in_progress
    update_client_enrichment(client_id, {"enrichment_status": "in_progress"})

    # 1. Scrape website if available
    scraped_data = ""
    enrichment_source = "ai_inference"

    if website:
        logger.info(f"Scraping website: {website}")
        scrape_result = await scrape_website_safe(website)
        if scrape_result:
            scraped_data = scrape_result.get("markdown", "")[:8000]
            enrichment_source = "website_scrape"
            logger.info(f"Scraped {len(scraped_data)} chars from {website}")

    # 2. Build prompt
    prompt = CLIENT_ENRICHMENT_PROMPT.format(
        name=name,
        website=website or "Not provided",
        scraped_data=scraped_data or "Not available - no website provided or scraping failed",
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

    # 5. Store enrichment
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
