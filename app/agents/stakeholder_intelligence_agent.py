"""Stakeholder Intelligence Agent - Core reasoning engine.

Progressively enriches individual stakeholder profiles as signals accumulate.
Operates at STAKEHOLDER level (within a project), not client level.

Follows OBSERVE → THINK → DECIDE → ACT pattern.
"""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from anthropic import Anthropic

from app.agents.stakeholder_intelligence_prompts import SI_AGENT_SYSTEM_PROMPT, SI_AGENT_TOOLS
from app.agents.stakeholder_intelligence_types import (
    SIGuidance,
    SIToolCall,
    StakeholderIntelligenceResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.stakeholders import get_stakeholder

logger = get_logger(__name__)


async def invoke_stakeholder_intelligence_agent(
    stakeholder_id: UUID,
    project_id: UUID,
    trigger: Literal[
        "signal_processed", "user_request", "periodic", "ci_agent_completed",
    ],
    trigger_context: str | None = None,
    specific_request: str | None = None,
    focus_areas: list[str] | None = None,
) -> StakeholderIntelligenceResponse:
    """
    Invoke the Stakeholder Intelligence Agent.

    Args:
        stakeholder_id: Stakeholder UUID
        project_id: Project UUID
        trigger: What triggered this invocation
        trigger_context: Additional context about the trigger
        specific_request: Specific user request
        focus_areas: Specific sections to focus on

    Returns:
        StakeholderIntelligenceResponse with reasoning trace and actions
    """
    settings = get_settings()
    start_time = datetime.utcnow()

    logger.info(
        f"Invoking SI Agent for stakeholder {stakeholder_id}, trigger={trigger}",
        extra={"stakeholder_id": str(stakeholder_id), "project_id": str(project_id), "trigger": trigger},
    )

    try:
        # ==================================================================
        # 1. OBSERVE - Load stakeholder state
        # ==================================================================

        stakeholder = get_stakeholder(stakeholder_id)
        if not stakeholder:
            raise ValueError(f"Stakeholder {stakeholder_id} not found")

        # Verify project ownership
        if str(stakeholder.get("project_id")) != str(project_id):
            raise ValueError(f"Stakeholder {stakeholder_id} does not belong to project {project_id}")

        # Compute current completeness
        from app.agents.stakeholder_intelligence_tools import _execute_update_profile_completeness
        completeness_result = await _execute_update_profile_completeness(stakeholder_id, project_id)
        completeness = completeness_result.get("data", {})

        # ==================================================================
        # 2. Build reasoning prompt
        # ==================================================================

        trigger_text = _format_trigger(trigger, trigger_context, specific_request)
        focus_text = ""
        if focus_areas:
            focus_text = f"\n\n**Focus areas:** {', '.join(focus_areas)}\nPrioritize these sections in your analysis."

        # Load recent SI logs so the agent knows what's already been tried
        recent_attempts_text = _format_recent_attempts(stakeholder_id)

        user_prompt = f"""# STAKEHOLDER STATE

## Identity
- **Name:** {stakeholder.get('name', 'Unknown')}
- **Role:** {stakeholder.get('role', 'Not set')}
- **Type:** {stakeholder.get('stakeholder_type', 'Not set')}
- **Email:** {stakeholder.get('email', 'Not set')}
- **Influence:** {stakeholder.get('influence_level', 'Not set')}
- **Organization:** {stakeholder.get('organization', 'Not set')}
- **Profile Completeness:** {completeness.get('score', 0)}/100 ({completeness.get('label', 'Unknown')})

## Section Scores
{_format_sections(completeness.get('sections', {}))}

## Current Enrichment Fields
{_format_enrichment_fields(stakeholder)}

## External Data Availability
- **LinkedIn URL:** {stakeholder.get('linkedin_profile') or 'NOT SET — ask consultant to provide'}
- **Email:** {stakeholder.get('email') or 'NOT SET'}
- **Organization:** {stakeholder.get('organization') or 'NOT SET'}
- **Enrichment Status:** {stakeholder.get('enrichment_status') or 'pending'}

## Evidence
- Source signals: {len(stakeholder.get('source_signal_ids') or [])}
- Evidence items: {len(stakeholder.get('evidence') or [])}
- Priorities: {json.dumps(stakeholder.get('priorities') or [], default=str)[:200]}
- Concerns: {json.dumps(stakeholder.get('concerns') or [], default=str)[:200]}
- Notes: {(stakeholder.get('notes') or 'None')[:300]}
{recent_attempts_text}
---

# YOUR TASK

{trigger_text}
{focus_text}

Follow OBSERVE → THINK → DECIDE → ACT:

1. **OBSERVE:** Review stakeholder profile completeness and section scores above
2. **THINK:** Which section has the biggest gap? What's the highest-leverage action?
3. **DECIDE:** Choose ONE tool to call (prefer enriching the thinnest section)
4. **ACT:** Execute your decision

The stakeholder_id for all tools is: {str(stakeholder_id)}
The project_id for all tools is: {str(project_id)}

CRITICAL RULES:
- NEVER repeat a tool that was already tried (see Recent Attempts above). Pick a DIFFERENT tool.
- Inference tools (enrich_engagement_profile, analyze_decision_authority, synthesize_win_conditions, detect_communication_patterns, infer_relationships) can infer from role, type, influence level, and project signals even without direct evidence.
- Only call enrich_from_external_sources if it has NOT been tried yet AND LinkedIn/email are available.
- Enrich the THINNEST section first (lowest score relative to max)
- If core identity is incomplete, flag that first

What's your reasoning and recommended action?"""

        # ==================================================================
        # 3. Call LLM
        # ==================================================================

        anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        anthropic_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in SI_AGENT_TOOLS
        ]

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SI_AGENT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=anthropic_tools,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={"effort": "medium"},
            thinking={"type": "adaptive"},
        )

        # Log LLM usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="stakeholder_intelligence",
            model=response.model,
            provider="anthropic",
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            tokens_cache_read=getattr(response.usage, "cache_read_input_tokens", 0),
            tokens_cache_create=getattr(response.usage, "cache_creation_input_tokens", 0),
            project_id=project_id,
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
            from app.agents.stakeholder_intelligence_tools import execute_si_tool

            for tool_call in agent_response.tools_called:
                try:
                    result = await execute_si_tool(
                        tool_name=tool_call.tool_name,
                        tool_args=tool_call.tool_args,
                        stakeholder_id=stakeholder_id,
                        project_id=project_id,
                    )
                    tool_call.result = result.get("data")
                    tool_call.success = result.get("success", False)
                    tool_call.error = result.get("error")

                    logger.info(
                        f"SI Tool {tool_call.tool_name}: {'OK' if tool_call.success else 'FAIL'}",
                        extra={"stakeholder_id": str(stakeholder_id), "tool": tool_call.tool_name},
                    )
                except Exception as e:
                    logger.error(f"SI tool {tool_call.tool_name} error: {e}")
                    tool_call.success = False
                    tool_call.error = str(e)

            # Recompute completeness after tools
            updated = await _execute_update_profile_completeness(stakeholder_id, project_id)
            agent_response.profile_completeness_after = updated.get("data", {}).get("score")

            # Track which fields were affected
            affected = set()
            for tc in agent_response.tools_called:
                affected.update(_tool_to_fields(tc.tool_name))
                if tc.result and isinstance(tc.result, dict):
                    affected.update(tc.result.get("fields_updated", []))
            agent_response.fields_affected = list(affected)

        # ==================================================================
        # 6. Log invocation
        # ==================================================================

        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        try:
            _log_invocation(
                stakeholder_id=stakeholder_id,
                project_id=project_id,
                trigger=trigger,
                agent_response=agent_response,
                trigger_context=trigger_context or specific_request,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to log SI agent invocation: {e}")

        logger.info(
            f"SI Agent completed: action={agent_response.action_type}, "
            f"completeness={agent_response.profile_completeness_before}→{agent_response.profile_completeness_after}",
            extra={"stakeholder_id": str(stakeholder_id)},
        )

        return agent_response

    except Exception as e:
        logger.error(f"SI Agent error for stakeholder {stakeholder_id}: {e}", exc_info=True)
        raise


# =============================================================================
# Helpers
# =============================================================================


def _format_recent_attempts(stakeholder_id: UUID) -> str:
    """Load recent SI agent invocations so the agent doesn't repeat failed tools."""
    try:
        from app.db.supabase_client import get_supabase

        supabase = get_supabase()
        logs = (
            supabase.table("stakeholder_intelligence_logs")
            .select("action_type, action_summary, tools_called, stop_reason, created_at")
            .eq("stakeholder_id", str(stakeholder_id))
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if not logs.data:
            return ""

        lines = ["\n## Recent Attempts (DO NOT repeat these tools)"]
        for log in logs.data:
            tools = log.get("tools_called") or []
            tool_names = [t.get("tool_name", "?") for t in tools]
            successes = [t.get("success", False) for t in tools]
            summary = log.get("action_summary") or log.get("stop_reason") or "no result"
            status = "OK" if all(successes) and successes else "NO EFFECT"
            # Mark as no effect if tool ran but completeness didn't change
            if summary and ("0 fields" in summary or "none" in summary.lower()):
                status = "NO EFFECT"
            lines.append(f"- Tool: {', '.join(tool_names)} → {status}: {summary}")

        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"Failed to load recent SI logs: {e}")
        return ""


def _format_trigger(trigger: str, context: str | None, specific: str | None) -> str:
    """Format trigger information."""
    trigger_map = {
        "signal_processed": "A new signal was processed. Check for new stakeholder evidence.",
        "user_request": f"Consultant request: {specific or 'Analyze this stakeholder'}",
        "periodic": "Scheduled periodic profile update.",
        "ci_agent_completed": "Client Intelligence Agent completed. Cross-reference organizational insights.",
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
        "core_identity": 10,
        "engagement_profile": 20,
        "decision_authority": 20,
        "relationships": 20,
        "communication": 10,
        "win_conditions_concerns": 15,
        "evidence_depth": 5,
    }

    lines = []
    for section, score in sorted(sections.items(), key=lambda x: x[1]):
        max_s = max_scores.get(section, 10)
        bar_len = int((score / max_s) * 10) if max_s > 0 else 0
        bar = "█" * bar_len + "░" * (10 - bar_len)
        lines.append(f"- {bar} {score}/{max_s} — {section.replace('_', ' ').title()}")

    return "\n".join(lines)


def _format_enrichment_fields(stakeholder: dict) -> str:
    """Show which enrichment fields are populated vs empty."""
    fields = {
        "engagement_level": stakeholder.get("engagement_level"),
        "engagement_strategy": stakeholder.get("engagement_strategy"),
        "risk_if_disengaged": stakeholder.get("risk_if_disengaged"),
        "decision_authority": stakeholder.get("decision_authority"),
        "approval_required_for": stakeholder.get("approval_required_for"),
        "veto_power_over": stakeholder.get("veto_power_over"),
        "reports_to_id": stakeholder.get("reports_to_id"),
        "allies": stakeholder.get("allies"),
        "potential_blockers": stakeholder.get("potential_blockers"),
        "preferred_channel": stakeholder.get("preferred_channel"),
        "communication_preferences": stakeholder.get("communication_preferences"),
        "last_interaction_date": stakeholder.get("last_interaction_date"),
        "win_conditions": stakeholder.get("win_conditions"),
        "key_concerns": stakeholder.get("key_concerns"),
    }

    lines = []
    for field, value in fields.items():
        if value:
            display = str(value)[:100]
            lines.append(f"  ✓ {field}: {display}")
        else:
            lines.append(f"  ✗ {field}: EMPTY")

    return "\n".join(lines)


def _parse_response(
    llm_response,
    profile_completeness_before: int,
) -> StakeholderIntelligenceResponse:
    """Parse LLM response into StakeholderIntelligenceResponse."""
    text_content = ""
    tool_calls = []

    for block in llm_response.content:
        if block.type == "thinking":
            continue
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
            return StakeholderIntelligenceResponse(
                observation=observation,
                thinking=thinking,
                decision=decision,
                action_type="stop",
                stop_reason=args.get("reason"),
                guidance=SIGuidance(
                    summary=args.get("reason", ""),
                    missing_info=args.get("missing_info", []),
                    suggested_actions=args.get("suggested_actions", []),
                    next_session_topics=args.get("next_session_topics", []),
                ),
                recommended_next="Gather the missing information in the next stakeholder interaction",
                profile_completeness_before=profile_completeness_before,
            )

        # Regular tool calls
        return StakeholderIntelligenceResponse(
            observation=observation,
            thinking=thinking,
            decision=decision,
            action_type="tool_call",
            tools_called=[SIToolCall(**tc) for tc in tool_calls],
            recommended_next="Review the analysis results and confirm insights",
            profile_completeness_before=profile_completeness_before,
        )

    # No tool calls — guidance only
    return StakeholderIntelligenceResponse(
        observation=observation,
        thinking=thinking,
        decision=decision,
        action_type="guidance",
        guidance=SIGuidance(
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

        if tool_name == "enrich_engagement_profile":
            level = result.get("engagement_level", "")
            parts.append(f"Engagement: {level}" if level else "Analyzed engagement")
        elif tool_name == "analyze_decision_authority":
            authority = result.get("decision_authority", "")
            parts.append(f"Authority: {authority[:50]}" if authority else "Analyzed authority")
        elif tool_name == "infer_relationships":
            resolved = result.get("resolved", {})
            count = sum(1 for v in resolved.values() if v)
            parts.append(f"Resolved {count} relationships")
        elif tool_name == "detect_communication_patterns":
            channel = result.get("preferred_channel", "")
            parts.append(f"Channel: {channel}" if channel else "Analyzed communication")
        elif tool_name == "synthesize_win_conditions":
            wc = result.get("win_conditions", [])
            kc = result.get("key_concerns", [])
            parts.append(f"{len(wc)} win conditions, {len(kc)} concerns")
        elif tool_name == "cross_reference_ci_insights":
            insights = result.get("insights", "")
            parts.append(f"CI cross-ref: {insights[:50]}" if insights else "Cross-referenced CI")
        elif tool_name == "enrich_from_external_sources":
            sources = result.get("sources_succeeded", [])
            updated = result.get("fields_updated", [])
            parts.append(f"External: {', '.join(sources) or 'none'} → {len(updated)} fields")
        elif tool_name == "update_profile_completeness":
            score = result.get("score")
            parts.append(f"Score: {score}/100" if score else "Updated completeness")
        else:
            parts.append(tool_name.replace("_", " "))

    return "; ".join(parts)


def _tool_to_fields(tool_name: str) -> list[str]:
    """Map tool name to affected profile fields."""
    mapping = {
        "enrich_engagement_profile": ["engagement_level", "engagement_strategy", "risk_if_disengaged"],
        "analyze_decision_authority": ["decision_authority", "approval_required_for", "veto_power_over"],
        "infer_relationships": ["reports_to_id", "allies", "potential_blockers"],
        "detect_communication_patterns": ["preferred_channel", "communication_preferences", "last_interaction_date"],
        "synthesize_win_conditions": ["win_conditions", "key_concerns"],
        "cross_reference_ci_insights": [],
        "enrich_from_external_sources": ["role", "organization", "domain_expertise", "decision_authority", "engagement_strategy"],
        "update_profile_completeness": ["profile_completeness"],
        "stop_with_guidance": [],
    }
    return mapping.get(tool_name, [])


def _log_invocation(
    stakeholder_id: UUID,
    project_id: UUID,
    trigger: str,
    agent_response: StakeholderIntelligenceResponse,
    trigger_context: str | None,
    execution_time_ms: int,
) -> None:
    """Log agent invocation to stakeholder_intelligence_logs table."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    action_summary = _generate_action_summary(agent_response.tools_called or [])

    log_data = {
        "stakeholder_id": str(stakeholder_id),
        "project_id": str(project_id),
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
        "fields_affected": agent_response.fields_affected,
        "stop_reason": agent_response.stop_reason,
        "execution_time_ms": execution_time_ms,
        "llm_model": "claude-sonnet-4-6",
        "success": True,
    }

    supabase.table("stakeholder_intelligence_logs").insert(log_data).execute()
