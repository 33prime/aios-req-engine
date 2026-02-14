"""Tool execution layer for DI Agent.

Maps DI Agent tool calls to actual backend operations. Each tool returns
a consistent dict format with "success" flag and "data".
"""

import json
from uuid import UUID

from anthropic import Anthropic
from openai import OpenAI

from app.chains.analyze_requirements_gaps import analyze_requirements_gaps
from app.db.project_memory import (
    add_decision,
    add_learning,
    get_memory_for_context,
    get_or_create_project_memory,
    update_project_memory,
)
from app.chains.enrich_competitor import enrich_competitor
from app.chains.enrich_kpi import enrich_kpi
from app.chains.enrich_pain_point import enrich_pain_point
from app.chains.enrich_goal import enrich_goal
from app.chains.enrich_stakeholder import enrich_stakeholder
from app.chains.enrich_risk import enrich_risk
from app.chains.extract_budget_constraints import extract_budget_constraints
from app.chains.extract_business_case import extract_business_case
from app.chains.extract_core_pain import extract_core_pain
from app.chains.extract_primary_persona import extract_primary_persona
from app.chains.extract_risks_from_signals import extract_risks_from_signals
from app.chains.identify_wow_moment import identify_wow_moment
from app.chains.propose_entity_updates import propose_entity_updates
from app.chains.run_strategic_foundation import run_strategic_foundation
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.readiness.score import compute_readiness
from app.db.business_drivers import list_business_drivers, smart_upsert_business_driver
from app.db.competitor_refs import list_competitor_refs, smart_upsert_competitor_ref
from app.db.foundation import get_foundation_element
from app.db.signals import list_project_signals
from app.db.stakeholders import list_stakeholders, smart_upsert_stakeholder
from app.db.di_cache import mark_signals_analyzed, update_cache
from app.graphs.research_agent_graph import run_research_agent_graph

logger = get_logger(__name__)


async def execute_di_tool(
    tool_name: str,
    tool_args: dict,
    project_id: UUID,
) -> dict:
    """
    Execute a DI Agent tool.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool (from LLM)
        project_id: Project UUID

    Returns:
        Dict with:
        - success: bool - Whether the tool executed successfully
        - data: dict - Tool result data
        - error: str | None - Error message if failed
    """
    logger.info(
        f"Executing DI tool: {tool_name}",
        extra={
            "project_id": str(project_id),
            "tool_name": tool_name,
            "tool_args": tool_args,
        },
    )

    try:
        # Route to appropriate tool executor
        if tool_name == "run_foundation":
            result = await _execute_run_foundation(project_id, tool_args)
        elif tool_name == "run_research":
            result = await _execute_run_research(project_id, tool_args)
        elif tool_name == "extract_core_pain":
            result = await _execute_extract_core_pain(project_id, tool_args)
        elif tool_name == "extract_primary_persona":
            result = await _execute_extract_primary_persona(project_id, tool_args)
        elif tool_name == "identify_wow_moment":
            result = await _execute_identify_wow_moment(project_id, tool_args)
        elif tool_name == "extract_business_case":
            result = await _execute_extract_business_case(project_id, tool_args)
        elif tool_name == "extract_budget_constraints":
            result = await _execute_extract_budget_constraints(project_id, tool_args)
        elif tool_name == "suggest_discovery_questions":
            result = await _execute_suggest_discovery_questions(project_id, tool_args)
        elif tool_name == "analyze_gaps":
            result = await _execute_analyze_gaps(project_id, tool_args)
        elif tool_name == "stop_with_guidance":
            result = await _execute_stop_with_guidance(project_id, tool_args)
        # Strategic Foundation tools (Phase 3)
        elif tool_name == "extract_business_drivers":
            result = await _execute_extract_business_drivers(project_id, tool_args)
        elif tool_name == "enrich_business_driver":
            result = await _execute_enrich_business_driver(project_id, tool_args)
        elif tool_name == "extract_competitors":
            result = await _execute_extract_competitors(project_id, tool_args)
        elif tool_name == "enrich_competitor":
            result = await _execute_enrich_competitor(project_id, tool_args)
        elif tool_name == "extract_stakeholders":
            result = await _execute_extract_stakeholders(project_id, tool_args)
        elif tool_name == "extract_risks":
            result = await _execute_extract_risks(project_id, tool_args)
        # Requirements Gap Analysis tools
        elif tool_name == "analyze_requirements_gaps":
            result = await _execute_analyze_requirements_gaps(project_id, tool_args)
        elif tool_name == "propose_entity_updates":
            result = await _execute_propose_entity_updates(project_id, tool_args)
        # Memory tools
        elif tool_name == "read_project_memory":
            result = await _execute_read_project_memory(project_id, tool_args)
        elif tool_name == "update_project_understanding":
            result = await _execute_update_project_understanding(project_id, tool_args)
        elif tool_name == "log_decision":
            result = await _execute_log_decision(project_id, tool_args)
        elif tool_name == "record_learning":
            result = await _execute_record_learning(project_id, tool_args)
        elif tool_name == "update_strategy":
            result = await _execute_update_strategy(project_id, tool_args)
        elif tool_name == "add_open_question":
            result = await _execute_add_open_question(project_id, tool_args)
        elif tool_name == "synthesize_value_path":
            result = await _execute_synthesize_value_path(project_id, tool_args)
        elif tool_name == "run_discover":
            result = await _execute_run_discover(project_id, tool_args)
        else:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "data": {},
                "error": f"Unknown tool: {tool_name}",
            }

        logger.info(
            f"DI tool executed successfully: {tool_name}",
            extra={
                "project_id": str(project_id),
                "tool_name": tool_name,
                "success": result.get("success", False),
            },
        )

        return result

    except Exception as e:
        logger.error(
            f"Error executing DI tool {tool_name}: {e}",
            exc_info=True,
            extra={
                "project_id": str(project_id),
                "tool_name": tool_name,
            },
        )
        return {
            "success": False,
            "data": {},
            "error": str(e),
        }


# ==========================================================================
# Tool Executors
# ==========================================================================


async def _execute_run_foundation(project_id: UUID, args: dict) -> dict:
    """
    Execute strategic foundation builder.

    Runs the full strategic foundation chain which extracts features,
    personas, VP steps, PRD sections, and stakeholders.
    """
    from datetime import datetime, timezone

    try:
        # Get current signals BEFORE running foundation
        signals_before = list_project_signals(project_id)
        signal_ids = [s["id"] for s in signals_before] if signals_before else []

        result = await run_strategic_foundation(project_id)

        # Mark signals as analyzed in the DI cache so agent doesn't repeat
        if signal_ids:
            try:
                mark_signals_analyzed(project_id, [UUID(s) for s in signal_ids])
                logger.info(f"Marked {len(signal_ids)} signals as analyzed for project {project_id}")
            except Exception as cache_err:
                logger.warning(f"Failed to update DI cache (non-fatal): {cache_err}")

        # Also update last_full_analysis_at
        try:
            update_cache(
                project_id,
                last_full_analysis_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as cache_err:
            logger.warning(f"Failed to update last_full_analysis_at (non-fatal): {cache_err}")

        # Calculate totals from result
        drivers_total = (
            result.get("business_drivers_created", 0) +
            result.get("business_drivers_updated", 0) +
            result.get("business_drivers_merged", 0)
        )
        competitors_total = (
            result.get("competitor_refs_created", 0) +
            result.get("competitor_refs_updated", 0) +
            result.get("competitor_refs_merged", 0)
        )

        return {
            "success": True,
            "data": {
                "company_enriched": result.get("company_enriched", False),
                "enrichment_source": result.get("enrichment_source"),
                "stakeholders_linked": result.get("stakeholders_linked", 0),
                "business_drivers_created": result.get("business_drivers_created", 0),
                "business_drivers_updated": result.get("business_drivers_updated", 0),
                "business_drivers_merged": result.get("business_drivers_merged", 0),
                "business_drivers_total": drivers_total,
                "competitor_refs_created": result.get("competitor_refs_created", 0),
                "competitor_refs_updated": result.get("competitor_refs_updated", 0),
                "competitor_refs_merged": result.get("competitor_refs_merged", 0),
                "competitor_refs_total": competitors_total,
                "signals_analyzed": len(signal_ids),
                "errors": result.get("errors", []),
                "message": f"Strategic foundation extracted: {drivers_total} business drivers, {competitors_total} competitor refs",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Foundation extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Foundation extraction failed: {str(e)}",
        }


async def _execute_run_research(project_id: UUID, args: dict) -> dict:
    """
    Execute research agent.

    Runs research queries using Perplexity to gather competitive/market context.
    """
    try:
        # Extract research goal from args (LLM should provide this)
        research_goal = args.get("research_goal", "Gather competitive and market context")

        result = await run_research_agent_graph(
            project_id=project_id,
            research_goal=research_goal,
        )

        return {
            "success": True,
            "data": {
                "queries_executed": result.get("queries_executed", 0),
                "findings_count": result.get("findings_count", 0),
                "synthesis": result.get("synthesis", "")[:500],  # Truncate for brevity
                "message": "Research completed successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Research agent failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Research agent failed: {str(e)}",
        }


async def _execute_run_discover(project_id: UUID, args: dict) -> dict:
    """
    Execute the discovery intelligence pipeline.

    Runs parallelized data-first research: SerpAPI → PDL + Firecrawl → Sonnet synthesis.
    Produces business drivers with evidence chains and entity links.
    """
    import uuid as uuid_mod

    from app.db.jobs import create_job, start_job
    from app.db.supabase_client import get_supabase

    try:
        company_name = args.get("company_name")
        company_website = args.get("company_website")
        industry = args.get("industry")
        focus_areas = args.get("focus_areas", [])

        if not company_name:
            # Try to get from project
            supabase = get_supabase()
            project = supabase.table("projects").select(
                "name, company_name, company_website, industry"
            ).eq("id", str(project_id)).maybe_single().execute()
            if project.data:
                company_name = project.data.get("company_name") or project.data.get("name", "Unknown")
                company_website = company_website or project.data.get("company_website")
                industry = industry or project.data.get("industry")

        run_id = uuid_mod.uuid4()
        job_id = create_job(
            project_id=project_id,
            job_type="discovery_pipeline",
            input_json={
                "company_name": company_name,
                "company_website": company_website,
                "industry": industry,
                "focus_areas": focus_areas,
            },
            run_id=run_id,
        )

        start_job(job_id)

        from app.graphs.discovery_pipeline_graph import run_discovery_pipeline

        result = run_discovery_pipeline(
            project_id=project_id,
            run_id=run_id,
            job_id=job_id,
            company_name=company_name or "Unknown",
            company_website=company_website,
            industry=industry,
            focus_areas=focus_areas,
        )

        return {
            "success": result.get("success", False),
            "data": {
                "job_id": str(job_id),
                "signal_id": result.get("signal_id"),
                "drivers_count": result.get("business_drivers_count", 0),
                "competitors_count": result.get("competitors_count", 0),
                "total_cost_usd": result.get("total_cost_usd", 0),
                "phase_errors": result.get("phase_errors", {}),
                "message": "Discovery pipeline completed",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Discovery pipeline failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Discovery pipeline failed: {str(e)}",
        }


async def _execute_extract_core_pain(project_id: UUID, args: dict) -> dict:
    """
    Extract core pain from signals.

    Returns THE singular core pain that the project is trying to solve.
    """
    try:
        # Extract optional args
        signal_ids = args.get("signal_ids", None)
        depth = args.get("depth", "standard")

        core_pain = await extract_core_pain(
            project_id=project_id,
            signal_ids=signal_ids,
            depth=depth,
        )

        return {
            "success": True,
            "data": {
                "statement": core_pain.statement,
                "confidence": core_pain.confidence,
                "trigger": core_pain.trigger,
                "stakes": core_pain.stakes,
                "who_feels_it": core_pain.who_feels_it,
                "message": "Core pain extracted successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Core pain extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Core pain extraction failed: {str(e)}",
        }


async def _execute_extract_primary_persona(project_id: UUID, args: dict) -> dict:
    """
    Extract primary persona from signals.

    Returns THE primary persona who feels the core pain most.
    """
    try:
        # Primary persona extraction loads core_pain from DB if not provided
        primary_persona = await extract_primary_persona(project_id=project_id)

        return {
            "success": True,
            "data": {
                "name": primary_persona.name,
                "role": primary_persona.role,
                "confidence": primary_persona.confidence,
                "context": primary_persona.context,
                "pain_experienced": primary_persona.pain_experienced,
                "current_behavior": primary_persona.current_behavior,
                "desired_outcome": primary_persona.desired_outcome,
                "message": "Primary persona extracted successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Primary persona extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Primary persona extraction failed: {str(e)}",
        }


async def _execute_identify_wow_moment(project_id: UUID, args: dict) -> dict:
    """
    Identify wow moment from signals.

    Returns THE wow moment where pain inverts to delight.
    """
    try:
        # Wow moment identification loads dependencies from DB if not provided
        wow_moment = await identify_wow_moment(project_id=project_id)

        return {
            "success": True,
            "data": {
                "description": wow_moment.description,
                "confidence": wow_moment.confidence,
                "trigger_event": wow_moment.trigger_event,
                "emotional_response": wow_moment.emotional_response,
                "level_1_core": wow_moment.level_1_core,
                "level_2_adjacent": wow_moment.level_2_adjacent,
                "level_3_unstated": wow_moment.level_3_unstated,
                "message": "Wow moment identified successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Wow moment identification failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Wow moment identification failed: {str(e)}",
        }


async def _execute_extract_business_case(project_id: UUID, args: dict) -> dict:
    """
    Extract business case from signals.

    Returns business value, ROI, KPIs, and priority.
    """
    try:
        business_case = await extract_business_case(project_id=project_id)

        return {
            "success": True,
            "data": {
                "value_to_business": business_case.value_to_business,
                "roi_framing": business_case.roi_framing,
                "why_priority": business_case.why_priority,
                "confidence": business_case.confidence,
                "kpi_count": len(business_case.success_kpis),
                "message": "Business case extracted successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Business case extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Business case extraction failed: {str(e)}",
        }


async def _execute_extract_budget_constraints(project_id: UUID, args: dict) -> dict:
    """
    Extract budget and constraints from signals.

    Returns budget range, timeline, and technical/organizational constraints.
    """
    try:
        budget_constraints = await extract_budget_constraints(project_id=project_id)

        return {
            "success": True,
            "data": {
                "budget_range": budget_constraints.budget_range,
                "budget_flexibility": budget_constraints.budget_flexibility,
                "timeline": budget_constraints.timeline,
                "confidence": budget_constraints.confidence,
                "technical_constraints_count": len(budget_constraints.technical_constraints),
                "organizational_constraints_count": len(
                    budget_constraints.organizational_constraints
                ),
                "message": "Budget and constraints extracted successfully",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Budget/constraints extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Budget/constraints extraction failed: {str(e)}",
        }


async def _execute_suggest_discovery_questions(project_id: UUID, args: dict) -> dict:
    """
    Generate targeted discovery questions based on gate gaps.

    Analyzes current gate status and generates specific questions to fill gaps.
    """
    try:
        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Get current readiness with gates
        readiness = compute_readiness(project_id)

        # Build gate analysis
        unsatisfied_gates = [
            gate for gate in readiness.gates if not gate.is_satisfied
        ]

        if not unsatisfied_gates:
            return {
                "success": True,
                "data": {
                    "questions": [],
                    "message": "All gates satisfied - no discovery questions needed",
                },
                "error": None,
            }

        # Build prompt for LLM
        gates_summary = "\n".join(
            [
                f"- {gate.gate_name}: {gate.status} (confidence: {gate.confidence:.2f}, "
                f"reason: {gate.reason_not_satisfied or 'N/A'})"
                for gate in unsatisfied_gates
            ]
        )

        system_prompt = """You are a senior consultant expert at asking targeted discovery questions.

Your job is to generate specific, actionable questions that will help fill gaps in the project foundation.

For each unsatisfied gate, generate 2-3 questions that:
1. Are specific and actionable (not generic)
2. Will elicit the information needed to satisfy the gate
3. Are appropriate to ask at this stage of the project
4. Help understand WHY this information is missing

Output as JSON array of question objects:
{
  "questions": [
    {
      "gate": "gate_name",
      "question": "Specific question text?",
      "rationale": "Why this question helps"
    }
  ]
}"""

        user_prompt = f"""Generate targeted discovery questions for these unsatisfied gates:

{gates_summary}

Generate 2-3 specific questions per gate that will help gather the missing information.

Output as JSON."""

        response = client.chat.completions.create(
            model=settings.FACTS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        parsed = json.loads(raw_output)
        questions = parsed.get("questions", [])

        return {
            "success": True,
            "data": {
                "questions": questions,
                "unsatisfied_gate_count": len(unsatisfied_gates),
                "message": f"Generated {len(questions)} discovery questions",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Discovery questions generation failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Discovery questions generation failed: {str(e)}",
        }


async def _execute_analyze_gaps(project_id: UUID, args: dict) -> dict:
    """
    Analyze gaps between current foundation and complete state.

    Compares what we have vs what we need for each gate.
    """
    try:
        # Get current readiness with gates
        readiness = compute_readiness(project_id)

        # Analyze each gate
        gap_analysis = []

        for gate in readiness.gates:
            gap = {
                "gate": gate.gate_name,
                "is_satisfied": gate.is_satisfied,
                "confidence": gate.confidence,
                "completeness": gate.completeness,
                "status": gate.status,
            }

            # Add gap details if not satisfied
            if not gate.is_satisfied:
                gap["gap_type"] = (
                    "low_confidence" if gate.confidence < 0.7 else "incomplete"
                )
                gap["reason"] = gate.reason_not_satisfied
                gap["recommended_action"] = _get_recommended_action(gate.gate_name)

            gap_analysis.append(gap)

        # Calculate summary
        total_gates = len(readiness.gates)
        satisfied_gates = sum(1 for g in readiness.gates if g.is_satisfied)
        avg_confidence = sum(g.confidence for g in readiness.gates) / total_gates

        return {
            "success": True,
            "data": {
                "gaps": gap_analysis,
                "summary": {
                    "total_gates": total_gates,
                    "satisfied_gates": satisfied_gates,
                    "unsatisfied_gates": total_gates - satisfied_gates,
                    "avg_confidence": round(avg_confidence, 2),
                    "current_phase": readiness.phase,
                },
                "message": f"Analyzed {total_gates} gates, found {total_gates - satisfied_gates} gaps",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Gap analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Gap analysis failed: {str(e)}",
        }


async def _execute_stop_with_guidance(project_id: UUID, args: dict) -> dict:
    """
    Format guidance for consultant.

    Packages reasoning and recommendations for human decision-making.
    """
    try:
        # Extract guidance from args (LLM should provide this)
        guidance_text = args.get("guidance", "")
        next_steps = args.get("next_steps", [])
        reasoning = args.get("reasoning", "")

        # Get current readiness for context
        readiness = compute_readiness(project_id)

        return {
            "success": True,
            "data": {
                "guidance": guidance_text,
                "next_steps": next_steps,
                "reasoning": reasoning,
                "current_phase": readiness.phase,
                "current_score": readiness.total_readiness,
                "message": "Guidance prepared for consultant",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Guidance formatting failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Guidance formatting failed: {str(e)}",
        }


# ==========================================================================
# Strategic Foundation Tools (Phase 3)
# ==========================================================================


async def _execute_extract_business_drivers(project_id: UUID, args: dict) -> dict:
    """
    Extract and update business drivers (KPIs, pain points, goals) from signals.

    Uses smart_upsert to merge evidence and update existing drivers.
    """
    try:
        driver_types = args.get("driver_types", ["kpi", "pain", "goal"])
        enrich = args.get("enrich", False)
        signal_ids = args.get("signal_ids", None)

        # Use the run_strategic_foundation extraction
        from app.chains.run_strategic_foundation import extract_strategic_entities_from_signals

        result = extract_strategic_entities_from_signals(project_id)

        # Optionally enrich newly created drivers
        enriched_count = 0
        if enrich:
            drivers = list_business_drivers(project_id, limit=100)
            for driver in drivers:
                if driver.get("enrichment_status") == "none":
                    driver_type = driver.get("driver_type")
                    driver_id = UUID(driver["id"])

                    try:
                        if driver_type == "kpi":
                            await enrich_kpi(driver_id, project_id, depth="quick")
                        elif driver_type == "pain":
                            await enrich_pain_point(driver_id, project_id, depth="quick")
                        elif driver_type == "goal":
                            await enrich_goal(driver_id, project_id, depth="quick")
                        enriched_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to enrich {driver_type} driver {driver_id}: {e}")

        return {
            "success": True,
            "data": {
                "drivers_created": result.get("business_drivers_created", 0),
                "drivers_updated": result.get("business_drivers_updated", 0),
                "drivers_merged": result.get("business_drivers_merged", 0),
                "drivers_enriched": enriched_count,
                "signals_processed": result.get("signals_processed", 0),
                "message": f"Extracted {result.get('business_drivers_created', 0) + result.get('business_drivers_updated', 0) + result.get('business_drivers_merged', 0)} business drivers",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Business drivers extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Business drivers extraction failed: {str(e)}",
        }


async def _execute_enrich_business_driver(project_id: UUID, args: dict) -> dict:
    """
    Enrich a specific business driver with measurement/impact details.

    Calls the appropriate enrichment chain based on driver type (KPI/pain/goal).
    """
    try:
        driver_id = UUID(args.get("driver_id"))
        depth = args.get("depth", "standard")

        # Get driver to determine type
        from app.db.business_drivers import get_business_driver

        driver = get_business_driver(driver_id)
        if not driver:
            return {
                "success": False,
                "data": {},
                "error": f"Business driver {driver_id} not found",
            }

        driver_type = driver.get("driver_type")

        # Call appropriate enrichment chain
        if driver_type == "kpi":
            result = await enrich_kpi(driver_id, project_id, depth=depth)
        elif driver_type == "pain":
            result = await enrich_pain_point(driver_id, project_id, depth=depth)
        elif driver_type == "goal":
            result = await enrich_goal(driver_id, project_id, depth=depth)
        else:
            return {
                "success": False,
                "data": {},
                "error": f"Unknown driver type: {driver_type}",
            }

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "driver_id": str(driver_id),
                    "driver_type": driver_type,
                    "updated_fields": result.get("updated_fields", []),
                    "enrichment": result.get("enrichment", {}),
                    "message": f"Enriched {driver_type} driver with {len(result.get('updated_fields', []))} fields",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": result.get("error", "Enrichment failed"),
            }

    except Exception as e:
        logger.error(f"Business driver enrichment failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Business driver enrichment failed: {str(e)}",
        }


async def _execute_extract_competitors(project_id: UUID, args: dict) -> dict:
    """
    Extract and update competitor references from signals.

    Uses smart_upsert to merge evidence and update existing competitors.
    """
    try:
        include_research = args.get("include_research", False)
        signal_ids = args.get("signal_ids", None)

        # Use the run_strategic_foundation extraction
        from app.chains.run_strategic_foundation import extract_strategic_entities_from_signals

        result = extract_strategic_entities_from_signals(project_id)

        # Optionally run enrichment
        enriched_count = 0
        if include_research:
            competitors = list_competitor_refs(project_id, reference_type="competitor")
            for comp in competitors[:5]:  # Limit to top 5
                if comp.get("enrichment_status") == "none":
                    try:
                        comp_result = await enrich_competitor(
                            UUID(comp["id"]),
                            project_id,
                            depth="standard"
                        )
                        if comp_result.get("success"):
                            enriched_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to enrich competitor {comp['id']}: {e}")

        return {
            "success": True,
            "data": {
                "competitors_created": result.get("competitor_refs_created", 0),
                "competitors_updated": result.get("competitor_refs_updated", 0),
                "competitors_merged": result.get("competitor_refs_merged", 0),
                "competitors_enriched": enriched_count,
                "signals_processed": result.get("signals_processed", 0),
                "message": f"Extracted {result.get('competitor_refs_created', 0) + result.get('competitor_refs_updated', 0) + result.get('competitor_refs_merged', 0)} competitors",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Competitor extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Competitor extraction failed: {str(e)}",
        }


async def _execute_enrich_competitor(project_id: UUID, args: dict) -> dict:
    """
    Enrich a specific competitor with market analysis.
    """
    try:
        ref_id = UUID(args.get("ref_id"))
        depth = args.get("depth", "standard")
        include_web_scraping = args.get("include_web_scraping", False)

        # Note: Web scraping integration not implemented yet
        if include_web_scraping:
            logger.warning("Web scraping not yet implemented for competitor enrichment")

        result = await enrich_competitor(ref_id, project_id, depth=depth)

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "ref_id": str(ref_id),
                    "updated_fields": result.get("updated_fields", []),
                    "enrichment": result.get("enrichment", {}),
                    "message": f"Enriched competitor with {len(result.get('updated_fields', []))} fields",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": result.get("error", "Enrichment failed"),
            }

    except Exception as e:
        logger.error(f"Competitor enrichment failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Competitor enrichment failed: {str(e)}",
        }


async def _execute_extract_stakeholders(project_id: UUID, args: dict) -> dict:
    """
    Extract and update stakeholders from signals.

    Uses smart_upsert to merge evidence and update existing stakeholders.
    """
    try:
        link_to_personas = args.get("link_to_personas", True)
        signal_ids = args.get("signal_ids", None)

        # Extract stakeholders from signals (this logic can be enhanced)
        # For now, use the existing stakeholder extraction in run_strategic_foundation
        from app.chains.run_strategic_foundation import extract_strategic_entities_from_signals

        result = extract_strategic_entities_from_signals(project_id)

        # Optionally enrich stakeholders
        enriched_count = 0
        stakeholders = list_stakeholders(project_id)
        for stakeholder in stakeholders[:10]:  # Limit to top 10
            if stakeholder.get("enrichment_status") == "none":
                try:
                    enrich_result = await enrich_stakeholder(
                        UUID(stakeholder["id"]),
                        project_id,
                        depth="quick"
                    )
                    if enrich_result.get("success"):
                        enriched_count += 1
                except Exception as e:
                    logger.warning(f"Failed to enrich stakeholder {stakeholder['id']}: {e}")

        # Note: Link to personas logic not implemented yet
        if link_to_personas:
            logger.info("Persona linking logic to be implemented")

        return {
            "success": True,
            "data": {
                "stakeholders_count": len(stakeholders),
                "stakeholders_enriched": enriched_count,
                "message": f"Processed {len(stakeholders)} stakeholders, enriched {enriched_count}",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Stakeholder extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Stakeholder extraction failed: {str(e)}",
        }


async def _execute_extract_risks(project_id: UUID, args: dict) -> dict:
    """
    Extract and update project risks from signals.

    Uses smart_upsert to merge evidence and update existing risks.
    """
    try:
        risk_types = args.get("risk_types", None)  # None = all types
        signal_ids = args.get("signal_ids", None)
        limit = args.get("limit", 10)

        # Extract risks from signals
        if signal_ids:
            signal_id_list = [UUID(sid) for sid in signal_ids]
        else:
            signal_id_list = None

        result = await extract_risks_from_signals(
            project_id=project_id,
            signal_ids=signal_id_list,
            limit=limit
        )

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "risks_created": result.get("risks_created", 0),
                    "risks_updated": result.get("risks_updated", 0),
                    "risks_merged": result.get("risks_merged", 0),
                    "signals_processed": result.get("signals_processed", 0),
                    "total_risks": result.get("risks_created", 0) + result.get("risks_updated", 0) + result.get("risks_merged", 0),
                    "message": f"Extracted {result.get('risks_created', 0) + result.get('risks_updated', 0) + result.get('risks_merged', 0)} risks from {result.get('signals_processed', 0)} signals",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": result.get("error", "Risk extraction failed"),
            }

    except Exception as e:
        logger.error(f"Risk extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Risk extraction failed: {str(e)}",
        }


# ==========================================================================
# Helper Functions
# ==========================================================================


def _get_recommended_action(gate_name: str) -> str:
    """Get recommended action for an unsatisfied gate."""
    actions = {
        "core_pain": "Run extract_core_pain to identify THE singular pain",
        "primary_persona": "Run extract_primary_persona to identify who feels pain most",
        "wow_moment": "Run identify_wow_moment to define pain→delight inversion",
        "design_preferences": "Gather design preferences through discovery questions",
        "business_case": "Run extract_business_case to articulate business value",
        "budget_constraints": "Run extract_budget_constraints to understand budget/timeline",
        "full_requirements": "Run run_foundation to extract complete requirements, then analyze_requirements_gaps to check for logical gaps",
    }
    return actions.get(gate_name, "Gather more information through discovery questions")


# ==========================================================================
# Requirements Gap Analysis Tools
# ==========================================================================


async def _execute_analyze_requirements_gaps(project_id: UUID, args: dict) -> dict:
    """
    Analyze requirements for logical gaps and inconsistencies.

    Checks for missing feature references, orphaned entities, incomplete
    definitions, and VP flow continuity issues.
    """
    try:
        focus_areas = args.get("focus_areas", None)

        result = await analyze_requirements_gaps(
            project_id=project_id,
            focus_areas=focus_areas,
        )

        if result.get("success"):
            gaps = result.get("gaps", [])
            summary = result.get("summary", {})

            return {
                "success": True,
                "data": {
                    "gaps": gaps,
                    "total_gaps": summary.get("total_gaps", len(gaps)),
                    "high_severity": summary.get("high_severity", 0),
                    "medium_severity": summary.get("medium_severity", 0),
                    "low_severity": summary.get("low_severity", 0),
                    "overall_completeness": summary.get("overall_completeness", "unknown"),
                    "most_critical_area": summary.get("most_critical_area", "unknown"),
                    "recommendations": result.get("recommendations", []),
                    "entities_analyzed": result.get("entities_analyzed", {}),
                    "message": f"Found {len(gaps)} requirement gaps ({summary.get('high_severity', 0)} high severity)",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": result.get("error", "Gap analysis failed"),
            }

    except Exception as e:
        logger.error(f"Requirements gap analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Requirements gap analysis failed: {str(e)}",
        }


async def _execute_propose_entity_updates(project_id: UUID, args: dict) -> dict:
    """
    Generate proposals to fill identified requirement gaps.

    Creates proposals for features, personas, or VP steps based on
    the gap analysis results.
    """
    try:
        gap_analysis = args.get("gap_analysis")
        if not gap_analysis:
            return {
                "success": False,
                "data": {},
                "error": "gap_analysis is required - run analyze_requirements_gaps first",
            }

        max_proposals = args.get("max_proposals", 5)
        entity_types = args.get("entity_types", None)
        auto_create = args.get("auto_create_proposals", True)

        # Get project stage from readiness if available
        project_stage = "requirements"  # Default
        try:
            readiness = compute_readiness(project_id)
            project_stage = readiness.phase
        except Exception:
            pass

        result = await propose_entity_updates(
            project_id=project_id,
            gap_analysis=gap_analysis,
            max_proposals=max_proposals,
            entity_types=entity_types,
            project_stage=project_stage,
            auto_create_proposals=auto_create,
        )

        if result.get("success"):
            proposals = result.get("proposals", [])
            proposals_created = result.get("proposals_created", [])
            summary = result.get("summary", {})

            return {
                "success": True,
                "data": {
                    "proposals": proposals,
                    "proposals_generated": len(proposals),
                    "proposals_created_in_db": len(proposals_created),
                    "proposal_ids": [p.get("id") for p in proposals_created if p],
                    "creates": summary.get("creates", 0),
                    "updates": summary.get("updates", 0),
                    "by_entity_type": summary.get("by_entity_type", {}),
                    "gaps_addressed": summary.get("gaps_addressed", 0),
                    "message": f"Generated {len(proposals)} proposals ({len(proposals_created)} created for review)",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": result.get("error", "Proposal generation failed"),
            }

    except Exception as e:
        logger.error(f"Proposal generation failed: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Proposal generation failed: {str(e)}",
        }


# ==========================================================================
# Memory Tools - Persistent Project Memory
# ==========================================================================


async def _execute_read_project_memory(project_id: UUID, args: dict) -> dict:
    """
    Read the project memory document.
    """
    try:
        memory = get_or_create_project_memory(project_id)
        content = get_memory_for_context(project_id, max_tokens=3000)

        return {
            "success": True,
            "data": {
                "content": content,
                "version": memory.get("version", 1),
                "last_updated": memory.get("updated_at"),
                "updated_by": memory.get("last_updated_by"),
                "tokens_estimate": memory.get("tokens_estimate", 0),
                "message": f"Project memory loaded (v{memory.get('version', 1)})",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to read project memory: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to read project memory: {str(e)}",
        }


async def _execute_update_project_understanding(project_id: UUID, args: dict) -> dict:
    """
    Update the project understanding section of memory.
    """
    try:
        understanding = args.get("understanding", "")
        client_profile_updates = args.get("client_profile_updates", {})

        # Get existing memory to merge client profile
        memory = get_or_create_project_memory(project_id)
        existing_profile = memory.get("client_profile", {}) or {}

        # Merge profile updates
        updated_profile = {**existing_profile, **client_profile_updates}

        result = update_project_memory(
            project_id=project_id,
            project_understanding=understanding,
            client_profile=updated_profile if client_profile_updates else None,
            updated_by="di_agent",
        )

        return {
            "success": True,
            "data": {
                "version": result.get("version", 1),
                "understanding_updated": bool(understanding),
                "profile_fields_updated": list(client_profile_updates.keys()) if client_profile_updates else [],
                "message": "Project understanding updated",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to update project understanding: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to update project understanding: {str(e)}",
        }


async def _execute_log_decision(project_id: UUID, args: dict) -> dict:
    """
    Log a decision with full rationale.
    """
    try:
        title = args.get("title", "Untitled Decision")
        decision = args.get("decision", "")
        rationale = args.get("rationale", "")
        alternatives = args.get("alternatives_considered", [])
        decided_by = args.get("decided_by", "di_agent")
        decision_type = args.get("decision_type", "feature")

        result = add_decision(
            project_id=project_id,
            title=title,
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives,
            decided_by=decided_by,
            decision_type=decision_type,
        )

        return {
            "success": True,
            "data": {
                "decision_id": result.get("id"),
                "title": title,
                "decision_type": decision_type,
                "message": f"Decision logged: {title}",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to log decision: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to log decision: {str(e)}",
        }


async def _execute_record_learning(project_id: UUID, args: dict) -> dict:
    """
    Record a learning in project memory.
    """
    try:
        title = args.get("title", "Untitled Learning")
        context = args.get("context", "")
        learning = args.get("learning", "")
        learning_type = args.get("learning_type", "insight")
        domain = args.get("domain")

        result = add_learning(
            project_id=project_id,
            title=title,
            context=context,
            learning=learning,
            learning_type=learning_type,
            domain=domain,
        )

        emoji = {"insight": "💡", "mistake": "⚠️", "pattern": "🔄", "terminology": "📝"}.get(learning_type, "📌")

        return {
            "success": True,
            "data": {
                "learning_id": result.get("id"),
                "title": title,
                "learning_type": learning_type,
                "message": f"{emoji} Learning recorded: {title}",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to record learning: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to record learning: {str(e)}",
        }


async def _execute_update_strategy(project_id: UUID, args: dict) -> dict:
    """
    Update the current strategy and hypotheses.
    """
    try:
        focus = args.get("focus", "")
        hypotheses = args.get("hypotheses", [])
        next_actions = args.get("next_actions", [])

        strategy = {
            "focus": focus,
            "hypotheses": hypotheses,
            "next_actions": next_actions,
        }

        result = update_project_memory(
            project_id=project_id,
            current_strategy=strategy,
            updated_by="di_agent",
        )

        return {
            "success": True,
            "data": {
                "focus": focus,
                "hypotheses_count": len(hypotheses),
                "next_actions_count": len(next_actions),
                "message": f"Strategy updated: {focus[:50]}...",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to update strategy: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to update strategy: {str(e)}",
        }


async def _execute_add_open_question(project_id: UUID, args: dict) -> dict:
    """
    Add an open question to project memory.
    """
    try:
        question = args.get("question", "")
        why_important = args.get("why_important", "")
        affects_gate = args.get("affects_gate")

        # Get existing questions
        memory = get_or_create_project_memory(project_id)
        existing_questions = memory.get("open_questions", []) or []

        # Add new question
        new_question = {
            "question": question,
            "why_important": why_important,
            "affects_gate": affects_gate,
            "resolved": False,
            "added_at": str(datetime.utcnow()),
        }
        existing_questions.append(new_question)

        from datetime import datetime

        result = update_project_memory(
            project_id=project_id,
            open_questions=existing_questions,
            updated_by="di_agent",
        )

        return {
            "success": True,
            "data": {
                "question": question,
                "total_open_questions": len(existing_questions),
                "message": f"Open question added: {question[:50]}...",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to add open question: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to add open question: {str(e)}",
        }


async def _execute_synthesize_value_path(project_id: UUID, args: dict) -> dict:
    """
    Synthesize the optimal value path for the Canvas View prototype.
    """
    try:
        from app.chains.synthesize_value_path import synthesize_value_path

        result = await synthesize_value_path(project_id)

        return {
            "success": True,
            "data": {
                "step_count": result.get("step_count", 0),
                "version": result.get("version", 1),
                "synthesis_rationale": result.get("synthesis_rationale", ""),
                "message": f"Value path synthesized with {result.get('step_count', 0)} steps (v{result.get('version', 1)})",
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to synthesize value path: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "error": f"Failed to synthesize value path: {str(e)}",
        }
