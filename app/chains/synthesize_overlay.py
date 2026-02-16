"""DEPRECATED: Replaced by analyze_feature_overlay.py which produces
OverlayContent directly from a single LLM call with prompt caching.

Synthesize analysis + questions + AIOS context into overlay card content.

Combines feature analysis, generated questions, and AIOS context into the
final OverlayContent object shown in the feature overlay panel.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    BusinessRule,
    Dependency,
    FeatureAnalysis,
    GeneratedQuestion,
    OverlayContent,
    OverlayQuestion,
    PersonaRef,
    UploadSuggestion,
)

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are synthesizing feature overlay content for a prototype review interface. \
Combine the analysis results, generated questions, persona context, and journey \
position into a structured overlay card.

Determine:
1. STATUS: "understood" (>80% confidence, <2 gaps), "partial" (50-80%), "unknown" (<50%)
2. GAPS COUNT: Number of unanswered high/medium questions + unconfirmed rules
3. UPLOAD SUGGESTIONS: Documents that would fill gaps (e.g., "API spec for auth provider")
4. IMPLEMENTATION NOTES: Practical notes for developers

Output ONLY valid JSON matching this schema:
{
  "status": "understood|partial|unknown",
  "confidence": 0.0-1.0,
  "gaps_count": 0,
  "implementation_notes": "...",
  "upload_suggestions": [{"title": "...", "description": "...", "priority": "high|medium|low"}]
}
"""


def synthesize_overlay(
    feature: dict[str, Any],
    analysis: FeatureAnalysis,
    questions: list[GeneratedQuestion],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> OverlayContent:
    """Synthesize overlay content from analysis and context.

    Args:
        feature: AIOS feature record
        analysis: Feature analysis results
        questions: Generated questions for this feature
        personas: All project personas
        vp_steps: All VP steps (for flow position)
        settings: App settings
        model_override: Optional model override

    Returns:
        OverlayContent for display in the overlay panel
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    feature_name = feature.get("name", "Unknown")
    feature_id = feature.get("id")
    logger.info(f"Synthesizing overlay for feature '{feature_name}'")

    # Build persona refs
    persona_refs = []
    for p in personas:
        related = p.get("related_features", [])
        if feature_id and feature_id in related:
            persona_refs.append(
                PersonaRef(
                    persona_id=p["id"],
                    persona_name=p.get("name", "Unknown"),
                    role="primary",
                )
            )

    # Find flow position from VP steps
    flow_position = None
    for step in vp_steps:
        features_used = step.get("features_used", [])
        for fu in features_used:
            if fu.get("feature_id") == feature_id:
                flow_position = {
                    "vp_step_index": step.get("step_index", 0),
                    "vp_step_label": step.get("label", ""),
                }
                break
        if flow_position:
            break

    # Build business rules from analysis
    business_rules = [
        BusinessRule(
            rule=br.get("rule", ""),
            source=br.get("source", "inferred"),
            confidence=br.get("confidence", 0.5),
        )
        for br in analysis.business_rules
    ]

    # Build question overlay objects
    overlay_questions = [
        OverlayQuestion(
            id="",  # Will be set when saved to DB
            question=q.question,
            category=q.category,
            priority=q.priority,
            answer=None,
            answered_in_session=None,
        )
        for q in questions
    ]

    # Call LLM for status assessment and upload suggestions
    user_message = f"""## Feature: {feature_name}
Analysis confidence: {analysis.confidence}
Questions: {len(questions)} ({sum(1 for q in questions if q.priority == "high")} high priority)
Business rules: {len(analysis.business_rules)} ({sum(1 for br in analysis.business_rules if br.get("source") == "inferred")} inferred)
Implementation status: {analysis.implementation_status}
Personas using this: {len(persona_refs)}
Flow position: {json.dumps(flow_position)}

Determine status, gaps count, implementation notes, and upload suggestions.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
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

    upload_suggestions = [
        UploadSuggestion(**s)
        for s in parsed.get("upload_suggestions", [])
    ]

    overlay = OverlayContent(
        feature_id=feature_id,
        feature_name=feature_name,
        status=parsed.get("status", "unknown"),
        confidence=parsed.get("confidence", analysis.confidence),
        gaps_count=parsed.get("gaps_count", len(questions)),
        triggers=analysis.triggers,
        actions=analysis.actions,
        data_requirements=analysis.data_requirements,
        personas=persona_refs,
        flow_position=flow_position,
        dependencies=[],  # Populated by cross-feature analysis
        questions=overlay_questions,
        business_rules=business_rules,
        implementation_notes=parsed.get("implementation_notes", analysis.notes),
        upload_suggestions=upload_suggestions,
    )

    logger.info(
        f"Overlay for '{feature_name}': status={overlay.status}, "
        f"gaps={overlay.gaps_count}, confidence={overlay.confidence:.2f}"
    )
    return overlay
