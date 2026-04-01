"""
Workflow Gap Analysis Chain

Uses load_project_data() to get the full BRD picture, computes lightweight
coverage stats, then asks Sonnet: "What workflows are missing?"

Returns coverage summary + up to 10 suggested workflows with steps.
"""

import json
import re
import time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Output schemas
# ============================================================================


class SuggestedStep(BaseModel):
    """A proposed step for a suggested workflow."""

    label: str
    actor_persona_name: str | None = None
    automation_level: Literal[
        "manual", "semi_automated", "fully_automated"
    ] = "manual"
    operation_type: str | None = None
    benefit_description: str | None = None
    time_minutes: float | None = None


class SuggestedWorkflow(BaseModel):
    """A proposed workflow to fill a gap."""

    name: str
    description: str
    state_type: Literal["current", "future"] = "future"
    owner_persona: str | None = None
    rationale: str = ""
    steps: list[SuggestedStep] = Field(default_factory=list)
    addresses_features: list[str] = []
    addresses_pains: list[str] = []
    addresses_goals: list[str] = []


class CoverageSummary(BaseModel):
    """High-level BRD entity counts."""

    workflows: int = 0
    workflow_pairs: int = 0
    current_steps: int = 0
    future_steps: int = 0
    features: int = 0
    personas: int = 0
    pains: int = 0
    goals: int = 0
    kpis: int = 0
    constraints: int = 0
    data_entities: int = 0


class WorkflowGapAnalysis(BaseModel):
    """Complete gap analysis result."""

    project_id: str
    coverage: CoverageSummary = Field(
        default_factory=CoverageSummary
    )
    suggested_workflows: list[SuggestedWorkflow] = []
    observations: list[str] = []


# ============================================================================
# Context building
# ============================================================================


def _build_context(data: dict[str, Any]) -> str:
    """Build compact BRD context for the LLM."""
    parts: list[str] = []

    # Personas
    personas = data.get("personas") or []
    if personas:
        parts.append("## Personas")
        for p in personas:
            goals = (p.get("goals") or [])[:3]
            pains = (p.get("pain_points") or [])[:3]
            parts.append(
                f"- {p.get('name', '?')} — {p.get('role', '?')}"
            )
            if goals:
                parts.append(f"  Goals: {'; '.join(goals)}")
            if pains:
                parts.append(f"  Pains: {'; '.join(pains)}")

    # Features
    features = data.get("features") or []
    if features:
        parts.append("\n## Features")
        for f in features[:30]:
            overview = (f.get("overview") or "")[:80]
            parts.append(
                f"- {f.get('name', '?')} "
                f"({f.get('category', '?')})"
                + (f" — {overview}" if overview else "")
            )

    # Business drivers
    drivers = data.get("drivers") or []
    pains = [d for d in drivers if d.get("driver_type") == "pain"]
    goals = [d for d in drivers if d.get("driver_type") == "goal"]
    kpis = [d for d in drivers if d.get("driver_type") == "kpi"]

    if pains:
        parts.append("\n## Pain Points")
        for d in pains:
            parts.append(f"- {(d.get('description') or '?')[:100]}")

    if goals:
        parts.append("\n## Goals")
        for d in goals:
            parts.append(f"- {(d.get('description') or '?')[:100]}")

    if kpis:
        parts.append("\n## KPIs")
        for d in kpis:
            desc = (d.get("description") or "?")[:80]
            baseline = d.get("baseline_value") or "?"
            target = d.get("target_value") or "?"
            parts.append(f"- {desc} ({baseline} → {target})")

    # Constraints
    constraints = _load_constraints(data)
    if constraints:
        parts.append("\n## Constraints")
        for c in constraints:
            parts.append(
                f"- [{c.get('severity', '?')}] "
                f"{c.get('title', '?')}: "
                f"{(c.get('description') or '')[:80]}"
            )

    # Data entities
    data_entities = _load_data_entities(data)
    if data_entities:
        parts.append("\n## Data Entities")
        for de in data_entities:
            parts.append(
                f"- {de.get('name', '?')} "
                f"({de.get('entity_category', '?')})"
            )

    # Existing workflows
    workflow_pairs = data.get("workflow_pairs") or []
    if workflow_pairs:
        parts.append("\n## Existing Workflows")
        for wp in workflow_pairs:
            parts.append(f"\n### {wp.get('name', '?')}")
            if wp.get("description"):
                parts.append(f"{wp['description'][:120]}")

            current = wp.get("current_steps") or []
            future = wp.get("future_steps") or []

            if current:
                parts.append("Current state:")
                for s in current:
                    pain = s.get("pain_description") or ""
                    line = (
                        f"  {s.get('step_index', '?')}. "
                        f"{s.get('label', '?')}"
                    )
                    if s.get("actor_persona_name"):
                        line += f" [{s['actor_persona_name']}]"
                    if pain:
                        line += f" — {pain[:60]}"
                    parts.append(line)

            if future:
                parts.append("Future state:")
                for s in future:
                    benefit = s.get("benefit_description") or ""
                    auto = s.get("automation_level", "manual")
                    line = (
                        f"  {s.get('step_index', '?')}. "
                        f"{s.get('label', '?')} [{auto}]"
                    )
                    if s.get("actor_persona_name"):
                        line += f" [{s['actor_persona_name']}]"
                    if benefit:
                        line += f" — {benefit[:60]}"
                    parts.append(line)

            roi = wp.get("roi")
            if roi:
                parts.append(
                    f"ROI: {roi.get('time_saved_percent', 0):.0f}% "
                    f"time saved, "
                    f"${roi.get('cost_saved_per_year', 0):,.0f}/yr"
                )
    else:
        parts.append("\n## Existing Workflows\nNone yet.")

    return "\n".join(parts)


def _load_constraints(data: dict[str, Any]) -> list[dict]:
    """Load constraints (not in load_project_data)."""
    try:
        from app.db.supabase_client import get_supabase

        pid = data.get("_project_id", "")
        if not pid:
            return []
        supabase = get_supabase()
        result = (
            supabase.table("constraints")
            .select("id, title, constraint_type, severity, "
                    "description")
            .eq("project_id", pid)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def _load_data_entities(data: dict[str, Any]) -> list[dict]:
    """Load data entities (not in load_project_data)."""
    try:
        from app.db.supabase_client import get_supabase

        pid = data.get("_project_id", "")
        if not pid:
            return []
        supabase = get_supabase()
        result = (
            supabase.table("data_entities")
            .select("id, name, entity_category, description")
            .eq("project_id", pid)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def _build_coverage(data: dict[str, Any]) -> CoverageSummary:
    """Compute lightweight coverage stats."""
    drivers = data.get("drivers") or []
    workflow_pairs = data.get("workflow_pairs") or []

    return CoverageSummary(
        workflows=sum(
            (1 if wp.get("current_workflow_id") else 0)
            + (1 if wp.get("future_workflow_id") else 0)
            for wp in workflow_pairs
        ),
        workflow_pairs=len(workflow_pairs),
        current_steps=sum(
            len(wp.get("current_steps") or [])
            for wp in workflow_pairs
        ),
        future_steps=sum(
            len(wp.get("future_steps") or [])
            for wp in workflow_pairs
        ),
        features=len(data.get("features") or []),
        personas=len(data.get("personas") or []),
        pains=sum(
            1 for d in drivers if d.get("driver_type") == "pain"
        ),
        goals=sum(
            1 for d in drivers if d.get("driver_type") == "goal"
        ),
        kpis=sum(
            1 for d in drivers if d.get("driver_type") == "kpi"
        ),
        constraints=len(data.get("_constraints") or []),
        data_entities=len(data.get("_data_entities") or []),
    )


# ============================================================================
# LLM call
# ============================================================================


_SYSTEM_PROMPT = """\
You are a senior business analyst reviewing a project's BRD. \
You have: personas, features, pains, goals, KPIs, constraints, \
data entities, and existing workflows.

The project already has workflows. Your job: look at what's \
covered, then identify the MOST IMPORTANT missing user journeys. \
Target {target} suggestions, maximum {max_suggestions}. Only suggest \
workflows that fill real gaps — not duplicates or minor variants.

Return VALID JSON (keep descriptions short — 1 sentence max):
{{
  "observations": ["short observation about coverage"],
  "suggested_workflows": [
    {{
      "name": "workflow name",
      "description": "one sentence",
      "owner_persona": "persona name",
      "rationale": "one sentence: why needed",
      "steps": [
        {{
          "label": "step name",
          "actor_persona_name": "persona name",
          "automation_level": "manual|semi_automated|fully_automated",
          "benefit_description": "short benefit"
        }}
      ],
      "addresses_features": ["feature name"],
      "addresses_pains": ["pain snippet"],
      "addresses_goals": ["goal snippet"]
    }}
  ]
}}

Rules:
- Target {target}, max {max_suggestions} suggested workflows
- 2-4 observations (one sentence each)
- 3-5 steps per workflow, keep step descriptions under 15 words
- Use persona names from the BRD
- Don't duplicate existing workflows
- Focus on the highest-impact gaps first"""


async def _suggest_workflows(
    context: str,
    existing_count: int = 0,
) -> tuple[list[str], list[SuggestedWorkflow]]:
    """Call Sonnet to suggest missing workflows."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    settings = get_settings()

    # Scale suggestions based on existing coverage
    target = max(2, 6 - existing_count)
    max_suggestions = min(6, max(2, 8 - existing_count))

    prompt = _SYSTEM_PROMPT.format(
        target=target, max_suggestions=max_suggestions,
    )

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.4,
        max_tokens=4000,
    )

    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=(
            "Analyze this project's BRD and suggest missing "
            "workflows:\n\n" + context
        )),
    ])

    text = response.content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            result = json.loads(match.group())
        else:
            logger.warning(
                "Could not parse workflow suggestion response"
            )
            return [], []

    observations = result.get("observations", [])

    suggested: list[SuggestedWorkflow] = []
    for sw in result.get("suggested_workflows", [])[:max_suggestions]:
        try:
            steps = []
            for s in sw.get("steps", [])[:8]:
                steps.append(SuggestedStep(
                    label=s.get("label", "?"),
                    actor_persona_name=s.get(
                        "actor_persona_name"
                    ),
                    automation_level=s.get(
                        "automation_level", "manual"
                    ),
                    operation_type=s.get("operation_type"),
                    benefit_description=s.get(
                        "benefit_description"
                    ),
                    time_minutes=s.get("time_minutes"),
                ))
            suggested.append(SuggestedWorkflow(
                name=sw.get("name", "?"),
                description=sw.get("description", ""),
                state_type=sw.get("state_type", "future"),
                owner_persona=sw.get("owner_persona"),
                rationale=sw.get("rationale", ""),
                steps=steps,
                addresses_features=sw.get(
                    "addresses_features", []
                ),
                addresses_pains=sw.get(
                    "addresses_pains", []
                ),
                addresses_goals=sw.get(
                    "addresses_goals", []
                ),
            ))
        except Exception:
            continue

    return observations, suggested


# ============================================================================
# Main entry point
# ============================================================================


async def analyze_workflow_gaps(
    project_id: UUID,
    include_semantic: bool = True,
) -> dict[str, Any]:
    """
    Analyze BRD and suggest missing workflows.

    1. load_project_data() for full BRD snapshot
    2. Lightweight coverage stats
    3. Sonnet call: "what workflows are missing?"

    Returns WorkflowGapAnalysis as dict.
    """
    from app.core.project_data import load_project_data

    t0 = time.time()

    # Load BRD data via existing infrastructure
    data = await load_project_data(project_id)
    # Stash project_id for constraint/data_entity loading
    data["_project_id"] = str(project_id)

    # Load constraints + data entities (not in load_project_data)
    constraints = _load_constraints(data)
    data_entities = _load_data_entities(data)
    data["_constraints"] = constraints
    data["_data_entities"] = data_entities

    t1 = time.time()

    # Coverage stats
    coverage = _build_coverage(data)

    # Build context for LLM
    context = _build_context(data)
    t2 = time.time()

    # Suggest missing workflows
    observations: list[str] = []
    suggested: list[SuggestedWorkflow] = []

    if include_semantic:
        try:
            observations, suggested = await _suggest_workflows(
                context,
                existing_count=coverage.workflow_pairs,
            )
        except Exception:
            logger.exception("Workflow suggestion failed")

    t3 = time.time()

    result = WorkflowGapAnalysis(
        project_id=str(project_id),
        coverage=coverage,
        suggested_workflows=suggested,
        observations=observations,
    )

    logger.info(
        f"Workflow gap analysis for {project_id}: "
        f"{len(suggested)} suggested workflows, "
        f"{len(observations)} observations. "
        f"Load: {t1-t0:.1f}s, "
        f"Context: {t2-t1:.2f}s, "
        f"LLM: {t3-t2:.1f}s"
    )

    return result.model_dump()
