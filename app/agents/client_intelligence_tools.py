"""Tool execution layer for Client Intelligence Agent.

Maps tool calls to backend operations. Each tool returns
a consistent dict with "success", "data", and optionally "error".
"""

import json
from typing import Any
from uuid import UUID

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.clients import (
    get_client,
    get_client_projects,
    update_client,
    update_client_enrichment,
)

logger = get_logger(__name__)


async def execute_ci_tool(
    tool_name: str,
    tool_args: dict,
    client_id: UUID,
) -> dict:
    """Route and execute a Client Intelligence Agent tool."""
    logger.info(f"Executing CI tool: {tool_name}", extra={"client_id": str(client_id)})

    try:
        if tool_name == "enrich_firmographics":
            return await _execute_enrich_firmographics(client_id)
        elif tool_name == "analyze_stakeholder_map":
            return await _execute_analyze_stakeholder_map(client_id)
        elif tool_name == "identify_role_gaps":
            return await _execute_identify_role_gaps(client_id)
        elif tool_name == "synthesize_constraints":
            return await _execute_synthesize_constraints(
                client_id, tool_args.get("include_inferred", True)
            )
        elif tool_name == "synthesize_vision":
            return await _execute_synthesize_vision(client_id)
        elif tool_name == "analyze_data_landscape":
            return await _execute_analyze_data_landscape(client_id)
        elif tool_name == "assess_organizational_context":
            return await _execute_assess_organizational_context(client_id)
        elif tool_name == "assess_portfolio_health":
            return await _execute_assess_portfolio_health(client_id)
        elif tool_name == "update_profile_completeness":
            return await _execute_update_profile_completeness(client_id)
        elif tool_name == "generate_process_document":
            return await _execute_generate_process_document(
                client_id,
                tool_args.get("project_id", ""),
                tool_args.get("kb_category", ""),
                tool_args.get("kb_item_id", ""),
            )
        elif tool_name == "stop_with_guidance":
            return {"success": True, "data": tool_args}
        else:
            return {"success": False, "data": {}, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"CI tool {tool_name} failed: {e}", exc_info=True)
        return {"success": False, "data": {}, "error": str(e)}


# =============================================================================
# Tool Executors
# =============================================================================


async def _execute_enrich_firmographics(client_id: UUID) -> dict:
    """Enrich client with firmographic data."""
    from app.chains.enrich_client import enrich_client

    result = await enrich_client(client_id)

    if result.get("success"):
        # Update completeness after enrichment
        await _execute_update_profile_completeness(client_id)

    return {
        "success": result.get("success", False),
        "data": {
            "enrichment_source": result.get("enrichment_source"),
            "fields_enriched": result.get("fields_enriched", []),
        },
        "error": result.get("error"),
    }


async def _execute_analyze_stakeholder_map(client_id: UUID) -> dict:
    """Analyze stakeholders across all client projects."""
    from app.db.supabase_client import get_supabase

    projects = get_client_projects(client_id)
    if not projects:
        return {"success": True, "data": {"stakeholders": [], "message": "No projects linked"}}

    supabase = get_supabase()
    project_ids = [p["id"] for p in projects]

    # Load all stakeholders across projects
    all_stakeholders = []
    for pid in project_ids:
        resp = (
            supabase.table("stakeholders")
            .select("id, name, first_name, last_name, role, email, stakeholder_type, "
                    "influence_level, is_primary_contact, decision_authority, domain_expertise, "
                    "concerns, project_id")
            .eq("project_id", pid)
            .execute()
        )
        all_stakeholders.extend(resp.data)

    if not all_stakeholders:
        return {"success": True, "data": {
            "stakeholders": [],
            "analysis": "No stakeholders found across client projects.",
            "role_distribution": {},
        }}

    # Analyze with Sonnet
    settings = get_settings()
    client_data = get_client(client_id)
    client_name = client_data.get("name", "Unknown") if client_data else "Unknown"

    stakeholder_text = json.dumps(all_stakeholders, default=str)[:6000]
    projects_text = json.dumps(projects, default=str)[:2000]

    prompt = f"""Analyze the stakeholder landscape for client "{client_name}".

Stakeholders across {len(projects)} projects:
{stakeholder_text}

Projects:
{projects_text}

Return JSON:
{{
    "decision_makers": ["name - role"],
    "influence_map": {{"high": ["name"], "medium": ["name"], "low": ["name"]}},
    "alignment_notes": "Brief assessment of stakeholder alignment",
    "potential_conflicts": ["description of potential conflict"],
    "cross_project_stakeholders": ["name appears in multiple projects"],
    "engagement_assessment": "Overall engagement level assessment"
}}"""

    analysis = await _call_sonnet(prompt, "stakeholder_analysis")

    # Store organizational context
    if analysis:
        org_context = client_data.get("organizational_context") or {}
        org_context["stakeholder_analysis"] = analysis
        update_client(client_id, {"organizational_context": json.dumps(org_context) if isinstance(org_context, dict) else org_context})

    return {
        "success": True,
        "data": {
            "stakeholder_count": len(all_stakeholders),
            "project_count": len(projects),
            "analysis": analysis or {},
        },
    }


async def _execute_identify_role_gaps(client_id: UUID) -> dict:
    """Identify missing roles for requirements gathering."""
    from app.db.supabase_client import get_supabase

    client_data = get_client(client_id)
    if not client_data:
        return {"success": False, "data": {}, "error": "Client not found"}

    projects = get_client_projects(client_id)
    project_ids = [p["id"] for p in projects]

    supabase = get_supabase()

    # Load stakeholders, features, and workflows for context
    stakeholders = []
    features = []
    workflows = []

    for pid in project_ids:
        sh = supabase.table("stakeholders").select("name, role, stakeholder_type, domain_expertise").eq("project_id", pid).execute()
        stakeholders.extend(sh.data)
        ft = supabase.table("features").select("name, overview, priority_group").eq("project_id", pid).limit(20).execute()
        features.extend(ft.data)
        wf = supabase.table("vp_steps").select("label, description, actor_persona_id").eq("project_id", pid).limit(20).execute()
        workflows.extend(wf.data)

    prompt = f"""Analyze the stakeholder roster for client "{client_data.get('name')}" and identify missing roles.

Industry: {client_data.get('industry', 'Unknown')}
Company size: {client_data.get('size', 'Unknown')}

Current stakeholders:
{json.dumps(stakeholders, default=str)[:3000]}

Features being built:
{json.dumps(features, default=str)[:2000]}

Workflow steps:
{json.dumps(workflows, default=str)[:2000]}

Identify roles that SHOULD be involved but aren't represented. Consider:
- Technical leads for complex features
- Domain experts for specialized workflows
- Compliance/legal for regulated industries
- Data stewards for data-heavy features
- End users who'll actually use the system
- Executive sponsors for budget decisions

Return JSON:
{{
    "missing_roles": [
        {{
            "role": "Role title",
            "why_needed": "Why this role matters for this client",
            "urgency": "high|medium|low",
            "which_areas": ["features/workflows this role would inform"]
        }}
    ],
    "well_covered_areas": ["areas with good stakeholder coverage"],
    "recommendation": "Summary recommendation"
}}"""

    analysis = await _call_sonnet(prompt, "role_gap_analysis")

    # Store role gaps
    if analysis and analysis.get("missing_roles"):
        update_client(client_id, {"role_gaps": json.dumps(analysis["missing_roles"])})

    return {"success": True, "data": analysis or {}}


async def _execute_synthesize_constraints(client_id: UUID, include_inferred: bool) -> dict:
    """Synthesize constraints from signals and firmographics."""
    from app.db.supabase_client import get_supabase

    client_data = get_client(client_id)
    if not client_data:
        return {"success": False, "data": {}, "error": "Client not found"}

    projects = get_client_projects(client_id)
    project_ids = [p["id"] for p in projects]

    supabase = get_supabase()

    # Load existing constraints and business drivers
    constraints = []
    drivers = []
    for pid in project_ids:
        c = supabase.table("constraints").select("title, description, constraint_type, severity").eq("project_id", pid).execute()
        constraints.extend(c.data)
        d = supabase.table("business_drivers").select("description, driver_type, severity").eq("project_id", pid).execute()
        drivers.extend(d.data)

    inferred_section = ""
    if include_inferred:
        inferred_section = f"""
Also INFER likely constraints from the client's profile:
- Industry: {client_data.get('industry')} → what regulatory/compliance constraints are standard?
- Size: {client_data.get('size')} → what resource/budget constraints are typical?
- Tech maturity: {client_data.get('technology_maturity')} → what technical constraints exist?
- Digital readiness: {client_data.get('digital_readiness')} → what organizational constraints?

Mark inferred constraints with "source": "ai_inferred" and explain the reasoning.
"""

    prompt = f"""Synthesize all constraints for client "{client_data.get('name')}".

Existing constraints from signals:
{json.dumps(constraints, default=str)[:3000]}

Business drivers (pains/goals that imply constraints):
{json.dumps(drivers, default=str)[:2000]}

Client profile:
- Industry: {client_data.get('industry', 'Unknown')}
- Size: {client_data.get('size', 'Unknown')}
- Revenue: {client_data.get('revenue_range', 'Unknown')}
- Tech stack: {json.dumps(client_data.get('tech_stack', []))}
- Digital readiness: {client_data.get('digital_readiness', 'Unknown')}
{inferred_section}

Return JSON:
{{
    "constraints": [
        {{
            "title": "Constraint title",
            "description": "What this means for the project",
            "category": "budget|timeline|regulatory|organizational|technical|strategic",
            "severity": "must_have|should_have|nice_to_have",
            "source": "signal|stakeholder|ai_inferred",
            "source_detail": "Where this came from",
            "impacts": ["What this constrains"]
        }}
    ],
    "category_summary": {{
        "budget": "Brief summary of budget constraints",
        "timeline": "Brief summary",
        "regulatory": "Brief summary",
        "organizational": "Brief summary",
        "technical": "Brief summary",
        "strategic": "Brief summary"
    }},
    "risk_assessment": "Overall constraint risk assessment"
}}"""

    analysis = await _call_sonnet(prompt, "constraint_synthesis")

    if analysis and analysis.get("constraints"):
        update_client(client_id, {"constraint_summary": json.dumps(analysis["constraints"])})

    return {"success": True, "data": analysis or {}}


async def _execute_synthesize_vision(client_id: UUID) -> dict:
    """Synthesize coherent vision from project data."""
    from app.db.supabase_client import get_supabase

    client_data = get_client(client_id)
    if not client_data:
        return {"success": False, "data": {}, "error": "Client not found"}

    projects = get_client_projects(client_id)
    supabase = get_supabase()

    # Load vision and strategic context from each project
    visions = []
    for p in projects:
        proj = supabase.table("projects").select("name, vision, description").eq("id", p["id"]).maybe_single().execute()
        if proj.data:
            visions.append(proj.data)

    # Load business drivers for goal alignment
    drivers = []
    for p in projects:
        d = supabase.table("business_drivers").select("description, driver_type").eq("project_id", p["id"]).execute()
        drivers.extend(d.data)

    prompt = f"""Synthesize a coherent vision for client "{client_data.get('name')}".

Project visions and descriptions:
{json.dumps(visions, default=str)[:3000]}

Business drivers:
{json.dumps(drivers, default=str)[:2000]}

Company context:
- Summary: {client_data.get('company_summary', 'Not available')}
- Market position: {client_data.get('market_position', 'Not available')}

Create a synthesized vision that:
1. Unifies themes across projects
2. Ties back to business drivers
3. Is clear and measurable

Return JSON:
{{
    "synthesized_vision": "2-3 sentence unified vision",
    "clarity_score": 0.0-1.0,
    "clarity_assessment": "What makes it clear or unclear",
    "completeness_assessment": "What's covered vs missing",
    "success_criteria": ["Measurable success criterion 1", "Criterion 2"],
    "alignment_with_drivers": "How well the vision connects to business drivers",
    "recommendations": ["How to strengthen the vision"]
}}"""

    analysis = await _call_sonnet(prompt, "vision_synthesis")

    if analysis and analysis.get("synthesized_vision"):
        update_client(client_id, {"vision_synthesis": analysis["synthesized_vision"]})

    return {"success": True, "data": analysis or {}}


async def _execute_analyze_data_landscape(client_id: UUID) -> dict:
    """Analyze data entities across client projects."""
    from app.db.supabase_client import get_supabase

    client_data = get_client(client_id)
    if not client_data:
        return {"success": False, "data": {}, "error": "Client not found"}

    projects = get_client_projects(client_id)
    supabase = get_supabase()

    entities = []
    for p in projects:
        de = supabase.table("data_entities").select("name, description, entity_category, fields").eq("project_id", p["id"]).execute()
        entities.extend(de.data)

    if not entities:
        return {"success": True, "data": {
            "entities": [],
            "message": "No data entities found. Consider extracting from signals.",
        }}

    prompt = f"""Analyze the data landscape for client "{client_data.get('name')}".

Industry: {client_data.get('industry', 'Unknown')}

Data entities across {len(projects)} projects:
{json.dumps(entities, default=str)[:5000]}

Analyze:
1. Domain model completeness — are key business objects represented?
2. Field definitions — which entities need more field detail?
3. Relationships — what connections between entities are implied?
4. AI/ML opportunities — which fields or entities could benefit from AI processing?
5. Data sensitivity — which entities contain PII, financial data, or health data?
6. System events — which entities need real-time events (created, updated, deleted)?

Return JSON:
{{
    "entity_count": 0,
    "completeness_assessment": "How complete is the domain model",
    "missing_entities": ["Entities that should exist given the industry/workflows"],
    "field_gaps": [{{"entity": "name", "missing_fields": ["field1"], "why_needed": "reason"}}],
    "relationships": [{{"from": "Entity A", "to": "Entity B", "type": "1:M", "description": "why"}}],
    "ai_opportunities": [{{"entity": "name", "field": "field_name", "opportunity": "what AI could do"}}],
    "sensitivity_flags": [{{"entity": "name", "classification": "PII|PHI|Financial", "fields": ["field"]}}],
    "event_needs": [{{"entity": "name", "events": ["created", "updated"], "why": "reason"}}]
}}"""

    analysis = await _call_sonnet(prompt, "data_landscape")
    return {"success": True, "data": analysis or {}}


async def _execute_assess_organizational_context(client_id: UUID) -> dict:
    """Assess organizational dynamics from signals and stakeholders."""
    from app.db.supabase_client import get_supabase

    client_data = get_client(client_id)
    if not client_data:
        return {"success": False, "data": {}, "error": "Client not found"}

    projects = get_client_projects(client_id)
    supabase = get_supabase()

    # Load recent signals for organizational cues
    signals = []
    stakeholders = []
    for p in projects:
        s = (supabase.table("signals")
             .select("raw_text, signal_type, source")
             .eq("project_id", p["id"])
             .order("created_at", desc=True)
             .limit(5)
             .execute())
        for sig in s.data:
            signals.append({"content": (sig.get("raw_text") or "")[:500], "type": sig.get("signal_type")})
        sh = supabase.table("stakeholders").select("name, role, stakeholder_type, influence_level, concerns").eq("project_id", p["id"]).execute()
        stakeholders.extend(sh.data)

    prompt = f"""Assess the organizational context for client "{client_data.get('name')}".

Company profile:
- Industry: {client_data.get('industry', 'Unknown')}
- Size: {client_data.get('size', 'Unknown')}
- Digital readiness: {client_data.get('digital_readiness', 'Unknown')}
- Tech maturity: {client_data.get('technology_maturity', 'Unknown')}

Stakeholders:
{json.dumps(stakeholders, default=str)[:3000]}

Recent signal excerpts (meeting notes, emails, etc.):
{json.dumps(signals, default=str)[:3000]}

Assess:
1. Decision-making style (consensus, top-down, distributed)
2. Change readiness (resistant, cautious, open, eager)
3. Organizational politics (who has real power vs formal power)
4. Communication patterns (formal, informal, mixed)
5. Risk tolerance (risk-averse, moderate, risk-taking)

Return JSON:
{{
    "decision_making_style": "consensus|top_down|distributed|unknown",
    "decision_making_notes": "Evidence for this assessment",
    "change_readiness": "resistant|cautious|open|eager|unknown",
    "change_readiness_notes": "Evidence",
    "risk_tolerance": "risk_averse|moderate|risk_taking|unknown",
    "political_dynamics": "Assessment of organizational politics",
    "communication_style": "formal|informal|mixed|unknown",
    "key_insight": "The most important thing to know about working with this organization",
    "watch_out_for": ["Potential pitfall 1", "Potential pitfall 2"]
}}"""

    analysis = await _call_sonnet(prompt, "organizational_context")

    if analysis:
        org_context = client_data.get("organizational_context") or {}
        if isinstance(org_context, str):
            try:
                org_context = json.loads(org_context)
            except json.JSONDecodeError:
                org_context = {}
        org_context["assessment"] = analysis
        update_client(client_id, {"organizational_context": json.dumps(org_context)})

    return {"success": True, "data": analysis or {}}


async def _execute_assess_portfolio_health(client_id: UUID) -> dict:
    """Assess project portfolio health."""
    from app.db.supabase_client import get_supabase

    projects = get_client_projects(client_id)
    if not projects:
        return {"success": True, "data": {"message": "No projects linked to client"}}

    supabase = get_supabase()

    # Get entity counts per project
    project_summaries = []
    for p in projects:
        pid = p["id"]
        features = supabase.table("features").select("id", count="exact").eq("project_id", pid).execute()
        personas = supabase.table("personas").select("id", count="exact").eq("project_id", pid).execute()
        signals = supabase.table("signals").select("id", count="exact").eq("project_id", pid).execute()

        project_summaries.append({
            "name": p.get("name"),
            "stage": p.get("stage"),
            "status": p.get("status"),
            "feature_count": features.count or 0,
            "persona_count": personas.count or 0,
            "signal_count": signals.count or 0,
        })

    result_data = {
        "project_count": len(projects),
        "projects": project_summaries,
        "summary": f"{len(projects)} projects, "
                   f"{sum(p['feature_count'] for p in project_summaries)} total features, "
                   f"{sum(p['signal_count'] for p in project_summaries)} total signals",
    }

    # Update completeness after portfolio assessment to avoid agent re-selecting this tool
    await _execute_update_profile_completeness(client_id)

    return {"success": True, "data": result_data}


async def _execute_update_profile_completeness(client_id: UUID) -> dict:
    """Recompute client profile completeness score."""
    client = get_client(client_id)
    if not client:
        return {"success": False, "data": {}, "error": "Client not found"}

    score = 0
    sections: dict[str, int] = {}

    # 1. Firmographics (15 pts)
    firm_score = 0
    if client.get("company_summary"):
        firm_score += 5
    if client.get("market_position"):
        firm_score += 5
    firmographic_fields = ["employee_count", "revenue_range", "headquarters", "founding_year", "tech_stack"]
    filled = sum(1 for f in firmographic_fields if client.get(f))
    firm_score += min(5, filled * 1)
    sections["firmographics"] = min(15, firm_score)
    score += sections["firmographics"]

    # 2. Stakeholder Map (20 pts)
    from app.db.clients import get_client_stakeholder_count
    sh_count = get_client_stakeholder_count(client_id)
    sh_score = min(10, sh_count * 3)  # 3 pts per stakeholder, max 10
    org = client.get("organizational_context") or {}
    if isinstance(org, str):
        try:
            org = json.loads(org)
        except (json.JSONDecodeError, TypeError):
            org = {}
    if org.get("stakeholder_analysis"):
        sh_score += 5
    if client.get("role_gaps"):
        sh_score += 5
    sections["stakeholder_map"] = min(20, sh_score)
    score += sections["stakeholder_map"]

    # 3. Organizational Context (15 pts)
    org_score = 0
    if org.get("assessment"):
        assessment = org["assessment"]
        if assessment.get("decision_making_style") and assessment["decision_making_style"] != "unknown":
            org_score += 5
        if assessment.get("change_readiness") and assessment["change_readiness"] != "unknown":
            org_score += 5
        if assessment.get("key_insight"):
            org_score += 5
    sections["organizational_context"] = min(15, org_score)
    score += sections["organizational_context"]

    # 4. Constraints (15 pts)
    constraints = client.get("constraint_summary") or []
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints)
        except (json.JSONDecodeError, TypeError):
            constraints = []
    constraint_categories = set()
    for c in constraints:
        if isinstance(c, dict):
            constraint_categories.add(c.get("category", ""))
    c_score = min(10, len(constraints) * 2)  # 2 pts per constraint, max 10
    c_score += min(5, len(constraint_categories) * 2)  # 2 pts per category, max 5
    sections["constraints"] = min(15, c_score)
    score += sections["constraints"]

    # 5. Vision & Strategy (10 pts)
    v_score = 0
    if client.get("vision_synthesis"):
        v_score += 7
    projects = get_client_projects(client_id)
    for p in projects:
        from app.db.supabase_client import get_supabase
        proj = get_supabase().table("projects").select("vision").eq("id", p["id"]).maybe_single().execute()
        if proj.data and proj.data.get("vision"):
            v_score += 3
            break
    sections["vision_strategy"] = min(10, v_score)
    score += sections["vision_strategy"]

    # 6. Data Landscape (10 pts)
    de_count = 0
    for p in projects:
        from app.db.supabase_client import get_supabase
        de = get_supabase().table("data_entities").select("id", count="exact").eq("project_id", p["id"]).execute()
        de_count += de.count or 0
    sections["data_landscape"] = min(10, de_count * 3)  # 3 pts per entity, max 10
    score += sections["data_landscape"]

    # 7. Competitive Context (10 pts)
    competitors = client.get("competitors") or []
    if isinstance(competitors, str):
        try:
            competitors = json.loads(competitors)
        except (json.JSONDecodeError, TypeError):
            competitors = []
    sections["competitive_context"] = min(10, len(competitors) * 5)
    score += sections["competitive_context"]

    # 8. Portfolio Health (5 pts)
    portfolio_score = min(5, len(projects) * 2)  # 2 pts per project, max 5
    sections["portfolio_health"] = portfolio_score
    score += sections["portfolio_health"]

    total = min(100, score)
    label = "Poor" if total < 30 else "Fair" if total < 60 else "Good" if total < 80 else "Excellent"

    update_client(client_id, {
        "profile_completeness": total,
        "last_analyzed_at": "now()",
    })

    return {
        "success": True,
        "data": {
            "score": total,
            "label": label,
            "sections": sections,
        },
    }


async def _execute_generate_process_document(
    client_id: UUID, project_id: str, kb_category: str, kb_item_id: str
) -> dict:
    """Generate a process document from a KB item."""
    from app.chains.generate_process_document import generate_process_document
    from app.db.process_documents import (
        create_process_document,
        get_process_document_by_kb_item,
    )
    from app.db.supabase_client import get_supabase

    # Check if already exists
    existing = get_process_document_by_kb_item(kb_item_id)
    if existing:
        return {
            "success": True,
            "data": {
                "doc_id": existing["id"],
                "title": existing["title"],
                "message": "Process document already exists for this KB item",
            },
        }

    # Find KB item text — stored as JSONB array directly on clients table column
    supabase = get_supabase()
    client_resp = (
        supabase.table("clients")
        .select(f"{kb_category}")
        .eq("id", str(client_id))
        .maybe_single()
        .execute()
    )
    if not client_resp or not client_resp.data:
        return {"success": False, "data": {}, "error": "Client not found"}

    items = client_resp.data.get(kb_category, [])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, TypeError):
            items = []
    kb_item_text = None
    for item in items:
        if isinstance(item, dict) and item.get("id") == kb_item_id:
            kb_item_text = item.get("text")
            break

    if not kb_item_text:
        return {"success": False, "data": {}, "error": "KB item not found"}

    # Generate
    doc_data = generate_process_document(
        kb_item_text=kb_item_text,
        kb_category=kb_category,
        project_id=project_id,
        client_id=str(client_id),
    )

    doc_data["source_kb_category"] = kb_category
    doc_data["source_kb_item_id"] = kb_item_id
    if not doc_data.get("title"):
        doc_data["title"] = kb_item_text[:80]

    from uuid import UUID as _UUID
    doc = create_process_document(project_id=_UUID(project_id), data=doc_data)

    return {
        "success": True,
        "data": {
            "doc_id": doc["id"],
            "title": doc["title"],
            "step_count": len(doc.get("steps") or []),
            "role_count": len(doc.get("roles") or []),
            "scenario": doc.get("generation_scenario"),
        },
    }


# =============================================================================
# Helpers
# =============================================================================


async def _call_sonnet(prompt: str, context: str = "") -> dict[str, Any]:
    """Call Claude Sonnet for analysis. Returns parsed JSON or empty dict."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning(f"No Anthropic API key for CI tool ({context})")
        return {}

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
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

    logger.warning(f"Failed to parse JSON from CI tool response ({context})")
    return {}
