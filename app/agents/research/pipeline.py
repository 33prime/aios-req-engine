"""Optimized Research Pipeline - Deterministic, Cost-Efficient.

Target: ~$0.20 per run (vs $0.70 agentic)

Architecture:
- 5 deterministic phases (no agentic loop)
- Haiku for parsing ($0.25/1M vs $3/1M)
- Batched Perplexity queries (3-4 calls vs 8-12)
- Sonnet only for final synthesis

Cost breakdown:
- Phase 1 (Discovery): 1 Perplexity call (~$0.03)
- Phase 2 (Deep Dives): 1 batched Perplexity call (~$0.04)
- Phase 3 (Reviews): 1 Perplexity call (~$0.03)
- Phase 4 (Analysis): 1 Haiku call (~$0.02)
- Phase 5 (Synthesis): 1 Sonnet call (~$0.08)
Total: ~$0.20
"""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from anthropic import Anthropic
from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase
from app.db.competitor_refs import create_competitor_ref
from app.agents.research.schemas import (
    DeepResearchRequest,
    DeepResearchResponse,
    CompetitorIntelligence,
)

logger = get_logger(__name__)


# === PHASE 1: DISCOVERY ===

DISCOVERY_QUERY_TEMPLATE = """Find the top {max_competitors} competitors and alternatives for this product:

Product: {product_name}
Description: {product_description}
Industry: {industry}
Target Users: {target_users}
Key Features: {key_features}

Focus on:
- Direct competitors (same market, same features)
- Adjacent competitors (similar market, different approach)
- Emerging players (newer entrants with innovative approaches)

For each competitor, provide:
1. Company name
2. Website URL
3. One-line description
4. Target market (SMB/mid-market/enterprise)
5. Key differentiator
6. Category: direct_competitor, adjacent, or emerging"""


async def phase_discovery(
    state_snapshot: str,
    features: list[dict],
    personas: list[dict],
    focus_areas: list[str],
    max_competitors: int,
) -> list[dict]:
    """
    Phase 1: Discover competitors via single Perplexity call.

    Cost: ~$0.03 (1 Perplexity sonar call)
    """
    settings = get_settings()

    # Build context from project data
    feature_names = [f.get("name", "") for f in features[:10]]
    persona_names = [f"{p.get('name', '')} ({p.get('role', '')})" for p in personas]

    # Extract product info from state snapshot
    lines = state_snapshot.split("\n")
    product_name = "the product"
    product_desc = ""
    for line in lines:
        if line.startswith("Project:"):
            product_name = line.replace("Project:", "").strip()
        if line.startswith("Description:"):
            product_desc = line.replace("Description:", "").strip()

    query = DISCOVERY_QUERY_TEMPLATE.format(
        max_competitors=max_competitors + 2,  # Get extra to filter
        product_name=product_name,
        product_description=product_desc[:200],
        industry=", ".join(focus_areas) if focus_areas else "software",
        target_users=", ".join(persona_names) if persona_names else "business users",
        key_features=", ".join(feature_names[:5]) if feature_names else "core functionality",
    )

    # Single Perplexity call
    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    response = client.chat.completions.create(
        model="sonar",  # Use cheaper model for discovery
        messages=[
            {
                "role": "system",
                "content": "You are a market research analyst. Provide factual, specific competitor information. Format as a numbered list with clear structure."
            },
            {"role": "user", "content": query}
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    raw_results = response.choices[0].message.content or ""

    # Parse with Haiku (cheap)
    competitors = await _parse_competitors_haiku(raw_results, max_competitors)

    logger.info(f"Discovery found {len(competitors)} competitors")
    return competitors


# === PHASE 2: DEEP DIVES ===

DEEP_DIVE_QUERY_TEMPLATE = """Provide detailed analysis for these competitors:

{competitor_list}

For EACH competitor, provide:
1. Full company description (2-3 sentences)
2. Pricing model (per_seat, flat_rate, usage_based, freemium, enterprise)
3. Pricing range ($, $$, $$$, $$$$)
4. Top 5 key features
5. 3 main strengths
6. 3 main weaknesses
7. Target customer size (SMB, mid-market, enterprise)
8. Notable customers (if known)

Be specific with feature names and pricing details."""


async def phase_deep_dives(
    competitors: list[dict],
) -> list[dict]:
    """
    Phase 2: Deep dive on competitors via single batched Perplexity call.

    Cost: ~$0.04 (1 Perplexity sonar-pro call for quality)
    """
    settings = get_settings()

    if not competitors:
        return []

    # Build competitor list for query
    competitor_list = "\n".join([
        f"{i+1}. {c.get('name', 'Unknown')} ({c.get('website', 'no url')})"
        for i, c in enumerate(competitors[:5])
    ])

    query = DEEP_DIVE_QUERY_TEMPLATE.format(competitor_list=competitor_list)

    # Single Perplexity call with pro model for better quality
    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    response = client.chat.completions.create(
        model="sonar-pro",  # Pro for detailed analysis
        messages=[
            {
                "role": "system",
                "content": "You are a competitive intelligence analyst. Provide detailed, accurate information about each competitor. Structure your response clearly by competitor."
            },
            {"role": "user", "content": query}
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    raw_results = response.choices[0].message.content or ""

    # Parse and merge with existing competitor data using Haiku
    enriched = await _parse_deep_dives_haiku(raw_results, competitors)

    logger.info(f"Deep dives enriched {len(enriched)} competitors")
    return enriched


# === PHASE 3: USER VOICE ===

REVIEWS_QUERY_TEMPLATE = """Find user reviews and feedback for these products from G2, Capterra, TrustRadius, or similar review sites:

Products: {product_list}
Industry context: {industry}

For each product, find:
1. Overall rating (out of 5)
2. Number of reviews
3. 2-3 actual user quotes (positive and negative)
4. Most common praise themes
5. Most common complaint themes
6. Reviewer roles mentioned (e.g., "Sales Manager", "IT Admin")

Focus on recent reviews (2024-2025) and quotes from users similar to: {target_personas}"""


async def phase_user_voice(
    competitors: list[dict],
    personas: list[dict],
    focus_areas: list[str],
) -> list[dict]:
    """
    Phase 3: Gather user reviews via single Perplexity call.

    Cost: ~$0.03 (1 Perplexity sonar call)
    """
    settings = get_settings()

    if not competitors:
        return []

    product_list = ", ".join([c.get("name", "") for c in competitors[:5]])
    persona_list = ", ".join([p.get("role", "") for p in personas[:3]]) if personas else "business users"

    query = REVIEWS_QUERY_TEMPLATE.format(
        product_list=product_list,
        industry=", ".join(focus_areas) if focus_areas else "software",
        target_personas=persona_list,
    )

    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {
                "role": "system",
                "content": "You are researching user reviews. Extract actual quotes and specific feedback. Be factual and cite the review source when possible."
            },
            {"role": "user", "content": query}
        ],
        temperature=0.2,
        max_tokens=3000,
    )

    raw_results = response.choices[0].message.content or ""

    # Parse reviews with Haiku
    reviews = await _parse_reviews_haiku(raw_results, competitors)

    logger.info(f"User voice gathered {len(reviews)} review summaries")
    return reviews


# === PHASE 4: FEATURE ANALYSIS ===

async def phase_feature_analysis(
    competitors: list[dict],
    our_features: list[dict],
) -> dict:
    """
    Phase 4: Build feature matrix using Haiku.

    Cost: ~$0.02 (1 Haiku call)
    """
    settings = get_settings()

    # Build feature comparison prompt
    our_feature_names = [f.get("name", "") for f in our_features]

    competitor_features = {}
    for comp in competitors:
        competitor_features[comp.get("name", "Unknown")] = comp.get("key_features", [])

    prompt = f"""Analyze this feature comparison data and create a structured analysis:

OUR FEATURES:
{json.dumps(our_feature_names, indent=2)}

COMPETITOR FEATURES:
{json.dumps(competitor_features, indent=2)}

Provide:
1. TABLE STAKES: Features that ALL competitors have (we must have these)
2. DIFFERENTIATORS: Features only 1-2 competitors have (opportunity to stand out)
3. OUR UNIQUE: Features we have that competitors don't
4. GAPS: Features competitors have that we're missing
5. MARKET TRENDS: What features are becoming standard?

Output as JSON:
{{
  "table_stakes": ["feature1", "feature2"],
  "differentiators": {{"competitor": ["unique_feature"]}},
  "our_unique": ["feature"],
  "gaps": ["missing_feature"],
  "trends": ["emerging_feature"]
}}"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text

    # Parse JSON from response
    try:
        # Find JSON in response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            analysis = json.loads(raw[start:end])
        else:
            analysis = {"table_stakes": [], "differentiators": {}, "our_unique": [], "gaps": [], "trends": []}
    except json.JSONDecodeError:
        analysis = {"table_stakes": [], "differentiators": {}, "our_unique": [], "gaps": [], "trends": []}

    logger.info("Feature analysis complete")
    return analysis


# === PHASE 5: SYNTHESIS ===

async def phase_synthesis(
    state_snapshot: str,
    competitors: list[dict],
    reviews: list[dict],
    feature_analysis: dict,
    focus_areas: list[str],
) -> dict:
    """
    Phase 5: Generate executive summary using Sonnet.

    Cost: ~$0.08 (1 Sonnet call - quality matters here)
    """
    settings = get_settings()

    # Build comprehensive context
    competitor_summary = "\n".join([
        f"- {c.get('name')}: {c.get('description', 'No description')} | Strengths: {', '.join(c.get('strengths', [])[:2])} | Weaknesses: {', '.join(c.get('weaknesses', [])[:2])}"
        for c in competitors[:5]
    ])

    review_summary = "\n".join([
        f"- {r.get('competitor')}: Rating {r.get('rating', 'N/A')}/5 | Praise: {', '.join(r.get('praise_themes', [])[:2])} | Complaints: {', '.join(r.get('complaint_themes', [])[:2])}"
        for r in reviews[:5]
    ])

    prompt = f"""You are a strategic consultant synthesizing competitive research for a product team.

## PROJECT CONTEXT
{state_snapshot}

## COMPETITORS ANALYZED
{competitor_summary}

## USER FEEDBACK SUMMARY
{review_summary}

## FEATURE ANALYSIS
- Table Stakes: {', '.join(feature_analysis.get('table_stakes', []))}
- Our Unique Features: {', '.join(feature_analysis.get('our_unique', []))}
- Gaps to Address: {', '.join(feature_analysis.get('gaps', []))}
- Market Trends: {', '.join(feature_analysis.get('trends', []))}

## YOUR TASK
Write a strategic brief with:

1. **EXECUTIVE SUMMARY** (2-3 paragraphs)
   - Market landscape overview
   - Our competitive position
   - Key opportunity

2. **TOP 5 INSIGHTS** (bullet points)
   - Specific, actionable findings
   - Reference competitor names and data

3. **RECOMMENDED ACTIONS** (3-5 items)
   - Prioritized by impact
   - Specific features or strategies

4. **MARKET GAPS** (2-3 opportunities)
   - Unmet needs in the market
   - How we could address them

Be specific and strategic. Reference actual competitor names and features."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    synthesis = response.content[0].text

    # Parse into structured sections
    result = _parse_synthesis(synthesis)

    logger.info("Synthesis complete")
    return result


# === HAIKU PARSING HELPERS ===

async def _parse_competitors_haiku(raw_text: str, max_count: int) -> list[dict]:
    """Parse competitor list using Haiku."""
    settings = get_settings()

    prompt = f"""Extract competitor information from this text into JSON format.

TEXT:
{raw_text[:4000]}

Output a JSON array of competitors:
[
  {{
    "name": "Company Name",
    "website": "https://...",
    "description": "One line description",
    "target_market": "SMB|mid-market|enterprise",
    "differentiator": "Key differentiator",
    "category": "direct_competitor|adjacent|emerging"
  }}
]

Return only the JSON array, max {max_count} competitors."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text

    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            competitors = json.loads(raw[start:end])
            return competitors[:max_count]
    except json.JSONDecodeError:
        pass

    return []


async def _parse_deep_dives_haiku(raw_text: str, existing: list[dict]) -> list[dict]:
    """Parse deep dive info and merge with existing competitor data."""
    settings = get_settings()

    existing_names = [c.get("name", "").lower() for c in existing]

    prompt = f"""Extract detailed competitor information from this text and merge with existing data.

EXISTING COMPETITORS:
{json.dumps([c.get('name') for c in existing])}

NEW INFORMATION:
{raw_text[:5000]}

Output JSON array with enriched competitor data:
[
  {{
    "name": "Company Name",
    "description": "Full description",
    "pricing_model": "per_seat|flat_rate|usage_based|freemium|enterprise",
    "pricing_range": "$|$$|$$$|$$$$",
    "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"],
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "target_market": "SMB|mid-market|enterprise",
    "notable_customers": ["customer1", "customer2"]
  }}
]

Return only JSON array."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text

    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            enriched = json.loads(raw[start:end])

            # Merge with existing data
            result = []
            for comp in existing:
                name = comp.get("name", "").lower()
                # Find matching enriched data
                for e in enriched:
                    if e.get("name", "").lower() == name or name in e.get("name", "").lower():
                        comp.update(e)
                        break
                result.append(comp)

            return result
    except json.JSONDecodeError:
        pass

    return existing


async def _parse_reviews_haiku(raw_text: str, competitors: list[dict]) -> list[dict]:
    """Parse review information using Haiku."""
    settings = get_settings()

    prompt = f"""Extract review/feedback information from this text.

COMPETITORS:
{json.dumps([c.get('name') for c in competitors])}

REVIEW TEXT:
{raw_text[:4000]}

Output JSON array:
[
  {{
    "competitor": "Company Name",
    "rating": 4.2,
    "review_count": "500+",
    "praise_themes": ["ease of use", "good support"],
    "complaint_themes": ["expensive", "limited features"],
    "sample_quotes": ["Actual user quote 1", "Actual user quote 2"],
    "reviewer_roles": ["Sales Manager", "IT Admin"]
  }}
]

Return only JSON array."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text

    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass

    return []


def _parse_synthesis(text: str) -> dict:
    """Parse synthesis text into structured sections."""
    result = {
        "executive_summary": "",
        "key_insights": [],
        "recommended_actions": [],
        "market_gaps": [],
    }

    lines = text.split("\n")
    current_section = "summary"  # Start with summary
    buffer = []

    for line in lines:
        line_lower = line.lower().strip()

        # Detect section headers
        if "executive summary" in line_lower:
            current_section = "summary"
            buffer = []
            continue
        elif "insight" in line_lower and ("top" in line_lower or "#" in line):
            if buffer:
                result["executive_summary"] = "\n".join(buffer).strip()
            current_section = "insights"
            continue
        elif "recommend" in line_lower and ("action" in line_lower or "#" in line):
            current_section = "actions"
            continue
        elif "gap" in line_lower and "#" in line:
            current_section = "gaps"
            continue

        # Process content based on current section
        if current_section == "summary":
            if line.strip() and not line.startswith("#"):
                buffer.append(line)
        elif line.strip().startswith(("-", "•", "*")) or (line.strip() and line.strip()[0].isdigit() and "." in line[:5]):
            clean = line.strip().lstrip("-•*0123456789.)").strip()
            if clean and len(clean) > 10:
                if current_section == "insights":
                    result["key_insights"].append(clean)
                elif current_section == "actions":
                    result["recommended_actions"].append(clean)
                elif current_section == "gaps":
                    result["market_gaps"].append(clean)

    # Capture remaining buffer as executive summary if not already set
    if buffer and not result["executive_summary"]:
        result["executive_summary"] = "\n".join(buffer).strip()

    # If still no executive summary, use first 500 chars of text
    if not result["executive_summary"]:
        clean_text = text.replace("#", "").strip()
        result["executive_summary"] = clean_text[:800]

    return result


# === MAIN PIPELINE ===

async def run_research_pipeline(
    request: DeepResearchRequest,
) -> DeepResearchResponse:
    """
    Run the optimized research pipeline.

    Total cost: ~$0.18-0.22
    - Phase 1: ~$0.03 (Perplexity sonar)
    - Phase 2: ~$0.04 (Perplexity sonar-pro)
    - Phase 3: ~$0.03 (Perplexity sonar)
    - Phase 4: ~$0.02 (Haiku)
    - Phase 5: ~$0.08 (Sonnet)
    + Haiku parsing: ~$0.02
    """
    run_id = uuid4()
    started_at = datetime.utcnow()
    phases_completed = []

    logger.info(f"Starting research pipeline for project {request.project_id}", extra={"run_id": str(run_id)})

    # Get project context
    state_snapshot = get_state_snapshot(request.project_id)
    supabase = get_supabase()

    features = supabase.table("features").select(
        "id, name, overview, is_mvp"
    ).eq("project_id", str(request.project_id)).execute().data or []

    personas = supabase.table("personas").select(
        "id, name, role"
    ).eq("project_id", str(request.project_id)).execute().data or []

    # === PHASE 1: DISCOVERY ===
    logger.info("Phase 1: Discovery")
    competitors = await phase_discovery(
        state_snapshot=state_snapshot,
        features=features,
        personas=personas,
        focus_areas=request.focus_areas,
        max_competitors=request.max_competitors,
    )
    phases_completed.append("discovery")

    # === PHASE 2: DEEP DIVES ===
    logger.info("Phase 2: Deep Dives")
    competitors = await phase_deep_dives(competitors)
    phases_completed.append("deep_dives")

    # Save competitors to database
    for comp in competitors:
        try:
            create_competitor_ref(
                project_id=request.project_id,
                reference_type="competitor",
                name=comp.get("name", "Unknown"),
                url=comp.get("website"),
                category=comp.get("category", "direct_competitor"),
                strengths=comp.get("strengths", []),
                weaknesses=comp.get("weaknesses", []),
                features_to_study=comp.get("key_features", []),
                research_notes=f"Pricing: {comp.get('pricing_model', 'unknown')} ({comp.get('pricing_range', '$')})\nTarget: {comp.get('target_market', 'unknown')}",
            )
        except Exception as e:
            logger.warning(f"Failed to save competitor {comp.get('name')}: {e}")

    # === PHASE 3: USER VOICE ===
    logger.info("Phase 3: User Voice")
    reviews = await phase_user_voice(
        competitors=competitors,
        personas=personas,
        focus_areas=request.focus_areas,
    )
    phases_completed.append("user_voice")

    # === PHASE 4: FEATURE ANALYSIS ===
    logger.info("Phase 4: Feature Analysis")
    feature_analysis = await phase_feature_analysis(
        competitors=competitors,
        our_features=features,
    )
    phases_completed.append("feature_analysis")

    # === PHASE 5: SYNTHESIS ===
    logger.info("Phase 5: Synthesis")
    synthesis = await phase_synthesis(
        state_snapshot=state_snapshot,
        competitors=competitors,
        reviews=reviews,
        feature_analysis=feature_analysis,
        focus_areas=request.focus_areas,
    )
    phases_completed.append("synthesis")

    completed_at = datetime.utcnow()

    logger.info(
        f"Research pipeline complete for project {request.project_id}",
        extra={
            "run_id": str(run_id),
            "competitors": len(competitors),
            "duration_seconds": (completed_at - started_at).total_seconds(),
        }
    )

    return DeepResearchResponse(
        run_id=run_id,
        project_id=request.project_id,
        status="completed",
        competitors_found=len(competitors),
        competitors_analyzed=len(competitors),
        features_mapped=len(features),
        reviews_analyzed=len(reviews),
        market_gaps_identified=len(synthesis.get("market_gaps", [])),
        executive_summary=synthesis.get("executive_summary", ""),
        key_insights=synthesis.get("key_insights", []),
        recommended_actions=synthesis.get("recommended_actions", []),
        started_at=started_at,
        completed_at=completed_at,
        phases_completed=phases_completed,
    )
