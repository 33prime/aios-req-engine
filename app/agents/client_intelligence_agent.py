"""Client Intelligence Agent - Core reasoning engine.

Builds and maintains deep understanding of client organizations.
Operates at CLIENT level (across projects), not project level.

Follows OBSERVE → THINK → DECIDE → ACT pattern.
"""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from anthropic import Anthropic

from app.agents.client_intelligence_prompts import CI_AGENT_SYSTEM_PROMPT, CI_AGENT_TOOLS
from app.agents.client_intelligence_types import (
    CIGuidance,
    CIToolCall,
    ClientIntelligenceResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.clients import get_client, get_client_projects

logger = get_logger(__name__)


async def invoke_client_intelligence_agent(
    client_id: UUID,
    trigger: Literal[
        "new_client", "stakeholder_added", "project_milestone",
        "user_request", "scheduled", "enrichment_complete", "signal_confirmed",
    ],
    trigger_context: str | None = None,
    specific_request: str | None = None,
    focus_sections: list[str] | None = None,
) -> ClientIntelligenceResponse:
    """
    Invoke the Client Intelligence Agent.

    Args:
        client_id: Client UUID
        trigger: What triggered this invocation
        trigger_context: Additional context about the trigger
        specific_request: Specific user request
        focus_sections: Specific sections to focus on

    Returns:
        ClientIntelligenceResponse with reasoning trace and actions
    """
    settings = get_settings()
    start_time = datetime.utcnow()

    logger.info(
        f"Invoking CI Agent for client {client_id}, trigger={trigger}",
        extra={"client_id": str(client_id), "trigger": trigger},
    )

    try:
        # ==================================================================
        # 1. OBSERVE - Load client state
        # ==================================================================

        client = get_client(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        projects = get_client_projects(client_id)

        # Compute current completeness
        from app.agents.client_intelligence_tools import _execute_update_profile_completeness
        completeness_result = await _execute_update_profile_completeness(client_id)
        completeness = completeness_result.get("data", {})

        # Build client context summary
        client_context = _build_client_context(client, projects, completeness)

        # ==================================================================
        # 2. Build reasoning prompt
        # ==================================================================

        trigger_text = _format_trigger(trigger, trigger_context, specific_request)
        focus_text = ""
        if focus_sections:
            focus_text = f"\n\n**Focus sections:** {', '.join(focus_sections)}\nPrioritize these sections in your analysis."

        user_prompt = f"""# CLIENT STATE

## Profile Overview
- **Name:** {client.get('name', 'Unknown')}
- **Industry:** {client.get('industry', 'Not set')}
- **Size:** {client.get('size', 'Not set')}
- **Website:** {client.get('website', 'Not set')}
- **Enrichment:** {client.get('enrichment_status', 'pending')}
- **Profile Completeness:** {completeness.get('score', 0)}/100 ({completeness.get('label', 'Unknown')})

## Section Scores
{_format_sections(completeness.get('sections', {}))}

## Projects
{_format_projects(projects)}

## Client Context
{client_context}

---

# YOUR TASK

{trigger_text}
{focus_text}

Follow OBSERVE → THINK → DECIDE → ACT:

1. **OBSERVE:** Review client profile completeness and section scores above
2. **THINK:** Which section has the biggest gap? What's the highest-leverage action?
3. **DECIDE:** Choose ONE tool to call (prefer enriching the thinnest section)
4. **ACT:** Execute your decision

The client_id for all tools is: {str(client_id)}

Remember:
- Enrich the THINNEST section first (lowest score relative to max)
- If firmographics are empty, start there — everything else depends on knowing the company
- If no stakeholders exist, flag that immediately
- Cross-reference across projects for patterns

What's your reasoning and recommended action?"""

        # ==================================================================
        # 3. Call LLM
        # ==================================================================

        anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        anthropic_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in CI_AGENT_TOOLS
        ]

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=CI_AGENT_SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # ==================================================================
        # 4. Parse response
        # ==================================================================

        agent_response = _parse_response(
            response,
            profile_completeness_before=completeness.get("score", 0),
        )

        # ==================================================================
        # 5. Execute tools
        # ==================================================================

        if agent_response.action_type == "tool_call" and agent_response.tools_called:
            from app.agents.client_intelligence_tools import execute_ci_tool

            for tool_call in agent_response.tools_called:
                try:
                    result = await execute_ci_tool(
                        tool_name=tool_call.tool_name,
                        tool_args=tool_call.tool_args,
                        client_id=client_id,
                    )
                    tool_call.result = result.get("data")
                    tool_call.success = result.get("success", False)
                    tool_call.error = result.get("error")

                    logger.info(
                        f"CI Tool {tool_call.tool_name}: {'OK' if tool_call.success else 'FAIL'}",
                        extra={"client_id": str(client_id), "tool": tool_call.tool_name},
                    )
                except Exception as e:
                    logger.error(f"CI tool {tool_call.tool_name} error: {e}")
                    tool_call.success = False
                    tool_call.error = str(e)

            # Recompute completeness after tools
            updated = await _execute_update_profile_completeness(client_id)
            agent_response.profile_completeness_after = updated.get("data", {}).get("score")

            # Track which sections were affected
            affected = set()
            for tc in agent_response.tools_called:
                affected.update(_tool_to_sections(tc.tool_name))
            agent_response.sections_affected = list(affected)

        # ==================================================================
        # 6. Log invocation
        # ==================================================================

        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        try:
            _log_invocation(
                client_id=client_id,
                trigger=trigger,
                agent_response=agent_response,
                trigger_context=trigger_context or specific_request,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to log CI agent invocation: {e}")

        logger.info(
            f"CI Agent completed: action={agent_response.action_type}, "
            f"completeness={agent_response.profile_completeness_before}→{agent_response.profile_completeness_after}",
            extra={"client_id": str(client_id)},
        )

        return agent_response

    except Exception as e:
        logger.error(f"CI Agent error for client {client_id}: {e}", exc_info=True)
        raise


# =============================================================================
# Helpers
# =============================================================================


def _build_client_context(client: dict, projects: list[dict], completeness: dict) -> str:
    """Build a context summary of the client for the agent prompt."""
    parts = []

    if client.get("company_summary"):
        parts.append(f"**Company Summary:** {client['company_summary'][:300]}")
    if client.get("market_position"):
        parts.append(f"**Market Position:** {client['market_position'][:200]}")
    if client.get("technology_maturity"):
        parts.append(f"**Tech Maturity:** {client['technology_maturity']}")
    if client.get("digital_readiness"):
        parts.append(f"**Digital Readiness:** {client['digital_readiness']}")
    if client.get("vision_synthesis"):
        parts.append(f"**Synthesized Vision:** {client['vision_synthesis'][:200]}")

    # Constraint summary
    constraints = client.get("constraint_summary") or []
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints)
        except (json.JSONDecodeError, TypeError):
            constraints = []
    if constraints:
        parts.append(f"**Known Constraints:** {len(constraints)} identified")

    # Role gaps
    role_gaps = client.get("role_gaps") or []
    if isinstance(role_gaps, str):
        try:
            role_gaps = json.loads(role_gaps)
        except (json.JSONDecodeError, TypeError):
            role_gaps = []
    if role_gaps:
        gap_names = [g.get("role", "?") for g in role_gaps if isinstance(g, dict)]
        parts.append(f"**Role Gaps:** {', '.join(gap_names[:5])}")

    if not parts:
        return "No client intelligence gathered yet."

    return "\n".join(parts)


def _format_trigger(trigger: str, context: str | None, specific: str | None) -> str:
    """Format trigger information."""
    trigger_map = {
        "new_client": "A new client was created. Build initial profile.",
        "stakeholder_added": "A new stakeholder was added. Update stakeholder map.",
        "project_milestone": "A project reached a milestone. Update portfolio health.",
        "user_request": f"Consultant request: {specific or 'Analyze this client'}",
        "scheduled": "Scheduled periodic profile update.",
        "enrichment_complete": "Firmographic enrichment completed. Assess what's next.",
        "signal_confirmed": "Signal data was confirmed. Update constraints and vision.",
    }
    base = trigger_map.get(trigger, f"Trigger: {trigger}")
    if context:
        base += f"\n\nContext: {context}"
    return base


def _format_sections(sections: dict) -> str:
    """Format section scores as a readable summary."""
    if not sections:
        return "No section scores computed yet."

    max_scores = {
        "firmographics": 15, "stakeholder_map": 20, "organizational_context": 15,
        "constraints": 15, "vision_strategy": 10, "data_landscape": 10,
        "competitive_context": 10, "portfolio_health": 5,
    }

    lines = []
    for section, score in sorted(sections.items(), key=lambda x: x[1]):
        max_s = max_scores.get(section, 10)
        bar_len = int((score / max_s) * 10) if max_s > 0 else 0
        bar = "█" * bar_len + "░" * (10 - bar_len)
        lines.append(f"- {bar} {score}/{max_s} — {section.replace('_', ' ').title()}")

    return "\n".join(lines)


def _format_projects(projects: list[dict]) -> str:
    """Format project list."""
    if not projects:
        return "No projects linked to this client."

    lines = []
    for p in projects[:10]:
        lines.append(f"- **{p.get('name', '?')}** ({p.get('stage', '?')}) — updated {str(p.get('updated_at', ''))[:10]}")
    return "\n".join(lines)


def _parse_response(
    llm_response,
    profile_completeness_before: int,
) -> ClientIntelligenceResponse:
    """Parse LLM response into ClientIntelligenceResponse."""
    text_content = ""
    tool_calls = []

    for block in llm_response.content:
        if hasattr(block, "text"):
            text_content += block.text + "\n"
        elif block.type == "tool_use":
            tool_calls.append({
                "tool_name": block.name,
                "tool_args": block.input,
            })

    observation, thinking, decision = _extract_reasoning(text_content)

    if tool_calls:
        # Check for stop_with_guidance
        stop_tools = [tc for tc in tool_calls if tc["tool_name"] == "stop_with_guidance"]
        if stop_tools:
            args = stop_tools[0]["tool_args"]
            return ClientIntelligenceResponse(
                observation=observation,
                thinking=thinking,
                decision=decision,
                action_type="stop",
                stop_reason=args.get("reason"),
                guidance=CIGuidance(
                    summary=args.get("reason", ""),
                    missing_info=args.get("missing_info", []),
                    suggested_actions=args.get("suggested_actions", []),
                    next_session_topics=args.get("next_session_topics", []),
                ),
                recommended_next="Gather the missing information in the next client session",
                profile_completeness_before=profile_completeness_before,
            )

        # Regular tool calls
        return ClientIntelligenceResponse(
            observation=observation,
            thinking=thinking,
            decision=decision,
            action_type="tool_call",
            tools_called=[CIToolCall(**tc) for tc in tool_calls],
            recommended_next="Review the analysis results and confirm insights",
            profile_completeness_before=profile_completeness_before,
        )

    # No tool calls
    return ClientIntelligenceResponse(
        observation=observation,
        thinking=thinking,
        decision=decision,
        action_type="guidance",
        guidance=CIGuidance(
            summary=thinking[:300] if thinking else "Analysis complete",
            missing_info=[],
            suggested_actions=[],
            next_session_topics=[],
        ),
        recommended_next=text_content[-300:] if text_content else "Review analysis",
        profile_completeness_before=profile_completeness_before,
    )


def _extract_reasoning(text: str) -> tuple[str, str, str]:
    """Extract OBSERVE, THINK, DECIDE sections."""
    text_lower = text.lower()
    observation = thinking = decision = ""

    for label, attr in [("observe", "observation"), ("think", "thinking"), ("decide", "decision")]:
        if label in text_lower:
            start = text_lower.find(label)
            if start >= 0:
                next_markers = [
                    text_lower.find(m, start + len(label))
                    for m in ["think", "decide", "act", "##"]
                    if text_lower.find(m, start + len(label)) > start
                ]
                end = min(next_markers) if next_markers else min(start + 500, len(text))
                chunk = text[start:end].strip()
                if attr == "observation":
                    observation = chunk
                elif attr == "thinking":
                    thinking = chunk
                else:
                    decision = chunk

    if not observation and not thinking and not decision:
        parts = text.split("\n\n")
        if len(parts) >= 3:
            observation, thinking, decision = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            observation, thinking = parts[0], parts[1]
            decision = "Proceeding"
        else:
            observation = text[:300]
            thinking = text[:500]
            decision = text[:200]

    return observation, thinking, decision


def _generate_action_summary(tools_called: list) -> str:
    """Generate a one-line human-readable summary from tool results."""
    if not tools_called:
        return ""

    parts = []
    for tc in tools_called:
        tool_name = tc.tool_name
        result = tc.result or {}

        if tool_name == "enrich_firmographics":
            fields = result.get("fields_enriched", [])
            parts.append(f"Enriched {len(fields)} fields" if fields else "Enriched firmographics")
        elif tool_name == "analyze_stakeholder_map":
            count = result.get("stakeholder_count")
            parts.append(f"Mapped {count} stakeholders" if count else "Analyzed stakeholders")
        elif tool_name == "identify_role_gaps":
            missing = result.get("missing_roles", [])
            parts.append(f"Found {len(missing)} role gaps" if missing else "Assessed roles")
        elif tool_name == "synthesize_constraints":
            constraints = result.get("constraints", [])
            parts.append(f"Identified {len(constraints)} constraints" if constraints else "Synthesized constraints")
        elif tool_name == "synthesize_vision":
            clarity = result.get("clarity_score")
            parts.append(f"Vision synthesized ({int(clarity * 100)}% clarity)" if clarity else "Synthesized vision")
        elif tool_name == "assess_organizational_context":
            style = result.get("decision_making_style", "")
            parts.append(f"Assessed org context ({style.replace('_', ' ')})" if style else "Assessed org context")
        elif tool_name == "assess_portfolio_health":
            count = result.get("project_count")
            parts.append(f"Portfolio health ({count} projects)" if count else "Assessed portfolio")
        elif tool_name == "update_profile_completeness":
            score = result.get("score")
            parts.append(f"Score: {score}/100" if score else "Updated completeness")
        elif tool_name == "extract_knowledge_base":
            parts.append("Extracted knowledge base")
        elif tool_name == "generate_process_document":
            title = result.get("title", "")
            steps = result.get("step_count", 0)
            parts.append(f"Generated process doc '{title}' ({steps} steps)" if title else "Generated process doc")
        else:
            parts.append(tool_name.replace("_", " "))

    return "; ".join(parts)


def _tool_to_sections(tool_name: str) -> list[str]:
    """Map tool name to affected profile sections."""
    mapping = {
        "enrich_firmographics": ["firmographics"],
        "analyze_stakeholder_map": ["stakeholder_map"],
        "identify_role_gaps": ["stakeholder_map"],
        "synthesize_constraints": ["constraints"],
        "synthesize_vision": ["vision_strategy"],
        "analyze_data_landscape": ["data_landscape"],
        "assess_organizational_context": ["organizational_context"],
        "assess_portfolio_health": ["portfolio_health"],
        "update_profile_completeness": [],
        "generate_process_document": ["organizational_context"],
    }
    return mapping.get(tool_name, [])


def _log_invocation(
    client_id: UUID,
    trigger: str,
    agent_response: ClientIntelligenceResponse,
    trigger_context: str | None,
    execution_time_ms: int,
) -> None:
    """Log agent invocation to client_intelligence_logs table."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    action_summary = _generate_action_summary(agent_response.tools_called or [])

    log_data = {
        "client_id": str(client_id),
        "trigger": trigger,
        "trigger_context": trigger_context,
        "observation": agent_response.observation[:2000],
        "thinking": agent_response.thinking[:2000],
        "decision": agent_response.decision[:1000],
        "action_type": agent_response.action_type,
        "tools_called": [tc.model_dump() for tc in (agent_response.tools_called or [])],
        "guidance": agent_response.guidance.model_dump() if agent_response.guidance else None,
        "action_summary": action_summary or None,
        "profile_completeness_before": agent_response.profile_completeness_before,
        "profile_completeness_after": agent_response.profile_completeness_after,
        "sections_affected": agent_response.sections_affected,
        "stop_reason": agent_response.stop_reason,
        "execution_time_ms": execution_time_ms,
        "llm_model": "claude-sonnet-4-20250514",
        "success": True,
    }

    supabase.table("client_intelligence_logs").insert(log_data).execute()
