"""DEPRECATED: Replaced by analyze_feature_overlay.py which uses prompt caching
and produces the new OverlayContent schema (overview/impact/gaps).

Analyze a single feature's prototype code against AIOS metadata.

Extracts triggers, actions, data requirements, business rules, and
integration points from the code and compares with known feature data.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import FeatureAnalysis

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a senior technical analyst examining prototype code for a specific feature. \
Compare the code implementation against the AIOS feature specification to determine:

1. TRIGGERS: What user actions or events trigger this feature?
2. ACTIONS: What does the feature do in response?
3. DATA REQUIREMENTS: What data does this feature need? (fields, types, validations)
4. BUSINESS RULES: What rules govern behavior? Mark each as:
   - "aios" (from the spec), "inferred" (you deduced from code), or "confirmed" (explicitly in both)
   - Include confidence 0-1 for inferred rules
5. INTEGRATION POINTS: What other features/modules does this connect to?
6. IMPLEMENTATION STATUS: "functional" (works as spec'd), "partial" (some missing), "placeholder" (stub only)
7. CONFIDENCE: Overall confidence 0-1 in your analysis
8. NOTES: Any implementation observations

Output ONLY valid JSON matching this schema:
{
  "triggers": ["..."],
  "actions": ["..."],
  "data_requirements": ["..."],
  "business_rules": [{"rule": "...", "source": "aios|inferred|confirmed", "confidence": 0.0-1.0}],
  "integration_points": ["..."],
  "implementation_status": "functional|partial|placeholder",
  "confidence": 0.0-1.0,
  "notes": "..."
}
"""


def analyze_prototype_feature(
    code_content: str,
    feature: dict[str, Any],
    handoff_entry: str | None,
    settings: Settings,
    model_override: str | None = None,
) -> FeatureAnalysis:
    """Analyze a feature's code against AIOS metadata.

    Args:
        code_content: Source code of the feature's component
        feature: AIOS feature record with enrichment data
        handoff_entry: Feature entry from HANDOFF.md, if present
        settings: App settings
        model_override: Optional model override

    Returns:
        FeatureAnalysis with detailed breakdown
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    feature_name = feature.get("name", "Unknown")
    logger.info(f"Analyzing feature '{feature_name}' using {model}")

    feature_spec = {
        "id": feature.get("id"),
        "name": feature_name,
        "category": feature.get("category"),
        "overview": feature.get("overview"),
        "user_actions": feature.get("user_actions", []),
        "system_behaviors": feature.get("system_behaviors", []),
        "ui_requirements": feature.get("ui_requirements", []),
        "rules": feature.get("rules", []),
        "integrations": feature.get("integrations", []),
    }

    user_message = f"""## AIOS Feature Specification
{json.dumps(feature_spec, indent=2, default=str)}

## HANDOFF.md Entry
{handoff_entry or "Not found in HANDOFF.md"}

## Prototype Code
```
{code_content[:8000]}
```
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
    analysis = FeatureAnalysis(**parsed)

    logger.info(
        f"Feature '{feature_name}': status={analysis.implementation_status}, "
        f"confidence={analysis.confidence:.2f}"
    )
    return analysis
