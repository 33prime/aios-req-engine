"""Single-call feature overlay analysis with Anthropic prompt caching.

Replaces the old 3-chain pipeline (analyze_prototype_feature → generate_feature_questions
→ synthesize_overlay) with one cached call per feature.

Prompt caching layout:
  SYSTEM [cached]:  Instructions + output JSON schema (~800 tokens)
  USER block 1 [cached]:  Project context: all features, personas, VP steps (~4000 tokens)
  USER block 2 [NOT cached]:  This feature's spec + code (~2500 tokens)

Feature 1: cache write (full price). Features 2-14: cache read (90% off ~4800 cached tokens).
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    FeatureGap,
    FeatureImpact,
    FeatureOverview,
    OverlayContent,
    PersonaImpact,
)

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a senior requirements analyst examining a prototype feature. Your job is to \
compare what the AIOS specification says against what the prototype code actually does, \
identify who is affected, and surface exactly 3 focused questions that will improve the \
requirements specification.

## Rules

1. **spec_summary**: Write 2-3 sentences from AIOS data ONLY (overview, user_actions, \
system_behaviors, rules). Do NOT reference code here.
2. **prototype_summary**: Write 2-3 sentences from CODE ONLY. Describe what the component \
renders and handles. Do NOT reference the spec here.
3. **delta**: List concrete, falsifiable gaps. Good: "Missing payment validation on submit". \
Bad: "Some gaps exist". Each item should name what is missing or different.
4. **implementation_status**: "functional" = code matches spec, "partial" = some gaps, \
"placeholder" = stub/skeleton only.
5. **personas_affected**: For each persona from the project context that uses this feature, \
explain HOW they are affected (1 sentence).
6. **value_path_position**: If this feature appears in a VP step, state which one \
(e.g. "Step 3 of 7: User completes assessment"). null if unmapped.
7. **downstream_risk**: Name specific OTHER features from the project context that would \
break or degrade if this feature's gaps are not resolved. Be specific.
8. **gaps**: EXACTLY 3 questions. Each must be specific to THIS feature (not generic). \
Each must help the consultant improve requirements. Include why_it_matters and \
requirement_area (one of: business_rules, data_handling, user_flow, permissions, integration).
9. **status**: "understood" if confidence >= 0.7 and delta is empty/minor. \
"partial" if 0.4-0.7. "unknown" if < 0.4.
10. **confidence**: 0.0-1.0 based on how well the code matches the spec.

Output ONLY valid JSON matching this schema:
{
  "feature_id": "uuid or null",
  "feature_name": "...",
  "overview": {
    "spec_summary": "...",
    "prototype_summary": "...",
    "delta": ["..."],
    "implementation_status": "functional|partial|placeholder"
  },
  "impact": {
    "personas_affected": [{"name": "...", "how_affected": "..."}],
    "value_path_position": "Step X of Y: label" or null,
    "downstream_risk": "..."
  },
  "gaps": [
    {"question": "...", "why_it_matters": "...", "requirement_area": "business_rules|data_handling|user_flow|permissions|integration"},
    {"question": "...", "why_it_matters": "...", "requirement_area": "..."},
    {"question": "...", "why_it_matters": "...", "requirement_area": "..."}
  ],
  "status": "understood|partial|unknown",
  "confidence": 0.0-1.0
}
"""


def build_cached_blocks(
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build cacheable content blocks for system prompt and project context.

    Returns:
        (system_blocks, context_blocks) — both with cache_control markers.
    """
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # Build compact project context
    feature_summaries = []
    for f in features:
        feature_summaries.append({
            "id": f.get("id"),
            "name": f.get("name"),
            "overview": f.get("overview", ""),
            "user_actions": f.get("user_actions", []),
            "system_behaviors": f.get("system_behaviors", []),
            "rules": f.get("rules", []),
        })

    persona_summaries = []
    for p in personas:
        persona_summaries.append({
            "name": p.get("name"),
            "goals": p.get("goals", []),
            "pain_points": p.get("pain_points", []),
            "related_features": p.get("related_features", []),
        })

    vp_summaries = []
    for i, step in enumerate(vp_steps):
        vp_summaries.append({
            "step_index": step.get("step_index", i),
            "label": step.get("label", ""),
            "features_used": [
                {"feature_id": fu.get("feature_id"), "role": fu.get("role")}
                for fu in step.get("features_used", [])
            ],
        })

    context_text = f"""## PROJECT CONTEXT

### All Features ({len(feature_summaries)})
{json.dumps(feature_summaries, indent=2, default=str)}

### All Personas ({len(persona_summaries)})
{json.dumps(persona_summaries, indent=2, default=str)}

### Value Path Steps ({len(vp_summaries)})
{json.dumps(vp_summaries, indent=2, default=str)}
"""

    context_blocks = [
        {
            "type": "text",
            "text": context_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    return system_blocks, context_blocks


def analyze_feature_overlay(
    client: Anthropic,
    system_blocks: list[dict[str, Any]],
    context_blocks: list[dict[str, Any]],
    feature: dict[str, Any],
    code_content: str,
    handoff_entry: str | None,
    settings: Settings,
    model_override: str | None = None,
) -> OverlayContent:
    """Analyze a single feature with prompt caching.

    Args:
        client: Shared Anthropic client instance.
        system_blocks: Cached system prompt blocks from build_cached_blocks().
        context_blocks: Cached project context blocks from build_cached_blocks().
        feature: AIOS feature record.
        code_content: Source code of the feature's component.
        handoff_entry: Feature entry from HANDOFF.md, if present.
        settings: App settings.
        model_override: Optional model override.

    Returns:
        OverlayContent with overview, impact, and gaps.
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    feature_name = feature.get("name", "Unknown")
    feature_id = feature.get("id")

    logger.info(f"Analyzing feature '{feature_name}' using {model} with prompt caching")

    # Build per-feature content (NOT cached)
    feature_spec = {
        "id": feature_id,
        "name": feature_name,
        "category": feature.get("category"),
        "overview": feature.get("overview"),
        "user_actions": feature.get("user_actions", []),
        "system_behaviors": feature.get("system_behaviors", []),
        "ui_requirements": feature.get("ui_requirements", []),
        "rules": feature.get("rules", []),
        "integrations": feature.get("integrations", []),
    }

    per_feature_text = f"""## THIS FEATURE — Analyze this one now

### AIOS Specification
{json.dumps(feature_spec, indent=2, default=str)}

### HANDOFF.md Entry
{handoff_entry or "Not found in HANDOFF.md"}

### Prototype Code
```
{code_content[:8000]}
```
"""

    # Combine cached context + per-feature content into user message
    user_content = context_blocks + [{"type": "text", "text": per_feature_text}]

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_blocks,
        messages=[{"role": "user", "content": user_content}],
    )

    # Log cache performance
    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_create = getattr(usage, "cache_creation_input_tokens", 0)
    logger.info(
        f"Feature '{feature_name}': cache_read={cache_read}, cache_create={cache_create}, "
        f"input_tokens={usage.input_tokens}, output_tokens={usage.output_tokens}"
    )

    # Parse response
    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json"):]
    if response_text.startswith("```"):
        response_text = response_text[len("```"):]
    if response_text.endswith("```"):
        response_text = response_text[:-len("```")]
    parsed = json.loads(response_text.strip())

    # Build OverlayContent from parsed response
    overview_data = parsed.get("overview", {})
    overview = FeatureOverview(
        spec_summary=overview_data.get("spec_summary", ""),
        prototype_summary=overview_data.get("prototype_summary", ""),
        delta=overview_data.get("delta", []),
        implementation_status=overview_data.get("implementation_status", "placeholder"),
    )

    impact_data = parsed.get("impact", {})
    personas_affected = [
        PersonaImpact(name=p.get("name", ""), how_affected=p.get("how_affected", ""))
        for p in impact_data.get("personas_affected", [])
    ]
    impact = FeatureImpact(
        personas_affected=personas_affected,
        value_path_position=impact_data.get("value_path_position"),
        downstream_risk=impact_data.get("downstream_risk", ""),
    )

    gaps = [
        FeatureGap(
            question=g.get("question", ""),
            why_it_matters=g.get("why_it_matters", ""),
            requirement_area=g.get("requirement_area", "business_rules"),
        )
        for g in parsed.get("gaps", [])[:3]  # Enforce max 3
    ]

    overlay = OverlayContent(
        feature_id=feature_id,
        feature_name=feature_name,
        overview=overview,
        impact=impact,
        gaps=gaps,
        status=parsed.get("status", "unknown"),
        confidence=parsed.get("confidence", 0.0),
    )

    logger.info(
        f"Overlay for '{feature_name}': status={overlay.status}, "
        f"gaps={len(overlay.gaps)}, confidence={overlay.confidence:.2f}"
    )
    return overlay
