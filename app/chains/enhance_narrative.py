"""AI-assisted rewriting for project vision and background narratives.

CONTEXT STRATEGY: Full BRD context (drivers, features, signals) — no single entity graph.

Vision = the future state based on problems, goals, and pain.
Background = problem provenance — the past that led to the present.

Together, reading both should define a clear problem/solution statement.

See docs/context/retrieval-rules.md for when to use graph/retrieval/manual patterns.
"""

import logging

from anthropic import Anthropic

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 500

_SYSTEM_VISION = """\
You are a requirements engineering consultant writing a concise vision statement.
The vision describes the FUTURE STATE — what success looks like once the solution is built.

Format rules:
- 1-2 sentence opening paragraph (the core transformation)
- 3-4 bullet points, each ONE sentence max, bold the key term:
  "- **Automated intake** — clients self-qualify through a guided flow"
- No blank lines between bullets — keep them as a tight list
- Optional: one closing *italic* sentence on broader impact
- Total length: under 150 words

Be specific. Reference actual features, personas, goals from the evidence.
Return ONLY the markdown — no preamble."""

_SYSTEM_BACKGROUND = """\
You are a requirements engineering consultant writing a concise project background.
The background is PROBLEM PROVENANCE — what pain exists and why now.

Format rules:
- 1-2 sentence opening paragraph (the core problem)
- 3-4 bullet points, each ONE sentence max, bold the key pain:
  "- **Manual modeling** — consultants rebuild spreadsheets from scratch each time"
- No blank lines between bullets — keep them as a tight list
- Optional: one closing *italic* sentence on why now is the moment
- Total length: under 150 words

Be specific. Reference actual stakeholders, pain points from the evidence.
Return ONLY the markdown — no preamble."""

_SYSTEM_MACRO_OUTCOME = """\
You are a requirements engineering consultant writing a concise market/process problem statement.
This describes the CORE PROBLEM — the pain, gap, or opportunity that justifies the project.

Format rules:
- 1-2 sentence opening paragraph (the core problem)
- 2-3 bullet points, each ONE sentence max, bold the key issue:
  "- **Manual onboarding** — new customers wait 2-3 weeks for account setup"
- No blank lines between bullets — keep them as a tight list
- Total length: under 120 words

Be specific. Reference actual pain points, stakeholders, and business impact from the evidence.
Return ONLY the markdown — no preamble."""

_SYSTEM_OUTCOME_THESIS = """\
You are a requirements engineering consultant writing a concise solution thesis.
This describes the PROPOSED SOLUTION — how the product or initiative will address the problem.

Format rules:
- 1-2 sentence opening paragraph (the solution approach)
- 2-3 bullet points, each ONE sentence max, bold the key capability:
  "- **Self-service portal** — customers configure their own accounts in under 30 minutes"
- No blank lines between bullets — keep them as a tight list
- Optional: one closing *italic* sentence on expected impact
- Total length: under 120 words

Be specific. Reference actual features, capabilities, and goals from the evidence.
Return ONLY the markdown — no preamble."""


def enhance_narrative(
    project_id: str,
    field: str,
    mode: str,
    user_notes: str | None = None,
) -> str:
    """Generate an AI-enhanced version of the vision or background narrative.

    Args:
        project_id: Project UUID
        field: 'vision' or 'background'
        mode: 'rewrite' or 'notes'
        user_notes: Consultant's direction (only for 'notes' mode)

    Returns:
        The AI-generated suggestion text.
    """
    if field not in ("vision", "background", "macro_outcome", "outcome_thesis"):
        raise ValueError(f"field must be 'vision', 'background', 'macro_outcome', or 'outcome_thesis', got '{field}'")

    client = get_supabase()

    # Load project + company info
    project = (
        client.table("projects")
        .select("name, vision, vision_updated_at, macro_outcome, outcome_thesis")
        .eq("id", project_id)
        .single()
        .execute()
    )
    if not project.data:
        raise ValueError(f"Project {project_id} not found")

    project_name = project.data.get("name", "the project")
    current_vision = project.data.get("vision") or ""
    current_macro_outcome = project.data.get("macro_outcome") or ""
    current_outcome_thesis = project.data.get("outcome_thesis") or ""

    # Load background from company_info
    company_info = (
        client.table("company_info")
        .select("description, name, industry")
        .eq("project_id", project_id)
        .maybe_single()
        .execute()
    )

    current_background = ""
    company_name = ""
    industry = ""
    if company_info and company_info.data:
        current_background = company_info.data.get("description") or ""
        company_name = company_info.data.get("name") or ""
        industry = company_info.data.get("industry") or ""

    field_value_map = {
        "vision": current_vision,
        "background": current_background,
        "macro_outcome": current_macro_outcome,
        "outcome_thesis": current_outcome_thesis,
    }
    current_value = field_value_map.get(field, "")

    # ── Build rich context from BRD data ──
    context_parts = [f"Project: {project_name}"]
    if company_name:
        context_parts.append(f"Company: {company_name}")
    if industry:
        context_parts.append(f"Industry: {industry}")

    # Include related fields as context
    if field == "vision" and current_background:
        context_parts.append(f"\nProject Background (problem provenance):\n{current_background}")
    elif field == "background" and current_vision:
        context_parts.append(f"\nProject Vision (future state):\n{current_vision}")
    elif field == "macro_outcome" and current_outcome_thesis:
        context_parts.append(f"\nProposed Solution:\n{current_outcome_thesis}")
    elif field == "outcome_thesis" and current_macro_outcome:
        context_parts.append(f"\nMarket Problem:\n{current_macro_outcome}")
    # Also include vision/background as extra context for problem/solution fields
    if field in ("macro_outcome", "outcome_thesis"):
        if current_vision:
            context_parts.append(f"\nProject Vision:\n{current_vision}")
        if current_background:
            context_parts.append(f"\nProject Background:\n{current_background}")

    # Load pain points
    pains = (
        client.table("business_drivers")
        .select("title, description, severity, business_impact, affected_users")
        .eq("project_id", project_id)
        .eq("driver_type", "pain")
        .limit(8)
        .execute()
    )
    if pains.data:
        context_parts.append("\nPain Points:")
        for p in pains.data:
            title = p.get("title") or p.get("description", "")[:80]
            severity = p.get("severity", "")
            impact = p.get("business_impact", "")
            line = f"  - {title}"
            if severity:
                line += f" (severity: {severity})"
            if impact:
                line += f" — {impact[:120]}"
            context_parts.append(line)

    # Load goals
    goals = (
        client.table("business_drivers")
        .select("title, description, success_criteria, goal_timeframe")
        .eq("project_id", project_id)
        .eq("driver_type", "goal")
        .limit(8)
        .execute()
    )
    if goals.data:
        context_parts.append("\nBusiness Goals:")
        for g in goals.data:
            title = g.get("title") or g.get("description", "")[:80]
            timeframe = g.get("goal_timeframe", "")
            criteria = g.get("success_criteria", "")
            line = f"  - {title}"
            if timeframe:
                line += f" (timeframe: {timeframe})"
            if criteria:
                line += f" — success: {criteria[:120]}"
            context_parts.append(line)

    # Load KPIs
    kpis = (
        client.table("business_drivers")
        .select("title, description, baseline_value, target_value, measurement_method")
        .eq("project_id", project_id)
        .eq("driver_type", "kpi")
        .limit(6)
        .execute()
    )
    if kpis.data:
        context_parts.append("\nKey Metrics / KPIs:")
        for k in kpis.data:
            title = k.get("title") or k.get("description", "")[:80]
            baseline = k.get("baseline_value", "")
            target = k.get("target_value", "")
            line = f"  - {title}"
            if baseline and target:
                line += f" (from {baseline} → {target})"
            context_parts.append(line)

    # Load top features for solution context
    features = (
        client.table("features")
        .select("name, priority_group")
        .eq("project_id", project_id)
        .limit(10)
        .execute()
    )
    if features.data:
        must_have = [f["name"] for f in features.data if f.get("priority_group") == "must_have"]
        if must_have:
            context_parts.append(f"\nKey Solution Features: {', '.join(must_have[:6])}")

    # Load signal evidence (recent excerpts from driver evidence arrays)
    signal_excerpts = _gather_signal_excerpts(client, project_id)
    if signal_excerpts:
        context_parts.append("\nSignal Evidence (from source documents):")
        for i, excerpt in enumerate(signal_excerpts[:6], 1):
            context_parts.append(f'  [{i}] "{excerpt[:300]}"')

    context_block = "\n".join(context_parts)

    # Build user prompt
    system_map = {
        "vision": _SYSTEM_VISION,
        "background": _SYSTEM_BACKGROUND,
        "macro_outcome": _SYSTEM_MACRO_OUTCOME,
        "outcome_thesis": _SYSTEM_OUTCOME_THESIS,
    }
    system = system_map[field]

    if mode == "notes" and user_notes:
        user_prompt = (
            f"Rewrite the {field} for this project, "
            f"incorporating the consultant's direction: {user_notes}\n"
            f"Also weave in evidence where relevant.\n\n"
            f"Current {field}: {current_value or '(not yet written)'}\n\n"
            f"Context:\n{context_block}"
        )
    else:
        user_prompt = (
            f"Rewrite the {field} for this project, "
            f"incorporating all available evidence. Be specific and cite concrete data.\n\n"
            f"Current {field}: {current_value or '(not yet written)'}\n\n"
            f"Context:\n{context_block}"
        )

    # Call Haiku
    anthropic = Anthropic()
    response = anthropic.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    suggestion = response.content[0].text.strip()
    logger.info(
        "Enhanced narrative %s for project %s (mode=%s, tokens=%d/%d)",
        field,
        project_id[:8],
        mode,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    return suggestion


def _gather_signal_excerpts(client, project_id: str) -> list[str]:
    """Gather evidence excerpts from business drivers for context."""
    try:
        drivers = (
            client.table("business_drivers")
            .select("evidence")
            .eq("project_id", project_id)
            .limit(15)
            .execute()
        )

        excerpts = []
        for d in drivers.data or []:
            evidence = d.get("evidence") or []
            if isinstance(evidence, list):
                for ev in evidence:
                    excerpt = ev.get("excerpt", "")
                    if excerpt and len(excerpt) > 20:
                        excerpts.append(excerpt)

        # Deduplicate and return top excerpts
        seen = set()
        unique = []
        for ex in excerpts:
            key = ex[:60].lower()
            if key not in seen:
                seen.add(key)
                unique.append(ex)
        return unique[:8]
    except Exception:
        return []
