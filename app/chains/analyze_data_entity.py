"""Data entity analysis chain.

Analyzes a data entity's fields, workflow links, and project context
to provide intelligence: sensitivity, PII, AI opportunities, system design notes.
Stores result in data_entities.enrichment_data.
"""

import json
import logging
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def analyze_data_entity(entity_id: UUID, project_id: UUID) -> dict[str, Any]:
    """
    Analyze a data entity for sensitivity, PII, design recommendations.

    Returns enrichment dict and stores it in data_entities.enrichment_data.
    """
    client = get_supabase()

    try:
        # Load entity
        entity_result = client.table("data_entities").select(
            "id, name, description, entity_category, fields"
        ).eq("id", str(entity_id)).single().execute()

        if not entity_result.data:
            return {}

        entity = entity_result.data

        # Load workflow links
        links_result = client.table("data_entity_workflow_steps").select(
            "operation_type, vp_step_id"
        ).eq("data_entity_id", str(entity_id)).execute()
        workflow_links = links_result.data or []

        # Load step labels for context
        step_ids = [l["vp_step_id"] for l in workflow_links if l.get("vp_step_id")]
        step_labels: dict[str, str] = {}
        if step_ids:
            steps_result = client.table("vp_steps").select(
                "id, label"
            ).in_("id", step_ids).execute()
            for s in (steps_result.data or []):
                step_labels[s["id"]] = s.get("label", "")

        # Load features for context
        features_result = client.table("features").select(
            "name"
        ).eq("project_id", str(project_id)).limit(15).execute()
        feature_names = [f["name"] for f in (features_result.data or [])]

        # Build context
        fields = entity.get("fields") or []
        field_summary = []
        for f in fields[:30]:
            if isinstance(f, dict):
                field_summary.append(
                    f"{f.get('name', '?')} ({f.get('type', 'text')})"
                    + (" [required]" if f.get("required") else "")
                )

        link_summary = []
        for l in workflow_links:
            step_label = step_labels.get(l.get("vp_step_id", ""), "Unknown Step")
            link_summary.append(f"{l.get('operation_type', '?').upper()} in '{step_label}'")

    except Exception as e:
        logger.error(f"Failed to load data for entity analysis: {e}")
        return {}

    prompt = f"""You are a data architecture consultant. Analyze this data entity and provide intelligence.

Entity: {entity.get('name', 'Unknown')}
Category: {entity.get('entity_category', 'domain')}
Description: {entity.get('description', 'No description')}

Fields ({len(fields)}):
{chr(10).join(field_summary) if field_summary else 'No fields defined'}

Workflow Operations:
{chr(10).join(link_summary) if link_summary else 'No workflow links'}

Project Features: {', '.join(feature_names[:15]) if feature_names else 'None'}

Analyze and return JSON only:
{{
  "sensitivity_level": "<low|medium|high|critical>",
  "pii_fields": [<field names that may contain PII/sensitive data>],
  "ai_opportunities": [<1-3 specific ways AI could enhance this entity>],
  "system_design_notes": "<1-2 sentences on system design considerations>",
  "relationship_suggestions": [
    {{"target_entity": "<name>", "relationship_type": "<has_many|belongs_to|references>", "rationale": "<why>"}}
  ],
  "validation_suggestions": [<1-3 field validation rules that should be enforced>]
}}"""

    try:
        from anthropic import AsyncAnthropic
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("No Anthropic API key for data entity analysis")
            return {}

        anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text if response.content else "{}"

        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            analysis = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Failed to parse data entity analysis: {text[:200]}")
            return {}

        # Store in data_entities
        try:
            client.table("data_entities").update({
                "enrichment_data": analysis,
                "enrichment_status": "enriched",
                "enrichment_attempted_at": "now()",
                "pii_flags": analysis.get("pii_fields", []),
                "relationships": analysis.get("relationship_suggestions", []),
            }).eq("id", str(entity_id)).execute()
        except Exception as e:
            logger.warning(f"Failed to store data entity enrichment: {e}")

        return analysis

    except Exception as e:
        logger.error(f"Data entity analysis failed for {entity_id}: {e}")
        # Mark as failed
        try:
            client.table("data_entities").update({
                "enrichment_status": "failed",
                "enrichment_attempted_at": "now()",
            }).eq("id", str(entity_id)).execute()
        except Exception:
            pass
        return {}
