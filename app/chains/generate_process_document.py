"""Generate a structured process document from a KB item seed.

Uses project context (workflows, personas, data entities, stakeholders, signals)
to build a comprehensive process document with steps, roles, data flow,
decision points, exceptions, and tribal knowledge callouts.
"""

import json
import time
from typing import Any

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a business process documentation expert. Your job is to take a knowledge base \
item (a short text snippet about a business process, SOP, or institutional knowledge) \
and expand it into a full, structured process document.

You will receive:
1. The KB item text and its category
2. Project context: workflows, value path steps, personas, data entities, stakeholders
3. Relevant signal excerpts that may contain additional detail

Your output must be a JSON object with these sections:

{
    "title": "Clear process title",
    "purpose": "Why this process exists and its business value",
    "trigger_event": "What initiates this process",
    "frequency": "How often it occurs (daily, weekly, ad-hoc, etc.)",
    "generation_scenario": "reconstruct|generate|tribal_capture",
    "steps": [
        {
            "step_index": 1,
            "label": "Step name",
            "description": "What happens",
            "actor_persona_id": "uuid or null",
            "actor_persona_name": "Who does this",
            "vp_step_id": "uuid or null if matches existing VP step",
            "time_minutes": 5,
            "decision_points": ["Decision that must be made here"],
            "exceptions": ["What can go wrong"],
            "evidence": [{"signal_id": "uuid", "excerpt": "relevant quote"}]
        }
    ],
    "roles": [
        {
            "persona_id": "uuid or null",
            "persona_name": "Role name",
            "responsibilities": ["What they're responsible for"],
            "authority_level": "approver|executor|reviewer|informed",
            "evidence": []
        }
    ],
    "data_flow": [
        {
            "data_entity_id": "uuid or null",
            "data_entity_name": "Data object name",
            "operation": "create|read|update|delete|validate|transfer",
            "step_indices": [1, 3],
            "description": "How this data is used",
            "evidence": []
        }
    ],
    "decision_points": [
        {
            "label": "Decision name",
            "description": "What must be decided",
            "criteria": ["Criterion 1"],
            "outcomes": ["Outcome A", "Outcome B"],
            "owner_persona_id": "uuid or null",
            "step_index": 2,
            "evidence": []
        }
    ],
    "exceptions": [
        {
            "label": "Exception name",
            "description": "What goes wrong",
            "handling_procedure": "How to handle it",
            "escalation_path": "Who to escalate to",
            "frequency": "rare|occasional|frequent",
            "evidence": []
        }
    ],
    "tribal_knowledge_callouts": [
        {
            "text": "The insight or undocumented knowledge",
            "stakeholder_name": "Who knows this",
            "context": "Why this matters",
            "importance": "critical|important|nice_to_know",
            "evidence": []
        }
    ],
    "evidence": [
        {"signal_id": "uuid", "excerpt": "supporting text", "section": "which section"}
    ]
}

Rules:
- Link to existing persona IDs and VP step IDs where they match (use the UUIDs provided)
- Link to existing data entity IDs where data objects match
- If the KB item describes an existing process with clear steps, set scenario to "reconstruct"
- If the KB item is vague and you're inferring the process, set scenario to "generate"
- If the KB item contains undocumented institutional knowledge, set scenario to "tribal_capture"
- Include evidence references wherever possible (signal_id + excerpt)
- Every step should have at least an actor and description
- Be thorough but realistic — don't fabricate steps that aren't supported by context
- Output ONLY valid JSON, no markdown fences
"""


def _load_project_context(project_id: str) -> dict[str, Any]:
    """Load project context for process document generation."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    # Workflows / VP steps
    vp_steps_resp = (
        supabase.table("vp_steps")
        .select("id, step_index, label, description, actor_persona_id, actor_persona_name, time_minutes")
        .eq("project_id", project_id)
        .order("step_index")
        .execute()
    )

    # Personas
    personas_resp = (
        supabase.table("personas")
        .select("id, name, role, description")
        .eq("project_id", project_id)
        .execute()
    )

    # Data entities
    data_entities_resp = (
        supabase.table("data_entities")
        .select("id, name, description, entity_category, fields")
        .eq("project_id", project_id)
        .execute()
    )

    # Stakeholders
    stakeholders_resp = (
        supabase.table("stakeholders")
        .select("id, name, first_name, last_name, role, stakeholder_type, domain_expertise")
        .eq("project_id", project_id)
        .execute()
    )

    # Recent signals (for evidence)
    signals_resp = (
        supabase.table("signals")
        .select("id, raw_text, signal_type, source")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # Features
    features_resp = (
        supabase.table("features")
        .select("id, name, overview, category")
        .eq("project_id", project_id)
        .limit(30)
        .execute()
    )

    return {
        "vp_steps": vp_steps_resp.data or [],
        "personas": personas_resp.data or [],
        "data_entities": data_entities_resp.data or [],
        "stakeholders": stakeholders_resp.data or [],
        "signals": signals_resp.data or [],
        "features": features_resp.data or [],
    }


def _parse_json_response(text: str) -> dict[str, Any]:
    """Robustly parse JSON from LLM response."""
    import re

    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown fences
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        pass

    # Regex fallback
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON from process document generation response")
    return {}


def generate_process_document(
    kb_item_text: str,
    kb_category: str,
    project_id: str,
    client_id: str | None = None,
) -> dict[str, Any]:
    """Generate a structured process document from a KB item.

    Args:
        kb_item_text: The KB item text to expand
        kb_category: Category (business_processes, sops, tribal_knowledge)
        project_id: Project UUID for context loading
        client_id: Optional client UUID

    Returns:
        Dict with all structured sections + generation metadata
    """
    settings = get_settings()
    start_time = time.time()

    logger.info(f"Generating process document for project {project_id}, category={kb_category}")

    # Load project context
    context = _load_project_context(project_id)

    # Build user prompt
    user_message = f"""## KB Item to Expand
**Category:** {kb_category}
**Text:** {kb_item_text}

## Project Context

### Value Path Steps ({len(context['vp_steps'])} steps)
{json.dumps(context['vp_steps'], default=str)[:4000]}

### Personas ({len(context['personas'])} personas)
{json.dumps(context['personas'], default=str)[:2000]}

### Data Entities ({len(context['data_entities'])} entities)
{json.dumps(context['data_entities'], default=str)[:2000]}

### Stakeholders ({len(context['stakeholders'])} stakeholders)
{json.dumps(context['stakeholders'], default=str)[:1500]}

### Features ({len(context['features'])} features)
{json.dumps(context['features'], default=str)[:2000]}

### Recent Signals (for evidence)
{json.dumps([{"id": s["id"], "type": s.get("signal_type"), "excerpt": (s.get("raw_text") or "")[:300]} for s in context['signals']], default=str)[:3000]}

Generate the full structured process document JSON."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text if response.content else "{}"
    doc = _parse_json_response(text)

    duration_ms = int((time.time() - start_time) * 1000)

    # Add generation metadata
    doc["generation_model"] = "claude-sonnet-4-20250514"
    doc["generation_duration_ms"] = duration_ms
    doc["project_id"] = project_id
    if client_id:
        doc["client_id"] = client_id

    logger.info(
        f"Generated process document: {doc.get('title', 'untitled')}, "
        f"{len(doc.get('steps', []))} steps, {duration_ms}ms"
    )

    return doc
