"""External source enrichment — PDL, BrightData, Firecrawl.

No LLM calls. Pure API integrations for firmographic/social data.
Preserved from the old SI agent tools.
"""

import asyncio

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.core.logging import get_logger

logger = get_logger(__name__)


async def enrich_from_external(ctx: StakeholderContext) -> list[str]:
    """Pull data from external APIs. Returns changed fields."""
    s = ctx.stakeholder
    linkedin_url = s.get("linkedin_profile")
    email = s.get("email")

    if not linkedin_url and not email:
        return []

    pdl_data = None
    bd_data = None

    async def safe_pdl():
        nonlocal pdl_data
        from app.core.pdl_service import enrich_person_safe

        result = await enrich_person_safe(
            linkedin_url=linkedin_url, email=email,
        )
        if result:
            pdl_data = result

    async def safe_brightdata():
        nonlocal bd_data
        if not linkedin_url:
            return
        from app.core.brightdata_service import (
            scrape_linkedin_profile_safe,
        )

        result = await scrape_linkedin_profile_safe(linkedin_url)
        if result:
            bd_data = result

    tasks = [safe_pdl()]
    if linkedin_url:
        tasks.append(safe_brightdata())

    await asyncio.gather(*tasks, return_exceptions=True)

    updates: dict = {}

    # PDL data → role, organization, domain expertise, email
    if pdl_data:
        if pdl_data.get("job_title"):
            updates["role"] = pdl_data["job_title"]

        if pdl_data.get("company_name") and not s.get("organization"):
            updates["organization"] = pdl_data["company_name"]

        if pdl_data.get("skills"):
            existing = s.get("domain_expertise") or []
            merged = list(set(existing + pdl_data["skills"][:10]))
            if len(merged) > len(existing):
                updates["domain_expertise"] = merged

        if pdl_data.get("emails") and not s.get("email"):
            first = pdl_data["emails"][0]
            if isinstance(first, dict):
                first = first.get("address", "")
            if first:
                updates["email"] = first

        if (
            pdl_data.get("linkedin_url")
            and not s.get("linkedin_profile")
        ):
            updates["linkedin_profile"] = pdl_data["linkedin_url"]

        # Infer decision authority from title levels
        levels = pdl_data.get("job_title_levels") or []
        if levels and not s.get("decision_authority"):
            if any(lv in levels for lv in ["cxo", "director", "vp"]):
                updates["decision_authority"] = (
                    f"Senior leader ({', '.join(levels)}). "
                    "Likely approves strategic and budget decisions."
                )
            elif "manager" in levels:
                updates["decision_authority"] = (
                    f"Manager-level ({', '.join(levels)}). "
                    "Approves operational decisions within domain."
                )

    # BrightData → headline, about, engagement signals
    if bd_data:
        if bd_data.get("headline") and not s.get("role"):
            updates["role"] = bd_data["headline"]

        if bd_data.get("about"):
            existing_notes = s.get("notes") or ""
            if "LinkedIn:" not in existing_notes:
                snippet = bd_data["about"][:500]
                updates["notes"] = (
                    f"{existing_notes}\n\nLinkedIn: {snippet}"
                    if existing_notes
                    else f"LinkedIn: {snippet}"
                ).strip()

        if bd_data.get("follower_count"):
            followers = bd_data["follower_count"]
            if (
                isinstance(followers, (int, float))
                and followers > 5000
                and not s.get("engagement_strategy")
            ):
                updates["engagement_strategy"] = (
                    f"Active LinkedIn presence "
                    f"({followers:,} followers). "
                    "Engage via thought leadership."
                )

        company = bd_data.get("current_company")
        if company and not s.get("organization"):
            if isinstance(company, dict):
                company = company.get("name", str(company))
            updates["organization"] = str(company)

    if updates:
        updates["enrichment_status"] = "enriched"
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
