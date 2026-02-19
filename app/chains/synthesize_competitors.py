"""Aggregate competitor synthesis chain.

Synthesizes insights across all analyzed competitors for a project into a
market landscape view with feature heatmap and positioning recommendations.
"""

import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.phase0 import insert_signal
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Output Schemas
# ============================================================================


class FeatureHeatmapRow(BaseModel):
    feature_area: str
    competitors: dict[str, str] = Field(default_factory=dict)  # name → "strong" | "basic" | "missing"
    our_status: str = "missing"  # "strong" | "basic" | "planned" | "missing"


class CompetitorThreat(BaseModel):
    competitor_name: str
    threat_level: str
    key_risk: str


class CompetitorSynthesis(BaseModel):
    market_landscape: str = ""
    feature_heatmap: list[FeatureHeatmapRow] = Field(default_factory=list)
    common_themes: list[str] = Field(default_factory=list)
    market_gaps: list[str] = Field(default_factory=list)
    positioning_recommendation: str = ""
    threat_summary: list[CompetitorThreat] = Field(default_factory=list)


# ============================================================================
# Main Chain
# ============================================================================


async def synthesize_competitors(project_id: UUID) -> CompetitorSynthesis:
    """
    Synthesize insights across all analyzed competitors for a project.

    Returns:
        CompetitorSynthesis with market landscape, heatmap, and recommendations
    """
    supabase = get_supabase()

    # Load all analyzed competitors
    refs_result = supabase.table("competitor_references").select(
        "id, name, deep_analysis, market_position, category"
    ).eq(
        "project_id", str(project_id)
    ).eq(
        "deep_analysis_status", "completed"
    ).execute()

    competitors = refs_result.data or []
    if not competitors:
        raise ValueError("No analyzed competitors found for synthesis")

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

    # ================================================================
    # Build LLM prompt
    # ================================================================
    competitor_sections = []
    for comp in competitors:
        analysis = comp.get("deep_analysis", {})
        competitor_sections.append(f"""### {comp['name']}
Market Position: {comp.get('market_position', 'unknown')}
Category: {comp.get('category', 'unknown')}
Positioning: {analysis.get('positioning_summary', 'N/A')}
Threat Level: {analysis.get('threat_level', 'unknown')}
Feature Overlap: {len(analysis.get('feature_overlap', []))} shared features
Unique to Them: {len(analysis.get('unique_to_them', []))} unique features
Inferred Pains: {', '.join(analysis.get('inferred_pains', [])[:5])}
Differentiation Opps: {', '.join(analysis.get('differentiation_opportunities', [])[:3])}
""")

    feature_list = "\n".join(
        f"- {f['name']} ({f.get('priority_group', 'unknown')}): {f.get('overview', '')[:80]}"
        for f in features
    )

    prompt = f"""Synthesize a cross-competitor market analysis. Return structured JSON.

## Our Project
Name: {project.get('name', 'Unknown')}
Vision: {project.get('vision', 'Not defined')}

### Our Features
{feature_list or 'No features defined yet'}

## Analyzed Competitors ({len(competitors)})
{''.join(competitor_sections)}

## Instructions
Return a JSON object with:
- market_landscape: 3-4 sentence overview of the competitive landscape
- feature_heatmap: Array of {{feature_area, competitors: {{competitor_name: "strong"|"basic"|"missing"}}, our_status: "strong"|"basic"|"planned"|"missing"}}
  - Include the top 8-12 most important feature areas across all competitors
- common_themes: Array of strings — patterns across competitors (3-5)
- market_gaps: Array of strings — opportunities nobody is addressing (3-5)
- positioning_recommendation: 2-3 sentences on where this project should position
- threat_summary: Array of {{competitor_name, threat_level, key_risk}} for each competitor

Return ONLY valid JSON, no markdown fences."""

    # ================================================================
    # Call LLM
    # ================================================================
    from anthropic import Anthropic

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "medium"},
    )

    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    synthesis_data = json.loads(raw_text)
    synthesis = CompetitorSynthesis(**synthesis_data)

    # ================================================================
    # Store as signal
    # ================================================================
    report_markdown = _format_synthesis_report(synthesis, project.get("name", "Unknown"))

    insert_signal(
        project_id=project_id,
        signal_type="research",
        source="competitor_intelligence_synthesis",
        raw_text=report_markdown,
        metadata={
            "pipeline": "competitor_intelligence_synthesis",
            "competitor_count": len(competitors),
            "competitor_names": [c["name"] for c in competitors],
        },
        run_id=uuid4(),
        source_label="Competitor Market Synthesis",
    )

    logger.info(f"Completed competitor synthesis for project {project_id} ({len(competitors)} competitors)")
    return synthesis


def _format_synthesis_report(synthesis: CompetitorSynthesis, project_name: str) -> str:
    """Format synthesis as markdown report for signal ingestion."""
    lines = [f"# Competitor Market Synthesis: {project_name}\n"]

    lines.append("## Market Landscape")
    lines.append(synthesis.market_landscape)

    if synthesis.common_themes:
        lines.append("\n## Common Themes")
        for t in synthesis.common_themes:
            lines.append(f"- {t}")

    if synthesis.market_gaps:
        lines.append("\n## Market Gaps")
        for g in synthesis.market_gaps:
            lines.append(f"- {g}")

    lines.append("\n## Positioning Recommendation")
    lines.append(synthesis.positioning_recommendation)

    if synthesis.threat_summary:
        lines.append("\n## Threat Summary")
        for t in synthesis.threat_summary:
            lines.append(f"- **{t.competitor_name}** [{t.threat_level}]: {t.key_risk}")

    if synthesis.feature_heatmap:
        lines.append("\n## Feature Heatmap")
        for row in synthesis.feature_heatmap:
            comp_str = ", ".join(f"{k}: {v}" for k, v in row.competitors.items())
            lines.append(f"- **{row.feature_area}** (us: {row.our_status}) — {comp_str}")

    return "\n".join(lines)
