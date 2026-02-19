"""Constraint inference chain.

Analyzes project context (industry, data entities, features, workflows)
to suggest constraints that may not have been explicitly stated.
Creates constraints with source='ai_inferred'.
"""

import json
import logging
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def infer_constraints(project_id: UUID) -> list[dict[str, Any]]:
    """
    Analyze project context to suggest constraints.

    Looks at:
    - Industry (regulatory implications)
    - Data entities (PII, sensitivity)
    - Features (complexity, scale)
    - Workflows (integration points)

    Returns list of suggested constraint dicts (not yet persisted).
    """
    client = get_supabase()

    # Load project context
    try:
        # Company info for industry context
        ci_result = client.table("company_info").select(
            "name, industry, company_type, industry_display"
        ).eq("project_id", str(project_id)).maybe_single().execute()
        company_info = ci_result.data if ci_result and ci_result.data else {}

        # Data entities for PII/sensitivity
        de_result = client.table("data_entities").select(
            "id, name, description, entity_category, fields, pii_flags"
        ).eq("project_id", str(project_id)).execute()
        data_entities = de_result.data or []

        # Features for scope context
        feat_result = client.table("features").select(
            "id, name, category, priority_group"
        ).eq("project_id", str(project_id)).execute()
        features = feat_result.data or []

        # Existing constraints to avoid duplicates
        existing_result = client.table("constraints").select(
            "title, constraint_type"
        ).eq("project_id", str(project_id)).execute()
        existing = existing_result.data or []
        existing_titles = {c["title"].lower() for c in existing}

    except Exception as e:
        logger.error(f"Failed to load project context for constraint inference: {e}")
        return []

    # Build context for Sonnet
    industry = company_info.get("industry_display") or company_info.get("industry") or "Unknown"
    entity_names = [de["name"] for de in data_entities]
    entity_fields_summary = []
    for de in data_entities[:10]:
        fields = de.get("fields") or []
        field_names = [f.get("name", "") for f in fields[:5]] if isinstance(fields, list) else []
        pii = de.get("pii_flags") or []
        entity_fields_summary.append(
            f"- {de['name']} ({de.get('entity_category', 'domain')}): fields={field_names}, PII={pii}"
        )

    feature_names = [f["name"] for f in features[:20]]
    existing_constraint_summary = [f"- {c['title']} ({c.get('constraint_type', '')})" for c in existing[:15]]

    prompt = f"""You are a senior requirements consultant. Analyze the following project context and suggest constraints that may not have been explicitly stated.

Industry: {industry}
Company: {company_info.get('name', 'Unknown')}

Data Entities ({len(data_entities)}):
{chr(10).join(entity_fields_summary) if entity_fields_summary else 'None defined yet'}

Features ({len(features)}):
{', '.join(feature_names) if feature_names else 'None defined yet'}

Existing Constraints:
{chr(10).join(existing_constraint_summary) if existing_constraint_summary else 'None yet'}

Based on the industry, data entities (especially PII), and features, suggest 2-5 NEW constraints that the team should consider. DO NOT duplicate existing constraints.

For each constraint, categorize it as one of: budget, timeline, regulatory, organizational, technical, strategic

Return JSON array only:
[
  {{
    "title": "<concise constraint title>",
    "description": "<1-2 sentence description of the constraint and its impact>",
    "constraint_type": "<budget|timeline|regulatory|organizational|technical|strategic>",
    "severity": "<critical|high|medium|low>",
    "confidence": <0.0-1.0 float — how confident you are this is relevant>,
    "impact_description": "<brief description of what happens if this constraint is ignored>"
  }}
]"""

    try:
        from anthropic import AsyncAnthropic
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("No Anthropic API key for constraint inference")
            return []

        anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text if response.content else "[]"

        # Parse JSON
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            suggestions = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Failed to parse constraint inference response: {text[:200]}")
            return []

        if not isinstance(suggestions, list):
            return []

        # Filter out duplicates
        results = []
        for s in suggestions:
            if not isinstance(s, dict) or not s.get("title"):
                continue
            if s["title"].lower() in existing_titles:
                continue
            results.append({
                "title": s["title"],
                "description": s.get("description", ""),
                "constraint_type": s.get("constraint_type", "technical"),
                "severity": s.get("severity", "medium"),
                "confidence": s.get("confidence", 0.7),
                "impact_description": s.get("impact_description", ""),
                "source": "ai_inferred",
            })

        # Persist as ai_generated constraints
        for c in results:
            try:
                client.table("constraints").insert({
                    "project_id": str(project_id),
                    "title": c["title"],
                    "description": c["description"],
                    "constraint_type": c["constraint_type"],
                    "severity": c["severity"],
                    "confidence": c["confidence"],
                    "impact_description": c["impact_description"],
                    "source": "ai_inferred",
                    "confirmation_status": "ai_generated",
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to insert inferred constraint: {e}")

        return results

    except Exception as e:
        logger.error(f"Constraint inference failed for project {project_id}: {e}")
        return []
