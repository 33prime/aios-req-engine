"""Detect derivative business drivers from a promoted unlock.

Single Haiku call: given an unlock's narrative + provenance, identify new
pains, goals, or KPIs that this capability reveals. ~$0.0002 per call.
"""

import json
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def detect_derivative_drivers(unlock: dict, project_id: UUID) -> list[dict]:
    """Detect new pains/goals/KPIs that a promoted unlock reveals.

    Args:
        unlock: Full unlock dict with title, narrative, provenance, tier
        project_id: Project UUID (for loading existing drivers to avoid dupes)

    Returns:
        List of dicts: {driver_type, description, parent_driver_id?}
    """
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()

    # Build context from unlock
    title = unlock.get("title", "")
    narrative = unlock.get("narrative", "")
    provenance = unlock.get("provenance") or []
    tier = unlock.get("tier", "unknown")

    provenance_text = ""
    parent_driver_ids = []
    for link in provenance:
        if isinstance(link, dict):
            etype = link.get("entity_type", "")
            ename = link.get("entity_name", "")
            erel = link.get("relationship", "")
            provenance_text += f"- {etype}: {ename} ({erel})\n"
            if etype in ("pain", "goal", "kpi"):
                parent_driver_ids.append(link.get("entity_id"))

    prompt = (
        "Analyze this newly promoted unlock and identify 0-3 derivative "
        "business drivers (new pains, goals, or KPIs) that implementing "
        "this capability would REVEAL or CREATE.\n\n"
        f"UNLOCK: {title}\n"
        f"NARRATIVE: {narrative}\n"
        f"TIER: {tier}\n"
        f"PROVENANCE:\n{provenance_text}\n"
        "Rules:\n"
        "- Only NEW consequences of building this\n"
        "- Each: distinct business impact\n"
        "- Empty array if no cascading effects\n"
        "- One sentence per description\n\n"
        'Return JSON: [{{"driver_type": "pain|goal|kpi", '
        '"description": "..."}}]\n'
        "Return [] if none detected."
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Extract JSON from response
        if "[]" in text and len(text) < 10:
            return []

        # Find JSON array in response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            return []

        drivers = json.loads(text[start:end])

        # Validate and enrich
        result = []
        for d in drivers:
            if not isinstance(d, dict):
                continue
            dtype = d.get("driver_type", "")
            desc = d.get("description", "")
            if dtype not in ("pain", "goal", "kpi") or not desc:
                continue

            entry = {"driver_type": dtype, "description": desc}

            # Link to parent driver if provenance had one of the same type
            if parent_driver_ids:
                entry["parent_driver_id"] = UUID(parent_driver_ids[0])

            result.append(entry)

        uid = unlock.get("id", "?")
        logger.info(f"Detected {len(result)} derivative drivers from unlock {uid}")
        return result[:3]

    except Exception as e:
        logger.warning(f"Derivative driver detection failed: {e}")
        return []
