"""Strategic context generation chain.

This chain generates the strategic context for a project from signals and research:
- Project type detection (internal vs market product)
- Executive summary
- Opportunity analysis
- Risk identification
- Investment case
- Success metrics
- Constraints
- Stakeholder identification
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_strategic_context import GeneratedStrategicContext
from app.db.signals import list_project_signals
from app.db.stakeholders import upsert_stakeholder
from app.db.strategic_context import get_strategic_context, upsert_strategic_context
from app.db.personas import list_personas
from app.db.features import list_features
from app.db.vp import list_vp_steps
from app.db.business_drivers import create_business_driver, find_similar_driver
from app.db.constraints import create_constraint, list_constraints

logger = get_logger(__name__)


# System prompt for strategic context generation
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements consultant analyzing a software project to extract strategic business context.

You will receive:
1. Signals from conversations, documents, and meetings
2. Any existing context about the project

Your job is to synthesize the "big picture" - the business case and strategic context that explains WHY this software is being built.

You MUST output ONLY valid JSON matching this exact schema:

{
  "project_type": "internal" | "market_product",
  "executive_summary": "2-3 sentence overview of the project and its strategic value",
  "opportunity": {
    "problem_statement": "What problem are we solving?",
    "business_opportunity": "What's the upside if we solve it?",
    "client_motivation": "Why does the client want this now?",
    "strategic_fit": "How does this align with their broader strategy?",
    "market_gap": "What gap exists in the market? (for market_product only, null for internal)"
  },
  "risks": [
    {
      "category": "business" | "technical" | "compliance" | "competitive",
      "description": "Clear description of the risk",
      "severity": "high" | "medium" | "low",
      "mitigation": "Suggested mitigation strategy or null if unknown",
      "evidence_ids": []
    }
  ],
  "investment_case": {
    // For internal projects:
    "efficiency_gains": "Expected efficiency improvements",
    "cost_reduction": "Expected cost savings",
    "risk_mitigation": "Risks avoided by building this",
    "roi_estimate": "ROI estimate if mentioned (or null)",
    "roi_timeframe": "Timeframe for ROI if mentioned (or null)"
    // For market products:
    // "tam": "Total Addressable Market if mentioned",
    // "sam": "Serviceable Addressable Market if mentioned",
    // "som": "Serviceable Obtainable Market if mentioned",
    // "revenue_projection": "Revenue projection if mentioned",
    // "market_timing": "Why is now the right time?",
    // "competitive_advantage": "How this beats alternatives"
  },
  "success_metrics": [
    {
      "metric": "What to measure",
      "target": "Target value",
      "current": "Current value if known (or null)",
      "evidence_ids": []
    }
  ],
  "constraints": {
    "budget": "Budget constraints if mentioned (or null)",
    "timeline": "Timeline constraints if mentioned (or null)",
    "team_size": "Team size constraints if mentioned (or null)",
    "technical": ["Technical constraints"],
    "compliance": ["Compliance requirements"]
  },
  "stakeholders": [
    {
      "name": "Person or role name",
      "role": "Job title if known",
      "organization": "Company/department if known",
      "stakeholder_type": "champion" | "sponsor" | "blocker" | "influencer" | "end_user",
      "influence_level": "high" | "medium" | "low",
      "priorities": ["What they care about"],
      "concerns": ["Their worries or objections"]
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation.
2. Only include information you have EVIDENCE for in the signals.
3. Do NOT invent numbers, metrics, or data - use null if unknown.
4. project_type: "internal" for internal tools/software, "market_product" for products sold to market.
5. Stakeholder types:
   - champion: Internal advocate pushing for the project
   - sponsor: Decision maker with budget authority
   - blocker: Person or group with concerns/opposition
   - influencer: Opinion leader who affects decisions
   - end_user: Actual user of the software
6. Keep investment_case fields relevant to project_type (internal or market).
7. Base everything on the provided signals - don't make assumptions."""


def _build_strategic_context_prompt(
    project_id: UUID,
    signals: list[dict[str, Any]],
    state_snapshot: dict[str, Any] | None = None,
    existing_context: dict | None = None,
) -> str:
    """
    Build the prompt for strategic context generation.

    Args:
        project_id: Project UUID
        signals: List of signal dicts
        state_snapshot: Current project state (PRD, personas, features, VP, research)
        existing_context: Any existing strategic context

    Returns:
        Complete prompt for the LLM
    """
    prompt_parts = [
        "# Strategic Context Analysis Task",
        "",
        f"Project ID: {project_id}",
        "",
        "Analyze the following project data to extract strategic business context.",
        "",
    ]

    # Add current state snapshot first (most important)
    if state_snapshot:
        # PRD sections
        prd = state_snapshot.get("prd", {})
        if prd:
            prompt_parts.append("## Current PRD (Product Requirements)")
            for section in prd.get("sections", []):
                slug = section.get("slug", "")
                title = section.get("title", slug)
                content = section.get("content", "")
                if content and slug not in ["personas", "key_features", "happy_path"]:
                    prompt_parts.append(f"### {title}")
                    prompt_parts.append(content[:1500])
                    prompt_parts.append("")

        # Personas
        personas = state_snapshot.get("personas", [])
        if personas:
            prompt_parts.append("## Personas (User Types)")
            for p in personas[:5]:  # Limit to 5
                name = p.get("name", "Unknown")
                role = p.get("role", "")
                goals = p.get("goals", [])
                pain_points = p.get("pain_points", [])
                prompt_parts.append(f"**{name}** ({role})")
                if goals:
                    prompt_parts.append(f"  Goals: {', '.join(goals[:3])}")
                if pain_points:
                    prompt_parts.append(f"  Pain Points: {', '.join(pain_points[:3])}")
            prompt_parts.append("")

        # Features
        features = state_snapshot.get("features", [])
        if features:
            prompt_parts.append("## Key Features")
            for f in features[:10]:  # Limit to 10
                name = f.get("name", "Unknown")
                desc = f.get("description", "")[:200]
                priority = f.get("priority", "medium")
                prompt_parts.append(f"- **{name}** [{priority}]: {desc}")
            prompt_parts.append("")

        # Value Path
        vp_steps = state_snapshot.get("vp_steps", [])
        if vp_steps:
            prompt_parts.append("## Value Path (User Journey)")
            for step in vp_steps[:8]:  # Limit to 8
                title = step.get("title", "")
                desc = step.get("description", "")[:150]
                prompt_parts.append(f"- {title}: {desc}")
            prompt_parts.append("")

        # Research findings
        research = state_snapshot.get("research", [])
        if research:
            prompt_parts.append("## Research Findings")
            for r in research[:5]:  # Limit to 5
                query = r.get("query", "")
                answer = r.get("answer", "")[:500]
                prompt_parts.append(f"**Q: {query}**")
                prompt_parts.append(f"A: {answer}")
                prompt_parts.append("")

    # Add signals (raw source material)
    if signals:
        prompt_parts.append("## Original Signals (Source Documents)")
        prompt_parts.append("")
        for i, signal in enumerate(signals[:5], 1):  # Limit to 5 signals
            signal_type = signal.get("signal_type", "unknown")
            source = signal.get("source_type", "")
            content = signal.get("content", "")[:1500]  # Truncate

            prompt_parts.append(f"### Signal {i} ({signal_type} from {source})")
            prompt_parts.append(content)
            prompt_parts.append("")

    # Add existing context if regenerating
    if existing_context:
        prompt_parts.append("## Existing Strategic Context (for reference)")
        if existing_context.get("executive_summary"):
            prompt_parts.append(f"Summary: {existing_context['executive_summary']}")
        if existing_context.get("project_type"):
            prompt_parts.append(f"Project Type: {existing_context['project_type']}")
        prompt_parts.append("")

    # Instructions
    prompt_parts.extend([
        "## Instructions",
        "1. Determine if this is an internal software project or a market product",
        "2. Write a concise executive summary (2-3 sentences) based on the PRD and features",
        "3. Extract the opportunity details - what problem is being solved?",
        "4. Identify risks mentioned or implied in the requirements",
        "5. Build the investment case with only verifiable data from the project",
        "6. List any success metrics or KPIs mentioned",
        "7. Note any constraints (budget, timeline, technical, compliance)",
        "8. Identify stakeholders mentioned and their roles",
        "",
        "IMPORTANT: Base your analysis on the actual project data above. Be specific, not generic.",
        "",
        "Output ONLY valid JSON matching the required schema.",
    ])

    return "\n".join(prompt_parts)


def _get_state_snapshot(project_id: UUID) -> dict[str, Any]:
    """
    Get the current state snapshot for a project.

    Fetches PRD, personas, features, and value path steps.

    Args:
        project_id: Project UUID

    Returns:
        Dict with personas, features, vp_steps
    """
    snapshot = {}

    try:
        # Get personas
        personas = list_personas(project_id)
        if personas:
            snapshot["personas"] = personas
    except Exception as e:
        logger.warning(f"Failed to get personas: {e}")

    try:
        # Get features
        features = list_features(project_id)
        if features:
            snapshot["features"] = features
    except Exception as e:
        logger.warning(f"Failed to get features: {e}")

    try:
        # Get value path steps
        vp_steps = list_vp_steps(project_id)
        if vp_steps:
            snapshot["vp_steps"] = vp_steps
    except Exception as e:
        logger.warning(f"Failed to get VP steps: {e}")

    # TODO: Add research findings when available

    return snapshot


def generate_strategic_context(
    project_id: UUID,
    model_override: str | None = None,
    regenerate: bool = False,
) -> GeneratedStrategicContext:
    """
    Generate strategic context for a project.

    Args:
        project_id: Project UUID
        model_override: Optional model name to use
        regenerate: Whether to regenerate existing context

    Returns:
        GeneratedStrategicContext with all fields

    Raises:
        ValueError: If generation fails
    """
    settings = get_settings()
    model = model_override or settings.STRATEGIC_CONTEXT_MODEL or "gpt-4o-mini"

    logger.info(
        f"Generating strategic context for project {project_id}",
        extra={"project_id": str(project_id), "model": model, "regenerate": regenerate},
    )

    # Get signals - list_project_signals returns {'signals': [...], 'total': N}
    signal_result = list_project_signals(project_id)
    signals = signal_result.get("signals", [])
    logger.info(f"Found {len(signals)} signals for context generation")

    # Get current state snapshot (PRD, personas, features, VP)
    state_snapshot = _get_state_snapshot(project_id)
    logger.info(
        f"State snapshot: PRD={bool(state_snapshot.get('prd'))}, "
        f"personas={len(state_snapshot.get('personas', []))}, "
        f"features={len(state_snapshot.get('features', []))}, "
        f"vp_steps={len(state_snapshot.get('vp_steps', []))}"
    )

    # Get existing context if regenerating
    existing_context = None
    if regenerate:
        existing_context = get_strategic_context(project_id)

    # Build prompt
    prompt = _build_strategic_context_prompt(project_id, signals, state_snapshot, existing_context)

    # Call LLM
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from LLM")

    logger.debug(f"Raw LLM response: {content[:500]}...")

    # Parse response
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise ValueError(f"Invalid JSON in LLM response: {e}") from e

    # Validate with Pydantic
    try:
        result = GeneratedStrategicContext(**data)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise ValueError(f"Invalid strategic context format: {e}") from e

    logger.info(
        f"Generated strategic context: type={result.project_type}, "
        f"risks={len(result.risks)}, metrics={len(result.success_metrics)}, "
        f"stakeholders={len(result.stakeholders)}",
        extra={"project_id": str(project_id)},
    )

    return result


def generate_and_save_strategic_context(
    project_id: UUID,
    model_override: str | None = None,
    regenerate: bool = False,
) -> dict:
    """
    Generate strategic context and save to database.

    Args:
        project_id: Project UUID
        model_override: Optional model name to use
        regenerate: Whether to regenerate existing context

    Returns:
        Saved strategic context dict

    Raises:
        ValueError: If generation or save fails
    """
    settings = get_settings()
    model = model_override or settings.STRATEGIC_CONTEXT_MODEL or "gpt-4o-mini"

    # Generate context
    result = generate_strategic_context(
        project_id=project_id,
        model_override=model_override,
        regenerate=regenerate,
    )

    # Save strategic context
    context = upsert_strategic_context(
        project_id=project_id,
        project_type=result.project_type,
        executive_summary=result.executive_summary,
        opportunity=result.opportunity,
        risks=result.risks,
        investment_case=result.investment_case,
        success_metrics=result.success_metrics,
        constraints=result.constraints,
        evidence=[],  # Will be linked later via UI
        confirmation_status="ai_generated",
        generation_model=model,
    )

    # Save stakeholders
    stakeholders_saved = 0
    for sh in result.stakeholders:
        try:
            upsert_stakeholder(
                project_id=project_id,
                name=sh.get("name", "Unknown"),
                stakeholder_type=sh.get("stakeholder_type", "influencer"),
                role=sh.get("role"),
                organization=sh.get("organization"),
                influence_level=sh.get("influence_level", "medium"),
                priorities=sh.get("priorities", []),
                concerns=sh.get("concerns", []),
                confirmation_status="ai_generated",
            )
            stakeholders_saved += 1
        except Exception as e:
            logger.warning(f"Failed to save stakeholder {sh.get('name')}: {e}")

    logger.info(
        f"Saved strategic context and {stakeholders_saved} stakeholders for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # =========================================================================
    # Extract entities to dedicated tables (Option A implementation)
    # =========================================================================

    # 1. Extract success_metrics → business_drivers (KPIs)
    kpis_created = 0
    for metric in result.success_metrics:
        metric_name = metric.get("metric", "")
        if not metric_name:
            continue

        # Check for existing similar KPI to avoid duplicates
        existing = find_similar_driver(project_id, metric_name, driver_type="kpi", threshold=0.7)
        if existing:
            logger.debug(f"Skipping duplicate KPI: {metric_name}")
            continue

        try:
            create_business_driver(
                project_id=project_id,
                driver_type="kpi",
                description=metric_name,
                measurement=metric.get("target"),
                timeframe=None,  # Could extract from context if available
                priority=2,  # Default to high priority for success metrics
            )
            kpis_created += 1
        except Exception as e:
            logger.warning(f"Failed to create KPI business driver: {e}")

    logger.info(f"Created {kpis_created} KPI business drivers from success_metrics")

    # 2. Extract constraints → constraints table
    constraints_created = 0
    constraint_data = result.constraints or {}

    # Technical constraints
    for tech_constraint in constraint_data.get("technical", []) or []:
        if not tech_constraint:
            continue
        try:
            create_constraint(
                project_id=project_id,
                title=tech_constraint[:100],  # Truncate for title
                constraint_type="technical",
                description=tech_constraint,
                severity="must_have",
                confirmation_status="ai_generated",
            )
            constraints_created += 1
        except Exception as e:
            logger.warning(f"Failed to create technical constraint: {e}")

    # Compliance constraints
    for compliance_constraint in constraint_data.get("compliance", []) or []:
        if not compliance_constraint:
            continue
        try:
            create_constraint(
                project_id=project_id,
                title=compliance_constraint[:100],
                constraint_type="compliance",
                description=compliance_constraint,
                severity="must_have",
                confirmation_status="ai_generated",
            )
            constraints_created += 1
        except Exception as e:
            logger.warning(f"Failed to create compliance constraint: {e}")

    # Budget constraint
    if constraint_data.get("budget"):
        try:
            create_constraint(
                project_id=project_id,
                title="Budget Constraint",
                constraint_type="business",
                description=constraint_data["budget"],
                severity="must_have",
                confirmation_status="ai_generated",
            )
            constraints_created += 1
        except Exception as e:
            logger.warning(f"Failed to create budget constraint: {e}")

    # Timeline constraint
    if constraint_data.get("timeline"):
        try:
            create_constraint(
                project_id=project_id,
                title="Timeline Constraint",
                constraint_type="timeline",
                description=constraint_data["timeline"],
                severity="must_have",
                confirmation_status="ai_generated",
            )
            constraints_created += 1
        except Exception as e:
            logger.warning(f"Failed to create timeline constraint: {e}")

    logger.info(f"Created {constraints_created} constraints from strategic context")

    # 3. Extract risks → constraints table (as risk type)
    risks_created = 0
    for risk in result.risks:
        risk_desc = risk.get("description", "")
        if not risk_desc:
            continue
        try:
            severity_map = {"high": "must_have", "medium": "should_have", "low": "nice_to_have"}
            create_constraint(
                project_id=project_id,
                title=f"{risk.get('category', 'business').title()} Risk: {risk_desc[:50]}",
                constraint_type="risk",
                description=f"{risk_desc}\n\nMitigation: {risk.get('mitigation', 'TBD')}",
                severity=severity_map.get(risk.get("severity", "medium"), "should_have"),
                confirmation_status="ai_generated",
            )
            risks_created += 1
        except Exception as e:
            logger.warning(f"Failed to create risk constraint: {e}")

    logger.info(f"Created {risks_created} risk entries from strategic context")

    return context


def identify_stakeholders(
    project_id: UUID,
    model_override: str | None = None,
) -> list[dict]:
    """
    Identify stakeholders from signals for a project.

    This is a lighter-weight operation that just identifies stakeholders
    without regenerating the full strategic context.

    Args:
        project_id: Project UUID
        model_override: Optional model name to use

    Returns:
        List of identified stakeholders

    Raises:
        ValueError: If identification fails
    """
    settings = get_settings()
    model = model_override or settings.STRATEGIC_CONTEXT_MODEL or "gpt-4o-mini"

    logger.info(
        f"Identifying stakeholders for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get signals - list_project_signals returns {'signals': [...], 'total': N}
    signal_result = list_project_signals(project_id)
    signals = signal_result.get("signals", [])

    stakeholder_prompt = """Analyze the following signals and identify all stakeholders mentioned.

For each stakeholder, determine:
- name: Their name or role title
- role: Their job title if known
- organization: Their company/department if known
- stakeholder_type: champion|sponsor|blocker|influencer|end_user
- influence_level: high|medium|low
- priorities: What they care about (list)
- concerns: Their worries/objections (list)

Output ONLY valid JSON:
{
  "stakeholders": [
    {
      "name": "string",
      "role": "string or null",
      "organization": "string or null",
      "stakeholder_type": "champion|sponsor|blocker|influencer|end_user",
      "influence_level": "high|medium|low",
      "priorities": ["list of strings"],
      "concerns": ["list of strings"]
    }
  ]
}
"""

    # Build signal context
    signal_text = "\n\n".join([
        f"Signal {i+1} ({s.get('signal_type', 'unknown')}): {s.get('content', '')[:1000]}"
        for i, s in enumerate(signals[:20])  # Limit to 20 signals
    ])

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": stakeholder_prompt},
            {"role": "user", "content": f"Signals:\n\n{signal_text}"},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        return []

    try:
        data = json.loads(content)
        stakeholders = data.get("stakeholders", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse stakeholders JSON")
        return []

    # Save stakeholders
    saved = []
    for sh in stakeholders:
        try:
            result = upsert_stakeholder(
                project_id=project_id,
                name=sh.get("name", "Unknown"),
                stakeholder_type=sh.get("stakeholder_type", "influencer"),
                role=sh.get("role"),
                organization=sh.get("organization"),
                influence_level=sh.get("influence_level", "medium"),
                priorities=sh.get("priorities", []),
                concerns=sh.get("concerns", []),
                confirmation_status="ai_generated",
            )
            saved.append(result)
        except Exception as e:
            logger.warning(f"Failed to save stakeholder: {e}")

    logger.info(f"Identified and saved {len(saved)} stakeholders")
    return saved
