"""
Company Enrichment Chain

Uses Firecrawl for web scraping + Claude Sonnet 4 for enrichment.
This is pre-research enrichment - fast (~5-10 seconds), not deep.
"""

import json
import logging
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_safe
from app.db.company_info import get_company_info, update_company_enrichment

logger = logging.getLogger(__name__)

COMPANY_ENRICHMENT_PROMPT = '''You are a business analyst providing quick company analysis.

Input Data:
Name: {name}
Website: {website}
Scraped website data:
{scraped_data}

Industry hint: {industry}
Description: {description}

Generate a JSON object with these fields:

1. "unique_selling_point": 2 sentences describing core value proposition

2. "customers": HTML string describing target customers/segments
   Use only: <p>, <ul>, <li>, <strong>
   Example: "<p>Target customers include:</p><ul><li><strong>Enterprise teams</strong> - Large organizations...</li></ul>"

3. "products_services": HTML string describing main offerings
   Use only: <p>, <ul>, <li>, <strong>

4. "industry_overview": HTML string with industry context (3-4 paragraphs)
   Use only: <p>, <ul>, <li>, <strong>

5. "industry_trends": HTML string with current trends (bullet points)
   Use only: <p>, <ul>, <li>, <strong>

6. "fast_facts": HTML string with key market facts
   Structure sections: Market Size, Technology Trends, Common Pain Points
   Use only: <p>, <ul>, <li>, <strong>

7. "company_type": One of: "Startup", "SMB", "Enterprise", "Agency", "Government", "Non-Profit"

8. "industry_display": Format as "Industry1 • Industry2 • Industry3" (max 3)
   Example: "PropTech • Construction • SaaS"

9. "industry_naics": NAICS-style classification string
   Example: "541512 - Computer Systems Design Services"

10. "data_dictionary": Object with:
    - "product_service_types": array of category strings relevant to this business
    - "specialized_vocabulary": array of industry-specific terms
    - "example_names": array of realistic product/service names for this type of company

11. "industry_use_cases": Array of objects with:
    - "title": Use case title
    - "description": Brief description
    - "relevance": "high", "medium", or "low"

Return ONLY valid JSON. Do not include any explanation or markdown code fences.
'''


async def enrich_company(project_id: UUID) -> dict[str, Any]:
    """
    Enrich company data from website + AI inference.
    Fast enrichment (~5-10 seconds).

    Args:
        project_id: Project UUID

    Returns:
        Dict with enrichment results and metadata
    """
    settings = get_settings()

    # Get existing company info
    company_info = get_company_info(project_id)
    if not company_info:
        logger.warning(f"No company info found for project {project_id}")
        return {"success": False, "error": "No company info found"}

    name = company_info.get("name", "Unknown")
    website = company_info.get("website")
    industry = company_info.get("industry")
    description = company_info.get("description")

    # 1. Scrape website if available
    scraped_data = ""
    enrichment_source = "ai_inference"
    enrichment_confidence = 0.5

    if website:
        logger.info(f"Scraping website: {website}")
        scrape_result = await scrape_website_safe(website)
        if scrape_result:
            # Limit context to avoid token overflow
            scraped_data = scrape_result.get("markdown", "")[:8000]
            enrichment_source = "website_scrape"
            enrichment_confidence = 0.8
            logger.info(f"Scraped {len(scraped_data)} chars from {website}")

    # 2. Build prompt
    prompt = COMPANY_ENRICHMENT_PROMPT.format(
        name=name,
        website=website or "Not provided",
        scraped_data=scraped_data or "Not available - no website provided or scraping failed",
        industry=industry or "Not specified",
        description=description or "Not provided",
    )

    # 3. Get enrichment via Claude Sonnet 4
    logger.info(f"Running enrichment inference for {name}")
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = response.content[0].text if response.content else ""

    # 4. Parse JSON response
    try:
        # Handle potential markdown code fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        enrichment = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse enrichment response: {e}")
        return {"success": False, "error": f"JSON parse error: {e}"}

    # 5. Store enrichment in company_info
    update_company_enrichment(
        project_id=project_id,
        unique_selling_point=enrichment.get("unique_selling_point"),
        customers=enrichment.get("customers"),
        products_services=enrichment.get("products_services"),
        industry_overview=enrichment.get("industry_overview"),
        industry_trends=enrichment.get("industry_trends"),
        fast_facts=enrichment.get("fast_facts"),
        company_type=enrichment.get("company_type"),
        industry_display=enrichment.get("industry_display"),
        industry_naics=enrichment.get("industry_naics"),
        data_dictionary=enrichment.get("data_dictionary", {}),
        industry_use_cases=enrichment.get("industry_use_cases", []),
        enrichment_source=enrichment_source,
        enrichment_confidence=enrichment_confidence,
        raw_website_content=scraped_data if scraped_data else None,
    )

    logger.info(f"Company enrichment complete for project {project_id}")

    # 6. Extract brand assets (non-blocking — failure doesn't affect enrichment)
    brand_result = None
    try:
        from app.chains.extract_brand import extract_brand_from_website

        brand_result = await extract_brand_from_website(project_id)
    except Exception as e:
        logger.warning(f"Brand extraction failed for project {project_id}: {e}")

    return {
        "success": True,
        "enrichment_source": enrichment_source,
        "enrichment_confidence": enrichment_confidence,
        "scraped_chars": len(scraped_data) if scraped_data else 0,
        "fields_enriched": list(enrichment.keys()),
        "brand_extracted": brand_result is not None,
    }
