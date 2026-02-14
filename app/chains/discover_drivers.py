"""Phase 7: Evidence-Based Business Drivers — Sonnet synthesis.

Synthesizes business drivers ONLY from real evidence collected in Phases 2-6.
Produces drivers with relationship context for entity linking.
"""

import json
import logging
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DRIVER_SYNTHESIS_PROMPT = """You are synthesizing business drivers from REAL evidence gathered about a company.
Every driver MUST be backed by evidence from the provided data. NEVER generate facts that aren't supported.

## Context

Company: {company_name}
Industry: {industry}
{vision_section}

## Existing Project Entities (for relationship matching)
Personas: {persona_names}
Workflow Steps: {workflow_labels}
Features: {feature_names}

## Evidence Sources

### Company Profile
{company_evidence}

### Competitor Intelligence
{competitor_evidence}

### Market Data
{market_evidence}

### User Voice (Reviews & Forums)
{user_voice_evidence}

### Feature Analysis
{feature_analysis}

## Instructions

Synthesize business drivers from the evidence above. For each driver:

1. **Type**: pain (problem/friction), goal (desired outcome), or kpi (measurable metric)
2. **Description**: Clear, specific description backed by evidence
3. **Evidence**: Array of source citations with URL and exact quote
4. **Relationship Context**: Match to existing project entities by name
   - `related_actor`: Which persona from the list above experiences this? (exact name or null)
   - `related_process`: Which workflow step from the list above does this relate to? (exact label or null)
   - `addresses_feature`: Which feature from the list above addresses this? (exact name or null)
5. **Type-specific fields**:
   - For pains: severity (critical/high/medium/low), business_impact, affected_users
   - For KPIs: baseline_value, target_value
   - For goals: success_criteria

Return JSON:
{{
    "drivers": [
        {{
            "driver_type": "pain|goal|kpi",
            "description": "...",
            "evidence": [
                {{"source_url": "...", "quote": "exact text", "source_type": "g2_review|firecrawl|pdl|reddit|capterra", "confidence": 0.85}}
            ],
            "synthesis_rationale": "Why this driver was identified from the evidence",
            "related_actor": "Persona Name or null",
            "related_process": "Step Label or null",
            "addresses_feature": "Feature Name or null",
            "severity": "high",
            "business_impact": "$50K/mo in staff time",
            "affected_users": "All operations staff",
            "baseline_value": null,
            "target_value": null,
            "success_criteria": null
        }}
    ]
}}

Generate 5-15 drivers. Prioritize pains backed by multiple independent sources.
"""


def _format_evidence_section(items: list[dict[str, Any]], label: str) -> str:
    """Format evidence items into readable text for the prompt."""
    if not items:
        return f"No {label} data available."

    parts = []
    for item in items[:20]:  # Cap at 20 items
        if isinstance(item, dict):
            content = item.get("content") or item.get("description") or item.get("quote", "")
            url = item.get("source_url") or item.get("url", "")
            parts.append(f"- {content[:200]} [Source: {url}]")
        elif isinstance(item, str):
            parts.append(f"- {item[:200]}")
    return "\n".join(parts) if parts else f"No {label} data available."


async def run_driver_synthesis(
    company_name: str,
    industry: str | None,
    project_vision: str | None,
    persona_names: list[str],
    workflow_labels: list[str],
    feature_names: list[str],
    company_profile: dict[str, Any],
    competitors: list[dict[str, Any]],
    market_evidence: list[dict[str, Any]],
    user_voice: list[dict[str, Any]],
    feature_matrix: dict[str, Any],
    gap_analysis: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute Phase 7: Evidence-Based Business Driver Synthesis.

    Returns:
        Tuple of (business_drivers, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key, cannot synthesize drivers")
        return [], cost_entries

    from anthropic import AsyncAnthropic

    # Format company evidence
    company_parts = []
    if company_profile:
        company_parts.append(f"Name: {company_profile.get('name', company_name)}")
        if company_profile.get("employee_count"):
            company_parts.append(f"Employees: {company_profile['employee_count']}")
        if company_profile.get("revenue_range"):
            company_parts.append(f"Revenue: {company_profile['revenue_range']}")
        if company_profile.get("description"):
            company_parts.append(f"Description: {company_profile['description']}")
        for ev in company_profile.get("evidence", [])[:5]:
            company_parts.append(f"- \"{ev.get('quote', '')}\" [Source: {ev.get('source_url', '')}]")
    company_evidence = "\n".join(company_parts) or "No company data."

    # Format competitor evidence
    comp_parts = []
    for c in competitors[:5]:
        comp_parts.append(f"\n**{c.get('name', '?')}** ({c.get('employee_count', '?')} employees)")
        for ev in c.get("evidence", [])[:3]:
            comp_parts.append(f"  - \"{ev.get('quote', '')}\" [Source: {ev.get('source_url', '')}]")
        if c.get("strengths"):
            comp_parts.append(f"  Strengths: {', '.join(c['strengths'][:3])}")
        if c.get("weaknesses"):
            comp_parts.append(f"  Weaknesses: {', '.join(c['weaknesses'][:3])}")
    competitor_evidence = "\n".join(comp_parts) or "No competitor data."

    # Format market evidence
    market_text = _format_evidence_section(market_evidence, "market")

    # Format user voice
    user_voice_text = _format_evidence_section(user_voice, "user voice")

    # Format feature analysis
    feature_text_parts = []
    if feature_matrix and feature_matrix.get("features"):
        for f in feature_matrix["features"][:10]:
            feature_text_parts.append(
                f"- {f.get('name', '?')}: table_stakes={f.get('table_stakes', '?')}"
            )
    for gap in gap_analysis[:5]:
        feature_text_parts.append(f"- GAP: {gap}")
    feature_text = "\n".join(feature_text_parts) or "No feature analysis data."

    # Vision section
    vision_section = f"Project Vision: {project_vision}" if project_vision else ""

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": DRIVER_SYNTHESIS_PROMPT.format(
                    company_name=company_name,
                    industry=industry or "Unknown",
                    vision_section=vision_section,
                    persona_names=", ".join(persona_names) if persona_names else "None yet",
                    workflow_labels=", ".join(workflow_labels) if workflow_labels else "None yet",
                    feature_names=", ".join(feature_names) if feature_names else "None yet",
                    company_evidence=company_evidence,
                    competitor_evidence=competitor_evidence,
                    market_evidence=market_text,
                    user_voice_evidence=user_voice_text,
                    feature_analysis=feature_text,
                ),
            }],
        )
        cost_entries.append({
            "phase": "business_drivers",
            "service": "anthropic_sonnet",
            "cost_usd": 0.12,
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
        drivers = parsed.get("drivers", [])

        logger.info(
            f"Driver synthesis complete: {len(drivers)} drivers "
            f"({sum(1 for d in drivers if d.get('driver_type') == 'pain')} pains, "
            f"{sum(1 for d in drivers if d.get('driver_type') == 'goal')} goals, "
            f"{sum(1 for d in drivers if d.get('driver_type') == 'kpi')} KPIs)"
        )

        return drivers, cost_entries

    except Exception as e:
        logger.warning(f"Driver synthesis failed: {e}")
        return [], cost_entries
