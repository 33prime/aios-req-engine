"""Creative Brief Extraction Agent.

Extracts client context and project details from signals to auto-populate
the creative brief. Runs on every signal to fill gaps in the brief.

Fields extracted:
- client_name: Company name
- industry: Industry/vertical
- website: Client website URL
- competitors: Competitor names mentioned
- focus_areas: Key areas of concern/interest
- target_users: Target user types mentioned
- success_metrics: KPIs and success criteria
- constraints: Budget, timeline, technical constraints
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.creative_briefs import get_creative_brief, upsert_creative_brief

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an expert at extracting client and project context from business communications.

Analyze the provided content and extract information that would help build a creative brief for a software project.

Extract the following if mentioned:
1. **client_name**: The name of the client company (not individuals)
2. **industry**: The industry or vertical (e.g., "Healthcare SaaS", "E-commerce", "FinTech", "HR Tech")
3. **website**: Client's website URL if mentioned
4. **competitors**: Names of competitor products or companies mentioned
5. **focus_areas**: Key areas of concern, priorities, or pain points the client emphasizes
6. **target_users**: Types of users who will use the product (e.g., "sales managers", "nurses", "small business owners")
7. **success_metrics**: KPIs, goals, or success criteria mentioned
8. **constraints**: Any constraints mentioned (budget, timeline, technical requirements, compliance)

IMPORTANT RULES:
- Only extract information that is EXPLICITLY stated or strongly implied
- For client_name, extract the COMPANY name, not individual person names
- Be conservative - don't guess if something isn't clearly mentioned
- Competitors should be actual product/company names, not generic terms
- Focus areas should be specific concerns, not generic business goals
- Set confidence based on how explicitly the information was stated

Output ONLY valid JSON:
{
  "client_name": "string or null",
  "industry": "string or null",
  "website": "string or null",
  "competitors": ["list of competitor names"] or [],
  "focus_areas": ["list of focus areas"] or [],
  "target_users": ["list of user types"] or [],
  "success_metrics": ["list of metrics/KPIs"] or [],
  "constraints": {
    "budget": "string or null",
    "timeline": "string or null",
    "technical": ["list of technical constraints"] or [],
    "compliance": ["list of compliance requirements"] or []
  },
  "confidence": 0.0-1.0,
  "extraction_notes": "Brief explanation of what was found"
}
"""


def extract_creative_brief_from_signal(
    project_id: UUID,
    signal_id: UUID,
    content: str,
    auto_apply: bool = True,
) -> dict[str, Any]:
    """
    Extract creative brief data from signal content.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID for provenance tracking
        content: Signal content text
        auto_apply: If True, automatically update the creative brief

    Returns:
        Dict with extracted fields and metadata
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # Get current brief to understand what's missing
        current_brief = get_creative_brief(project_id)
        current_fields = _get_current_field_status(current_brief)

        # Build context about what we need
        user_prompt = f"""Current creative brief status:
{current_fields}

Content to analyze:
---
{content[:12000]}
---

Extract any creative brief information from this content. Focus especially on fields that are currently empty or could be enriched."""

        response = client.chat.completions.create(
            model=settings.FACTS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        extracted = _parse_extraction(raw_output)

        if not extracted:
            logger.info(
                f"No creative brief data extracted from signal {signal_id}",
                extra={"project_id": str(project_id), "signal_id": str(signal_id)},
            )
            return {
                "extracted": False,
                "fields_found": [],
                "applied": False,
            }

        # Determine which fields have new data
        fields_found = _get_extracted_fields(extracted, current_brief)

        logger.info(
            f"Extracted creative brief data: {fields_found}",
            extra={
                "project_id": str(project_id),
                "signal_id": str(signal_id),
                "fields_found": fields_found,
                "confidence": extracted.get("confidence", 0),
            },
        )

        # Auto-apply if enabled and we found something useful
        applied = False
        if auto_apply and fields_found and extracted.get("confidence", 0) >= 0.5:
            applied = _apply_extraction(project_id, signal_id, extracted, current_brief)

        return {
            "extracted": True,
            "fields_found": fields_found,
            "applied": applied,
            "data": extracted,
            "confidence": extracted.get("confidence", 0),
        }

    except Exception as e:
        logger.error(
            f"Failed to extract creative brief from signal {signal_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id), "signal_id": str(signal_id)},
        )
        return {
            "extracted": False,
            "error": str(e),
            "fields_found": [],
            "applied": False,
        }


def extract_from_client_info(
    project_id: UUID,
    signal_id: UUID,
    client_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply client_info extracted by fact extraction to creative brief.

    The fact extraction agent already extracts client_info. This function
    takes that output and applies it to the creative brief.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        client_info: Client info dict from fact extraction

    Returns:
        Dict with application result
    """
    if not client_info:
        return {"applied": False, "reason": "No client_info provided"}

    current_brief = get_creative_brief(project_id)

    # Map client_info fields to creative brief fields
    extracted = {
        "client_name": client_info.get("client_name"),
        "industry": client_info.get("industry"),
        "website": client_info.get("website"),
        "competitors": client_info.get("competitors", []),
        "confidence": _confidence_to_float(client_info.get("confidence", "medium")),
    }

    fields_found = _get_extracted_fields(extracted, current_brief)

    if not fields_found:
        return {"applied": False, "reason": "No new fields to apply"}

    applied = _apply_extraction(project_id, signal_id, extracted, current_brief)

    logger.info(
        f"Applied client_info to creative brief: {fields_found}",
        extra={
            "project_id": str(project_id),
            "signal_id": str(signal_id),
            "fields_found": fields_found,
        },
    )

    return {
        "applied": applied,
        "fields_found": fields_found,
    }


def _get_current_field_status(brief: dict | None) -> str:
    """Build a summary of current brief status for the prompt."""
    if not brief:
        return "No creative brief exists yet - all fields are empty."

    lines = []

    if brief.get("client_name"):
        lines.append(f"- client_name: '{brief['client_name']}' (filled)")
    else:
        lines.append("- client_name: EMPTY (needed)")

    if brief.get("industry"):
        lines.append(f"- industry: '{brief['industry']}' (filled)")
    else:
        lines.append("- industry: EMPTY (needed)")

    if brief.get("website"):
        lines.append(f"- website: '{brief['website']}' (filled)")
    else:
        lines.append("- website: EMPTY")

    competitors = brief.get("competitors") or []
    if competitors:
        lines.append(f"- competitors: {len(competitors)} known ({', '.join(competitors[:3])}...)")
    else:
        lines.append("- competitors: EMPTY")

    focus_areas = brief.get("focus_areas") or []
    if focus_areas:
        lines.append(f"- focus_areas: {len(focus_areas)} known")
    else:
        lines.append("- focus_areas: EMPTY")

    return "\n".join(lines)


def _parse_extraction(raw_output: str) -> dict | None:
    """Parse the LLM extraction output."""
    try:
        # Handle potential markdown wrapping
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse creative brief extraction: {e}")
        return None


def _get_extracted_fields(extracted: dict, current_brief: dict | None) -> list[str]:
    """Determine which fields have new data."""
    fields_found = []
    current = current_brief or {}

    # Check scalar fields
    scalar_fields = ["client_name", "industry", "website"]
    for field in scalar_fields:
        new_value = extracted.get(field)
        current_value = current.get(field)

        if new_value and (not current_value or len(str(new_value)) > len(str(current_value or ""))):
            fields_found.append(field)

    # Check array fields
    array_fields = ["competitors", "focus_areas", "target_users", "success_metrics"]
    for field in array_fields:
        new_items = extracted.get(field, [])
        current_items = current.get(field, [])

        if new_items:
            # Check if there are new items not in current
            current_lower = {str(i).lower() for i in current_items}
            new_unique = [i for i in new_items if str(i).lower() not in current_lower]
            if new_unique:
                fields_found.append(field)

    # Check constraints
    constraints = extracted.get("constraints", {})
    if constraints:
        if constraints.get("budget") or constraints.get("timeline"):
            fields_found.append("constraints")
        if constraints.get("technical"):
            fields_found.append("technical_constraints")
        if constraints.get("compliance"):
            fields_found.append("compliance_requirements")

    return fields_found


def _apply_extraction(
    project_id: UUID,
    signal_id: UUID,
    extracted: dict,
    current_brief: dict | None,
) -> bool:
    """Apply extracted data to the creative brief."""
    try:
        update_data = {}
        current = current_brief or {}

        # Only update scalar fields if they're empty or new value is better
        for field in ["client_name", "industry", "website"]:
            new_value = extracted.get(field)
            current_value = current.get(field)

            if new_value:
                # Only update if current is empty OR if source was also extracted
                field_sources = current.get("field_sources", {})
                if not current_value or field_sources.get(field) != "user":
                    update_data[field] = new_value

        # Merge array fields
        for field in ["competitors", "focus_areas"]:
            new_items = extracted.get(field, [])
            if new_items:
                update_data[field] = new_items

        # Handle target_users -> focus_areas (map to existing field)
        target_users = extracted.get("target_users", [])
        if target_users:
            # Add as focus areas with "Target: " prefix
            user_focus = [f"Target users: {u}" for u in target_users]
            update_data.setdefault("focus_areas", []).extend(user_focus)

        # Handle success_metrics -> custom_questions (map to existing field)
        success_metrics = extracted.get("success_metrics", [])
        if success_metrics:
            # Add as custom questions
            metric_questions = [f"How to measure: {m}" for m in success_metrics]
            update_data.setdefault("custom_questions", []).extend(metric_questions)

        if not update_data:
            return False

        upsert_creative_brief(
            project_id=project_id,
            data=update_data,
            source="extracted",
            signal_id=signal_id,
        )

        return True

    except Exception as e:
        logger.error(f"Failed to apply creative brief extraction: {e}")
        return False


def _confidence_to_float(confidence: str | float) -> float:
    """Convert confidence string to float."""
    if isinstance(confidence, (int, float)):
        return float(confidence)

    mapping = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.9,
    }
    return mapping.get(confidence.lower(), 0.5)


async def run_creative_brief_extraction(
    project_id: UUID,
    signal_id: UUID,
    content: str,
) -> dict[str, Any]:
    """
    Async wrapper for creative brief extraction.

    Used by the signal pipeline for integration.
    """
    return extract_creative_brief_from_signal(
        project_id=project_id,
        signal_id=signal_id,
        content=content,
        auto_apply=True,
    )
