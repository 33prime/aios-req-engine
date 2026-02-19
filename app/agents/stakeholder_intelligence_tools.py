"""Tool execution layer for Stakeholder Intelligence Agent.

Maps tool calls to backend operations. Each tool returns
a consistent dict with "success", "data", and optionally "error".
"""

import json
from typing import Any
from uuid import UUID

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.stakeholders import get_stakeholder, update_stakeholder, find_similar_stakeholder

logger = get_logger(__name__)


async def execute_si_tool(
    tool_name: str,
    tool_args: dict,
    stakeholder_id: UUID,
    project_id: UUID,
) -> dict:
    """Route and execute a Stakeholder Intelligence Agent tool."""
    logger.info(
        f"Executing SI tool: {tool_name}",
        extra={"stakeholder_id": str(stakeholder_id), "project_id": str(project_id)},
    )

    try:
        if tool_name == "enrich_engagement_profile":
            return await _execute_enrich_engagement(stakeholder_id, project_id)
        elif tool_name == "analyze_decision_authority":
            return await _execute_analyze_decision_authority(stakeholder_id, project_id)
        elif tool_name == "infer_relationships":
            return await _execute_infer_relationships(stakeholder_id, project_id)
        elif tool_name == "detect_communication_patterns":
            return await _execute_detect_communication(stakeholder_id, project_id)
        elif tool_name == "synthesize_win_conditions":
            return await _execute_synthesize_win_conditions(stakeholder_id, project_id)
        elif tool_name == "cross_reference_ci_insights":
            return await _execute_cross_reference_ci(stakeholder_id, project_id)
        elif tool_name == "enrich_from_external_sources":
            return await _execute_enrich_external(stakeholder_id, project_id)
        elif tool_name == "update_profile_completeness":
            return await _execute_update_profile_completeness(stakeholder_id, project_id)
        elif tool_name == "stop_with_guidance":
            return {"success": True, "data": tool_args}
        else:
            return {"success": False, "data": {}, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"SI tool {tool_name} failed: {e}", exc_info=True)
        return {"success": False, "data": {}, "error": str(e)}


# =============================================================================
# Helpers
# =============================================================================


def _load_stakeholder_context(stakeholder: dict, project_id: UUID) -> str:
    """Build context string from stakeholder + related signals."""
    from app.db.supabase_client import get_supabase

    parts = []
    parts.append(f"Name: {stakeholder.get('name', '?')}")
    parts.append(f"Role: {stakeholder.get('role', 'Unknown')}")
    parts.append(f"Type: {stakeholder.get('stakeholder_type', 'Unknown')}")
    parts.append(f"Influence: {stakeholder.get('influence_level', 'Unknown')}")

    if stakeholder.get("email"):
        parts.append(f"Email: {stakeholder['email']}")
    if stakeholder.get("organization"):
        parts.append(f"Organization: {stakeholder['organization']}")
    if stakeholder.get("notes"):
        parts.append(f"Notes: {stakeholder['notes'][:500]}")

    priorities = stakeholder.get("priorities") or []
    if isinstance(priorities, str):
        priorities = [priorities]
    if priorities:
        parts.append(f"Priorities: {', '.join(priorities[:5])}")

    concerns = stakeholder.get("concerns") or []
    if isinstance(concerns, str):
        concerns = [concerns]
    if concerns:
        parts.append(f"Concerns: {', '.join(concerns[:5])}")

    # Load evidence text
    evidence = stakeholder.get("evidence") or []
    for ev in evidence[:5]:
        if isinstance(ev, dict) and ev.get("text"):
            parts.append(f"Evidence: {ev['text'][:400]}")

    # Load signal chunks from source signals
    supabase = get_supabase()
    source_signal_ids = stakeholder.get("source_signal_ids") or []
    for sid in source_signal_ids[:5]:
        try:
            chunks = (
                supabase.table("signal_chunks")
                .select("content")
                .eq("signal_id", str(sid))
                .limit(3)
                .execute()
            )
            for chunk in (chunks.data or [])[:3]:
                content = chunk.get("content", "")[:600]
                if content:
                    parts.append(f"Signal excerpt: {content}")
        except Exception:
            pass

    # Load recent signals mentioning this stakeholder name
    name = stakeholder.get("name", "")
    if name:
        try:
            signals = (
                supabase.table("signals")
                .select("raw_text, signal_type, source_label")
                .eq("project_id", str(project_id))
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for sig in (signals.data or []):
                raw = sig.get("raw_text") or ""
                if name.lower() in raw.lower():
                    parts.append(
                        f"Signal ({sig.get('signal_type', '?')}): "
                        f"{raw[:600]}"
                    )
        except Exception:
            pass

    return "\n".join(parts)


def _track_field_changes(
    stakeholder_id: UUID,
    project_id: UUID,
    stakeholder: dict,
    updates: dict,
    source: str = "si_agent",
) -> list[str]:
    """Track which fields changed and record enrichment revision."""
    from app.db.supabase_client import get_supabase

    changed_fields = []
    changes = {}

    for key, new_val in updates.items():
        if key in ("updated_at", "version", "intelligence_version", "last_intelligence_at", "profile_completeness"):
            continue
        old_val = stakeholder.get(key)
        if old_val != new_val and new_val is not None:
            changed_fields.append(key)
            changes[key] = {"old": str(old_val)[:200] if old_val else None, "new": str(new_val)[:200]}

    if changed_fields:
        try:
            supabase = get_supabase()
            current_version = stakeholder.get("version", 1)
            supabase.table("enrichment_revisions").insert({
                "project_id": str(project_id),
                "entity_type": "stakeholder",
                "entity_id": str(stakeholder_id),
                "entity_label": stakeholder.get("name", "")[:100],
                "revision_type": "enriched",
                "changes": changes,
                "revision_number": current_version + 1,
                "diff_summary": f"SI Agent enriched: {', '.join(changed_fields[:5])}",
                "created_by": source,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to track enrichment revision: {e}")

    return changed_fields


def _apply_updates(
    stakeholder_id: UUID,
    project_id: UUID,
    stakeholder: dict,
    updates: dict,
) -> tuple[dict, list[str]]:
    """Apply updates to stakeholder, track changes, bump version."""
    current_version = stakeholder.get("version", 1)
    intel_version = stakeholder.get("intelligence_version", 0)

    updates["version"] = current_version + 1
    updates["intelligence_version"] = intel_version + 1
    updates["last_intelligence_at"] = "now()"

    changed = _track_field_changes(stakeholder_id, project_id, stakeholder, updates)

    result = update_stakeholder(stakeholder_id, updates)
    return result, changed


# =============================================================================
# Tool Executors
# =============================================================================


async def _execute_enrich_engagement(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Analyze signals for engagement cues."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    context = _load_stakeholder_context(stakeholder, project_id)

    prompt = f"""Analyze the engagement profile for this stakeholder.

{context}

Current engagement fields:
- engagement_level: {stakeholder.get('engagement_level', 'NOT SET')}
- engagement_strategy: {stakeholder.get('engagement_strategy', 'NOT SET')}
- risk_if_disengaged: {stakeholder.get('risk_if_disengaged', 'NOT SET')}

Based on the signals and evidence, assess:
1. How engaged is this person? (highly_engaged, moderately_engaged, neutral, disengaged)
2. What strategy should the consultant use to maintain/increase engagement?
3. What's the risk if this person disengages from the project?

Return JSON:
{{
    "engagement_level": "highly_engaged|moderately_engaged|neutral|disengaged",
    "engagement_strategy": "Specific actionable strategy for this person",
    "risk_if_disengaged": "Concrete impact description",
    "confidence": 0.0-1.0,
    "evidence_summary": "What signals informed this assessment"
}}"""

    analysis = await _call_sonnet(prompt, "engagement_profile")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    updates = {}
    if analysis.get("engagement_level"):
        updates["engagement_level"] = analysis["engagement_level"]
    if analysis.get("engagement_strategy"):
        updates["engagement_strategy"] = analysis["engagement_strategy"]
    if analysis.get("risk_if_disengaged"):
        updates["risk_if_disengaged"] = analysis["risk_if_disengaged"]

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    return {"success": True, "data": analysis}


async def _execute_analyze_decision_authority(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Infer decision patterns from transcripts/emails."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    context = _load_stakeholder_context(stakeholder, project_id)

    prompt = f"""Analyze the decision authority for this stakeholder.

{context}

Current decision fields:
- decision_authority: {stakeholder.get('decision_authority', 'NOT SET')}
- approval_required_for: {json.dumps(stakeholder.get('approval_required_for') or [], default=str)}
- veto_power_over: {json.dumps(stakeholder.get('veto_power_over') or [], default=str)}

Based on their role, interactions, and organizational position, determine:
1. What is their decision authority scope? (e.g., "Budget <$50K", "Technical architecture")
2. What specific areas require their approval?
3. What can they veto or block?

Return JSON:
{{
    "decision_authority": "Description of their decision scope",
    "approval_required_for": ["area1", "area2"],
    "veto_power_over": ["area1"],
    "confidence": 0.0-1.0,
    "reasoning": "How this was inferred"
}}"""

    analysis = await _call_sonnet(prompt, "decision_authority")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    updates = {}
    if analysis.get("decision_authority"):
        updates["decision_authority"] = analysis["decision_authority"]
    if analysis.get("approval_required_for"):
        updates["approval_required_for"] = analysis["approval_required_for"]
    if analysis.get("veto_power_over"):
        updates["veto_power_over"] = analysis["veto_power_over"]

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    return {"success": True, "data": analysis}


async def _execute_infer_relationships(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Detect hierarchy/alliances/blockers from co-occurrence."""
    from app.db.supabase_client import get_supabase

    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    # Load all project stakeholders for UUID resolution
    supabase = get_supabase()
    all_sh = (
        supabase.table("stakeholders")
        .select("id, name, role, stakeholder_type, influence_level")
        .eq("project_id", str(project_id))
        .execute()
    )
    other_stakeholders = [s for s in (all_sh.data or []) if s["id"] != str(stakeholder_id)]

    context = _load_stakeholder_context(stakeholder, project_id)

    other_sh_text = json.dumps(other_stakeholders, default=str)[:3000]

    prompt = f"""Analyze relationships for this stakeholder within the project.

TARGET STAKEHOLDER:
{context}

OTHER STAKEHOLDERS IN PROJECT:
{other_sh_text}

Current relationship fields:
- reports_to_id: {stakeholder.get('reports_to_id', 'NOT SET')}
- allies: {json.dumps(stakeholder.get('allies') or [], default=str)}
- potential_blockers: {json.dumps(stakeholder.get('potential_blockers') or [], default=str)}

Based on organizational cues, role hierarchy, and signal co-occurrence, determine:
1. Who does this person likely report to? (use exact name from the stakeholder list)
2. Who are their allies/champions? (people who support their goals)
3. Who are potential blockers? (people with conflicting priorities)

IMPORTANT: Only reference people from the OTHER STAKEHOLDERS list above. Use exact names.

Return JSON:
{{
    "reports_to_name": "Name of manager or null",
    "ally_names": ["Name1", "Name2"],
    "blocker_names": ["Name1"],
    "relationship_notes": "Key dynamics to be aware of",
    "confidence": 0.0-1.0
}}"""

    analysis = await _call_sonnet(prompt, "relationships")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    # Resolve names to UUIDs
    updates = {}
    resolved = {"reports_to": None, "allies": [], "blockers": []}

    reports_to_name = analysis.get("reports_to_name")
    if reports_to_name:
        match = find_similar_stakeholder(project_id, reports_to_name)
        if match and match["id"] != str(stakeholder_id):
            updates["reports_to_id"] = match["id"]
            resolved["reports_to"] = {"name": match["name"], "id": match["id"]}

    ally_names = analysis.get("ally_names") or []
    ally_ids = []
    for name in ally_names:
        match = find_similar_stakeholder(project_id, name)
        if match and match["id"] != str(stakeholder_id):
            ally_ids.append(match["id"])
            resolved["allies"].append({"name": match["name"], "id": match["id"]})
    if ally_ids:
        updates["allies"] = ally_ids

    blocker_names = analysis.get("blocker_names") or []
    blocker_ids = []
    for name in blocker_names:
        match = find_similar_stakeholder(project_id, name)
        if match and match["id"] != str(stakeholder_id):
            blocker_ids.append(match["id"])
            resolved["blockers"].append({"name": match["name"], "id": match["id"]})
    if blocker_ids:
        updates["potential_blockers"] = blocker_ids

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    analysis["resolved"] = resolved
    return {"success": True, "data": analysis}


async def _execute_detect_communication(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Infer channel preferences from signal metadata."""
    from app.db.supabase_client import get_supabase

    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    # Load signal types to infer communication patterns
    supabase = get_supabase()
    name = stakeholder.get("name", "")

    signal_types = []
    try:
        signals = (
            supabase.table("signals")
            .select("signal_type, source_label, source, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        signal_types = signals.data or []
    except Exception:
        pass

    context = _load_stakeholder_context(stakeholder, project_id)

    prompt = f"""Analyze communication patterns for this stakeholder.

{context}

Recent signal types in this project (shows how stakeholder communicates):
{json.dumps(signal_types, default=str)[:3000]}

Current communication fields:
- preferred_channel: {stakeholder.get('preferred_channel', 'NOT SET')}
- communication_preferences: {json.dumps(stakeholder.get('communication_preferences') or {}, default=str)}
- last_interaction_date: {stakeholder.get('last_interaction_date', 'NOT SET')}

Infer:
1. Preferred communication channel (email, meeting, chat, phone)
2. Communication style preferences (formal/informal, detail level, frequency)
3. Best time/approach for engaging them

Return JSON:
{{
    "preferred_channel": "email|meeting|chat|phone",
    "communication_preferences": {{
        "formality": "formal|informal|mixed",
        "detail_level": "high_detail|summary|bullet_points",
        "frequency": "weekly|biweekly|monthly|as_needed",
        "best_approach": "Description of how to approach"
    }},
    "last_interaction_date": "YYYY-MM-DD or null if unknown",
    "confidence": 0.0-1.0,
    "reasoning": "How this was inferred from signals"
}}"""

    analysis = await _call_sonnet(prompt, "communication_patterns")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    updates = {}
    if analysis.get("preferred_channel"):
        updates["preferred_channel"] = analysis["preferred_channel"]
    if analysis.get("communication_preferences"):
        updates["communication_preferences"] = analysis["communication_preferences"]
    if analysis.get("last_interaction_date") and analysis["last_interaction_date"] != "null":
        updates["last_interaction_date"] = analysis["last_interaction_date"]

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    return {"success": True, "data": analysis}


async def _execute_synthesize_win_conditions(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Synthesize goals and concerns from accumulated evidence."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    context = _load_stakeholder_context(stakeholder, project_id)

    prompt = f"""Synthesize win conditions and key concerns for this stakeholder.

{context}

Current fields:
- win_conditions: {json.dumps(stakeholder.get('win_conditions') or [], default=str)}
- key_concerns: {json.dumps(stakeholder.get('key_concerns') or [], default=str)}
- priorities: {json.dumps(stakeholder.get('priorities') or [], default=str)}
- concerns: {json.dumps(stakeholder.get('concerns') or [], default=str)}

Based on ALL available evidence (signals, stated priorities, role, organizational context):

1. What does SUCCESS look like for this person? What would make them a champion of the project?
2. What are their KEY CONCERNS? What could make them resist or disengage?

Be specific and actionable — avoid generic statements.

Return JSON:
{{
    "win_conditions": ["Specific success criterion 1", "Criterion 2", "Criterion 3"],
    "key_concerns": ["Specific concern 1", "Concern 2", "Concern 3"],
    "confidence": 0.0-1.0,
    "evidence_summary": "What informed these assessments"
}}"""

    analysis = await _call_sonnet(prompt, "win_conditions")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    updates = {}
    if analysis.get("win_conditions"):
        updates["win_conditions"] = analysis["win_conditions"]
    if analysis.get("key_concerns"):
        updates["key_concerns"] = analysis["key_concerns"]

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    return {"success": True, "data": analysis}


async def _execute_cross_reference_ci(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Flow CI-level organizational analysis back to individual stakeholder."""
    from app.db.supabase_client import get_supabase

    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    # Find the client for this project
    supabase = get_supabase()
    project = (
        supabase.table("projects")
        .select("client_id")
        .eq("id", str(project_id))
        .maybe_single()
        .execute()
    )
    if not project.data or not project.data.get("client_id"):
        return {"success": True, "data": {"message": "No client linked to project"}}

    client_id = project.data["client_id"]

    # Load client intelligence
    client = (
        supabase.table("clients")
        .select("name, organizational_context, constraint_summary, role_gaps, vision_synthesis")
        .eq("id", str(client_id))
        .maybe_single()
        .execute()
    )
    if not client.data:
        return {"success": True, "data": {"message": "Client not found"}}

    client_data = client.data
    org_context = client_data.get("organizational_context") or {}
    if isinstance(org_context, str):
        try:
            org_context = json.loads(org_context)
        except (json.JSONDecodeError, TypeError):
            org_context = {}

    role_gaps = client_data.get("role_gaps") or []
    if isinstance(role_gaps, str):
        try:
            role_gaps = json.loads(role_gaps)
        except (json.JSONDecodeError, TypeError):
            role_gaps = []

    constraints = client_data.get("constraint_summary") or []
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints)
        except (json.JSONDecodeError, TypeError):
            constraints = []

    if not org_context and not role_gaps and not constraints:
        return {"success": True, "data": {"message": "No CI insights available yet. Run CI Agent first."}}

    context = _load_stakeholder_context(stakeholder, project_id)

    prompt = f"""Cross-reference client-level intelligence with this individual stakeholder.

STAKEHOLDER:
{context}

CLIENT-LEVEL INTELLIGENCE:
Organization: {client_data.get('name', '?')}

Organizational Context:
{json.dumps(org_context, default=str)[:2000]}

Constraint Summary:
{json.dumps(constraints, default=str)[:1500]}

Role Gaps:
{json.dumps(role_gaps, default=str)[:1000]}

Vision: {client_data.get('vision_synthesis', 'Not set')}

Based on the organizational-level analysis, what insights apply to THIS specific stakeholder?

Consider:
1. How does the org's decision-making style affect this person's authority?
2. Do any constraints especially impact their domain?
3. Are they filling a gap that the role gap analysis identified?
4. How does the org context change engagement strategy for this person?

Return JSON:
{{
    "engagement_strategy_update": "Updated strategy based on org context, or null",
    "decision_authority_update": "Updated authority based on org analysis, or null",
    "risk_if_disengaged_update": "Updated risk based on role gaps, or null",
    "additional_concerns": ["Concern from org context"],
    "additional_win_conditions": ["Win condition from org vision"],
    "insights": "Key cross-reference insight for the consultant"
}}"""

    analysis = await _call_sonnet(prompt, "ci_cross_reference")
    if not analysis:
        return {"success": False, "data": {}, "error": "LLM analysis failed"}

    updates = {}
    if analysis.get("engagement_strategy_update"):
        updates["engagement_strategy"] = analysis["engagement_strategy_update"]
    if analysis.get("decision_authority_update"):
        updates["decision_authority"] = analysis["decision_authority_update"]
    if analysis.get("risk_if_disengaged_update"):
        updates["risk_if_disengaged"] = analysis["risk_if_disengaged_update"]

    # Merge additional concerns/win_conditions
    if analysis.get("additional_concerns"):
        existing = stakeholder.get("key_concerns") or []
        if isinstance(existing, str):
            existing = [existing]
        merged = list(set(existing + analysis["additional_concerns"]))
        if merged != existing:
            updates["key_concerns"] = merged

    if analysis.get("additional_win_conditions"):
        existing = stakeholder.get("win_conditions") or []
        if isinstance(existing, str):
            existing = [existing]
        merged = list(set(existing + analysis["additional_win_conditions"]))
        if merged != existing:
            updates["win_conditions"] = merged

    if updates:
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        analysis["fields_updated"] = changed

    return {"success": True, "data": analysis}


async def _execute_enrich_external(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Pull data from external APIs based on available identifiers.

    Routing logic (adapted from Forge stakeholder_enrichment module):
    - LinkedIn URL → PDL person + BrightData scrape in parallel
    - Email only → PDL person lookup by email
    - Organization website → Firecrawl for org context
    - None → returns guidance on what to collect
    """
    import asyncio

    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    linkedin_url = stakeholder.get("linkedin_profile")
    email = stakeholder.get("email")
    organization = stakeholder.get("organization")

    # Check if we have anything to work with
    if not linkedin_url and not email:
        return {
            "success": True,
            "data": {
                "sources_tried": [],
                "message": "No LinkedIn URL or email available. Ask the consultant to provide one.",
                "guidance": {
                    "most_valuable": "LinkedIn URL — confirms role, gives experience/skills/connections",
                    "second_best": "Email address — enables PDL person lookup",
                    "fallback": "Organization website — provides company context",
                },
            },
        }

    sources_tried = []
    sources_succeeded = []
    errors = []
    pdl_data = None
    bd_data = None

    # --- Parallel external enrichment ---

    async def safe_pdl():
        nonlocal pdl_data
        from app.core.pdl_service import enrich_person_safe
        result = await enrich_person_safe(
            linkedin_url=linkedin_url,
            email=email,
        )
        if result:
            pdl_data = result
            sources_succeeded.append("pdl")
        sources_tried.append("pdl")

    async def safe_brightdata():
        nonlocal bd_data
        if not linkedin_url:
            return
        from app.core.brightdata_service import scrape_linkedin_profile_safe
        result = await scrape_linkedin_profile_safe(linkedin_url)
        if result:
            bd_data = result
            sources_succeeded.append("brightdata")
        sources_tried.append("brightdata")

    tasks = [safe_pdl()]
    if linkedin_url:
        tasks.append(safe_brightdata())

    await asyncio.gather(*tasks, return_exceptions=True)

    # --- Apply data to stakeholder ---

    updates = {}
    data_summary = {"sources_tried": sources_tried, "sources_succeeded": sources_succeeded}

    # PDL data → role, organization, domain expertise, email
    if pdl_data:
        if pdl_data.get("job_title") and not stakeholder.get("role"):
            updates["role"] = pdl_data["job_title"]
        elif pdl_data.get("job_title") and stakeholder.get("role") != pdl_data["job_title"]:
            # Update if PDL gives a more specific title
            updates["role"] = pdl_data["job_title"]

        if pdl_data.get("company_name") and not stakeholder.get("organization"):
            updates["organization"] = pdl_data["company_name"]

        if pdl_data.get("skills"):
            existing_expertise = stakeholder.get("domain_expertise") or []
            merged = list(set(existing_expertise + pdl_data["skills"][:10]))
            if len(merged) > len(existing_expertise):
                updates["domain_expertise"] = merged

        if pdl_data.get("emails") and not stakeholder.get("email"):
            first_email = pdl_data["emails"][0]
            if isinstance(first_email, dict):
                first_email = first_email.get("address", "")
            if first_email:
                updates["email"] = first_email

        if pdl_data.get("linkedin_url") and not stakeholder.get("linkedin_profile"):
            updates["linkedin_profile"] = pdl_data["linkedin_url"]

        # Infer decision authority from title levels
        title_levels = pdl_data.get("job_title_levels") or []
        if title_levels and not stakeholder.get("decision_authority"):
            if any(l in title_levels for l in ["cxo", "director", "vp"]):
                updates["decision_authority"] = f"Senior leader ({', '.join(title_levels)}). Likely approves strategic and budget decisions."
            elif "manager" in title_levels:
                updates["decision_authority"] = f"Manager-level ({', '.join(title_levels)}). Approves operational decisions within their domain."

        data_summary["pdl"] = {
            "job_title": pdl_data.get("job_title"),
            "company": pdl_data.get("company_name"),
            "skills_count": len(pdl_data.get("skills") or []),
            "experience_count": len(pdl_data.get("experience") or []),
        }

    # BrightData LinkedIn → headline, about, engagement signals
    if bd_data:
        if bd_data.get("headline") and not stakeholder.get("role"):
            updates["role"] = bd_data["headline"]

        if bd_data.get("about"):
            # Extract win conditions from LinkedIn about section
            existing_notes = stakeholder.get("notes") or ""
            if "LinkedIn:" not in existing_notes:
                about_snippet = bd_data["about"][:500]
                updates["notes"] = (
                    f"{existing_notes}\n\nLinkedIn: {about_snippet}" if existing_notes
                    else f"LinkedIn: {about_snippet}"
                ).strip()

        if bd_data.get("follower_count"):
            # High follower count = thought leader / influencer
            followers = bd_data["follower_count"]
            if isinstance(followers, (int, float)) and followers > 5000:
                if not stakeholder.get("engagement_strategy"):
                    updates["engagement_strategy"] = (
                        f"Active LinkedIn presence ({followers:,} followers). "
                        "Engage via thought leadership — share industry insights and reference their content."
                    )

        if bd_data.get("current_company") and not stakeholder.get("organization"):
            company = bd_data["current_company"]
            if isinstance(company, dict):
                company = company.get("name", str(company))
            updates["organization"] = str(company)

        data_summary["brightdata"] = {
            "headline": bd_data.get("headline"),
            "has_about": bool(bd_data.get("about")),
            "follower_count": bd_data.get("follower_count"),
            "posts_count": len(bd_data.get("posts") or []),
            "experience_count": len(bd_data.get("experience") or []),
        }

    # Apply updates
    if updates:
        updates["enrichment_status"] = "enriched"
        _, changed = _apply_updates(stakeholder_id, project_id, stakeholder, updates)
        data_summary["fields_updated"] = changed
    else:
        data_summary["fields_updated"] = []
        data_summary["message"] = "External sources returned data but no new fields to update."

    return {"success": True, "data": data_summary}


async def _execute_update_profile_completeness(stakeholder_id: UUID, project_id: UUID) -> dict:
    """Recompute stakeholder profile completeness score. No LLM call."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {"success": False, "data": {}, "error": "Stakeholder not found"}

    score = 0
    sections: dict[str, int] = {}

    # 1. Core Identity (10 pts)
    core_score = 0
    if stakeholder.get("name"):
        core_score += 3
    if stakeholder.get("role"):
        core_score += 3
    if stakeholder.get("stakeholder_type"):
        core_score += 2
    if stakeholder.get("email"):
        core_score += 2
    sections["core_identity"] = min(10, core_score)
    score += sections["core_identity"]

    # 2. Engagement Profile (20 pts)
    eng_score = 0
    if stakeholder.get("engagement_level"):
        eng_score += 7
    if stakeholder.get("engagement_strategy"):
        eng_score += 7
    if stakeholder.get("risk_if_disengaged"):
        eng_score += 6
    sections["engagement_profile"] = min(20, eng_score)
    score += sections["engagement_profile"]

    # 3. Decision Authority (20 pts)
    dec_score = 0
    if stakeholder.get("decision_authority"):
        dec_score += 10
    if stakeholder.get("approval_required_for"):
        dec_score += 5
    if stakeholder.get("veto_power_over"):
        dec_score += 5
    sections["decision_authority"] = min(20, dec_score)
    score += sections["decision_authority"]

    # 4. Relationships (20 pts)
    rel_score = 0
    if stakeholder.get("reports_to_id"):
        rel_score += 8
    if stakeholder.get("allies"):
        rel_score += 6
    if stakeholder.get("potential_blockers"):
        rel_score += 6
    sections["relationships"] = min(20, rel_score)
    score += sections["relationships"]

    # 5. Communication (10 pts)
    comm_score = 0
    if stakeholder.get("preferred_channel"):
        comm_score += 4
    if stakeholder.get("communication_preferences"):
        comm_score += 4
    if stakeholder.get("last_interaction_date"):
        comm_score += 2
    sections["communication"] = min(10, comm_score)
    score += sections["communication"]

    # 6. Win Conditions & Concerns (15 pts)
    win_score = 0
    wc = stakeholder.get("win_conditions") or []
    kc = stakeholder.get("key_concerns") or []
    if isinstance(wc, str):
        wc = [wc]
    if isinstance(kc, str):
        kc = [kc]
    win_score += min(8, len(wc) * 3)
    win_score += min(7, len(kc) * 3)
    sections["win_conditions_concerns"] = min(15, win_score)
    score += sections["win_conditions_concerns"]

    # 7. Evidence Depth (5 pts)
    ev_score = 0
    source_signals = stakeholder.get("source_signal_ids") or []
    evidence = stakeholder.get("evidence") or []
    ev_count = max(len(source_signals), len(evidence))
    ev_score = min(5, ev_count * 2)
    sections["evidence_depth"] = ev_score
    score += sections["evidence_depth"]

    total = min(100, score)
    label = "Poor" if total < 30 else "Fair" if total < 60 else "Good" if total < 80 else "Excellent"

    update_stakeholder(stakeholder_id, {
        "profile_completeness": total,
        "last_intelligence_at": "now()",
    })

    return {
        "success": True,
        "data": {
            "score": total,
            "label": label,
            "sections": sections,
        },
    }


# =============================================================================
# LLM Helper
# =============================================================================


async def _call_sonnet(prompt: str, context: str = "") -> dict[str, Any]:
    """Call Claude Sonnet for analysis. Returns parsed JSON or empty dict."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning(f"No Anthropic API key for SI tool ({context})")
        return {}

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low"},
        )

        # Log LLM usage for cost tracking
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="stakeholder_intelligence",
            chain=context,
            model=response.model,
            provider="anthropic",
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
        )

        text = response.content[0].text if response.content else "{}"
        return _parse_json_response(text, context)
    except Exception as e:
        logger.error(f"Sonnet call failed ({context}): {e}")
        return {}


def _parse_json_response(text: str, context: str = "") -> dict[str, Any]:
    """Robustly parse JSON from LLM response."""
    import re

    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from SI tool response ({context})")
    return {}
