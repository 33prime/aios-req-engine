"""Synthesize session feedback into actionable changes per feature.

Combines consultant and client feedback with overlay data to produce
a structured synthesis identifying confirmed requirements, new requirements,
contradictions, and code changes needed.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import FeedbackSynthesis

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are synthesizing feedback from a prototype review session into actionable changes. \
You have consultant observations/requirements, client responses, and current feature state.

For each feature with feedback, produce:
1. confirmed_requirements: Things both consultant and client agree on
2. new_requirements: New things discovered during the session
3. contradictions: Where consultant and client disagree (with suggested resolution)
4. questions_resolved: Which overlay questions were answered
5. code_changes: Specific code changes needed (file, what, why, priority)
6. recommended_status: Updated confirmation status for AIOS

Also identify:
- new_features_discovered: Features not in AIOS that emerged from feedback
- high_priority_changes: Changes that should be made immediately
- session_summary: Human-readable summary

Output ONLY valid JSON:
{
  "by_feature": {
    "<feature_id>": {
      "feature_id": "...",
      "confirmed_requirements": ["..."],
      "new_requirements": ["..."],
      "contradictions": [{"consultant_said": "...", "client_said": "...", "resolution": "..."}],
      "questions_resolved": [{"question_id": "...", "answer": "...", "source": "consultant|client"}],
      "code_changes": [{"file": "...", "what_to_change": "...", "why": "...", "priority": "high|medium|low"}],
      "recommended_status": "confirmed_consultant|confirmed_client|needs_client|ai_generated"
    }
  },
  "new_features_discovered": [{"name": "...", "description": "...", "source": "..."}],
  "high_priority_changes": [{"description": "...", "feature_id": "...", "reason": "..."}],
  "session_summary": "..."
}
"""


def synthesize_session_feedback(
    feedback_items: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
    features: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> FeedbackSynthesis:
    """Synthesize all feedback from a session.

    Args:
        feedback_items: All feedback records for the session
        overlays: Current overlay data for the prototype
        features: AIOS features for the project
        settings: App settings
        model_override: Optional model override

    Returns:
        FeedbackSynthesis with per-feature breakdown
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    logger.info(f"Synthesizing {len(feedback_items)} feedback items using {model}")

    # Group feedback by feature
    by_feature: dict[str, list[dict]] = {}
    general_feedback = []
    for fb in feedback_items:
        fid = fb.get("feature_id")
        if fid:
            by_feature.setdefault(fid, []).append(fb)
        else:
            general_feedback.append(fb)

    # Build feature context map
    feature_map = {f["id"]: f for f in features}
    overlay_map = {
        o.get("feature_id"): o for o in overlays if o.get("feature_id")
    }

    user_message = f"""## Session Feedback ({len(feedback_items)} items)

### Feedback by Feature
{json.dumps({fid: [{"source": fb["source"], "type": fb.get("feedback_type"), "content": fb["content"]} for fb in fbs] for fid, fbs in by_feature.items()}, indent=2, default=str)}

### General Feedback (not tied to a feature)
{json.dumps([{"source": fb["source"], "type": fb.get("feedback_type"), "content": fb["content"]} for fb in general_feedback], indent=2, default=str)}

### Current Feature State
{json.dumps([{"id": f["id"], "name": f["name"], "confirmation_status": f.get("confirmation_status")} for f in features], indent=2, default=str)}

### Current Overlay Data
{json.dumps([{"feature_id": o.get("feature_id"), "status": o.get("status"), "gaps_count": o.get("gaps_count")} for o in overlays], indent=2, default=str)}

Synthesize this feedback into actionable changes.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json") :]
    if response_text.startswith("```"):
        response_text = response_text[len("```") :]
    if response_text.endswith("```"):
        response_text = response_text[: -len("```")]
    parsed = json.loads(response_text.strip())
    synthesis = FeedbackSynthesis(**parsed)

    logger.info(
        f"Synthesis complete: {len(synthesis.by_feature)} features, "
        f"{len(synthesis.new_features_discovered)} new features, "
        f"{len(synthesis.high_priority_changes)} high-priority changes"
    )
    return synthesis
