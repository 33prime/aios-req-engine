"""Deep competitor analysis chain.

Scrapes competitor website via Firecrawl, runs LLM analysis comparing
features/positioning/pains against the project, stores output and creates a signal.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.firecrawl_service import scrape_website_safe
from app.core.logging import get_logger
from app.db.phase0 import insert_signal
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Output Schemas
# ============================================================================


class FeatureComparison(BaseModel):
    feature_name: str
    our_approach: str | None = None
    their_approach: str | None = None
    advantage: Literal["us", "them", "neutral"] = "neutral"


class FeatureNote(BaseModel):
    feature_name: str
    description: str
    strategic_relevance: Literal["high", "medium", "low"] = "medium"


class CompetitorDeepAnalysis(BaseModel):
    # Feature comparison
    feature_overlap: list[FeatureComparison] = Field(default_factory=list)
    unique_to_them: list[FeatureNote] = Field(default_factory=list)
    unique_to_us: list[FeatureNote] = Field(default_factory=list)

    # Market intelligence
    inferred_pains: list[str] = Field(default_factory=list)
    inferred_benefits: list[str] = Field(default_factory=list)
    positioning_summary: str = ""
    threat_level: Literal["low", "medium", "high", "critical"] = "medium"
    threat_reasoning: str = ""

    # Strategic
    differentiation_opportunities: list[str] = Field(default_factory=list)
    gaps_to_address: list[str] = Field(default_factory=list)


# ============================================================================
# Page Discovery
# ============================================================================


def _find_subpages(homepage_markdown: str, base_url: str) -> list[str]:
    """Extract likely subpage URLs from homepage markdown content."""
    urls: list[str] = []
    # Match markdown links and raw URLs
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)|(?:href=["\'])([^"\']+)["\']')

    keywords = ["pricing", "features", "product", "solutions", "about", "platform"]

    for match in link_pattern.finditer(homepage_markdown):
        link_text = (match.group(1) or "").lower()
        url = match.group(2) or match.group(3) or ""

        # Normalize relative URLs
        if url.startswith("/"):
            url = base_url.rstrip("/") + url
        elif not url.startswith("http"):
            continue

        # Check if URL or link text matches keywords
        url_lower = url.lower()
        if any(kw in url_lower or kw in link_text for kw in keywords):
            if url not in urls and base_url.split("//")[1].split("/")[0] in url:
                urls.append(url)

    return urls[:4]  # Max 4 subpages (homepage already scraped)


# ============================================================================
# Main Chain
# ============================================================================


async def analyze_competitor(
    ref_id: UUID,
    project_id: UUID,
) -> CompetitorDeepAnalysis:
    """
    Run deep analysis on a competitor reference.

    1. Load competitor ref + project context
    2. Scrape competitor website (up to 5 pages)
    3. Run LLM analysis
    4. Store results + create signal

    Returns:
        CompetitorDeepAnalysis result
    """
    supabase = get_supabase()

    # Mark as analyzing
    supabase.table("competitor_references").update({
        "deep_analysis_status": "analyzing",
    }).eq("id", str(ref_id)).execute()

    try:
        # Load competitor ref
        ref_result = supabase.table("competitor_references").select("*").eq(
            "id", str(ref_id)
        ).single().execute()
        competitor = ref_result.data

        # Load project context
        proj_result = supabase.table("projects").select(
            "name, vision, description"
        ).eq("id", str(project_id)).single().execute()
        project = proj_result.data

        # Load project features
        features_result = supabase.table("features").select(
            "name, overview, category, priority_group"
        ).eq("project_id", str(project_id)).execute()
        features = features_result.data or []

        # Load project personas
        personas_result = supabase.table("personas").select(
            "name, role"
        ).eq("project_id", str(project_id)).execute()
        personas = personas_result.data or []

        # ================================================================
        # Scrape competitor website
        # ================================================================
        scraped_pages: list[dict[str, Any]] = []
        all_markdown = ""
        competitor_url = competitor.get("website") or competitor.get("url") or ""

        if competitor_url:
            # Homepage
            homepage = await scrape_website_safe(competitor_url)
            if homepage:
                scraped_pages.append({
                    "url": competitor_url,
                    "title": homepage.get("metadata", {}).get("title", "Homepage"),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
                all_markdown += f"\n\n## Homepage\n{homepage['markdown']}"

                # Discover subpages
                subpage_urls = _find_subpages(homepage["markdown"], competitor_url)
                for sub_url in subpage_urls:
                    sub_result = await scrape_website_safe(sub_url)
                    if sub_result:
                        scraped_pages.append({
                            "url": sub_url,
                            "title": sub_result.get("metadata", {}).get("title", sub_url),
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                        })
                        all_markdown += f"\n\n## {sub_result.get('metadata', {}).get('title', sub_url)}\n{sub_result['markdown']}"

        # Truncate to avoid token limits
        if len(all_markdown) > 30000:
            all_markdown = all_markdown[:30000] + "\n\n[Content truncated]"

        # ================================================================
        # Build LLM prompt
        # ================================================================
        feature_list = "\n".join(
            f"- {f['name']}: {f.get('overview', '')[:100]} (priority: {f.get('priority_group', 'unknown')})"
            for f in features
        )
        persona_list = "\n".join(
            f"- {p['name']}: {p.get('role', 'N/A')}" for p in personas
        )

        prompt = f"""Analyze this competitor against our project. Return a structured JSON analysis.

## Our Project
Name: {project.get('name', 'Unknown')}
Vision: {project.get('vision', 'Not defined')}

### Our Features
{feature_list or 'No features defined yet'}

### Our Personas
{persona_list or 'No personas defined yet'}

## Competitor
Name: {competitor.get('name', 'Unknown')}
Website: {competitor_url}
Category: {competitor.get('category', 'Unknown')}
Market Position: {competitor.get('market_position', 'Unknown')}
Key Differentiator: {competitor.get('key_differentiator', 'Unknown')}

## Competitor Website Content
{all_markdown or 'No website content available — analyze based on known information only.'}

## Instructions
Return a JSON object with these fields:
- feature_overlap: Array of {{feature_name, our_approach, their_approach, advantage: "us"|"them"|"neutral"}}
- unique_to_them: Array of {{feature_name, description, strategic_relevance: "high"|"medium"|"low"}}
- unique_to_us: Array of {{feature_name, description, strategic_relevance: "high"|"medium"|"low"}}
- inferred_pains: Array of strings — customer pains they solve (from their marketing copy)
- inferred_benefits: Array of strings — benefits they claim
- positioning_summary: 2-3 sentence market positioning summary
- threat_level: "low"|"medium"|"high"|"critical"
- threat_reasoning: Why this threat level
- differentiation_opportunities: Array of strings — where we can stand out
- gaps_to_address: Array of strings — things they have we should consider

Return ONLY valid JSON, no markdown fences."""

        # ================================================================
        # Call LLM
        # ================================================================
        from anthropic import Anthropic

        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

        analysis_data = json.loads(raw_text)
        analysis = CompetitorDeepAnalysis(**analysis_data)

        # ================================================================
        # Store results
        # ================================================================
        supabase.table("competitor_references").update({
            "deep_analysis": analysis.model_dump(),
            "deep_analysis_status": "completed",
            "deep_analysis_at": datetime.now(timezone.utc).isoformat(),
            "scraped_pages": scraped_pages,
        }).eq("id", str(ref_id)).execute()

        # ================================================================
        # Create signal for pipeline
        # ================================================================
        competitor_name = competitor.get("name", "Unknown")
        report_markdown = _format_analysis_report(analysis, competitor_name)

        insert_signal(
            project_id=project_id,
            signal_type="research",
            source="competitor_intelligence",
            raw_text=report_markdown,
            metadata={
                "pipeline": "competitor_intelligence",
                "competitor_id": str(ref_id),
                "competitor_name": competitor_name,
            },
            run_id=uuid4(),
            source_label=f"Competitor Analysis: {competitor_name}",
        )

        logger.info(f"Completed deep analysis for competitor {competitor_name} ({ref_id})")
        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze competitor {ref_id}: {e}", exc_info=True)
        supabase.table("competitor_references").update({
            "deep_analysis_status": "failed",
        }).eq("id", str(ref_id)).execute()
        raise


def _format_analysis_report(analysis: CompetitorDeepAnalysis, name: str) -> str:
    """Format analysis as a markdown report for signal ingestion."""
    lines = [f"# Competitor Deep Analysis: {name}\n"]

    lines.append("## Positioning")
    lines.append(analysis.positioning_summary)
    lines.append(f"\n**Threat Level**: {analysis.threat_level}")
    lines.append(f"**Reasoning**: {analysis.threat_reasoning}\n")

    if analysis.feature_overlap:
        lines.append("## Feature Overlap")
        for f in analysis.feature_overlap:
            adv = f"(advantage: {f.advantage})" if f.advantage != "neutral" else ""
            lines.append(f"- **{f.feature_name}** {adv}")
            if f.our_approach:
                lines.append(f"  - Us: {f.our_approach}")
            if f.their_approach:
                lines.append(f"  - Them: {f.their_approach}")

    if analysis.unique_to_them:
        lines.append("\n## Unique to Them")
        for f in analysis.unique_to_them:
            lines.append(f"- **{f.feature_name}** [{f.strategic_relevance}]: {f.description}")

    if analysis.unique_to_us:
        lines.append("\n## Unique to Us")
        for f in analysis.unique_to_us:
            lines.append(f"- **{f.feature_name}** [{f.strategic_relevance}]: {f.description}")

    if analysis.inferred_pains:
        lines.append("\n## Inferred Customer Pains")
        for p in analysis.inferred_pains:
            lines.append(f"- {p}")

    if analysis.inferred_benefits:
        lines.append("\n## Claimed Benefits")
        for b in analysis.inferred_benefits:
            lines.append(f"- {b}")

    if analysis.differentiation_opportunities:
        lines.append("\n## Differentiation Opportunities")
        for d in analysis.differentiation_opportunities:
            lines.append(f"- {d}")

    if analysis.gaps_to_address:
        lines.append("\n## Gaps to Address")
        for g in analysis.gaps_to_address:
            lines.append(f"- {g}")

    return "\n".join(lines)
