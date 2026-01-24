"""Design Intelligence Agent - Core reasoning engine.

This module implements the DI Agent that drives toward project readiness
by identifying gaps in foundation and taking action to fill them.

The agent follows OBSERVE → THINK → DECIDE → ACT pattern.
"""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from anthropic import Anthropic

from app.agents.di_agent_prompts import DI_AGENT_SYSTEM_PROMPT, DI_AGENT_TOOLS
from app.agents.di_agent_types import ConsultantGuidance, DIAgentResponse, QuestionToAsk
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import timer, track_performance
from app.core.readiness.score import compute_readiness
from app.core.state_snapshot import get_state_snapshot
from app.db.di_cache import get_di_cache, is_cache_valid, get_unanalyzed_signals
from app.db.di_logs import log_agent_invocation

logger = get_logger(__name__)


async def invoke_di_agent(
    project_id: UUID,
    trigger: Literal["new_signal", "user_request", "scheduled", "pre_call"],
    trigger_context: str | None = None,
    specific_request: str | None = None,
) -> DIAgentResponse:
    """
    Invoke the Design Intelligence Agent.

    The agent follows OBSERVE → THINK → DECIDE → ACT pattern to identify
    the biggest gap in project foundation and take action to fill it.

    Args:
        project_id: Project UUID
        trigger: What triggered this invocation
        trigger_context: Additional context about the trigger
        specific_request: Specific user request (if trigger = user_request)

    Returns:
        DIAgentResponse with complete reasoning trace

    Raises:
        Exception: If agent invocation fails
    """
    settings = get_settings()
    start_time = datetime.utcnow()

    logger.info(
        f"Invoking DI Agent for project {project_id}, trigger={trigger}",
        extra={"project_id": str(project_id), "trigger": trigger},
    )

    try:
        # ======================================================================
        # 1. OBSERVE - Load current state (optimized to avoid redundant DB calls)
        # ======================================================================

        with timer("DI Agent - Fetch state snapshot", str(project_id)):
            state_snapshot = get_state_snapshot(project_id)

        with timer("DI Agent - Compute readiness", str(project_id)):
            readiness = compute_readiness(project_id)

        with timer("DI Agent - Check cache", str(project_id)):
            # Get DI cache once
            di_cache = get_di_cache(project_id)

            # Get unanalyzed signals (passing cache to avoid refetch)
            unanalyzed = get_unanalyzed_signals(project_id, cache=di_cache)

            # Check cache validity (passing both cache and unanalyzed to avoid refetches)
            cache_valid = is_cache_valid(project_id, cache=di_cache, unanalyzed_signals=unanalyzed) if di_cache else False

        logger.info(
            f"Agent observed state: score={readiness.score}, phase={readiness.phase}, "
            f"cache_valid={cache_valid}, unanalyzed_signals={len(unanalyzed)}",
            extra={
                "project_id": str(project_id),
                "score": readiness.score,
                "phase": readiness.phase,
            },
        )

        # ======================================================================
        # 2. Build reasoning prompt
        # ======================================================================

        # Format gates for prompt
        gates_summary = _format_gates_summary(readiness.gates)

        # Format cache status
        cache_summary = _format_cache_summary(di_cache, cache_valid)

        # Build trigger context
        trigger_text = _format_trigger(trigger, trigger_context, specific_request)

        # Build user prompt
        user_prompt = f"""# CURRENT STATE

## Readiness Assessment
- **Score:** {readiness.score}/100
- **Phase:** {readiness.phase}
- **Prototype Ready:** {"Yes" if readiness.prototype_ready else "No"}
- **Build Ready:** {"Yes" if readiness.build_ready else "No"}
- **Next Milestone:** {readiness.next_milestone}

## Gates Status
{gates_summary}

## Blocking Gates
{', '.join(readiness.blocking_gates) if readiness.blocking_gates else 'None'}

## Signals
- **Unanalyzed signals:** {len(unanalyzed)}
- **Total client signals:** {readiness.client_signals_count}

## DI Cache
{cache_summary}

## Project Context
{state_snapshot[:3000]}

---

# YOUR TASK

{trigger_text}

Follow the OBSERVE → THINK → DECIDE → ACT pattern:

1. **OBSERVE:** Review the current state above
2. **THINK:** Analyze the biggest gap blocking progress toward next milestone ({readiness.next_milestone})
3. **DECIDE:** Choose ONE action (tool call, guidance, or stop)
4. **ACT:** Execute your decision

Remember:
- Focus on the highest-leverage gap
- Prototype gates (core_pain, primary_persona, wow_moment) come before build gates
- Be honest about confidence - it's okay to suggest questions if signal is sparse
- Drive toward {readiness.next_milestone}

What's your reasoning and recommended action?"""

        # ======================================================================
        # 3. Call LLM with tool calling
        # ======================================================================

        # Initialize Anthropic client
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Convert tool definitions to Anthropic format
        anthropic_tools = _convert_tools_to_anthropic_format(DI_AGENT_TOOLS)

        # Call Claude
        response = client.messages.create(
            model=settings.DI_AGENT_MODEL or "claude-sonnet-4-20250514",
            max_tokens=4096,
            system=DI_AGENT_SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=[{"role": "user", "content": user_prompt}],
        )

        logger.debug(f"LLM response stop_reason: {response.stop_reason}")

        # ======================================================================
        # 4. Parse response
        # ======================================================================

        agent_response = _parse_agent_response(
            response,
            readiness_before=int(readiness.score),
            readiness_after=None,  # Will update if gates change
            gates_affected=[],  # Will populate based on tool calls
        )

        # ======================================================================
        # 5. Log reasoning
        # ======================================================================

        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        try:
            log_agent_invocation(
                project_id=project_id,
                trigger=trigger,
                observation=agent_response.observation,
                thinking=agent_response.thinking,
                decision=agent_response.decision,
                action_type=agent_response.action_type,
                trigger_context=trigger_context or specific_request,
                tools_called=[tc.model_dump() for tc in (agent_response.tools_called or [])],
                guidance_provided=agent_response.guidance.model_dump() if agent_response.guidance else None,
                stop_reason=agent_response.stop_reason,
                readiness_before=agent_response.readiness_before,
                readiness_after=agent_response.readiness_after,
                gates_affected=agent_response.gates_affected,
                execution_time_ms=execution_time_ms,
                llm_model=settings.DI_AGENT_MODEL or "claude-sonnet-4-20250514",
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to log agent invocation: {e}")
            # Don't fail the whole invocation if logging fails

        logger.info(
            f"DI Agent completed: action={agent_response.action_type}, "
            f"recommended={agent_response.recommended_next[:100]}",
            extra={
                "project_id": str(project_id),
                "action_type": agent_response.action_type,
            },
        )

        return agent_response

    except Exception as e:
        logger.error(
            f"Error invoking DI Agent for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )

        # Try to log the failure
        try:
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_agent_invocation(
                project_id=project_id,
                trigger=trigger,
                observation="Error occurred before observation",
                thinking="Error occurred before thinking",
                decision="Error occurred",
                action_type="stop",
                trigger_context=trigger_context,
                stop_reason=f"Error: {str(e)}",
                execution_time_ms=execution_time_ms,
                llm_model=settings.DI_AGENT_MODEL or "claude-sonnet-4-20250514",
                success=False,
                error_message=str(e),
            )
        except Exception:
            pass  # If logging fails, just continue

        raise


# =============================================================================
# Helper Functions
# =============================================================================


def _format_gates_summary(gates: dict) -> str:
    """Format gates dictionary into readable summary."""
    if not gates:
        return "No gate information available"

    lines = []

    # Prototype gates
    lines.append("### Prototype Gates (Phase 1)")
    prototype_gates = gates.get("prototype_gates", {})
    for gate_name, gate_data in prototype_gates.items():
        status = "✓" if gate_data.get("satisfied") else "✗"
        conf = gate_data.get("confidence", 0)
        lines.append(f"- {status} **{gate_data.get('name', gate_name)}** (confidence: {conf:.2f})")
        if not gate_data.get("satisfied") and gate_data.get("missing"):
            lines.append(f"  Missing: {', '.join(gate_data['missing'][:2])}")

    # Build gates
    lines.append("\n### Build Gates (Phase 2)")
    build_gates = gates.get("build_gates", {})
    for gate_name, gate_data in build_gates.items():
        status = "✓" if gate_data.get("satisfied") else "✗"
        conf = gate_data.get("confidence", 0)
        lines.append(f"- {status} **{gate_data.get('name', gate_name)}** (confidence: {conf:.2f})")
        if not gate_data.get("satisfied") and gate_data.get("missing"):
            lines.append(f"  Missing: {', '.join(gate_data['missing'][:2])}")

    return "\n".join(lines)


def _format_cache_summary(cache: dict | None, is_valid: bool) -> str:
    """Format DI cache status."""
    if not cache:
        return "No DI cache exists yet"

    if not is_valid:
        reason = cache.get("invalidation_reason", "unknown")
        return f"Cache INVALID (reason: {reason})"

    analyzed = len(cache.get("signals_analyzed", []))
    last_analysis = cache.get("last_full_analysis_at", "never")
    return f"Cache VALID ({analyzed} signals analyzed, last: {last_analysis[:10]})"


def _format_trigger(
    trigger: str,
    trigger_context: str | None,
    specific_request: str | None,
) -> str:
    """Format trigger information."""
    trigger_map = {
        "new_signal": "A new signal was added to the project.",
        "user_request": f"User request: {specific_request or 'No specific request provided'}",
        "scheduled": "Scheduled periodic check.",
        "pre_call": "Pre-call preparation - help consultant prepare for client conversation.",
    }

    base = trigger_map.get(trigger, f"Trigger: {trigger}")

    if trigger_context:
        base += f"\n\nContext: {trigger_context}"

    return base


def _convert_tools_to_anthropic_format(tools: list[dict]) -> list[dict]:
    """Convert DI tool definitions to Anthropic tool format.

    Anthropic format:
    {
        "name": "tool_name",
        "description": "Description",
        "input_schema": {...}
    }
    """
    anthropic_tools = []

    for tool in tools:
        anthropic_tool = {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        anthropic_tools.append(anthropic_tool)

    return anthropic_tools


def _parse_agent_response(
    llm_response,
    readiness_before: int,
    readiness_after: int | None,
    gates_affected: list[str],
) -> DIAgentResponse:
    """Parse LLM response into DIAgentResponse.

    The LLM response contains:
    - Text blocks with reasoning (observation, thinking, decision)
    - Tool use blocks (if action is tool_call)

    We extract:
    - Reasoning trace from text
    - Tool calls from tool_use blocks
    - Action type based on what the LLM did
    """
    # Extract text and tool calls from response
    text_content = ""
    tool_calls = []

    for block in llm_response.content:
        if hasattr(block, "text"):
            text_content += block.text + "\n"
        elif block.type == "tool_use":
            tool_calls.append({
                "tool_name": block.name,
                "tool_args": block.input,
                "result": None,  # Not executed yet
                "success": True,
            })

    # Parse reasoning from text
    # Look for OBSERVE/THINK/DECIDE/ACT sections or similar markers
    observation, thinking, decision = _extract_reasoning_from_text(text_content)

    # Determine action type
    if tool_calls:
        # Check what kind of tools were called
        tool_names = [tc["tool_name"] for tc in tool_calls]

        if "stop_with_guidance" in tool_names:
            action_type = "stop"
            # Extract stop reason from tool args
            stop_tool = next(tc for tc in tool_calls if tc["tool_name"] == "stop_with_guidance")
            stop_reason = stop_tool["tool_args"].get("reason")
            what_would_help = stop_tool["tool_args"].get("what_would_help", [])
            recommended_next = stop_tool["tool_args"].get("recommended_next", "")

            return DIAgentResponse(
                observation=observation,
                thinking=thinking,
                decision=decision,
                action_type=action_type,
                stop_reason=stop_reason,
                what_would_help=what_would_help,
                recommended_next=recommended_next,
                readiness_before=readiness_before,
                readiness_after=readiness_after,
                gates_affected=gates_affected,
            )

        elif "suggest_discovery_questions" in tool_names:
            action_type = "guidance"
            # Extract guidance from tool args
            guidance_tool = next(tc for tc in tool_calls if tc["tool_name"] == "suggest_discovery_questions")
            focus_area = guidance_tool["tool_args"].get("focus_area", "general")

            # Create placeholder guidance (would be generated by tool execution)
            guidance = ConsultantGuidance(
                summary=f"Need more signal for {focus_area}",
                questions_to_ask=[
                    QuestionToAsk(
                        question="Placeholder - tool would generate actual questions",
                        why_ask="Placeholder reason",
                        listen_for=["Placeholder signals"],
                    )
                ],
                signals_to_watch=["Client pain points", "Business drivers"],
                what_this_unlocks=f"Better understanding of {focus_area}",
            )

            return DIAgentResponse(
                observation=observation,
                thinking=thinking,
                decision=decision,
                action_type=action_type,
                guidance=guidance,
                recommended_next=text_content.split("recommended")[-1][:200] if "recommended" in text_content.lower() else "Ask client the discovery questions",
                readiness_before=readiness_before,
                readiness_after=readiness_after,
                gates_affected=gates_affected,
            )

        else:
            # Regular tool calls (extraction, analysis, etc.)
            action_type = "tool_call"

            # Convert tool calls to ToolCall objects
            from app.agents.di_agent_types import ToolCall
            tool_call_objects = [
                ToolCall(**tc) for tc in tool_calls
            ]

            return DIAgentResponse(
                observation=observation,
                thinking=thinking,
                decision=decision,
                action_type=action_type,
                tools_called=tool_call_objects,
                recommended_next=text_content.split("Next:")[-1][:200] if "Next:" in text_content else "Execute the tool calls to gather missing information",
                readiness_before=readiness_before,
                readiness_after=readiness_after,
                gates_affected=gates_affected,
            )

    else:
        # No tool calls - this is unusual, treat as guidance
        action_type = "guidance"

        guidance = ConsultantGuidance(
            summary=thinking[:200] if thinking else "Analysis of current state",
            questions_to_ask=[],
            signals_to_watch=[],
            what_this_unlocks="Next steps for project",
        )

        return DIAgentResponse(
            observation=observation,
            thinking=thinking,
            decision=decision,
            action_type=action_type,
            guidance=guidance,
            recommended_next=text_content[-300:] if text_content else "Review agent analysis and take next steps",
            readiness_before=readiness_before,
            readiness_after=readiness_after,
            gates_affected=gates_affected,
        )


def _extract_reasoning_from_text(text: str) -> tuple[str, str, str]:
    """Extract OBSERVE, THINK, DECIDE sections from agent text.

    Returns:
        Tuple of (observation, thinking, decision)
    """
    # Try to find structured sections
    text_lower = text.lower()

    observation = ""
    thinking = ""
    decision = ""

    # Look for OBSERVE/OBSERVATION section
    if "observe" in text_lower or "observation" in text_lower:
        start = max(text_lower.find("observe"), text_lower.find("observation"))
        if start >= 0:
            # Find end (next section or 500 chars)
            end_markers = [text_lower.find("think", start), text_lower.find("decide", start)]
            end = min([e for e in end_markers if e > start] or [start + 500])
            observation = text[start:end].strip()

    # Look for THINK/THINKING section
    if "think" in text_lower:
        start = text_lower.find("think")
        if start >= 0:
            end_markers = [text_lower.find("decide", start), text_lower.find("act", start)]
            end = min([e for e in end_markers if e > start] or [start + 500])
            thinking = text[start:end].strip()

    # Look for DECIDE/DECISION section
    if "decide" in text_lower or "decision" in text_lower:
        start = max(text_lower.find("decide"), text_lower.find("decision"))
        if start >= 0:
            end_markers = [text_lower.find("act", start), text_lower.find("recommended", start)]
            end = min([e for e in end_markers if e > start] or [start + 500])
            decision = text[start:end].strip()

    # Fallback: use whole text in chunks if sections not found
    if not observation and not thinking and not decision:
        parts = text.split("\n\n")
        if len(parts) >= 3:
            observation = parts[0]
            thinking = parts[1]
            decision = parts[2]
        elif len(parts) == 2:
            observation = parts[0]
            thinking = parts[1]
            decision = "Proceeding with action"
        else:
            observation = text[:300]
            thinking = text[:500]
            decision = text[:200]

    return observation, thinking, decision
