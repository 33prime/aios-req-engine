"""Vision clarity analysis chain.

Scores a vision statement on conciseness, measurability, completeness, and alignment.
Stores result in projects.vision_analysis.
"""

import json
import logging
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def analyze_vision_clarity(project_id: UUID, vision_text: str) -> dict[str, Any]:
    """
    Analyze a vision statement for clarity using Sonnet.

    Scores: conciseness (0-1), measurability (0-1), completeness (0-1), alignment (0-1)
    Also generates improvement suggestions.

    Returns the analysis dict and stores it in projects.vision_analysis.
    """
    if not vision_text or len(vision_text.strip()) < 10:
        return {}

    client = get_supabase()

    # Load features for alignment check
    features_result = client.table("features").select(
        "id, name, category"
    ).eq("project_id", str(project_id)).execute()

    feature_names = [f["name"] for f in (features_result.data or [])]
    feature_context = ", ".join(feature_names[:20]) if feature_names else "No features defined yet"

    prompt = f"""Analyze this product vision statement for clarity and quality. Score each dimension from 0.0 to 1.0.

Vision: "{vision_text}"

Current features: {feature_context}

Return JSON only:
{{
  "conciseness": <0-1 float — is it clear and focused, not rambling?>,
  "measurability": <0-1 float — does it define or imply measurable outcomes?>,
  "completeness": <0-1 float — does it cover who, what, why, and for whom?>,
  "alignment": <0-1 float — how well does it align with the listed features?>,
  "overall_score": <0-1 float — weighted average>,
  "suggestions": [<1-3 specific improvement suggestions as strings>],
  "summary": "<1-sentence assessment>"
}}"""

    try:
        from anthropic import AsyncAnthropic
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("No Anthropic API key for vision analysis")
            return {}

        anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text if response.content else "{}"

        # Parse JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            analysis = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Failed to parse vision analysis response: {text[:200]}")
            return {}

        # Store in projects table
        try:
            client.table("projects").update({
                "vision_analysis": analysis,
            }).eq("id", str(project_id)).execute()
        except Exception as e:
            logger.warning(f"Failed to store vision analysis: {e}")

        return analysis

    except Exception as e:
        logger.error(f"Vision analysis failed for project {project_id}: {e}")
        return {}
