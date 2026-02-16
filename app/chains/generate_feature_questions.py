"""DEPRECATED: Replaced by analyze_feature_overlay.py which generates
exactly 3 gap questions per feature as part of the single-call pipeline.

Generate questions about unknowns for a feature.

Takes analysis results and AIOS context to produce targeted questions
that consultants should ask during review sessions.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import FeatureAnalysis, GeneratedQuestion

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a requirements analyst generating questions about a feature's unknowns. \
Based on the analysis of the prototype code and AIOS feature data, identify \
questions that need answers before the feature can be fully specified.

Rules:
1. Only ask about things NOT already answered in the AIOS data
2. Focus on gaps between what the code does and what the spec says
3. Prioritize questions that block implementation (high), affect UX (medium), or are nice-to-know (low)
4. Categorize each question: business_rules, edge_cases, permissions, integration, data_handling
5. Explain why each question matters

Output ONLY a JSON array:
[
  {
    "question": "...",
    "category": "business_rules|edge_cases|permissions|integration|data_handling",
    "priority": "high|medium|low",
    "why_important": "..."
  }
]
"""


def generate_feature_questions(
    analysis: FeatureAnalysis,
    feature: dict[str, Any],
    personas: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> list[GeneratedQuestion]:
    """Generate questions about unknowns for a feature.

    Args:
        analysis: FeatureAnalysis from the analyzer chain
        feature: AIOS feature record
        personas: All project personas (for context)
        settings: App settings
        model_override: Optional model override

    Returns:
        List of generated questions
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    feature_name = feature.get("name", "Unknown")
    logger.info(f"Generating questions for feature '{feature_name}'")

    user_message = f"""## Feature: {feature_name}

## Analysis Results
{json.dumps(analysis.model_dump(), indent=2)}

## AIOS Feature Data (what we already know)
- Overview: {feature.get("overview", "Not enriched")}
- User Actions: {json.dumps(feature.get("user_actions", []))}
- System Behaviors: {json.dumps(feature.get("system_behaviors", []))}
- Rules: {json.dumps(feature.get("rules", []))}
- UI Requirements: {json.dumps(feature.get("ui_requirements", []))}

## Personas Who Use This Feature
{json.dumps([{"name": p.get("name"), "goals": p.get("goals", []), "pain_points": p.get("pain_points", [])} for p in personas], indent=2, default=str)}

Generate questions about what's still unknown.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
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
    questions = [GeneratedQuestion(**q) for q in parsed]

    logger.info(f"Generated {len(questions)} questions for '{feature_name}'")
    return questions
