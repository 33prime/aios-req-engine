"""Tool execution layer for DI Agent.

Maps DI Agent tool calls to actual backend operations. Each tool returns
a consistent dict format with "success" flag and "data".
"""

import json
from uuid import UUID

from anthropic import Anthropic
from openai import OpenAI

from app.chains.extract_budget_constraints import extract_budget_constraints
from app.chains.extract_business_case import extract_business_case
from app.chains.extract_core_pain import extract_core_pain
from app.chains.extract_primary_persona import extract_primary_persona
from app.chains.identify_wow_moment import identify_wow_moment
from app.chains.run_strategic_foundation import run_strategic_foundation
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.readiness.score import compute_readiness
from app.db.foundation import get_foundation_element
from app.db.signals import list_project_signals
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
    try:
        result = await run_strategic_foundation(project_id)

        return {
            "success": True,
            "data": {
                "features_count": result.get("features_count", 0),
                "personas_count": result.get("personas_count", 0),
                "vp_steps_count": result.get("vp_steps_count", 0),
                "prd_sections_count": result.get("prd_sections_count", 0),
                "stakeholders_count": result.get("stakeholders_count", 0),
                "message": "Strategic foundation extracted successfully",
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
        "full_requirements": "Run run_foundation to extract complete requirements",
    }
    return actions.get(gate_name, "Gather more information through discovery questions")
