"""
Brand Extraction Chain

Extracts brand assets (logo, colors, typography, design characteristics) from
a company's website HTML using Firecrawl + Claude analysis.
"""

import json
import logging
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.firecrawl_service import scrape_website_full_safe
from app.db.company_info import get_company_info, update_brand_data

logger = logging.getLogger(__name__)

BRAND_EXTRACTION_PROMPT = """\
You are a brand identity analyst. Analyze the following website HTML to extract brand assets.

Website: {website}
Company: {name}

HTML content (truncated):
{html_content}

Extract the following and return as JSON:

1. "logo_url": The most likely logo URL. Look for:
   - <img> inside <header>, <nav>, or elements with class containing "logo"
   - <link rel="icon"> or favicon as fallback
   - Return the full absolute URL (resolve relative paths against {website})
   - Return null if not found

2. "brand_colors": Array of hex color strings (max 6). Look for:
   - CSS custom properties (--primary-color, --brand-color, etc.)
   - Background colors on buttons, headers, CTAs
   - Text colors on headings
   - Accent/highlight colors
   - Order: primary first, then secondary, then accents

3. "typography": Object with:
   - "heading_font": Primary heading font family (e.g., "Inter", "Playfair Display")
   - "body_font": Body text font family
   - Look at CSS font-family declarations, Google Fonts links, @font-face rules
   - If only one font is used, set both to the same value

4. "design_characteristics": Object with:
   - "overall_feel": One of "minimal", "bold", "warm", "luxury", "tech", "playful", "corporate"
   - "spacing": One of "compact", "balanced", "generous"
   - "corners": One of "sharp", "slightly-rounded", "rounded", "pill"
   - "visual_weight": One of "light", "medium", "heavy"

Return ONLY valid JSON. No explanation or code fences.
"""


async def extract_brand_from_website(project_id: UUID) -> dict[str, Any] | None:
    """
    Scrape website with full HTML and extract brand assets via Claude.

    Args:
        project_id: Project UUID

    Returns:
        Dict with extraction results, or None if extraction failed
    """
    settings = get_settings()

    company_info = get_company_info(project_id)
    if not company_info:
        logger.warning(f"No company info for project {project_id}")
        return None

    website = company_info.get("website")
    if not website:
        logger.info(f"No website for project {project_id}, skipping brand extraction")
        return None

    name = company_info.get("name", "Unknown")

    # 1. Scrape with full HTML
    scrape_result = await scrape_website_full_safe(website)
    if not scrape_result or not scrape_result.get("html"):
        logger.warning(f"Failed to scrape full HTML for {website}")
        return None

    # Limit HTML to avoid token overflow
    html_content = scrape_result["html"][:15000]

    # 2. Claude analysis
    prompt = BRAND_EXTRACTION_PROMPT.format(
        website=website,
        name=name,
        html_content=html_content,
    )

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text if response.content else ""

    # 3. Parse response
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        brand_data = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse brand extraction response: {e}")
        return None

    # 4. Store in company_info
    update_brand_data(
        project_id=project_id,
        logo_url=brand_data.get("logo_url"),
        brand_colors=brand_data.get("brand_colors", []),
        typography=brand_data.get("typography"),
        design_characteristics=brand_data.get("design_characteristics"),
    )

    logger.info(
        f"Brand extraction complete for project {project_id}: "
        f"logo={'yes' if brand_data.get('logo_url') else 'no'}, "
        f"colors={len(brand_data.get('brand_colors', []))}"
    )

    return brand_data
