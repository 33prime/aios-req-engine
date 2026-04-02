"""
Generate Future State Workflow Steps

Takes existing current-state workflows and generates future-state steps
based on project outcomes, features, pain points, and constraints.

For new products, the "current state" is the manual/painful way things
work today (inferred from discovery). The "future state" is how the
platform transforms those workflows.
"""

import json
import re
import time
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def generate_future_state_steps(
    project_id: UUID,
    workflow_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Generate future-state steps for current-state workflows.

    Args:
        project_id: The project UUID.
        workflow_ids: Optional list of specific workflow IDs. If None, processes all
                     current-state workflows missing future steps.

    Returns:
        {"workflows_updated": int, "steps_created": int, "details": [...]}
    """
    from anthropic import AsyncAnthropic
    from app.db.supabase_client import get_supabase

    settings = get_settings()
    sb = get_supabase()
    start = time.time()

    # Load project context
    project = sb.table("projects").select("*").eq("id", str(project_id)).single().execute().data
    project_name = project.get("name", "")
    project_type = project.get("project_type", "new_product")
    macro_outcome = project.get("macro_outcome") or ""
    vision = project.get("vision") or ""

    # Load workflows
    wf_query = sb.table("workflows").select("*").eq("project_id", str(project_id))
    if workflow_ids:
        wf_query = wf_query.in_("id", workflow_ids)
    workflows = wf_query.execute().data or []

    # Filter to current-state workflows
    current_workflows = [w for w in workflows if w.get("state_type") != "future"]
    if not current_workflows:
        return {"workflows_updated": 0, "steps_created": 0, "details": []}

    # Load current steps for these workflows
    wf_ids = [w["id"] for w in current_workflows]
    steps_resp = sb.table("vp_steps").select("*").in_("workflow_id", wf_ids).order("step_index").execute()
    all_steps = steps_resp.data or []

    steps_by_wf: dict[str, list] = {}
    for s in all_steps:
        wfid = s.get("workflow_id")
        if wfid:
            steps_by_wf.setdefault(wfid, []).append(s)

    # Check which workflows already have a paired future workflow
    paired_ids = {w.get("paired_workflow_id") for w in workflows if w.get("paired_workflow_id")}
    future_wfs = {w["id"]: w for w in workflows if w.get("state_type") == "future"}

    # Filter out workflows that already have future steps via pairing
    to_generate = []
    for wf in current_workflows:
        # Skip if already paired and the pair has steps
        paired_id = wf.get("paired_workflow_id")
        if paired_id and paired_id in future_wfs:
            future_step_count = len([s for s in all_steps if s.get("workflow_id") == paired_id])
            if future_step_count > 0:
                continue
        current_steps = steps_by_wf.get(wf["id"], [])
        if not current_steps:
            continue
        to_generate.append((wf, current_steps))

    if not to_generate:
        return {"workflows_updated": 0, "steps_created": 0, "details": []}

    # Load supporting context
    features = sb.table("features").select("name, category").eq("project_id", str(project_id)).execute().data or []
    outcomes = sb.table("outcomes").select("title, description, horizon").eq("project_id", str(project_id)).execute().data or []
    personas = sb.table("personas").select("name, role, goals, pain_points").eq("project_id", str(project_id)).execute().data or []
    constraints = sb.table("constraints").select("title").eq("project_id", str(project_id)).execute().data or []

    # Build context block
    context_parts = [f"Project: {project_name}"]
    if macro_outcome:
        context_parts.append(f"Macro Outcome: {macro_outcome}")
    if vision:
        context_parts.append(f"Vision: {vision}")
    if outcomes:
        context_parts.append("Outcomes:")
        for o in outcomes:
            context_parts.append(f"  - [{o.get('horizon','h1')}] {o['title']}")
    if features:
        context_parts.append("Features/Capabilities:")
        for f in features[:15]:
            cat = f" [{f['category']}]" if f.get("category") else ""
            context_parts.append(f"  - {f['name']}{cat}")
    if personas:
        context_parts.append("Actors:")
        for p in personas:
            goals = ", ".join((p.get("goals") or [])[:3])
            context_parts.append(f"  - {p['name']} ({p.get('role','')}): goals={goals}")
    if constraints:
        context_parts.append("Constraints:")
        for c in constraints:
            context_parts.append(f"  - {c['title']}")

    project_context = "\n".join(context_parts)

    # Build workflow descriptions
    workflow_blocks = []
    for wf, steps in to_generate:
        lines = [f"Workflow: {wf['name']}", f"Description: {wf.get('description', '')}"]
        lines.append("Current State Steps:")
        for s in steps:
            pain = f" | Pain: {s['pain_description']}" if s.get("pain_description") else ""
            lines.append(
                f"  {s.get('step_index', 0)}. {s.get('label', '')} "
                f"[{s.get('automation_level', 'manual')}, {s.get('time_minutes', '?')}min]"
                f" — {s.get('description', '')}{pain}"
            )
        workflow_blocks.append("\n".join(lines))

    workflows_text = "\n\n---\n\n".join(workflow_blocks)

    prompt = f"""You are a senior solutions architect designing the future-state workflows for a platform.

<project_context>
{project_context}
</project_context>

<current_state_workflows>
{workflows_text}
</current_state_workflows>

For EACH workflow above, generate the FUTURE STATE steps — how this workflow will work AFTER the platform is built. The future state should:

1. Address every pain point in the current state
2. Leverage the features and capabilities being built
3. Reduce time and manual effort dramatically
4. Use appropriate automation levels:
   - "fully_automated": System handles entirely, no human needed
   - "semi_automated": Human triggers or reviews, system executes
   - "manual": Step genuinely remains manual (rare in future state)
5. Include realistic time estimates (future steps should be much faster)
6. Include benefit_description for each step (what specifically improves vs current)

Return a JSON array where each element is:
{{
  "workflow_id": "<id>",
  "workflow_name": "<name>",
  "future_steps": [
    {{
      "step_index": 1,
      "label": "Short action label",
      "description": "1-2 sentence description of what happens",
      "time_minutes": 5,
      "automation_level": "semi_automated",
      "benefit_description": "What specifically improves vs current state"
    }}
  ]
}}

Rules:
- Generate 4-8 future steps per workflow
- Future steps should mirror and improve upon current steps — not be a completely different process
- Total time should be 50-80% less than current state
- At least 50% of steps should be semi_automated or fully_automated
- Labels should be concrete actions, not vague
- benefit_description is required for every step

Return ONLY valid JSON array, no markdown fences."""

    # Call Anthropic
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    generated = json.loads(raw)

    # Persist future state steps
    total_steps = 0
    details = []
    wf_lookup = {wf["id"]: wf for wf, _ in to_generate}

    # Also build a name-to-id lookup for fuzzy matching
    name_lookup = {wf["name"].lower().strip(): wf["id"] for wf, _ in to_generate}

    logger.info(f"LLM returned {len(generated)} workflow entries, wf_lookup has {len(wf_lookup)} entries")

    for entry in generated:
        wf_id = entry.get("workflow_id")
        # Try name-based matching if ID doesn't match
        if (not wf_id or wf_id not in wf_lookup) and entry.get("workflow_name"):
            matched_id = name_lookup.get(entry["workflow_name"].lower().strip())
            if matched_id:
                wf_id = matched_id
                logger.info(f"Matched by name: {entry['workflow_name']} -> {wf_id}")
        if not wf_id or wf_id not in wf_lookup:
            continue

        wf = wf_lookup[wf_id]
        future_steps = entry.get("future_steps", [])
        if not future_steps:
            continue

        # Create a future-state workflow
        future_wf = sb.table("workflows").insert({
            "project_id": str(project_id),
            "name": wf["name"],
            "description": wf.get("description", ""),
            "state_type": "future",
            "paired_workflow_id": wf_id,
            "confirmation_status": "ai_generated",
        }).execute().data[0]

        # Pair the current workflow back
        sb.table("workflows").update({
            "paired_workflow_id": future_wf["id"],
        }).eq("id", wf_id).execute()

        # Insert steps
        for idx, step in enumerate(future_steps):
            sb.table("vp_steps").insert({
                "project_id": str(project_id),
                "workflow_id": future_wf["id"],
                "step_index": step.get("step_index", idx + 1),
                "sort_order": idx + 1,
                "label": step.get("label", ""),
                "description": step.get("description", ""),
                "time_minutes": step.get("time_minutes"),
                "automation_level": step.get("automation_level", "semi_automated"),
                "benefit_description": step.get("benefit_description", ""),
                "confirmation_status": "ai_generated",
            }).execute()
            total_steps += 1

        details.append({
            "workflow_id": wf_id,
            "workflow_name": wf["name"],
            "future_workflow_id": future_wf["id"],
            "steps_created": len(future_steps),
        })

    duration = int((time.time() - start) * 1000)
    logger.info(
        f"Generated future state: {len(details)} workflows, {total_steps} steps in {duration}ms"
    )

    return {
        "workflows_updated": len(details),
        "steps_created": total_steps,
        "duration_ms": duration,
        "details": details,
    }
