"""Phase 6: Feature & Pricing Analysis — Haiku LLM-only analysis.

Builds feature comparison matrix, pricing comparison, and gap analysis
from competitor data collected in Phase 3.
"""

import json
import logging
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FEATURE_ANALYSIS_PROMPT = """You are analyzing competitor data to build a feature comparison matrix.
Use ONLY the competitor data provided below. Do NOT invent features or pricing.

COMPANY: {company_name}
COMPANY PROFILE: {company_profile}

COMPETITORS:
{competitor_data}

Return a JSON object:
{{
    "feature_matrix": {{
        "categories": ["Category1", "Category2"],
        "features": [
            {{
                "name": "Feature Name",
                "category": "Category1",
                "table_stakes": true,
                "company_has": true,
                "competitors": {{
                    "CompetitorA": true,
                    "CompetitorB": false
                }}
            }}
        ]
    }},
    "pricing_comparison": [
        {{
            "company": "CompetitorA",
            "model": "subscription",
            "tiers": ["Free: ...", "Pro: $X/mo"],
            "notes": "Any relevant pricing notes"
        }}
    ],
    "gap_analysis": [
        "Gap 1: Description of a feature gap or opportunity",
        "Gap 2: Description of another gap"
    ],
    "differentiators": [
        "Differentiator 1: What makes the company unique",
        "Differentiator 2: Another differentiator"
    ]
}}
"""


async def run_feature_analysis(
    company_name: str,
    company_profile: dict[str, Any],
    competitors: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Execute Phase 6: Feature & Pricing Analysis.

    Returns:
        Tuple of (feature_matrix, pricing_comparison, gap_analysis, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []

    if not competitors:
        logger.warning("No competitors for feature analysis, skipping")
        return {}, [], [], cost_entries

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return {}, [], [], cost_entries

    from anthropic import AsyncAnthropic

    # Format competitor data
    comp_texts = []
    for c in competitors:
        comp_texts.append(
            f"### {c.get('name', 'Unknown')}\n"
            f"- Employees: {c.get('employee_count', '?')}\n"
            f"- Features: {', '.join(c.get('key_features', []))}\n"
            f"- Pricing: {', '.join(c.get('pricing_tiers', []))}\n"
            f"- Strengths: {', '.join(c.get('strengths', []))}\n"
            f"- Weaknesses: {', '.join(c.get('weaknesses', []))}\n"
        )

    # Format company profile
    cp_text = (
        f"Products: {', '.join(company_profile.get('key_products') or [])}\n"
        f"Pricing: {company_profile.get('pricing_model', '?')}\n"
        f"Tiers: {', '.join(company_profile.get('pricing_tiers') or [])}\n"
    )

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": FEATURE_ANALYSIS_PROMPT.format(
                    company_name=company_name,
                    company_profile=cp_text,
                    competitor_data="\n".join(comp_texts),
                ),
            }],
        )
        cost_entries.append({
            "phase": "feature_analysis",
            "service": "anthropic_haiku",
            "cost_usd": 0.03,
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

        feature_matrix = parsed.get("feature_matrix", {})
        pricing_comparison = parsed.get("pricing_comparison", [])
        gap_analysis = parsed.get("gap_analysis", [])

        logger.info(
            f"Feature analysis complete: "
            f"{len(feature_matrix.get('features', []))} features, "
            f"{len(gap_analysis)} gaps identified"
        )

        return feature_matrix, pricing_comparison, gap_analysis, cost_entries

    except Exception as e:
        logger.warning(f"Feature analysis failed: {e}")
        return {}, [], [], cost_entries
