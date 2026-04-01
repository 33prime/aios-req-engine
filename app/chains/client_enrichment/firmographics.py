"""Firmographic enrichment chain — website scraping + AI structured extraction.

Uses Firecrawl for web content, then PydanticAI for structured enrichment.
"""

from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.client_enrichment.models import FirmographicEnrichment
from app.core.firecrawl_service import scrape_website_safe
from app.core.logging import get_logger
from app.db.clients import get_client, update_client_enrichment

logger = get_logger(__name__)

ENRICHMENT_INSTRUCTIONS = """\
You are a business analyst providing company intelligence.

CRITICAL: You MUST provide intelligence about the SPECIFIC company described in the prompt.
Do NOT confuse this company with similarly-named companies.

Rules:
1. If website data is available, base analysis PRIMARILY on that data.
2. If the scraped data does NOT match the company identity, IGNORE it and note the mismatch.
3. NEVER substitute data from a different company with a similar name.
4. If you cannot find reliable information, return null for that field — do NOT guess.
"""

firmographics_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=FirmographicEnrichment,
    instructions=ENRICHMENT_INSTRUCTIONS,
    model_settings=ModelSettings(temperature=0.3, max_tokens=4096),
    retries=2,
)


def _verify_scraped_content(company_name: str, text: str) -> bool:
    """Check that scraped content plausibly matches the target company."""
    text_lower = text[:2000].lower()
    skip = {"the", "inc", "llc", "ltd", "co", "corp", "company", "group", "and", "of", "for"}
    words = [w for w in company_name.lower().split() if len(w) > 2 and w not in skip]
    if not words:
        return True
    return sum(1 for w in words if w in text_lower) >= 1


async def enrich_firmographics(client_id: UUID) -> dict:
    """Enrich a client with firmographic data.

    Returns dict with success, enrichment_source, fields_enriched.
    """
    client = get_client(client_id)
    if not client:
        return {"success": False, "error": "Client not found"}

    name = client.get("name", "Unknown")
    website = client.get("website")

    update_client_enrichment(client_id, {"enrichment_status": "in_progress"})

    # 1. Scrape website
    scraped_data = ""
    enrichment_source = "ai_inference"

    if website:
        scrape_result = await scrape_website_safe(website)
        if scrape_result:
            raw = scrape_result.get("markdown", "")[:8000]
            if raw and _verify_scraped_content(name, raw):
                scraped_data = raw
                enrichment_source = "website_scrape"
            elif raw:
                logger.warning(
                    f"Scraped content from {website} doesn't match '{name}' — discarding"
                )

    # 2. Build prompt and run PydanticAI agent
    prompt = f"""Analyze this company and extract firmographic intelligence.

## Company Identity (GROUND TRUTH)
Name: {name}
Website: {website or "Not provided"}
Location: {client.get("headquarters") or client.get("location") or "Not specified"}
Industry: {client.get("industry") or "Not specified"}
Description: {(client.get("description") or "Not provided")[:200]}

## Website Data
{scraped_data or "Not available — use ONLY the company identity above."}
"""

    try:
        result = await firmographics_agent.run(prompt)
        enrichment = result.output
    except Exception as e:
        logger.error(f"Firmographic enrichment failed for {client_id}: {e}")
        update_client_enrichment(client_id, {"enrichment_status": "failed"})
        return {"success": False, "error": str(e)}

    # 3. Verify enrichment matches target company
    if enrichment.company_summary and not _verify_scraped_content(name, enrichment.company_summary):
        logger.error(
            f"Enrichment returned data for wrong company: {enrichment.company_summary[:200]}"
        )
        update_client_enrichment(client_id, {"enrichment_status": "failed"})
        return {"success": False, "error": "Enrichment returned data for wrong company"}

    # 4. Persist — convert model to dict, filter None values
    data = enrichment.model_dump(exclude_none=True, exclude={"verification_status"})
    data["enrichment_status"] = "completed"
    data["enriched_at"] = "now()"
    data["enrichment_source"] = enrichment_source

    # Serialize nested models for JSONB columns
    if "growth_signals" in data:
        data["growth_signals"] = [
            gs if isinstance(gs, dict) else gs for gs in data["growth_signals"]
        ]
    if "competitors" in data:
        data["competitors"] = [c if isinstance(c, dict) else c for c in data["competitors"]]

    update_client_enrichment(client_id, data)

    fields = [
        k for k, v in enrichment.model_dump().items() if v is not None and v != [] and v != ""
    ]
    return {"success": True, "enrichment_source": enrichment_source, "fields_enriched": fields}
